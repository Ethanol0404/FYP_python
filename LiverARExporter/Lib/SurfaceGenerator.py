"""Closed-surface generation helpers for Slicer segmentation nodes."""


def create_closed_surfaces(segmentation_node):
    segmentation_node.CreateClosedSurfaceRepresentation()


def export_model_to_obj(slicer_module, model_node, output_path):
    if not slicer_module.util.saveNode(model_node, str(output_path)):
        raise RuntimeError("Could not export model to {0}".format(output_path))
