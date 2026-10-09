# SPDX-License-Identifier: GPL-3.0-or-later
"""BPM - Procedural Materials.

A library of procedural materials (bare and painted metal, military paint and
camouflage, concrete, wood, plastic, glass, lenses, leather, fabric and composites,
biomechanical surfaces) with simple sliders, overlays (dirt, dust, edge wear,
scratches) that layer on top of any material, box-projected decals, and
one-click "Auto Texture": new UVs, baking to image textures and applying them.

Find it in: 3D Viewport > Sidebar (press N) > BPM tab.
"""

bl_info = {
    "name": "BPM - Procedural Materials",
    "author": "verdictzero",
    "version": (1, 5, 0),
    "blender": (4, 2, 0),
    "location": "3D Viewport > Sidebar (N) > BPM",
    "description": "Procedural metal, paint, camouflage, concrete, wood, plastic, glass, lens, leather, fabric and "
                   "biomechanical materials, dirt, dust, wear and scratch overlays, decals, and one-click "
                   "auto texturing (UVs, bake, apply)",
    "doc_url": "https://github.com/verdictzero/bpm",
    "category": "Material",
}

_SUBMODULES = ('nodebuilder', 'features', 'gencommon', 'mat_metal', 'mat_paint', 'mat_camo', 'mat_concrete', 'mat_wood',
               'mat_plastic', 'mat_glass', 'mat_lens', 'mat_leather', 'mat_fabric', 'mat_organic', 'overlays',
               'generators', 'presets', 'library', 'decals', 'bake', 'props', 'previews', 'operators', 'ui')

if "bpy" in locals():  # support "Reload Scripts"
    import importlib
    for _name in _SUBMODULES:
        if _name in locals():
            importlib.reload(locals()[_name])

import bpy  # noqa: E402,F401

from . import nodebuilder, features, gencommon  # noqa: E402,F401
from . import mat_metal, mat_paint, mat_camo, mat_concrete, mat_wood, mat_plastic  # noqa: E402,F401
from . import mat_glass, mat_lens, mat_leather, mat_fabric, mat_organic  # noqa: E402,F401
from . import overlays, generators, presets, library, decals, bake  # noqa: E402,F401
from . import props, previews, operators, ui  # noqa: E402

_MODULES = (decals, props, previews, operators, ui)


def register():
    for module in _MODULES:
        module.register()


def unregister():
    for module in reversed(_MODULES):
        module.unregister()
