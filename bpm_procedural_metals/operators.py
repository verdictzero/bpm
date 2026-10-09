# SPDX-License-Identifier: GPL-3.0-or-later
"""Operators (buttons) of the add-on."""

import os
import random
import traceback

import bpy
from bpy.props import EnumProperty, FloatProperty, FloatVectorProperty, IntProperty, StringProperty

from . import bake as B
from . import decals as D
from . import library as L
from . import meshmaps as M
from . import presets as P
from .nodebuilder import set_socket_value


def _selected_material_objects(context):
    objs = [o for o in context.selected_objects if L.can_have_material(o)]
    if not objs and L.can_have_material(context.active_object):
        objs = [context.active_object]
    return objs


def _fit(node, objects, generator, settings):
    """Scale the preset's pattern size to the objects (keeps the preset's own Scale as a factor)."""
    if settings.fit_to_object and 'Scale' in node.inputs:
        node.inputs['Scale'].default_value *= L.fit_scale(objects, generator)


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
        if P.is_overlay(preset):
            return bpy.ops.bpm.add_overlay(preset=preset['id'])
        settings = context.scene.bpm
        if context.mode == 'EDIT_MESH':
            return self._apply_to_faces(context, preset, settings)
        objs = _selected_material_objects(context)
        if not objs:
            self.report({'ERROR'}, 'Select an object first (left-click it in the 3D view).')
            return {'CANCELLED'}
        mat = L.create_material(preset['id'])
        _fit_material(mat, objs, settings)
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
        _fit_material(mat, [obj], settings)
        obj.data.materials.append(mat)
        obj.active_material_index = len(obj.material_slots) - 1
        bpy.ops.object.material_slot_assign()
        self.report({'INFO'}, 'Applied "%s" to the selected faces.' % preset['name'])
        return {'FINISHED'}


def _fit_material(mat, objects, settings):
    node = L.find_bpm_node(mat)
    _fit(node, objects, node.node_tree['bpm_generator'], settings)
    for overlay in L.overlay_stack(mat):
        _fit(overlay, objects, overlay.node_tree['bpm_generator'], settings)


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
        if P.is_overlay(preset):
            return bpy.ops.bpm.add_overlay(preset=preset['id'])
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
        node.inputs['Scale'].default_value = L.fit_scale(users, node.node_tree['bpm_generator'])
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


class BPM_OT_set_value(bpy.types.Operator):
    """Pick this option"""
    bl_idname = 'bpm.set_value'
    bl_label = 'Set Option'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    socket: StringProperty()
    value: FloatProperty()

    def execute(self, context):
        obj, mat, node = L.active_bpm_material(context)
        sock = node.inputs.get(self.socket) if node is not None else None
        if sock is None or sock.type not in {'VALUE', 'INT'}:
            return {'CANCELLED'}
        set_socket_value(sock, self.value)
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


# ------------------------------------------------------------------ overlays
def _overlay_items(self, context):
    items = []
    for category, label, *_rest in P.CATEGORIES:
        if category in P.OVERLAY_CATEGORIES:
            items.append(('', label, ''))  # heading in the menu
            items += [(p['id'], p['name'], p['desc']) for p in P.by_category(category)]
    _overlay_items.cache = items
    return items


def _plain_material(obj):
    """A simple material for objects that have none, so dirt can go on top of it."""
    mat = bpy.data.materials.new('Material')
    L.ensure_node_tree(mat)
    L.assign_material(obj, mat)
    return mat


class BPM_OT_add_overlay(bpy.types.Operator):
    """Layer dirt, dust, edge wear or scratches on top of the material of the selected objects"""
    bl_idname = 'bpm.add_overlay'
    bl_label = 'Add Overlay'
    bl_options = {'REGISTER', 'UNDO'}

    preset: EnumProperty(items=_overlay_items, name='Overlay')

    def execute(self, context):
        preset = P.find(self.preset)
        if preset is None or not P.is_overlay(preset):
            return {'CANCELLED'}
        objs = _selected_material_objects(context)
        if not objs:
            self.report({'ERROR'}, 'Select an object first (left-click it in the 3D view).')
            return {'CANCELLED'}
        done, users = [], {}
        for obj in objs:
            B.restore_procedural(obj)  # dirt goes on the procedural material, not the baked one
            mat = obj.active_material or _plain_material(obj)
            users.setdefault(mat, []).append(obj)
        settings = context.scene.bpm
        for mat, mat_objs in users.items():
            if mat.library is not None:
                self.report({'WARNING'}, '"%s" is linked from another file and cannot be changed.' % mat.name)
                continue
            try:
                node = L.add_overlay(mat, preset['generator'], L.preset_values(preset))
            except L.OverlayError as exc:
                self.report({'WARNING'}, str(exc))
                continue
            node.label = preset['name']
            _fit(node, mat_objs, preset['generator'], settings)
            done.append(mat)
        if not done:
            return {'CANCELLED'}
        self.report({'INFO'}, 'Added "%s" on top of %d material%s.' % (preset['name'], len(done),
                                                                       's' * (len(done) > 1)))
        return {'FINISHED'}


