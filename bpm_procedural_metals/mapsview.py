# SPDX-License-Identifier: GPL-3.0-or-later
"""Debug view of the shape analysis: show the mesh maps themselves on the objects.

Every mesh object in the view layer temporarily shows the material "BPM Analysis
View" (as an object-level material, so the materials on the mesh stay as they
are) and the 3D viewports switch to Material Preview.  Turning the view off puts
everything back.  Baking and analyzing turn it off while they run.

A view layer material override would be simpler, but Material Preview ignores it
in Blender 4.x.

Also: writing an object's maps to image files (combined and one per channel).
"""

import os

import bpy
import numpy as np

from . import meshmaps as M
from .nodebuilder import Builder

MATERIAL_NAME = 'BPM Analysis View'
MATERIAL_TAG = 'bpm_analysis_view'
MODES = [
    ('OFF', 'Off', 'Show the objects\' own materials'),
    ('ALL', 'All', 'Red = outer edges, green = inner corners, blue = occlusion'),
    ('CONVEX', 'Edges', 'Outer edges: white on the edge, fading to black at the edge reach'),
    ('CONCAVE', 'Corners', 'Inner corners and creases: white in the corner, fading to black at the corner reach'),
    ('OCCLUSION', 'Occlusion', 'How enclosed the surface is: white = enclosed, black = open'),
    ('UV', 'UV Layout', 'The maps\' own UV layout as a checker: stretched or tiny squares show where the maps '
                        'are blurry'),
]
NO_MAPS = (0.12, 0.02, 0.12, 1.0)  # objects without (readable) maps: dark purple
CHANNEL = {'CONVEX': 0, 'CONCAVE': 1, 'OCCLUSION': 2}

_shading = {}  # 3D viewport (pointer) -> shading type before the view was turned on


# --------------------------------------------------------------- material
def find_material():
    for mat in bpy.data.materials:
        if mat.get(MATERIAL_TAG) and mat.library is None:
            return mat
    return None


def build_material(mode):
    """The view material for `mode` (made or rebuilt)."""
    mat = find_material()
    if mat is None:
        mat = bpy.data.materials.new(MATERIAL_NAME)
        mat[MATERIAL_TAG] = True
    if not mat.use_nodes:
        mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    b = Builder(tree)
    uv = b.node('ShaderNodeUVMap', label='Mesh Maps UV')
    uv.uv_map = M.UV_NAME
    flag = b.node('ShaderNodeAttribute', label=M.FLAG)
    flag.attribute_type = 'OBJECT'
    flag.attribute_name = M.FLAG
    if mode == 'UV':
        local = b.vmath('FRACTION', uv.outputs['UV'])  # the position inside its tile
        u, v, _w = b.separate(local)
        bright = b.combine_color(u, v, 0.6)
        checker = b.node('ShaderNodeTexChecker')
        checker.inputs['Scale'].default_value = 32.0
        b.feed(checker.inputs['Vector'], local)
        b.feed(checker.inputs['Color1'], bright)
        b.feed(checker.inputs['Color2'], b.color_scale(bright, 0.35))
        color = checker.outputs['Color']
    else:
        tex = b.node('ShaderNodeTexImage', label='Mesh Maps')
        tex.image = M.ensure_image()
        tex.interpolation = 'Linear'
        tex.extension = 'EXTEND'
        b.feed(tex.inputs['Vector'], uv.outputs['UV'])
        if mode in CHANNEL:
            channel = b.separate_color(tex.outputs['Color'])[CHANNEL[mode]]
            color = b.combine_color(channel, channel, channel)
        else:
            color = tex.outputs['Color']
    color = b.mix_color(b.clamp01(flag.outputs['Fac']), NO_MAPS, color)
    emission = b.node('ShaderNodeEmission')
    b.feed(emission.inputs['Color'], color)
    out = b.node('ShaderNodeOutputMaterial')
    tree.links.new(emission.outputs[0], out.inputs['Surface'])
    mat[MATERIAL_TAG] = mode
    return mat


# --------------------------------------------------------------- objects
def _targets(context):
    return [obj for obj in context.view_layer.objects
            if obj.type == 'MESH' and obj.library is None and obj.data.library is None]


def is_shown(obj):
    return bool(getattr(obj, 'bpm_view_slots', None)) or bool(obj.get('bpm_view_added_slot'))


def _show_on(obj, mat):
    if is_shown(obj):
        for slot in obj.material_slots:
            if slot.link == 'OBJECT':
                slot.material = mat
        return
    if not obj.material_slots:
        obj.data.materials.append(None)
        obj['bpm_view_added_slot'] = True
    for index, slot in enumerate(obj.material_slots):
        entry = obj.bpm_view_slots.add()
        entry.index = index
        entry.link = slot.link
        slot.link = 'OBJECT'
        entry.material = slot.material  # the object's own material (usually none)
        slot.material = mat


def _hide_on(obj):
    for entry in obj.bpm_view_slots:
        if entry.index < len(obj.material_slots):
            slot = obj.material_slots[entry.index]
            if slot.link != 'OBJECT':
                slot.link = 'OBJECT'
            slot.material = entry.material
            slot.link = entry.link or 'DATA'
    obj.bpm_view_slots.clear()
    if obj.get('bpm_view_added_slot'):
        del obj['bpm_view_added_slot']
        mats = obj.data.materials
        if len(mats) == 1 and mats[0] is None:  # the mesh had no materials (pop() keeps the slot)
            mats.clear()


