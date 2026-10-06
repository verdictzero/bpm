# SPDX-License-Identifier: GPL-3.0-or-later
"""Render the gallery thumbnails for every preset (Cycles, headless).

    blender -b --factory-startup -P tools/render_thumbnails.py -- [--size 256] [--samples 48]
            [--out DIR] [--only id,id,...]
"""

import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import preview_scene  # noqa: E402
from bpm_procedural_metals import generators as G  # noqa: E402
from bpm_procedural_metals import library as L  # noqa: E402
from bpm_procedural_metals import presets as P  # noqa: E402


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument('--size', type=int, default=256)
    parser.add_argument('--samples', type=int, default=48)
    parser.add_argument('--out', default=os.path.join(ROOT, 'bpm_procedural_metals', 'thumbnails'))
    parser.add_argument('--only', default='')
    parser.add_argument('--shape', default='cube')
    args = parser.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    only = {s.strip() for s in args.only.split(',') if s.strip()}

    for preset in P.PRESETS:
        if only and preset['id'] not in only:
            continue
        names = {p.name for p in G.params_for(preset['generator'])}
        unknown = set(preset['values']) - names
        if unknown:
            raise SystemExit('Preset %s has unknown values: %s' % (preset['id'], sorted(unknown)))
        start = time.time()
        scene, obj = preview_scene.setup(size=args.size, samples=args.samples, shape=args.shape)
        mat = L.create_material(preset['id'])
        obj.data.materials.append(mat)
        preview_scene.render(os.path.join(args.out, preset['id'] + '.png'))
        print('THUMB %-28s %.1fs' % (preset['id'], time.time() - start), flush=True)


main()
