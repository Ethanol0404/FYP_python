using System.IO;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.XR.ARFoundation;

namespace LiverAR
{
    public class LiverARModelLoader : MonoBehaviour
    {
        [System.Serializable]
        class ExportMetadata { public ModelMetadata[] models; }

        [System.Serializable]
        class ModelMetadata { public string id; public string displayName; public string file; }

        [SerializeField] ARAnchorManager anchorManager;
        [SerializeField] Material defaultMaterial;

        public void LoadFolder(string folderPath, Pose pose)
        {
            var anchor = anchorManager.AddAnchor(pose);
            if (anchor == null) { Debug.LogError("Could not create AR anchor."); return; }
            foreach (var modelInfo in ReadModelList(folderPath))
            {
                var model = new GameObject(modelInfo.id);
                model.transform.SetParent(anchor.transform, false);
                var filter = model.AddComponent<MeshFilter>();
                var renderer = model.AddComponent<MeshRenderer>();
                filter.sharedMesh = ObjMeshReader.Read(Path.Combine(folderPath, modelInfo.file));
                renderer.sharedMaterial = defaultMaterial;
                model.AddComponent<TouchModelInteractor>();
            }
        }

        static IEnumerable<ModelMetadata> ReadModelList(string folderPath)
        {
            var metadataPath = Path.Combine(folderPath, "metadata.json");
            if (File.Exists(metadataPath))
            {
                var metadata = JsonUtility.FromJson<ExportMetadata>(File.ReadAllText(metadataPath));
                if (metadata != null && metadata.models != null)
                {
                    foreach (var model in metadata.models)
                    {
                        if (model != null && !string.IsNullOrEmpty(model.file) && File.Exists(Path.Combine(folderPath, model.file)))
                        {
                            if (string.IsNullOrEmpty(model.id)) model.id = Path.GetFileNameWithoutExtension(model.file);
                            yield return model;
                        }
                    }
                    yield break;
                }
            }

            foreach (var objPath in Directory.GetFiles(folderPath, "*.obj"))
            {
                var id = Path.GetFileNameWithoutExtension(objPath);
                yield return new ModelMetadata { id = id, displayName = id, file = Path.GetFileName(objPath) };
            }
        }
    }
}
