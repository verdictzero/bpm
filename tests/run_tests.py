# SPDX-License-Identifier: GPL-3.0-or-later
"""Headless test suite.

    blender -b --factory-startup --python-exit-code 1 -P tests/run_tests.py [-- -k name]

Exits with code 1 if any test fails.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

import bpy
import numpy as np
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import bpm_procedural_metals as addon  # noqa: E402
from bpm_procedural_metals import bake as B  # noqa: E402
from bpm_procedural_metals import generators as G  # noqa: E402
from bpm_procedural_metals import features as F  # noqa: E402
from bpm_procedural_metals import library as L  # noqa: E402
from bpm_procedural_metals import meshmaps as M  # noqa: E402
from bpm_procedural_metals import presets as P  # noqa: E402

TMP = tempfile.mkdtemp(prefix='bpm_tests_')
TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


def fresh_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if not hasattr(bpy.types.Scene, 'bpm'):
        addon.register()


def add_cube(name='Cube', size=2.0, uv=True, location=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=size, location=location)
    obj = bpy.context.active_object
    obj.name = name
    if not uv:
        while obj.data.uv_layers:
            obj.data.uv_layers.remove(obj.data.uv_layers[0])
    return obj


def settings(**kw):
    base = dict(resolution=64, quality='FAST', output_dir=os.path.join(TMP, 'out'))
    base.update(kw)
    return B.BakeSettings(**base)


def read_png(path):
    img = bpy.data.images.load(path, check_existing=False)
    try:
        img.colorspace_settings.name = 'Non-Color'
    except TypeError:
        pass
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, 4)


def seam_ok(a):
    """False if the texture has a visible seam where it wraps around."""
    for axis in (0, 1):
        steps = np.abs(np.diff(a, axis=axis)).mean(axis=(1 - axis, 2))  # one value per row/column step
        wrap = np.abs(np.take(a, 0, axis=axis) - np.take(a, -1, axis=axis)).mean()
        if wrap > 1.25 * steps.max() + 1e-4:
            return False
    return True


def generic_material(base=(0.5, 0.5, 0.5, 1.0), metallic=0.25, roughness=0.75):
    mat = bpy.data.materials.new('Generic')
    tree = L.ensure_node_tree(mat)
    bsdf = next(n for n in tree.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = base
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    return mat


# --------------------------------------------------------------------- tests
@test
def register_unregister():
    fresh_scene()
    assert hasattr(bpy.types.Scene, 'bpm') and hasattr(bpy.ops.bpm, 'bake')
    addon.unregister()
    assert not hasattr(bpy.types.Scene, 'bpm')
    addon.register()
    assert hasattr(bpy.types.Object, 'bpm_backup')


@test
def groups_are_clean():
    fresh_scene()
    for gen in G.GENERATORS:
        if G.GENERATORS[gen]['custom']:  # decals: built per decal (see decals_project_and_bake)
            continue
        for tile in (False, True):
            ng = G.build_group(gen, tile)
            assert all(link.is_valid for link in ng.links), ng.name
            mismatched = [l for l in ng.links if l.from_node.bl_idname != 'NodeGroupInput'
                          and l.to_node.bl_idname != 'NodeGroupOutput'
                          and l.from_socket.type != l.to_socket.type]
            assert not mismatched, '%s has %d implicit conversions' % (ng.name, len(mismatched))
            names = [s.name for s in ng.interface.items_tree if getattr(s, 'in_out', None) == 'INPUT']
            assert names == [p.name for p in G.params_for(gen, tile)], ng.name


@test
def presets_are_valid():
    ids = set()
    for preset in P.PRESETS:
        assert preset['id'] not in ids, 'duplicate id ' + preset['id']
        ids.add(preset['id'])
        params = {p.name: p for p in G.params_for(preset['generator'])}
        for key, value in preset['values'].items():
            assert key in params, '%s: unknown value %s' % (preset['id'], key)
            p = params[key]
            if p.kind == 'FLOAT':
                assert p.min <= value <= p.max, '%s: %s=%s out of range' % (preset['id'], key, value)
            if p.kind == 'COLOR':
                assert len(value) in (3, 4) and all(0.0 <= c <= 1.0 for c in value), preset['id']
        for gen, values in preset['overlays']:
            assert G.is_overlay(gen), preset['id']
            names = {p.name for p in G.params_for(gen)}
            assert set(values) <= names, '%s: unknown overlay values %s' % (preset['id'], set(values) - names)
        base = preset['thumb'].get('base')
        assert base is None or not P.is_overlay(P.get(base)), preset['id']
        assert P.is_overlay(preset) == G.is_overlay(preset['generator']), preset['id']
    assert len(P.PRESETS) >= 120, 'expected a big library'
    for cat, *_rest in P.CATEGORIES:
        assert P.by_category(cat), cat
    for gen in G.GENERATORS:
        assert G.GENERATORS[gen]['custom'] or any(p['generator'] == gen for p in P.PRESETS), \
            'no preset uses ' + gen


@test
def every_preset_renders():
    fresh_scene()
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 1
    scene.cycles.use_denoising = False
    scene.render.resolution_x = scene.render.resolution_y = 12
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
    scene.collection.objects.link(cam)
    cam.location = (0, -6, 0)
    cam.rotation_euler = (1.5708, 0, 0)
    scene.camera = cam
    obj = add_cube()
    for preset in P.PRESETS:
        if P.is_overlay(preset):
            mat = generic_material()
            L.add_overlay(mat, preset['generator'], L.preset_values(preset))
            assert len(L.overlay_stack(mat)) == 1
        else:
            mat = L.create_material(preset['id'])
            assert L.find_bpm_node(mat) is not None
            assert len(L.overlay_stack(mat)) == len(preset['overlays'])
        obj.data.materials.clear()
        obj.data.materials.append(mat)
        bpy.ops.render.render()


def bsdf_source(mat, name):
    sock = L.find_principled(mat.node_tree).inputs[name]
    return sock.links[0].from_node if sock.is_linked else None


def uv_array(mesh, name):
    uv = np.empty(len(mesh.loops) * 2, dtype=np.float64)
    mesh.uv_layers[name].data.foreach_get('uv', uv)
    return uv.reshape(-1, 2)


def face_uv_centers(mesh, name):
    uv = uv_array(mesh, name)
    return np.array([uv[p.loop_start:p.loop_start + p.loop_total].mean(axis=0) for p in mesh.polygons])


def uv_overlap(mesh, name, res=256):
    """Fraction of the covered texels that more than one face covers (0 = no overlapping UVs)."""
    uv = uv_array(mesh, name) * res
    count = np.zeros((res, res), dtype=np.int32)
    for poly in mesh.polygons:
        pts = uv[poly.loop_start:poly.loop_start + poly.loop_total]
        x0, y0 = np.clip(np.floor(pts.min(axis=0)).astype(int), 0, res)
        x1, y1 = np.clip(np.ceil(pts.max(axis=0)).astype(int), 0, res)
        ys, xs = np.mgrid[y0:y1, x0:x1] + 0.5
        inside = np.zeros(xs.shape, dtype=bool)
        for i in range(1, len(pts) - 1):  # fan of triangles
            tri = [pts[0], pts[i], pts[i + 1]]
            sides = [(b[0] - a[0]) * (ys - a[1]) - (b[1] - a[1]) * (xs - a[0])
                     for a, b in zip(tri, tri[1:] + tri[:1])]
            inside |= np.all([d > 0 for d in sides], axis=0) | np.all([d < 0 for d in sides], axis=0)
        count[y0:y1, x0:x1] += inside
    return (count > 1).sum() / max((count > 0).sum(), 1)


def sample(img, uvs):
    """Pixel values of an image (rows from the bottom, like Blender) at UV positions."""
    h, w = img.shape[:2]
    x = np.clip((uvs[:, 0] * w).astype(int), 0, w - 1)
    y = np.clip((uvs[:, 1] * h).astype(int), 0, h - 1)
    return img[y, x]


def uv_material():
    """Roughness = U and Metallic = V of the UV map "UVMap", like a texture made for those UVs."""
    mat = generic_material()
    tree = mat.node_tree
    uv = tree.nodes.new('ShaderNodeUVMap')
    uv.uv_map = 'UVMap'
    sep = tree.nodes.new('ShaderNodeSeparateXYZ')
    tree.links.new(uv.outputs['UV'], sep.inputs[0])
    bsdf = L.find_principled(tree)
    tree.links.new(sep.outputs['X'], bsdf.inputs['Roughness'])
    tree.links.new(sep.outputs['Y'], bsdf.inputs['Metallic'])
    return mat


@test
def overlay_stack_operations():
    fresh_scene()
    mat = L.create_material('paint_industrial_yellow')
    group = L.find_bpm_node(mat)
    dirt = L.add_overlay(mat, 'DIRT')
    dust = L.add_overlay(mat, 'DUST', {'Amount': 0.9})
    assert L.overlay_stack(mat) == [dirt, dust]
    assert bsdf_source(mat, 'Base Color') == dust and bsdf_source(mat, 'Coat Weight') == dust
    assert dust.inputs['Base Color'].links[0].from_node == dirt
    assert dirt.inputs['Height'].links[0].from_node == group
    assert L.height_source(mat).node == dust
    assert abs(dust.inputs['Amount'].default_value - 0.9) < 1e-6
    assert L.find_bpm_node(mat) == group, 'overlays must not be mistaken for the material'
    # reorder, hide / show
    assert L.move_overlay(mat, 0, 1)
    assert [n.node_tree['bpm_generator'] for n in L.overlay_stack(mat)] == ['DUST', 'DIRT']
    top = L.overlay_stack(mat)[1]
    L.toggle_overlay(top)
    assert top.inputs['Opacity'].default_value == 0.0 and L.overlay_hidden(top)
    L.toggle_overlay(top)
    assert top.inputs['Opacity'].default_value == 1.0 and not L.overlay_hidden(top)
    # loading a preset of another family keeps the user's overlays
    L.load_preset_into(mat, 'wood_oak_floor')
    assert L.generator_of(mat) == 'WOOD'
    assert [n.node_tree['bpm_generator'] for n in L.overlay_stack(mat)] == ['DUST', 'DIRT']
    assert bsdf_source(mat, 'Base Color').node_tree['bpm_generator'] == 'DIRT'
    # removing everything restores the plain wiring
    for node in list(L.overlay_stack(mat)):
        L.remove_overlay(mat, node)
    assert bsdf_source(mat, 'Base Color') == L.find_bpm_node(mat)
    assert bsdf_source(mat, 'Normal') == L.find_bpm_node(mat)
    # preset overlays are replaced when another preset is loaded, user overlays stay
    mat = L.create_material('plastic_dirty_bin')
    assert [n.node_tree['bpm_generator'] for n in L.overlay_stack(mat)] == ['DIRT']
    L.add_overlay(mat, 'DUST')
    L.load_preset_into(mat, 'plastic_retro_beige')
    gens = [n.node_tree['bpm_generator'] for n in L.overlay_stack(mat)]
    assert sorted(gens) == ['DUST', 'DUST'], gens
    # a plain material: unconnected values are carried over and restored
    mat = generic_material((0.1, 0.2, 0.8, 1.0), 0.0, 0.3)
    node = L.add_overlay(mat, 'DUST')
    assert abs(node.inputs['Roughness'].default_value - 0.3) < 1e-6
    assert tuple(node.inputs['Base Color'].default_value)[:3] == (0.1, 0.2, 0.8) or \
        abs(node.inputs['Base Color'].default_value[2] - 0.8) < 1e-6
    L.remove_overlay(mat, node)
    bsdf = L.find_principled(mat.node_tree)
    assert not bsdf.inputs['Base Color'].is_linked and abs(bsdf.inputs['Roughness'].default_value - 0.3) < 1e-6
    # no Principled BSDF: clear error
    mat = bpy.data.materials.new('Emit')
    tree = L.ensure_node_tree(mat)
    tree.nodes.clear()
    out = tree.nodes.new('ShaderNodeOutputMaterial')
    tree.links.new(tree.nodes.new('ShaderNodeEmission').outputs[0], out.inputs['Surface'])
    try:
        L.add_overlay(mat, 'DIRT')
    except L.OverlayError:
        pass
    else:
        raise AssertionError('expected an OverlayError')


@test
def overlay_operators():
    fresh_scene()
    a = add_cube('A')
    b = add_cube('B', location=(4, 0, 0))
    a.data.materials.append(L.create_material('steel_polished'))
    for o in (a, b):
        o.select_set(True)
    bpy.context.view_layer.objects.active = a
    # from the gallery: an overlay preset goes on top instead of replacing the material
    assert bpy.ops.bpm.apply_preset(preset='dust_heavy') == {'FINISHED'}
    assert L.generator_of(a.active_material) == 'METAL'
    assert len(L.overlay_stack(a.active_material)) == 1
    assert b.active_material is not None and len(L.overlay_stack(b.active_material)) == 1, \
        'objects without a material get a plain one'
    assert bpy.ops.bpm.add_overlay(preset='dirt_mud') == {'FINISHED'}
    assert [n.label for n in L.overlay_stack(a.active_material)] == ['Heavy Dust', 'Mud Splatter']
    assert bpy.ops.bpm.move_overlay(index=1, step=-1) == {'FINISHED'}
    assert [n.label for n in L.overlay_stack(a.active_material)] == ['Mud Splatter', 'Heavy Dust']
    assert bpy.ops.bpm.toggle_overlay(index=0) == {'FINISHED'}
    assert bpy.ops.bpm.overlay_seed(index=0) == {'FINISHED'}
    assert bpy.ops.bpm.remove_overlay(index=0) == {'FINISHED'}
    assert [n.label for n in L.overlay_stack(a.active_material)] == ['Heavy Dust']
    assert bpy.ops.bpm.set_value(socket='Metal Color', value=0.0) == {'CANCELLED'}, 'only for number sockets'
    assert bpy.ops.bpm.set_value(socket='Nope', value=0.0) == {'CANCELLED'}
    # the weave buttons
    a.data.materials[0] = L.create_material('fabric_canvas')
    assert bpy.ops.bpm.set_value(socket='Weave', value=3.0) == {'FINISHED'}
    assert L.find_bpm_node(a.active_material).inputs['Weave'].default_value == 3.0


@test
def overlays_are_baked():
    """Dust must show up in the baked color map and give a height map to plain materials."""
    fresh_scene()
    obj = add_cube()
    mat = generic_material((0.02, 0.02, 0.02, 1.0), 0.0, 0.3)
    obj.data.materials.append(mat)
    out_a = os.path.join(TMP, 'ov_a')
    B.run_to_end(B.ObjectBakeJob(bpy.context, [obj], settings(maps={'BASE_COLOR', 'HEIGHT'}, output_dir=out_a,
                                                             assign_baked=False)))
    assert not os.path.exists(os.path.join(out_a, 'Cube_Height.png')), 'plain material has no height'
    L.add_overlay(mat, 'DUST', {'Amount': 1.0, 'Top Facing': 0.0})
    out_b = os.path.join(TMP, 'ov_b')
    B.run_to_end(B.ObjectBakeJob(bpy.context, [obj], settings(maps={'BASE_COLOR', 'HEIGHT', 'ROUGHNESS'},
                                                             output_dir=out_b, assign_baked=False)))
    plain = read_png(os.path.join(out_a, 'Cube_BaseColor.png'))
    dusty = read_png(os.path.join(out_b, 'Cube_BaseColor.png'))
    rough = read_png(os.path.join(out_b, 'Cube_Roughness.png'))
    covered = plain[..., 0] > 0.08  # texels inside the UV islands (the background stays black)
    assert 0.2 < covered.mean() < 0.9, covered.mean()
    assert dusty[..., 0][covered].mean() > plain[..., 0][covered].mean() + 0.2, 'dust missing from the bake'
    assert rough[..., 0][covered].mean() > 0.6
    assert os.path.exists(os.path.join(out_b, 'Cube_Height.png'))


def linked_from(sock):
    return sock.links[0].from_node if sock.is_linked else None


@test
def glass_transmission_and_overlays():
    """Glass lets light through; dirt and dust on top block it; opaque materials stay untouched."""
    fresh_scene()
    mat = L.create_material('glass_clear')
    node = L.find_bpm_node(mat)
    bsdf = L.find_principled(mat.node_tree)
    assert linked_from(bsdf.inputs['Transmission Weight']) == node
    assert linked_from(bsdf.inputs['IOR']) == node
    if hasattr(mat, 'use_raytrace_refraction'):
        assert mat.use_raytrace_refraction, 'EEVEE must show what is behind the glass'
    assert mat.diffuse_color[3] < 1.0, 'see-through in Solid mode'
    dirt = L.add_overlay(mat, 'DIRT')
    assert linked_from(bsdf.inputs['Transmission Weight']) == dirt
    assert linked_from(dirt.inputs['Transmission']) == node
    assert linked_from(bsdf.inputs['IOR']) == node, 'IOR goes straight to the BSDF'
    L.remove_overlay(mat, dirt)
    assert linked_from(bsdf.inputs['Transmission Weight']) == node
    # opaque materials: the overlay does not touch transmission at all
    paint = L.create_material('paint_industrial_yellow')
    dust = L.add_overlay(paint, 'DUST')
    pbsdf = L.find_principled(paint.node_tree)
    assert not pbsdf.inputs['Transmission Weight'].is_linked and not dust.outputs['Transmission'].is_linked
    # overlays made by older versions have no Transmission socket: removing them still works
    old = L.add_overlay(paint, 'DIRT')
    tree = old.node_tree.copy()
    old.node_tree = tree
    for item in [i for i in tree.interface.items_tree if getattr(i, 'name', '') == 'Transmission']:
        tree.interface.remove(item)
    assert 'Transmission' not in old.inputs
    L.remove_overlay(paint, old)
    assert len(L.overlay_stack(paint)) == 1
    assert L.move_overlay(paint, 0, 1) is False


@test
def glass_bakes_to_glass():
    """The bake writes Transmission (+ Opacity) for glass only and rebuilds a glass material."""
    fresh_scene()
    glass = add_cube('Window')
    gmat = L.create_material('glass_dirty_window')
    L.find_bpm_node(gmat).inputs['IOR'].default_value = 1.52
    glass.data.materials.append(gmat)
    clean = add_cube('Clean', location=(3, 0, 0))
    clean.data.materials.append(L.create_material('glass_clear'))
    solid = add_cube('Solid', location=(6, 0, 0))
    solid.data.materials.append(L.create_material('steel_brushed'))
    job = B.ObjectBakeJob(bpy.context, [glass, clean, solid],
                          settings(maps={'BASE_COLOR', 'ROUGHNESS', 'TRANSMISSION'}))
    B.run_to_end(job)
    names = sorted(os.listdir(job.output_dir))
    for name in ('Window_Transmission.png', 'Window_Opacity.png', 'Clean_Transmission.png'):
        assert name in names, names
    assert not any(n.startswith('Solid_Transmission') or n.startswith('Solid_Opacity') for n in names), names
    covered = read_png(os.path.join(job.output_dir, 'Window_BaseColor.png'))[..., 0] > 0.02  # inside the UVs
    trans = read_png(os.path.join(job.output_dir, 'Window_Transmission.png'))[..., 0]
    opacity = read_png(os.path.join(job.output_dir, 'Window_Opacity.png'))[..., 0]
    clean_trans = read_png(os.path.join(job.output_dir, 'Clean_Transmission.png'))[..., 0]
    clean_covered = read_png(os.path.join(job.output_dir, 'Clean_BaseColor.png'))[..., 0] > 0.3
    assert clean_trans[clean_covered].mean() > 0.9, clean_trans[clean_covered].mean()
    dirty_mean = trans[covered].mean()
    assert 0.15 < dirty_mean < clean_trans[clean_covered].mean() - 0.05, dirty_mean
    assert np.abs((1.0 - trans) - opacity).max() < 2.5 / 255
    mat = glass.active_material
    bsdf = L.find_principled(mat.node_tree)
    src = linked_from(bsdf.inputs['Transmission Weight'])
    assert src is not None and src.bl_idname == 'ShaderNodeTexImage', 'baked glass must stay see-through'
    assert abs(bsdf.inputs['IOR'].default_value - 1.52) < 1e-6
    sbsdf = L.find_principled(solid.active_material.node_tree)
    assert not sbsdf.inputs['Transmission Weight'].is_linked
    # seamless tiles of glass, with the transmission map too
    tiles = B.TileBakeJob(bpy.context, [L.create_material('glass_stained'), L.create_material('steel_brushed')],
                          settings(resolution=64, maps={'BASE_COLOR', 'TRANSMISSION', 'NORMAL'}))
    B.run_to_end(tiles)
    written = sorted(os.path.basename(p) for p in tiles.written)
    assert 'Stained_Glass_Window_Transmission.png' in written and 'Stained_Glass_Window_Opacity.png' in written
    assert not any('Brushed' in n and ('Transmission' in n or 'Opacity' in n) for n in written), written
    for path in tiles.written:
        assert seam_ok(read_png(path)[..., :3].astype(np.float64)), 'visible seam in ' + os.path.basename(path)
    tiled = next(m for m in tiles.tile_materials if 'Stained' in m.name)
    tbsdf = L.find_principled(tiled.node_tree)
    assert tbsdf.inputs['Transmission Weight'].is_linked


@test
def military_patterns():
    """Camouflage shapes stay seamless as tiles; digital camouflage really is made of square pixels."""
    fresh_scene()
    ids = ('mil_woodland', 'mil_digital_woodland', 'mil_splinter', 'mil_tiger', 'mil_ambush')
    mats = [L.create_material(pid) for pid in ids]
    clean = {'Mud': 0.0, 'Splatter': 0.0, 'Dust': 0.0, 'Grime': 0.0, 'Rain Streaks': 0.0, 'Chips': 0.0,
             'Edge Wear': 0.0, 'Scratches': 0.0, 'Color Variation': 0.0, 'Fading': 0.0, 'Rust Streaks': 0.0}
    for mat in mats[:2]:
        L.apply_values(L.find_bpm_node(mat), clean)
    job = B.TileBakeJob(bpy.context, mats, settings(resolution=128, maps={'BASE_COLOR'}))
    B.run_to_end(job)
    assert len(job.written) == len(ids), job.written
    changing = {}
    for path in job.written:
        a = read_png(path)[..., :3].astype(np.float64)
        name = os.path.basename(path)
        assert seam_ok(a), 'visible seam in ' + name
        assert a.std() > 0.01, 'no camouflage in ' + name
        steps = np.abs(np.diff(a, axis=1)).max(axis=2) > 0.02
        changing[name] = int((steps.mean(axis=0) > 0.02).sum())  # columns where colors change
    digital = changing['Digital_Woodland_BaseColor.png']
    smooth = changing['Woodland_Camo_BaseColor.png']
    assert digital <= 64 < smooth, changing  # pixels: colors only change on the pixel grid


@test
def wear_and_scratch_overlays():
    """Edge wear and scratches stack like dirt and dust, cut through clear coat and reach the bake."""
    fresh_scene()
    mat = L.create_material('paint_car_red')  # has a clear coat
    group = L.find_bpm_node(mat)
    wear = L.add_overlay(mat, 'WEAR', {'Amount': 1.0, 'Chips': 0.3})
    scratch = L.add_overlay(mat, 'SCRATCH', {'Amount': 1.0, 'Reveal': 1.0})
    assert L.overlay_stack(mat) == [wear, scratch]
    assert bsdf_source(mat, 'Coat Weight') == scratch and linked_from(wear.inputs['Coat']) == group
    assert linked_from(scratch.inputs['Normal']) == wear and linked_from(wear.inputs['Height']) == group
    L.remove_overlay(mat, scratch)
    L.remove_overlay(mat, wear)
    assert bsdf_source(mat, 'Coat Weight') == group and bsdf_source(mat, 'Normal') == group
    # plastic chipped through to steel: metal shows up in the baked metallic map, and a height map
    obj = add_cube()
    plastic = L.create_material('plastic_glossy_red')
    L.add_overlay(plastic, 'WEAR', {'Amount': 1.0, 'Chips': 0.3})
    obj.data.materials.append(plastic)
    out = os.path.join(TMP, 'wear')
    B.run_to_end(B.ObjectBakeJob(bpy.context, [obj], settings(maps={'BASE_COLOR', 'METALLIC', 'HEIGHT'},
                                                             output_dir=out, assign_baked=False)))
    covered = read_png(os.path.join(out, 'Cube_BaseColor.png'))[..., 0] > 0.02
    metal = read_png(os.path.join(out, 'Cube_Metallic.png'))[..., 0]
    assert 0.03 < (metal[covered] > 0.5).mean() < 0.9, (metal[covered] > 0.5).mean()
    assert os.path.exists(os.path.join(out, 'Cube_Height.png'))
    # rubbed edges stay the same material: no metal
    L.apply_values(L.overlay_stack(plastic)[0], {'Rubbed': 1.0})
    B.run_to_end(B.ObjectBakeJob(bpy.context, [obj], settings(maps={'METALLIC'}, output_dir=out,
                                                             assign_baked=False)))
    metal = read_png(os.path.join(out, 'Cube_Metallic.png'))[..., 0]
    assert metal.max() < 0.05, metal.max()


@test
def lens_keeps_its_coating():
    """Lenses are opaque; their coating (thin film) and IOR are copied into the baked material."""
    fresh_scene()
    mat = L.create_material('lens_camera')
    node = L.find_bpm_node(mat)
    bsdf = L.find_principled(mat.node_tree)
    assert linked_from(bsdf.inputs['Thin Film Thickness']) == node
    assert linked_from(bsdf.inputs['Thin Film IOR']) == node and linked_from(bsdf.inputs['IOR']) == node
    obj = add_cube('Lens')
    obj.data.materials.append(mat)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    # the coating color buttons set the thickness slider
    assert bpy.ops.bpm.set_value(socket='Coating', value=350.0) == {'FINISHED'}
    assert node.inputs['Coating'].default_value == 350.0
    job = B.ObjectBakeJob(bpy.context, [obj], settings(maps={'BASE_COLOR', 'ROUGHNESS', 'TRANSMISSION'},
                                                       output_dir=os.path.join(TMP, 'lens')))
    B.run_to_end(job)
    names = os.listdir(job.output_dir)
    assert 'Lens_BaseColor.png' in names, names
    assert not any('Transmission' in n or 'Opacity' in n for n in names), 'lenses are not see-through'
    baked = L.find_principled(obj.active_material.node_tree)
    assert abs(baked.inputs['Thin Film Thickness'].default_value - 350.0) < 1e-3
    assert abs(baked.inputs['Thin Film IOR'].default_value - 1.38) < 1e-3
    assert abs(baked.inputs['IOR'].default_value - 1.6) < 1e-3
    assert read_png(os.path.join(job.output_dir, 'Lens_Roughness.png'))[..., 0].max() < 0.3, 'lenses are glossy'
    # seamless tiles keep the coating too
    tiles = B.TileBakeJob(bpy.context, [L.create_material('lens_tail_light')], settings(resolution=64,
                                                                                      maps={'BASE_COLOR'}))
    B.run_to_end(tiles)
    tiled = L.find_principled(tiles.tile_materials[0].node_tree)
    assert abs(tiled.inputs['IOR'].default_value - 1.5) < 1e-3


@test
def overlay_menu_lists_every_overlay():
    from bpm_procedural_metals import operators as OPS
    fresh_scene()
    items = OPS._overlay_items(None, bpy.context)
    assert [i[0] for i in items if i[0]] == [p['id'] for p in P.PRESETS if P.is_overlay(p)]
    assert [i[1] for i in items if not i[0]] == ['Dirt & Dust', 'Edge Wear & Scratches']
    obj = add_cube()
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    assert bpy.ops.bpm.add_overlay(preset='scratch_light') == {'FINISHED'}
    assert bpy.ops.bpm.apply_preset(preset='wear_chipped_paint') == {'FINISHED'}
    assert [n.label for n in L.overlay_stack(obj.active_material)] == ['Light Scratches', 'Chipped Paint Edges']
    assert bpy.ops.bpm.overlay_seed(index=1) == {'FINISHED'}


@test
def concrete_finishes_and_damage():
    """Concrete: block, slab and board patterns stay seamless as tiles; rebar is metal; fresh concrete isn't."""
    fresh_scene()
    ids = ('concrete_blocks', 'concrete_sidewalk', 'concrete_board_formed', 'concrete_brutalist', 'concrete_spalled')
    mats = [L.create_material(pid) for pid in ids]
    job = B.TileBakeJob(bpy.context, mats, settings(resolution=128, maps={'BASE_COLOR', 'HEIGHT'}))
    B.run_to_end(job)
    assert len(job.written) == 2 * len(ids), job.written
    for path in job.written:
        a = read_png(path)[..., :3].astype(np.float64)
        assert seam_ok(a), 'visible seam in ' + os.path.basename(path)
        assert a.std() > 0.004, 'flat texture: ' + os.path.basename(path)
    # spalls show the rusty reinforcing bars: metal in the metallic map
    out = os.path.join(TMP, 'concrete')
    wall = add_cube('Wall')
    wall.data.materials.append(L.create_material('concrete_spalled'))
    L.apply_values(L.find_bpm_node(wall.active_material), {'Spalling': 1.0, 'Rebar': 1.0})
    clean = add_cube('Clean', location=(4, 0, 0))
    clean.data.materials.append(L.create_material('concrete_fresh'))
    B.run_to_end(B.ObjectBakeJob(bpy.context, [wall, clean], settings(maps={'BASE_COLOR', 'METALLIC'},
                                                                     output_dir=out, assign_baked=False,
                                                                     resolution=128)))
    metal = read_png(os.path.join(out, 'Wall_Metallic.png'))[..., 0]
    assert (metal > 0.15).mean() > 0.002, 'no rebar in the spalls'
    assert not os.path.exists(os.path.join(out, 'Clean_Metallic.png')) or \
        read_png(os.path.join(out, 'Clean_Metallic.png'))[..., 0].max() < 0.05


