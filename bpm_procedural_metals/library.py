# SPDX-License-Identifier: GPL-3.0-or-later
"""Creating, identifying and editing BPM materials."""

import bpy

from . import generators as G
from . import overlays as O
from . import presets as P
from .nodebuilder import color4, is_socket, set_socket_value, socket_value

MATERIAL_TAG = 'bpm_generator'
BAKED_TAG = 'bpm_baked'
PRESET_OVERLAY_TAG = 'bpm_preset_overlay'

# overlay channel -> Principled BSDF input it feeds
OVERLAY_LINKS = (
    ('Base Color', 'Base Color'),
    ('Metallic', 'Metallic'),
    ('Roughness', 'Roughness'),
    ('Normal', 'Normal'),
    ('Coat', 'Coat Weight'),
)
OVERLAY_STEP = 280.0  # horizontal room made for every overlay node


# ---------------------------------------------------------------- node groups
def ensure_group(generator, tile=False):
    """Return the up-to-date node group for a generator, building it if needed."""
    version = G.GENERATORS[generator]['version']
    for ng in bpy.data.node_groups:
        if (ng.get('bpm_generator') == generator and bool(ng.get('bpm_tile')) == bool(tile)
                and ng.get('bpm_version') == version and not ng.library):
            return ng
    return G.build_group(generator, tile)


def is_bpm_group(tree):
    return tree is not None and tree.get('bpm_generator') in G.GENERATORS


def is_material_group(tree):
    return is_bpm_group(tree) and not G.is_overlay(tree['bpm_generator'])


def is_overlay_group(tree):
    return is_bpm_group(tree) and G.is_overlay(tree['bpm_generator'])


def is_overlay_node(node):
    return node is not None and node.bl_idname == 'ShaderNodeGroup' and is_overlay_group(node.node_tree)


# ------------------------------------------------------------------ materials
def ensure_node_tree(mat):
    """Make sure a material has a node tree (Blender 4.x needs use_nodes)."""
    if mat.node_tree is None:
        mat.use_nodes = True
    return mat.node_tree


def find_bpm_node(mat):
    """Return the BPM material generator group node of a material, or None."""
    if mat is None or mat.node_tree is None:
        return None
    best = None
    for node in mat.node_tree.nodes:
        if node.bl_idname == 'ShaderNodeGroup' and is_material_group(node.node_tree):
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


def _surface_link(out):
    links = [l for l in out.inputs['Surface'].links if not getattr(l, 'is_muted', False)]
    return links[0] if links else None


def find_principled(tree, out=None):
    """The Principled BSDF that feeds the material output (searching upstream)."""
    if out is None:
        out = output_node(tree)
    if out is None:
        return None
    link = _surface_link(out)
    if link is None:
        return None
    stack, seen = [link.from_node], set()
    while stack:
        node = stack.pop(0)
        if node in seen:
            continue
        seen.add(node)
        if node.bl_idname == 'ShaderNodeBsdfPrincipled':
            return node
        for inp in node.inputs:
            if inp.type == 'SHADER':
                for l in inp.links:
                    stack.append(l.from_node)
    for node in tree.nodes:
        if node.bl_idname == 'ShaderNodeBsdfPrincipled':
            return node
    return None


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
    spec = G.GENERATORS.get(generator)
    if spec is None or 'display' not in spec:
        return
    color_name, metallic, rough_name = spec['display']
    mat.diffuse_color = color4(values.get(color_name, (0.8, 0.8, 0.8)))
    mat.metallic = float(values.get(metallic, 0.0)) if isinstance(metallic, str) else float(metallic)
    mat.roughness = float(values.get(rough_name, 0.5))


def build_material(mat, generator, values, tile=False):
    """(Re)build `mat` as a BPM material for `generator` with `values` (overlays are kept)."""
    tree = ensure_node_tree(mat)
    kept = overlay_states(mat)
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
    spec = G.GENERATORS[generator]
    for name in ('Base Color', 'Metallic', 'Roughness', 'Normal'):
        links.new(group.outputs[name], bsdf.inputs[name])
    for out_name, bsdf_name in spec['links'].items():
        if bsdf_name in bsdf.inputs:
            links.new(group.outputs[out_name], bsdf.inputs[bsdf_name])
    for bsdf_name, value in spec['bsdf'].items():
        if bsdf_name in bsdf.inputs:
            set_socket_value(bsdf.inputs[bsdf_name], value)
    apply_values(group, values)
    mat[MATERIAL_TAG] = generator
    _set_viewport_display(mat, values, generator)
    for state in kept:
        add_overlay_state(mat, state, tile)
    tree.nodes.active = group
    return group


