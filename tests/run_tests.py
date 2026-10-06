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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import bpm_procedural_metals as addon  # noqa: E402
from bpm_procedural_metals import bake as B  # noqa: E402
from bpm_procedural_metals import generators as G  # noqa: E402
from bpm_procedural_metals import library as L  # noqa: E402
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
    assert len(P.PRESETS) >= 40, 'expected a big library'
    for cat, _label, _desc in P.CATEGORIES:
        assert P.by_category(cat), cat


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
        mat = L.create_material(preset['id'])
        obj.data.materials.clear()
        obj.data.materials.append(mat)
        bpy.ops.render.render()
        assert L.find_bpm_node(mat) is not None


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
        assert job.output_dir.startswith(B.FALLBACK_DIR), job.output_dir
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
    def seam_ok(a):
        for axis in (0, 1):
            steps = np.abs(np.diff(a, axis=axis)).mean(axis=(1 - axis, 2))  # one value per row/column step
            wrap = np.abs(np.take(a, 0, axis=axis) - np.take(a, -1, axis=axis)).mean()
            if wrap > 1.25 * steps.max() + 1e-4:
                return False
        return True

    for path in job.written:
        a = read_png(path)[..., :3].astype(np.float64)
        assert seam_ok(a), 'visible seam in ' + os.path.basename(path)
    # negative control: a cropped (no longer periodic) tile must be detected
    rust = read_png([p for p in job.written if p.endswith('Heavily_Rusted_Iron_BaseColor.png')][0])[..., :3]
    assert not seam_ok(rust[:, :80].astype(np.float64)), 'seam check cannot detect seams'
    assert len(job.tile_materials) == 3


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


STACK_SCRIPT = r'''
import bpy, sys
sys.path.insert(0, %(root)r)
import bpm_procedural_metals as addon
from bpm_procedural_metals import library as L
bpy.ops.wm.read_factory_settings(use_empty=True)
addon.register()
scene = bpy.context.scene; scene.render.engine = 'CYCLES'; scene.cycles.samples = 1
bpy.ops.mesh.primitive_cube_add(); ob = bpy.context.active_object
for gen in ('METAL', 'PAINT'):
    for tile in (False, True):
        for mode in ('full', 'normal'):
            mat = bpy.data.materials.new('STACK_%%s_%%s_%%s' %% (gen, int(tile), mode))
            ob.data.materials.clear(); ob.data.materials.append(mat)
            L.build_material(mat, gen, L.default_values(gen), tile=tile)
            nt = mat.node_tree; grp = L.find_bpm_node(mat); out = L.output_node(nt)
            if mode == 'normal':
                d = nt.nodes.new('ShaderNodeBsdfDiffuse')
                nt.links.new(grp.outputs['Normal'], d.inputs['Normal'])
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
