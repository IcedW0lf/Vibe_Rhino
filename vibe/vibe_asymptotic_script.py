import math
import System
import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc

"""
Variant of the live geometry script where both grid edge families
are driven toward surface asymptotic directions (no geodesic family).
"""

# Global tuning parameters
U_VERTS = 21  # number of vertices along surface U direction (quads = U_VERTS-1)
V_VERTS = 21  # number of vertices along surface V direction (quads = V_VERTS-1)
ITERATIONS = 20
STEP_SIZE = 0.15

W_ASYMPTOTIC = 1.0
W_FAIRNESS = 0.1
W_SURFACE = 2.0


EPS = 1e-8
LOG = True
OUTPUT_LAYER_NAME = "ag_output"
TARGET_LAYER_NAME = "ag_surface"  # optional: place your reference surface here



# ------------------------------------------------------------
# Utility helpers
# ------------------------------------------------------------
def clamp(val, lo=-1.0, hi=1.0):
    return max(lo, min(hi, val))


def log(msg):
    if LOG:
        Rhino.RhinoApp.WriteLine("[vibe] " + str(msg))


def safe_unit(vec):
    v = rg.Vector3d(vec)
    if v.IsTiny(EPS):
        return None, 0.0
    length = v.Length
    v.Unitize()
    return v, length


def project_to_tangent(vec, normal):
    # Remove normal component so the result lies in the tangent plane.
    return vec - normal * rg.Vector3d.Multiply(vec, normal)


def asymptotic_directions_from_principal(k1, k2, d1, d2):
    """
    Compute the two asymptotic directions given principal curvature values and directions.
    Formula: tan^2(theta) = -k1/k2 (hyperbolic regions only).
    Returns None if Gaussian curvature is non-negative.
    """
    if k1 * k2 >= 0:
        return None
    if abs(k2) < EPS:
        return None

    ratio = -k1 / k2
    if ratio < 0:
        return None
    root = math.sqrt(ratio)

    a1 = rg.Vector3d(d1)
    a1 += d2 * root
    a2 = rg.Vector3d(d1)
    a2 -= d2 * root
    a1.Unitize()
    a2.Unitize()
    return (a1, a2)

def select_asym_dir(candidates, tangent):
    """
    Pick the asymptotic direction that best matches the current edge tangent.
    """
    if candidates is None:
        return None
    best = None
    best_dot = -1.0
    for c in candidates:
        dot = abs(rg.Vector3d.Multiply(c, tangent))
        if dot > best_dot:
            best_dot = dot
            best = c
    return best

# ------------------------------------------------------------
# Surface acquisition and initial mesh generation
# ------------------------------------------------------------
def create_default_saddle_surface(width=20.0, depth=20.0, sag=5.0):
    """
    Create a simple hyperbolic paraboloid as fallback reference surface.
    z = sag * ( (x/width)^2 - (y/depth)^2 )
    """
    u_count = 6
    v_count = 6
    pts = []
    for i in range(u_count):
        u = -0.5 + i / float(u_count - 1)
        x = u * width
        for j in range(v_count):
            v = -0.5 + j / float(v_count - 1)
            y = v * depth
            z = sag * ((u * 2) ** 2 - (v * 2) ** 2)
            pts.append(rg.Point3d(x, y, z))

    # NurbsSurface.CreateFromPoints expects a flat list with counts.
    surf = rg.NurbsSurface.CreateFromPoints(pts, u_count, v_count, 3, 3)
    return surf