def create_material(preset_id, name=None):
    preset = P.get(preset_id)
    if G.is_overlay(preset['generator']):
        raise ValueError('%s is an overlay, not a material' % preset_id)
    mat = bpy.data.materials.new(name or preset['name'])
    build_material(mat, preset['generator'], preset_values(preset))
    _add_preset_overlays(mat, preset)
    mat['bpm_preset'] = preset_id
    return mat


def _add_preset_overlays(mat, preset):
    for generator, values in preset.get('overlays', ()):
        node = add_overlay(mat, generator, values)
        node[PRESET_OVERLAY_TAG] = True


def load_preset_into(mat, preset_id, keep_pattern=True):
    """Load a preset into an existing BPM material (rebuilds if generator differs).

    Overlays the user added stay; overlays that came with the previous preset
    are replaced by the ones of the new preset.
    """
    preset = P.get(preset_id)
    values = preset_values(preset)
    node = find_bpm_node(mat)
    if keep_pattern and node is not None:
        for key in ('Scale', 'Seed'):
            if key in node.inputs:
                values[key] = socket_value(node.inputs[key])
    for overlay in overlay_stack(mat):
        if overlay.get(PRESET_OVERLAY_TAG):
            remove_overlay(mat, overlay)
    if node is None or node.node_tree.get('bpm_generator') != preset['generator']:
        build_material(mat, preset['generator'], values)
    else:
        apply_values(node, values)
        _set_viewport_display(mat, values, preset['generator'])
    _add_preset_overlays(mat, preset)
    mat['bpm_preset'] = preset_id


# ------------------------------------------------------------------ overlays
class OverlayState:
    """Everything needed to re-create an overlay node."""

    def __init__(self, node):
        self.generator = node.node_tree['bpm_generator']
        self.values = {k: v for k, v in read_values(node).items() if k not in O.CHANNEL_NAMES}
        self.label = node.label
        self.from_preset = bool(node.get(PRESET_OVERLAY_TAG))
        self.hidden_opacity = node.get('bpm_opacity')


def overlay_nodes(mat):
    if mat is None or mat.node_tree is None:
        return []
    return [n for n in mat.node_tree.nodes if is_overlay_node(n)]


def _overlay_feeding(node, channels):
    """The overlay node linked into one of `channels` of `node` (or None)."""
    for name in channels:
        sock = node.inputs.get(name)
        if sock is None or not sock.is_linked:
            continue
        src = sock.links[0].from_node
        if is_overlay_node(src):
            return src
    return None


def overlay_stack(mat):
    """Overlay nodes in stacking order: first = right above the material, last = on top."""
    nodes = overlay_nodes(mat)
    if not nodes:
        return []
    chain = []
    bsdf = find_principled(mat.node_tree)
    current = _overlay_feeding(bsdf, [b for _o, b in OVERLAY_LINKS]) if bsdf is not None else None
    while current is not None and current not in chain:
        chain.append(current)
        current = _overlay_feeding(current, O.CHANNEL_NAMES)
    chain.reverse()
    return [n for n in nodes if n not in chain] + chain


def overlay_states(mat):
    return [OverlayState(n) for n in overlay_stack(mat)]


def height_source(mat, out=None):
    """Socket (or constant) holding the height of the whole material, overlays included."""
    stack = overlay_stack(mat)
    if stack:
        return stack[-1].outputs['Height']
    node = find_bpm_node(mat)
    if node is not None:
        return node.outputs['Height']
    tree = mat.node_tree if mat is not None else None
    if tree is None:
        return None
    out = out or output_node(tree)
    disp = out.inputs.get('Displacement') if out is not None else None
    if disp is not None and disp.is_linked:
        link = disp.links[0]
        node = link.from_node
        if node.bl_idname == 'ShaderNodeDisplacement':
            h = node.inputs['Height']
            return h.links[0].from_socket if h.is_linked else h.default_value
        return link.from_socket
    return None


class OverlayError(Exception):
    """A message meant for the user."""


