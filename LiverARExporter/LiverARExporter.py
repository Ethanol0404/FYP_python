"""3D Slicer module: CT -> TotalSegmentator -> liver AR export."""

import logging
from pathlib import Path

try:
    import slicer
    import qt
    import ctk
    from slicer.ScriptedLoadableModule import (
        ScriptedLoadableModule,
        ScriptedLoadableModuleLogic,
        ScriptedLoadableModuleWidget,
    )
except ImportError:  # Allows pure-Python tests to import package helpers.
    slicer = None

from Lib.ModelExporter import canonical_segment_name, expected_export_names, write_metadata
from Lib.GlbExporter import convert_obj_folder_to_glb
from Lib.MonaiLabelRunner import task_output_plan
from Lib.SegmentIVSplitter import split_segment_iv_in_slicer
from Lib.TotalSegmentatorRunner import TotalSegmentatorRunner
from Lib.VesselPostProcessor import VesselPostProcessor
from Lib.SurfaceGenerator import create_closed_surfaces, export_model_to_obj


LOGGER = logging.getLogger(__name__)


def create_output_folder_selector(ctk_module):
    selector = ctk_module.ctkPathLineEdit()
    selector.filters = ctk_module.ctkPathLineEdit.Dirs
    return selector


def pipeline_inputs(volume, folder, require_output_folder):
    if not volume:
        raise ValueError("Select a CT volume.")
    if require_output_folder and not folder:
        raise ValueError("Select an export folder.")
    return volume, folder or None


def export_segment_to_representation(segmentation_logic, segment, representation_node):
    """Export one vtkSegment using Slicer's two-argument API."""
    return segmentation_logic.ExportSegmentToRepresentationNode(segment, representation_node)


class LiverARExporter(ScriptedLoadableModule if slicer else object):
    def __init__(self, parent=None):
        if not slicer:
            return
        super().__init__(parent)
        self.parent.title = "Liver AR Exporter"
        self.parent.categories = ["Segmentation"]
        self.parent.contributors = ["FYP Project"]
        self.parent.helpText = "Exports TotalSegmentator liver anatomy as OBJ models for Unity AR."


class LiverARExporterWidget(ScriptedLoadableModuleWidget if slicer else object):
    def setup(self):
        super().setup()
        self.logic = LiverARExporterLogic()
        form = qt.QFormLayout()
        self.layout.addLayout(form)
        self.input_selector = slicer.qMRMLNodeComboBox()
        self.input_selector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.input_selector.setMRMLScene(slicer.mrmlScene)
        form.addRow("CT volume:", self.input_selector)
        self.output_selector = create_output_folder_selector(ctk)
        form.addRow("Export folder:", self.output_selector)
        self.status = qt.QLabel("Select a CT volume and export folder.")
        self.layout.addWidget(self.status)
        for label, callback in (
            ("Run Segmentation", self.run_segmentation),
            ("Process Models", self.process_models),
            ("Export Models", self.export_models),
            ("Run Full Pipeline", self.run_full_pipeline),
        ):
            button = qt.QPushButton(label)
            button.connect("clicked()", callback)
            self.layout.addWidget(button)
        self.layout.addStretch(1)

    def _inputs(self, require_output_folder):
        volume = self.input_selector.currentNode()
        folder = self.output_selector.currentPath
        return pipeline_inputs(volume, folder, require_output_folder)

    def _run(self, action):
        try:
            action()
            self.status.text = "Completed. Review the Data and Models views before clinical use."
        except Exception as error:
            LOGGER.exception("Liver AR Exporter failed")
            self.status.text = "Error: {0}".format(error)

    def run_segmentation(self):
        self._run(lambda: self.logic.run_segmentation(self._inputs(False)[0]))

    def process_models(self):
        self._run(lambda: self.logic.process_models())

    def export_models(self):
        self._run(lambda: self.logic.export_models(self._inputs(True)[1]))

    def run_full_pipeline(self):
        self._run(lambda: self.logic.run_full_pipeline(*self._inputs(True)))


