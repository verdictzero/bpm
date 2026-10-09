# SPDX-License-Identifier: GPL-3.0-or-later
"""Box-projected decals: any image, plus optional PBR maps, projected through a box.

A decal is an Empty shown as a box.  Every surface inside the box gets the
image, projected along the box's Z axis: move, scale or rotate the box to
place the decal.  In the materials of the objects inside the box, the decal
is an overlay (see overlays.py), so it stacks with dirt and wear layers and
ends up in baked textures.

Every decal has its own node group:

* a Texture Coordinate node set to the box gives coordinates in box space
  (-1..1 inside the box), which become the decal's UVs;
* drivers copy the directions of the box's axes into the group.  They let
  surfaces that face away from the box keep their look (no smearing on side
  faces) and turn normal maps the right way.  They are simple expressions,
  so they run even where Python scripts are not allowed.

The .blend file keeps working without the add-on.
"""

import math
import os
import re

import bpy
from mathutils import Matrix, Vector

from . import features as F
from . import gencommon as C
from . import library as L
from . import overlays as O
from .nodebuilder import Builder, auto_layout, create_group

GENERATOR = 'DECAL'
COLLECTION = 'BPM Decals'
BOX = 'BPM Box'  # name of the group's Texture Coordinate node that reads the box

# map -> words that mark it at the end of a file name ("Logo_Normal.png", "logo-rough.jpg"...)
MAP_WORDS = {
    'COLOR': ('basecolor', 'base_color', 'albedo', 'diffuse', 'diff', 'color', 'colour', 'col'),
    'NORMAL': ('normalgl', 'normal_gl', 'normal', 'nor', 'nrm', 'norm'),
    'ROUGHNESS': ('roughness', 'rough', 'rgh'),
    'METALLIC': ('metallic', 'metalness', 'metal', 'mtl'),
    'HEIGHT': ('height', 'displacement', 'disp', 'bump'),
}
MAP_PROPS = {'COLOR': 'color_map', 'NORMAL': 'normal_map', 'ROUGHNESS': 'roughness_map',
             'METALLIC': 'metallic_map', 'HEIGHT': 'height_map'}
IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.tga', '.tif', '.tiff', '.exr', '.webp', '.bmp', '.hdr')

PARAMS = O._channel_params() + [C.fac('Opacity', 1.0, 'Decal', 'Fade this decal in or out (0 = hidden)')]

# Directions of the box's X, Y and Z axes from its world rotation (XYZ Euler: R = Rz Ry Rx).
AXIS_EXPRESSIONS = {
    'X': ('cos(ry)*cos(rz)', 'cos(ry)*sin(rz)', '-sin(ry)'),
    'Y': ('sin(rx)*sin(ry)*cos(rz)-cos(rx)*sin(rz)', 'sin(rx)*sin(ry)*sin(rz)+cos(rx)*cos(rz)',
          'sin(rx)*cos(ry)'),
    'Z': ('cos(rx)*sin(ry)*cos(rz)+sin(rx)*sin(rz)', 'cos(rx)*sin(ry)*sin(rz)-sin(rx)*cos(rz)',
          'cos(rx)*cos(ry)'),
}

_quiet = False  # True while a decal is being set up: its settings don't rebuild anything yet


# ------------------------------------------------------------------- maps
def find_maps(path):
    """The texture set an image belongs to: {map: file} of the maps found next to it.

    "Rust_Logo_BaseColor.png" finds "Rust_Logo_Normal.png", "Rust_Logo_Roughness.jpg"...;
    a plain "logo.png" finds "logo_normal.png" and so on.
    """
    folder, name = os.path.split(path)
    stem = os.path.splitext(name)[0]
    base = stem
    for word in MAP_WORDS['COLOR']:
        found = re.match(r'^(.*?)[ _.-]*%s$' % re.escape(word), stem, re.IGNORECASE)
        if found and found.group(1):
            base = found.group(1)
            break
    maps = {'COLOR': path}
    try:
        files = sorted(os.listdir(folder or '.'))
    except OSError:
        return maps
    for file in files:
        file_stem, ext = os.path.splitext(file)
        if ext.lower() not in IMAGE_EXTENSIONS or not file_stem.lower().startswith(base.lower()):
            continue
        rest = file_stem[len(base):].strip(' _.-').lower()
        for key, words in MAP_WORDS.items():
            if key != 'COLOR' and key not in maps and rest in words:
                maps[key] = os.path.join(folder, file)
    return maps


