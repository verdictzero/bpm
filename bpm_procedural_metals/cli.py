# SPDX-License-Identifier: GPL-3.0-or-later
"""Command line interface: fully automated baking without opening Blender's UI.

Run through the ``bpm_cli.py`` script next to this add-on folder, for example::

    blender -b -P bpm_cli.py -- list
    blender -b -P bpm_cli.py -- tile --preset "Rusty Teal" --size 2048 --out ./textures
    blender -b -P bpm_cli.py -- tile --preset all --size 1024
    blender -b model.blend -P bpm_cli.py -- apply --preset steel_brushed --objects Body,Lid --save
    blender -b model.blend -P bpm_cli.py -- bake --objects Body,Lid --size 2048 --out ./textures
"""

import argparse
import sys

import bpy

from . import bake as B
from . import library as L
from . import presets as P

MAP_NAMES = {
    'basecolor': 'BASE_COLOR', 'base_color': 'BASE_COLOR', 'color': 'BASE_COLOR',
    'metallic': 'METALLIC', 'roughness': 'ROUGHNESS', 'normal': 'NORMAL',
    'height': 'HEIGHT', 'ao': 'AO',
}


def _parser():
    parser = argparse.ArgumentParser(prog='blender -b [file.blend] -P bpm_cli.py --',
                                     description='BPM Procedural Metals: batch tools')
    sub = parser.add_subparsers(dest='command', required=True)

    sub.add_parser('list', help='List all material presets')

    def bake_options(p):
        p.add_argument('--size', type=int, default=2048, help='Texture size in pixels (default 2048)')
        p.add_argument('--quality', choices=['fast', 'good', 'best'], default='good')
        p.add_argument('--out', default='//BPM_Textures', help='Output folder (default: //BPM_Textures)')
        p.add_argument('--maps', default='basecolor,metallic,roughness,normal,height,ao',
                       help='Comma separated: basecolor,metallic,roughness,normal,height,ao')
        p.add_argument('--directx', action='store_true', help='DirectX normal maps (Unreal Engine)')
        p.add_argument('--16bit', dest='use_16bit', action='store_true', help='16-bit PNG files')
        p.add_argument('--orm', action='store_true', help='Also save packed AO/Roughness/Metallic')
        p.add_argument('--unity', action='store_true', help='Also save Unity Metallic/Smoothness')
        p.add_argument('--gpu', action='store_true', help='Use the GPU if one is configured')

    tile = sub.add_parser('tile', help='Bake seamless tileable texture sets from presets')
    tile.add_argument('--preset', required=True, help='Preset id or name, comma separated, or "all"')
    tile.add_argument('--tile-size', type=float, default=1.0, help='Meters shown by one tile (default 1)')
    tile.add_argument('--scale', type=float, default=None, help='Override the pattern Scale')
    tile.add_argument('--seed', type=float, default=None, help='Override the pattern Seed')
    bake_options(tile)

    apply = sub.add_parser('apply', help='Apply a preset to objects in the opened .blend')
    apply.add_argument('--preset', required=True)
    apply.add_argument('--objects', required=True, help='Comma separated object names, or "selected"/"all"')
    apply.add_argument('--no-fit', action='store_true', help='Do not fit the pattern size to the objects')
    apply.add_argument('--save', action='store_true', help='Save the .blend file afterwards')

    bake = sub.add_parser('bake', help='Bake objects of the opened .blend to textures')
    bake.add_argument('--objects', default='selected', help='Comma separated names, or "selected"/"all"')
    bake.add_argument('--keep-material', action='store_true',
                      help='Do not switch the objects to the baked material')
    bake.add_argument('--save', action='store_true', help='Save the .blend file afterwards')
    bake_options(bake)
    return parser


def _objects(spec):
    if spec == 'all':
        return [o for o in bpy.context.view_layer.objects if o.type == 'MESH']
    if spec == 'selected':
        return [o for o in bpy.context.view_layer.objects if o.select_get()]
    objs = []
    for name in (n.strip() for n in spec.split(',') if n.strip()):
        obj = bpy.data.objects.get(name)
        if obj is None:
            raise SystemExit('No object called "%s" in this file.' % name)
        objs.append(obj)
    return objs


def _presets(spec):
    if spec.strip().lower() == 'all':
        return list(P.PRESETS)
    found = []
    for name in (n.strip() for n in spec.split(',') if n.strip()):
        preset = P.find(name)
        if preset is None:
            raise SystemExit('Unknown preset "%s". Run the "list" command to see all names.' % name)
        found.append(preset)
    return found


def _settings(args, **extra):
    maps = set()
    for name in args.maps.split(','):
        key = MAP_NAMES.get(name.strip().lower())
        if key is None:
            raise SystemExit('Unknown map "%s".' % name)
        maps.add(key)
    return B.BakeSettings(resolution=args.size, quality=args.quality.upper(), maps=maps, output_dir=args.out,
                          normal_directx=args.directx, use_16bit=args.use_16bit, pack_orm=args.orm,
                          pack_unity=args.unity, device='AUTO' if args.gpu else 'CPU', **extra)


def _print_messages(job):
    for level, text in job.messages:
        print('BPM %s: %s' % (level.lower(), text))
    print('BPM: wrote %d files to %s' % (len(job.written), job.output_dir))


def main(argv=None):
    if argv is None:
        argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    args = _parser().parse_args(argv)

    if args.command == 'list':
        for category, label, _ in P.CATEGORIES:
            print('\n%s:' % label)
            for p in P.by_category(category):
                print('  %-28s %s' % (p['id'], p['name']))
        return

    if args.command == 'tile':
        mats = []
        for preset in _presets(args.preset):
            mat = L.create_material(preset['id'])
            node = L.find_bpm_node(mat)
            if args.scale is not None:
                node.inputs['Scale'].default_value = args.scale
            if args.seed is not None:
                node.inputs['Seed'].default_value = args.seed
            mats.append(mat)
        job = B.TileBakeJob(bpy.context, mats, _settings(args, tile_size=args.tile_size,
                                                         create_tile_material=False))
        B.run_to_end(job)
        _print_messages(job)
        return

    if args.command == 'apply':
        preset = _presets(args.preset)[0]
        objs = [o for o in _objects(args.objects) if L.can_have_material(o)]
        if not objs:
            raise SystemExit('No objects to apply the material to.')
        mat = L.create_material(preset['id'])
        if not args.no_fit:
            L.find_bpm_node(mat).inputs['Scale'].default_value = L.fit_scale(objs)
        for obj in objs:
            L.assign_material(obj, mat)
        print('BPM: applied "%s" to %s' % (preset['name'], ', '.join(o.name for o in objs)))
        if args.save:
            bpy.ops.wm.save_mainfile()
        return

    if args.command == 'bake':
        objs = _objects(args.objects)
        job = B.ObjectBakeJob(bpy.context, objs, _settings(args, assign_baked=not args.keep_material))
        try:
            B.run_to_end(job)
        except B.BakeError as exc:
            raise SystemExit('BPM error: %s' % exc)
        _print_messages(job)
        if args.save:
            if not bpy.data.filepath:
                raise SystemExit('Cannot --save: open a .blend file first.')
            bpy.ops.wm.save_mainfile()
