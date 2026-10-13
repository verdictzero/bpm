# SPDX-License-Identifier: GPL-3.0-or-later
"""Your own presets: the settings of a material saved under a name of your choice.

They are kept in one JSON file outside the add-on folder (so updating or
reinstalling the add-on keeps them), next to a small thumbnail per preset,
and show up in the gallery under 'My Presets' and under their material's
category.  The folder can be moved with the BPM_PRESET_DIR environment variable.
"""

import json
import os
import re

import bpy

from . import generators as G
from . import presets as P

FILE_NAME = 'user_presets.json'
VERSION = 1
PREFIX = 'user_'


def folder(create=True):
    """Where your presets live (created on demand)."""
    path = os.environ.get('BPM_PRESET_DIR')
    if not path:
        try:  # an extension: its own user folder, kept on updates
            path = bpy.utils.extension_path_user(__package__, path='presets', create=create)
        except (ValueError, AttributeError, RuntimeError):
            path = None
    if not path:  # a legacy add-on or a plain module
        path = bpy.utils.user_resource('CONFIG', path='bpm_user_presets', create=create)
    if create:
        os.makedirs(path, exist_ok=True)
    return path


def file_path():
    return os.path.join(folder(), FILE_NAME)


def thumbnail_path(preset_id):
    return os.path.join(folder(), preset_id + '.png')


def _jsonable(value):
    if isinstance(value, (int, float, bool, str)):
        return value
    return [float(v) for v in value]


def _from_json(value):
    return tuple(float(v) for v in value) if isinstance(value, list) else value


def _read():
    try:
        with open(file_path(), encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    entries = data.get('presets', []) if isinstance(data, dict) else []
    return [e for e in entries if isinstance(e, dict) and e.get('id') and e.get('generator')]


def _write(entries):
    path = file_path()
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump({'version': VERSION, 'presets': entries}, f, indent=1)
    os.replace(tmp, path)


def _to_preset(entry):
    """A JSON entry -> a library preset (None when its material type no longer exists)."""
    generator = entry['generator']
    if generator not in G.GENERATORS or G.is_overlay(generator) or G.GENERATORS[generator]['custom']:
        return None
    names = {p.name for p in G.params_for(generator)}
    values = {k: _from_json(v) for k, v in entry.get('values', {}).items() if k in names}
    overlays = []
    for item in entry.get('overlays', []):
        try:
            gen, ov_values = item
        except (TypeError, ValueError):
            continue
        if gen in G.GENERATORS and G.is_overlay(gen) and not G.GENERATORS[gen]['custom']:
            ov_names = {p.name for p in G.params_for(gen)}
            overlays.append((gen, {k: _from_json(v) for k, v in ov_values.items() if k in ov_names}))
    return dict(id=entry['id'], name=str(entry.get('name') or entry['id']), generator=generator,
                category=P.USER_CATEGORY, desc=str(entry.get('desc') or 'Your own preset.'),
                values=values, overlays=overlays, thumb={}, user=True)


def load():
    """(Re)load your presets into the library."""
    P.PRESETS[:] = [p for p in P.PRESETS if not p.get('user')]
    for entry in _read():
        preset = _to_preset(entry)
        if preset is not None and not any(p['id'] == preset['id'] for p in P.PRESETS):
            P.PRESETS.append(preset)


def user_presets():
    return [p for p in P.PRESETS if p.get('user')]


def slug(name):
    text = re.sub(r'[^a-z0-9]+', '_', name.strip().lower()).strip('_')
    return PREFIX + (text or 'preset')


def find_by_name(name):
    key = name.strip().lower()
    return next((p for p in user_presets() if p['name'].lower() == key), None)


def save(mat, name, desc='', include_overlays=True):
    """Save the settings of BPM material `mat` as your preset `name` (same name: replaced)."""
    from . import library as L
    node = L.find_bpm_node(mat)
    if node is None:
        raise ValueError('%s is not a BPM material' % mat.name)
    name = name.strip() or mat.name
    existing = find_by_name(name)
    pid = existing['id'] if existing else slug(name)
    taken = {p['id'] for p in P.PRESETS if p is not existing}
    number = 2
    base = pid
    while pid in taken:
        pid = '%s_%d' % (base, number)
        number += 1
    generator = node.node_tree['bpm_generator']
    names = {p.name for p in G.params_for(generator)}
    values = {k: _jsonable(v) for k, v in L.read_values(node).items() if k in names}
    overlays = []
    saved_nodes = []
    if include_overlays:
        for ov_node in L.overlay_stack(mat):
            state = L.OverlayState(ov_node)
            if state.tree is None and state.hidden_opacity is None:  # decals and hidden overlays stay out
                overlays.append([state.generator, {k: _jsonable(v) for k, v in state.values.items()}])
                saved_nodes.append(ov_node)
    entry = dict(id=pid, name=name, generator=generator, desc=desc.strip(), values=values, overlays=overlays)
    entries = [e for e in _read() if e['id'] != pid]
    entries.append(entry)
    _write(entries)
    load()
    mat['bpm_preset'] = pid
    for ov_node in L.overlay_stack(mat):  # the saved overlays now come with the preset (Reset, Load)
        if ov_node in saved_nodes:
            ov_node[L.PRESET_OVERLAY_TAG] = True
        elif ov_node.get(L.PRESET_OVERLAY_TAG):
            del ov_node[L.PRESET_OVERLAY_TAG]
    return P.get(pid)


def delete(preset_id):
    entries = _read()
    kept = [e for e in entries if e['id'] != preset_id]
    if len(kept) == len(entries):
        return False
    _write(kept)
    try:
        os.remove(thumbnail_path(preset_id))
    except OSError:
        pass
    load()
    from . import previews
    previews.forget(preset_id)
    return True


# ------------------------------------------------------------------ thumbnails
def save_thumbnail(mat, preset_id, tries=60):
    """Save Blender's own material preview as the preset's thumbnail.  The preview is rendered in
    the background, so this polls for a few seconds; returns at once without a UI."""
    if bpy.app.background:
        return
    try:
        mat.asset_generate_preview()  # renders it in the background
    except (AttributeError, RuntimeError):
        try:
            mat.preview_ensure()
        except (AttributeError, RuntimeError):
            return
    name = mat.name

    def poll():
        mat_now = bpy.data.materials.get(name)
        if mat_now is None or mat_now.preview is None:
            return None
        preview = mat_now.preview
        width, height = preview.image_size
        pixels = list(preview.image_pixels_float) if width and height else []
        if not pixels or max(pixels) <= 0.0:
            state['tries'] -= 1
            return 0.25 if state['tries'] > 0 else None
        _write_png(thumbnail_path(preset_id), width, height, pixels)
        from . import previews
        previews.forget(preset_id)
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
        return None

    state = {'tries': tries}
    bpy.app.timers.register(poll, first_interval=0.25)


def _write_png(path, width, height, pixels):
    img = bpy.data.images.new('.bpm_thumbnail', width, height, alpha=True)
    try:
        img.pixels.foreach_set(pixels)
        img.filepath_raw = path
        img.file_format = 'PNG'
        img.save()
    finally:
        bpy.data.images.remove(img)


def register():
    load()


def unregister():
    P.PRESETS[:] = [p for p in P.PRESETS if not p.get('user')]