def load_image(path, data=False):
    image = bpy.data.images.load(path, check_existing=True)
    if data:
        try:
            image.colorspace_settings.name = 'Non-Color'
        except TypeError:
            pass
    return image


def image_maps(image):
    """{map: image} for an image and the PBR maps saved next to it."""
    maps = {'COLOR': image}
    path = bpy.path.abspath(image.filepath) if image.filepath else ''
    if path and os.path.exists(path):
        for key, file in find_maps(path).items():
            if key != 'COLOR':
                maps[key] = load_image(file, data=True)
    return maps


# ------------------------------------------------------------------ boxes
def is_box(obj):
    """True for the box of a decal."""
    return (obj is not None and obj.type == 'EMPTY' and getattr(obj, 'bpm_decal', None) is not None
            and obj.bpm_decal.group is not None)


def boxes(scene):
    return [o for o in scene.objects if is_box(o)]


def box_of(tree):
    """The box a decal group projects from (None if it was deleted)."""
    node = tree.nodes.get(BOX) if tree is not None else None
    return node.object if node is not None else None


def is_decal_group(tree):
    return tree is not None and tree.get('bpm_generator') == GENERATOR


def touches(box, obj):
    """True if the bounding box of `obj` reaches into the decal box."""
    to_box = box.matrix_world.inverted_safe() @ obj.matrix_world
    corners = [to_box @ Vector(corner) for corner in obj.bound_box]
    return all(min(c[i] for c in corners) <= 1.0 and max(c[i] for c in corners) >= -1.0 for i in range(3))


def box_matrix(center, x_axis, z_axis, width, height, depth):
    """World matrix of a decal box: `width` x `height` decal, `depth` deep on both sides."""
    z = Vector(z_axis).normalized()
    x = Vector(x_axis)
    x = (x - z * x.dot(z)).normalized()
    y = z.cross(x)
    rotation = Matrix((x, y, z)).transposed().to_4x4()
    return Matrix.Translation(center) @ rotation @ Matrix.Diagonal((width / 2.0, height / 2.0, depth, 1.0))


def box_from_hits(hits, corner_rays, view_x, view_dir, aspect=1.0):
    """The decal box for a rectangle dragged over the model.

    hits:        [(location, normal)] of rays shot through the rectangle; the first is its center
    corner_rays: [(origin, direction)] through the 4 corners of the rectangle
    view_x:      screen right, view_dir: looking direction (world space)
    aspect:      width / height of the image: the decal keeps its proportions
    """
    if not hits:
        return None
    view_dir = Vector(view_dir).normalized()
    normal = Vector((0.0, 0.0, 0.0))
    for _location, n in hits:
        n = Vector(n)
        normal += n if n.dot(view_dir) < 0.0 else -n  # facing the viewer
    if normal.length < 1e-6:
        normal = -view_dir
    z = normal.normalized()
    x = Vector(view_x) - z * Vector(view_x).dot(z)
    if x.length < 1e-6:  # looking along the surface: use the view's up direction
        x = z.cross(view_dir)
    x.normalize()
    y = z.cross(x)
    anchor = Vector(hits[0][0])
    points = []
    for origin, direction in corner_rays:
        origin, direction = Vector(origin), Vector(direction)
        along = direction.dot(z)
        t = (anchor - origin).dot(z) / along if abs(along) > 1e-6 else (anchor - origin).length
        points.append(origin + direction * t)
    xs = [(p - anchor).dot(x) for p in points]
    ys = [(p - anchor).dot(y) for p in points]
    width, height = max(xs) - min(xs), max(ys) - min(ys)
    center = anchor + x * (max(xs) + min(xs)) / 2.0 + y * (max(ys) + min(ys)) / 2.0
    width, height = max(width, 1e-4), max(height, 1e-4)
    if width / height > aspect:  # fit the image into the rectangle
        width = height * aspect
    else:
        height = width / aspect
    reach = max(abs((Vector(location) - center).dot(z)) for location, _n in hits)
    depth = reach + 0.15 * max(width, height)
    return box_matrix(center, x, z, width, height, depth)