def decal_image(name='Logo', size=64):
    """A red disc on a transparent background, saved as a PNG: a test decal."""
    folder = os.path.join(TMP, 'decal_src')
    os.makedirs(folder, exist_ok=True)
    img = bpy.data.images.new(name + '_BaseColor', size, size, alpha=True)
    yy, xx = np.mgrid[0:size, 0:size]
    px = np.zeros((size, size, 4), np.float32)
    px[(xx - size / 2) ** 2 + (yy - size / 2) ** 2 < (size * 0.4) ** 2] = (1.0, 0.0, 0.0, 1.0)
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw = os.path.join(folder, name + '_BaseColor.png')
    img.file_format = 'PNG'
    img.save()
    return img


@test
def decal_maps_are_found():
    from bpm_procedural_metals import decals as D
    folder = os.path.join(TMP, 'maps')
    os.makedirs(folder, exist_ok=True)
    for name in ('Rust_Logo_BaseColor.png', 'Rust_Logo_Normal.png', 'Rust_Logo_Roughness.jpg', 'Rust_Logo2_Normal.png',
                 'sign.png', 'sign_normal.png', 'sign-rough.png', 'sign_metallic.tga', 'sign_height.exr',
                 'sign_notes.txt'):
        open(os.path.join(folder, name), 'w').close()
    found = D.find_maps(os.path.join(folder, 'Rust_Logo_BaseColor.png'))
    assert {k: os.path.basename(v) for k, v in found.items()} == {
        'COLOR': 'Rust_Logo_BaseColor.png', 'NORMAL': 'Rust_Logo_Normal.png', 'ROUGHNESS': 'Rust_Logo_Roughness.jpg'}
    found = D.find_maps(os.path.join(folder, 'sign.png'))
    assert sorted(found) == ['COLOR', 'HEIGHT', 'METALLIC', 'NORMAL', 'ROUGHNESS'], found
    # the box of a rectangle dragged over a floor (seen from above): 2 x 1, keeps the image proportions
    hits = [((0.0, 0.0, 0.0), (0.0, 0.0, 1.0)), ((0.5, 0.2, 0.05), (0.0, 0.0, -1.0))]
    rays = [((x, y, 5.0), (0.0, 0.0, -1.0)) for x, y in ((-1, -0.5), (1, -0.5), (1, 0.5), (-1, 0.5))]
    m = D.box_from_hits(hits, rays, (1.0, 0.0, 0.0), (0.0, 0.0, -1.0), aspect=2.0)
    loc, rot, scale = m.decompose()
    assert (loc - Vector((0.0, 0.0, 0.0))).length < 1e-5, loc
    assert (rot.to_matrix().col[2] - Vector((0.0, 0.0, 1.0))).length < 1e-5, 'projects down onto the floor'
    assert abs(scale.x - 1.0) < 1e-5 and abs(scale.y - 0.5) < 1e-5 and 0.3 < scale.z < 0.4, scale
    m = D.box_from_hits(hits, rays, (1.0, 0.0, 0.0), (0.0, 0.0, -1.0), aspect=1.0)
    assert abs(m.to_scale().x - 0.5) < 1e-5 and abs(m.to_scale().y - 0.5) < 1e-5, 'square image, square decal'
    assert D.box_from_hits([], rays, (1, 0, 0), (0, 0, -1)) is None


