# SPDX-License-Identifier: GPL-3.0-or-later
"""Builds a small studio scene for rendering material previews headlessly.

Used by render_thumbnails.py and the look-development scripts.
"""

import math
import os

import bpy


def studio_hdri(name='courtyard.exr'):
    folder = bpy.utils.system_resource('DATAFILES', path='studiolights/world')
    path = os.path.join(folder, name)
    return path if os.path.exists(path) else None


def setup(size=256, samples=48, hdri='forest.exr', transparent=True, shape='cube', strength=1.0, zoom=1.0):
    """Studio scene with one preview object.  `zoom` < 1 shrinks object and camera together,
    so the object looks the same on screen but material details appear bigger."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.use_adaptive_sampling = True
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = transparent
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA' if transparent else 'RGB'

    world = bpy.data.worlds.new('Preview World')
    scene.world = world
    if world.node_tree is None:
        world.use_nodes = True
    if hdri == 'studio':
        build_studio_world(world.node_tree, strength)
    else:
        build_hdri_world(world.node_tree, hdri, strength)

    obj = make_shape(shape)
    obj.scale = (zoom, zoom, zoom)

    cam_data = bpy.data.cameras.new('Camera')
    cam_data.lens = 85
    cam = bpy.data.objects.new('Camera', cam_data)
    scene.collection.objects.link(cam)
    cam.location = (5.2 * zoom, -5.2 * zoom, 4.1 * zoom)
    cam_data.clip_start = 0.01 * zoom
    track = cam.constraints.new('TRACK_TO')
    target = bpy.data.objects.new('Target', None)
    scene.collection.objects.link(target)
    target.location = (0.0, 0.0, -0.05 * zoom)
    track.target = target
    track.track_axis = 'TRACK_NEGATIVE_Z'
    track.up_axis = 'UP_Y'
    scene.camera = cam
    return scene, obj


def build_hdri_world(nt, hdri, strength):
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg = nt.nodes.new('ShaderNodeBackground')
    bg.inputs['Strength'].default_value = strength
    path = studio_hdri(hdri)
    if path:
        env = nt.nodes.new('ShaderNodeTexEnvironment')
        env.image = bpy.data.images.load(path, check_existing=True)
        mapping = nt.nodes.new('ShaderNodeMapping')
        mapping.inputs['Rotation'].default_value = (0.0, 0.0, math.radians(110))
        coord = nt.nodes.new('ShaderNodeTexCoord')
        nt.links.new(coord.outputs['Generated'], mapping.inputs['Vector'])
        nt.links.new(mapping.outputs['Vector'], env.inputs['Vector'])
        nt.links.new(env.outputs['Color'], bg.inputs['Color'])
    nt.links.new(bg.outputs['Background'], out.inputs['Surface'])


# Soft, neutral studio: a dim dome plus a few big soft boxes placed so that every
# visible face of the preview cube reflects one of them.
SOFTBOXES = (
    # direction, cos(outer), cos(inner), intensity
    ((-0.45, 0.55, 0.70), 0.90, 0.97, 1.6),    # above-behind: top face
    ((-0.70, -0.62, -0.10), 0.95, 0.985, 1.2),  # front-left low: left face
    ((0.66, 0.68, -0.10), 0.95, 0.985, 0.9),    # back-right low: right face
    ((0.55, -0.75, 0.45), 0.94, 0.98, 2.4),     # key light from camera side
)


def build_studio_world(nt, strength=1.0):
    from mathutils import Vector
    nt.nodes.clear()
    links = nt.links
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg = nt.nodes.new('ShaderNodeBackground')
    bg.inputs['Strength'].default_value = strength
    coord = nt.nodes.new('ShaderNodeTexCoord')
    norm = nt.nodes.new('ShaderNodeVectorMath')
    norm.operation = 'NORMALIZE'
    links.new(coord.outputs['Generated'], norm.inputs[0])
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    links.new(norm.outputs['Vector'], sep.inputs[0])
    dome = nt.nodes.new('ShaderNodeMapRange')
    dome.inputs['From Min'].default_value = -0.3
    dome.inputs['From Max'].default_value = 0.9
    dome.inputs['To Min'].default_value = 0.012
    dome.inputs['To Max'].default_value = 0.16
    links.new(sep.outputs['Z'], dome.inputs['Value'])
    total = dome.outputs['Result']
    for direction, c_out, c_in, intensity in SOFTBOXES:
        dot = nt.nodes.new('ShaderNodeVectorMath')
        dot.operation = 'DOT_PRODUCT'
        links.new(norm.outputs['Vector'], dot.inputs[0])
        dot.inputs[1].default_value = Vector(direction).normalized()
        box = nt.nodes.new('ShaderNodeMapRange')
        box.interpolation_type = 'SMOOTHSTEP'
        box.inputs['From Min'].default_value = c_out
        box.inputs['From Max'].default_value = c_in
        box.inputs['To Max'].default_value = intensity
        links.new(dot.outputs['Value'], box.inputs['Value'])
        add = nt.nodes.new('ShaderNodeMath')
        add.operation = 'ADD'
        links.new(total, add.inputs[0])
        links.new(box.outputs['Result'], add.inputs[1])
        total = add.outputs[0]
    links.new(total, bg.inputs['Color'])
    links.new(bg.outputs['Background'], out.inputs['Surface'])


def make_shape(shape='cube'):
    if shape == 'cube':
        bpy.ops.mesh.primitive_cube_add(size=1.7)
        obj = bpy.context.active_object
        bev = obj.modifiers.new('Bevel', 'BEVEL')
        bev.width = 0.035
        bev.segments = 4
        bev.limit_method = 'NONE'
        bev.harden_normals = True
        for poly in obj.data.polygons:
            poly.use_smooth = True
        obj.rotation_euler = (0.0, 0.0, math.radians(8))
    elif shape == 'sharp_cube':
        bpy.ops.mesh.primitive_cube_add(size=1.7)
        obj = bpy.context.active_object
    elif shape == 'sphere':
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1.1, segments=64, ring_count=32)
        obj = bpy.context.active_object
        for poly in obj.data.polygons:
            poly.use_smooth = True
    elif shape == 'steps':
        obj = make_steps()
    elif shape == 'cylinder':
        bpy.ops.mesh.primitive_cylinder_add(radius=0.9, depth=1.7, vertices=64)
        obj = bpy.context.active_object
        bev = obj.modifiers.new('Bevel', 'BEVEL')
        bev.width = 0.03
        bev.segments = 3
        bev.harden_normals = True
        for poly in obj.data.polygons:
            poly.use_smooth = True
    else:
        raise ValueError(shape)
    obj.name = 'Preview'
    return obj


def make_steps():
    """A small staircase block: corners and crevices show off dirt and dust."""
    import bmesh
    bm = bmesh.new()

    def box(x0, y0, z0, x1, y1, z1):
        result = bmesh.ops.create_cube(bm, size=1.0)
        for v in result['verts']:
            v.co.x = x0 if v.co.x < 0 else x1
            v.co.y = y0 if v.co.y < 0 else y1
            v.co.z = z0 if v.co.z < 0 else z1

    box(-0.9, -0.9, -0.9, 0.9, 0.9, -0.3)
    box(-0.9, -0.3, -0.3, 0.9, 0.9, 0.3)
    box(-0.9, 0.3, 0.3, 0.9, 0.9, 0.9)
    box(-0.25, -0.9, -0.3, 0.25, -0.5, 0.2)
    mesh = bpy.data.meshes.new('Steps')
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new('Preview', mesh)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.rotation_euler = (0.0, 0.0, 0.6)
    return obj


def render(path):
    scene = bpy.context.scene
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