def find_reference_surface(doc):
    """
    Find a reference surface/Brep face/extrusion. Do NOT create fallback geometry;
    if nothing is found, return None so build can bail without touching the scene.
    """
    log("searching for reference surface in doc...")

    # Helper to choose the first suitable surface-like object from a list.
    def pick_surface(seq, label):
        for obj in seq:
            if obj is None or obj.IsDeleted:
                continue
            geo = obj.Geometry
            if isinstance(geo, rg.Brep) and geo.Faces.Count > 0:
                log("using {} Brep face as surface".format(label))
                return geo.Faces[0].ToNurbsSurface()
            if isinstance(geo, rg.BrepFace):
                log("using {} BrepFace".format(label))
                return geo.ToNurbsSurface()
            if isinstance(geo, rg.Surface):
                log("using {} Surface".format(label))
                return geo.ToNurbsSurface()
            if isinstance(geo, rg.Extrusion):
                log("using {} Extrusion -> Surface".format(label))
                return geo.ToNurbsSurface()
            # Mesh cannot supply differential data we need; skip.
        return None


    # 1) Explicit selection only (objects or sub-objects)
    selected_objs = list(doc.Objects.GetSelectedObjects(False, False) or [])
    log("selected objects: {}".format(len(selected_objs)))
    surf = pick_surface(selected_objs, "selected")
    if surf:
        return surf

    selected_sub = list(doc.Objects.GetSelectedObjects(False, True) or [])
    log("selected sub-objects: {}".format(len(selected_sub)))
    for objref in selected_sub:
        try:
            face = objref.Face()
        except Exception:
            face = None
        if face:
            log("using selected BrepFace (sub-object)")
            return face.ToNurbsSurface()

    # Fallback: any non-deleted object in the doc
    for obj in doc.Objects:
        if obj.IsDeleted:
            continue
        geo = obj.Geometry
        try:
            geo_name = type(geo).__name__
        except Exception:
            geo_name = "Unknown"
        log(" found object type: {}".format(geo_name))
        if isinstance(geo, rg.Brep) and geo.Faces.Count > 0:
            log("using first Brep face as surface")
            return geo.Faces[0].ToNurbsSurface()
        if isinstance(geo, rg.Surface):
            log("using first standalone surface")
            return geo.ToNurbsSurface()
        if isinstance(geo, rg.Extrusion):
            log("using first Extrusion -> Surface")
            return geo.ToNurbsSurface()
        if isinstance(geo, rg.BrepFace):
            log("using first BrepFace")
            return geo.ToNurbsSurface()
    log("no surface found; skipping build (no geometry will be added)")
    return None


class GridMesh(object):
    """
    Structured quad mesh wrapper carrying uv parameters and edge family labels.
    Both grid directions are constrained to asymptotic directions on the surface.
    """

    def __init__(self, mesh, u_count, v_count, uv_params, edge_family, neighbors):
        self.mesh = mesh
        self.u_count = u_count
        self.v_count = v_count
        self.uv = uv_params  # list[Point2d]
        self.edge_family = edge_family  # dict[(i,j)]->str
        self.neighbors = neighbors  # list[list[int]]

    def idx(self, i, j):
        return i * self.v_count + j

    def valid(self, i, j):
        return 0 <= i < self.u_count and 0 <= j < self.v_count

    def vertex(self, i, j):
        return self.mesh.Vertices[self.idx(i, j)]


def build_param_grid(surface, u_count, v_count):
    """
    Sample the surface on a regular uv grid to create a quad mesh with stored uv coordinates.
    """
    log("building param grid {}x{}".format(u_count, v_count))
    u_dom = surface.Domain(0)
    v_dom = surface.Domain(1)

    mesh = rg.Mesh()
    uv_params = []

    for i in range(u_count):
        u = u_dom.T0 + (u_dom.T1 - u_dom.T0) * (i / float(u_count - 1))
        for j in range(v_count):
            v = v_dom.T0 + (v_dom.T1 - v_dom.T0) * (j / float(v_count - 1))
            pt = surface.PointAt(u, v)
            mesh.Vertices.Add(pt)
            uv_params.append(rg.Point2d(u, v))
            mesh.TextureCoordinates.Add(u, v)

    for i in range(u_count - 1):
        for j in range(v_count - 1):
            a = i * v_count + j
            b = (i + 1) * v_count + j
            c = (i + 1) * v_count + (j + 1)
            d = i * v_count + (j + 1)
            mesh.Faces.AddFace(a, b, c, d)

    mesh.Normals.ComputeNormals()
    mesh.Compact()
    log("grid vertices: {}, faces: {}".format(mesh.Vertices.Count, mesh.Faces.Count))

    # Edge family labels (sorted vertex tuple as key)
    edge_family = {}
    for i in range(u_count - 1):
        for j in range(v_count):
            v0 = i * v_count + j
            v1 = (i + 1) * v_count + j
            edge_family[tuple(sorted((v0, v1)))] = "asym"
    for i in range(u_count):
        for j in range(v_count - 1):
            v0 = i * v_count + j
            v1 = i * v_count + (j + 1)
            edge_family[tuple(sorted((v0, v1)))] = "asym"

    # Vertex neighbors for Laplacian fairness (4-neighborhood on grid)
    neighbors = [[] for _ in range(u_count * v_count)]
    for i in range(u_count):
        for j in range(v_count):
            idx = i * v_count + j
            if i > 0:
                neighbors[idx].append((i - 1) * v_count + j)
            if i < u_count - 1:
                neighbors[idx].append((i + 1) * v_count + j)
            if j > 0:
                neighbors[idx].append(i * v_count + j - 1)
            if j < v_count - 1:
                neighbors[idx].append(i * v_count + j + 1)

    return GridMesh(mesh, u_count, v_count, uv_params, edge_family, neighbors)

