# Liver AR Exporter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a testable 3D Slicer liver-export module and Unity Android AR loader companion.

**Architecture:** A Slicer controller delegates each processing concern to a small library module. Pure Python helpers carry the geometry and export contracts, so baseline verification does not depend on a local Slicer installation; Slicer-specific calls are isolated behind guarded imports.

**Tech Stack:** Python 3 standard library, NumPy in Slicer, 3D Slicer MRML/Segment Editor APIs, C# Unity AR Foundation.

**Spec:** `docs/superpowers/specs/2026-08-28-liver-ar-exporter-design.md`

## Global Constraints

- Do not change TotalSegmentator source or assume a fixed extension method name.
- Use RAS physical coordinates for Segment IV splitting and record the Unity conversion contract in metadata.
- Keep tumor optional and avoid destructive vessel simplification by default.
- Do not hardcode patient paths.

---

### Task 1: Testable Processing Contracts

**Files:**
- Create: `tests/test_liver_ar_exporter.py`
- Create: `LiverARExporter/Lib/SegmentIVSplitter.py`
- Create: `LiverARExporter/Lib/ModelExporter.py`

**Interfaces:**
- Produces: `split_mask_by_superior_midpoint(mask, ijk_to_ras, array_order='kji') -> (iva, ivb)`.
- Produces: `expected_export_names(include_tumor) -> list[str]` and `write_metadata(output_dir, entries) -> Path`.

- [ ] Write tests for a physical-space split, tumor-optional names, and metadata output.
- [ ] Run `python -m unittest discover -s tests` and confirm missing-module failure.
- [ ] Implement the smallest pure functions needed for those tests.
- [ ] Run the same command and confirm all tests pass.

### Task 2: Slicer Pipeline Components

**Files:**
- Create: `LiverARExporter/LiverARExporter.py`
- Create: `LiverARExporter/Lib/TotalSegmentatorRunner.py`
- Create: `LiverARExporter/Lib/VesselPostProcessor.py`
- Create: `LiverARExporter/Lib/SurfaceGenerator.py`
- Create: `LiverARExporter/Testing/Python/LiverARExporterTest.py`

**Interfaces:**
- Consumes: Slicer MRML nodes and `TotalSegmentatorRunner`.
- Produces: `LiverAR_Segmentation` and named closed-surface model nodes.

- [ ] Add dependency-report tests and run them before implementation.
- [ ] Implement runtime API discovery, guarded Slicer imports, UI controls, orchestration, conservative cleanup, and closed-surface creation.
- [ ] Run the standard-library tests and Slicer-host test discovery where available.

### Task 3: Unity Android Companion

**Files:**
- Create: `UnityAndroid/Scripts/LiverARModelLoader.cs`
- Create: `UnityAndroid/Scripts/ObjMeshReader.cs`
- Create: `UnityAndroid/Scripts/TouchModelInteractor.cs`
- Create: `UnityAndroid/README.md`

**Interfaces:**
- Consumes: `metadata.json` and exported OBJ files.
- Produces: an anchored Unity scene hierarchy containing the imported meshes.

- [ ] Add a documented runtime loading contract.
- [ ] Implement guarded runtime OBJ parsing and touch controls.
- [ ] Verify Python tests and review generated C# source for AR Foundation/package assumptions.