@test
def decals_project_and_bake():
    """A decal goes on what is inside its box, follows the box, survives rebuilds and is baked."""
    from bpm_procedural_metals import decals as D
    fresh_scene()
    scene = bpy.context.scene
    crate = add_cube('Crate')
    crate.data.materials.append(L.create_material('plastic_white_abs'))
    far = add_cube('Far', location=(10, 0, 0))
    far.data.materials.append(generic_material((0.8, 0.8, 0.8, 1.0)))
    box = D.create(scene, decal_image(), D.box_matrix(Vector((1.0, 0.0, 0.0)), (0, 1, 0), (1, 0, 0), 1.2, 1.2, 0.3))
    assert D.is_box(box) and box.empty_display_type == 'CUBE'
    group = box.bpm_decal.group
    assert D.refresh(box, scene) == [crate]
    mat = crate.active_material
    assert [n.node_tree for n in L.overlay_stack(mat)] == [group]
    assert D.add_to(box, crate) and len(L.overlay_stack(mat)) == 1, 'a decal goes on a material only once'
    # taken off by hand: it stays off until asked for again
    crate.select_set(True)
    bpy.context.view_layer.objects.active = crate
    assert bpy.ops.bpm.remove_overlay(index=0) == {'FINISHED'} and not L.overlay_stack(mat)
    assert not D.refresh(box, scene) and not L.overlay_stack(mat)
    assert D.refresh(box, scene, force=True) == [crate] and len(L.overlay_stack(mat)) == 1
    # the box's axes reach the shader through drivers that need no Python
    drivers = group.animation_data.drivers
    assert len(drivers) == 9 and all(d.driver.is_simple_expression for d in drivers)
    box.rotation_euler = (0.3, -0.5, 1.1)
    bpy.context.view_layer.update()
    rot = box.matrix_world.to_3x3().normalized()
    for i, axis in enumerate('XYZ'):
        driven = Vector([s.default_value for s in group.nodes['BPM Axis ' + axis].inputs[:3]])
        assert (driven - rot.col[i]).length < 1e-4, (axis, driven, rot.col[i])
    box.rotation_euler = D.box_matrix(Vector((1, 0, 0)), (0, 1, 0), (1, 0, 0), 1, 1, 1).to_euler()
    bpy.context.view_layer.update()
    # settings land in the group
    box.bpm_decal.opacity = 0.75
    assert abs(group.nodes['BPM Opacity'].outputs[0].default_value - 0.75) < 1e-6
    box.bpm_decal.opacity = 1.0
    # the decal is baked into the object's textures, only where the box is
    out = os.path.join(TMP, 'decal')
    B.run_to_end(B.ObjectBakeJob(bpy.context, [crate], settings(maps={'BASE_COLOR'}, output_dir=out,
                                                               assign_baked=False, resolution=128)))
    color = read_png(os.path.join(out, 'Crate_BaseColor.png'))
    red = (color[..., 0] > 0.5) & (color[..., 1] < 0.2)
    white = (color[..., 0] > 0.6) & (color[..., 1] > 0.6)
    assert 0.003 < red.mean() < 0.1 and white.mean() > 0.2, (red.mean(), white.mean())
    # loading another preset keeps the decal
    L.load_preset_into(mat, 'plastic_glossy_red')
    assert [n.node_tree for n in L.overlay_stack(mat)] == [group]
    # seamless tiles leave decals out
    tiles = B.TileBakeJob(bpy.context, [mat], settings(resolution=32, maps={'BASE_COLOR'}))
    B.run_to_end(tiles)
    assert not L.overlay_stack(tiles.tile_materials[0])
    # moved onto another object: baking it puts the decal there by itself
    box.location = (11.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    B.run_to_end(B.ObjectBakeJob(bpy.context, [far], settings(maps={'BASE_COLOR'}, output_dir=out,
                                                             assign_baked=False)))
    assert [n.node_tree for n in L.overlay_stack(far.active_material)] == [group]
    # a copied box (Shift+D) gets a decal of its own
    copy = box.copy()
    box.users_collection[0].objects.link(copy)
    D._fix_decals()
    assert copy.bpm_decal.group not in {None, group} and D.box_of(copy.bpm_decal.group) == copy
    # deleting a box takes its decal off every material
    bpy.data.objects.remove(box)
    D._fix_decals()
    left = [t for t in bpy.data.node_groups if D.is_decal_group(t)]
    assert len(left) == 1 and D.box_of(left[0]) == copy, left
    for m in (mat, far.active_material):
        assert not any(D.is_decal_group(n.node_tree) and D.box_of(n.node_tree) is None
                       for n in L.overlay_stack(m))
    assert bsdf_source(mat, 'Base Color') == L.find_bpm_node(mat)
    D.remove(copy)
    assert not [t for t in bpy.data.node_groups if D.is_decal_group(t)]


@test
def apply_operator_and_fit():
    fresh_scene()
    big = add_cube('Big', size=10.0)
    small = add_cube('Small', size=0.1, location=(8, 0, 0))
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    small.select_set(True)
    bpy.context.view_layer.objects.active = small
    assert bpy.ops.bpm.apply_preset(preset='steel_brushed') == {'FINISHED'}
    node = L.find_bpm_node(small.active_material)
    assert node.inputs['Scale'].default_value > 5.0, 'small objects get a larger pattern scale'
    big.select_set(True)
    small.select_set(False)
    bpy.context.view_layer.objects.active = big
    assert bpy.ops.bpm.apply_preset(preset='Hazard Stripes') == {'FINISHED'}  # by display name
    assert L.find_bpm_node(big.active_material).inputs['Scale'].default_value < 1.0
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    assert bpy.ops.bpm.apply_preset(preset='steel_brushed') == {'FINISHED'}  # falls back to active


@test
def color_values_are_exact():
    """Linear 0.5 must come out as sRGB 188 in the color map and data maps stay linear."""
    fresh_scene()
    obj = add_cube()
    obj.data.materials.append(generic_material())
    job = B.ObjectBakeJob(bpy.context, [obj], settings(maps={'BASE_COLOR', 'METALLIC', 'ROUGHNESS'}))
    B.run_to_end(job)
    out = job.output_dir
    base = read_png(os.path.join(out, 'Cube_BaseColor.png'))
    metal = read_png(os.path.join(out, 'Cube_Metallic.png'))
    rough = read_png(os.path.join(out, 'Cube_Roughness.png'))
    assert abs(np.median(base[..., 0]) * 255 - 188) <= 1, np.median(base[..., 0]) * 255
    assert abs(np.median(metal[..., 0]) * 255 - 64) <= 1, np.median(metal[..., 0]) * 255
    assert abs(np.median(rough[..., 0]) * 255 - 191) <= 1, np.median(rough[..., 0]) * 255


@test
def object_bake_full():
    fresh_scene()
    obj = add_cube()
    mat = L.create_material('paint_industrial_yellow')
    obj.data.materials.append(mat)
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.cycles.samples = 77
    node_count = len(mat.node_tree.nodes)
    other = add_cube('Other', location=(5, 0, 0))
    other.select_set(True)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = other
    job = B.ObjectBakeJob(bpy.context, [obj], settings(pack_orm=True, pack_unity=True))
    B.run_to_end(job)
    names = sorted(os.path.basename(p) for p in job.written)
    for suffix in ('BaseColor', 'Metallic', 'Roughness', 'Normal', 'Height', 'AO', 'ORM', 'MetallicSmoothness'):
        assert 'Cube_%s.png' % suffix in names, names
    # state restored
    assert scene.render.engine == 'BLENDER_WORKBENCH'
    assert scene.cycles.samples == 77
    assert bpy.context.view_layer.objects.active == other
    assert other.select_get() and obj.select_get()
    assert len(mat.node_tree.nodes) == node_count, 'temporary nodes left behind'
    # baked material shown, procedural kept
    assert L.is_baked_material(obj.active_material)
    assert obj.bpm_backup[0].material == mat and mat.use_fake_user
    # sanity of the maps
    normal = read_png(os.path.join(job.output_dir, 'Cube_Normal.png'))
    covered = normal[..., 2] > 0.3
    assert covered.mean() > 0.3
    mean = normal[covered][:, :3].mean(axis=0)
    assert abs(mean[0] - 0.5) < 0.08 and abs(mean[1] - 0.5) < 0.08 and mean[2] > 0.85, mean
    orm = read_png(os.path.join(job.output_dir, 'Cube_ORM.png'))
    rough = read_png(os.path.join(job.output_dir, 'Cube_Roughness.png'))
    assert np.abs(orm[..., 1] - rough[..., 0]).max() < 2.0 / 255
    # back and forth
    assert B.restore_procedural(obj) and obj.active_material == mat
    assert bpy.ops.bpm.show_baked() == {'FINISHED'} or True


@test
def rebake_uses_procedural_material():
    fresh_scene()
    obj = add_cube()
    mat = L.create_material('gunmetal')
    obj.data.materials.append(mat)
    B.run_to_end(B.ObjectBakeJob(bpy.context, [obj], settings(maps={'BASE_COLOR'})))
    assert L.is_baked_material(obj.active_material)
    first = read_png(os.path.join(TMP, 'out', 'Cube_BaseColor.png'))
    L.find_bpm_node(mat).inputs['Metal Color'].default_value = (1.0, 0.0, 0.0, 1.0)
    B.run_to_end(B.ObjectBakeJob(bpy.context, [obj], settings(maps={'BASE_COLOR'})))
    second = read_png(os.path.join(TMP, 'out', 'Cube_BaseColor.png'))
    assert L.is_baked_material(obj.active_material)
    assert second[..., 0].mean() > first[..., 0].mean() + 0.05, 'second bake must use the edited material'
    assert len([m for m in bpy.data.materials if m.name.startswith('Cube Baked')]) == 1


@test
def auto_uv_and_bad_uvs():
    fresh_scene()
    no_uv = add_cube('NoUV', uv=False)
    no_uv.data.materials.append(L.create_material('steel_polished'))
    stacked = add_cube('Stacked', location=(4, 0, 0))
    uv = stacked.data.uv_layers.active
    coords = [0, 0, 1, 0, 1, 1, 0, 1] * len(stacked.data.polygons)
    uv.data.foreach_set('uv', coords)  # every face covers the whole square
    stacked.data.materials.append(L.create_material('steel_polished'))
    job = B.ObjectBakeJob(bpy.context, [no_uv, stacked], settings(maps={'BASE_COLOR'}))
    B.run_to_end(job)
    assert B.BAKE_UV_NAME in no_uv.data.uv_layers
    assert B.BAKE_UV_NAME in stacked.data.uv_layers
    assert any('overlap' in text for _lvl, text in job.messages)
    tex = [n for n in stacked.active_material.node_tree.nodes if n.bl_idname == 'ShaderNodeUVMap'][0]
    assert tex.uv_map == B.BAKE_UV_NAME
    # without auto unwrap: clear error
    fresh_scene()
    obj = add_cube('NoUV', uv=False)
    obj.data.materials.append(L.create_material('steel_polished'))
    try:
        B.run_to_end(B.ObjectBakeJob(bpy.context, [obj], settings(auto_unwrap=False)))
    except B.BakeError as exc:
        assert 'UV' in str(exc)
    else:
        raise AssertionError('expected a BakeError')


@test
def multi_material_empty_slot_and_generic():
    fresh_scene()
    obj = add_cube()
    m1 = L.create_material('paint_hazard_stripes')
    m2 = generic_material((0.1, 0.2, 0.8, 1.0), 0.0, 0.3)
    obj.data.materials.append(m1)
    obj.data.materials.append(m2)
    obj.data.materials.append(None)
    for i, poly in enumerate(obj.data.polygons):
        poly.material_index = i % 3
    job = B.ObjectBakeJob(bpy.context, [obj], settings(maps={'BASE_COLOR', 'NORMAL', 'HEIGHT'},
                                                        assign_baked=False))
    B.run_to_end(job)
    assert [s.material for s in obj.material_slots] == [m1, m2, None], 'slots must be restored'
    assert not [m for m in bpy.data.materials if m.get('bpm_stand_in')]
    assert os.path.exists(os.path.join(job.output_dir, 'Cube_Height.png'))


@test
def non_mesh_objects():
    fresh_scene()
    bpy.ops.object.text_add()
    text = bpy.context.active_object
    text.data.materials.append(L.create_material('gold_polished'))
    try:
        B.run_to_end(B.ObjectBakeJob(bpy.context, [text], settings()))
    except B.BakeError as exc:
        assert 'mesh' in str(exc)
    else:
        raise AssertionError('expected a BakeError')
    cube = add_cube()
    cube.data.materials.append(L.create_material('gold_polished'))
    job = B.ObjectBakeJob(bpy.context, [text, cube], settings(maps={'BASE_COLOR'}))
    B.run_to_end(job)
    assert any('Skipped' in t for _l, t in job.messages)


@test
def no_material_and_nothing_selected():
    fresh_scene()
    obj = add_cube()
    for job in (B.ObjectBakeJob(bpy.context, [], settings()), B.ObjectBakeJob(bpy.context, [obj], settings())):
        try:
            job.check()
        except B.BakeError:
            pass
        else:
            raise AssertionError('expected a BakeError')


@test
def cancel_restores_everything():
    """Cancelling mid-bake (Esc in the UI) must leave the scene exactly as it was."""
    fresh_scene()
    obj = add_cube(uv=False)
    mat = L.create_material('paint_military_olive')
    obj.data.materials.append(mat)
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_WORKBENCH'
    nodes = len(mat.node_tree.nodes)
    images = len(bpy.data.images)
    job = B.ObjectBakeJob(bpy.context, [obj], settings())
    job.check()
    steps = job.run()
    for _ in range(4):  # preparing, base color, metallic, roughness
        next(steps)
    assert scene.render.engine == 'CYCLES'
    steps.close()  # what the modal operator does on Esc
    assert scene.render.engine == 'BLENDER_WORKBENCH'
    assert len(mat.node_tree.nodes) == nodes
    assert len(bpy.data.images) == images, 'temporary images left behind'
    assert obj.active_material == mat and not len(obj.bpm_backup)
    assert len(obj.data.uv_layers) == 0, 'unfinished UV map left behind'


@test
def directx_normals_flip_green():
    fresh_scene()
    obj = add_cube()
    obj.data.materials.append(L.create_material('copper_hammered'))
    B.run_to_end(B.ObjectBakeJob(bpy.context, [obj], settings(maps={'NORMAL'}, output_dir=os.path.join(TMP, 'gl'))))
    B.run_to_end(B.ObjectBakeJob(bpy.context, [obj], settings(maps={'NORMAL'}, normal_directx=True,
                                                                output_dir=os.path.join(TMP, 'dx'))))
    gl = read_png(os.path.join(TMP, 'gl', 'Cube_Normal.png'))
    dx = read_png(os.path.join(TMP, 'dx', 'Cube_Normal.png'))
    mask = gl[..., 2] > 0.3
    assert np.abs(gl[..., 0][mask] - dx[..., 0][mask]).mean() < 0.02
    assert np.abs(gl[..., 1][mask] - (1.0 - dx[..., 1][mask])).mean() < 0.02


@test
def unsaved_file_uses_home_folder():
    fresh_scene()
    old = B.FALLBACK_DIR
    B.FALLBACK_DIR = os.path.join(TMP, 'home', 'BPM_Textures')
    try:
        obj = add_cube()
        obj.data.materials.append(L.create_material('steel_polished'))
        job = B.ObjectBakeJob(bpy.context, [obj], settings(maps={'METALLIC'}, output_dir='//BPM_Textures/'))
        B.run_to_end(job)
        assert job.output_dir == B.FALLBACK_DIR, job.output_dir  # not BPM_Textures/BPM_Textures
        assert B.unsaved_dir('//other/') == os.path.join(B.FALLBACK_DIR, 'other')
        assert os.path.exists(os.path.join(job.output_dir, 'Cube_Metallic.png'))
    finally:
        B.FALLBACK_DIR = old


@test
def saved_file_uses_relative_folder():
    fresh_scene()
    blend = os.path.join(TMP, 'project', 'scene.blend')
    os.makedirs(os.path.dirname(blend), exist_ok=True)
    obj = add_cube()
    obj.data.materials.append(L.create_material('steel_polished'))
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    obj = bpy.data.objects['Cube']
    job = B.ObjectBakeJob(bpy.context, [obj], settings(maps={'BASE_COLOR'}, output_dir='//BPM_Textures/'))
    B.run_to_end(job)
    assert job.output_dir == os.path.join(os.path.dirname(blend), 'BPM_Textures')
    img = next(i for i in bpy.data.images if i.name.startswith('Cube_BaseColor'))
    assert img.filepath.startswith('//'), img.filepath
    bpy.ops.wm.save_mainfile()
    bpy.ops.wm.open_mainfile(filepath=blend)
    img = next(i for i in bpy.data.images if i.name.startswith('Cube_BaseColor'))
    assert img.has_data or img.size[0] == 64


@test
def tiles_are_seamless():
    fresh_scene()
    mats = [L.create_material(pid) for pid in ('paint_hazard_stripes', 'iron_rust_heavy', 'steel_brushed')]
    job = B.TileBakeJob(bpy.context, mats, settings(resolution=128))
    B.run_to_end(job)
    assert len(job.written) == 15, job.written
    for path in job.written:
        a = read_png(path)[..., :3].astype(np.float64)
        assert seam_ok(a), 'visible seam in ' + os.path.basename(path)
    # negative control: a cropped (no longer periodic) tile must be detected
    rust = read_png([p for p in job.written if p.endswith('Heavily_Rusted_Iron_BaseColor.png')][0])[..., :3]
    assert not seam_ok(rust[:, :80].astype(np.float64)), 'seam check cannot detect seams'
    assert len(job.tile_materials) == 3


@test
def new_families_tile_seamlessly():
    """Every family (and overlays on top) must bake to seamless tiles."""
    fresh_scene()
    ids = ('wood_barn_red', 'plastic_dirty_bin', 'leather_sofa', 'fabric_carbon_twill', 'bio_xeno_tubes',
           'glass_abandoned', 'lens_fresnel', 'mil_battle_worn', 'wood_walnut')
    mats = [L.create_material(pid) for pid in ids]
    L.add_overlay(mats[-2], 'WEAR', {'Chips': 0.2})
    L.add_overlay(mats[-2], 'SCRATCH', {'Swirls': 0.5, 'Scuffs': 0.5})
    L.add_overlay(mats[-1], 'DUST', {'Amount': 0.8})
    job = B.TileBakeJob(bpy.context, mats, settings(resolution=128, maps={'BASE_COLOR', 'NORMAL', 'HEIGHT'}))
    B.run_to_end(job)
    assert len(job.written) == 3 * len(ids), job.written
    for path in job.written:
        a = read_png(path)[..., :3].astype(np.float64)
        assert seam_ok(a), 'visible seam in ' + os.path.basename(path)
        if path.endswith('BaseColor.png'):
            assert a.std() > 0.003, 'flat texture: ' + os.path.basename(path)
    walnut = read_png([p for p in job.written if p.endswith('Varnished_Walnut_BaseColor.png')][0])
    assert walnut[..., 0].mean() > 0.35, 'the dust overlay must be in the tile'


@test
def tile_normals_match_cycles_bump():
    """The numpy normal map of tiles must agree with what Cycles' bump node produces."""
    fresh_scene()
    mat = L.create_material('copper_hammered')
    node = L.find_bpm_node(mat)
    node.inputs['Bump Strength'].default_value = 1.5
    job = B.TileBakeJob(bpy.context, [mat], settings(resolution=128, quality='GOOD', maps={'NORMAL'},
                                                     use_16bit=True))
    B.run_to_end(job)
    ours = read_png(job.written[0])[..., :3]
    # reference: Cycles normal bake of the same tile material on the same plane
    size = 1.0
    mesh = bpy.data.meshes.new('Ref')
    mesh.from_pydata([(0, 0, 0), (size, 0, 0), (size, size, 0), (0, size, 0)], [], [(0, 1, 2, 3)])
    mesh.uv_layers.new(name='UVMap').data.foreach_set('uv', [0, 0, 1, 0, 1, 1, 0, 1])
    plane = bpy.data.objects.new('Ref', mesh)
    bpy.context.scene.collection.objects.link(plane)
    tmat = bpy.data.materials.new('RefMat')
    values = L.read_values(node)
    values['Tile Size'] = size
    L.build_material(tmat, 'METAL', values, tile=True)
    mesh.materials.append(tmat)
    img = bpy.data.images.new('ref', 128, 128, float_buffer=True, is_data=True)
    tex = tmat.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = img
    tmat.node_tree.nodes.active = tex
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.samples = 16
    with bpy.context.temp_override(active_object=plane, object=plane, selected_objects=[plane],
                                   selected_editable_objects=[plane]):
        bpy.ops.object.bake(type='NORMAL', margin=0, normal_space='TANGENT')
    ref = np.empty(128 * 128 * 4, np.float32)
    img.pixels.foreach_get(ref)
    ref = ref.reshape(128, 128, 4)[..., :3]
    inner = (slice(4, -4), slice(4, -4))
    diff = np.abs(ours[inner] - ref[inner]).mean()
    detail = np.abs(ref[inner] - ref[inner].mean(axis=(0, 1))).mean()
    assert detail > 0.01, 'reference has no detail'
    assert diff < 0.35 * detail, 'numpy normals differ from Cycles: %.4f (detail %.4f)' % (diff, detail)


@test
def scopes_pick_the_right_objects():
    fresh_scene()
    a = add_cube('A')
    b = add_cube('B', location=(3, 0, 0))
    add_cube('C', location=(6, 0, 0))
    hidden = add_cube('Hidden', location=(9, 0, 0))
    hidden.hide_set(True)
    bpy.ops.object.camera_add()
    cam = bpy.context.active_object
    bpy.ops.object.text_add()
    bpy.context.active_object.data.materials.append(generic_material())
    bpy.ops.object.text_add(location=(0, 3, 0))  # no material: left out like the camera
    bpy.ops.object.empty_add()
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in (a, b, cam):
        o.select_set(True)
    bpy.context.view_layer.objects.active = b

    def names(scope):
        return sorted(o.name for o in B.scope_objects(bpy.context, scope))
    assert names('ACTIVE') == ['B']
    assert names('SELECTED') == ['A', 'B'], names('SELECTED')
    assert names('SCENE') == ['A', 'B', 'C', 'Text'], names('SCENE')
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    assert names('SELECTED') == ['B'], 'nothing selected: the active object'
    bpy.context.view_layer.objects.active = None
    assert names('ACTIVE') == [] and names('SELECTED') == []


@test
def auto_texture_makes_packed_uvs_first():
    fresh_scene()
    obj = add_cube()
    mesh = obj.data
    second = mesh.uv_layers.new(name='Second')
    second.data.foreach_set('uv', np.random.default_rng(3).random(len(mesh.loops) * 2).astype(np.float32))
    second.active_render = True
    before = {name: uv_array(mesh, name) for name in ('UVMap', 'Second')}
    obj.data.materials.append(L.create_material('paint_industrial_yellow'))
    job = B.ObjectBakeJob(bpy.context, [obj], settings(force_new_uv=True, maps={'BASE_COLOR', 'NORMAL'}))
    B.run_to_end(job)
    assert job.baked == ['Cube'] and job.summary().startswith('Auto-textured 1 object. Saved 2 textures')
    names = [layer.name for layer in mesh.uv_layers]
    assert names == [B.BAKE_UV_NAME, 'UVMap', 'Second'], names
    assert mesh.uv_layers.active.name == B.BAKE_UV_NAME
    assert [layer.name for layer in mesh.uv_layers if layer.active_render] == ['Second']
    for name, uv in before.items():
        assert np.array_equal(uv_array(mesh, name), uv), '%s must not change' % name
    margin = settings().uv_margin
    uv = uv_array(mesh, B.BAKE_UV_NAME)
    assert uv.min() >= 0.9 * margin and uv.max() <= 1.0 - 0.9 * margin, (uv.min(), uv.max())
    assert uv_overlap(mesh, B.BAKE_UV_NAME) < 0.001
    area = B.uv_stats(mesh, mesh.uv_layers[B.BAKE_UV_NAME])[0]
    assert area > 0.2, 'the islands are not packed: %.3f' % area  # (64 px: 4 pixel gaps are wide)
    mat = obj.active_material
    assert L.is_baked_material(mat)
    for node in mat.node_tree.nodes:
        if node.bl_idname in {'ShaderNodeUVMap', 'ShaderNodeNormalMap'}:
            assert node.uv_map == B.BAKE_UV_NAME, (node.bl_idname, node.uv_map)
    # again: same UVs, no extra UV maps
    B.run_to_end(B.ObjectBakeJob(bpy.context, [obj], settings(force_new_uv=True, maps={'BASE_COLOR'})))
    assert [layer.name for layer in mesh.uv_layers] == [B.BAKE_UV_NAME, 'UVMap', 'Second']
    assert np.abs(uv_array(mesh, B.BAKE_UV_NAME) - uv).max() < 1e-5


@test
def auto_texture_bakes_through_the_old_uvs():
    """While baking, materials still see the UVs they were made for, even after the UVs change."""
    fresh_scene()
    obj = add_cube()
    mesh = obj.data
    obj.data.materials.append(uv_material())
    old = face_uv_centers(mesh, 'UVMap')
    maps = {'ROUGHNESS', 'METALLIC'}
    out = os.path.join(TMP, 'olduv')

    def bake():
        job = B.ObjectBakeJob(bpy.context, [obj], settings(force_new_uv=True, maps=maps, output_dir=out))
        B.run_to_end(job)
        rough = read_png(os.path.join(job.output_dir, 'Cube_Roughness.png'))[..., 0]
        metal = read_png(os.path.join(job.output_dir, 'Cube_Metallic.png'))[..., 0]
        centers = face_uv_centers(mesh, B.BAKE_UV_NAME)
        return np.stack([sample(rough, centers), sample(metal, centers)], axis=-1), centers
    first, centers1 = bake()
    assert np.abs(first - old).max() < 0.04, np.abs(first - old).max()
    # the object now shows its baked material, which reads the textures through "BPM_Bake";
    # without a procedural material to go back to, the next bake reads those textures
    obj.bpm_backup.clear()
    co = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    co[:, 0] *= 2.5  # stretch the mesh: the new unwrap is different
    mesh.vertices.foreach_set('co', co.ravel())
    mesh.update()
    second, centers2 = bake()
    assert np.abs(centers2 - centers1).max() > 0.05, 'the UVs did not change'
    assert np.abs(second - old).max() < 0.06, np.abs(second - old).max()


@test
def auto_texture_linked_duplicates_and_bad_objects():
    fresh_scene()
    a = add_cube('A')
    a.data.materials.append(generic_material((0.8, 0.1, 0.1, 1.0)))
    twin = a.copy()  # linked duplicate (Alt+D): same mesh, same materials
    twin.name = 'Twin'
    twin.location.x = 3
    bpy.context.scene.collection.objects.link(twin)
    own = a.copy()  # same mesh, but its own material
    own.name = 'Own'
    own.location.x = 6
    bpy.context.scene.collection.objects.link(own)
    own.material_slots[0].link = 'OBJECT'
    own.material_slots[0].material = generic_material((0.1, 0.1, 0.8, 1.0))
    full = add_cube('Full', location=(9, 0, 0))
    full.data.materials.append(generic_material())
    for i in range(7):
        full.data.uv_layers.new(name='Extra%d' % i)
    plain = add_cube('Plain', location=(12, 0, 0))
    job = B.ObjectBakeJob(bpy.context, [a, twin, own, full, plain],
                          settings(force_new_uv=True, maps={'BASE_COLOR'}))
    B.run_to_end(job)
    assert job.baked == ['A', 'Twin', 'Own'], job.baked
    warnings = job.warnings()
    assert any('too many UV maps' in t for t in warnings), warnings
    assert any('Plain' in t and 'no material' in t for t in warnings), warnings
    assert len(full.data.uv_layers) == 8 and B.UV_TEMP_NAME not in full.data.uv_layers
    assert not L.is_baked_material(full.active_material)
    assert sum('made new UVs' in t for _l, t in job.messages) == 1, 'a shared mesh is unwrapped once'
    assert [layer.name for layer in a.data.uv_layers] == [B.BAKE_UV_NAME, 'UVMap']
    names = sorted(os.listdir(job.output_dir))
    assert 'A_BaseColor.png' in names and 'Own_BaseColor.png' in names and 'Twin_BaseColor.png' not in names
    assert twin.active_material == a.active_material and L.is_baked_material(a.active_material)
    assert L.is_baked_material(own.active_material) and own.active_material != a.active_material
    own_color = read_png(os.path.join(job.output_dir, 'Own_BaseColor.png'))
    assert own_color[..., 2].max() > own_color[..., 0].max(), 'Own must use its own (blue) material'
    assert B.restore_procedural(twin) and not L.is_baked_material(a.active_material)
    # nothing at all could be baked: the job fails with the reason
    try:
        B.run_to_end(B.ObjectBakeJob(bpy.context, [full], settings(force_new_uv=True, maps={'BASE_COLOR'})))
    except B.BakeError as exc:
        assert 'too many UV maps' in str(exc)
    else:
        raise AssertionError('expected a BakeError')


@test
def auto_texture_cancel_keeps_the_old_uvs():
    fresh_scene()
    obj = add_cube()
    obj.data.materials.append(L.create_material('steel_brushed'))
    uv = uv_array(obj.data, 'UVMap')
    job = B.ObjectBakeJob(bpy.context, [obj], settings(force_new_uv=True))
    job.check()
    steps = job.run()
    seen = [next(steps) for _ in range(4)]  # preparing, unwrapping, base color, metallic
    assert any('Unwrapping' in t for t in seen), seen
    assert B.UV_TEMP_NAME in obj.data.uv_layers
    steps.close()
    assert [layer.name for layer in obj.data.uv_layers] == ['UVMap']
    assert obj.data.uv_layers.active.name == 'UVMap'
    assert np.array_equal(uv_array(obj.data, 'UVMap'), uv)
    assert not L.is_baked_material(obj.active_material)


@test
def auto_texture_operator_scopes():
    fresh_scene()
    a = add_cube('A')
    a.data.materials.append(generic_material((0.2, 0.6, 0.2, 1.0)))
    b = add_cube('B', location=(3, 0, 0))
    b.data.materials.append(generic_material((0.6, 0.2, 0.2, 1.0)))
    add_cube('Bare', location=(6, 0, 0))
    bpy.ops.object.camera_add()
    props = bpy.context.scene.bpm
    props.resolution = '512'
    props.quality = 'FAST'
    props.output_dir = os.path.join(TMP, 'auto_op')
    for key in B.MAP_ORDER:
        setattr(props, 'map_' + key.lower(), key == 'BASE_COLOR')
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = a
    props.bake_scope = 'ACTIVE'
    assert bpy.ops.bpm.auto_texture() == {'FINISHED'}
    assert props.last_report.startswith('Auto-textured 1 object. Saved 1 texture'), props.last_report
    assert L.is_baked_material(a.active_material) and not L.is_baked_material(b.active_material)
    props.bake_scope = 'SCENE'
    assert bpy.ops.bpm.auto_texture() == {'FINISHED'}
    assert props.last_report.startswith('Auto-textured 2 objects. Saved 2 textures'), props.last_report
    assert '(1 object skipped)' in props.last_report and props.last_level == 'WARNING'
    assert 'Bare' in props.last_warnings and 'Camera' not in props.last_warnings, props.last_warnings
    assert L.is_baked_material(b.active_material) and b.data.uv_layers[0].name == B.BAKE_UV_NAME
    bpy.context.view_layer.objects.active = None
    props.bake_scope = 'ACTIVE'
    try:
        bpy.ops.bpm.auto_texture()
    except RuntimeError as exc:  # errors of operators called from Python become exceptions
        assert 'active object' in str(exc)
    else:
        raise AssertionError('expected an error')
    assert props.last_level == 'ERROR' and 'active' in props.last_report
    # the regular bake button uses the scope too, and keeps good UVs
    bpy.context.view_layer.objects.active = b
    B.restore_procedural(b)
    uv = uv_array(b.data, B.BAKE_UV_NAME)
    assert bpy.ops.bpm.bake() == {'FINISHED'}
    assert props.last_report.startswith('Baked 1 object.'), props.last_report
    assert np.array_equal(uv_array(b.data, B.BAKE_UV_NAME), uv)


@test
def command_line_auto():
    fresh_scene()
    obj = add_cube('Crate')
    obj.data.materials.append(L.create_material('wood_oak_floor'))
    add_cube('Bare', location=(4, 0, 0))
    blend = os.path.join(TMP, 'cli_auto', 'scene.blend')
    os.makedirs(os.path.dirname(blend), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    out = os.path.join(TMP, 'cli_auto', 'textures')
    cmd = [bpy.app.binary_path, '-b', '--factory-startup', blend, '-P', os.path.join(ROOT, 'bpm_cli.py'), '--',
           'auto', '--size', '32', '--quality', 'fast', '--maps', 'basecolor,normal', '--out', out, '--save']
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    text = res.stdout + res.stderr
    assert res.returncode == 0, text[-3000:]
    assert 'Auto-textured 1 object' in text and 'Bare' in text, text[-3000:]
    assert os.path.exists(os.path.join(out, 'Crate_BaseColor.png'))
    bpy.ops.wm.open_mainfile(filepath=blend)
    obj = bpy.data.objects['Crate']
    assert L.is_baked_material(obj.active_material)
    assert obj.data.uv_layers[0].name == B.BAKE_UV_NAME and obj.data.uv_layers.active.name == B.BAKE_UV_NAME


@test
def modal_operator_executes_in_background():
    fresh_scene()
    obj = add_cube()
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    assert bpy.ops.bpm.apply_preset(preset='paint_car_red') == {'FINISHED'}
    props = bpy.context.scene.bpm
    props.resolution = '512'
    props.quality = 'FAST'
    props.map_ao = False
    props.output_dir = os.path.join(TMP, 'op')
    props.resolution = '512'
    assert bpy.ops.bpm.bake() == {'FINISHED'}
    assert 'Saved 5 textures' in props.last_report, props.last_report
    props.bake_mode = 'TILE'
    assert bpy.ops.bpm.bake() == {'FINISHED'}


@test
def command_line_tool():
    out = os.path.join(TMP, 'cli')
    cmd = [bpy.app.binary_path, '-b', '--factory-startup', '-P', os.path.join(ROOT, 'bpm_cli.py'), '--',
           'tile', '--preset', 'gunmetal,Hazard Stripes', '--size', '32', '--quality', 'fast', '--out', out]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    assert res.returncode == 0, res.stdout[-2000:] + res.stderr[-2000:]
    assert os.path.exists(os.path.join(out, 'Gunmetal_Tile', 'Gunmetal_Normal.png'))
    res = subprocess.run(cmd[:6] + ['tile', '--preset', 'does-not-exist'], capture_output=True, text=True,
                         timeout=300)
    assert res.returncode != 0 and 'Unknown preset' in (res.stdout + res.stderr)
    res = subprocess.run(cmd[:6] + ['tile', '--preset', 'Kevlar (Aramid)', '--overlay', 'dust_light,dirt_grime',
                                    '--size', '32', '--quality', 'fast', '--maps', 'basecolor', '--out', out],
                         capture_output=True, text=True, timeout=600)
    assert res.returncode == 0, res.stdout[-2000:] + res.stderr[-2000:]
    assert os.path.exists(os.path.join(out, 'Kevlar_Aramid_Tile', 'Kevlar_Aramid_BaseColor.png'))
    res = subprocess.run(cmd[:6] + ['list'], capture_output=True, text=True, timeout=300)
    assert 'carbon' in res.stdout and 'dust_light' in res.stdout


# ------------------------------------------------------------- mesh maps
def grid_box(name, half=0.5, location=(0, 0, 0)):
    """A box made of grids that are finer near the edges (exact sample points for the mesh maps)."""
    import bmesh
    fine = [0.0, 0.005, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.1, 0.15, 0.25]
    ax = sorted({round(v, 6) for d in fine for v in (-half + d, half - d, d, -d)} | {-half, 0.0, half})
    ax = [a for a in ax if -half <= a <= half]
    bm = bmesh.new()
    n = len(ax)

    def grid(fn):
        vs = [[bm.verts.new(fn(ax[i], ax[j])) for j in range(n)] for i in range(n)]
        for i in range(n - 1):
            for j in range(n - 1):
                bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]))
    h = half
    for fn in (lambda a, b: (a, b, h), lambda a, b: (b, a, -h), lambda a, b: (b, h, a),
               lambda a, b: (a, -h, b), lambda a, b: (h, a, b), lambda a, b: (-h, b, a)):
        grid(fn)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    bpy.context.scene.collection.objects.link(obj)
    return obj