# ------------------------------------------------------------
# Differential geometry evaluation
# ------------------------------------------------------------
class SurfData(object):
    def __init__(self, normals, principal1, principal2, curvatures, asym_dirs):
        self.normals = normals
        self.principal1 = principal1
        self.principal2 = principal2
        self.curvatures = curvatures
        self.asym_dirs = asym_dirs


def evaluate_surface_data(surface, grid):
    log("evaluating surface data...")
    normals = []
    p1 = []
    p2 = []
    curvatures = []
    asym_dirs = []

    for uv in grid.uv:
        try:
            scurv = surface.CurvatureAt(uv.X, uv.Y)
            n = scurv.Normal
            n.Unitize()
            d1 = rg.Vector3d(scurv.Direction1)
            d2 = rg.Vector3d(scurv.Direction2)
            d1.Unitize()
            d2.Unitize()
            k1 = scurv.K1
            k2 = scurv.K2
            asym = asymptotic_directions_from_principal(k1, k2, d1, d2)
        except Exception:
            # Fallback: approximate tangents from local frame.
            success, frame = surface.FrameAt(uv.X, uv.Y)
            if not success:
                n = surface.NormalAt(uv.X, uv.Y)
                n.Unitize()
                d1 = rg.Vector3d(1, 0, 0)
                d2 = rg.Vector3d(0, 1, 0)
            else:
                n = frame.ZAxis
                d1 = frame.XAxis
                d2 = frame.YAxis
                n.Unitize()
                d1.Unitize()
                d2.Unitize()
            k1 = k2 = 0.0
            asym = None

        normals.append(n)
        p1.append(d1)
        p2.append(d2)
        curvatures.append((k1, k2))
        asym_dirs.append(asym)

    return SurfData(normals, p1, p2, curvatures, asym_dirs)



# ------------------------------------------------------------
# Energy and forces
# ------------------------------------------------------------
def add_asymptotic_forces(grid, surf_data, forces):
    mesh = grid.mesh
    for edge, family in grid.edge_family.items():
        if family != "asym":
            continue
        i, j = edge
        pi = mesh.Vertices[i]
        pj = mesh.Vertices[j]
        t_vec = pj - pi
        t_unit, t_len = safe_unit(t_vec)
        if t_unit is None:
            continue

        n_avg = rg.Vector3d(surf_data.normals[i])
        n_avg += surf_data.normals[j]
        if n_avg.IsTiny(EPS):
            continue
        n_avg.Unitize()

        asym_i = select_asym_dir(surf_data.asym_dirs[i], t_unit)
        asym_j = select_asym_dir(surf_data.asym_dirs[j], t_unit)
        target = None
        if asym_i and asym_j:
            target = asym_i + asym_j
        elif asym_i:
            target = asym_i
        elif asym_j:
            target = asym_j
        if target is None or target.IsTiny(EPS):
            continue

        target = project_to_tangent(target, n_avg)
        if target.IsTiny(EPS):
            continue
        target.Unitize()

        cross = rg.Vector3d.CrossProduct(t_unit, target)
        correction = rg.Vector3d.CrossProduct(cross, t_unit)
        if correction.IsTiny(EPS):
            continue

        forces[i] += correction * (W_ASYMPTOTIC / max(t_len, EPS))
        forces[j] -= correction * (W_ASYMPTOTIC / max(t_len, EPS))


def add_fairness_forces(grid, forces):
    mesh = grid.mesh
    for idx, neigh in enumerate(grid.neighbors):
        if not neigh:
            continue
        avg_vec = rg.Vector3d(0, 0, 0)
        for n in neigh:
            avg_vec += rg.Vector3d(mesh.Vertices[n])
        avg_vec *= 1.0 / float(len(neigh))
        lap = avg_vec - rg.Vector3d(mesh.Vertices[idx])
        forces[idx] += lap * W_FAIRNESS


