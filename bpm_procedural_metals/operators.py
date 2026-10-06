# SPDX-License-Identifier: GPL-3.0-or-later
"""Operators (buttons) of the add-on."""

import os
import random
import traceback

import bpy
from bpy.props import FloatVectorProperty, IntProperty, StringProperty

from . import bake as B
from . import library as L
from . import presets as P


def _selected_material_objects(context):
    objs = [o for o in context.selected_objects if L.can_have_material(o)]
    if not objs and L.can_have_material(context.active_object):
        objs = [context.active_object]
    return objs


def _redraw(context):
    screen = context.screen
    if screen is not None:
        for area in screen.areas:
            area.tag_redraw()


# ------------------------------------------------------------------ library
class BPM_OT_apply_preset(bpy.types.Operator):
    """Put this material on the selected objects (or the selected faces in Edit Mode)"""
    bl_idname = 'bpm.apply_preset'
    bl_label = 'Apply Material'
    bl_options = {'REGISTER', 'UNDO'}

    preset: StringProperty(name='Preset')

    def execute(self, context):
        preset = P.find(self.preset) if self.preset else None
        if preset is None:
            self.report({'ERROR'}, 'Pick a material in the gallery first.')
            return {'CANCELLED'}
        settings = context.scene.bpm
        if context.mode == 'EDIT_MESH':
            return self._apply_to_faces(context, preset, settings)
        objs = _selected_material_objects(context)
        if not objs:
            self.report({'ERROR'}, 'Select an object first (left-click it in the 3D view).')
            return {'CANCELLED'}
        mat = L.create_material(preset['id'])
        if settings.fit_to_object:
            L.find_bpm_node(mat).inputs['Scale'].default_value = L.fit_scale(objs)
        for obj in objs:
            B.restore_procedural(obj)  # drop a baked material that might be shown
            L.assign_material(obj, mat)
        self.report({'INFO'}, 'Applied "%s" to %d object%s.' % (preset['name'], len(objs), 's' * (len(objs) > 1)))
        return {'FINISHED'}

    def _apply_to_faces(self, context, preset, settings):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, 'Edit Mode: the active object must be a mesh.')
            return {'CANCELLED'}
        mat = L.create_material(preset['id'])
        if settings.fit_to_object:
            L.find_bpm_node(mat).inputs['Scale'].default_value = L.fit_scale([obj])
        obj.data.materials.append(mat)
        obj.active_material_index = len(obj.material_slots) - 1
        bpy.ops.object.material_slot_assign()
        self.report({'INFO'}, 'Applied "%s" to the selected faces.' % preset['name'])
        return {'FINISHED'}


class BPM_OT_gallery_step(bpy.types.Operator):
    """Show the previous / next material of the gallery"""
    bl_idname = 'bpm.gallery_step'
    bl_label = 'Browse Materials'
    bl_options = {'INTERNAL'}

    step: IntProperty(default=1)

    def execute(self, context):
        wm = context.window_manager
        presets = P.by_category(context.scene.bpm.category)
        if not presets:
            return {'CANCELLED'}
        ids = [p['id'] for p in presets]
        try:
            index = ids.index(wm.bpm_gallery)
        except (ValueError, TypeError):
            index = 0
        wm.bpm_gallery = ids[(index + self.step) % len(ids)]
        return {'FINISHED'}


class BPM_OT_load_preset(bpy.types.Operator):
    """Load a preset's settings into the active material (keeps its pattern size and seed)"""
    bl_idname = 'bpm.load_preset'
    bl_label = 'Load Preset'
    bl_options = {'REGISTER', 'UNDO'}

    preset: StringProperty()

    def execute(self, context):
        obj, mat, node = L.active_bpm_material(context)
        preset = P.find(self.preset)
        if mat is None or preset is None:
            return {'CANCELLED'}
        L.load_preset_into(mat, preset['id'])
        self.report({'INFO'}, 'Loaded "%s".' % preset['name'])
        return {'FINISHED'}


class BPM_OT_reset_material(bpy.types.Operator):
    """Undo all slider changes: go back to the original preset values"""
    bl_idname = 'bpm.reset_material'
    bl_label = 'Reset to Preset'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj, mat, node = L.active_bpm_material(context)
        if node is None:
            return {'CANCELLED'}
        preset_id = mat.get('bpm_preset')
        preset = P.find(preset_id) if preset_id else None
        if preset is None:
            L.apply_values(node, L.default_values(node.node_tree['bpm_generator']))
        else:
            L.load_preset_into(mat, preset['id'], keep_pattern=True)
        return {'FINISHED'}