def _viewports(context):
    wm = context.window_manager
    for window in wm.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        yield area, space


def show(context, mode):
    """Show the maps (`mode` from MODES, not 'OFF') on every mesh object of the view layer."""
    mat = build_material(mode)
    for obj in _targets(context):
        _show_on(obj, mat)
    for area, space in _viewports(context):
        if space.shading.type in {'SOLID', 'WIREFRAME'}:
            _shading.setdefault(space.as_pointer(), space.shading.type)
            space.shading.type = 'MATERIAL'
        area.tag_redraw()


def hide(context, viewports=True):
    """Put the objects' own materials back (`viewports`: also their shading, and drop the
    view material; not while a job only suspends the view)."""
    for obj in bpy.data.objects:
        if obj.library is None and is_shown(obj):
            _hide_on(obj)
    if viewports:
        mat = find_material()
        if mat is not None and mat.users == 0:
            bpy.data.materials.remove(mat)
        for area, space in _viewports(context):
            old = _shading.pop(space.as_pointer(), None)
            if old is not None and space.shading.type == 'MATERIAL':
                space.shading.type = old
            area.tag_redraw()
        _shading.clear()


def mode_of(context):
    props = getattr(context.scene, 'bpm', None)
    return getattr(props, 'analysis_view', 'OFF') if props is not None else 'OFF'


def update(context):
    """Apply the scene's view setting (called when it changes)."""
    mode = mode_of(context)
    if mode == 'OFF':
        hide(context)
    else:
        show(context, mode)


def turn_off(context):
    """Show the objects' own materials again (before materials are assigned)."""
    try:
        props = getattr(context.scene, 'bpm', None)
        if props is not None and props.analysis_view != 'OFF':
            props.analysis_view = 'OFF'  # its update hides the view
        elif any(is_shown(o) for o in bpy.data.objects if o.library is None):
            hide(context)
    except (AttributeError, ReferenceError, RuntimeError):
        pass


def suspend(context):
    """Hide the view while a job bakes; returns what resume() needs."""
    try:
        mode = mode_of(context)
        if mode != 'OFF' or any(is_shown(o) for o in bpy.data.objects if o.library is None):
            hide(context, viewports=False)
        return mode
    except (AttributeError, ReferenceError, RuntimeError):
        return 'OFF'


def resume(context, mode):
    if mode and mode != 'OFF':
        try:
            show(context, mode)
        except (AttributeError, ReferenceError, RuntimeError):
            pass


# --------------------------------------------------------------- image files
def tile_pixels(mesh):
    """(height, width, 4) float pixels of a mesh's tile, rows from the bottom, or None."""
    img = M.find_image()
    if img is None or not M.has_maps(mesh):
        return None
    data = M._tile_files(img).get(int(mesh.get(M.TILE, 0)))
    if data is None:
        return None
    folder = bpy.app.tempdir or os.path.dirname(bpy.data.filepath) or '.'
    path = os.path.join(folder, 'bpm_tile_%d.png' % int(mesh[M.TILE]))
    with open(path, 'wb') as f:
        f.write(data)
    tmp = bpy.data.images.load(path, check_existing=False)
    try:
        M._non_color(tmp)
        width, height = tmp.size
        px = np.empty(width * height * 4, dtype=np.float32)
        tmp.pixels.foreach_get(px)
    finally:
        bpy.data.images.remove(tmp)
        try:
            os.remove(path)
        except OSError:
            pass
    return px.reshape(height, width, 4)


def _safe(name):
    return ''.join(c if c.isalnum() or c in '-_' else '_' for c in name).strip('_') or 'Object'


def save_images(objects, folder):
    """Write each analyzed object's maps as PNG files: <Name>_MeshMaps.png (R = edges,
    G = corners, B = occlusion) and _Edges / _Corners / _Occlusion.png.  Returns
    ({object name: [paths]}, [names without maps])."""
    os.makedirs(folder, exist_ok=True)
    saved, missing, done = {}, [], {}
    for obj in objects:
        if obj is None or obj.type != 'MESH':
            continue
        mesh = obj.data
        if mesh.name in done:
            saved[obj.name] = done[mesh.name]
            continue
        px = tile_pixels(mesh)
        if px is None:
            missing.append(obj.name)
            continue
        height, width = px.shape[:2]
        base = os.path.join(folder, _safe(obj.name))
        paths = []
        rgb = px.copy()
        rgb[..., 3] = 1.0
        for suffix, image in (('MeshMaps', rgb), ('Edges', None), ('Corners', None), ('Occlusion', None)):
            if image is None:
                channel = px[..., {'Edges': 0, 'Corners': 1, 'Occlusion': 2}[suffix]]
                image = np.stack([channel, channel, channel, np.ones_like(channel)], axis=-1)
            path = '%s_%s.png' % (base, suffix)
            M._write_png(path, image, width, height)
            paths.append(path)
        saved[obj.name] = done[mesh.name] = paths
    return saved, missing


def show_in_image_editor(context, path):
    """Load `path` into an open Image Editor, if there is one.  Returns True if shown."""
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'IMAGE_EDITOR':
                img = bpy.data.images.load(path, check_existing=True)
                img.reload()
                M._non_color(img)
                area.spaces.active.image = img
                area.tag_redraw()
                return True
    return False