class _OverlayOperator:
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    index: IntProperty()

    def _target(self, context):
        obj = context.active_object
        mat = obj.active_material if L.can_have_material(obj) else None
        stack = L.overlay_stack(mat)
        if not 0 <= self.index < len(stack):
            return mat, None
        return mat, stack[self.index]


class BPM_OT_remove_overlay(_OverlayOperator, bpy.types.Operator):
    """Remove this layer (a decal stays off this material until you click Update Decal)"""
    bl_idname = 'bpm.remove_overlay'
    bl_label = 'Remove Overlay'

    def execute(self, context):
        mat, node = self._target(context)
        if node is None:
            return {'CANCELLED'}
        if D.is_decal_group(node.node_tree):
            D.exclude(mat, node.node_tree)  # baking would put it back otherwise
        L.remove_overlay(mat, node)
        return {'FINISHED'}


class BPM_OT_move_overlay(_OverlayOperator, bpy.types.Operator):
    """Move this layer up (on top of the others) or down"""
    bl_idname = 'bpm.move_overlay'
    bl_label = 'Move Overlay'

    step: IntProperty(default=1)

    def execute(self, context):
        mat, node = self._target(context)
        if node is None or not L.move_overlay(mat, self.index, self.step):
            return {'CANCELLED'}
        return {'FINISHED'}


class BPM_OT_toggle_overlay(_OverlayOperator, bpy.types.Operator):
    """Hide or show this layer (compare with / without it)"""
    bl_idname = 'bpm.toggle_overlay'
    bl_label = 'Show / Hide Overlay'

    def execute(self, context):
        mat, node = self._target(context)
        if node is None:
            return {'CANCELLED'}
        L.toggle_overlay(node)
        return {'FINISHED'}


class BPM_OT_overlay_seed(_OverlayOperator, bpy.types.Operator):
    """Pick a new random variation of this layer"""
    bl_idname = 'bpm.overlay_seed'
    bl_label = 'New Variation'

    def execute(self, context):
        mat, node = self._target(context)
        if node is None or 'Seed' not in node.inputs:
            return {'CANCELLED'}
        node.inputs['Seed'].default_value = round(random.uniform(0.0, 100.0), 2)
        return {'FINISHED'}


# --------------------------------------------------------------------- bake
NO_OBJECTS = {
    'ACTIVE': 'Click the object you want to texture first (there is no active object).',
    'SELECTED': 'Select the object(s) you want to texture first.',
    'SCENE': 'There are no visible mesh objects in the scene.',
}


def _scope_objects(context):
    scope = context.scene.bpm.bake_scope
    objs = B.scope_objects(context, scope)
    if not objs:
        raise B.BakeError(NO_OBJECTS.get(scope, NO_OBJECTS['SELECTED']))
    return objs


class _BakeRunner:
    """Runs a bake job step by step (modal, with progress and Esc to cancel)."""
    bl_options = {'REGISTER'}

    _job = None
    _steps = None
    _timer = None
    undo_message = 'BPM Bake'

    def _make_job(self, context):
        raise NotImplementedError

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
            done = len(getattr(self._job, 'baked', ()))
            message = 'Bake cancelled.'
            if done:
                message += ' The %d object%s finished before keep%s the new textures.' % (
                    done, 's' * (done > 1), '' if done > 1 else 's')
            return self._finish(context, message, level='WARNING')
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
            props = context.scene.bpm
            props.last_report, props.last_level, props.last_warnings = str(exc), 'ERROR', ''
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
            props = context.scene.bpm
            props.last_report, props.last_level, props.last_warnings = message, level, ''
        else:
            self._report(context, self._job)
        try:
            bpy.ops.ed.undo_push(message=self.undo_message)
        except RuntimeError:
            pass
        _redraw(context)
        return {'FINISHED'} if level == 'INFO' else {'CANCELLED'}

    def _report(self, context, job):
        warnings = job.warnings()
        for text in warnings:
            self.report({'WARNING'}, text)
        props = context.scene.bpm
        props.last_folder = job.output_dir or ''
        summary = job.summary()
        props.last_report = summary
        props.last_level = 'WARNING' if warnings else 'INFO'
        props.last_warnings = '\n'.join(warnings)
        self.report({'INFO'}, summary)


