# Liver AR Exporter Design

## Purpose

Provide a 3D Slicer scripted module that turns a CT volume into a small, well-named liver anatomy model set for an Android AR application. The module coordinates an installed TotalSegmentator extension, derives Segment IVa and IVb from Segment IV in patient physical space, conservatively prepares vessel and lesion surfaces, and exports OBJ files with machine-readable metadata.

## Boundaries

The module does not modify or retrain TotalSegmentator, implement a new medical segmentation algorithm, load AR content in Slicer, or make unverified coordinate flips. It validates dependencies at runtime and gives actionable messages when an extension, task, input volume, or expected segment is unavailable.

## Architecture

`LiverARExporter.py` owns the Slicer UI and pipeline orchestration. Focused library modules own TotalSegmentator API inspection, Segment IV splitting, light vessel cleanup, model creation, and export metadata. Pure Python functions isolate geometry and export-name behavior for tests that run without Slicer.

## Data Flow

1. User selects CT and an output folder.
2. The runner validates the installed TotalSegmentator API, discovers callable entry points, and invokes configured Couinaud, vessel, and lesion tasks only through discovered methods.
3. The orchestrator collects results in a `LiverAR_Segmentation` node. Segment IV is exported to a temporary labelmap, split around its physical RAS superior/inferior midpoint, and re-imported as `Segment_IVa` and `Segment_IVb`.
4. Vessel cleanup only removes islands smaller than a configurable threshold; default surface processing preserves branches.
5. Closed surfaces are generated and exported as `Segment_I` through `Segment_VIII`, `PortalVein`, `HepaticVeins`, and optional `Tumor`. `metadata.json` records RAS units, source model files, and the Unity coordinate-conversion contract.

## Unity Companion

The Unity folder contains scripts for choosing an export folder/file set at runtime, parsing untextured OBJ geometry, grouping loaded models under an AR anchor, and touch rotation/scale. It assumes the Unity project provides AR Foundation and an Android-compatible runtime file picker. The included documentation identifies these project-side dependencies and tells Unity consumers to use the metadata transform rather than inventing a second coordinate conversion.

## Error Handling

The pipeline stops before segmentation if required Slicer/TotalSegmentator APIs are unavailable. It logs warnings for absent tumor results and continues exporting the available anatomy. Segment names are normalized through aliases so variations in upstream labels do not silently produce confusing output.

## Validation

Standard-library tests cover physical Segment IV splitting, metadata and expected OBJ naming, missing tumor export behavior, and dependency reports. A Slicer test harness is included for module loading and cleanup but can only be run from 3D Slicer. Unity scripts are supplied as source and must be compiled in a Unity Android project with its required packages.
