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

import bpy
import numpy as np

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
    if mesh.get(SIGNATURE) != signature(mesh):
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
# Bevel node: normal deviation (1 - dot) next to a 90 degree edge at distance s (in edge
# reaches) for a bevel radius of 2 edge reaches (measured).
_BEVEL_S = np.array([0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.1])
_BEVEL_DEV = np.array([0.29, 0.242, 0.143, 0.071, 0.031, 0.011, 0.003])


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


def process(pass_a, pass_b, size):
    """Turn the two baked passes into the map pixels (size * size * 4 floats).

    pass_a: ambient occlusion inside (R), outside at the cavity reach (G), outside at the
    occlusion reach (B); pass_b: Bevel normal deviation (R).  Alpha = baked pixel.
    """
    a = pass_a.reshape(size, size, 4)
    b = pass_b.reshape(size, size, 4)
    covered = a[..., 3] > 0.5
    raw = blur(np.concatenate([a[..., :3], b[..., :1]], axis=-1), covered)
    occ_in, occ_cav, occ_far = 1.0 - raw[..., 0], 1.0 - raw[..., 1], 1.0 - raw[..., 2]
    dev = raw[..., 3]
    # outer edges seen from inside the object; faded out where every ray is blocked (thin plates)
    convex_ao = (1.0 - wall_distance(occ_in)) * (1.0 - smoothstep(0.8, 0.93, occ_in))
    # sharp edges (also on thin plates): the Bevel node, except near inner corners where it
    # bends the normal too
    s = np.interp(dev, _BEVEL_DEV[::-1], _BEVEL_S[::-1])
    convex_bevel = np.clip(1.0 - s, 0.0, 1.0) * smoothstep(0.006, 0.02, dev) * (1.0 - smoothstep(0.05, 0.25, occ_cav))
    convex = np.maximum(convex_ao, convex_bevel)
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


def _ao(tree, distance, samples, inside=False, only_local=True):
    ao = tree.nodes.new('ShaderNodeAmbientOcclusion')
    ao.samples = samples
    ao.inside = inside
    ao.only_local = only_local
    ao.inputs['Distance'].default_value = distance
    return ao.outputs['AO']


def occlusion_material(image, edge, cavity, far, samples, other_objects):
    mat, tree, em = _pass_material('BPM Mesh Analysis', image)
    combine = tree.nodes.new('ShaderNodeCombineColor')
    tree.links.new(_ao(tree, edge, samples, inside=True), combine.inputs[0])
    tree.links.new(_ao(tree, cavity, samples, only_local=not other_objects), combine.inputs[1])
    tree.links.new(_ao(tree, far, samples, only_local=not other_objects), combine.inputs[2])
    tree.links.new(combine.outputs[0], em.inputs['Color'])
    return mat


def bevel_material(image, edge, samples):
    mat, tree, em = _pass_material('BPM Mesh Analysis Edges', image)
    bevel = tree.nodes.new('ShaderNodeBevel')
    bevel.samples = min(max(samples, 4), 16)
    bevel.inputs['Radius'].default_value = 2.0 * edge
    geo = tree.nodes.new('ShaderNodeNewGeometry')
    dot = tree.nodes.new('ShaderNodeVectorMath')
    dot.operation = 'DOT_PRODUCT'
    tree.links.new(bevel.outputs['Normal'], dot.inputs[0])
    tree.links.new(geo.outputs['Normal'], dot.inputs[1])
    dev = tree.nodes.new('ShaderNodeMath')
    dev.operation = 'SUBTRACT'
    dev.inputs[0].default_value = 1.0
    tree.links.new(dot.outputs['Value'], dev.inputs[1])
    tree.links.new(dev.outputs[0], em.inputs['Color'])
    return mat


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


def _bake(context, obj):
    override = dict(active_object=obj, object=obj, selected_objects=[obj], selected_editable_objects=[obj])
    try:
        with context.temp_override(**override):
            result = bpy.ops.object.bake(type='EMIT', margin=0, use_clear=False, use_selected_to_active=False,
                                         target='IMAGE_TEXTURES', save_mode='INTERNAL', uv_layer=UV_NAME)
    except RuntimeError as exc:
        detail = str(exc).strip().splitlines()[-1]
        raise B.BakeError('Blender could not analyze "%s": %s' % (obj.name, detail))
    if 'FINISHED' not in result:
        raise B.BakeError('Analyzing "%s" was cancelled.' % obj.name)


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
        samples, rays = self.settings.samples
        errors = []
        try:
            device = B.choose_device(self.settings.device)
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
                    self.info('"%s" shares its mesh with "%s": it uses the same maps.' % (obj.name, twin))
                    continue
                yield 'Analyzing %s' % obj.name
                try:
                    yield from self._analyze(obj, state, rays)
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

            images = []
            for label in ('Occlusion', 'Edges'):
                img = bpy.data.images.new('BPM_tmp_maps_' + label, size, size, alpha=True, float_buffer=True,
                                          is_data=True)
                img.pixels.foreach_set(np.zeros(size * size * 4, dtype=np.float32))  # alpha 0 = not baked
                self._temp_images.append(img)
                images.append(img)
            occ_mat = occlusion_material(images[0], edge, cavity, far, rays, s.other_objects)
            edge_mat = bevel_material(images[1], edge, rays)
            self._materials += [occ_mat, edge_mat]
            if not obj.material_slots:
                mesh.materials.append(None)
                added_slot = True
            for mat, label in ((occ_mat, 'corners and occlusion'), (edge_mat, 'sharp edges')):
                yield 'Measuring %s of %s' % (label, obj.name)
                for slot in obj.material_slots:
                    slot.material = mat
                _bake(context, obj)
                self.done_steps += 0.5
            yield 'Processing the mesh maps of %s' % obj.name
            pixels = process(B._pixels(images[0]), B._pixels(images[1]), size)
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
            mesh[SIGNATURE] = signature(mesh)
            mesh[RESOLUTION] = size
            self._new_tiles[tile] = (pixels, size)
            self.done_steps += 1
            finished = True
        finally:
            if added_slot:
                mesh.materials.pop()
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
