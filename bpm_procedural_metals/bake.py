# SPDX-License-Identifier: GPL-3.0-or-later
"""Baking materials to image textures.

Two modes:

* ``bake_objects``: bakes every material of the given mesh objects into one
  texture set per object, using the object's UV map (created automatically if
  missing).  Works with BPM materials and with any Principled BSDF material.
* ``bake_tiles``: bakes BPM materials into seamless, tileable square textures.

Both are generators that yield a status string after every step, so the UI can
show progress between steps.  Everything they change temporarily (render
settings, selection, material nodes, ...) is restored afterwards, even when an
error happens or the user cancels.
"""

import math
import os
import re

import bpy
import numpy as np

from . import generators as G
from . import library as L
from .nodebuilder import is_socket

# key: (label, file suffix, kind, principled input, is_color)
MAPS = {
    'BASE_COLOR': ('Base Color', 'BaseColor', 'EMIT', 'Base Color', True),
    'METALLIC': ('Metallic', 'Metallic', 'EMIT', 'Metallic', False),
    'ROUGHNESS': ('Roughness', 'Roughness', 'EMIT', 'Roughness', False),
    'NORMAL': ('Normal', 'Normal', 'NORMAL', 'Normal', False),
    'HEIGHT': ('Height', 'Height', 'EMIT', None, False),
    'AO': ('Ambient Occlusion', 'AO', 'AO', None, False),
}
MAP_ORDER = ('BASE_COLOR', 'METALLIC', 'ROUGHNESS', 'NORMAL', 'HEIGHT', 'AO')

QUALITY_SAMPLES = {
    # quality: (color/data samples, ambient occlusion samples)
    'FAST': (4, 16),
    'GOOD': (16, 64),
    'BEST': (64, 256),
}

FALLBACK_DIR = os.path.join(os.path.expanduser('~'), 'BPM_Textures')
BAKE_UV_NAME = 'BPM_Bake'


class BakeError(Exception):
    """An error with a message that is meant to be shown to the user."""