# ------------------------------------------------------------ node group
def _value(b, name, label):
    node = b.node('ShaderNodeValue', label=label)
    node.name = name
    return node.outputs[0]


def _axis(b, name, label, value):
    node = b.node('ShaderNodeCombineXYZ', label=label)
    node.name = name
    for i in range(3):
        node.inputs[i].default_value = value[i]
    return node.outputs[0]


def _texture(b, image, vector, label):
    node = b.node('ShaderNodeTexImage', label=label)
    node.image = image
    node.extension = 'CLIP'  # nothing outside the box
    node.interpolation = 'Linear'
    b.feed(node.inputs['Vector'], vector)
    return node


def _build_nodes(b, I, gout, box):
    st = box.bpm_decal
    col, metal, rough, normal, height, _coat, geo_n = O._below(b, I)
    rot = box.matrix_world.to_3x3().normalized()

    coords = b.node('ShaderNodeTexCoord', label='Decal Box')
    coords.name = BOX
    coords.object = box
    x, y, z = b.separate(coords.outputs['Object'])
    uv = b.combine(b.madd(x, 0.5, 0.5), b.madd(y, 0.5, 0.5), 0.0)
    axes = {k: _axis(b, 'BPM Axis ' + k, 'Box %s Axis' % k, rot.col[i]) for i, k in enumerate('XYZ')}

    # where the decal is: the image's alpha, inside the box, on surfaces that face the box
    color_tex = _texture(b, st.color_map, uv, 'Decal Color')
    facing = b.vmath('DOT_PRODUCT', geo_n, axes['Z'])
    limit = _value(b, 'BPM Facing', 'Facing Limit')
    mask = b.mul(color_tex.outputs['Alpha'], b.smoothstep(b.sub(limit, 0.08), b.add(limit, 0.02), facing))
    mask = b.mul(mask, b.one_minus(b.smoothstep(0.85, 1.0, b.absolute(z))))
    mask = b.mul(mask, b.mul(_value(b, 'BPM Opacity', 'Opacity'), I['Opacity']))
    S = F.Space(b, False, 1.0, 0.0, salt=5)
    wz = b.madd(S.znoise(6.0, 2, detail=3.0, roughness=0.6, label='Wear Patches'), 0.6,
                S.znoise(40.0, 1, detail=4.0, roughness=0.6, label='Wear'))
    mask = b.mul(mask, b.one_minus(F.cover(b, wz, _value(b, 'BPM Wear', 'Wear'), 0.3)))

    tint = b.node('ShaderNodeRGB', label='Tint')
    tint.name = 'BPM Tint'
    decal = b.mix_color(1.0, color_tex.outputs['Color'], tint.outputs[0], blend='MULTIPLY')
    b.feed(gout.inputs['Base Color'], b.mix_color(mask, col, decal))

    def channel(image, setting, label):
        if image is None:
            return _value(b, setting, label)
        return b.separate_color(_texture(b, image, uv, 'Decal ' + label).outputs['Color'])[0]
    b.feed(gout.inputs['Roughness'], b.mix(mask, rough, channel(st.roughness_map, 'BPM Roughness', 'Roughness')))
    b.feed(gout.inputs['Metallic'], b.mix(mask, metal, channel(st.metallic_map, 'BPM Metallic', 'Metallic')))

    if st.normal_map is not None:  # tangent space = the box's X and Y axes laid onto the surface
        r, g, bl = b.separate_color(_texture(b, st.normal_map, uv, 'Decal Normal').outputs['Color'])
        strength = _value(b, 'BPM Normal Strength', 'Normal Strength')
        flip = _value(b, 'BPM Flip Green', 'Green Direction')  # 1 = OpenGL, -1 = DirectX
        nx = b.mul(b.madd(r, 2.0, -1.0), strength)
        ny = b.mul(b.mul(b.madd(g, 2.0, -1.0), flip), strength)
        nz = b.madd(bl, 2.0, -1.0)

        def on_surface(axis):
            return b.vmath('NORMALIZE', b.vmath('SUBTRACT', axis, b.vscale(normal, b.vmath('DOT_PRODUCT', normal,
                                                                                               axis))))
        bent = b.vadd(b.vadd(b.vscale(on_surface(axes['X']), nx), b.vscale(on_surface(axes['Y']), ny)),
                      b.vscale(normal, nz))
        normal = b.vmath('NORMALIZE', b.mix_vector(mask, normal, b.vmath('NORMALIZE', bent)))
    b.feed(gout.inputs['Normal'], normal)

    if st.height_map is not None:
        bump = b.separate_color(_texture(b, st.height_map, uv, 'Decal Height').outputs['Color'])[0]
        height = b.clamp01(b.madd(b.mul(bump, mask), b.mul(_value(b, 'BPM Relief', 'Relief'), 0.15), height))
    b.feed(gout.inputs['Height'], height)
    b.feed(gout.inputs['Coat'], I['Coat'])
    b.feed(gout.inputs['Transmission'], b.mul(I['Transmission'], b.one_minus(mask)))


