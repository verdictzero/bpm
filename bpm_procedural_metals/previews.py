# SPDX-License-Identifier: GPL-3.0-or-later
"""Thumbnail icons for the material gallery."""

import os
import zlib

import bpy

from . import presets as P

_collection = None
_items = {}  # keeps EnumProperty items alive (Blender requires this)
# The id the gallery shows.  The gallery stores a number, and reading it from Python
# prints a warning once the number matches no item (another category, a deleted
# preset, a newly loaded file), so the panels use this instead.
_current = None
_shown_in = None  # the category it was picked in


def thumbnails_dir():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'thumbnails')


def _thumbnail_path(preset_id):
    path = os.path.join(thumbnails_dir(), preset_id + '.png')
    if not os.path.exists(path):
        from . import user_presets
        if preset_id.startswith(user_presets.PREFIX):
            return user_presets.thumbnail_path(preset_id)
    return path


_reload = set()  # thumbnails that changed on disk


def icon_id(preset_id):
    if _collection is None:
        return 0
    if preset_id not in _collection:
        path = _thumbnail_path(preset_id)
        if not os.path.exists(path):
            return 0
        try:
            _collection.load(preset_id, path, 'IMAGE', force_reload=preset_id in _reload)
        except (KeyError, RuntimeError):
            return 0
        _reload.discard(preset_id)
    return _collection[preset_id].icon_id


def forget(preset_id):
    """A thumbnail was saved or deleted: load it again next time."""
    if _collection is not None and preset_id in _collection:
        del _collection[preset_id]
    _reload.add(preset_id)


# The gallery popup hands the picked item's number back as a float, so numbers above
# 2**24 come back rounded and match no item: clicking a thumbnail did nothing.
_MAX_NUMBER = 0xFFFFFF


def _number(preset_id, taken):
    """A stable item number (the same in every category, and when presets come and go)."""
    number = (zlib.crc32(preset_id.encode('utf-8')) & _MAX_NUMBER) or 1
    while number in taken:
        number = number % _MAX_NUMBER + 1
    return number


def _category(context):
    if context is not None and getattr(context, 'scene', None) is not None and hasattr(context.scene, 'bpm'):
        return context.scene.bpm.category
    return 'ALL'


def gallery_items(self, context):
    category = _category(context)
    items, taken = [], {0}
    for preset in P.PRESETS:
        if P.in_category(preset, category):
            # the first item is 0, the default, so a new gallery shows something valid
            number = _number(preset['id'], taken) if items else 0
            taken.add(number)
            items.append((preset['id'], preset['name'], preset['desc'], icon_id(preset['id']), number))
    if not items:
        items = [('NONE', 'No materials', '', 0, 0)]
    _items[category] = items
    return items


def picked(self, context):
    """Update of the gallery property."""
    global _current, _shown_in
    _current = self.bpm_gallery
    _shown_in = _category(context)


def current(context):
    """The id of the material the gallery shows, or None (no materials).  When the
    gallery's stored number is unknown or stale, this schedules sync() and returns
    the material it will show."""
    ids = [item[0] for item in gallery_items(None, context)]
    if _current not in ids or _shown_in != _category(context):  # e.g. after an undo or another scene
        _sync_soon()
        if _current in ids and _current != 'NONE':
            return _current
        return ids[0] if ids[0] != 'NONE' else None
    return _current if _current != 'NONE' else None


def sync(context=None):
    """Point the gallery at a material of its category (the one it showed, if there)."""
    global _current, _shown_in
    context = context or bpy.context
    wm = getattr(context, 'window_manager', None)
    if wm is None or wm.bl_rna.properties.get('bpm_gallery') is None:  # (hasattr would read it)
        return
    ids = [item[0] for item in gallery_items(None, context)]
    wanted = _current if _current in ids else ids[0]
    try:
        wm.bpm_gallery = wanted
    except (TypeError, AttributeError, RuntimeError):
        return
    _current, _shown_in = wanted, _category(context)


def _sync_soon():
    if not bpy.app.timers.is_registered(_sync_timer):
        bpy.app.timers.register(_sync_timer, first_interval=0.0)


def _sync_timer():
    try:
        sync()
    except (AttributeError, ReferenceError, RuntimeError):
        pass
    return None


@bpy.app.handlers.persistent
def _on_load(*_args):
    global _current
    _current = None  # the loaded file's gallery number may be stale


def register():
    global _collection
    try:
        import bpy.utils.previews as collections
        _collection = collections.new()
    except Exception:  # e.g. very restricted background sessions
        _collection = None
    if _on_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_on_load)


def unregister():
    global _collection, _current, _shown_in
    if _on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load)
    if bpy.app.timers.is_registered(_sync_timer):
        bpy.app.timers.unregister(_sync_timer)
    _current = _shown_in = None
    if _collection is not None:
        import bpy.utils.previews as collections
        collections.remove(_collection)
    _collection = None
    _items.clear()
