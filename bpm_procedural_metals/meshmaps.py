# SPDX-License-Identifier: GPL-3.0-or-later
"""Mesh maps: a one-time analysis of each object's shape, like the curvature and
ambient occlusion maps of texture painting programs.

Live edge and crevice detection (Bevel and Ambient Occlusion nodes) is noisy,
only works in Cycles and cannot tell a 2 mm chamfer from a 2 cm one.  The
analysis bakes, per object:

* convex:    1 on outer edges, falling linearly to 0 at the "edge reach",
* concave:   the same for inner corners and creases,
* occlusion: how enclosed the surface is (0 open .. 1 enclosed), including
  other objects nearby when wanted.

Convex and concave come from ambient occlusion with a known ray length: next to
a wall, the share of blocked rays only depends on (distance / ray length), so it
can be turned back into the distance to the edge.  The materials then draw
edge wear and grime as bands of an exact width in meters, solid in every
corner, and the same in EEVEE (Material Preview) as in Cycles.

Making it hold up on real meshes:

* Thin parts (plates, panels, fins thinner than the edge reach) block fewer
  rays than a thick block, which would make their edge bands too wide.  The
  occlusion of the flat surface around each edge tells the thickness, and
  tables measured on test plates of known thickness turn (thickness, value)
  back into the distance.  Edges are measured twice (ambient occlusion from
  inside, and the Bevel node); the more trustworthy of the two wins.
* Smooth-shaded low-poly meshes: the rays leave along a normal blended
  towards the true face normal where the shading bends far from it, so a
  smooth cube does not read as a crease everywhere.
* Inside-out meshes (normals pointing in) are measured from the other side;
  mixed normals, modifiers that repeat the UVs (Array, Mirror, ...) and edge
  reaches only a few pixels wide in the maps are reported.
* The maps are marked out of date when the mesh or its modifiers change.

Storage (survives saving, works with materials shared by many objects):

* UV map "BPM_Maps" on the mesh: its own Smart UV layout, moved into the
  mesh's tile of the shared UDIM image "BPM Mesh Maps".  Tile 1001 stays empty:
  meshes without maps read zeros there.
* Image channels: R = convex, G = concave, B = occlusion.
* Mesh custom properties, read by the materials with an Attribute node (Object
  type): bpm_maps (1 = has maps), bpm_maps_edge / bpm_maps_cavity (reach of the
  R / G channels in object units).
"""

import os
import re
import shutil
import tempfile
import zlib

import bpy
import numpy as np
from mathutils import Vector

from . import bake as B
from . import library as L

IMAGE_NAME = 'BPM Mesh Maps'
IMAGE_TAG = 'bpm_mesh_maps'
UV_NAME = B.MAPS_UV_NAME  # 'BPM_Maps'
FLAG = 'bpm_maps'
TILE = 'bpm_maps_tile'
EDGE = 'bpm_maps_edge'
CAVITY = 'bpm_maps_cavity'
OCCLUSION = 'bpm_maps_occlusion'
SIGNATURE = 'bpm_maps_signature'
RESOLUTION = 'bpm_maps_resolution'
PROPS = (FLAG, TILE, EDGE, CAVITY, OCCLUSION, SIGNATURE, RESOLUTION)
FIRST_TILE = 1002  # 1001 is the empty tile

QUALITY = {
    # quality: (Cycles samples, rays per sample)
    'FAST': (8, 8),
    'GOOD': (16, 16),
    'BEST': (32, 32),
}
# On the GPU every probe casts at most this many rays per sample (and the samples go up to
# keep the same number of rays): each GPU job stays short.  Long ones can be killed as "hung"
# by the graphics driver (Windows: about 2 s, Linux i915: about 4 s): "device lost".
GPU_RAYS = 4
# reach limits in meters: (edge, cavity, occlusion)
REACH_MIN = (0.002, 0.004, 0.01)
REACH_MAX = (0.2, 0.4, 2.0)
DILATE = 8  # pixels the maps are extended around the UV islands


