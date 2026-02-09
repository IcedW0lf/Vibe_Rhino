import Rhino.Geometry as rg



def build(doc):
    # Clear and rebuild happens in the watcher.
    doc.Objects.AddPoint(rg.Point3d(0, 0, 0))

    line = rg.Line(rg.Point3d(0, 0, 0), rg.Point3d(5, 0, 0))
    doc.Objects.AddLine(line)

    circle = rg.Circle(rg.Plane(rg.Point3d(5, 5, 0), rg.Vector3d.ZAxis), 3.0)
    doc.Objects.AddCircle(circle)

    sphere = rg.Sphere(rg.Point3d(15, 5, 5), 4.0)
    doc.Objects.AddSphere(sphere)

    polyline = rg.Polyline(
        [
            rg.Point3d(0, 10, 0),
            rg.Point3d(3, 12, 0),
            rg.Point3d(6, 11, 0),
            rg.Point3d(8, 14, 0),
        ]
    )
    doc.Objects.AddPolyline(polyline)
