# SPDX-License-Identifier: GPL-3.0-or-later
"""Thumbnail icons for the material gallery."""

import os

from . import presets as P

_collection = None
_items = {}  # keeps EnumProperty items alive (Blender requires this)


def thumbnails_dir():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'thumbnails')


def icon_id(preset_id):
    if _collection is None:
        return 0
    if preset_id not in _collection:
        path = os.path.join(thumbnails_dir(), preset_id + '.png')
        if not os.path.exists(path):
            return 0
        try:
            _collection.load(preset_id, path, 'IMAGE')
        except (KeyError, RuntimeError):
            return 0
    return _collection[preset_id].icon_id


def gallery_items(self, context):
    category = 'ALL'
    if context is not None and getattr(context, 'scene', None) is not None and hasattr(context.scene, 'bpm'):
        category = context.scene.bpm.category
    items = []
    for number, preset in enumerate(P.PRESETS):
        if category in {'ALL', preset['category']}:
            items.append((preset['id'], preset['name'], preset['desc'], icon_id(preset['id']), number))
    if not items:
        items = [('NONE', 'No materials', '', 0, 999)]
    _items[category] = items
    return items


def register():
    global _collection
    try:
        import bpy.utils.previews
        _collection = bpy.utils.previews.new()
    except Exception:  # e.g. very restricted background sessions
        _collection = None


def unregister():
    global _collection
    if _collection is not None:
        import bpy.utils.previews
        bpy.utils.previews.remove(_collection)
    _collection = None
    _items.clear()
