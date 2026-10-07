# SPDX-License-Identifier: GPL-3.0-or-later
"""BPM - Procedural Materials.

A library of procedural materials (bare and painted metal, wood, plastic, glass,
leather, fabric and composites, biomechanical surfaces) with simple sliders,
dirt and dust overlays that layer on top of any material, and one-click
"Auto Texture": new UVs, baking to image textures and applying them.

Find it in: 3D Viewport > Sidebar (press N) > BPM tab.
"""

bl_info = {
    "name": "BPM - Procedural Materials",
    "author": "verdictzero",
    "version": (1, 3, 0),
    "blender": (4, 2, 0),
    "location": "3D Viewport > Sidebar (N) > BPM",
    "description": "Procedural metal, paint, wood, plastic, glass, leather, fabric and biomechanical materials, "
                   "dirt and dust overlays, and one-click auto texturing (UVs, bake, apply)",
    "doc_url": "https://github.com/verdictzero/bpm",
    "category": "Material",
}

_SUBMODULES = ('nodebuilder', 'features', 'gencommon', 'mat_metal', 'mat_paint', 'mat_wood', 'mat_plastic',
               'mat_glass', 'mat_leather', 'mat_fabric', 'mat_organic', 'overlays', 'generators', 'presets',
               'library', 'bake', 'props', 'previews', 'operators', 'ui')

if "bpy" in locals():  # support "Reload Scripts"
    import importlib
    for _name in _SUBMODULES:
        if _name in locals():
            importlib.reload(locals()[_name])

import bpy  # noqa: E402,F401

from . import nodebuilder, features, gencommon  # noqa: E402,F401
from . import mat_metal, mat_paint, mat_wood, mat_plastic, mat_glass  # noqa: E402,F401
from . import mat_leather, mat_fabric, mat_organic  # noqa: E402,F401
from . import overlays, generators, presets, library, bake  # noqa: E402,F401
from . import props, previews, operators, ui  # noqa: E402

_MODULES = (props, previews, operators, ui)


def register():
    for module in _MODULES:
        module.register()


def unregister():
    for module in reversed(_MODULES):
        module.unregister()
