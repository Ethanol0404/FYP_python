"""Conservative vessel cleanup with a centrally configurable island threshold."""


class VesselPostProcessor:
    def __init__(self, minimum_island_size_mm3=20.0):
        self.minimum_island_size_mm3 = minimum_island_size_mm3

    def cleanup(self, segmentation_node, segment_id, slicer_module):
        """Remove only very small disconnected islands when Segment Editor supports it."""
        editor = slicer_module.vtkMRMLSegmentEditorNode()
        slicer_module.mrmlScene.AddNode(editor)
        editor.SetSegmentationNode(segmentation_node)
        widget = slicer_module.qMRMLSegmentEditorWidget()
        widget.setMRMLScene(slicer_module.mrmlScene)
        widget.setMRMLSegmentEditorNode(editor)
        editor.SetSelectedSegmentID(segment_id)
        try:
            widget.setActiveEffectByName("Islands")
            effect = widget.activeEffect()
            effect.setParameter("Operation", "REMOVE_SMALL_ISLANDS")
            effect.setParameter("MinimumSize", str(self.minimum_island_size_mm3))
            effect.self().onApply()
        finally:
            widget.setActiveEffectByName(None)
            slicer_module.mrmlScene.RemoveNode(editor)
