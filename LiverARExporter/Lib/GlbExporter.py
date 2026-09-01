"""Dependency-free OBJ-to-GLB conversion for the Liver AR export folder."""

import json
import struct
from pathlib import Path


JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942


def _parse_obj(path):
    vertices = []
    indices = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        fields = line.strip().split()
        if not fields:
            continue
        if fields[0] == "v" and len(fields) >= 4:
            vertices.append(tuple(float(value) for value in fields[1:4]))
        elif fields[0] == "f" and len(fields) >= 4:
            face = []
            for token in fields[1:]:
                index = int(token.split("/")[0])
                face.append(index - 1 if index > 0 else len(vertices) + index)
            for position in range(1, len(face) - 1):
                indices.extend((face[0], face[position], face[position + 1]))
    if not vertices or not indices:
        raise ValueError("OBJ file must contain vertices and faces: {0}".format(path))
    if any(index < 0 or index >= len(vertices) for index in indices):
        raise ValueError("OBJ face index is out of range: {0}".format(path))
    return vertices, indices


def _pad(data, alignment=4, value=b"\x00"):
    remainder = len(data) % alignment
    return data if remainder == 0 else data + value * (alignment - remainder)


def _add_mesh(mesh_name, vertices, indices, binary, views, accessors):
    position_offset = len(binary)
    position_data = b"".join(struct.pack("<3f", *vertex) for vertex in vertices)
    binary += position_data
    binary = _pad(binary)
    views.append({"buffer": 0, "byteOffset": position_offset, "byteLength": len(position_data), "target": 34962})
    position_view = len(views) - 1
    mins = [min(vertex[index] for vertex in vertices) for index in range(3)]
    maxs = [max(vertex[index] for vertex in vertices) for index in range(3)]
    accessors.append({"bufferView": position_view, "componentType": 5126, "count": len(vertices), "type": "VEC3", "min": mins, "max": maxs})
    position_accessor = len(accessors) - 1

    index_offset = len(binary)
    index_data = b"".join(struct.pack("<I", index) for index in indices)
    binary += index_data
    binary = _pad(binary)
    views.append({"buffer": 0, "byteOffset": index_offset, "byteLength": len(index_data), "target": 34963})
    index_view = len(views) - 1
    accessors.append({"bufferView": index_view, "componentType": 5125, "count": len(indices), "type": "SCALAR", "min": [min(indices)], "max": [max(indices)]})
    index_accessor = len(accessors) - 1

    return binary, {"name": mesh_name, "primitives": [{"attributes": {"POSITION": position_accessor}, "indices": index_accessor, "mode": 4}]}


def convert_obj_folder_to_glb(export_folder, output_path=None, metadata_path=None):
    """Convert metadata-declared OBJ files into one GLB with separate nodes."""
    folder = Path(export_folder)
    metadata_file = Path(metadata_path) if metadata_path else folder / "metadata.json"
    if metadata_file.exists():
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        models = metadata.get("models", [])
    else:
        models = [{"name": path.stem, "file": path.name} for path in sorted(folder.glob("*.obj"))]
    if not models:
        raise ValueError("No OBJ models found in {0}".format(folder))

    binary = b""
    views = []
    accessors = []
    meshes = []
    nodes = [{"name": "PatientModelRoot", "children": []}]
    for model in models:
        name = model.get("id") or model.get("name") or Path(model["file"]).stem
        obj_path = folder / model["file"]
        vertices, indices = _parse_obj(obj_path)
        binary, mesh = _add_mesh(name, vertices, indices, binary, views, accessors)
        meshes.append(mesh)
        nodes[0]["children"].append(len(nodes))
        nodes.append({"name": name, "mesh": len(meshes) - 1})

    document = {
        "asset": {"version": "2.0", "generator": "LiverARExporter"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": nodes,
        "meshes": meshes,
        "bufferViews": views,
        "accessors": accessors,
        "buffers": [{"byteLength": len(binary)}],
    }
    json_data = _pad(json.dumps(document, separators=(",", ":"), ensure_ascii=False).encode("utf-8"), value=b" ")
    binary = _pad(binary)
    total_length = 12 + 8 + len(json_data) + 8 + len(binary)
    glb = struct.pack("<4sII", b"glTF", 2, total_length)
    glb += struct.pack("<II", len(json_data), JSON_CHUNK) + json_data
    glb += struct.pack("<II", len(binary), BIN_CHUNK) + binary
    destination = Path(output_path) if output_path else folder / "patient.glb"
    destination.write_bytes(glb)
    return destination
