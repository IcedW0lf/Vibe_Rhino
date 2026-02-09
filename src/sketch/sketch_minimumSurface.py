import math
import Rhino
import Rhino.DocObjects as rd
import Rhino.Geometry as rg
import scriptcontext as sc



def _lerp(a, b, t):
    return a + (b - a) * t

def _enneper(u, v, scale):
    # Enneper is a classic analytic minimal surface with mean curvature = 0.
    x = u - (u**3) / 3.0 + u * v * v
    y = v - (v**3) / 3.0 + v * u * u
    z = (u * u - v * v)
    return rg.Point3d(x * scale, y * scale, z * scale)


def _build_mesh(res_u=20, res_v=10, span=1.4, scale=3.0):
    mesh = rg.Mesh()

    for i in range(res_u + 1):
        u = _lerp(-span, span, i / float(res_u))
        for j in range(res_v + 1):
            v = _lerp(-span, span, j / float(res_v))
            mesh.Vertices.Add(_enneper(u, v, scale))

    stride = res_v + 1
    for i in range(res_u):
        for j in range(res_v):
            a = i * stride + j
            b = a + 1
            c = a + stride + 1
            d = a + stride
            mesh.Faces.AddFace(a, b, c, d)

    mesh.Normals.ComputeNormals()
    mesh.Compact()
    mesh.Weld(math.pi)  # smooth shading
    mesh.UnifyNormals()
    return mesh


def _add_wireframe(doc, mesh):
    """Add the mesh's topology edges as separate line objects for visualization."""
    wire_attrs = rd.ObjectAttributes()
    wire_attrs.Name = "Enneper wireframe"
    for i in range(mesh.TopologyEdges.Count):
        edge = mesh.TopologyEdges.EdgeLine(i)
        if edge.IsValid:
            doc.Objects.AddLine(edge, wire_attrs)


def build(doc):
    """
    Creates an Enneper minimal surface mesh centered at the origin.

    Use the Vibe watcher by pointing TARGET_SCRIPT to this file, or run it
    directly in Rhino (`_RunPythonScript`) to populate the active document.
    """
    mesh = _build_mesh()
    attributes = rd.ObjectAttributes()
    attributes.Name = "Enneper minimal surface"
    doc.Objects.AddMesh(mesh, attributes)
    _add_wireframe(doc, mesh)

    # Simple frame to keep orientation in viewports.
    axis_len = 8.0
    doc.Objects.AddLine(rg.Line(rg.Point3d.Origin, rg.Point3d(axis_len, 0, 0)))
    doc.Objects.AddLine(rg.Line(rg.Point3d.Origin, rg.Point3d(0, axis_len, 0)))
    doc.Objects.AddLine(rg.Line(rg.Point3d.Origin, rg.Point3d(0, 0, axis_len)))


if __name__ == "__main__":
    # Allow running without the watcher for quick previews.
    doc = sc.doc or Rhino.RhinoDoc.ActiveDoc
    if doc is not None:
        doc.Objects.Clear()
        build(doc)
        doc.Views.Redraw()