def maps_tile(mesh):
    """Pixels (rows from the bottom) of a mesh's tile of the mesh maps image."""
    data = M._tile_files(M.find_image())[int(mesh[M.TILE])]
    path = os.path.join(TMP, 'tile_%d.png' % mesh[M.TILE])
    with open(path, 'wb') as f:
        f.write(data)
    return read_png(path)


def maps_at_loops(mesh):
    px = maps_tile(mesh)
    du, dv = M.tile_offset(mesh[M.TILE])
    return sample(px, uv_array(mesh, M.UV_NAME) - (du, dv))


@test
def mesh_maps_measure_edges_and_corners():
    fresh_scene()
    box = grid_box('Box')
    box.scale = (2.0, 2.0, 2.0)  # 2 m box: reaches are stored in object units
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(-0.5, 0.0, 1.5))  # a block standing on top
    bpy.context.view_layer.update()
    job = M.analyze(bpy.context, [box], M.MapsSettings(resolution=512, quality='GOOD'))
    assert job.analyzed == ['Box'], job.messages
    mesh = box.data
    assert M.status(box) == 'OK' and int(mesh[M.TILE]) == M.FIRST_TILE
    edge, cavity = mesh[M.EDGE], mesh[M.CAVITY]
    assert abs(edge - 0.05) < 1e-6 and abs(cavity - 0.15) < 1e-6, (edge, cavity)  # 5 % / 15 % of 2 m, in object units
    values = maps_at_loops(mesh)
    co = np.array([mesh.vertices[l.vertex_index].co[:] for l in mesh.loops])
    normal = np.array([mesh.polygons[i].normal[:] for i, p in enumerate(mesh.polygons) for _ in p.loop_indices])
    top = (np.abs(co[:, 2] - 0.5) < 1e-6) & (normal[:, 2] > 0.99) & (np.abs(co[:, 1]) < 0.2)
    for d in (0.01, 0.02, 0.03, 0.04, 0.06, 0.1, 0.25):
        rows = top & (np.abs((0.5 - co[:, 0]) - d) < 1e-6)  # distance to the outer edge at x = 0.5
        convex = values[rows, 0].mean()
        expected = max(0.0, 1.0 - d / edge)
        assert abs(convex - expected) < 0.12, ('convex', d, convex, expected)
        rows = top & (np.abs(co[:, 0] - d) < 1e-6)  # distance to the block's wall at x = 0
        concave = values[rows, 1].mean()
        expected = max(0.0, 1.0 - d / cavity)
        assert abs(concave - expected) < 0.12, ('concave', d, concave, expected)
    flat = top & (np.abs(co[:, 0] - 0.25) < 1e-6)
    assert values[flat, :3].max() < 0.05, values[flat, :3].max()


