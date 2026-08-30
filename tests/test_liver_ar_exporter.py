import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "LiverARExporter"))

from Lib.ModelExporter import canonical_segment_name, expected_export_names, write_metadata
from Lib.SegmentIVSplitter import split_mask_by_superior_midpoint
from Lib.TotalSegmentatorRunner import DependencyReport, TotalSegmentatorRunner
from LiverARExporter import create_output_folder_selector, pipeline_inputs


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

            self.assertEqual(payload["coordinateSystem"]["source"], "RAS")
            self.assertEqual(payload["coordinateSystem"]["unityConversion"], "metadata-defined")
            self.assertEqual(payload["models"][0]["file"], "Segment_I.obj")
            self.assertEqual(payload["models"][0]["id"], "Segment_I")
            self.assertEqual(payload["models"][0]["displayName"], "Segment I")


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


if __name__ == "__main__":
    unittest.main()