class BPM_OT_bake(_BakeRunner, bpy.types.Operator):
    """Bake the material(s) to image textures, using the objects' current UV maps. Press Esc to cancel"""
    bl_idname = 'bpm.bake'
    bl_label = 'Bake Textures'

    @classmethod
    def description(cls, context, properties):
        if context.scene.bpm.bake_mode == 'TILE':
            return 'Bake the active material into square textures that repeat seamlessly. Press Esc to cancel'
        return cls.__doc__

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
        return B.ObjectBakeJob(context, _scope_objects(context), settings)


class BPM_OT_auto_texture(_BakeRunner, bpy.types.Operator):
    """One click: new UVs (Smart UV Project + Pack Islands), bake all maps, save them and apply them. Esc cancels"""
    bl_idname = 'bpm.auto_texture'
    bl_label = 'Auto Texture'
    undo_message = 'BPM Auto Texture'

    def _make_job(self, context):
        settings = B.BakeSettings.from_props(context.scene.bpm)
        settings.force_new_uv = True
        settings.assign_baked = True
        objects = _scope_objects(context)
        job = B.ObjectBakeJob(context, objects, settings)
        props = context.scene.bpm
        if props.auto_mesh_maps:
            job = M.analyze_then_bake(context, objects, job, M.MapsSettings.from_props(props))
        return job


class BPM_OT_analyze_shape(_BakeRunner, bpy.types.Operator):
    """Analyze the shape of the objects (outer edges, inner corners, occlusion) once, like the curvature and
AO maps of texture painting programs: edge wear and grime then follow the shape exactly and look the same in
Material Preview (EEVEE) and Cycles. Run it again after editing a mesh. Esc cancels"""
    bl_idname = 'bpm.analyze_shape'
    bl_label = 'Analyze Shape'
    undo_message = 'BPM Analyze Shape'

    def _make_job(self, context):
        return M.MapsJob(context, _scope_objects(context), M.MapsSettings.from_props(context.scene.bpm))


class BPM_OT_remove_mesh_maps(bpy.types.Operator):
    """Remove the mesh maps of the objects: their materials go back to live edge and cavity detection"""
    bl_idname = 'bpm.remove_mesh_maps'
    bl_label = 'Remove Mesh Maps'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            objs = _scope_objects(context)
        except B.BakeError as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        meshes = {o.data for o in objs if o.type == 'MESH' and o.data.library is None and o.data.get(M.FLAG)}
        if not meshes:
            self.report({'INFO'}, 'These objects have no mesh maps.')
            return {'CANCELLED'}
        M.remove(meshes)
        self.report({'INFO'}, 'Removed the mesh maps of %d mesh%s.' % (len(meshes), 'es' * (len(meshes) != 1)))
        _redraw(context)
        return {'FINISHED'}


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


# ------------------------------------------------------------------- decals
def _view_region(area):
    for region in area.regions:
        if region.type == 'WINDOW':
            return region
    return None


def _draw_drag_box(op):
    if op.start is None or op.end is None:
        return
    import gpu
    from gpu_extras.batch import batch_for_shader
    (x0, y0), (x1, y1) = op.start, op.end
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    gpu.state.blend_set('ALPHA')
    batch = batch_for_shader(shader, 'TRIS', {'pos': corners}, indices=((0, 1, 2), (0, 2, 3)))
    shader.uniform_float('color', (1.0, 0.55, 0.1, 0.15))
    batch.draw(shader)
    batch = batch_for_shader(shader, 'LINE_LOOP', {'pos': corners})
    shader.uniform_float('color', (1.0, 0.55, 0.1, 1.0))
    batch.draw(shader)
    gpu.state.blend_set('NONE')