class LiverARExporterLogic(ScriptedLoadableModuleLogic if slicer else object):
    OPTIONAL_TASKS = {"tumor", "vessels"}
    SEGMENT_ALIASES = {
        "PortalVein": ("portal_vein", "portal vein"),
        "HepaticVeins": ("hepatic_vein", "hepatic veins"),
        "LiverVessels": ("liver_vessels", "liver vessels", "blood_vessels", "blood vessels", "vessels", "vascular"),
        "Tumor": ("liver_tumor", "liver tumor", "tumor"),
    }

    def __init__(self):
        if slicer:
            super().__init__()
            self.runner = TotalSegmentatorRunner(slicer)
        self.segmentation_node = None
        self.task_nodes = {}

    def _ensure_slicer(self):
        if not slicer:
            raise RuntimeError("Run LiverARExporter inside 3D Slicer.")
        if not self.runner.report.available:
            raise RuntimeError(self.runner.report.message)

    def run_segmentation(self, input_volume):
        self._ensure_slicer()
        self.segmentation_node = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLSegmentationNode", "LiverAR_Segmentation"
        )
        self.task_nodes = {}
        for task in ("couinaud", "vessels", "tumor"):
            node_name, _ = task_output_plan(task)
            task_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", node_name)
            self.task_nodes[task] = task_node
            try:
                self.runner.run_task(input_volume, task, task_node)
            except RuntimeError:
                if task in self.OPTIONAL_TASKS:
                    LOGGER.warning("%s task unavailable; export will continue with available outputs.", task)
                    slicer.mrmlScene.RemoveNode(task_node)
                    self.task_nodes.pop(task, None)
                    continue
                slicer.mrmlScene.RemoveNode(task_node)
                self.task_nodes.pop(task, None)
                raise
            self._normalize_segment_names(task_node)
        self._merge_task_nodes()
        return self.segmentation_node

    def _normalize_segment_names(self, segmentation_node):
        segmentation = segmentation_node.GetSegmentation()
        used_names = set()
        for index in range(segmentation.GetNumberOfSegments()):
            segment_id = segmentation.GetNthSegmentID(index)
            segment = segmentation.GetSegment(segment_id)
            canonical = canonical_segment_name(segment.GetName())
            if canonical and canonical not in used_names:
                segment.SetName(canonical)
                used_names.add(canonical)

    def _merge_task_nodes(self):
        target = self.segmentation_node.GetSegmentation()
        for task, source_node in self.task_nodes.items():
            _, allowed_names = task_output_plan(task)
            source = source_node.GetSegmentation()
            for index in range(source.GetNumberOfSegments()):
                source_id = source.GetNthSegmentID(index)
                source_segment = source.GetSegment(source_id)
                if source_segment.GetName() not in allowed_names:
                    continue
                if target.GetSegmentIdBySegmentName(source_segment.GetName()):
                    continue
                target.CopySegmentFromSegmentation(source, source_id)
            slicer.mrmlScene.RemoveNode(source_node)
        self.task_nodes = {}

    def process_models(self):
        self._ensure_slicer()
        if not self.segmentation_node:
            raise RuntimeError("Run segmentation before processing models.")
        segmentation = self.segmentation_node.GetSegmentation()
        segment_iv_id = self._find_segment_id(("Segment_IV", "segment_iv", "liver_segment_4", "liver segment 4"))
        if segment_iv_id:
            split_segment_iv_in_slicer(slicer, self.segmentation_node, segment_iv_id)
            segmentation = self.segmentation_node.GetSegmentation()
        for index in range(segmentation.GetNumberOfSegments()):
            segment_id = segmentation.GetNthSegmentID(index)
            segment_name = segmentation.GetSegment(segment_id).GetName()
            if "vein" in segment_name.lower():
                VesselPostProcessor().cleanup(self.segmentation_node, segment_id, slicer)
        create_closed_surfaces(self.segmentation_node)

    def _find_segment_id(self, aliases):
        segmentation = self.segmentation_node.GetSegmentation()
        for index in range(segmentation.GetNumberOfSegments()):
            segment_id = segmentation.GetNthSegmentID(index)
            name = segmentation.GetSegment(segment_id).GetName().lower()
            if name in {alias.lower() for alias in aliases}:
                return segment_id
        return None

    def export_models(self, output_directory):
        self._ensure_slicer()
        if not self.segmentation_node:
            raise RuntimeError("Run segmentation before exporting models.")
        folder = Path(output_directory)
        folder.mkdir(parents=True, exist_ok=True)
        segmentation = self.segmentation_node.GetSegmentation()
        entries = []
        export_names = expected_export_names(include_tumor=True) + ["LiverVessels"]
        for name in export_names:
            segment_id = self._find_segment_id((name,) + self.SEGMENT_ALIASES.get(name, ()))
            if not segment_id:
                if name in ("Tumor", "LiverVessels"):
                    continue
                LOGGER.warning("Expected segment %s was not present and was not exported.", name)
                continue
            model = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", name)
            try:
                export_segment_to_representation(
                    slicer.modules.segmentations.logic(),
                    segmentation.GetSegment(segment_id),
                    model,
                )
                path = folder / (name + ".obj")
                export_model_to_obj(slicer, model, path)
                role = "vessels" if name in ("PortalVein", "HepaticVeins", "LiverVessels") else "anatomy"
                entries.append({"name": name, "file": path.name, "role": role})
            finally:
                slicer.mrmlScene.RemoveNode(model)
        metadata_path = write_metadata(folder, entries)
        convert_obj_folder_to_glb(folder, metadata_path=metadata_path)
        return metadata_path

    def run_full_pipeline(self, input_volume, output_directory):
        self.run_segmentation(input_volume)
        self.process_models()
        return self.export_models(output_directory)
