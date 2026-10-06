# SPDX-License-Identifier: GPL-3.0-or-later
"""Run BPM Procedural Metals from the command line (no Blender window needed).

Examples (use the path to your Blender executable instead of "blender"):

    blender -b -P bpm_cli.py -- list
    blender -b -P bpm_cli.py -- tile --preset all --size 1024 --out ./textures
    blender -b -P bpm_cli.py -- tile --preset "Hazard Stripes" --size 2048 --directx --orm
    blender -b my_model.blend -P bpm_cli.py -- apply --preset steel_brushed --objects Body --save
    blender -b my_model.blend -P bpm_cli.py -- bake --objects Body,Lid --size 2048 --save

Add "--help" after a command to see all its options.
"""

import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))


def _load_addon():
    """Use the installed add-on if there is one, otherwise the copy next to this script."""
    import addon_utils
    for mod in addon_utils.modules():
        if mod.__name__.endswith('bpm_procedural_metals'):
            addon_utils.enable(mod.__name__, default_set=False)
            return sys.modules[mod.__name__]
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import bpm_procedural_metals
    if not hasattr(bpy.types.Scene, 'bpm'):
        bpm_procedural_metals.register()
    return bpm_procedural_metals


def main():
    addon = _load_addon()
    cli = sys.modules[addon.__name__ + '.cli'] if addon.__name__ + '.cli' in sys.modules else None
    if cli is None:
        import importlib
        cli = importlib.import_module(addon.__name__ + '.cli')
    try:
        cli.main()
    except SystemExit as exc:
        if exc.code not in (None, 0):
            print(exc.code if isinstance(exc.code, str) else 'BPM: failed', file=sys.stderr)
            sys.stdout.flush()
            os._exit(1)


main()
