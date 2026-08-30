"""Geometry-aware splitting for Couinaud Segment IV."""


def _shape_3d(values):
    return len(values), len(values[0]), len(values[0][0])


def _copy_mask(mask):
    return [[[int(bool(value)) for value in row] for row in plane] for plane in mask]


def _ras_superior(matrix, i, j, k):
    return matrix[2][0] * i + matrix[2][1] * j + matrix[2][2] * k + matrix[2][3]


def split_mask_by_superior_midpoint(mask, ijk_to_ras, array_order="kji"):
    """Return Segment IVa (superior) and IVb (inferior) binary masks.

    ``mask`` is intentionally accepted as nested lists or a NumPy array. Slicer
    labelmap arrays use KJI ordering, while the geometry matrix consumes IJK.
    """
    if array_order != "kji":
        raise ValueError("Only Slicer KJI labelmap arrays are supported")

    values = mask.tolist() if hasattr(mask, "tolist") else mask
    depth, height, width = _shape_3d(values)
    populated = []
    for k in range(depth):
        for j in range(height):
            for i in range(width):
                if values[k][j][i]:
                    populated.append((i, j, k, _ras_superior(ijk_to_ras, i, j, k)))
    if not populated:
        return _copy_mask([[[0] * width for _ in range(height)] for _ in range(depth)]), _copy_mask(
            [[[0] * width for _ in range(height)] for _ in range(depth)]
        )

    midpoint = (min(point[3] for point in populated) + max(point[3] for point in populated)) / 2.0
    iva = [[[0] * width for _ in range(height)] for _ in range(depth)]
    ivb = [[[0] * width for _ in range(height)] for _ in range(depth)]
    for i, j, k, superior in populated:
        if superior >= midpoint:
            iva[k][j][i] = 1
        else:
            ivb[k][j][i] = 1
    return iva, ivb


def split_segment_iv_in_slicer(slicer_module, segmentation_node, segment_id):
    """Replace one Segment IV with Segment_IVa and Segment_IVb in Slicer.

    This round-trip uses a temporary labelmap only to obtain the source
    IJK-to-RAS matrix. The split itself remains independent of array direction.
    """
    import numpy
    import vtk

    labelmap = slicer_module.mrmlScene.AddNewNodeByClass(
        "vtkMRMLLabelMapVolumeNode", "LiverAR_SegmentIV_Temporary"
    )
    segment_ids = vtk.vtkStringArray()
    segment_ids.InsertNextValue(segment_id)
    logic = slicer_module.modules.segmentations.logic()
    try:
        if not logic.ExportSegmentsToLabelmapNode(segmentation_node, segment_ids, labelmap):
            raise RuntimeError("Could not export Segment IV to a temporary labelmap.")
        matrix = vtk.vtkMatrix4x4()
        labelmap.GetIJKToRASMatrix(matrix)
        ijk_to_ras = [[matrix.GetElement(row, col) for col in range(4)] for row in range(4)]
        source_array = slicer_module.util.arrayFromVolume(labelmap)
        iva, ivb = split_mask_by_superior_midpoint(source_array, ijk_to_ras)
        del source_array
        segmentation = segmentation_node.GetSegmentation()
        segmentation.RemoveSegment(segment_id)
        added = []
        for name, mask in (("Segment_IVa", iva), ("Segment_IVb", ivb)):
            slicer_module.util.updateVolumeFromArray(labelmap, numpy.asarray(mask, dtype=numpy.uint8))
            labelmap.SetName(name)
            before = _segment_id_set(segmentation, vtk)
            if not logic.ImportLabelmapToSegmentationNode(labelmap, segmentation_node):
                raise RuntimeError("Could not import {0} into LiverAR_Segmentation.".format(name))
            created = list(_segment_id_set(segmentation, vtk) - before)
            if not created:
                raise RuntimeError("Slicer did not create {0}.".format(name))
            segmentation.GetSegment(created[0]).SetName(name)
            added.append(created[0])
        return tuple(added)
    finally:
        if "source_array" in locals():
            del source_array
        if "iva" in locals():
            del iva
        if "ivb" in locals():
            del ivb
        slicer_module.mrmlScene.RemoveNode(labelmap)


def _segment_id_set(segmentation, vtk_module):
    ids = vtk_module.vtkStringArray()
    segmentation.GetSegmentIDs(ids)
    return {ids.GetValue(index) for index in range(ids.GetNumberOfValues())}
