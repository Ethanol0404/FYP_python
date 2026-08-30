# Unity Android Companion

Copy `Scripts/` into a Unity Android project that has AR Foundation and an ARCore XR Plug-in configured. Add `LiverARModelLoader` to a scene object, assign an `ARAnchorManager` and a material, then call `LoadFolder(folderPath, placementPose)` after a user chooses the folder exported by 3D Slicer.

The loader accepts the OBJ files created by `LiverARExporter`. It reads `metadata.json` when present and loads the declared files in metadata order. Each GameObject is named with the stable `id` (`Segment_I`, `Segment_IVa`, `PortalVein`, etc.), so UI code can map directly to an anatomical part; `displayName` provides the user-facing label. Older OBJ-only folders still use the filename fallback.

Read `metadata.json` before applying transforms: exports are in millimetre RAS coordinates. Coordinate conversion must be defined once in the Unity app from that metadata; do not add a second hardcoded axis flip in the OBJ reader.

`ObjMeshReader` supports geometry-only OBJ files (vertices and polygon faces), which is the output expected from this exporter. Use a dedicated Android runtime file picker or copy an export folder into the app-accessible storage location before calling `LoadFolder`.