def add_overlay(mat, generator, values=None, tile=False):
    """Insert an overlay between the material and its Principled BSDF (on top of the stack)."""
    if not G.is_overlay(generator):
        raise ValueError(generator)
    tree = ensure_node_tree(mat)
    bsdf = find_principled(tree)
    if bsdf is None:
        raise OverlayError('"%s" has no Principled BSDF node, so dirt and dust cannot be layered on it.'
                           % mat.name)
    height = height_source(mat)
    node = tree.nodes.new('ShaderNodeGroup')
    node.node_tree = ensure_group(generator, tile)
    node.label = G.GENERATORS[generator]['label']
    node.width = 220
    x0 = bsdf.location.x
    for other in tree.nodes:
        if other != node and other.location.x >= x0 - 1.0:
            other.location.x += OVERLAY_STEP
    node.location = (x0, bsdf.location.y)
    apply_values(node, {k: v for k, v in (values or {}).items() if k not in O.CHANNEL_NAMES})
    links = tree.links
    for channel, bsdf_name in OVERLAY_LINKS:
        target = bsdf.inputs.get(bsdf_name)
        if target is None:
            continue
        if target.is_linked:
            links.new(target.links[0].from_socket, node.inputs[channel])
        elif channel != 'Normal':  # unconnected normal = plain surface normal
            set_socket_value(node.inputs[channel], socket_value(target))
        links.new(node.outputs[channel], target)
    if is_socket(height):
        links.new(height, node.inputs['Height'])
    elif height is not None:
        set_socket_value(node.inputs['Height'], height)
    return node


def add_overlay_state(mat, state, tile=False, extra=None):
    values = dict(state.values)
    values.update(extra or {})
    node = add_overlay(mat, state.generator, values, tile)
    node.label = state.label or node.label
    if state.from_preset:
        node[PRESET_OVERLAY_TAG] = True
    if state.hidden_opacity is not None:
        node['bpm_opacity'] = state.hidden_opacity
    return node


def remove_overlay(mat, node):
    """Take an overlay out of the stack, reconnecting what was below it to what was above."""
    tree = mat.node_tree
    links = tree.links
    for channel in O.CHANNEL_NAMES:
        inp, out = node.inputs[channel], node.outputs[channel]
        src = inp.links[0].from_socket if inp.is_linked else None
        for target in [l.to_socket for l in out.links]:
            if src is not None:
                links.new(src, target)
            elif channel != 'Normal' and hasattr(target, 'default_value'):
                set_socket_value(target, socket_value(inp))
    x = node.location.x
    tree.nodes.remove(node)
    for other in tree.nodes:
        if other.location.x > x + 1.0:
            other.location.x -= OVERLAY_STEP


def move_overlay(mat, index, step):
    """Move overlay number `index` (in stack order) up (+1) or down (-1)."""
    stack = overlay_stack(mat)
    new = index + step
    if not (0 <= index < len(stack) and 0 <= new < len(stack)):
        return False
    states = [OverlayState(n) for n in stack]
    states[index], states[new] = states[new], states[index]
    tile = bool(stack[0].node_tree.get('bpm_tile'))
    for node in reversed(stack):
        remove_overlay(mat, node)
    for state in states:
        add_overlay_state(mat, state, tile)
    return True


def copy_overlays(src, dst, tile=False, extra=None):
    """Re-create the overlays of material `src` on top of material `dst`."""
    for state in overlay_states(src):
        add_overlay_state(dst, state, tile, extra)


def toggle_overlay(node):
    """Hide / show an overlay (through its Opacity, see overlays.py)."""
    sock = node.inputs['Opacity']
    if node.get('bpm_opacity') is not None:
        sock.default_value = float(node['bpm_opacity']) or 1.0
        del node['bpm_opacity']
    else:
        node['bpm_opacity'] = float(sock.default_value)
        sock.default_value = 0.0


def overlay_hidden(node):
    return node.get('bpm_opacity') is not None


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


def fit_scale(objects, generator=None):
    """Pattern scale so that features look natural for the object size."""
    sizes = [max(o.dimensions) for o in objects if o is not None and max(o.dimensions) > 1e-6]
    if not sizes:
        return 1.0
    size = sum(sizes) / len(sizes)
    strength = G.GENERATORS[generator]['fit'] if generator in G.GENERATORS else 0.75
    return float(min(max((2.0 / size) ** strength, 0.02), 50.0))


def active_bpm_material(context):
    """(object, material, bpm node) for the active object, or Nones."""
    obj = context.active_object
    if not can_have_material(obj):
        return obj, None, None
    mat = obj.active_material
    return obj, mat, find_bpm_node(mat)