class MapsSettings:
    """Plain settings container (filled from the UI or the command line)."""

    def __init__(self, **kwargs):
        self.resolution = 1024
        self.quality = 'GOOD'
        self.edge_reach = 0.05       # share of the object's size
        self.cavity_reach = 0.15
        self.occlusion_reach = 0.25
        self.other_objects = True    # other objects nearby darken the occlusion and add creases
        self.device = 'AUTO'
        for key, value in kwargs.items():
            if not hasattr(self, key):
                raise TypeError('Unknown mesh maps setting: %s' % key)
            setattr(self, key, value)

    @classmethod
    def from_props(cls, props):
        return cls(resolution=int(props.maps_resolution), quality=props.maps_quality,
                   edge_reach=props.maps_edge_reach / 100.0, cavity_reach=props.maps_cavity_reach / 100.0,
                   occlusion_reach=props.maps_occlusion_reach / 100.0, other_objects=props.maps_other_objects,
                   device=props.device)

    @property
    def samples(self):
        return QUALITY.get(self.quality, QUALITY['GOOD'])

    def samples_on(self, device):
        """(Cycles samples, rays per sample) on 'CPU' or 'GPU': the same rays in total."""
        samples, rays = self.samples
        if device == 'GPU' and rays > GPU_RAYS:
            return samples * rays // GPU_RAYS, GPU_RAYS
        return samples, rays

    @property
    def uv_margin(self):
        """Room around the UV islands: blurring and extending the maps must not mix islands."""
        size = max(int(self.resolution), 1)
        return max(6, size // 128) / size


# ----------------------------------------------------------------- per mesh
def object_scale(obj):
    """Average scale of an object (object units -> meters)."""
    m = obj.matrix_world.to_3x3()
    return max(sum(m.col[i].length for i in range(3)) / 3.0, 1e-9)


def reaches(obj, settings):
    """(edge, cavity, occlusion) ray lengths in meters for `obj`."""
    dims = sorted(obj.dimensions)
    size = dims[1] if dims[1] > 1e-6 else dims[2]
    shares = (settings.edge_reach, settings.cavity_reach, settings.occlusion_reach)
    return tuple(min(max(share * size, lo), hi) for share, lo, hi in zip(shares, REACH_MIN, REACH_MAX))


def signature(mesh):
    """Short text that changes when the mesh is edited (counts + weighted sum of the coordinates)."""
    n = len(mesh.vertices)
    co = np.empty(n * 3, dtype=np.float32)
    mesh.vertices.foreach_get('co', co)
    weights = 1.0 + (np.arange(n * 3) % 13)
    return '%d/%d/%.6e' % (n, len(mesh.polygons), float(np.dot(co.astype(np.float64), weights)))


_UI_PROPS = {'name', 'show_viewport', 'show_render', 'show_in_editmode', 'show_on_cage', 'show_expanded',
             'is_active', 'is_override_data_editable', 'use_pin_to_last', 'persistent_uid', 'use_apply_on_spline',
             'execution_time'}


def modifier_signature(obj):
    """Text that changes when the modifiers that shape the analyzed surface change ('' without any).

    The analysis measures the evaluated mesh (as shown in the viewport), so an Array count or a
    Solidify thickness changes the maps as much as editing the mesh does.  The add-on's own
    displacement preview is left out: it only shows what the materials already draw."""
    parts = []
    for mod in getattr(obj, 'modifiers', ()):
        if mod.name == L.DISPLACE_MODIFIER or not mod.show_viewport:
            continue
        values = [mod.type]
        for prop in mod.bl_rna.properties:
            key = prop.identifier
            if key in _UI_PROPS or key == 'rna_type' or prop.is_readonly:
                continue
            try:
                value = getattr(mod, key)
            except AttributeError:
                continue
            if prop.type == 'POINTER':
                value = getattr(value, 'name', None)
            elif prop.type == 'COLLECTION':
                continue
            elif getattr(prop, 'is_array', False):
                value = tuple(value)
            if isinstance(value, float):
                value = round(value, 6)
            values.append('%s=%r' % (key, value))
        try:
            keys = sorted(mod.keys())  # Geometry Nodes inputs
        except TypeError:  # other modifiers have no custom properties
            keys = ()
        for key in keys:
            value = mod[key]
            if hasattr(value, 'to_list'):
                value = value.to_list()
            values.append('%s=%r' % (key, getattr(value, 'name', value)))
        parts.append(';'.join(values))
    if not parts:
        return ''
    return '%08x' % (zlib.crc32('|'.join(parts).encode('utf-8')) & 0xffffffff)


def full_signature(obj):
    """The mesh's signature, plus its modifiers' when it has any (older files keep matching)."""
    text = signature(obj.data)
    extra = modifier_signature(obj)
    return text + '/m' + extra if extra else text


def has_maps(mesh):
    return mesh is not None and bool(mesh.get(FLAG)) and UV_NAME in mesh.uv_layers


def status(obj):
    """'NONE', 'OK', 'OUTDATED' (mesh edited since) or 'BROKEN' (maps lost) for an object."""
    if obj is None or obj.type != 'MESH':
        return 'NONE'
    mesh = obj.data
    if not mesh.get(FLAG):
        return 'NONE'
    img = find_image()
    if UV_NAME not in mesh.uv_layers or img is None or int(mesh.get(TILE, 0)) not in tile_numbers(img):
        return 'BROKEN'
    current = full_signature(obj)
    if mesh.get(SIGNATURE) != current:
        # another object using the same mesh with other modifiers: it uses the maps made for
        # the first one (said when they were made), until either changes
        geometry = str(mesh.get(SIGNATURE, '')).split('/m')[0]
        if obj.get(SIGNATURE) != current or geometry != signature(mesh):
            return 'OUTDATED'
    return 'OK'


def tile_offset(tile):
    index = int(tile) - 1001
    return float(index % 10), float(index // 10)


def clear_mesh(mesh):
    """Forget a mesh's maps (properties and UV map); its tile is dropped at the next image rebuild."""
    for key in PROPS:
        if key in mesh:
            del mesh[key]
    layer = mesh.uv_layers.get(UV_NAME)
    if layer is not None:
        mesh.uv_layers.remove(layer)


# --------------------------------------------------------------- the image
def _non_color(img):
    try:
        img.colorspace_settings.name = 'Non-Color'
    except TypeError:
        img.colorspace_settings.is_data = True


def find_image():
    for img in bpy.data.images:
        if img.get(IMAGE_TAG) and img.library is None:
            return img
    return None


def ensure_image():
    """The shared UDIM image of all mesh maps (an empty placeholder until something is analyzed)."""
    img = find_image()
    if img is None:
        img = bpy.data.images.new(IMAGE_NAME, 4, 4, alpha=False, float_buffer=True, tiled=True)
        img.generated_color = (0.0, 0.0, 0.0, 1.0)
        img[IMAGE_TAG] = True
        img.use_fake_user = True  # keep the maps while no material uses them for a moment
        _non_color(img)
    return img


def tile_numbers(img):
    return {t.number for t in img.tiles}


_TILE_RE = re.compile(r'[._](\d{4}|<UDIM>)(\.[^./\\]+)$')


def _tile_files(img):
    """{tile number: file contents} of the image's tiles that have pixels (packed or on disk)."""
    found = {}
    if img.source != 'TILED' or not img.filepath:
        return found  # generated placeholder: no pixels worth keeping
    for pf in img.packed_files:
        number = getattr(pf, 'tile_number', 0)
        if not number:
            match = _TILE_RE.search(pf.filepath)
            number = int(match.group(1)) if match and match.group(1).isdigit() else 0
        if number:
            found[number] = bytes(pf.packed_file.data)
    if found:
        return found
    path = bpy.path.abspath(img.filepath)
    for tile in img.tiles:
        tile_path = _TILE_RE.sub(lambda m: '.%d%s' % (tile.number, m.group(2)), path)
        if os.path.isfile(tile_path):
            with open(tile_path, 'rb') as f:
                found[tile.number] = f.read()
    return found


def _write_png(path, pixels, width, height):
    tmp = bpy.data.images.new('BPM tmp tile', width, height, alpha=False, float_buffer=True, is_data=True)
    try:
        _non_color(tmp)
        tmp.pixels.foreach_set(np.ascontiguousarray(pixels, dtype=np.float32).ravel())
        tmp.filepath_raw = path
        tmp.file_format = 'PNG'  # float pixels are saved as 16-bit PNG
        tmp.save()
    finally:
        bpy.data.images.remove(tmp)


def rebuild_image(new_tiles, keep):
    """Rebuild the UDIM image with the tiles in `keep` plus `new_tiles` {number: (pixels, size)}.

    Blender cannot write pixels into tiles directly: every tile is saved as a file, the
    image is loaded from them and packed into the .blend file (the files are deleted).
    """
    img = ensure_image()
    old = _tile_files(img)
    folder = tempfile.mkdtemp(prefix='bpm_maps_')
    try:
        def path(number):
            return os.path.join(folder, 'BPM_Mesh_Maps.%d.png' % number)
        wanted = {1001}
        for number, data in old.items():
            if number in keep and number not in new_tiles:
                with open(path(number), 'wb') as f:
                    f.write(data)
                wanted.add(number)
        for number, (pixels, size) in new_tiles.items():
            _write_png(path(number), pixels, size, size)
            wanted.add(number)
        if not os.path.exists(path(1001)):
            _write_png(path(1001), np.zeros(4 * 4 * 4, dtype=np.float32), 4, 4)
        if len(wanted) == 1:  # nothing analyzed any more: back to the light placeholder
            _reset_placeholder(img)
            return img
        if img.packed_files:
            img.unpack(method='REMOVE')
        img.source = 'FILE'
        img.filepath = path(1001)
        img.source = 'TILED'
        for tile in list(img.tiles):
            if tile.number not in wanted:
                img.tiles.remove(tile)
        present = tile_numbers(img)
        for number in sorted(wanted - present):
            img.tiles.new(tile_number=number)
        _non_color(img)
        img.reload()
        img.pack()
        _non_color(img)
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    return img


def _reset_placeholder(img):
    if img.packed_files:
        img.unpack(method='REMOVE')
    for tile in list(img.tiles):
        if tile.number != 1001:
            img.tiles.remove(tile)
    img.source = 'GENERATED'
    img.filepath = ''
    img.generated_width = img.generated_height = 4
    img.generated_color = (0.0, 0.0, 0.0, 1.0)
    img.source = 'TILED'
    _non_color(img)


def referenced_tiles():
    return {int(m[TILE]) for m in bpy.data.meshes if m.get(FLAG) and m.get(TILE)}


def remove(meshes):
    """Remove the maps of `meshes`; returns how many had maps."""
    count = 0
    for mesh in meshes:
        if mesh.get(FLAG) or UV_NAME in mesh.uv_layers:
            count += 1
        clear_mesh(mesh)
    if find_image() is not None:
        rebuild_image({}, referenced_tiles())
    return count


# -------------------------------------------------------------- processing
_T = np.linspace(0.0, 1.0, 4097)
# Share of blocked rays next to a wall, at distance t (in ray lengths) from it: the part
# of the cosine-weighted hemisphere whose rays hit the wall within the ray length.
_WALL = (np.arccos(_T) - _T * np.sqrt(1.0 - _T * _T)) / np.pi
# Calibration, measured on boxes and plates of thickness t with 90 degree edges (Cycles,
# 1024 px maps, after the blur): rows = t in edge reaches (the last row: thick objects),
# columns = distance to the edge in edge reaches.
_CAL_T = np.array([0.05, 0.1, 0.2, 0.3, 0.45, 0.6, 0.8, 1.0])
_CAL_D = np.array([0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1,
                   1.2, 1.3, 2.0])
# Bevel node (radius 2 edge reaches): normal deviation 1 - dot(bevel normal, normal)
_CAL_DEV = np.array([
    [0.2439, 0.2450, 0.2479, 0.2488, 0.2467, 0.2437, 0.2422, 0.2472, 0.2507, 0.2506, 0.2419, 0.2385, 0.2364,
     0.2141, 0.1899, 0.1542, 0.1293, 0.0955, 0.0684, 0.0466, 0.0000],
    [0.4274, 0.4287, 0.4311, 0.4319, 0.4290, 0.4232, 0.4107, 0.4045, 0.3968, 0.3855, 0.3477, 0.3291, 0.3153,
     0.2688, 0.2253, 0.1656, 0.1344, 0.0940, 0.0690, 0.0431, 0.0000],
    [0.5751, 0.5719, 0.5566, 0.5417, 0.5240, 0.5036, 0.4627, 0.4379, 0.4127, 0.3872, 0.3396, 0.3128, 0.2867,
     0.2227, 0.1825, 0.1300, 0.1003, 0.0667, 0.0470, 0.0229, 0.0000],
    [0.5710, 0.5632, 0.5364, 0.5118, 0.4864, 0.4609, 0.4147, 0.3896, 0.3644, 0.3383, 0.2836, 0.2551, 0.2302,
     0.1710, 0.1347, 0.0890, 0.0643, 0.0388, 0.0261, 0.0117, 0.0000],
    [0.5008, 0.4913, 0.4619, 0.4358, 0.4090, 0.3820, 0.3331, 0.3066, 0.2807, 0.2553, 0.2090, 0.1847, 0.1617,
     0.1088, 0.0811, 0.0514, 0.0350, 0.0197, 0.0133, 0.0054, 0.0000],
    [0.4417, 0.4328, 0.4027, 0.3761, 0.3498, 0.3237, 0.2768, 0.2513, 0.2270, 0.2038, 0.1624, 0.1411, 0.1212,
     0.0804, 0.0588, 0.0353, 0.0230, 0.0124, 0.0078, 0.0031, 0.0000],
    [0.3901, 0.3810, 0.3522, 0.3259, 0.2992, 0.2735, 0.2284, 0.2045, 0.1821, 0.1608, 0.1244, 0.1066, 0.0903,
     0.0576, 0.0408, 0.0234, 0.0152, 0.0079, 0.0047, 0.0018, 0.0000],
    [0.2985, 0.2915, 0.2750, 0.2460, 0.2205, 0.1891, 0.1721, 0.1433, 0.1225, 0.1032, 0.0823, 0.0716, 0.0554,
     0.0356, 0.0222, 0.0150, 0.0084, 0.0050, 0.0025, 0.0011, 0.0000],
])
# ambient occlusion inside the object (ray length 1 edge reach): share of blocked rays
_CAL_OCC = np.array([
    [0.9990, 0.9990, 0.9988, 0.9988, 0.9987, 0.9986, 0.9984, 0.9983, 0.9983, 0.9983, 0.9986, 0.9986, 0.9985,
     0.9981, 0.9981, 0.9977, 0.9975, 0.9974, 0.9975, 0.9976, 0.9977],
    [0.9962, 0.9961, 0.9959, 0.9957, 0.9954, 0.9951, 0.9946, 0.9944, 0.9943, 0.9941, 0.9939, 0.9937, 0.9934,
     0.9932, 0.9921, 0.9909, 0.9903, 0.9902, 0.9897, 0.9898, 0.9901],
    [0.9838, 0.9835, 0.9830, 0.9826, 0.9822, 0.9816, 0.9800, 0.9790, 0.9780, 0.9771, 0.9763, 0.9757, 0.9748,
     0.9710, 0.9683, 0.9645, 0.9612, 0.9601, 0.9599, 0.9604, 0.9598],
    [0.9641, 0.9635, 0.9622, 0.9609, 0.9594, 0.9576, 0.9548, 0.9532, 0.9514, 0.9492, 0.9467, 0.9446, 0.9418,
     0.9353, 0.9297, 0.9197, 0.9122, 0.9102, 0.9097, 0.9100, 0.9104],
    [0.9185, 0.9171, 0.9137, 0.9105, 0.9072, 0.9037, 0.8983, 0.8946, 0.8901, 0.8850, 0.8767, 0.8710, 0.8646,
     0.8503, 0.8378, 0.8128, 0.7994, 0.7970, 0.7970, 0.7968, 0.7998],
    [0.8540, 0.8512, 0.8448, 0.8387, 0.8321, 0.8252, 0.8137, 0.8064, 0.7988, 0.7904, 0.7752, 0.7643, 0.7525,
     0.7234, 0.6967, 0.6568, 0.6425, 0.6401, 0.6392, 0.6400, 0.6396],
    [0.7333, 0.7281, 0.7152, 0.7033, 0.6909, 0.6774, 0.6543, 0.6393, 0.6229, 0.6049, 0.5718, 0.5482, 0.5222,
     0.4586, 0.4191, 0.3775, 0.3637, 0.3596, 0.3593, 0.3601, 0.3596],
    [0.5475, 0.5381, 0.5161, 0.4801, 0.4475, 0.4066, 0.3814, 0.3390, 0.3050, 0.2712, 0.2299, 0.2043, 0.1633,
     0.1040, 0.0543, 0.0262, 0.0047, 0.0003, 0.0000, 0.0000, 0.0000],
])
# both fall with the distance (measurement noise aside); the occlusion as the share of its
# rise above the flat surface's value, which is measured per pixel
_CAL_DEV = np.minimum.accumulate(_CAL_DEV, axis=1)
_CAL_EXCESS = np.minimum.accumulate(
    (_CAL_OCC - _CAL_OCC[:, -1:]) / (_CAL_OCC[:, :1] - _CAL_OCC[:, -1:]), axis=1)


def wall_distance(occlusion):
    """Distance to the wall (in ray lengths, 0..1) from the share of blocked rays next to it."""
    return np.interp(occlusion, _WALL[::-1], _T[::-1])


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _conv1d(a, axis):
    """[1 4 6 4 1] / 16 along `axis` (zero outside)."""
    pad = [(0, 0)] * a.ndim
    pad[axis] = (2, 2)
    p = np.pad(a, pad)
    n = a.shape[axis]

    def part(k):
        sl = [slice(None)] * a.ndim
        sl[axis] = slice(k, k + n)
        return p[tuple(sl)]
    return (part(0) + part(4) + 4.0 * (part(1) + part(3)) + 6.0 * part(2)) * (1.0 / 16.0)


def blur(values, covered):
    """Soften noise: average of the covered pixels nearby (other UV islands are too far to mix in)."""
    w = covered.astype(np.float32)
    num = values * w[..., None]
    for axis in (0, 1):
        num = _conv1d(num, axis)
        w = _conv1d(w, axis)
    out = np.where(w[..., None] > 1e-6, num / np.maximum(w, 1e-6)[..., None], 0.0)
    return out * covered[..., None]


def dilate(values, covered, steps):
    """Extend the islands by `steps` pixels (texture filtering reads a little past their border)."""
    values = values.copy()
    covered = covered.copy()
    h, w = covered.shape
    for _ in range(steps):
        pv = np.pad(values * covered[..., None], ((1, 1), (1, 1), (0, 0)))
        pc = np.pad(covered.astype(np.float32), 1)
        total = np.zeros_like(values)
        count = np.zeros((h, w), dtype=np.float32)
        for dy in (0, 1, 2):
            for dx in (0, 1, 2):
                if dy == 1 and dx == 1:
                    continue
                total += pv[dy:dy + h, dx:dx + w]
                count += pc[dy:dy + h, dx:dx + w]
        grow = (~covered) & (count > 0)
        if not grow.any():
            break
        values[grow] = total[grow] / count[grow][:, None]
        covered = covered | grow
    return values


def _calibrated_distance(table, t, value):
    """Distance to the edge (edge reaches) where the row of `table` for thickness `t` has `value`."""
    pos = np.interp(t, _CAL_T, np.arange(len(_CAL_T), dtype=np.float64))
    lo = np.floor(pos).astype(int)
    frac = pos - lo
    out = np.zeros_like(value)
    for i, row in enumerate(table):
        weight = np.where(lo == i, 1.0 - frac, 0.0) + np.where(lo + 1 == i, frac, 0.0)
        use = weight > 0.0
        if use.any():
            out[use] += weight[use] * np.interp(value[use], row[::-1], _CAL_D[::-1])
    return out


def _block_min(values, f):
    h, w = values.shape
    big = np.full((-(-h // f) * f, -(-w // f) * f), np.inf, dtype=np.float32)
    big[:h, :w] = values
    return big.reshape(big.shape[0] // f, f, big.shape[1] // f, f).min(axis=(1, 3))


def background(values, covered, radius):
    """Lowest value within about `radius` pixels on the same UV island: the value of the flat
    surface next to the edges (worked out on smaller pixels when the radius is large)."""
    f = int(max(1, min(radius / 6.0, 8)))
    small = _block_min(np.where(covered, values, np.inf).astype(np.float32), f)
    inside = np.isfinite(small)
    h, w = small.shape
    for _ in range(int(np.ceil(radius / f))):
        p = np.pad(small, 1, constant_values=np.inf)
        low = small.copy()
        for dy in (0, 1, 2):
            for dx in (0, 1, 2):
                low = np.minimum(low, p[dy:dy + h, dx:dx + w])
        small = np.where(inside, low, np.inf)
    full = np.repeat(np.repeat(small, f, axis=0), f, axis=1)[:values.shape[0], :values.shape[1]]
    full = np.where(covered & np.isfinite(full), full, 0.0).astype(np.float32)
    for _ in range(max(1, f // 2)):  # no blocky steps
        full = blur(full[..., None], covered)[..., 0]
    return full


def process(pass_a, pass_b, size, edge_px=16.0):
    """Turn the two baked passes into the map pixels (size * size * 4 floats).

    pass_a: ambient occlusion inside (R), outside at the cavity reach (G), outside at the
    occlusion reach (B); pass_b: Bevel normal deviation (R).  Alpha = baked pixel.
    edge_px: the edge reach in pixels of the maps.
    """
    a = pass_a.reshape(size, size, 4)
    b = pass_b.reshape(size, size, 4)
    covered = a[..., 3] > 0.5
    raw = blur(np.concatenate([a[..., :3], b[..., :1]], axis=-1), covered)
    occ_in, occ_cav, occ_far = 1.0 - raw[..., 0], 1.0 - raw[..., 1], 1.0 - raw[..., 2]
    dev = raw[..., 3]
    convex = np.zeros((size, size), dtype=np.float32)
    if covered.any():
        # Thickness: inside the object, rays shorter than the edge reach only hit the back of
        # thin parts: on a flat plate of thickness t (in edge reaches) 1 - t^2 of them.
        flat = np.clip(background(occ_in, covered, 1.25 * max(edge_px, 1.0)), 0.0, 0.9975)
        sel = covered
        t = np.sqrt(1.0 - flat[sel])
        # 1) inside occlusion rising near the edges (walls of the object), relative to the flat
        #    surface: reliable unless the part is so thin that nearly every ray is blocked anyway
        top = np.interp(t, _CAL_T, _CAL_OCC[:, 0])
        excess = np.clip((occ_in[sel] - flat[sel]) / np.maximum(top - flat[sel], 1e-4), 0.0, 1.0)
        by_ao = np.clip(1.0 - _calibrated_distance(_CAL_EXCESS, t, excess), 0.0, 1.0)
        w_ao = smoothstep(0.25, 0.45, t)
        # 2) the Bevel node's bent normal: works on thin plates too, but inner corners bend it as
        #    well, and smooth shading hides edges from it
        by_bevel = np.clip(1.0 - _calibrated_distance(_CAL_DEV, t, dev[sel]), 0.0, 1.0)
        w_bevel = 1.0 - smoothstep(0.05, 0.25, occ_cav[sel])
        convex[sel] = np.maximum(w_ao * by_ao, w_bevel * by_bevel)
    concave = 1.0 - wall_distance(occ_cav)
    maps = np.stack([convex, concave, np.clip(occ_far, 0.0, 1.0)], axis=-1) * covered[..., None]
    maps = dilate(maps.astype(np.float32), covered, DILATE)
    out = np.ones((size, size, 4), dtype=np.float32)
    out[..., :3] = maps
    return out


# ---------------------------------------------------------------- analysis
def _pass_material(name, image):
    mat = bpy.data.materials.new(name)
    mat['bpm_analysis'] = True
    tree = L.ensure_node_tree(mat)
    tree.nodes.clear()
    out = tree.nodes.new('ShaderNodeOutputMaterial')
    out.target = 'ALL'
    em = tree.nodes.new('ShaderNodeEmission')
    em.inputs['Strength'].default_value = 1.0
    tree.links.new(em.outputs['Emission'], out.inputs['Surface'])
    target = tree.nodes.new('ShaderNodeTexImage')
    target.image = image
    tree.nodes.active = target
    return mat, tree, em


def _vector_math(tree, operation, a, b=None):
    node = tree.nodes.new('ShaderNodeVectorMath')
    node.operation = operation
    tree.links.new(a, node.inputs[0])
    if b is not None:
        tree.links.new(b, node.inputs[1])
    return node


def probe_normal(tree, sign=1.0):
    """The direction the probes look in: the shading normal, bent to the face's true normal
    where smooth shading tilts it more than about 20 degrees (a smooth-shaded low-poly cube
    would otherwise "see" its own faces: crevices everywhere, edges half as wide).  Mild
    smoothing, like the facets of a low-poly cylinder, stays round.  `sign` -1 looks the
    other way, for meshes whose faces all point inward."""
    geo = tree.nodes.new('ShaderNodeNewGeometry')
    shading, true = geo.outputs['Normal'], geo.outputs['True Normal']
    cos = _vector_math(tree, 'DOT_PRODUCT', shading, true)
    bend = tree.nodes.new('ShaderNodeMapRange')
    bend.interpolation_type = 'SMOOTHSTEP'
    bend.inputs['From Min'].default_value = 0.906  # cos 25 degrees: the true normal
    bend.inputs['From Max'].default_value = 0.966  # cos 15 degrees: the shading normal
    bend.inputs['To Min'].default_value = 1.0
    bend.inputs['To Max'].default_value = 0.0
    tree.links.new(cos.outputs['Value'], bend.inputs['Value'])
    diff = _vector_math(tree, 'SUBTRACT', true, shading)
    part = _vector_math(tree, 'SCALE', diff.outputs[0])
    tree.links.new(bend.outputs['Result'], part.inputs['Scale'])
    mixed = _vector_math(tree, 'ADD', shading, part.outputs[0])
    unit = _vector_math(tree, 'NORMALIZE', mixed.outputs[0])
    flip = _vector_math(tree, 'SCALE', unit.outputs[0])
    flip.inputs['Scale'].default_value = sign
    return flip.outputs[0]


def _ao(tree, normal, distance, samples, inside=False, only_local=True):
    ao = tree.nodes.new('ShaderNodeAmbientOcclusion')
    ao.samples = samples
    ao.inside = inside
    ao.only_local = only_local
    ao.inputs['Distance'].default_value = distance
    tree.links.new(normal, ao.inputs['Normal'])
    return ao.outputs['AO']


def occlusion_material(image, edge, cavity, far, samples, other_objects, sign=1.0):
    mat, tree, em = _pass_material('BPM Mesh Analysis', image)
    normal = probe_normal(tree, sign)
    combine = tree.nodes.new('ShaderNodeCombineColor')
    tree.links.new(_ao(tree, normal, edge, samples, inside=True), combine.inputs[0])
    tree.links.new(_ao(tree, normal, cavity, samples, only_local=not other_objects), combine.inputs[1])
    tree.links.new(_ao(tree, normal, far, samples, only_local=not other_objects), combine.inputs[2])
    tree.links.new(combine.outputs[0], em.inputs['Color'])
    return mat


def bevel_material(image, edge, samples, sign=1.0):
    mat, tree, em = _pass_material('BPM Mesh Analysis Edges', image)
    normal = probe_normal(tree, sign)
    bevel = tree.nodes.new('ShaderNodeBevel')
    bevel.samples = min(max(samples, 4), 16)
    bevel.inputs['Radius'].default_value = 2.0 * edge
    tree.links.new(normal, bevel.inputs['Normal'])
    dot = _vector_math(tree, 'DOT_PRODUCT', bevel.outputs['Normal'], normal)
    dev = tree.nodes.new('ShaderNodeMath')
    dev.operation = 'SUBTRACT'
    dev.inputs[0].default_value = 1.0
    tree.links.new(dot.outputs['Value'], dev.inputs[1])
    tree.links.new(dev.outputs[0], em.inputs['Color'])
    return mat


# ------------------------------------------------------------ mesh checks
def _triangles(mesh):
    """(loop indices (n, 3), vertex indices (n, 3)) of the mesh's triangles."""
    mesh.calc_loop_triangles()
    n = len(mesh.loop_triangles)
    loops = np.empty(n * 3, dtype=np.int64)
    verts = np.empty(n * 3, dtype=np.int64)
    mesh.loop_triangles.foreach_get('loops', loops)
    mesh.loop_triangles.foreach_get('vertices', verts)
    return loops.reshape(-1, 3), verts.reshape(-1, 3)


def _coordinates(mesh):
    co = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
    mesh.vertices.foreach_get('co', co)
    return co.reshape(-1, 3)


def areas(mesh, uv_name, matrix=None):
    """(surface area, UV area) of a mesh; the surface in world units if `matrix` is given.
    Overlapping UVs count every time."""
    loops, verts = _triangles(mesh)
    if not len(loops) or uv_name not in mesh.uv_layers:
        return 0.0, 0.0
    co = _coordinates(mesh)
    if matrix is not None:
        m = np.array(matrix)
        co = co @ m[:3, :3].T
    p = co[verts]
    surface = 0.5 * np.linalg.norm(np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), axis=1).sum()
    uv = np.empty(len(mesh.loops) * 2, dtype=np.float64)
    mesh.uv_layers[uv_name].data.foreach_get('uv', uv)
    q = uv.reshape(-1, 2)[loops]
    e1, e2 = q[:, 1] - q[:, 0], q[:, 2] - q[:, 0]
    return float(surface), float(0.5 * np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]).sum())


def orientation(mesh):
    """(share of the faces' shared edges where neighbors point opposite ways, inside-out
    measure: -1 every face points inward .. 1 every face points outward; 0 for open shapes)."""
    nl, ne = len(mesh.loops), len(mesh.edges)
    if not nl or not ne:
        return 0.0, 1.0
    lv = np.empty(nl, dtype=np.int64)
    le = np.empty(nl, dtype=np.int64)
    mesh.loops.foreach_get('vertex_index', lv)
    mesh.loops.foreach_get('edge_index', le)
    ev = np.empty(ne * 2, dtype=np.int64)
    mesh.edges.foreach_get('vertices', ev)
    forward = (lv == ev.reshape(-1, 2)[le, 0]).astype(np.float64)
    uses = np.bincount(le, minlength=ne)
    ahead = np.bincount(le, weights=forward, minlength=ne)
    shared = uses == 2  # an edge between two faces runs opposite ways in them
    flipped = float((ahead[shared] != 1).sum()) / max(int(shared.sum()), 1)
    _loops, verts = _triangles(mesh)
    co = _coordinates(mesh)
    p = co[verts] - co.mean(axis=0)
    volumes = np.einsum('ij,ij->i', p[:, 0], np.cross(p[:, 1], p[:, 2]))
    total = np.abs(volumes).sum()
    return flipped, float(volumes.sum() / total) if total > 0 else 1.0


_REPEATING = {'ARRAY': 'Array', 'MIRROR': 'Mirror', 'SOLIDIFY': 'Solidify', 'SCREW': 'Screw',
              'NODES': 'Geometry Nodes', 'PARTICLE_INSTANCE': 'Particle Instance'}


def check_mesh(context, obj):
    """Problems of an object for the analysis: (probe sign, [(level, text)])."""
    notes = []
    depsgraph = context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        flipped, outward = orientation(mesh)
        sign = 1.0
        if outward < -0.3:
            sign = -1.0
            notes.append(('INFO', '"%s": its faces point inward; it was analyzed as if they pointed outward. '
                          'Recalculate the normals (Edit Mode, Shift+N) to fix its shading too.' % obj.name))
        if flipped > 0.02:
            notes.append(('WARNING', '"%s": %d%% of its faces point the other way than their neighbors: edges '
                          'and corners are swapped there. Fix: Edit Mode, select all, Mesh > Normals > '
                          'Recalculate Outside (Shift+N).' % (obj.name, round(100 * flipped))))
        _surface, repeated = areas(mesh, UV_NAME)
    finally:
        evaluated.to_mesh_clear()
    _surface, own = areas(obj.data, UV_NAME)
    if own > 0 and repeated > 1.15 * own:
        kinds = sorted({_REPEATING[m.type] for m in obj.modifiers if m.show_viewport and m.type in _REPEATING})
        what = ('its %s modifier' % ' / '.join(kinds)) if kinds else 'a modifier'
        notes.append(('WARNING', '"%s": %s repeats faces with the same UVs, so the copies share one analysis '
                      '(their edges and corners mix). Apply the modifier (Ctrl+A) before analyzing for exact '
                      'maps.' % (obj.name, what)))
    return sign, notes


def texels_per_unit(obj, size):
    """Map pixels per meter on the object's surface (BPM_Maps UVs)."""
    surface, uv_area = areas(obj.data, UV_NAME, obj.matrix_world)
    if surface <= 0 or uv_area <= 0:
        return 0.0
    return size * float(np.sqrt(uv_area / surface))


def skip_reason(context, obj):
    if obj.type != 'MESH':
        return 'is not a mesh'
    if obj.library is not None or obj.data.library is not None:
        return 'is linked from another file'
    if len(obj.data.polygons) == 0:
        return 'has no faces'
    if obj.name not in context.view_layer.objects:
        return 'is not in the current view layer'
    if obj.hide_viewport:
        return 'is disabled in viewports (screen icon in the Outliner)'
    return None


OCCLUDERS = {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT', 'CURVES', 'POINTCLOUD', 'GPENCIL', 'GREASEPENCIL'}


def _world_box(obj):
    corners = np.array([tuple(obj.matrix_world @ Vector(c)) for c in obj.bound_box])
    return corners.min(axis=0), corners.max(axis=0)


def _seen_by(obj, other, low, high):
    """Could `other` darken the analysis of `obj` (whose box, grown by the reach, is low..high)?"""
    if other.instance_type == 'COLLECTION' or len(getattr(other, 'particle_systems', ())):
        return True  # what it puts in the scene is not in its own bounds
    if other.type not in OCCLUDERS:
        return False  # lights, cameras, volumes
    try:
        other_low, other_high = _world_box(other)
    except (AttributeError, TypeError, ValueError):
        return True
    return bool(np.all(other_low <= high) and np.all(other_high >= low))


def _hide_unseen(context, obj, reach, other_objects):
    """Hide from rendering what the analysis of `obj` cannot see: everything else without
    Include Other Objects, else what is beyond the reach.  Less to load onto the GPU (and less
    for the rays to search).  Returns the objects to show again."""
    if other_objects:
        low, high = _world_box(obj)
        low, high = low - reach, high + reach
    hidden = []
    for other in context.view_layer.objects:
        if other == obj or other.hide_render:
            continue
        if other_objects and _seen_by(obj, other, low, high):
            continue
        try:
            other.hide_render = True
        except (AttributeError, RuntimeError):  # linked from a library
            continue
        hidden.append(other)
    return hidden


def _show_again(hidden):
    for other in hidden:
        try:
            other.hide_render = False
        except (AttributeError, ReferenceError, RuntimeError):
            pass


def _bake(context, obj, image, reach, other_objects):
    """Bake the analysis material of `obj` into `image`.  Raises B.GpuFailure if the GPU failed
    (an error, or nothing baked: its pixels start transparent)."""
    on_gpu = context.scene.cycles.device == 'GPU'
    override = dict(active_object=obj, object=obj, selected_objects=[obj], selected_editable_objects=[obj])
    hidden = _hide_unseen(context, obj, reach, other_objects)
    try:
        with context.temp_override(**override):
            result = bpy.ops.object.bake(type='EMIT', margin=0, use_clear=False, use_selected_to_active=False,
                                         target='IMAGE_TEXTURES', save_mode='INTERNAL', uv_layer=UV_NAME)
    except RuntimeError as exc:
        detail = str(exc).strip().splitlines()[-1]
        if on_gpu and 'poll()' not in detail:
            raise B.GpuFailure('The GPU could not analyze "%s": %s' % (obj.name, detail), detail)
        raise B.BakeError('Blender could not analyze "%s": %s' % (obj.name, detail))
    finally:
        _show_again(hidden)
    if 'FINISHED' not in result:
        if on_gpu:
            raise B.GpuFailure('The GPU did not analyze "%s".' % obj.name, 'the bake was cancelled')
        raise B.BakeError('Analyzing "%s" was cancelled.' % obj.name)
    if on_gpu:
        px = B._pixels(image)
        if not px[:, 3].max() > 0.0 or not np.isfinite(px).all():
            raise B.GpuFailure('The GPU baked nothing for "%s".' % obj.name, 'it baked nothing')


class MapsJob(B.Job):
    """Analyze the shape of mesh objects (see the module docstring).  Runs like a bake job:
    a generator that yields a status text after every step."""

    STEPS = 3

    def __init__(self, context, objects, settings):
        super().__init__(context, settings)
        self.objects = []
        seen = set()
        for obj in objects:
            if obj is not None and obj.name not in seen:
                seen.add(obj.name)
                self.objects.append(obj)
        self.total_steps = max(1, len(self.objects) * self.STEPS)
        self.analyzed = []
        self.upgraded = 0
        self._new_tiles = {}   # tile number -> (pixels, size), written into the image at the end
        self._materials = []

    @property
    def baked(self):  # what the bake operators report after Esc
        return self.analyzed

    def check(self):
        B.check_cycles()
        if not self.objects:
            raise B.BakeError('Select the object(s) to analyze first.')
        if not any(skip_reason(self.context, o) is None for o in self.objects):
            reasons = '; '.join('%s %s' % (o.name, skip_reason(self.context, o)) for o in self.objects[:3])
            raise B.BakeError('Nothing can be analyzed: ' + reasons)

    def summary(self):
        count = len(self.analyzed)
        text = 'Mesh maps ready for %d object%s.' % (count, 's' * (count != 1))
        skipped = len(self.objects) - count
        if skipped:
            text += ' (%d skipped)' % skipped
        return text

    def run(self):
        context = self.context
        state = B._SceneState(context)
        errors = []
        try:
            device = self.device_for(self.settings.device)
            samples, rays = self.settings.samples_on(device)
            state.prepare(device, samples)
            skipped = {}
            for obj in self.objects:
                reason = skip_reason(context, obj)
                if reason:
                    skipped.setdefault(reason, []).append(obj.name)
            for reason, names in skipped.items():
                self.warn(B._skip_text(names, reason))
            done = {}  # mesh name -> object analyzed with it
            for index, obj in enumerate(self.objects):
                self.done_steps = index * self.STEPS
                if skip_reason(context, obj):
                    continue
                twin = done.get(obj.data.name)
                if twin is not None:
                    self.analyzed.append(obj.name)
                    obj[SIGNATURE] = full_signature(obj)
                    self.info('"%s" shares its mesh with "%s": it uses the same maps.' % (obj.name, twin))
                    continue
                yield 'Analyzing %s' % obj.name
                try:
                    try:
                        yield from self._analyze(obj, state, rays)
                    except B.GpuFailure as exc:
                        yield 'The GPU failed: analyzing %s on the CPU' % obj.name
                        samples, rays = self.settings.samples_on('CPU')
                        state.prepare('CPU', samples)
                        try:
                            yield from self._analyze(obj, state, rays)
                        except B.BakeError:
                            samples, rays = self.settings.samples_on(device)
                            state.prepare(device, samples)  # the CPU fails too: not the GPU's fault
                            raise
                        B.gpu_failed(exc.detail)
                        device = 'CPU'
                        self.warn(B.gpu_failure_text(obj.name, 'it was analyzed'))
                except B.BakeError as exc:
                    errors.append(str(exc))
                    self.warn(str(exc))
                else:
                    self.analyzed.append(obj.name)
                    done[obj.data.name] = obj.name
            self.done_steps = self.total_steps
            if errors and not self.analyzed:
                raise B.BakeError(errors[0])
        finally:
            try:
                self._commit()
            finally:
                self._drop_temp_images()
                for mat in self._materials:
                    try:
                        bpy.data.materials.remove(mat)
                    except ReferenceError:
                        pass
                self._materials = []
                state.restore()

    def _commit(self):
        """Write the finished tiles (also after Esc: those objects are done)."""
        if not self._new_tiles:
            return
        tiles, self._new_tiles = self._new_tiles, {}
        try:
            rebuild_image(tiles, referenced_tiles())
        except Exception:
            for mesh in bpy.data.meshes:
                if mesh.get(FLAG) and int(mesh.get(TILE, 0)) in tiles:
                    clear_mesh(mesh)
            raise
        names = set(self.analyzed)
        materials = set()
        for obj in self.objects:
            if obj.name in names:
                materials.update(slot.material for slot in obj.material_slots)
                # procedural materials kept while the baked ones are shown
                materials.update(entry.material for entry in getattr(obj, 'bpm_backup', ()))
        for mat in materials:
            self.upgraded += L.upgrade_groups(mat)

    def _pick_tile(self, mesh):
        """The mesh's own tile, or a free one if another mesh uses it too (a copy of the mesh)."""
        taken = set(self._new_tiles)
        for other in bpy.data.meshes:
            if other != mesh and other.get(FLAG) and other.get(TILE):
                taken.add(int(other[TILE]))
        current = int(mesh.get(TILE, 0) or 0)
        if current >= FIRST_TILE and current not in taken:
            return current
        tile = FIRST_TILE
        while tile in taken:
            tile += 1
        return tile

    def _analyze(self, obj, state, rays):
        s = self.settings
        context = self.context
        mesh = obj.data
        size = int(s.resolution)
        edge, cavity, far = reaches(obj, s)
        layers = mesh.uv_layers
        previous = layers.active.name if layers.active is not None else None
        render = next((layer.name for layer in layers if layer.active_render), None)
        old_uvs = B._uv_array(mesh, UV_NAME) if UV_NAME in layers else None
        added_uv = False
        if old_uvs is None:
            if len(layers) >= 8:
                raise B.BakeError('"%s" has too many UV maps (the maximum is 8). Delete one in '
                                  'Properties > Object Data > UV Maps.' % obj.name)
            if len(layers) == 0:
                # keep a UV map for the user in front: unwrapping in Edit Mode works on the
                # active one, which must not be the maps' own
                layers.new(name='UVMap')
                previous = render = 'UVMap'
                added_uv = True
            layers.new(name=UV_NAME, do_init=False)
        slots = [slot.material for slot in obj.material_slots]
        added_slot = False
        hidden = obj.hide_render
        finished = False
        try:
            obj.hide_render = False
            yield 'Unwrapping %s for its mesh maps' % obj.name
            state.select_only(obj)
            B.unwrap_and_pack(obj, UV_NAME, s.uv_margin)
            layers = mesh.uv_layers
            if previous is not None and previous in layers:
                layers.active = layers[previous]
            if render is not None and render in layers:
                layers[render].active_render = True
            self.done_steps += 1
            context.view_layer.update()
            sign, notes = check_mesh(context, obj)
            for level, text in notes:
                (self.warn if level == 'WARNING' else self.info)(text)
            edge_px = edge * texels_per_unit(obj, size)
            if 0.0 < edge_px < 2.5:
                self.warn('"%s": its edge reach (%.1f mm) is only %.1f pixels wide in its maps: the edges come out '
                          'blurry. Raise the Resolution (or the Edge Reach).' % (obj.name, edge * 1000.0, edge_px))

            images = []
            for label in ('Occlusion', 'Edges'):
                img = bpy.data.images.new('BPM_tmp_maps_' + label, size, size, alpha=True, float_buffer=True,
                                          is_data=True)
                img.pixels.foreach_set(np.zeros(size * size * 4, dtype=np.float32))  # alpha 0 = not baked
                self._temp_images.append(img)
                images.append(img)
            occ_mat = occlusion_material(images[0], edge, cavity, far, rays, s.other_objects, sign)
            edge_mat = bevel_material(images[1], edge, rays, sign)
            self._materials += [occ_mat, edge_mat]
            if not obj.material_slots:
                mesh.materials.append(None)
                added_slot = True
            for mat, image, label in ((occ_mat, images[0], 'corners and occlusion'),
                                      (edge_mat, images[1], 'sharp edges')):
                yield 'Measuring %s of %s' % (label, obj.name)
                for slot in obj.material_slots:
                    slot.material = mat
                _bake(context, obj, image, far + edge, s.other_objects)
                self.done_steps += 0.5
            yield 'Processing the mesh maps of %s' % obj.name
            pixels = process(B._pixels(images[0]), B._pixels(images[1]), size, edge_px or 16.0)
            self._drop_temp_images()

            tile = self._pick_tile(mesh)
            du, dv = tile_offset(tile)
            uvs = B._uv_array(mesh, UV_NAME).reshape(-1, 2)
            uvs[:, 0] += du
            uvs[:, 1] += dv
            mesh.uv_layers[UV_NAME].data.foreach_set('uv', uvs.ravel())
            scale = object_scale(obj)
            mesh[FLAG] = 1.0
            mesh[TILE] = tile
            mesh[EDGE] = edge / scale
            mesh[CAVITY] = cavity / scale
            mesh[OCCLUSION] = far / scale
            mesh[SIGNATURE] = obj[SIGNATURE] = full_signature(obj)
            mesh[RESOLUTION] = size
            self._new_tiles[tile] = (pixels, size)
            self.done_steps += 1
            finished = True
        finally:
            if added_slot:
                mesh.materials.clear()  # it had none; pop() would leave the object's slot behind
            else:
                for slot, mat in zip(obj.material_slots, slots):
                    slot.material = mat
            obj.hide_render = hidden
            if not finished:
                layers = mesh.uv_layers
                if old_uvs is None:
                    if UV_NAME in layers:
                        layers.remove(layers[UV_NAME])
                    if added_uv and 'UVMap' in layers:
                        layers.remove(layers['UVMap'])
                        previous = None
                elif UV_NAME in layers:
                    layers[UV_NAME].data.foreach_set('uv', old_uvs)
                if previous is not None and previous in layers:
                    layers.active = layers[previous]


def analyze(context, objects, settings):
    """Run a MapsJob to the end (command line, tests)."""
    return B.run_to_end(MapsJob(context, objects, settings))


def needs_analysis(obj):
    return status(obj) != 'OK'


class AnalyzeThenBakeJob:
    """Auto Texture with "Analyze Shape First": mesh maps for the objects that need them, then the bake."""

    def __init__(self, maps_job, bake_job):
        self.maps_job = maps_job
        self.bake_job = bake_job
        self._maps_ok = True

    @property
    def total_steps(self):
        return self.maps_job.total_steps + self.bake_job.total_steps

    @property
    def done_steps(self):
        return self.maps_job.done_steps + self.bake_job.done_steps

    @property
    def messages(self):
        return self.maps_job.messages + self.bake_job.messages

    @property
    def baked(self):
        return self.bake_job.baked

    @property
    def output_dir(self):
        return self.bake_job.output_dir

    def warnings(self):
        return self.maps_job.warnings() + self.bake_job.warnings()

    def summary(self):
        text = self.bake_job.summary()
        if self.maps_job.analyzed:
            text += ' Shape analyzed: %d object%s.' % (len(self.maps_job.analyzed),
                                                       's' * (len(self.maps_job.analyzed) != 1))
        return text

    def check(self):
        self.bake_job.check()
        try:
            self.maps_job.check()
        except B.BakeError:
            self._maps_ok = False  # nothing to analyze: just bake

    def run(self):
        if self._maps_ok:
            try:
                yield from self.maps_job.run()
            except B.BakeError as exc:  # bake anyway, with the live edge and cavity detection
                self.maps_job.warn('Shape analysis failed: %s' % exc)
        self.maps_job.done_steps = self.maps_job.total_steps
        yield from self.bake_job.run()


def analyze_then_bake(context, objects, bake_job, settings):
    """Wrap `bake_job` so the objects without up-to-date mesh maps are analyzed first."""
    todo = [o for o in objects if B.skip_reason(context, o) is None and skip_reason(context, o) is None
            and needs_analysis(o)]
    if not todo:
        return bake_job
    return AnalyzeThenBakeJob(MapsJob(context, todo, settings), bake_job)
