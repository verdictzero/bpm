# SPDX-License-Identifier: GPL-3.0-or-later
"""BPM - Procedural Materials.

A library of procedural materials (bare and painted metal, military paint and
camouflage, concrete, terrain and lava, gradients, wood, plastic, glass, lenses,
leather, fabric and composites, biomechanical surfaces) with simple sliders and
your own saved presets, overlays (dirt, dust, moss, edge wear, scratches) that layer on
top of any material, box-projected decals, and one-click "Auto Texture": new UVs, baking to image textures and applying them.

Find it in: 3D Viewport > Sidebar (press N) > BPM tab.
"""

bl_info = {
    "name": "BPM - Procedural Materials",
    "author": "verdictzero",
    "version": (1, 11, 0),
    "blender": (4, 2, 0),
    "location": "3D Viewport > Sidebar (N) > BPM",
    "description": "Procedural metal, paint, porcelain enamel, camouflage, concrete, lights and neon, wood, "
                   "plastic, glass, lens, leather, fabric and biomechanical materials, dirt, dust, moss, wear and "
                   "scratch overlays, decals, and one-click auto texturing (UVs, bake, apply)",
    "doc_url": "https://github.com/verdictzero/bpm",
    "category": "Material",
}

_SUBMODULES = ('nodebuilder', 'features', 'gencommon', 'mat_metal', 'mat_paint', 'mat_camo', 'mat_concrete',
               'mat_masonry', 'mat_wood', 'mat_plastic', 'mat_glass', 'mat_lens', 'mat_leather', 'mat_fabric', 'mat_organic', 'mat_terrain',
               'mat_gradient', 'mat_enamel', 'mat_light', 'overlays', 'generators', 'presets', 'user_presets',
               'library', 'decals', 'bake', 'meshmaps', 'mapsview', 'props', 'previews', 'operators', 'ui')

if "bpy" in locals():  # support "Reload Scripts"
    import importlib
    for _name in _SUBMODULES:
        if _name in locals():
            importlib.reload(locals()[_name])

import bpy  # noqa: E402,F401

from . import nodebuilder, features, gencommon  # noqa: E402,F401
from . import mat_metal, mat_paint, mat_camo, mat_concrete, mat_wood, mat_plastic  # noqa: E402,F401
from . import mat_glass, mat_lens, mat_leather, mat_fabric, mat_organic  # noqa: E402,F401
from . import mat_terrain, mat_gradient, mat_enamel, mat_light, mat_masonry  # noqa: E402,F401
from . import overlays, generators, presets, library, decals, bake, meshmaps, mapsview  # noqa: E402,F401
from . import user_presets, props, previews, operators, ui  # noqa: E402

_MODULES = (decals, user_presets, props, previews, operators, ui)


def register():
    for module in _MODULES:
        module.register()


def unregister():
    for module in reversed(_MODULES):
        module.unregister()