def place_decal(context, region, rv3d, rect, image):
    """Shoot rays through the rectangle `rect` (region pixels: x0, y0, x1, y1) and put a decal box
    on what they hit.  Returns (box, objects showing the decal, warnings), box None if nothing was hit."""
    from bpy_extras import view3d_utils
    from mathutils import Vector
    x0, y0, x1, y1 = rect
    scene = context.scene
    depsgraph = context.evaluated_depsgraph_get()

    def ray(px, py):
        return (view3d_utils.region_2d_to_origin_3d(region, rv3d, (px, py)),
                view3d_utils.region_2d_to_vector_3d(region, rv3d, (px, py)))

    steps = 8
    points = [((x0 + x1) / 2.0, (y0 + y1) / 2.0)]
    points += [(x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * j / steps)
               for i in range(steps + 1) for j in range(steps + 1)]
    hits, hit = [], set()
    for px, py in points:
        origin, direction = ray(px, py)
        found, location, normal, _index, obj, _matrix = scene.ray_cast(depsgraph, origin, direction)
        obj = getattr(obj, 'original', obj)
        if found and L.can_have_material(obj) and not D.is_box(obj):
            hits.append((location, normal))
            hit.add(obj)
    if not hits:
        return None, [], []
    corners = [ray(x0, y0), ray(x1, y0), ray(x1, y1), ray(x0, y1)]
    width, height = image.size
    aspect = width / height if width and height else 1.0
    matrix = D.box_from_hits(hits, corners, rv3d.view_rotation @ Vector((1.0, 0.0, 0.0)),
                             rv3d.view_rotation @ Vector((0.0, 0.0, -1.0)), aspect)
    box = D.create(scene, image, matrix)
    targets = list(hit) + [o for o in D.candidates(scene) if o not in hit and D.touches(box, o)]
    warnings, shown = [], []
    for obj in targets:
        B.restore_procedural(obj)  # the decal goes on the procedural material, not a baked one
        if D.add_to(box, obj, warnings, force=True):
            shown.append(obj)
    for obj in context.selected_objects:
        obj.select_set(False)
    box.select_set(True)
    context.view_layer.objects.active = box
    return box, shown, warnings


class BPM_OT_place_decal(bpy.types.Operator):
    """Drag a box over your model: the decal goes on everything inside the box"""
    bl_idname = 'bpm.place_decal'
    bl_label = 'Place Decal'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.scene.bpm.decal_image is None:
            cls.poll_message_set('Open the decal image first')
            return False
        return context.screen is not None

    def invoke(self, context, event):
        area = context.area if context.area is not None and context.area.type == 'VIEW_3D' else \
            next((a for a in context.screen.areas if a.type == 'VIEW_3D'), None)
        region = _view_region(area) if area is not None else None
        if region is None or area.spaces.active.region_3d is None:
            self.report({'ERROR'}, 'Use this in a 3D view.')
            return {'CANCELLED'}
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        self.area, self.region, self.rv3d = area, region, area.spaces.active.region_3d
        self.start = self.end = None
        self.handle = bpy.types.SpaceView3D.draw_handler_add(_draw_drag_box, (self,), 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self)
        context.window.cursor_modal_set('CROSSHAIR')
        area.header_text_set('Decal: drag a box over your model    (right-click or Esc: cancel)')
        return {'RUNNING_MODAL'}

    def _stop(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.handle, 'WINDOW')
        context.window.cursor_modal_restore()
        self.area.header_text_set(None)
        self.area.tag_redraw()

    def modal(self, context, event):
        x, y = event.mouse_x - self.region.x, event.mouse_y - self.region.y
        inside = 0 <= x < self.region.width and 0 <= y < self.region.height
        if event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            self._stop(context)
            return {'CANCELLED'}
        if event.type == 'LEFTMOUSE':
            if event.value == 'PRESS' and inside:
                self.start = self.end = (x, y)
            elif event.value == 'RELEASE' and self.start is not None:
                self.end = (x, y)
                self._stop(context)
                return self._place(context)
            return {'RUNNING_MODAL'}
        if event.type == 'MOUSEMOVE':
            if self.start is not None:
                self.end = (x, y)
                self.area.tag_redraw()
            return {'RUNNING_MODAL'}
        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'TRACKPADPAN', 'TRACKPADZOOM'} \
                or event.type.startswith(('NDOF', 'NUMPAD')):
            return {'PASS_THROUGH'}  # look around while placing
        return {'RUNNING_MODAL'}

    def _place(self, context):
        (x0, y0), (x1, y1) = self.start, self.end
        if abs(x1 - x0) < 6 or abs(y1 - y0) < 6:  # just a click: a box a quarter of the view high
            half = self.region.height / 8.0
            x0, x1, y0, y1 = x1 - half, x1 + half, y1 - half, y1 + half
        rect = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
        box, shown, warnings = place_decal(context, self.region, self.rv3d, rect, context.scene.bpm.decal_image)
        if box is None:
            self.report({'WARNING'}, 'No object under the box: drag it over your model.')
            return {'CANCELLED'}
        for text in warnings:
            self.report({'WARNING'}, text)
        self.report({'INFO'}, 'Decal on %d object%s. Move, scale or rotate the box (G, S, R) to adjust it.'
                    % (len(shown), 's' * (len(shown) != 1)))
        return {'FINISHED'}


