"""Stable OBJ naming and metadata output for downstream AR clients."""

import json
from pathlib import Path


REQUIRED_EXPORTS = [
    "Segment_I",
    "Segment_II",
    "Segment_III",
    "Segment_IVa",
    "Segment_IVb",
    "Segment_V",
    "Segment_VI",
    "Segment_VII",
    "Segment_VIII",
    "PortalVein",
    "HepaticVeins",
]


_CANONICAL_NAMES = {
    "segment1": "Segment_I",
    "liversegment1": "Segment_I",
    "segmenti": "Segment_I",
    "segment2": "Segment_II",
    "liversegment2": "Segment_II",
    "segmentii": "Segment_II",
    "segment3": "Segment_III",
    "liversegment3": "Segment_III",
    "segmentiii": "Segment_III",
    "segment4": "Segment_IV",
    "liversegment4": "Segment_IV",
    "segmentiv": "Segment_IV",
    "segment4a": "Segment_IVa",
    "segmentiva": "Segment_IVa",
    "segment4b": "Segment_IVb",
    "segmentivb": "Segment_IVb",
    "segment5": "Segment_V",
    "liversegment5": "Segment_V",
    "segmentv": "Segment_V",
    "segment6": "Segment_VI",
    "liversegment6": "Segment_VI",
    "segmentvi": "Segment_VI",
    "segment7": "Segment_VII",
    "liversegment7": "Segment_VII",
    "segmentvii": "Segment_VII",
    "segment8": "Segment_VIII",
    "liversegment8": "Segment_VIII",
    "segmentviii": "Segment_VIII",
    "portalvein": "PortalVein",
    "hepaticvein": "HepaticVeins",
    "hepaticveins": "HepaticVeins",
    "livervessels": "BloodVessels",
    "bloodvessels": "BloodVessels",
    "vessels": "BloodVessels",
    "vascular": "BloodVessels",
    "livertumor": "Tumor",
    "liverlesion": "Tumor",
    "liverlesions": "Tumor",
    "tumor": "Tumor",
}


def canonical_segment_name(name):
    """Return the stable export/UI name for a known upstream label."""
    key = "".join(character.lower() for character in name if character.isalnum())
    canonical = _CANONICAL_NAMES.get(key)
    if canonical:
        return canonical
    if key.startswith("portalvein"):
        return "PortalVein"
    if key.startswith("hepaticvein"):
        return "HepaticVeins"
    if key.startswith(("livervessels", "bloodvessels", "vessels", "vascular")):
        return "BloodVessels"
    return None


def display_name(name):
    return {
        "PortalVein": "Portal Vein",
        "HepaticVeins": "Hepatic Veins",
        "BloodVessels": "Blood Vessels",
        "Tumor": "Tumor",
    }.get(name, name.replace("_", " "))


def expected_export_names(include_tumor=False):
    names = list(REQUIRED_EXPORTS)
    if include_tumor:
        names.append("Tumor")
    return names


def metadata_payload(entries):
    models = []
    for entry in entries:
        model = dict(entry)
        model.setdefault("id", model["name"])
        model.setdefault("displayName", display_name(model["name"]))
        models.append(model)
    return {
        "formatVersion": 1,
        "units": "mm",
        "coordinateSystem": {
            "source": "LPS",
            "unityConversion": "metadata-defined",
            "note": "OBJ and GLB coordinates use LPS. Unity importer must apply one documented LPS-to-Unity transform; do not add arbitrary axis flips.",
        },
        "glbFile": "patient.glb",
        "glbRootNode": "PatientModelRoot",
        "models": models,
    }


def write_metadata(output_directory, entries):
    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)
    path = output_path / "metadata.json"
    path.write_text(json.dumps(metadata_payload(entries), indent=2), encoding="utf-8")
    return path