def _clear(tree):
    if tree.animation_data is not None:
        for fcurve in list(tree.animation_data.drivers):
            tree.animation_data.drivers.remove(fcurve)
    tree.nodes.clear()


def _drive_axes(tree, box):
    for axis, expressions in AXIS_EXPRESSIONS.items():
        node = tree.nodes['BPM Axis ' + axis]
        for i, expression in enumerate(expressions):
            driver = node.inputs[i].driver_add('default_value').driver
            driver.type = 'SCRIPTED'
            driver.use_self = False
            for name, channel in (('rx', 'ROT_X'), ('ry', 'ROT_Y'), ('rz', 'ROT_Z')):
                var = driver.variables.new()
                var.name = name
                var.type = 'TRANSFORMS'
                target = var.targets[0]
                target.id = box
                target.transform_type = channel
                target.transform_space = 'WORLD_SPACE'
                target.rotation_mode = 'XYZ'
            driver.expression = expression


def build(box):
    """(Re)build the node group of the decal `box` from its settings.

    The group keeps its name and sockets, so the materials using it stay connected.
    """
    st = box.bpm_decal
    tree = st.group
    if tree is None:
        tree, gin, gout = create_group('BPM Decal %s' % box.name, PARAMS, O.OUTPUTS)
        tree['bpm_generator'] = GENERATOR
        tree['bpm_tile'] = False
        tree['bpm_version'] = O.OVERLAY_VERSION
        st.group = tree
    else:
        _clear(tree)
        gin = tree.nodes.new('NodeGroupInput')
        gout = tree.nodes.new('NodeGroupOutput')
    b = Builder(tree)
    inputs = {p.name: gin.outputs[p.name] for p in PARAMS}
    _build_nodes(b, inputs, gout, box)
    auto_layout(tree)
    _drive_axes(tree, box)
    sync(box)
    return tree


def sync(box):
    """Copy the decal's settings into its node group."""
    st = box.bpm_decal
    tree = st.group
    if tree is None:
        return
    values = {
        'BPM Opacity': st.opacity,
        'BPM Facing': math.cos(st.angle_limit),
        'BPM Roughness': st.roughness,
        'BPM Metallic': st.metallic,
        'BPM Normal Strength': st.normal_strength,
        'BPM Flip Green': -1.0 if st.directx else 1.0,
        'BPM Relief': st.relief,
        'BPM Wear': st.wear,
    }
    for name, value in values.items():
        node = tree.nodes.get(name)
        if node is not None:
            node.outputs[0].default_value = value
    tint = tree.nodes.get('BPM Tint')
    if tint is not None:
        tint.outputs[0].default_value = tuple(st.tint) + (1.0,)


def _collection(scene):
    coll = bpy.data.collections.get(COLLECTION)
    if coll is None or coll.library is not None:
        coll = bpy.data.collections.new(COLLECTION)
    if coll.name not in scene.collection.children and coll not in scene.collection.children_recursive:
        scene.collection.children.link(coll)
    return coll


def create(scene, image, matrix, maps=None, name=None):
    """A new decal box at `matrix` (box space -1..1 holds the decal) showing `image`.

    `maps`: {map: image} with the PBR maps (found next to the image when None).
    """
    global _quiet
    maps = dict(image_maps(image) if maps is None else maps)
    maps['COLOR'] = image
    stem = os.path.splitext(image.name)[0]
    box = bpy.data.objects.new(name or 'Decal %s' % stem, None)
    box.empty_display_type = 'CUBE'
    box.empty_display_size = 1.0
    box.show_in_front = True
    _collection(scene).objects.link(box)
    box.matrix_world = matrix
    _quiet = True
    try:
        st = box.bpm_decal
        for key, prop in MAP_PROPS.items():
            setattr(st, prop, maps.get(key))
        if maps.get('HEIGHT') is None:
            st.relief = 0.0
    finally:
        _quiet = False
    build(box)
    return box


