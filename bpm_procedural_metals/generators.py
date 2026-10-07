# SPDX-License-Identifier: GPL-3.0-or-later
"""Registry of all generators.

Each generator (one module per material family) builds one shader node group.
All user-facing settings are inputs of that group, so they can be tweaked live
(from the BPM sidebar, the material properties or the node editor) without
recompiling anything.

Material generators output PBR channels for a Principled BSDF.  Overlay
generators take those channels as inputs and put dirt, dust... on top, so they
can be stacked on any material.
"""

from . import mat_fabric, mat_leather, mat_metal, mat_organic, mat_paint, mat_plastic, mat_wood, overlays
from .gencommon import MACRO_BUMP, MICRO_BUMP, TILE_PARAM  # noqa: F401  (used by bake.py / tests)
from .nodebuilder import Builder, auto_layout, create_group

GENERATOR_VERSION = 1

GENERATORS = {}


def _register(key, spec):
    spec = dict(spec)
    spec.setdefault('kind', 'material')
    spec.setdefault('links', {})
    spec.setdefault('bsdf', {})
    spec.setdefault('version', GENERATOR_VERSION)
    spec.setdefault('fit', 0.75)  # how strongly "Fit Pattern Size to Object" adapts the scale
    spec.setdefault('bump', MACRO_BUMP)  # relief depth of the 0..1 height range (meters at Scale 1)
    GENERATORS[key] = spec


_register('METAL', mat_metal.SPEC)
_register('PAINT', mat_paint.SPEC)
_register('WOOD', mat_wood.SPEC)
_register('PLASTIC', mat_plastic.SPEC)
_register('LEATHER', mat_leather.SPEC)
_register('FABRIC', mat_fabric.SPEC)
_register('ORGANIC', mat_organic.SPEC)
_register('DIRT', overlays.DIRT_SPEC)
_register('DUST', overlays.DUST_SPEC)


def is_overlay(generator):
    return GENERATORS.get(generator, {}).get('kind') == 'overlay'


def material_generators():
    return [key for key, spec in GENERATORS.items() if spec['kind'] == 'material']


def overlay_generators():
    return [key for key, spec in GENERATORS.items() if spec['kind'] == 'overlay']


def params_for(generator, tile=False):
    params = list(GENERATORS[generator]['params'])
    if tile:
        params.append(TILE_PARAM)
    return params


def build_group(generator, tile=False):
    """Build a fresh node group for `generator` and return it."""
    spec = GENERATORS[generator]
    params = params_for(generator, tile)
    name = 'BPM {}{}'.format(spec['label'], ' (Tileable)' if tile else '')
    tree, gin, gout = create_group(name, params, spec['outputs'])
    b = Builder(tree)
    inputs = {p.name: gin.outputs[p.name] for p in params}
    spec['build'](b, inputs, gout, tile)
    _prune(tree, gout)
    auto_layout(tree)
    tree['bpm_generator'] = generator
    tree['bpm_tile'] = bool(tile)
    tree['bpm_version'] = spec['version']
    return tree


def _prune(tree, gout):
    """Remove nodes that do not contribute to any output (keeps groups lean)."""
    keep = {gout}
    stack = [gout]
    feeders = {}
    for link in tree.links:
        feeders.setdefault(link.to_node, []).append(link.from_node)
    while stack:
        node = stack.pop()
        for src in feeders.get(node, ()):
            if src not in keep:
                keep.add(src)
                stack.append(src)
    for node in list(tree.nodes):
        if node not in keep and node.bl_idname not in {'NodeGroupInput', 'NodeGroupOutput'}:
            tree.nodes.remove(node)
