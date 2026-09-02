import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "LiverARExporter"))

from Lib.ModelExporter import canonical_segment_name, display_name, expected_export_names, write_metadata
from Lib.GlbExporter import convert_obj_folder_to_glb
from Lib.SegmentIVSplitter import split_mask_by_superior_midpoint
from Lib.TotalSegmentatorRunner import DependencyReport, TotalSegmentatorRunner
from Lib.MonaiLabelRunner import MonaiLabelRunner, task_output_plan
from LiverARExporter import (
    canonical_task_segment_name,
    create_output_folder_selector,
    export_segment_to_representation,
    pipeline_inputs,
)


class SegmentIVSplitterTest(unittest.TestCase):
    def test_uses_physical_superior_coordinate_not_array_index(self):
        # A reversed superior axis proves the split is based on RAS geometry.
        mask = [
            [[1]],
            [[1]],
            [[1]],
            [[1]],
        ]
        ijk_to_ras = [
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, -10, 30],
            [0, 0, 0, 1],
        ]

        iva, ivb = split_mask_by_superior_midpoint(mask, ijk_to_ras)

        self.assertEqual(iva, [[[1]], [[1]], [[0]], [[0]]])
        self.assertEqual(ivb, [[[0]], [[0]], [[1]], [[1]]])


class ModelExporterTest(unittest.TestCase):
    def test_normalizes_upstream_segment_labels_to_canonical_names(self):
        self.assertEqual(canonical_segment_name("liver segment 1"), "Segment_I")
        self.assertEqual(canonical_segment_name("Segment-IVa"), "Segment_IVa")
        self.assertEqual(canonical_segment_name("hepatic veins"), "HepaticVeins")
        self.assertEqual(canonical_segment_name("liver_vessels"), "BloodVessels")
        self.assertEqual(canonical_segment_name("blood vessels"), "BloodVessels")
        self.assertEqual(canonical_segment_name("vessels"), "BloodVessels")
        self.assertEqual(canonical_segment_name("portal_vein_main"), "PortalVein")
        self.assertEqual(canonical_segment_name("hepatic_vein_left"), "HepaticVeins")
        self.assertEqual(canonical_segment_name("hepatic_vein_right"), "HepaticVeins")
        self.assertEqual(display_name("BloodVessels"), "Blood Vessels")
        self.assertEqual(canonical_segment_name("liver_lesions"), "Tumor")
        self.assertIsNone(canonical_segment_name("unrelated structure"))

    def test_missing_tumor_does_not_remove_required_exports(self):
        names = expected_export_names(include_tumor=False)

        self.assertEqual(names[:3], ["Segment_I", "Segment_II", "Segment_III"])
        self.assertIn("Segment_IVa", names)
        self.assertIn("Segment_IVb", names)
        self.assertIn("PortalVein", names)
        self.assertIn("HepaticVeins", names)
        self.assertNotIn("Tumor", names)

    def test_expected_obj_filenames_are_stable(self):
        names = expected_export_names(include_tumor=True)

        self.assertEqual([name + ".obj" for name in names[-3:]], ["PortalVein.obj", "HepaticVeins.obj", "Tumor.obj"])

    def test_writes_metadata_that_declares_ras_and_unity_contract(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_metadata(
                folder,
                [{"name": "Segment_I", "file": "Segment_I.obj", "role": "liver_segment"}],
            )

            payload = json.loads(path.read_text(encoding="utf-8"))

            self.assertEqual(payload["coordinateSystem"]["source"], "LPS")
            self.assertEqual(payload["coordinateSystem"]["unityConversion"], "metadata-defined")
            self.assertEqual(payload["models"][0]["file"], "Segment_I.obj")
            self.assertEqual(payload["models"][0]["id"], "Segment_I")
            self.assertEqual(payload["models"][0]["displayName"], "Segment I")

    def test_metadata_declares_glb_output(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_metadata(folder, [])
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(payload["glbFile"], "patient.glb")
        self.assertEqual(payload["glbRootNode"], "PatientModelRoot")


class GlbExporterTest(unittest.TestCase):
    def test_converts_obj_files_to_separate_named_glb_nodes(self):
        with tempfile.TemporaryDirectory() as folder:
            folder_path = Path(folder)
            (folder_path / "Segment_I.obj").write_text(
                "# SPACE=LPS\nv 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n",
                encoding="utf-8",
            )
            (folder_path / "Tumor.obj").write_text(
                "v 0 0 1\nv 1 0 1\nv 0 1 1\nf 1 2 3\n",
                encoding="utf-8",
            )
            write_metadata(folder, [
                {"name": "Segment_I", "file": "Segment_I.obj", "role": "anatomy"},
                {"name": "Tumor", "file": "Tumor.obj", "role": "anatomy"},
            ])

            glb_path = convert_obj_folder_to_glb(folder)
            data = glb_path.read_bytes()
            _, version, total_length = struct.unpack_from("<4sII", data, 0)
            json_length, json_type = struct.unpack_from("<II", data, 12)
            document = json.loads(data[20:20 + json_length].decode("utf-8"))

        self.assertEqual(version, 2)
        self.assertEqual(total_length, len(data))
        self.assertEqual(json_type, 0x4E4F534A)
        self.assertEqual(
            [node["name"] for node in document["nodes"]],
            ["PatientModelRoot", "Segment_I", "Tumor"],
        )


class DependencyValidationTest(unittest.TestCase):
    def test_reports_missing_slicer_without_crashing(self):
        report = TotalSegmentatorRunner.validate_dependencies(None)

        self.assertFalse(report.available)
        self.assertIn("3D Slicer", report.message)

    def test_calls_installed_process_api_with_named_task(self):
        class ProcessLogic:
            def process(self, input_volume, output_segmentation, quality=None, cpu=False, task=None, **_):
                self.values = (input_volume, output_segmentation, quality, cpu, task)
                return "segmentation"

        logic = ProcessLogic()
        runner = object.__new__(TotalSegmentatorRunner)
        runner.report = DependencyReport(True, "available", logic=logic)

        result = runner.run_task("CT", "tumor", "LiverAR_Segmentation")

        self.assertEqual(result, "segmentation")
        self.assertEqual(logic.values, ("CT", "LiverAR_Segmentation", None, False, "liver_lesions"))

    def test_low_resource_mode_limits_threads_and_uses_fast_inference(self):
        class ProcessLogic:
            def process(self, input_volume, output_segmentation, quality=None, cpu=False,
                        task=None, fast=False, nr_threads=None, **_):
                self.values = (cpu, task, fast, nr_threads)
                return "segmentation"

        logic = ProcessLogic()
        runner = object.__new__(TotalSegmentatorRunner)
        runner.report = DependencyReport(True, "available", logic=logic)

        runner.run_task("CT", "couinaud", "LiverAR_Segmentation")

        self.assertEqual(logic.values, (False, "liver_segments", True, 1))


class SegmentationTargetTest(unittest.TestCase):
    def test_tasks_have_independent_output_targets_and_export_labels(self):
        self.assertEqual(task_output_plan("couinaud"), ("LiverAR_Couinaud", ("Segment_I", "Segment_II", "Segment_III", "Segment_IV", "Segment_V", "Segment_VI", "Segment_VII", "Segment_VIII")))
        self.assertEqual(task_output_plan("vessels"), ("LiverAR_Vessels", ("PortalVein", "HepaticVeins", "BloodVessels")))
        self.assertEqual(task_output_plan("tumor"), ("LiverAR_Tumor", ("Tumor",)))

    def test_vessel_task_is_optional_when_a_specific_vessel_is_unavailable(self):
        from LiverARExporter import LiverARExporterLogic

        self.assertIn("vessels", LiverARExporterLogic.OPTIONAL_TASKS)
        self.assertIn("blood vessels", LiverARExporterLogic.SEGMENT_ALIASES["BloodVessels"])

    def test_unknown_vessel_task_label_is_preserved_as_blood_vessels(self):
        self.assertEqual(canonical_task_segment_name("vessels", "unknown_vessel_label"), "BloodVessels")


class MonaiLabelRunnerTest(unittest.TestCase):
    def test_reports_missing_monai_client_without_crashing(self):
        runner = MonaiLabelRunner("http://127.0.0.1:8000", client_factory=None)

        self.assertFalse(runner.available)
        self.assertIn("MONAI Label", runner.message)


class FolderSelectorTest(unittest.TestCase):
    def test_creates_ctk_directory_selector(self):
        class FakePathLineEdit:
            Dirs = 7

            def __init__(self):
                self.filters = None

        class FakeCtk:
            ctkPathLineEdit = FakePathLineEdit

        selector = create_output_folder_selector(FakeCtk)

        self.assertIsInstance(selector, FakePathLineEdit)
        self.assertEqual(selector.filters, FakePathLineEdit.Dirs)


class InputValidationTest(unittest.TestCase):
    def test_segmentation_requires_ct_but_not_export_folder(self):
        volume, folder = pipeline_inputs("CT", "", require_output_folder=False)

        self.assertEqual(volume, "CT")
        self.assertIsNone(folder)

    def test_export_requires_export_folder(self):
        with self.assertRaisesRegex(ValueError, "export folder"):
            pipeline_inputs("CT", "", require_output_folder=True)


class SlicerApiCompatibilityTest(unittest.TestCase):
    def test_exports_a_segment_object_with_slicers_two_argument_api(self):
        class FakeLogic:
            def ExportSegmentToRepresentationNode(self, segment, model):
                self.values = (segment, model)
                return True

        logic = FakeLogic()
        self.assertTrue(export_segment_to_representation(logic, "segment", "model"))
        self.assertEqual(logic.values, ("segment", "model"))


if __name__ == "__main__":
    unittest.main()
