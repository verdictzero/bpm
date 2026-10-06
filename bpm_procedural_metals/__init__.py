# SPDX-License-Identifier: GPL-3.0-or-later
"""BPM - Procedural Metals.

A library of procedural bare-metal and painted-metal materials with simple
sliders, plus one-click baking to image textures.

Find it in: 3D Viewport > Sidebar (press N) > BPM tab.
"""

bl_info = {
    "name": "BPM - Procedural Metals",
    "author": "verdictzero",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "3D Viewport > Sidebar (N) > BPM",
    "description": "Procedural metal and painted metal materials with sliders and one-click texture baking",
    "doc_url": "https://github.com/verdictzero/bpm",
    "category": "Material",
}

if "bpy" in locals():  # support "Reload Scripts"
    import importlib
    for _name in ('nodebuilder', 'features', 'generators', 'presets', 'library', 'bake', 'props',
                  'previews', 'operators', 'ui'):
        if _name in locals():
            importlib.reload(locals()[_name])

import bpy  # noqa: E402,F401

from . import nodebuilder, features, generators, presets, library, bake  # noqa: E402,F401
from . import props, previews, operators, ui  # noqa: E402

_MODULES = (props, previews, operators, ui)


def register():
    for module in _MODULES:
        module.register()


def unregister():
    for module in reversed(_MODULES):
        module.unregister()