class BPM_OT_randomize_seed(bpy.types.Operator):
    """Pick a new random variation of the pattern"""
    bl_idname = 'bpm.randomize_seed'
    bl_label = 'New Variation'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj, mat, node = L.active_bpm_material(context)
        if node is None:
            return {'CANCELLED'}
        node.inputs['Seed'].default_value = round(random.uniform(0.0, 100.0), 2)
        return {'FINISHED'}


class BPM_OT_fit_scale(bpy.types.Operator):
    """Set the pattern size to suit the size of the selected object(s)"""
    bl_idname = 'bpm.fit_scale'
    bl_label = 'Fit to Object Size'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj, mat, node = L.active_bpm_material(context)
        if node is None:
            return {'CANCELLED'}
        users = [o for o in _selected_material_objects(context)
                 if any(slot.material == mat for slot in o.material_slots)] or [obj]
        node.inputs['Scale'].default_value = L.fit_scale(users)
        return {'FINISHED'}


class BPM_OT_set_vector(bpy.types.Operator):
    """Set this direction"""
    bl_idname = 'bpm.set_vector'
    bl_label = 'Set Direction'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    socket: StringProperty()
    value: FloatVectorProperty(size=3)

    def execute(self, context):
        obj, mat, node = L.active_bpm_material(context)
        if node is None or self.socket not in node.inputs:
            return {'CANCELLED'}
        node.inputs[self.socket].default_value = self.value
        return {'FINISHED'}


class BPM_OT_make_unique(bpy.types.Operator):
    """Give the active object its own copy of this material, so changes don't affect other objects"""
    bl_idname = 'bpm.make_unique'
    bl_label = 'Make Unique'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj, mat, node = L.active_bpm_material(context)
        if mat is None:
            return {'CANCELLED'}
        copy = mat.copy()
        obj.material_slots[obj.active_material_index].material = copy
        self.report({'INFO'}, 'This object now has its own material "%s".' % copy.name)
        return {'FINISHED'}


class BPM_OT_preview_cycles(bpy.types.Operator):
    """Preview with Cycles (shows edge wear and dirt in crevices exactly like the bake will)"""
    bl_idname = 'bpm.preview_cycles'
    bl_label = 'Preview in Cycles'
    bl_options = {'REGISTER'}

    def execute(self, context):
        try:
            context.scene.render.engine = 'CYCLES'
        except TypeError:
            self.report({'ERROR'}, 'The Cycles add-on is disabled (Edit > Preferences > Add-ons).')
            return {'CANCELLED'}
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'RENDERED'
        return {'FINISHED'}


class BPM_OT_preview_material(bpy.types.Operator):
    """Back to the fast Material Preview mode"""
    bl_idname = 'bpm.preview_material'
    bl_label = 'Material Preview'
    bl_options = {'REGISTER'}

    def execute(self, context):
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'MATERIAL'
        return {'FINISHED'}