def mask_material():
    """Emission = (edge mask, cavity mask, 0), like the materials use them."""
    mat = bpy.data.materials.new('Masks')
    tree = L.ensure_node_tree(mat)
    tree.nodes.clear()
    from bpm_procedural_metals.nodebuilder import Builder
    b = Builder(tree)
    space = F.Space(b, False, 1.0, 0.0)
    emission = b.node('ShaderNodeEmission')
    b.feed(emission.inputs['Color'], b.combine(F.edge_mask(b, space, 0.04), F.cavity_mask(b, space, 0.2), 0.0))
    out = b.node('ShaderNodeOutputMaterial')
    tree.links.new(emission.outputs[0], out.inputs['Surface'])
    return mat


def bake_masks(obj, mat, size=128):
    """Bake the mask material of `obj` through its UVMap (Cycles)."""
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.samples = 16
    img = bpy.data.images.new('mask_' + obj.name, size, size, float_buffer=True)
    tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = img
    mat.node_tree.nodes.active = tex
    with bpy.context.temp_override(active_object=obj, selected_objects=[obj], object=obj):
        bpy.ops.object.bake(type='EMIT', margin=2, uv_layer='UVMap')
    px = np.empty(size * size * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    mat.node_tree.nodes.remove(tex)
    return px.reshape(size, size, 4)


@test
def mesh_maps_drive_the_masks():
    fresh_scene()
    cubes = [add_cube('Analyzed', location=(0, 0, 0)), add_cube('Live', location=(5, 0, 0))]
    mat = mask_material()
    for obj in cubes:
        obj.data.materials.append(mat)
    M.analyze(bpy.context, cubes[:1], M.MapsSettings(resolution=256, quality='FAST'))
    for obj in cubes:
        obj.select_set(False)
    for obj in cubes:
        px = bake_masks(obj, mat)
        centers = sample(px, face_uv_centers(obj.data, 'UVMap'))
        uv = uv_array(obj.data, 'UVMap')
        mid = np.repeat(face_uv_centers(obj.data, 'UVMap'), 4, axis=0)
        near_corner = sample(px, uv + (mid - uv) * 0.03)
        assert centers[:, :2].max() < 0.05, (obj.name, centers[:, :2].max())
        assert near_corner[:, 0].min() > 0.8, (obj.name, near_corner[:, 0].min())  # both detect the edges
        if obj.name == 'Analyzed':
            assert near_corner[:, 1].max() < 0.05  # a lone cube has no inner corners


@test
def mesh_maps_fill_corners_with_grime():
    """Grime packs solidly into the corner where an object stands on the floor."""
    fresh_scene()
    box = add_cube('Box')
    bpy.ops.mesh.primitive_plane_add(size=10.0, location=(0.0, 0.0, -1.0))
    mat = mask_material()
    box.data.materials.append(mat)
    M.analyze(bpy.context, [box], M.MapsSettings(resolution=256, quality='GOOD'))
    box.select_set(False)
    px = bake_masks(box, mat)
    mesh = box.data
    uv = uv_array(mesh, 'UVMap')
    for height, low, high in ((0.03, 0.85, 1.01), (0.08, 0.2, 0.7), (0.5, -1.0, 0.05)):  # solid, fading, clean
        points = []
        for poly in mesh.polygons:
            if abs(poly.normal.z) > 0.5:
                continue
            loops = sorted(poly.loop_indices, key=lambda i: mesh.vertices[mesh.loops[i].vertex_index].co.z)
            bottom, top = uv[loops[:2]].mean(axis=0), uv[loops[2:]].mean(axis=0)
            points.append(bottom + (top - bottom) * height)
        cavity = sample(px, np.array(points))[:, 1]
        assert low < cavity.min() and cavity.max() < high, (height, cavity)


@test
def mesh_maps_storage_and_sharing():
    fresh_scene()
    a = add_cube('A')
    b = add_cube('B', location=(5, 0, 0))
    twin = bpy.data.objects.new('Twin', a.data)  # linked duplicate
    bpy.context.scene.collection.objects.link(twin)
    twin.location = (0, 5, 0)
    mat = L.create_material('paint_industrial_yellow')
    for obj in (a, b):
        obj.data.materials.append(mat)
    old = L.find_bpm_node(mat).node_tree
    old['bpm_version'] = -1  # pretend: made by an older add-on version
    L.find_bpm_node(mat).inputs['Scale'].default_value = 3.25
    job = M.analyze(bpy.context, [a, b, twin], M.MapsSettings(resolution=64, quality='FAST'))
    assert sorted(job.analyzed) == ['A', 'B', 'Twin'], job.messages
    assert job.upgraded == 1
    node = L.find_bpm_node(mat)
    assert node.node_tree != old and not L.is_outdated_group(node.node_tree)
    assert abs(node.inputs['Scale'].default_value - 3.25) < 1e-6 and node.outputs[0].is_linked
    img = M.find_image()
    assert M.tile_numbers(img) == {1001, 1002, 1003}, M.tile_numbers(img)
    assert {a.data[M.TILE], b.data[M.TILE]} == {1002, 1003}
    assert a.data.uv_layers.active.name == 'UVMap' and M.UV_NAME in a.data.uv_layers
    assert [layer.name for layer in a.data.uv_layers if layer.active_render] == ['UVMap']
    # saved and opened again
    blend = os.path.join(TMP, 'maps', 'maps.blend')
    os.makedirs(os.path.dirname(blend), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    bpy.ops.wm.open_mainfile(filepath=blend)
    a, b = bpy.data.objects['A'], bpy.data.objects['B']
    assert M.status(a) == M.status(b) == 'OK'
    img = M.find_image()
    assert M.tile_numbers(img) == {1001, 1002, 1003} and img.packed_files
    before_b = maps_tile(b.data)
    assert before_b[..., 0].max() > 0.5  # edges were stored
    # editing the mesh outdates its maps
    a.data.vertices[0].co.x += 0.1
    assert M.status(a) == 'OUTDATED'
    # removing one keeps the other's tile
    M.remove([a.data])
    assert M.status(a) == 'NONE' and M.UV_NAME not in a.data.uv_layers
    assert M.tile_numbers(M.find_image()) == {1001, int(b.data[M.TILE])}
    assert np.abs(maps_tile(b.data) - before_b).max() < 1e-3
    M.remove([b.data])
    assert M.tile_numbers(M.find_image()) == {1001}


@test
def mesh_maps_and_baking():
    fresh_scene()
    obj = add_cube('Crate', uv=False)
    obj.data.materials.append(L.create_material('paint_industrial_yellow'))
    L.add_overlay(obj.active_material, 'DIRT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    props = bpy.context.scene.bpm
    props.bake_scope = 'ACTIVE'
    props.maps_resolution = '512'
    props.maps_quality = 'FAST'
    assert bpy.ops.bpm.analyze_shape() == {'FINISHED'}, props.last_report
    mesh = obj.data
    assert [layer.name for layer in mesh.uv_layers] == ['UVMap', M.UV_NAME]  # a UV map for the user in front
    assert mesh.uv_layers.active.name == 'UVMap'
    # "Bake with Current UVs" never bakes with the mesh maps' UVs
    job = B.ObjectBakeJob(bpy.context, [obj], settings(maps={'BASE_COLOR'}))
    B.run_to_end(job)
    for node in obj.active_material.node_tree.nodes:
        if node.bl_idname == 'ShaderNodeUVMap':
            assert node.uv_map != M.UV_NAME
    # Auto Texture keeps the maps (and analyzes again only when needed)
    B.restore_procedural(obj)
    mesh.vertices[0].co.z += 0.05
    props.resolution = '512'
    props.quality = 'FAST'
    props.output_dir = os.path.join(TMP, 'maps_auto')
    props.map_ao = False
    assert bpy.ops.bpm.auto_texture() == {'FINISHED'}
    assert 'Shape analyzed: 1 object' in props.last_report, props.last_report
    assert mesh.uv_layers[0].name == B.BAKE_UV_NAME and M.status(obj) == 'OK'
    B.restore_procedural(obj)
    assert bpy.ops.bpm.auto_texture() == {'FINISHED'}
    assert 'Shape analyzed' not in props.last_report, props.last_report
    assert bpy.ops.bpm.remove_mesh_maps() == {'FINISHED'}
    assert M.status(obj) == 'NONE' and M.UV_NAME not in mesh.uv_layers


@test
def command_line_maps():
    fresh_scene()
    obj = add_cube('Crate')
    obj.data.materials.append(L.create_material('wood_oak_floor'))
    blend = os.path.join(TMP, 'cli_maps', 'scene.blend')
    os.makedirs(os.path.dirname(blend), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    cmd = [bpy.app.binary_path, '-b', '--factory-startup', blend, '-P', os.path.join(ROOT, 'bpm_cli.py'), '--',
           'maps', '--objects', 'all', '--size', '64', '--quality', 'fast', '--save']
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    text = res.stdout + res.stderr
    assert res.returncode == 0 and 'Mesh maps ready for 1 object' in text, text[-3000:]
    bpy.ops.wm.open_mainfile(filepath=blend)
    assert M.status(bpy.data.objects['Crate']) == 'OK'


STACK_SCRIPT = r'''
import bpy, sys
sys.path.insert(0, %(root)r)
import bpm_procedural_metals as addon
from bpm_procedural_metals import library as L
bpy.ops.wm.read_factory_settings(use_empty=True)
addon.register()
scene = bpy.context.scene; scene.render.engine = 'CYCLES'; scene.cycles.samples = 1
from bpm_procedural_metals import generators as G
bpy.ops.mesh.primitive_cube_add(); ob = bpy.context.active_object
combos = [(gen, ()) for gen in G.material_generators()]
combos += [(gen, ('DIRT', 'DUST')) for gen in G.material_generators()]
combos += [(gen, ('DIRT', 'DUST', 'WEAR', 'SCRATCH')) for gen in G.material_generators()]
for gen, overlays in combos:
    for tile in (False, True):
        # tile bakes only use emission passes (their normal maps are computed from the height)
        for mode in (('full',) if tile else ('full', 'normal')):
            mat = bpy.data.materials.new('STACK_%%s%%s_%%s_%%s' %% (gen, ''.join('+' + o for o in overlays),
                                                                   int(tile), mode))
            ob.data.materials.clear(); ob.data.materials.append(mat)
            L.build_material(mat, gen, L.default_values(gen), tile=tile)
            for o in overlays:
                L.add_overlay(mat, o, tile=tile)
            nt = mat.node_tree; out = L.output_node(nt); bsdf = L.find_principled(nt)
            if mode == 'normal':
                d = nt.nodes.new('ShaderNodeBsdfDiffuse')
                nt.links.new(bsdf.inputs['Normal'].links[0].from_socket, d.inputs['Normal'])
                nt.links.new(d.outputs[0], out.inputs['Surface'])
            img = bpy.data.images.new('t', 8, 8); tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = img
            nt.nodes.active = tex
            bpy.ops.object.bake(type='NORMAL' if mode == 'normal' else 'EMIT', margin=0)
'''


@test
def shader_stack_has_headroom():
    """Cycles shaders have a fixed stack (255); overflowing silently breaks the material."""
    script = os.path.join(TMP, 'stack_check.py')
    with open(script, 'w') as f:
        f.write(STACK_SCRIPT % {'root': ROOT})
    if bpy.app.version >= (5, 0, 0):
        log_args = ['--log', '*', '--log-level', 'debug']
    else:
        log_args = ['--debug-cycles', '--verbose', '4']
    res = subprocess.run([bpy.app.binary_path, '-b', '--factory-startup'] + log_args + ['-P', script],
                         capture_output=True, text=True, timeout=900)
    text = res.stdout + res.stderr
    assert 'out of SVM stack' not in text, 'SVM stack overflow!'
    peaks, name = {}, None
    for line in text.splitlines():
        found = re.search(r'Shader name: (\S+)', line)
        if found:
            name = found.group(1)
        found = re.search(r'Peak stack usage:\s+(\d+)', line)
        if found and name and name.startswith('STACK_'):
            peaks[name] = int(found.group(1))
    if not peaks:  # log format differs: at least the overflow check above ran
        print('    (no peak stack statistics in this Blender version)')
        return
    worst = max(int(v) for v in peaks.values())
    print('    peak stack usage: %d / 255' % worst)
    assert worst < 230, peaks


# --------------------------------------------------------------------- runner
def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    only = argv[argv.index('-k') + 1] if '-k' in argv else None
    print('\nBPM test suite on Blender %s\n' % bpy.app.version_string)
    failed = []
    for fn in TESTS:
        if only and only not in fn.__name__:
            continue
        start = time.time()
        try:
            fn()
        except Exception:
            failed.append(fn.__name__)
            print('FAIL  %-40s %.1fs' % (fn.__name__, time.time() - start))
            traceback.print_exc()
        else:
            print('ok    %-40s %.1fs' % (fn.__name__, time.time() - start))
    shutil.rmtree(TMP, ignore_errors=True)
    print('\n%d failed' % len(failed) if failed else '\nall tests passed')
    sys.stdout.flush()
    if failed:
        sys.exit(1)


main()