# ---------------------------------------------------------------- targets
def users(tree):
    """(material, node) pairs that use the decal group `tree`."""
    found = []
    for mat in bpy.data.materials:
        if mat.node_tree is None:
            continue
        for node in mat.node_tree.nodes:
            if node.bl_idname == 'ShaderNodeGroup' and node.node_tree == tree:
                found.append((mat, node))
    return found


def _materials(obj):
    mats = []
    for slot in obj.material_slots:
        if slot.material is not None and slot.material not in mats:
            mats.append(slot.material)
    return mats


EXCLUDED = 'bpm_no_decals'  # material property: decals taken off it by hand (they don't come back by themselves)


def exclude(mat, tree):
    """The user took this decal off `mat`: refreshing and baking won't put it back."""
    names = list(mat.get(EXCLUDED, []))
    if tree.name not in names:
        mat[EXCLUDED] = names + [tree.name]


def add_to(box, obj, warnings=None, force=False):
    """Put the decal on every material of `obj` (once).  Returns True if `obj` shows it.

    Materials the decal was taken off by hand are left alone, unless `force`.
    """
    tree = box.bpm_decal.group
    if not L.can_have_material(obj) or tree is None:
        return False
    if not _materials(obj):
        mat = bpy.data.materials.new('Material')
        L.ensure_node_tree(mat)
        L.assign_material(obj, mat)
    shown = False
    for mat in _materials(obj):
        if L.is_baked_material(mat):
            continue
        if mat.library is not None:
            if warnings is not None:
                warnings.append('"%s" is linked from another file: no decal on it.' % mat.name)
            continue
        if any(node.node_tree == tree for node in L.overlay_nodes(mat)):
            shown = True
            continue
        excluded = list(mat.get(EXCLUDED, []))
        if tree.name in excluded:
            if not force:
                continue
            excluded.remove(tree.name)
            mat[EXCLUDED] = excluded
        try:
            node = L.add_overlay(mat, GENERATOR, group=tree)
        except L.OverlayError as exc:
            if warnings is not None:
                warnings.append(str(exc))
            continue
        node.label = 'Decal: %s' % box.name
        shown = True
    return shown


def candidates(scene):
    return [o for o in scene.objects if L.can_have_material(o) and o.type != 'EMPTY' and o.visible_get()]


def refresh(box, scene, warnings=None, force=False):
    """Add the decal to the objects that are in its box now.  Returns those objects."""
    return [o for o in candidates(scene) if touches(box, o) and add_to(box, o, warnings, force)]


def refresh_object(obj, scene):
    """Before baking `obj`: put the decals whose box reaches it on its materials."""
    for box in boxes(scene):
        if touches(box, obj):
            add_to(box, obj)


def remove(box):
    """Delete a decal: its layers in all materials, its node group and its box."""
    tree = box.bpm_decal.group
    if tree is not None:
        _remove_group(tree)
    bpy.data.objects.remove(box)


def _remove_group(tree):
    for mat, node in users(tree):
        L.remove_overlay(mat, node)
    if tree.animation_data is not None:
        tree.animation_data_clear()
    bpy.data.node_groups.remove(tree)


# --------------------------------------------------- deleted / copied boxes
_scheduled = False


def _fix_decals():
    """Deleted box: remove its decal.  Copied box (Shift+D): give the copy a decal of its own."""
    global _scheduled
    _scheduled = False
    for tree in [t for t in bpy.data.node_groups if is_decal_group(t) and t.library is None]:
        box = box_of(tree)
        if box is None or box.users == 0 or not box.users_scene:
            _remove_group(tree)
    for scene in bpy.data.scenes:
        for box in boxes(scene):
            if box_of(box.bpm_decal.group) not in {box, None}:  # a copy still uses the original's group
                box.bpm_decal.group = None
                build(box)
                refresh(box, scene)
    return None


def _needs_fix():
    for tree in bpy.data.node_groups:
        if is_decal_group(tree) and tree.library is None:
            box = box_of(tree)
            if box is None or box.users == 0 or not box.users_scene:
                return True
    return False


