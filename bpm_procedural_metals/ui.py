# SPDX-License-Identifier: GPL-3.0-or-later
"""Sidebar panels: 3D Viewport > Sidebar (press N) > BPM tab."""

import textwrap

import bpy

from . import bake as B
from . import generators as G
from . import library as L
from . import overlays as O
from . import presets as P
from . import previews

CATEGORY = 'BPM'


def _wrap(layout, context, text, icon='NONE'):
    """Draw a paragraph that wraps to the sidebar width."""
    region_width = context.region.width if context.region else 300
    width = max(16, int((region_width - 30) / (7.4 * context.preferences.view.ui_scale)))
    col = layout.column(align=True)
    for i, line in enumerate(textwrap.wrap(text, width)):
        col.label(text=line, icon=icon if i == 0 else 'NONE')


def _draw_socket(layout, node, param):
    sock = node.inputs.get(param.name)
    if sock is None:
        return
    if sock.is_linked:
        layout.label(text='%s: (connected in node editor)' % param.name, icon='LINKED')
        return
    if isinstance(param.ui, tuple) and param.ui[0] == 'ENUM':
        layout.label(text=param.name)
        grid = layout.grid_flow(row_major=True, columns=3, even_columns=True, align=True)
        current = round(sock.default_value)
        for label, value in param.ui[1]:
            op = grid.operator('bpm.set_value', text=label, depress=current == round(value))
            op.socket = param.name
            op.value = value
        return
    if param.ui == 'AXIS':
        row = layout.row(align=True)
        row.label(text=param.name)
        for axis, value in (('X', (1.0, 0.0, 0.0)), ('Y', (0.0, 1.0, 0.0)), ('Z', (0.0, 0.0, 1.0))):
            current = tuple(round(v, 3) for v in sock.default_value)
            op = row.operator('bpm.set_vector', text=axis, depress=current == value)
            op.socket = param.name
            op.value = value
        return
    if param.kind == 'VECTOR':
        layout.label(text=param.name)
        layout.row().prop(sock, 'default_value', text='')
        return
    layout.prop(sock, 'default_value', text=param.name, slider=param.subtype == 'FACTOR')