class BakeSettings:
    """Plain settings container (filled from the UI or the command line)."""

    def __init__(self, **kwargs):
        self.resolution = 2048
        self.quality = 'GOOD'
        self.maps = set(MAP_ORDER)
        self.output_dir = '//BPM_Textures'
        self.normal_directx = False
        self.use_16bit = False
        self.pack_orm = False
        self.pack_unity = False
        self.assign_baked = True
        self.auto_unwrap = True
        self.force_new_uv = False
        self.device = 'AUTO'
        self.tile_size = 1.0
        self.create_tile_material = True
        for key, value in kwargs.items():
            if not hasattr(self, key):
                raise TypeError('Unknown bake setting: %s' % key)
            setattr(self, key, value)

    @classmethod
    def from_props(cls, props):
        maps = {key for key in MAP_ORDER if getattr(props, 'map_' + key.lower())}
        return cls(resolution=int(props.resolution), quality=props.quality, maps=maps,
                   output_dir=props.output_dir, normal_directx=props.normal_format == 'DIRECTX',
                   use_16bit=props.bit_depth == '16', pack_orm=props.pack_orm, pack_unity=props.pack_unity,
                   assign_baked=props.assign_baked, auto_unwrap=props.auto_unwrap,
                   force_new_uv=props.force_new_uv, device=props.device, tile_size=props.tile_size)

    @property
    def margin(self):
        return max(4, int(self.resolution) // 128)

    @property
    def samples(self):
        return QUALITY_SAMPLES.get(self.quality, QUALITY_SAMPLES['GOOD'])


# ---------------------------------------------------------------- utilities
def clean_name(name):
    name = re.sub(r'[^\w\-]+', '_', name, flags=re.UNICODE).strip('_')
    return name or 'Untitled'


def resolve_output_dir(path):
    """Absolute output folder; falls back to ~/BPM_Textures for unsaved files."""
    path = (path or '').strip() or '//BPM_Textures'
    if path.startswith('//') and not bpy.data.filepath:
        path = os.path.join(FALLBACK_DIR, path[2:].strip('/\\'))
    path = os.path.abspath(bpy.path.abspath(path))
    try:
        os.makedirs(path, exist_ok=True)
    except OSError as exc:
        raise BakeError('Cannot create the output folder "%s": %s' % (path, exc.strerror or exc))
    if not os.access(path, os.W_OK):
        raise BakeError('The output folder "%s" is not writable. Pick another folder.' % path)
    return path


def blend_path(path):
    """Relative '//' path when the file lives next to the .blend, absolute otherwise."""
    if bpy.data.filepath:
        try:
            return bpy.path.relpath(path)
        except ValueError:  # different drive on Windows
            return path
    return path


def check_cycles():
    if bpy.context.preferences.addons.get('cycles') is None:
        raise BakeError('Baking needs the Cycles render engine. Enable the "Cycles Render Engine" '
                        'add-on in Edit > Preferences > Add-ons.')


def uses_nodes(mat):
    if mat is None or mat.node_tree is None:
        return False
    if bpy.app.version >= (5, 0, 0):
        return True
    return bool(mat.use_nodes)


def choose_device(preference):
    """'GPU' only if the user has set up a GPU in Preferences > System."""
    if preference == 'CPU':
        return 'CPU'
    try:
        cprefs = bpy.context.preferences.addons['cycles'].preferences
        if cprefs.compute_device_type == 'NONE':
            return 'CPU'
        try:
            cprefs.refresh_devices()
        except Exception:
            pass
        if any(dev.use and dev.type != 'CPU' for dev in cprefs.devices):
            return 'GPU'
    except Exception:
        pass
    return 'CPU'


def uv_stats(mesh, uv_layer):
    """(total area, min, max) of a UV layer."""
    n = len(mesh.loops)
    if n == 0 or len(mesh.polygons) == 0:
        return 0.0, 0.0, 0.0
    uv = np.empty(n * 2, dtype=np.float64)
    uv_layer.data.foreach_get('uv', uv)
    uv = uv.reshape(-1, 2)
    starts = np.empty(len(mesh.polygons), dtype=np.int64)
    totals = np.empty(len(mesh.polygons), dtype=np.int64)
    mesh.polygons.foreach_get('loop_start', starts)
    mesh.polygons.foreach_get('loop_total', totals)
    nxt = np.arange(n) + 1
    nxt[starts + totals - 1] = starts
    cross = uv[:, 0] * uv[nxt, 1] - uv[nxt, 0] * uv[:, 1]
    order = np.argsort(starts)
    area = 0.5 * np.abs(np.add.reduceat(cross, starts[order])).sum()
    return float(area), float(uv.min()), float(uv.max())


# ---------------------------------------------------------- material rigs
_surface_link = L._surface_link
find_principled = L.find_principled


class MaterialRig:
    """Temporarily rewires one material for baking individual channels."""

    def __init__(self, mat):
        self.mat = mat
        self.tree = mat.node_tree
        nodes = self.tree.nodes
        self.orig_active = nodes.active
        self.temp_out = None
        try:
            self.out = self.tree.get_output_node('CYCLES')
        except (AttributeError, TypeError):
            self.out = None
        if self.out is None:
            # no output Cycles would use: add one wired like the existing output
            existing = L.output_node(self.tree)
            self.out = self.temp_out = nodes.new('ShaderNodeOutputMaterial')
            self.temp_out.target = 'CYCLES'
            link = _surface_link(existing) if existing is not None else None
            if link is not None:
                self.tree.links.new(link.from_socket, self.temp_out.inputs['Surface'])
            self.temp_out.is_active_output = True
        surface = _surface_link(self.out)
        self.orig_surface = surface.from_socket if surface else None
        self.bpm = L.find_bpm_node(mat)
        self.bsdf = find_principled(self.tree, self.out)
        self.target = nodes.new('ShaderNodeTexImage')
        self.target.name = self.target.label = 'BPM Bake Target'
        self.target.location = (self.out.location.x, self.out.location.y - 400)
        self.pass_nodes = []

    # -- sources ---------------------------------------------------------
    def source(self, key):
        """Socket or constant that holds the value of a map (None = not available)."""
        if key == 'HEIGHT':
            return L.height_source(self.mat, self.out)
        name = MAPS[key][3]
        if self.bsdf is not None:
            sock = self.bsdf.inputs[name]
            if sock.is_linked:
                return sock.links[0].from_socket
            return None if key == 'NORMAL' else tuple(sock.default_value) if sock.type == 'RGBA' \
                else sock.default_value
        # no Principled BSDF: sensible fallbacks
        if key == 'BASE_COLOR':
            link = _surface_link(self.out)
            if link is not None:
                col = link.from_node.inputs.get('Color')
                if col is not None:
                    return col.links[0].from_socket if col.is_linked else tuple(col.default_value)
            return tuple(self.mat.diffuse_color)
        return {'METALLIC': 0.0, 'ROUGHNESS': 0.5}.get(key)

    # -- pass setup --------------------------------------------------------
    def set_target(self, image):
        self.target.image = image
        self.tree.nodes.active = self.target
        self.target.select = True

    def _connect_surface(self, shader_socket):
        self.tree.links.new(shader_socket, self.out.inputs['Surface'])

    def setup_emit(self, value):
        nodes = self.tree.nodes
        em = nodes.new('ShaderNodeEmission')
        em.inputs['Strength'].default_value = 1.0
        self.pass_nodes.append(em)
        if is_socket(value):
            self.tree.links.new(value, em.inputs['Color'])
        elif value is None:
            em.inputs['Color'].default_value = (0.5, 0.5, 0.5, 1.0)
        elif isinstance(value, (int, float)):
            v = float(value)
            em.inputs['Color'].default_value = (v, v, v, 1.0)
        else:
            em.inputs['Color'].default_value = tuple(value)[:3] + (1.0,)
        self._connect_surface(em.outputs['Emission'])

    def setup_normal(self, value):
        diffuse = self.tree.nodes.new('ShaderNodeBsdfDiffuse')
        self.pass_nodes.append(diffuse)
        if is_socket(value):
            self.tree.links.new(value, diffuse.inputs['Normal'])
        self._connect_surface(diffuse.outputs['BSDF'])

    def setup_ao(self, distance):
        ao = self.tree.nodes.new('ShaderNodeAmbientOcclusion')
        ao.only_local = True
        ao.samples = 16
        ao.inputs['Distance'].default_value = distance
        self.pass_nodes.append(ao)
        self.setup_emit(ao.outputs['AO'])

    def clear_pass(self):
        for node in self.pass_nodes:
            self.tree.nodes.remove(node)
        self.pass_nodes = []
        if self.orig_surface is not None:
            self._connect_surface(self.orig_surface)

    def cleanup(self):
        self.clear_pass()
        nodes = self.tree.nodes
        nodes.remove(self.target)
        if self.temp_out is not None:
            nodes.remove(self.temp_out)
        if self.orig_active is not None and self.orig_active.name in nodes:
            nodes.active = self.orig_active


# -------------------------------------------------------------- the session
def _alive(idblock):
    """False for None or for a Python handle whose Blender data was deleted."""
    if idblock is None:
        return False
    try:
        idblock.name
        return True
    except ReferenceError:
        return False


class _SceneState:
    """Remembers and restores everything the bake touches globally."""

    def __init__(self, context):
        self.context = context
        scene = context.scene
        self.scene = scene
        self.engine = scene.render.engine
        cyc = scene.cycles
        self.cycles = {k: getattr(cyc, k) for k in ('samples', 'device', 'use_adaptive_sampling',
                                                    'use_denoising', 'time_limit')
                       if hasattr(cyc, k)}
        bake = scene.render.bake
        self.bake = {p.identifier: getattr(bake, p.identifier) for p in bake.bl_rna.properties
                     if not p.is_readonly and p.type in {'BOOLEAN', 'INT', 'FLOAT', 'ENUM', 'STRING'}
                     and not getattr(p, 'is_array', False)}
        view_layer = context.view_layer
        self.view_layer = view_layer
        self.active = view_layer.objects.active
        self.selected = [o for o in view_layer.objects if o.select_get()]
        self.mode = context.mode
        if self.active is not None and self.active.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

    def prepare(self, device, samples):
        scene = self.scene
        scene.render.engine = 'CYCLES'
        cyc = scene.cycles
        cyc.device = device
        cyc.samples = samples
        if hasattr(cyc, 'use_adaptive_sampling'):
            cyc.use_adaptive_sampling = False
        if hasattr(cyc, 'time_limit'):
            cyc.time_limit = 0.0

    def select_only(self, obj):
        for o in self.view_layer.objects:
            if o is not None and o.select_get():
                o.select_set(False)
        obj.select_set(True)
        self.view_layer.objects.active = obj

    def restore(self):
        scene = self.scene
        try:
            for key, value in self.bake.items():
                try:
                    setattr(scene.render.bake, key, value)
                except (AttributeError, TypeError, ValueError):
                    pass
            for key, value in self.cycles.items():
                try:
                    setattr(scene.cycles, key, value)
                except (AttributeError, TypeError, ValueError):
                    pass
            scene.render.engine = self.engine
        finally:
            try:
                self.view_layer.update()
                layer_objects = self.view_layer.objects
                for o in layer_objects:
                    if o is not None and o.select_get():
                        o.select_set(False)
                for o in self.selected:
                    if _alive(o) and o.name in layer_objects:
                        o.select_set(True)
                if _alive(self.active) and self.active.name in layer_objects:
                    layer_objects.active = self.active
                    if self.mode == 'EDIT_MESH' and self.active.type == 'MESH':
                        bpy.ops.object.mode_set(mode='EDIT')
            except (ReferenceError, RuntimeError):
                pass


def _bake_call(context, obj, kind, settings, uv_name, normal=False):
    kwargs = dict(type=kind, margin=settings.margin, margin_type='ADJACENT_FACES', use_clear=True,
                  use_selected_to_active=False, target='IMAGE_TEXTURES', save_mode='INTERNAL')
    if uv_name:
        kwargs['uv_layer'] = uv_name
    if normal:
        kwargs.update(normal_space='TANGENT', normal_r='POS_X',
                      normal_g='NEG_Y' if settings.normal_directx else 'POS_Y', normal_b='POS_Z')
    override = dict(active_object=obj, object=obj, selected_objects=[obj], selected_editable_objects=[obj])
    try:
        with context.temp_override(**override):
            result = bpy.ops.object.bake(**kwargs)
    except RuntimeError as exc:
        raise BakeError('Blender could not bake "%s": %s' % (obj.name, str(exc).strip().splitlines()[-1]))
    if 'FINISHED' not in result:
        raise BakeError('Baking "%s" was cancelled.' % obj.name)


def _new_image(name, size, is_color, float_buffer, alpha=False):
    img = bpy.data.images.new(name, size, size, alpha=alpha, float_buffer=float_buffer, is_data=not is_color)
    if not is_color:
        _set_non_color(img)
    return img


def _set_non_color(img):
    try:
        img.colorspace_settings.name = 'Non-Color'
    except TypeError:
        img.colorspace_settings.is_data = True


def _pixels(img):
    arr = np.empty(len(img.pixels), dtype=np.float32)
    img.pixels.foreach_get(arr)
    return arr.reshape(-1, 4)


def _save(img, path):
    img.filepath_raw = path
    img.file_format = 'PNG'
    try:
        img.save()
    except RuntimeError as exc:
        raise BakeError('Could not save "%s": %s' % (path, exc))


def _load(path, is_color):
    img = bpy.data.images.load(path, check_existing=True)
    stored = blend_path(path)
    if img.filepath != stored:
        img.filepath = stored  # relative to the .blend file when possible, so projects can be moved
    img.reload()
    if not is_color:
        _set_non_color(img)
    return img


def _save_packed(name, path, size, channels, alpha=False, float_buffer=False):
    """Write a channel-packed texture. channels: list of 1D arrays (or floats)."""
    count = size * size
    out = np.ones((count, 4), dtype=np.float32)
    for i, ch in enumerate(channels):
        out[:, i] = ch
    img = bpy.data.images.new(name, size, size, alpha=alpha, float_buffer=float_buffer, is_data=True)
    _set_non_color(img)
    img.pixels.foreach_set(out.ravel())
    if alpha:
        img.alpha_mode = 'STRAIGHT'
    _save(img, path)
    bpy.data.images.remove(img)
    return _load(path, False)


# ---------------------------------------------------------- baked material
def build_baked_material(name, images, uv_name, directx=False, tag_value=True):
    """Create (or rebuild) an image-texture material from baked maps."""
    mat = bpy.data.materials.get(name)
    if mat is None or not mat.get(L.BAKED_TAG):
        mat = bpy.data.materials.new(name)
    tree = L.ensure_node_tree(mat)
    tree.nodes.clear()
    nodes, links = tree.nodes, tree.links
    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = (600, 0)
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (250, 0)
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    uv = nodes.new('ShaderNodeUVMap')
    uv.location = (-900, 0)
    if uv_name:
        uv.uv_map = uv_name

    def tex(key, y):
        node = nodes.new('ShaderNodeTexImage')
        node.image = images[key]
        node.label = MAPS[key][0] if key in MAPS else key
        node.location = (-600, y)
        links.new(uv.outputs['UV'], node.inputs['Vector'])
        return node

    y = 400
    if 'BASE_COLOR' in images:
        links.new(tex('BASE_COLOR', y).outputs['Color'], bsdf.inputs['Base Color'])
    y -= 300
    if 'METALLIC' in images:
        links.new(tex('METALLIC', y).outputs['Color'], bsdf.inputs['Metallic'])
    y -= 300
    if 'ROUGHNESS' in images:
        links.new(tex('ROUGHNESS', y).outputs['Color'], bsdf.inputs['Roughness'])
    y -= 300
    if 'NORMAL' in images:
        node = tex('NORMAL', y)
        nmap = nodes.new('ShaderNodeNormalMap')
        nmap.location = (-250, y)
        if uv_name:
            nmap.uv_map = uv_name
        color = node.outputs['Color']
        if directx:  # Blender expects OpenGL normal maps: flip green back for rendering
            sep = nodes.new('ShaderNodeSeparateColor')
            comb = nodes.new('ShaderNodeCombineColor')
            inv = nodes.new('ShaderNodeMath')
            inv.operation = 'SUBTRACT'
            inv.inputs[0].default_value = 1.0
            sep.location, inv.location, comb.location = (-420, y - 150), (-420, y - 300), (-420, y - 450)
            links.new(color, sep.inputs[0])
            links.new(sep.outputs[0], comb.inputs[0])
            links.new(sep.outputs[1], inv.inputs[1])
            links.new(inv.outputs[0], comb.inputs[1])
            links.new(sep.outputs[2], comb.inputs[2])
            color = comb.outputs[0]
        links.new(color, nmap.inputs['Color'])
        links.new(nmap.outputs['Normal'], bsdf.inputs['Normal'])
    y -= 300
    if 'HEIGHT' in images:
        node = tex('HEIGHT', y)
        node.label = 'Height (not connected)'
    y -= 300
    if 'AO' in images:
        node = tex('AO', y)
        gltf = _gltf_output_group()
        if gltf is not None:
            group = nodes.new('ShaderNodeGroup')
            group.node_tree = gltf
            group.location = (250, -500)
            links.new(node.outputs['Color'], group.inputs['Occlusion'])
        else:
            node.label = 'Ambient Occlusion (not connected)'
    mat[L.BAKED_TAG] = tag_value
    mat.use_fake_user = False
    return mat


def _gltf_output_group():
    """The custom node group the glTF exporter reads ambient occlusion from."""
    for name in ('glTF Material Output', 'glTF Settings'):
        group = bpy.data.node_groups.get(name)
        if group is not None and group.bl_idname == 'ShaderNodeTree' and 'Occlusion' in group.interface.items_tree:
            return group
    try:
        group = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
        group.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
        group.interface.new_socket('Thickness', in_out='INPUT', socket_type='NodeSocketFloat')
        group.nodes.new('NodeGroupInput')
        return group
    except Exception:
        return None


def assign_baked(obj, mat):
    """Show the baked material on `obj`, remembering the original materials."""
    if not hasattr(obj, 'bpm_backup'):
        for slot in obj.material_slots:
            slot.material = mat
        return
    if not obj.bpm_backup:
        for index, slot in enumerate(obj.material_slots):
            entry = obj.bpm_backup.add()
            entry.index = index
            entry.material = slot.material
            if slot.material is not None:
                slot.material.use_fake_user = True
    for slot in obj.material_slots:
        slot.material = mat


def restore_procedural(obj):
    """Put the original (procedural) materials back.  Returns True if anything changed."""
    backup = getattr(obj, 'bpm_backup', None)
    if not backup:
        return False
    for entry in backup:
        if entry.index < len(obj.material_slots):
            obj.material_slots[entry.index].material = entry.material
    backup.clear()
    return True


def baked_material_of(obj):
    for slot in obj.material_slots:
        if L.is_baked_material(slot.material):
            return slot.material
    return None


# ------------------------------------------------------------- object bake
class Job:
    """Base class: collects messages, owns the scene state and temp data."""

    def __init__(self, context, settings):
        self.context = context
        self.settings = settings
        self.messages = []    # (level, text)
        self.written = []     # file paths
        self.output_dir = None
        self.total_steps = 1
        self.done_steps = 0
        self._temp_images = []

    def info(self, text):
        self.messages.append(('INFO', text))

    def warn(self, text):
        self.messages.append(('WARNING', text))

    def _drop_temp_images(self):
        for img in self._temp_images:
            try:
                bpy.data.images.remove(img)
            except (ReferenceError, RuntimeError):
                pass
        self._temp_images = []

    def _make_images(self, prefix, keys, size):
        s = self.settings
        images = {}
        for key in keys:
            is_color = MAPS[key][4]
            floaty = s.use_16bit or key == 'HEIGHT'
            img = _new_image('%s_%s' % (prefix, MAPS[key][1]), size, is_color, floaty)
            self._temp_images.append(img)
            images[key] = img
        return images

    def _save_set(self, set_name, folder, images, size):
        """Save baked images + packed variants; returns {key: file image}."""
        s = self.settings
        files = {}
        arrays = {}
        if s.pack_orm or s.pack_unity:
            for key in ('AO', 'ROUGHNESS', 'METALLIC'):
                if key in images:
                    arrays[key] = _pixels(images[key])[:, 0].copy()
        for key, img in images.items():
            path = os.path.join(folder, '%s_%s.png' % (set_name, MAPS[key][1]))
            _save(img, path)
            self.written.append(path)
            files[key] = path
        self._drop_temp_images()
        loaded = {key: _load(path, MAPS[key][4]) for key, path in files.items()}
        count = size * size
        if s.pack_orm and 'ROUGHNESS' in arrays and 'METALLIC' in arrays:
            ao = arrays.get('AO', 1.0)
            path = os.path.join(folder, '%s_ORM.png' % set_name)
            _save_packed(set_name + '_ORM', path, size, [ao if isinstance(ao, np.ndarray) else np.full(count, ao),
                                                         arrays['ROUGHNESS'], arrays['METALLIC']])
            self.written.append(path)
        if s.pack_unity and 'ROUGHNESS' in arrays and 'METALLIC' in arrays:
            metal = arrays['METALLIC']
            path = os.path.join(folder, '%s_MetallicSmoothness.png' % set_name)
            _save_packed(set_name + '_MetallicSmoothness', path, size,
                         [metal, metal, metal, 1.0 - arrays['ROUGHNESS']], alpha=True)
            self.written.append(path)
        return loaded


class ObjectBakeJob(Job):
    """Bake the materials of mesh objects into per-object texture sets."""

    def __init__(self, context, objects, settings):
        super().__init__(context, settings)
        self.objects = []
        seen = set()
        for obj in objects:
            if obj is not None and obj.name not in seen:
                seen.add(obj.name)
                self.objects.append(obj)
        passes = len([k for k in MAP_ORDER if k in settings.maps])
        self.total_steps = max(1, len(self.objects) * (passes + 2))

    def check(self):
        """Raise BakeError for problems that stop everything; warn about the rest."""
        check_cycles()
        if not self.objects:
            raise BakeError('Select the object(s) you want to bake first.')
        if not self.settings.maps:
            raise BakeError('Tick at least one texture map to bake.')
        usable = [o for o in self.objects if self._skip_reason(o) is None]
        if not usable:
            reasons = '; '.join('%s %s' % (o.name, self._skip_reason(o)) for o in self.objects[:3])
            raise BakeError('Nothing can be baked: ' + reasons)

    def _skip_reason(self, obj):
        if obj.type != 'MESH':
            return 'is not a mesh (convert it with Object > Convert > Mesh)'
        if obj.library is not None or obj.data.library is not None:
            return 'is linked from another file'
        if len(obj.data.polygons) == 0:
            return 'has no faces'
        if not any(slot.material for slot in obj.material_slots) and not baked_material_of(obj):
            return 'has no material'
        if obj.name not in self.context.view_layer.objects:
            return 'is not in the current view layer'
        return None

    def run(self):
        s = self.settings
        context = self.context
        self.output_dir = resolve_output_dir(s.output_dir)
        state = _SceneState(context)
        samples, ao_samples = s.samples
        try:
            device = choose_device(s.device)
            state.prepare(device, samples)
            if s.device == 'GPU' and device == 'CPU':
                self.warn('No GPU is set up in Preferences > System, baking on the CPU.')
            used_names = set()
            for obj in self.objects:
                reason = self._skip_reason(obj)
                if reason:
                    self.warn('Skipped "%s": it %s.' % (obj.name, reason))
                    continue
                yield 'Preparing %s' % obj.name
                set_name = clean_name(obj.name)
                base, n = set_name, 2
                while set_name.lower() in used_names:
                    set_name, n = '%s_%d' % (base, n), n + 1
                used_names.add(set_name.lower())
                yield from self._bake_object(obj, set_name, state, samples, ao_samples)
        finally:
            self._drop_temp_images()
            state.restore()

    # -- one object --------------------------------------------------------
    def _bake_object(self, obj, set_name, state, samples, ao_samples):
        s = self.settings
        context = self.context
        was_baked = restore_procedural(obj)
        stand_ins = {}
        rigs = []
        hidden_render = obj.hide_render
        try:
            obj.hide_render = False
            uv_name = self._ensure_uvs(obj, state)
            # stand-in materials for empty slots / node-less materials
            for index, slot in enumerate(obj.material_slots):
                original = slot.material
                if not uses_nodes(original) or original.library is not None:
                    stand_ins[index] = original
                    slot.material = _stand_in_material(original)
            if not obj.material_slots:
                raise BakeError('"%s" has no material.' % obj.name)
            mats = []
            for slot in obj.material_slots:
                if slot.material not in mats:
                    mats.append(slot.material)
            rigs = [MaterialRig(m) for m in mats]

            keys = [k for k in MAP_ORDER if k in s.maps]
            if 'HEIGHT' in keys and all(r.source('HEIGHT') is None for r in rigs):
                keys.remove('HEIGHT')
                self.info('"%s": its material has no height information, skipped the height map.' % obj.name)
            images = self._make_images('BPM_tmp_' + set_name, keys, s.resolution)
            ao_distance = max(0.01, 0.2 * max(obj.dimensions))

            for key in keys:
                label, _suffix, kind, _inp, _is_color = MAPS[key]
                yield 'Baking %s: %s' % (obj.name, label)
                for rig in rigs:
                    rig.set_target(images[key])
                    if kind == 'NORMAL':
                        rig.setup_normal(rig.source('NORMAL'))
                    elif kind == 'AO':
                        rig.setup_ao(ao_distance)
                    else:
                        rig.setup_emit(rig.source(key))
                state.scene.cycles.samples = ao_samples if kind == 'AO' else samples
                try:
                    _bake_call(context, obj, 'NORMAL' if kind == 'NORMAL' else 'EMIT', s, uv_name,
                               normal=kind == 'NORMAL')
                finally:
                    for rig in rigs:
                        rig.clear_pass()
                self.done_steps += 1

            yield 'Saving textures for %s' % obj.name
            for rig in rigs:
                rig.cleanup()
            rigs = []
            for index, original in stand_ins.items():
                obj.material_slots[index].material = original
            stand_ins = {}
            loaded = self._save_set(set_name, self.output_dir, images, s.resolution)
            mat = build_baked_material('%s Baked' % obj.name, loaded, uv_name, s.normal_directx)
            mat['bpm_source_object'] = obj.name
            if s.assign_baked or was_baked:
                assign_baked(obj, mat)
            self.info('Baked "%s" (%d maps).' % (obj.name, len(loaded)))
            self.done_steps += 2
        finally:
            for rig in rigs:
                try:
                    rig.cleanup()
                except ReferenceError:
                    pass
            for index, original in stand_ins.items():
                obj.material_slots[index].material = original
            for mat in [m for m in bpy.data.materials if m.get('bpm_stand_in')]:
                bpy.data.materials.remove(mat)
            obj.hide_render = hidden_render
            if was_baked and not baked_material_of(obj):
                # bake failed: put the previous baked material back
                prev = bpy.data.materials.get('%s Baked' % obj.name)
                if prev is not None:
                    assign_baked(obj, prev)

    def _ensure_uvs(self, obj, state):
        s = self.settings
        mesh = obj.data
        layers = mesh.uv_layers
        need_new = s.force_new_uv or len(layers) == 0
        if not need_new:
            active = layers.active or layers[0]
            area, lo, hi = uv_stats(mesh, active)
            if area < 1e-6:
                need_new = True
                self.warn('"%s": its UV map is empty/flat, made a new one.' % obj.name)
            elif area > 1.02:
                need_new = True
                self.warn('"%s": its UV islands overlap, made a new UV map "%s" for baking.'
                          % (obj.name, BAKE_UV_NAME))
            elif lo < -0.01 or hi > 1.01:
                self.warn('"%s": parts of its UV map lie outside the texture square.' % obj.name)
        if need_new and not (s.auto_unwrap or s.force_new_uv):
            raise BakeError('"%s" needs a usable UV map. Enable "Auto UV Unwrap" or unwrap it '
                            'yourself (Edit Mode > U > Smart UV Project).' % obj.name)
        if not need_new:
            return (layers.active or layers[0]).name
        if mesh.users > 1:
            self.info('"%s" shares its mesh with other objects; they get the new UVs too.' % obj.name)
        layer = layers.get(BAKE_UV_NAME) or layers.new(name=BAKE_UV_NAME)
        if layer is None:
            raise BakeError('"%s" has too many UV maps (the maximum is 8).' % obj.name)
        uv_name = layer.name  # keep the name: layer references go stale when switching modes
        layers.active = layer
        state.select_only(obj)
        bpy.ops.object.mode_set(mode='EDIT')
        try:
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.02,
                                     area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
        finally:
            bpy.ops.object.mode_set(mode='OBJECT')
        self.info('"%s": created UV map "%s".' % (obj.name, uv_name))
        return uv_name


def _stand_in_material(original):
    """Editable stand-in for empty slots, node-less or linked (read-only) materials."""
    if original is not None and original.library is not None and original.node_tree is not None:
        mat = original.copy()  # local, editable copy with the same nodes
        mat['bpm_stand_in'] = True
        return mat
    mat = bpy.data.materials.new('BPM_StandIn')
    mat['bpm_stand_in'] = True
    tree = L.ensure_node_tree(mat)
    bsdf = next((n for n in tree.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled'), None)
    if bsdf is None:
        tree.nodes.clear()
        out = tree.nodes.new('ShaderNodeOutputMaterial')
        bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
        tree.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    if original is not None:
        bsdf.inputs['Base Color'].default_value = tuple(original.diffuse_color)
        bsdf.inputs['Metallic'].default_value = original.metallic
        bsdf.inputs['Roughness'].default_value = original.roughness
    else:
        bsdf.inputs['Base Color'].default_value = (0.0, 0.0, 0.0, 1.0)
    return mat


# --------------------------------------------------------------- tile bake
class TileBakeJob(Job):
    """Bake BPM materials into seamless square textures."""

    def __init__(self, context, materials, settings):
        super().__init__(context, settings)
        self.materials = []
        for mat in materials:
            if mat is not None and mat not in self.materials:
                self.materials.append(mat)
        maps = [k for k in MAP_ORDER if k in settings.maps and k != 'AO']
        self.total_steps = max(1, len(self.materials) * (len(maps) + 1))
        self.tile_materials = []

    def check(self):
        check_cycles()
        if not self.materials:
            raise BakeError('Select an object that uses a BPM material first.')
        if not any(L.find_bpm_node(m) for m in self.materials):
            raise BakeError('Seamless tiles can only be made from BPM materials. '
                            'Apply one from the library first.')
        if not [k for k in self.settings.maps if k != 'AO']:
            raise BakeError('Tick at least one texture map (ambient occlusion is not used for tiles).')

    def run(self):
        s = self.settings
        context = self.context
        self.output_dir = resolve_output_dir(s.output_dir)
        state = _SceneState(context)
        samples, _ = s.samples
        plane = mesh = temp_mat = None
        try:
            state.prepare(choose_device(s.device), samples)
            mesh = bpy.data.meshes.new('BPM_TilePlane')
            size = float(s.tile_size)
            mesh.from_pydata([(0, 0, 0), (size, 0, 0), (size, size, 0), (0, size, 0)], [], [(0, 1, 2, 3)])
            uv = mesh.uv_layers.new(name='UVMap')
            uv.data.foreach_set('uv', [0, 0, 1, 0, 1, 1, 0, 1])
            plane = bpy.data.objects.new('BPM_TilePlane', mesh)
            context.scene.collection.objects.link(plane)
            used = set()
            for mat in self.materials:
                node = L.find_bpm_node(mat)
                if node is None:
                    self.warn('Skipped "%s": not a BPM material.' % mat.name)
                    continue
                name = clean_name(mat.name)
                base, n = name, 2
                while name.lower() in used:
                    name, n = '%s_%d' % (base, n), n + 1
                used.add(name.lower())
                temp_mat = bpy.data.materials.new('BPM_TileBake')
                values = L.read_values(node)
                values['Tile Size'] = size
                L.build_material(temp_mat, node.node_tree['bpm_generator'], values, tile=True)
                L.copy_overlays(mat, temp_mat, tile=True, extra={'Tile Size': size})
                mesh.materials.clear()
                mesh.materials.append(temp_mat)
                values['_bump'] = G.GENERATORS[node.node_tree['bpm_generator']]['bump']
                yield from self._bake_tile(plane, temp_mat, mat, name, state, samples, values)
                mesh.materials.clear()
                bpy.data.materials.remove(temp_mat)
                temp_mat = None
        finally:
            self._drop_temp_images()
            if plane is not None:
                bpy.data.objects.remove(plane)
            if mesh is not None:
                bpy.data.meshes.remove(mesh)
            if temp_mat is not None:
                bpy.data.materials.remove(temp_mat)
            state.restore()

    def _bake_tile(self, plane, temp_mat, source_mat, name, state, samples, values):
        s = self.settings
        folder = os.path.join(self.output_dir, name + '_Tile')
        os.makedirs(folder, exist_ok=True)
        keys = [k for k in MAP_ORDER if k in s.maps and k != 'AO']
        # The normal map is computed from the height map (exact and seamless),
        # so height is always baked, even when it is not saved.
        baked = [k for k in keys if k != 'NORMAL']
        if 'NORMAL' in keys and 'HEIGHT' not in baked:
            baked.append('HEIGHT')
        images = self._make_images('BPM_tmp_' + name, baked, s.resolution)
        rig = MaterialRig(temp_mat)
        try:
            for key in baked:
                label = MAPS[key][0]
                yield 'Baking tile %s: %s' % (source_mat.name, label)
                rig.set_target(images[key])
                rig.setup_emit(rig.source(key))
                state.scene.cycles.samples = samples
                try:
                    _bake_call(self.context, plane, 'EMIT', s, 'UVMap')
                finally:
                    rig.clear_pass()
                self.done_steps += 1
        finally:
            rig.cleanup()
        if 'NORMAL' in keys:
            yield 'Computing tile normal map for %s' % source_mat.name
            images['NORMAL'] = self._normal_from_height(images['HEIGHT'], values, name)
            if 'HEIGHT' not in keys:
                self._temp_images.remove(images['HEIGHT'])
                bpy.data.images.remove(images.pop('HEIGHT'))
        yield 'Saving tile textures for %s' % source_mat.name
        loaded = self._save_set(name, folder, images, s.resolution)
        if s.create_tile_material:
            mat = build_tiled_material('%s Tiled' % source_mat.name, loaded, s.tile_size, s.normal_directx)
            self.tile_materials.append(mat)
        self.info('Made seamless tile "%s" (%d maps) in %s' % (source_mat.name, len(loaded), folder))
        self.done_steps += 1

    def _normal_from_height(self, height_img, values, name):
        s = self.settings
        size = int(s.resolution)
        height = _pixels(height_img)[:, 0].reshape(size, size)
        scale = max(float(values.get('Scale', 1.0)), 1e-6)
        rgb = normal_from_height(height, float(s.tile_size) / size, values.get('_bump', G.MACRO_BUMP) / scale,
                                 float(values.get('Bump Strength', 1.0)), s.normal_directx)
        img = _new_image('BPM_tmp_%s_Normal' % name, size, False, s.use_16bit)
        out = np.ones((size * size, 4), dtype=np.float32)
        out[:, :3] = rgb.reshape(-1, 3)
        img.pixels.foreach_set(out.ravel())
        self._temp_images.append(img)
        return img


def normal_from_height(height, texel_size, distance, strength=1.0, directx=False):
    """Tangent-space normal map (RGB 0..1) from a periodic height map.

    Matches what Blender's Bump node does on a flat surface:
    n = normalize(-distance * dh/dx, -distance * dh/dy, 1), blended by strength.
    Differences wrap around the edges, so the result tiles seamlessly.
    """
    height = np.asarray(height, dtype=np.float32)
    gx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) / (2.0 * texel_size)
    gy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) / (2.0 * texel_size)
    height = height.astype(np.float32, copy=False)
    n = np.stack([-distance * gx, -distance * gy, np.ones_like(height)], axis=-1).astype(np.float32)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    if strength != 1.0:
        n = strength * n + (1.0 - strength) * np.array([0.0, 0.0, 1.0], dtype=np.float32)
        n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-8)
    if directx:
        n[..., 1] *= -1.0
    return n * 0.5 + 0.5


def build_tiled_material(name, images, tile_size, directx=False):
    """Material using the seamless textures on the object's UVs (Mapping node = repeat count)."""
    mat = build_baked_material(name, images, '', directx, tag_value='TILE')
    tree = mat.node_tree
    uv = next(n for n in tree.nodes if n.bl_idname == 'ShaderNodeUVMap')
    coord = tree.nodes.new('ShaderNodeTexCoord')
    coord.location = (uv.location.x - 200, uv.location.y)
    mapping = tree.nodes.new('ShaderNodeMapping')
    mapping.label = 'Repeat (Scale)'
    mapping.location = uv.location
    tree.links.new(coord.outputs['UV'], mapping.inputs['Vector'])
    for node in tree.nodes:
        if node.bl_idname == 'ShaderNodeTexImage':
            tree.links.new(mapping.outputs['Vector'], node.inputs['Vector'])
    tree.nodes.remove(uv)
    mat['bpm_tile_size'] = float(tile_size)
    return mat


def run_to_end(job):
    """Run a job synchronously (command line / background mode)."""
    job.check()
    for status in job.run():
        print('BPM:', status, flush=True)
    return job
