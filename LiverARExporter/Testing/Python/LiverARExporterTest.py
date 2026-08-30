import unittest

try:
    import slicer
except ImportError:
    slicer = None


@unittest.skipUnless(slicer, "This test is run from the 3D Slicer Python environment.")
class LiverARExporterTest(unittest.TestCase):
    def test_module_loads(self):
        self.assertIsNotNone(slicer.util.getModule("LiverARExporter"))

    def test_temporary_nodes_are_removed_after_segment_iv_failure(self):
        before = slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLLabelMapVolumeNode")
        temporary = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "LiverAR_TestTemporary")
        slicer.mrmlScene.RemoveNode(temporary)
        after = slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLLabelMapVolumeNode")
        self.assertEqual(before, after)
