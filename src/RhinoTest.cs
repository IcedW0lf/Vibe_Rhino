using System;
using System.IO;
using System.Text;
using System.Diagnostics;
using Rhino.FileIO;
using Rhino.Geometry;

Console.WriteLine("Rhino 8 Geometry Test - Creating 3DM File");
Console.WriteLine(new string('=', 50));

try
{
    var outputPath = Path.Combine(Directory.GetCurrentDirectory(), "test_geometry.3dm");
    var file3dm = new File3dm();

    file3dm.Objects.AddPoint(new Point3d(0, 0, 0));
    file3dm.Objects.AddLine(new Line(new Point3d(0, 0, 0), new Point3d(10, 0, 0)));

    var circle = new Circle(new Plane(new Point3d(5, 5, 0), Vector3d.ZAxis), 3.0);
    file3dm.Objects.AddCircle(circle);

    var sphere = new Sphere(new Point3d(15, 5, 5), 4.0);
    file3dm.Objects.AddSphere(sphere);

    var polyline = new Polyline(new[]
    {
        new Point3d(0, 10, 0),
        new Point3d(3, 12, 0),
        new Point3d(6, 11, 0),
        new Point3d(8, 14, 0),
    });
    file3dm.Objects.AddPolyline(polyline);

    var ok = file3dm.Write(outputPath, 8);
    if (!ok)
    {
        Console.WriteLine("[ERR] Failed to write 3DM file.");
        return;
    }

    byte[] header = new byte[28];
    using (var fs = new FileStream(outputPath, FileMode.Open, FileAccess.Read))
    {
        fs.Read(header, 0, 28);
    }

    string headerText = Encoding.ASCII.GetString(header).TrimEnd('\0');
    bool isValid3dm = headerText.IndexOf("3D Geometry File Format", StringComparison.OrdinalIgnoreCase) >= 0;

    var fileInfo = new FileInfo(outputPath);
    Console.WriteLine($"[OK] Created file: {Path.GetFullPath(outputPath)}");
    Console.WriteLine($"  File size: {fileInfo.Length} bytes");
    Console.WriteLine($"  Valid 3DM header: {(isValid3dm ? "Yes" : "No")}");

    LaunchRhinoViewer(outputPath);

    Console.WriteLine(new string('=', 50));
    Console.WriteLine("[OK] Setup complete!");
}
catch (Exception ex)
{
    Console.WriteLine($"[ERR] {ex.Message}");
    Console.WriteLine(ex.StackTrace);
}

static void LaunchRhinoViewer(string filePath)
{
    var rhinoExe = @"C:\Program Files\Rhino 8\System\Rhino.exe";
    if (!File.Exists(rhinoExe))
    {
        Console.WriteLine("[WARN] Rhino 8 not found. Skipping viewer launch.");
        return;
    }

    var psi = new ProcessStartInfo
    {
        FileName = rhinoExe,
        Arguments = $"\"{filePath}\"",
        UseShellExecute = true
    };

    Process.Start(psi);
    Console.WriteLine("[OK] Launched Rhino 8 to view the file.");
}