class BPM_PT_library(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY
    bl_label = 'Material Library'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.bpm
        wm = context.window_manager

        grid = layout.grid_flow(row_major=True, columns=3, even_columns=True, align=True)
        grid.prop(settings, 'category', expand=True)
        row = layout.row(align=True)
        row.operator('bpm.gallery_step', text='', icon='TRIA_LEFT').step = -1
        row.template_icon_view(wm, 'bpm_gallery', show_labels=True, scale=7.0, scale_popup=6.0)
        row.operator('bpm.gallery_step', text='', icon='TRIA_RIGHT').step = 1

        preset = P.find(wm.bpm_gallery) if wm.bpm_gallery not in {'', 'NONE'} else None
        if preset is not None:
            box = layout.box()
            overlay = P.is_overlay(preset)
            box.label(text=preset['name'], icon='MOD_OCEAN' if overlay else 'MATERIAL')
            _wrap(box, context, preset['desc'])
            if overlay:
                _wrap(box, context, 'Goes on top of the material the object already has.', 'INFO')
            col = layout.column(align=True)
            col.scale_y = 1.6
            if overlay:
                col.operator('bpm.apply_preset', text='Add on Top of Material', icon='ADD').preset = preset['id']
            else:
                label = 'Apply to Selected Faces' if context.mode == 'EDIT_MESH' else 'Apply to Selected'
                col.operator('bpm.apply_preset', text=label, icon='CHECKMARK').preset = preset['id']
            layout.prop(settings, 'fit_to_object')


class BPM_PT_adjust(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY
    bl_label = 'Adjust Material'

    def draw(self, context):
        layout = self.layout
        obj, mat, node = L.active_bpm_material(context)
        if obj is None:
            _wrap(layout, context, 'Select an object to adjust its material.', 'INFO')
            return
        if L.is_baked_material(mat):
            _wrap(layout, context, '"%s" is showing its baked textures.' % obj.name, 'IMAGE_DATA')
            if getattr(obj, 'bpm_backup', None):
                layout.operator('bpm.show_procedural', icon='NODE_MATERIAL')
            return
        if node is None:
            _wrap(layout, context, 'The active material is not a BPM material. Pick one in the gallery '
                                   'above and click "Apply to Selected". Dirt and dust overlays work on '
                                   'any material.', 'INFO')
            return

        generator = node.node_tree['bpm_generator']
        params = G.params_for(generator)
        users = mat.users - (1 if mat.use_fake_user else 0)

        row = layout.row(align=True)
        row.prop(mat, 'name', text='', icon='MATERIAL')
        if users > 1:
            row.operator('bpm.make_unique', text=str(users), icon='DUPLICATE')
        row = layout.row(align=True)
        row.operator_menu_enum('bpm.load_preset_menu', 'preset', text='Load Preset', icon='PRESET')
        row.operator('bpm.reset_material', text='', icon='LOOP_BACK')
        row.operator('bpm.randomize_seed', text='', icon='FILE_REFRESH')

        col = layout.column(align=True)
        for p in params:
            if p.key:
                _draw_socket(col, node, p)
        layout.operator('bpm.fit_scale', icon='FULLSCREEN_ENTER')

        panels = []
        for p in params:
            if p.panel not in panels:
                panels.append(p.panel)
        for name in panels:
            header, body = layout.panel('bpm_adjust_%s_%s' % (generator, name), default_closed=True)
            header.label(text=name)
            if body is not None:
                col = body.column(align=True)
                for p in params:
                    if p.panel == name:
                        _draw_socket(col, node, p)

        box = layout.box()
        _wrap(box, context, 'Cycles shows exactly what the bake will produce.', 'LIGHT')
        row = box.row(align=True)
        space = context.space_data
        if space is not None and getattr(space, 'shading', None) is not None and space.shading.type == 'RENDERED':
            row.operator('bpm.preview_material', icon='SHADING_TEXTURE')
        else:
            row.operator('bpm.preview_cycles', icon='SHADING_RENDERED')


class BPM_PT_overlays(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY
    bl_label = 'Dirt & Dust Overlays'

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        if not L.can_have_material(obj):
            _wrap(layout, context, 'Select an object to add dirt or dust to its material.', 'INFO')
            return
        mat = obj.active_material
        if L.is_baked_material(mat):
            _wrap(layout, context, 'This object shows its baked textures. Overlays are added to the '
                                   'procedural material (switch back with "Back to Procedural").', 'INFO')
        row = layout.row()
        row.scale_y = 1.3
        row.operator_menu_enum('bpm.add_overlay', 'preset', text='Add Dirt or Dust', icon='ADD')
        if mat is None or L.is_baked_material(mat):
            return
        stack = L.overlay_stack(mat)
        if not stack:
            _wrap(layout, context, 'Layers of dirt or dust stack on top of any material and are '
                                   'included when you bake.')
            return
        for index in reversed(range(len(stack))):  # top layer first
            self._draw_overlay(context, layout, stack[index], index, len(stack))

    def _draw_overlay(self, context, layout, node, index, count):
        box = layout.box()
        row = box.row(align=True)
        hidden = L.overlay_hidden(node)
        row.operator('bpm.toggle_overlay', text='', icon='HIDE_ON' if hidden else 'HIDE_OFF',
                     emboss=False).index = index
        row.label(text=node.label or node.node_tree.name)
        sub = row.row(align=True)
        sub.enabled = index < count - 1
        op = sub.operator('bpm.move_overlay', text='', icon='TRIA_UP')
        op.index, op.step = index, 1
        sub = row.row(align=True)
        sub.enabled = index > 0
        op = sub.operator('bpm.move_overlay', text='', icon='TRIA_DOWN')
        op.index, op.step = index, -1
        row.operator('bpm.overlay_seed', text='', icon='FILE_REFRESH').index = index
        row.operator('bpm.remove_overlay', text='', icon='X').index = index
        if hidden:
            return
        generator = node.node_tree['bpm_generator']
        params = [p for p in G.params_for(generator) if p.panel != O.BELOW]
        col = box.column(align=True)
        for p in params:
            if p.key:
                _draw_socket(col, node, p)
        header, body = box.panel('bpm_overlay_%s' % node.name, default_closed=True)
        header.label(text='More Settings')
        if body is not None:
            col = body.column(align=True)
            for p in params:
                if not p.key:
                    _draw_socket(col, node, p)


class BPM_OT_load_preset_menu(bpy.types.Operator):
    """Load the settings of another preset into this material"""
    bl_idname = 'bpm.load_preset_menu'
    bl_label = 'Load Preset'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def _items(self, context):
        obj, mat, node = L.active_bpm_material(context) if context else (None, None, None)
        generator = node.node_tree['bpm_generator'] if node else None
        items = [(p['id'], p['name'], p['desc']) for p in P.PRESETS
                 if generator is None or p['generator'] == generator]
        BPM_OT_load_preset_menu._cache = items
        return items or [('NONE', 'None', '')]

    preset: bpy.props.EnumProperty(items=_items, name='Preset')

    def execute(self, context):
        if self.preset == 'NONE':
            return {'CANCELLED'}
        return bpy.ops.bpm.load_preset(preset=self.preset)


class BPM_PT_bake(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY
    bl_label = 'Bake Textures'

    def draw(self, context):
        layout = self.layout
        props = context.scene.bpm
        layout.row().prop(props, 'bake_mode', expand=True)
        if props.bake_mode == 'OBJECTS':
            _wrap(layout, context, 'Makes textures that fit each object, ready for game engines and '
                                   'export (FBX, glTF...).')
        else:
            _wrap(layout, context, 'Makes square textures of the active material that repeat '
                                   'seamlessly, for use anywhere.')

        layout.label(text='Resolution')
        layout.row().prop(props, 'resolution', expand=True)
        layout.label(text='Quality')
        layout.row().prop(props, 'quality', expand=True)

        header, body = layout.panel('bpm_bake_maps', default_closed=False)
        header.label(text='Texture Maps')
        if body is not None:
            grid = body.grid_flow(columns=2, align=True)
            for key in B.MAP_ORDER:
                if key == 'AO' and props.bake_mode == 'TILE':
                    continue
                if key == 'AO':
                    grid.prop(props, 'map_ao', text='AO')
                else:
                    grid.prop(props, 'map_' + key.lower())

        layout.prop(props, 'output_dir')
        if props.output_dir.strip().startswith('//') and not bpy.data.filepath:
            _wrap(layout, context, 'Your .blend file is not saved yet, so the textures will go to: %s'
                  % B.unsaved_dir(props.output_dir), 'INFO')

        header, body = layout.panel('bpm_bake_options', default_closed=True)
        header.label(text='More Options')
        if body is not None:
            col = body.column()
            col.prop(props, 'normal_format')
            col.prop(props, 'bit_depth')
            col.prop(props, 'pack_orm')
            col.prop(props, 'pack_unity')
            if props.bake_mode == 'OBJECTS':
                col.prop(props, 'assign_baked')
                col.prop(props, 'auto_unwrap')
            else:
                col.prop(props, 'tile_size')
            col.prop(props, 'device')

        if props.bake_mode == 'OBJECTS':
            self._draw_object_buttons(context, layout, props)
        else:
            col = layout.column()
            col.scale_y = 1.8
            col.operator('bpm.bake', text='Bake Seamless Tile', icon='RENDER_STILL')
        if props.resolution == '8192':
            _wrap(layout, context, '8K textures need a lot of memory and time.', 'ERROR')

        obj = context.active_object
        if obj is not None and L.can_have_material(obj):
            if L.is_baked_material(obj.active_material) and getattr(obj, 'bpm_backup', None):
                layout.operator('bpm.show_procedural', icon='NODE_MATERIAL')
            elif bpy.data.materials.get('%s Baked' % obj.name) is not None:
                layout.operator('bpm.show_baked', icon='IMAGE_DATA')

        if props.last_report:
            box = layout.box()
            icon = {'ERROR': 'CANCEL', 'WARNING': 'ERROR'}.get(props.last_level, 'CHECKMARK')
            _wrap(box, context, props.last_report, icon)
            warnings = props.last_warnings.splitlines()
            for text in warnings[:6]:
                _wrap(box, context, text, 'DOT')
            if len(warnings) > 6:
                _wrap(box, context, '... and %d more (see Window > Info Log).' % (len(warnings) - 6))
            if props.last_folder and props.last_level != 'ERROR':
                box.operator('bpm.open_folder', icon='FILE_FOLDER')

    @staticmethod
    def _draw_object_buttons(context, layout, props):
        layout.label(text='Objects')
        layout.row().prop(props, 'bake_scope', expand=True)
        objs = B.scope_objects(context, props.bake_scope)
        count = len([o for o in objs if B.skip_reason(context, o) is None])
        things = '%d Object%s' % (count, '' if count == 1 else 's')
        col = layout.column()
        col.scale_y = 1.8
        col.enabled = count > 0
        col.operator('bpm.auto_texture', text='Auto Texture %s' % things if count else 'Auto Texture',
                     icon='SHADING_TEXTURE')
        if count:
            _wrap(layout, context, 'New UVs (Smart UV Project + Pack Islands), bake, save and apply: '
                                   'all in one click.')
        elif objs:
            reason = B.skip_reason(context, objs[0])
            hint = '"%s" %s.' % (objs[0].name, reason)
            if reason == 'has no material':
                hint += ' Pick one in the Material Library above.'
            _wrap(layout, context, hint, 'INFO')
        else:
            _wrap(layout, context, {'ACTIVE': 'Click the mesh you want to texture.',
                                    'SELECTED': 'Select the meshes you want to texture.',
                                    'SCENE': 'There are no visible meshes in the scene.'}[props.bake_scope],
                  'INFO')
        row = layout.row()
        row.scale_y = 1.2
        row.enabled = count > 0
        row.operator('bpm.bake', text='Bake %s with Current UVs' % things if count else 'Bake with Current UVs',
                     icon='RENDER_STILL')


class BPM_PT_help(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY
    bl_label = 'Quick Help'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        steps = (
            '1. Select your object (left-click it).',
            '2. Pick a material in the gallery and click "Apply to Selected".',
            '3. Change the look with the sliders in "Adjust Material".',
            'Want it dirty or dusty? Use "Add Dirt or Dust": the layers go on top of any material, '
            'even ones that are not from BPM.',
            '4. Click "Auto Texture" in "Bake Textures": it makes new UVs, bakes image textures, saves '
            'them and puts them on the object, all in one go. Pick Active, Selected or Scene first. '
            'The textures are saved next to your .blend file (or in BPM_Textures in your home folder if '
            'the file was never saved).',
            'Switch the 3D view to Material Preview (Z key > Material Preview) to see the materials.',
            'Texture too big or too small? Change "Scale" in Adjust Material.',
            'Want another random look? Click the refresh icon next to "Load Preset".',
        )
        for text in steps:
            _wrap(layout, context, text)


CLASSES = (BPM_OT_load_preset_menu, BPM_PT_library, BPM_PT_adjust, BPM_PT_overlays, BPM_PT_bake, BPM_PT_help)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.WindowManager.bpm_gallery = bpy.props.EnumProperty(
        items=previews.gallery_items, name='Material', description='Click to see all materials')


def unregister():
    del bpy.types.WindowManager.bpm_gallery
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
