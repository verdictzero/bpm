# SPDX-License-Identifier: GPL-3.0-or-later
"""Creating, identifying and editing BPM materials."""

import bpy

from . import generators as G
from . import presets as P
from .nodebuilder import color4, set_socket_value, socket_value

MATERIAL_TAG = 'bpm_generator'
BAKED_TAG = 'bpm_baked'


# ---------------------------------------------------------------- node groups
def ensure_group(generator, tile=False):
    """Return the up-to-date node group for a generator, building it if needed."""
    for ng in bpy.data.node_groups:
        if (ng.get('bpm_generator') == generator and bool(ng.get('bpm_tile')) == bool(tile)
                and ng.get('bpm_version') == G.GENERATOR_VERSION and not ng.library):
            return ng
    return G.build_group(generator, tile)


def is_bpm_group(tree):
    return tree is not None and tree.get('bpm_generator') in G.GENERATORS


# ------------------------------------------------------------------ materials
def ensure_node_tree(mat):
    """Make sure a material has a node tree (Blender 4.x needs use_nodes)."""
    if mat.node_tree is None:
        mat.use_nodes = True
    return mat.node_tree


def find_bpm_node(mat):
    """Return the BPM generator group node of a material, or None."""
    if mat is None or mat.node_tree is None:
        return None
    best = None
    for node in mat.node_tree.nodes:
        if node.bl_idname == 'ShaderNodeGroup' and is_bpm_group(node.node_tree):
            if node.outputs and any(s.is_linked for s in node.outputs):
                return node
            best = best or node
    return best


def generator_of(mat):
    node = find_bpm_node(mat)
    return node.node_tree['bpm_generator'] if node else None


def is_baked_material(mat):
    return mat is not None and bool(mat.get(BAKED_TAG))


def output_node(tree):
    """The material output node Cycles would use."""
    out = None
    try:
        out = tree.get_output_node('CYCLES')
    except (AttributeError, TypeError):
        out = None
    if out is None:
        outs = [n for n in tree.nodes if n.bl_idname == 'ShaderNodeOutputMaterial']
        active = [n for n in outs if n.is_active_output]
        out = (active or outs or [None])[0]
    return out


def apply_values(node, values):
    """Copy a {socket name: value} dict onto a group node's inputs."""
    for name, value in values.items():
        sock = node.inputs.get(name)
        if sock is not None and not sock.is_linked:
            set_socket_value(sock, value)


def read_values(node):
    return {s.name: socket_value(s) for s in node.inputs if hasattr(s, 'default_value')}


def default_values(generator):
    return {p.name: p.default for p in G.params_for(generator)}


def preset_values(preset):
    values = default_values(preset['generator'])
    values.update(preset['values'])
    return values


def _set_viewport_display(mat, values, generator):
    """Solid-mode viewport color so the material looks right even in Solid view."""
    if generator == 'PAINT':
        mat.diffuse_color = color4(values.get('Paint Color', (0.8, 0.8, 0.8)))
        mat.metallic = 0.0
        mat.roughness = float(values.get('Paint Roughness', 0.5))
    else:
        mat.diffuse_color = color4(values.get('Metal Color', (0.6, 0.6, 0.6)))
        mat.metallic = 1.0
        mat.roughness = float(values.get('Roughness', 0.3))


def build_material(mat, generator, values, tile=False):
    """(Re)build `mat` as a BPM material for `generator` with `values`."""
    tree = ensure_node_tree(mat)
    tree.nodes.clear()
    out = tree.nodes.new('ShaderNodeOutputMaterial')
    out.location = (500, 0)
    bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (150, 0)
    group = tree.nodes.new('ShaderNodeGroup')
    group.node_tree = ensure_group(generator, tile)
    group.location = (-200, 0)
    group.width = 260
    group.label = 'BPM ' + G.GENERATORS[generator]['label']
    links = tree.links
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    for name in ('Base Color', 'Metallic', 'Roughness', 'Normal'):
        links.new(group.outputs[name], bsdf.inputs[name])
    if generator == 'METAL':
        links.new(group.outputs['Anisotropic'], bsdf.inputs['Anisotropic'])
        links.new(group.outputs['Tangent'], bsdf.inputs['Tangent'])
    else:
        links.new(group.outputs['Coat'], bsdf.inputs['Coat Weight'])
        bsdf.inputs['Coat Roughness'].default_value = 0.03
    apply_values(group, values)
    tree.nodes.active = group
    mat[MATERIAL_TAG] = generator
    _set_viewport_display(mat, values, generator)
    return group


def create_material(preset_id, name=None):
    preset = P.get(preset_id)
    mat = bpy.data.materials.new(name or preset['name'])
    build_material(mat, preset['generator'], preset_values(preset))
    mat['bpm_preset'] = preset_id
    return mat


def load_preset_into(mat, preset_id, keep_pattern=True):
    """Load a preset into an existing BPM material (rebuilds if generator differs)."""
    preset = P.get(preset_id)
    values = preset_values(preset)
    node = find_bpm_node(mat)
    if keep_pattern and node is not None:
        for key in ('Scale', 'Seed'):
            if key in node.inputs:
                values[key] = socket_value(node.inputs[key])
    if node is None or node.node_tree.get('bpm_generator') != preset['generator']:
        build_material(mat, preset['generator'], values)
    else:
        apply_values(node, values)
        _set_viewport_display(mat, values, preset['generator'])
    mat['bpm_preset'] = preset_id


def refresh_viewport_display(mat):
    node = find_bpm_node(mat)
    if node is not None:
        _set_viewport_display(mat, read_values(node), node.node_tree['bpm_generator'])


# ------------------------------------------------------------------- objects
MATERIAL_TYPES = {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT', 'CURVES', 'POINTCLOUD', 'VOLUME'}


def can_have_material(obj):
    return obj is not None and obj.type in MATERIAL_TYPES and obj.data is not None


def assign_material(obj, mat):
    """Put `mat` in the active material slot (adding a slot if needed)."""
    if not obj.material_slots:
        obj.data.materials.append(mat)
        return
    index = max(0, min(obj.active_material_index, len(obj.material_slots) - 1))
    obj.material_slots[index].material = mat


def fit_scale(objects):
    """Pattern scale so that features look natural for the object size."""
    sizes = [max(o.dimensions) for o in objects if o is not None and max(o.dimensions) > 1e-6]
    if not sizes:
        return 1.0
    size = sum(sizes) / len(sizes)
    return float(min(max((2.0 / size) ** 0.75, 0.02), 50.0))


def active_bpm_material(context):
    """(object, material, bpm node) for the active object, or Nones."""
    obj = context.active_object
    if not can_have_material(obj):
        return obj, None, None
    mat = obj.active_material
    return obj, mat, find_bpm_node(mat)
