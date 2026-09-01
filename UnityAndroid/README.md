# Unity Android Companion

Copy `Scripts/` into a Unity Android project that has AR Foundation and an ARCore XR Plug-in configured. Add `LiverARModelLoader` to a scene object, assign an `ARAnchorManager` and a material, then call `LoadFolder(folderPath, placementPose)` after a user chooses the folder exported by 3D Slicer.

The exporter creates both the original OBJ files and a dependency-free `patient.glb`. The GLB keeps each declared model as a separate node below `PatientModelRoot`, with stable names such as `Segment_I`, `Segment_IVa`, and `PortalVein`. This allows Unity UI code to map directly to an anatomical part without joining meshes.

The current sample loader accepts OBJ files. For runtime GLB loading, install Unity's official glTFast package and instantiate `patient.glb` under your existing patient-model workspace. Older OBJ-only folders remain supported by the sample loader.

Read `metadata.json` before applying transforms: exports are in millimetre LPS coordinates. The Python GLB conversion preserves those coordinates. Coordinate conversion must be defined once in the Unity app from that metadata; do not add a second hardcoded axis flip in the OBJ reader.

`ObjMeshReader` supports geometry-only OBJ files (vertices and polygon faces). The Python GLB writer supports vertices and polygon faces without Blender, trimesh, pygltflib, or NumPy. Use a dedicated Android runtime file picker or copy an export folder into the app-accessible storage location before loading it.

## MONAI Label / MONAI Bundle direction

The Slicer exporter keeps inference outputs separate by task, so a MONAI Label result can be imported into a dedicated target node without replacing liver segments or vessels. The included `LiverARExporter/Lib/MonaiLabelRunner.py` uses the documented `MONAILabelClient.infer` API and expects model names supplied by a MONAI Label server. A MONAI Bundle containing a liver-tumor model must be installed/configured on that server; model selection and clinical validation are intentionally not embedded in the Unity client.
