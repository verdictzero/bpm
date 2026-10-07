# SPDX-License-Identifier: GPL-3.0-or-later
"""Command line interface: fully automated baking without opening Blender's UI.

Run through the ``bpm_cli.py`` script next to this add-on folder, for example::

    blender -b -P bpm_cli.py -- list
    blender -b -P bpm_cli.py -- tile --preset "Peeling Barn Red" --size 2048 --out ./textures
    blender -b -P bpm_cli.py -- tile --preset carbon_fiber_twill --overlay dust_light --size 1024
    blender -b -P bpm_cli.py -- tile --preset all --size 1024
    blender -b model.blend -P bpm_cli.py -- apply --preset steel_brushed --objects Body,Lid --save
    blender -b model.blend -P bpm_cli.py -- apply --preset dirt_grime --objects selected --save
    blender -b model.blend -P bpm_cli.py -- bake --objects Body,Lid --size 2048 --out ./textures
    blender -b model.blend -P bpm_cli.py -- auto --objects all --size 2048 --save
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
    'height': 'HEIGHT', 'ao': 'AO', 'transmission': 'TRANSMISSION',
}


def _parser():
    parser = argparse.ArgumentParser(prog='blender -b [file.blend] -P bpm_cli.py --',
                                     description='BPM Procedural Materials: batch tools')
    sub = parser.add_subparsers(dest='command', required=True)

    sub.add_parser('list', help='List all material presets')

    def bake_options(p):
        p.add_argument('--size', type=int, default=2048, help='Texture size in pixels (default 2048)')
        p.add_argument('--quality', choices=['fast', 'good', 'best'], default='good')
        p.add_argument('--out', default='//BPM_Textures', help='Output folder (default: //BPM_Textures)')
        p.add_argument('--maps', default='basecolor,metallic,roughness,transmission,normal,height,ao',
                       help='Comma separated: basecolor,metallic,roughness,transmission,normal,height,ao '
                            '(transmission is only written for glass)')
        p.add_argument('--directx', action='store_true', help='DirectX normal maps (Unreal Engine)')
        p.add_argument('--16bit', dest='use_16bit', action='store_true', help='16-bit PNG files')
        p.add_argument('--orm', action='store_true', help='Also save packed AO/Roughness/Metallic')
        p.add_argument('--unity', action='store_true', help='Also save Unity Metallic/Smoothness')
        p.add_argument('--gpu', action='store_true', help='Use the GPU if one is configured')

    tile = sub.add_parser('tile', help='Bake seamless tileable texture sets from presets')
    tile.add_argument('--preset', required=True, help='Preset id or name, comma separated, or "all"')
    tile.add_argument('--overlay', default='', help='Dirt / dust overlay presets to layer on top, comma separated')
    tile.add_argument('--tile-size', type=float, default=1.0, help='Meters shown by one tile (default 1)')
    tile.add_argument('--scale', type=float, default=None, help='Override the pattern Scale')
    tile.add_argument('--seed', type=float, default=None, help='Override the pattern Seed')
    bake_options(tile)

    apply = sub.add_parser('apply', help='Apply a preset (or add a dirt / dust overlay) to objects in the opened .blend')
    apply.add_argument('--preset', required=True)
    apply.add_argument('--overlay', default='', help='Dirt / dust overlay presets to layer on top, comma separated')
    apply.add_argument('--objects', required=True, help='Comma separated object names, or "selected"/"all"')
    apply.add_argument('--no-fit', action='store_true', help='Do not fit the pattern size to the objects')
    apply.add_argument('--save', action='store_true', help='Save the .blend file afterwards')

    bake = sub.add_parser('bake', help='Bake objects of the opened .blend to textures (keeps their UVs)')
    bake.add_argument('--objects', default='selected', help='Comma separated names, or "selected"/"active"/"all"')
    bake.add_argument('--keep-material', action='store_true',
                      help='Do not switch the objects to the baked material')
    bake.add_argument('--save', action='store_true', help='Save the .blend file afterwards')
    bake_options(bake)

    auto = sub.add_parser('auto', help='Auto Texture: new UVs (Smart UV Project + Pack Islands), bake, save '
                                       'and apply the textures')
    auto.add_argument('--objects', default='all', help='Comma separated names, or "selected"/"active"/"all" '
                                                       '(default: all meshes)')
    auto.add_argument('--save', action='store_true', help='Save the .blend file afterwards')
    bake_options(auto)
    return parser


def _objects(spec):
    if spec == 'all':
        return [o for o in bpy.context.view_layer.objects if o.type == 'MESH']
    if spec == 'selected':
        return [o for o in bpy.context.view_layer.objects if o.select_get()]
    if spec == 'active':
        active = bpy.context.view_layer.objects.active
        return [active] if active is not None else []
    objs = []
    for name in (n.strip() for n in spec.split(',') if n.strip()):
        obj = bpy.data.objects.get(name)
        if obj is None:
            raise SystemExit('No object called "%s" in this file.' % name)
        objs.append(obj)
    return objs


def _presets(spec, overlays=False):
    """Material presets (or overlay presets with `overlays`) named in `spec`."""
    if spec.strip().lower() == 'all':
        return [p for p in P.PRESETS if P.is_overlay(p) == overlays]
    found = []
    for name in (n.strip() for n in spec.split(',') if n.strip()):
        preset = P.find(name)
        if preset is None:
            raise SystemExit('Unknown preset "%s". Run the "list" command to see all names.' % name)
        found.append(preset)
    return found


def _add_overlays(mat, spec, objects=()):
    for preset in _presets(spec, overlays=True) if spec else ():
        if not P.is_overlay(preset):
            raise SystemExit('"%s" is a material, not a dirt / dust overlay.' % preset['name'])
        try:
            node = L.add_overlay(mat, preset['generator'], L.preset_values(preset))
        except L.OverlayError as exc:
            raise SystemExit('BPM error: %s' % exc)
        node.label = preset['name']
        if objects:
            node.inputs['Scale'].default_value *= L.fit_scale(objects, preset['generator'])


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
    print('BPM: %s' % job.summary())


def main(argv=None):
    if argv is None:
        argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    args = _parser().parse_args(argv)

    if args.command == 'list':
        for category, label, *_ in P.CATEGORIES:
            print('\n%s:' % label)
            for p in P.by_category(category):
                print('  %-28s %s' % (p['id'], p['name']))
        return

    if args.command == 'tile':
        mats = []
        for preset in _presets(args.preset):
            if P.is_overlay(preset):
                raise SystemExit('"%s" is a dirt / dust overlay: put it on a material with --overlay.'
                                 % preset['name'])
            mat = L.create_material(preset['id'])
            _add_overlays(mat, args.overlay)
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
        if P.is_overlay(preset):
            mats = []
            for obj in objs:
                B.restore_procedural(obj)
                if obj.active_material is None:
                    mat = bpy.data.materials.new('Material')
                    L.ensure_node_tree(mat)
                    L.assign_material(obj, mat)
                if obj.active_material not in mats:
                    mats.append(obj.active_material)
            for mat in mats:
                _add_overlays(mat, preset['id'], [] if args.no_fit else objs)
                _add_overlays(mat, args.overlay, [] if args.no_fit else objs)
        else:
            mat = L.create_material(preset['id'])
            if not args.no_fit:
                node = L.find_bpm_node(mat)
                node.inputs['Scale'].default_value *= L.fit_scale(objs, preset['generator'])
            _add_overlays(mat, args.overlay, [] if args.no_fit else objs)
            for obj in objs:
                B.restore_procedural(obj)
                L.assign_material(obj, mat)
        print('BPM: applied "%s" to %s' % (preset['name'], ', '.join(o.name for o in objs)))
        if args.save:
            bpy.ops.wm.save_mainfile()
        return

    if args.command in {'bake', 'auto'}:
        objs = _objects(args.objects)
        if args.command == 'auto':
            settings = _settings(args, force_new_uv=True, assign_baked=True)
        else:
            settings = _settings(args, assign_baked=not args.keep_material)
        job = B.ObjectBakeJob(bpy.context, objs, settings)
        try:
            B.run_to_end(job)
        except B.BakeError as exc:
            raise SystemExit('BPM error: %s' % exc)
        _print_messages(job)
        if args.save:
            if not bpy.data.filepath:
                raise SystemExit('Cannot --save: open a .blend file first.')
            bpy.ops.wm.save_mainfile()