@bpy.app.handlers.persistent
def _on_update(scene, depsgraph):
    global _scheduled
    if _scheduled:
        return
    copied = False
    for update in depsgraph.updates:
        obj = getattr(update.id, 'original', None)
        if isinstance(obj, bpy.types.Object) and is_box(obj) and box_of(obj.bpm_decal.group) is not obj:
            copied = True
            break
    if copied or _needs_fix():
        _scheduled = True
        bpy.app.timers.register(_fix_decals, first_interval=0.0)


# --------------------------------------------------------------- settings
def _settings_changed(self, context):
    if not _quiet:
        sync(self.id_data)


def _maps_changed(self, context):
    if not _quiet and self.group is not None:
        build(self.id_data)


class BPM_DecalSettings(bpy.types.PropertyGroup):
    group: bpy.props.PointerProperty(type=bpy.types.NodeTree, name='Decal Node Group')
    color_map: bpy.props.PointerProperty(
        type=bpy.types.Image, name='Image', update=_maps_changed,
        description='The decal image. Its transparency (alpha) cuts out the shape')
    normal_map: bpy.props.PointerProperty(type=bpy.types.Image, name='Normal', update=_maps_changed,
                                          description='Optional normal map of the decal')
    roughness_map: bpy.props.PointerProperty(type=bpy.types.Image, name='Roughness', update=_maps_changed,
                                             description='Optional roughness map (white = matte)')
    metallic_map: bpy.props.PointerProperty(type=bpy.types.Image, name='Metallic', update=_maps_changed,
                                            description='Optional metallic map (white = metal)')
    height_map: bpy.props.PointerProperty(type=bpy.types.Image, name='Height', update=_maps_changed,
                                          description='Optional height map (white = raised)')
    opacity: bpy.props.FloatProperty(name='Opacity', default=1.0, min=0.0, max=1.0, subtype='FACTOR',
                                     update=_settings_changed, description='Fade the decal in or out')
    angle_limit: bpy.props.FloatProperty(
        name='Angle Limit', default=math.radians(70.0), min=0.0, max=math.radians(90.0), subtype='ANGLE',
        update=_settings_changed,
        description='Surfaces turned further than this from the box\'s direction get no decal (no smearing '
                    'on side faces)')
    roughness: bpy.props.FloatProperty(name='Roughness', default=0.45, min=0.0, max=1.0, subtype='FACTOR',
                                       update=_settings_changed,
                                       description='Glossiness of the decal: 0 = glossy, 1 = matte (when it has '
                                                   'no roughness map)')
    metallic: bpy.props.FloatProperty(name='Metallic', default=0.0, min=0.0, max=1.0, subtype='FACTOR',
                                      update=_settings_changed,
                                      description='1 = metal foil (when it has no metallic map)')
    normal_strength: bpy.props.FloatProperty(name='Normal Strength', default=1.0, min=0.0, max=3.0,
                                             update=_settings_changed, description='Strength of the normal map')
    directx: bpy.props.BoolProperty(name='DirectX Normal Map', default=False, update=_settings_changed,
                                    description='Tick for normal maps made for Unreal / DirectX (green flipped)')
    relief: bpy.props.FloatProperty(name='Relief', default=0.5, min=0.0, max=1.0, subtype='FACTOR',
                                    update=_settings_changed,
                                    description='How much the height map raises the surface in the height map')
    wear: bpy.props.FloatProperty(name='Wear', default=0.0, min=0.0, max=1.0, subtype='FACTOR',
                                  update=_settings_changed, description='Worn, chipped away decal: old stencils')
    tint: bpy.props.FloatVectorProperty(name='Tint', subtype='COLOR', size=3, default=(1.0, 1.0, 1.0), min=0.0,
                                        max=1.0, update=_settings_changed,
                                        description='Multiplies the colors of the image')


CLASSES = (BPM_DecalSettings,)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Object.bpm_decal = bpy.props.PointerProperty(type=BPM_DecalSettings)
    if _on_update not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_on_update)


def unregister():
    if _on_update in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_on_update)
    if bpy.app.timers.is_registered(_fix_decals):
        bpy.app.timers.unregister(_fix_decals)
    del bpy.types.Object.bpm_decal
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
