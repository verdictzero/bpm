# SPDX-License-Identifier: GPL-3.0-or-later
"""Settings stored in the .blend file."""

import bpy
from bpy.props import (BoolProperty, CollectionProperty, EnumProperty, FloatProperty, IntProperty,
                       PointerProperty, StringProperty)

from . import presets as P


class BPM_SlotBackup(bpy.types.PropertyGroup):
    """Original material of a slot, kept while the baked material is shown."""
    index: IntProperty()
    material: PointerProperty(type=bpy.types.Material)


RESOLUTIONS = [
    ('512', '512', '512 x 512 pixels: fast, for small or distant objects'),
    ('1024', '1K', '1024 x 1024 pixels'),
    ('2048', '2K', '2048 x 2048 pixels: good default'),
    ('4096', '4K', '4096 x 4096 pixels: high detail, slower'),
    ('8192', '8K', '8192 x 8192 pixels: very slow and uses a lot of memory'),
]


class BPM_Settings(bpy.types.PropertyGroup):
    # --- library
    category: EnumProperty(
        name='Category',
        items=[('ALL', 'All', 'Show every material')] + [(c[0], c[3], c[2]) for c in P.CATEGORIES],
        default='ALL')
    fit_to_object: BoolProperty(
        name='Fit Pattern Size to Object', default=True,
        description='Adapt the pattern size (scratches, grain, dirt...) to the size of the selected object(s)')
    show_all_settings: BoolProperty(
        name='Show All Settings', default=False,
        description='Show every setting of the material, not just the most important ones')

    # --- bake
    bake_mode: EnumProperty(
        name='Bake Mode',
        items=[('OBJECTS', 'Objects',
                'Bake textures that fit the UV map of each selected object (for game engines / export)', 'OBJECT_DATA', 0),
               ('TILE', 'Seamless Tile',
                'Bake square textures that repeat seamlessly (for texture libraries or other software)', 'TEXTURE', 1)],
        default='OBJECTS')
    bake_scope: EnumProperty(
        name='Objects',
        items=[('ACTIVE', 'Active', 'Only the active object (the one you clicked last)', 'OBJECT_DATA', 0),
               ('SELECTED', 'Selected', 'All selected objects', 'RESTRICT_SELECT_OFF', 1),
               ('SCENE', 'Scene', 'Every visible mesh object in the scene', 'SCENE_DATA', 2)],
        default='SELECTED',
        description='Which objects to texture')
    resolution: EnumProperty(name='Resolution', items=RESOLUTIONS, default='2048',
                             description='Size of the baked textures in pixels')
    quality: EnumProperty(
        name='Quality',
        items=[('FAST', 'Fast', 'Quick preview bake (slightly grainy)'),
               ('GOOD', 'Good', 'Clean result, recommended'),
               ('BEST', 'Best', 'Smoothest result, slowest')],
        default='GOOD')
    map_base_color: BoolProperty(name='Base Color', default=True, description='Color texture (sRGB)')
    map_metallic: BoolProperty(name='Metallic', default=True, description='Black = paint/rust, white = metal')
    map_roughness: BoolProperty(name='Roughness', default=True, description='Black = glossy, white = matte')
    map_normal: BoolProperty(name='Normal', default=True, description='Surface detail (normal map)')
    map_height: BoolProperty(name='Height', default=True, description='Height / displacement map (16-bit)')
    map_ao: BoolProperty(name='Ambient Occlusion', default=True,
                         description='Ambient occlusion: soft shadows in crevices (Objects mode only)')
    normal_format: EnumProperty(
        name='Normal Map Format',
        items=[('OPENGL', 'OpenGL', 'Blender, Unity, Godot, glTF, Substance (default)'),
               ('DIRECTX', 'DirectX', 'Unreal Engine, CryEngine, 3ds Max')],
        default='OPENGL')
    bit_depth: EnumProperty(
        name='Bit Depth',
        items=[('8', '8-bit', 'Normal PNG files (smaller)'),
               ('16', '16-bit', 'Higher precision PNG files (bigger)')],
        default='8')
    pack_orm: BoolProperty(
        name='Packed ORM', default=False,
        description='Also save one texture with AO (red), Roughness (green), Metallic (blue): '
                    'Unreal Engine and glTF use this')
    pack_unity: BoolProperty(
        name='Unity Metallic/Smoothness', default=False,
        description='Also save Unity\'s Metallic (RGB) + Smoothness (alpha) texture')
    output_dir: StringProperty(
        name='Folder', subtype='DIR_PATH', default='//BPM_Textures/',
        description='Where the textures are saved ("//" means next to your .blend file). '
                    'If the .blend file was never saved, a BPM_Textures folder in your home folder is used')
    assign_baked: BoolProperty(
        name='Use Baked Material', default=True,
        description='Switch the object to a material that uses the baked textures (Auto Texture always '
                    'does). The procedural material is kept and can be restored any time')
    auto_unwrap: BoolProperty(
        name='Auto UV Unwrap', default=True,
        description='"Bake with Current UVs": make new UVs for objects that have none (or broken / '
                    'overlapping ones)')
    device: EnumProperty(
        name='Device',
        items=[('AUTO', 'Auto', 'Use the GPU if one is set up in Preferences > System, otherwise the CPU'),
               ('CPU', 'CPU', 'Always bake on the CPU'),
               ('GPU', 'GPU', 'Bake on the GPU (falls back to CPU if none is set up)')],
        default='AUTO')
    tile_size: FloatProperty(
        name='Tile Size', default=1.0, min=0.01, soft_max=10.0, subtype='DISTANCE', unit='LENGTH',
        description='How much real-world surface one seamless tile shows')

    # --- results
    last_folder: StringProperty(default='')
    last_report: StringProperty(default='')
    last_level: StringProperty(default='INFO')
    last_warnings: StringProperty(default='')


CLASSES = (BPM_SlotBackup, BPM_Settings)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.bpm = PointerProperty(type=BPM_Settings)
    bpy.types.Object.bpm_backup = CollectionProperty(type=BPM_SlotBackup)


def unregister():
    del bpy.types.Object.bpm_backup
    del bpy.types.Scene.bpm
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