# --------------------------------------------------------------------- bake
class BPM_OT_bake(bpy.types.Operator):
    """Bake the material(s) to image textures. Press Esc to cancel"""
    bl_idname = 'bpm.bake'
    bl_label = 'Bake Textures'
    bl_options = {'REGISTER'}

    _job = None
    _steps = None
    _timer = None

    def _make_job(self, context):
        props = context.scene.bpm
        settings = B.BakeSettings.from_props(props)
        if props.bake_mode == 'TILE':
            mats = []
            for obj in [context.active_object] + list(context.selected_objects):
                if L.can_have_material(obj):
                    mat = obj.active_material
                    if L.is_baked_material(mat) and getattr(obj, 'bpm_backup', None):
                        entry = next((e for e in obj.bpm_backup if e.index == obj.active_material_index), None)
                        mat = entry.material if entry else mat
                    if mat is not None and mat not in mats:
                        mats.append(mat)
            return B.TileBakeJob(context, mats, settings)
        objs = [o for o in context.selected_objects]
        if not objs and context.active_object is not None:
            objs = [context.active_object]
        return B.ObjectBakeJob(context, objs, settings)

    def invoke(self, context, event):
        try:
            job = self._make_job(context)
            job.check()
        except B.BakeError as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        if bpy.app.background or context.window is None:
            return self.execute(context)
        self._job = job
        self._steps = job.run()
        wm = context.window_manager
        wm.progress_begin(0, max(job.total_steps, 1))
        self._timer = wm.event_timer_add(0.05, window=context.window)
        wm.modal_handler_add(self)
        context.workspace.status_text_set('BPM: starting the bake... (press Esc to cancel)')
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'ESC' and event.value == 'PRESS':
            self._steps.close()
            return self._finish(context, 'Bake cancelled.', level='WARNING')
        if event.type != 'TIMER':
            return {'RUNNING_MODAL'}  # keep the user from changing things mid-bake
        try:
            status = next(self._steps)
        except StopIteration:
            return self._finish(context)
        except B.BakeError as exc:
            self._steps.close()
            return self._finish(context, str(exc), level='ERROR')
        except Exception as exc:  # never leave the user without a message
            traceback.print_exc()
            self._steps.close()
            return self._finish(context, 'Unexpected error: %s (see the system console)' % exc, level='ERROR')
        job = self._job
        context.window_manager.progress_update(job.done_steps)
        percent = int(100 * job.done_steps / max(job.total_steps, 1))
        context.workspace.status_text_set('BPM %d%%: %s ... (press Esc to cancel)' % (percent, status))
        _redraw(context)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        try:
            job = self._job or self._make_job(context)
            B.run_to_end(job)
        except B.BakeError as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        self._job = job
        self._report(context, job)
        return {'FINISHED'}

    def _finish(self, context, message=None, level='INFO'):
        wm = context.window_manager
        if self._timer is not None:
            wm.event_timer_remove(self._timer)
            self._timer = None
        wm.progress_end()
        context.workspace.status_text_set(None)
        if message:
            self.report({level}, message)
            context.scene.bpm.last_report = message
        else:
            self._report(context, self._job)
        try:
            bpy.ops.ed.undo_push(message='BPM Bake')
        except RuntimeError:
            pass
        _redraw(context)
        return {'FINISHED'} if level == 'INFO' else {'CANCELLED'}

    def _report(self, context, job):
        for level, text in job.messages:
            if level == 'WARNING':
                self.report({'WARNING'}, text)
        count = len(job.written)
        props = context.scene.bpm
        props.last_folder = job.output_dir or ''
        summary = 'Saved %d texture%s to %s' % (count, 's' * (count != 1), job.output_dir)
        props.last_report = summary
        self.report({'INFO'}, summary)


class BPM_OT_open_folder(bpy.types.Operator):
    """Open the folder with the baked textures"""
    bl_idname = 'bpm.open_folder'
    bl_label = 'Open Folder'

    def execute(self, context):
        folder = context.scene.bpm.last_folder
        if not folder or not os.path.isdir(folder):
            self.report({'ERROR'}, 'Nothing has been baked yet.')
            return {'CANCELLED'}
        bpy.ops.wm.path_open(filepath=folder)
        return {'FINISHED'}


class BPM_OT_show_procedural(bpy.types.Operator):
    """Switch back to the editable procedural material (the baked textures stay on disk)"""
    bl_idname = 'bpm.show_procedural'
    bl_label = 'Back to Procedural'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        done = 0
        for obj in _selected_material_objects(context):
            done += B.restore_procedural(obj)
        if not done:
            self.report({'WARNING'}, 'The selected objects already use their procedural materials.')
        return {'FINISHED'}


class BPM_OT_show_baked(bpy.types.Operator):
    """Switch to the material that uses the baked textures"""
    bl_idname = 'bpm.show_baked'
    bl_label = 'Use Baked Textures'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        done = 0
        for obj in _selected_material_objects(context):
            mat = bpy.data.materials.get('%s Baked' % obj.name)
            if mat is not None and L.is_baked_material(mat):
                B.assign_baked(obj, mat)
                done += 1
        if not done:
            self.report({'WARNING'}, 'Bake the object first.')
            return {'CANCELLED'}
        return {'FINISHED'}


CLASSES = (
    BPM_OT_apply_preset,
    BPM_OT_gallery_step,
    BPM_OT_load_preset,
    BPM_OT_reset_material,
    BPM_OT_randomize_seed,
    BPM_OT_fit_scale,
    BPM_OT_set_vector,
    BPM_OT_make_unique,
    BPM_OT_preview_cycles,
    BPM_OT_preview_material,
    BPM_OT_bake,
    BPM_OT_open_folder,
    BPM_OT_show_procedural,
    BPM_OT_show_baked,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