def add_surface_forces(surface, grid, forces):
    mesh = grid.mesh
    for idx in range(mesh.Vertices.Count):
        pt = rg.Point3d(mesh.Vertices[idx])
        success, u, v = surface.ClosestPoint(pt)
        if not success:
            continue
        target = surface.PointAt(u, v)
        forces[idx] += rg.Vector3d(target - pt) * W_SURFACE
        grid.uv[idx] = rg.Point2d(u, v)


# ------------------------------------------------------------
# Optimisation loop
# ------------------------------------------------------------
def optimize_mesh(surface, grid):
    mesh = grid.mesh
    log("starting optimisation iterations: {}".format(ITERATIONS))
    for it in range(ITERATIONS):
        surf_data = evaluate_surface_data(surface, grid)
        forces = [rg.Vector3d(0, 0, 0) for _ in range(mesh.Vertices.Count)]

        add_asymptotic_forces(grid, surf_data, forces)
        add_fairness_forces(grid, forces)
        add_surface_forces(surface, grid, forces)

        for idx, f in enumerate(forces):
            if f.IsTiny(EPS):
                continue
            if f.Length > 1.0:
                f.Unitize()
            move = f * STEP_SIZE
            new_pt = rg.Point3d(mesh.Vertices[idx]) + move

            success, u, v = surface.ClosestPoint(new_pt)
            if success:
                snapped = surface.PointAt(u, v)
                mesh.Vertices.SetVertex(idx, snapped)
                grid.uv[idx] = rg.Point2d(u, v)
            else:
                mesh.Vertices.SetVertex(idx, new_pt)

        mesh.Normals.ComputeNormals()
        if it % 5 == 4:
            log(" iteration {} done".format(it + 1))
    log("optimisation finished")


# ------------------------------------------------------------
# Result presentation
# ------------------------------------------------------------
def add_family_polylines(doc, grid, layer_index=None):
    mesh = grid.mesh
    nv = grid.v_count
    attr = Rhino.DocObjects.ObjectAttributes()
    if layer_index is not None:
        attr.LayerIndex = layer_index
    # U-curves (asymptotic family)
    for j in range(grid.v_count):
        pts = [rg.Point3d(mesh.Vertices[i * nv + j]) for i in range(grid.u_count)]
        doc.Objects.AddPolyline(pts, attr)

    # V-curves (also asymptotic in this variant)
    for i in range(grid.u_count):
        pts = [rg.Point3d(mesh.Vertices[i * nv + j]) for j in range(grid.v_count)]
        doc.Objects.AddPolyline(pts, attr)


def add_mesh(doc, grid, layer_index=None):
    attr = Rhino.DocObjects.ObjectAttributes()
    if layer_index is not None:
        attr.LayerIndex = layer_index
    doc.Objects.AddMesh(grid.mesh, attr)


def ensure_output_layer(doc):
    layer = doc.Layers.FindName(OUTPUT_LAYER_NAME)
    if layer:
        return layer
    new_layer = Rhino.DocObjects.Layer()
    new_layer.Name = OUTPUT_LAYER_NAME
    new_layer.Color = System.Drawing.Color.FromArgb(255, 80, 120, 200)
    idx = doc.Layers.Add(new_layer)
    return doc.Layers[idx]


def clear_output_layer(doc, layer):
    objs = list(doc.Objects.FindByLayer(layer) or [])
    removed = 0
    for o in objs:
        if not o.IsDeleted:
            doc.Objects.Delete(o, True)
            removed += 1
    if removed:
        log("cleared {} objects from {}".format(removed, layer.FullPath))


# ------------------------------------------------------------
# Entry point
# ------------------------------------------------------------
def build(doc):
    try:
        log("build() starting (objects in doc: {})".format(doc.Objects.Count))
        surface = find_reference_surface(doc)
        if surface is None:
            log("build() aborted: no reference surface")
            return
        out_layer = ensure_output_layer(doc)
        clear_output_layer(doc, out_layer)
        grid = build_param_grid(surface, U_VERTS, V_VERTS)
        optimize_mesh(surface, grid)
        add_mesh(doc, grid, out_layer.Index)
        add_family_polylines(doc, grid, out_layer.Index)
        log("build() finished successfully (objects now: {})".format(doc.Objects.Count))
    except Exception as exc:
        log("build() failed: {}".format(exc))
        import traceback

        log(traceback.format_exc())
