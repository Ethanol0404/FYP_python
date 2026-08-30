using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using UnityEngine;

namespace LiverAR
{
    public static class ObjMeshReader
    {
        public static Mesh Read(string path)
        {
            var vertices = new List<Vector3>();
            var triangles = new List<int>();
            foreach (var line in File.ReadLines(path))
            {
                var parts = line.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
                if (parts.Length < 2) continue;
                if (parts[0] == "v" && parts.Length >= 4)
                {
                    vertices.Add(new Vector3(Parse(parts[1]), Parse(parts[2]), Parse(parts[3])));
                }
                else if (parts[0] == "f" && parts.Length >= 4)
                {
                    var first = FaceIndex(parts[1]);
                    for (var i = 2; i < parts.Length - 1; i++)
                    {
                        triangles.Add(first); triangles.Add(FaceIndex(parts[i])); triangles.Add(FaceIndex(parts[i + 1]));
                    }
                }
            }
            var mesh = new Mesh { indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 };
            mesh.SetVertices(vertices); mesh.SetTriangles(triangles, 0); mesh.RecalculateNormals(); mesh.RecalculateBounds();
            return mesh;
        }

        static float Parse(string value) => float.Parse(value, CultureInfo.InvariantCulture);
        static int FaceIndex(string token) => int.Parse(token.Split('/')[0], CultureInfo.InvariantCulture) - 1;
    }
}
