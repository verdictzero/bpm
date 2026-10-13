# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared parts of all generators: the slider description class, common sliders,
outputs and helpers."""

from . import features as F
from .nodebuilder import is_socket


class Param:
    __slots__ = ('name', 'kind', 'default', 'min', 'max', 'panel', 'desc', 'subtype', 'ui', 'key')

    def __init__(self, name, kind, default, min=0.0, max=1.0, panel='', desc='', subtype=None,
                 ui=None, key=False):
        self.name = name
        self.kind = kind
        self.default = default
        self.min = min
        self.max = max
        self.panel = panel
        self.desc = desc
        self.subtype = subtype
        self.ui = ui
        self.key = key


def fac(name, default, panel, desc, key=False):
    return Param(name, 'FLOAT', default, 0.0, 1.0, panel, desc, 'FACTOR', key=key)


def scale(name, default, lo, hi, panel, desc, key=False):
    return Param(name, 'FLOAT', default, lo, hi, panel, desc, key=key)


def color(name, default, panel, desc, key=False):
    return Param(name, 'COLOR', default, panel=panel, desc=desc, key=key)


def axis(name, default, panel, desc):
    return Param(name, 'VECTOR', default, -1.0, 1.0, panel, desc, ui='AXIS')


STEEL = (0.56, 0.57, 0.58)
RUST_A = (0.22, 0.068, 0.020)
RUST_B = (0.055, 0.020, 0.008)
DIRT = (0.040, 0.033, 0.024)

PATTERN_PARAMS = [
    Param('Scale', 'FLOAT', 1.0, 0.01, 100.0, 'Pattern',
          'Overall size of every pattern. Higher = smaller, denser details', key=True),
    Param('Seed', 'FLOAT', 0.0, 0.0, 100.0, 'Pattern',
          'Change to get a different random variation of the same material', key=True),
    Param('Bump Strength', 'FLOAT', 1.0, 0.0, 3.0, 'Pattern',
          'Strength of all surface relief (dents, scratches, chips)'),
]

TILE_PARAM = Param('Tile Size', 'FLOAT', 1.0, 0.01, 100.0, 'Pattern',
                   'Real-world size covered by one seamless tile', subtype='DISTANCE')

COMMON_OUTPUTS = [
    ('Base Color', 'COLOR'),
    ('Metallic', 'FLOAT'),
    ('Roughness', 'FLOAT'),
    ('Normal', 'VECTOR'),
    ('Height', 'FLOAT'),
]

# Generators with real displacement: the Displacement output (meters) drives the material's
# Displacement node (library.py).  It is 0 until 'Real Displacement' is turned up.
DISPLACE_OUTPUTS = [('Displacement', 'FLOAT')]
DISPLACE_PARAM = fac('Real Displacement', 0.0, 'Displacement',
                     'Moves the surface itself by the height (craters get real depth and silhouettes). '
                     'Needs a finely divided mesh: use "Displace Geometry" in the BPM panel')
EMISSION_OUTPUTS = [('Emission', 'COLOR'), ('Emission Strength', 'FLOAT')]

# Bump distances in meters at Scale = 1 (divided by Scale so the look stays constant).
MACRO_BUMP = 0.012
MICRO_BUMP = 0.0015
BRUSH_STRETCH = 100.0


def bump_distance(b, scale, distance=MACRO_BUMP):
    """World-space bump distance used for the Height output (also used when baking tiles)."""
    return b.div(distance, scale)


def dirt_mask(b, S, amount, cav, edge, offset, extra=0.0, spots=0.5):
    """Soft grime on open surfaces plus heavier dirt packed into crevices.

    `spots` controls how much dirty spots also appear on open surfaces.
    """
    dz = S.znoise(2.5, offset, detail=6.0, roughness=0.6, label='Dirt')
    grime = b.mul(b.smoothstep(-1.5, 2.5, dz), b.mul(amount, 0.3))
    if is_socket(cav):
        packed_z = b.madd(dz, spots, b.madd(cav, 3.0, b.mul(edge, -1.5)))
        packed = b.mul(F.cover(b, packed_z, b.mul(amount, 0.35), 0.5), 0.9)
        grime = b.maximum(grime, packed)
    return b.clamp01(b.add(grime, b.mul(extra, amount)))


def finish(b, gout, inputs, color, metallic, rough, h_macro, h_micro, extra=None, distance=MACRO_BUMP,
           cover=None, displace=None):
    """Shared tail: normals from height, clamp and connect the group outputs.

    `distance` is the relief depth (meters at Scale 1) of the full 0..1 height
    range; it must match the generator's 'bump' entry (used for tile normals).
    `cover` is an optional (mask, level) of a soft layer on top, like mud: it
    hides the relief below where `mask` is 1 and lies at `level` in the Height
    output.  It is not part of the bump, which keeps Cycles' shader stack small.
    `displace` (0..1, generators with a Displacement output) is the part of the
    big relief (h_macro) that moves the surface itself (real displacement); it
    leaves the bump, so the slopes aren't shaded twice.  Height stays complete.
    """
    # One bump node for everything: two chained ones make Cycles' shader stack overflow.
    height = b.clamp01(b.madd(h_micro, MICRO_BUMP / distance, h_macro))
    world = bump_distance(b, inputs['Scale'], distance)
    bumped = height
    if displace is not None:
        relief = b.sub(b.clamp01(h_macro), 0.5)
        bumped = b.sub(height, b.mul(relief, b.clamp01(displace)))
        b.feed(gout.inputs['Displacement'], b.mul(b.mul(relief, displace), world))
    normal = b.bump(bumped, strength=inputs['Bump Strength'], distance=world, label='Bump')
    if cover is not None:
        mask, level = cover
        normal = b.vmath('NORMALIZE', b.mix_vector(mask, normal, b.geometry().outputs['Normal']))
        height = b.clamp01(b.mix(mask, height, level))
    b.feed(gout.inputs['Base Color'], color)
    b.feed(gout.inputs['Metallic'], b.clamp01(metallic))
    b.feed(gout.inputs['Roughness'], b.clamp01(rough))
    b.feed(gout.inputs['Normal'], normal)
    b.feed(gout.inputs['Height'], height)
    for name, value in (extra or {}).items():
        b.feed(gout.inputs[name], value)