def _decal_box(context, name):
    obj = bpy.data.objects.get(name) if name else context.active_object
    return obj if D.is_box(obj) else None


class BPM_OT_decal_refresh(bpy.types.Operator):
    """Put the decal on everything that is inside its box now (after moving it over other objects)"""
    bl_idname = 'bpm.decal_refresh'
    bl_label = 'Update Decal'
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty()

    def execute(self, context):
        box = _decal_box(context, self.name)
        if box is None:
            return {'CANCELLED'}
        inside = [o for o in D.candidates(context.scene) if D.touches(box, o)]
        for obj in inside:
            B.restore_procedural(obj)
        warnings = []
        shown = [o for o in inside if D.add_to(box, o, warnings, force=True)]
        for text in warnings:
            self.report({'WARNING'}, text)
        self.report({'INFO'}, '"%s" is on %d object%s.' % (box.name, len(shown), 's' * (len(shown) != 1)))
        return {'FINISHED'}


class BPM_OT_decal_remove(bpy.types.Operator):
    """Delete this decal (its box and the decal on every material)"""
    bl_idname = 'bpm.decal_remove'
    bl_label = 'Remove Decal'
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty()

    def execute(self, context):
        box = _decal_box(context, self.name)
        if box is None:
            return {'CANCELLED'}
        D.remove(box)
        return {'FINISHED'}


class BPM_OT_decal_select(bpy.types.Operator):
    """Select this decal's box (to move, scale or rotate it and change its settings)"""
    bl_idname = 'bpm.decal_select'
    bl_label = 'Select Decal'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    name: StringProperty()

    def execute(self, context):
        box = _decal_box(context, self.name)
        if box is None or not box.visible_get():
            return {'CANCELLED'}
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        for obj in context.selected_objects:
            obj.select_set(False)
        box.select_set(True)
        context.view_layer.objects.active = box
        return {'FINISHED'}


class BPM_OT_decal_find_maps(bpy.types.Operator):
    """Look for the decal's normal, roughness, metallic and height maps next to its image file"""
    bl_idname = 'bpm.decal_find_maps'
    bl_label = 'Find PBR Maps'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        box = _decal_box(context, '')
        if box is None or box.bpm_decal.color_map is None:
            return {'CANCELLED'}
        found = D.image_maps(box.bpm_decal.color_map)
        for key, image in found.items():
            if key != 'COLOR':
                setattr(box.bpm_decal, D.MAP_PROPS[key], image)
        names = [k.title() for k in found if k != 'COLOR']
        self.report({'INFO'}, 'Found: %s.' % ', '.join(names) if names else 'No other maps next to the image.')
        return {'FINISHED'}


CLASSES = (
    BPM_OT_apply_preset,
    BPM_OT_gallery_step,
    BPM_OT_load_preset,
    BPM_OT_reset_material,
    BPM_OT_randomize_seed,
    BPM_OT_fit_scale,
    BPM_OT_set_vector,
    BPM_OT_set_value,
    BPM_OT_make_unique,
    BPM_OT_preview_cycles,
    BPM_OT_preview_material,
    BPM_OT_add_overlay,
    BPM_OT_remove_overlay,
    BPM_OT_move_overlay,
    BPM_OT_toggle_overlay,
    BPM_OT_overlay_seed,
    BPM_OT_bake,
    BPM_OT_auto_texture,
    BPM_OT_analyze_shape,
    BPM_OT_remove_mesh_maps,
    BPM_OT_open_folder,
    BPM_OT_show_procedural,
    BPM_OT_show_baked,
    BPM_OT_place_decal,
    BPM_OT_decal_refresh,
    BPM_OT_decal_remove,
    BPM_OT_decal_select,
    BPM_OT_decal_find_maps,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
