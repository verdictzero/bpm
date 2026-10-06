# SPDX-License-Identifier: GPL-3.0-or-later
"""The two material generators: bare metal and painted metal.

Each generator builds one shader node group.  All user-facing settings are
inputs of that group, so they can be tweaked live (from the BPM sidebar, the
material properties or the node editor) without recompiling anything.
"""

from . import features as F
from .nodebuilder import Builder, auto_layout, create_group, is_socket

GENERATOR_VERSION = 1


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


def _fac(name, default, panel, desc, key=False):
    return Param(name, 'FLOAT', default, 0.0, 1.0, panel, desc, 'FACTOR', key=key)


def _scale(name, default, lo, hi, panel, desc):
    return Param(name, 'FLOAT', default, lo, hi, panel, desc)


def _color(name, default, panel, desc, key=False):
    return Param(name, 'COLOR', default, panel=panel, desc=desc, key=key)


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

METAL_PARAMS = [
    # -- Base
    _color('Metal Color', STEEL, 'Base', 'Reflection color of the metal', key=True),
    _fac('Roughness', 0.25, 'Base', 'How blurry reflections are: 0 = mirror, 1 = matte', key=True),
    _fac('Roughness Variation', 0.3, 'Base', 'Uneven, blotchy glossiness'),
    _fac('Color Variation', 0.15, 'Base', 'Subtle uneven brightness of the metal'),
    _scale('Variation Scale', 2.0, 0.05, 100.0, 'Base', 'Size of the blotches (higher = smaller)'),
    # -- Finish
    _fac('Brushed', 0.0, 'Finish', 'Fine parallel brush lines (brushed steel / aluminium)', key=True),
    _scale('Brush Scale', 150.0, 1.0, 2000.0, 'Finish', 'Fineness of the brush lines'),
    Param('Brush Direction', 'VECTOR', (1.0, 0.0, 0.0), -1.0, 1.0, 'Finish',
          'Direction of the brush lines (object axes)', ui='AXIS'),
    _fac('Hammered', 0.0, 'Finish', 'Hand-hammered dents'),
    _scale('Hammer Scale', 8.0, 0.5, 200.0, 'Finish', 'Dent density (higher = smaller dents)'),
    _fac('Grain', 0.0, 'Finish', 'Sandblasted / cast micro texture'),
    _fac('Pitting', 0.0, 'Finish', 'Small pits and pores (cast iron, corrosion pits)'),
    _scale('Pit Scale', 150.0, 5.0, 5000.0, 'Finish', 'Density of grain and pits'),
    _fac('Spangle', 0.0, 'Finish', 'Crystal flake pattern of hot-dip galvanized steel'),
    _scale('Spangle Scale', 12.0, 1.0, 500.0, 'Finish', 'Density of the crystal flakes'),
    _fac('Heat Tint', 0.0, 'Finish', 'Rainbow temper colors of heated steel / titanium'),
    _scale('Heat Tint Scale', 0.5, 0.05, 50.0, 'Finish', 'Size of the heat color bands'),
    # -- Wear
    _fac('Scratches', 0.2, 'Wear', 'How many scratches', key=True),
    _scale('Scratch Scale', 1.0, 0.05, 20.0, 'Wear', 'Scratch size (higher = smaller, denser)'),
    _fac('Smudges', 0.0, 'Wear', 'Fingerprints and greasy smudges'),
    _fac('Edge Polish', 0.0, 'Wear',
         'Edges worn to bare shiny metal (visible in Cycles and in baked textures)'),
    _color('Edge Color', (0.62, 0.62, 0.62), 'Wear', 'Color of the worn edges'),
    Param('Edge Width', 'FLOAT', 0.035, 0.001, 0.3, 'Wear', 'Width of edge wear', subtype='DISTANCE'),
    # -- Aging
    _fac('Tarnish', 0.0, 'Aging', 'Dark oxidation film (silver, brass, copper); heavier in crevices'),
    _color('Tarnish Color', (0.30, 0.22, 0.12), 'Aging', 'Tint of the tarnish'),
    _scale('Tarnish Scale', 3.0, 0.05, 100.0, 'Aging', 'Size of tarnish patches'),
    _fac('Rust', 0.0, 'Aging', 'Share of the surface covered in rust or patina', key=True),
    _color('Rust Color', RUST_A, 'Aging', 'Bright rust / patina color'),
    _color('Rust Color 2', RUST_B, 'Aging', 'Dark rust / patina color'),
    _scale('Rust Scale', 3.0, 0.05, 100.0, 'Aging', 'Size of rust patches'),
    _fac('Dirt', 0.0, 'Aging', 'Grime in crevices (crevices need Cycles or baking)', key=True),
    _color('Dirt Color', DIRT, 'Aging', 'Color of the grime'),
] + PATTERN_PARAMS

PAINT_PARAMS = [
    # -- Paint
    _color('Paint Color', (0.80, 0.42, 0.02), 'Paint', 'Main paint color', key=True),
    _fac('Paint Roughness', 0.4, 'Paint', '0 = glossy, 1 = flat matte', key=True),
    _fac('Paint Metallic', 0.0, 'Paint', 'Metallic paint (car paint, hammertone)'),
    _fac('Paint Variation', 0.2, 'Paint', 'Uneven, blotchy paint'),
    _scale('Variation Scale', 2.0, 0.05, 100.0, 'Paint', 'Size of the blotches'),
    _fac('Orange Peel', 0.15, 'Paint', 'Fine bumpy texture of sprayed paint'),
    _fac('Flakes', 0.0, 'Paint', 'Sparkly metallic flakes'),
    _fac('Hammered', 0.0, 'Paint', 'Hammertone paint dimples'),
    _scale('Hammer Scale', 30.0, 0.5, 300.0, 'Paint', 'Dimple density'),
    _fac('Clear Coat', 0.0, 'Paint', 'Glossy varnish layer on top (render only, not baked)'),
    _fac('Fading', 0.0, 'Paint', 'Sun-bleached, chalky old paint'),
    # -- Stripes
    _fac('Stripes', 0.0, 'Stripes', 'Hazard-style stripes in a second color'),
    _color('Stripe Color', (0.02, 0.02, 0.02), 'Stripes', 'Color of the stripes'),
    Param('Stripe Width', 'FLOAT', 0.12, 0.005, 10.0, 'Stripes', 'Width of each stripe', subtype='DISTANCE'),
    Param('Stripe Direction', 'VECTOR', (0.7071, 0.0, 0.7071), -1.0, 1.0, 'Stripes',
          'Direction across the stripes (object axes)'),
    # -- Wear
    _fac('Wear', 0.04, 'Wear', 'Share of the paint chipped off all over (0.1 = 10%)', key=True),
    _fac('Edge Wear', 0.6, 'Wear',
         'Paint chipped off on edges (visible in Cycles and in baked textures)', key=True),
    Param('Edge Width', 'FLOAT', 0.035, 0.001, 0.3, 'Wear', 'Width of edge wear', subtype='DISTANCE'),
    _scale('Chip Scale', 5.0, 0.05, 100.0, 'Wear', 'Chip size (higher = smaller chips)'),
    _fac('Chip Detail', 0.6, 'Wear', 'Ragged, detailed chip borders'),
    _fac('Primer', 0.4, 'Wear', 'Visible primer layer around chips'),
    _color('Primer Color', (0.32, 0.32, 0.30), 'Wear', 'Color of the primer'),
    _fac('Paint Thickness', 0.5, 'Wear', 'Depth of chip edges'),
    _fac('Scratches', 0.2, 'Wear', 'Scratches through the paint', key=True),
    _scale('Scratch Scale', 1.0, 0.05, 20.0, 'Wear', 'Scratch size (higher = smaller, denser)'),
    # -- Metal
    _color('Metal Color', STEEL, 'Metal Underneath', 'Bare metal under the paint'),
    _fac('Metal Roughness', 0.35, 'Metal Underneath', 'Glossiness of the bare metal'),
    # -- Aging
    _fac('Rust', 0.3, 'Aging', 'How much of the bare metal (chips, scratches) has rusted', key=True),
    _fac('Rust Spread', 0.3, 'Aging', 'Rust creeping under the paint and rust spots'),
    _fac('Rust Streaks', 0.0, 'Aging', 'Rust running down the paint (along object Z)'),
    _color('Rust Color', RUST_A, 'Aging', 'Bright rust color'),
    _color('Rust Color 2', RUST_B, 'Aging', 'Dark rust color'),
    _scale('Rust Scale', 4.0, 0.05, 100.0, 'Aging', 'Size of rust patches'),
    _fac('Dirt', 0.2, 'Aging', 'Grime in crevices (crevices need Cycles or baking)', key=True),
    _color('Dirt Color', DIRT, 'Aging', 'Color of the grime'),
] + PATTERN_PARAMS

COMMON_OUTPUTS = [
    ('Base Color', 'COLOR'),
    ('Metallic', 'FLOAT'),
    ('Roughness', 'FLOAT'),
    ('Normal', 'VECTOR'),
    ('Height', 'FLOAT'),
]
METAL_OUTPUTS = COMMON_OUTPUTS + [('Anisotropic', 'FLOAT'), ('Tangent', 'VECTOR')]
PAINT_OUTPUTS = COMMON_OUTPUTS + [('Coat', 'FLOAT')]

HEAT_STOPS = [
    (0.00, (0.75, 0.60, 0.35)),   # straw
    (0.22, (0.55, 0.33, 0.15)),   # bronze
    (0.42, (0.32, 0.13, 0.30)),   # purple
    (0.60, (0.12, 0.16, 0.42)),   # deep blue
    (0.80, (0.32, 0.45, 0.60)),   # light blue
    (1.00, (0.60, 0.60, 0.62)),   # grey
]

# Bump distances in meters at Scale = 1 (divided by Scale so the look stays constant).
MACRO_BUMP = 0.012
MICRO_BUMP = 0.0015
BRUSH_STRETCH = 100.0


def bump_distance(b, scale):
    """World-space bump distance used for the Height output (also used when baking tiles)."""
    return b.div(MACRO_BUMP, scale)


def dirt_mask(b, S, amount, cav, edge, offset, extra=0.0):
    """Soft grime on open surfaces plus heavier dirt packed into crevices."""
    dz = S.znoise(2.5, offset, detail=6.0, roughness=0.6, label='Dirt')
    grime = b.mul(b.smoothstep(-1.5, 2.5, dz), b.mul(amount, 0.3))
    if is_socket(cav):
        packed_z = b.madd(dz, 0.5, b.madd(cav, 3.0, b.mul(edge, -1.5)))
        packed = b.mul(F.cover(b, packed_z, b.mul(amount, 0.35), 0.5), 0.9)
        grime = b.maximum(grime, packed)
    return b.clamp01(b.add(grime, b.mul(extra, amount)))


def _finish(b, gout, inputs, color, metallic, rough, h_macro, h_micro, extra=None):
    """Shared tail: normals from height, clamp and connect the group outputs."""
    # One bump node for everything: two chained ones make Cycles' shader stack overflow.
    height = b.clamp01(b.madd(h_micro, MICRO_BUMP / MACRO_BUMP, h_macro))
    normal = b.bump(height, strength=inputs['Bump Strength'], distance=bump_distance(b, inputs['Scale']),
                    label='Bump')
    b.feed(gout.inputs['Base Color'], color)
    b.feed(gout.inputs['Metallic'], b.clamp01(metallic))
    b.feed(gout.inputs['Roughness'], b.clamp01(rough))
    b.feed(gout.inputs['Normal'], normal)
    b.feed(gout.inputs['Height'], height)
    for name, value in (extra or {}).items():
        b.feed(gout.inputs[name], value)


# ----------------------------------------------------------------- metal
def build_metal(b, I, gout, tile):
    S = F.Space(b, tile, I['Scale'], I['Seed'], I['Tile Size'] if tile else 1.0)
    inv = b.div(1.0, I['Scale'])
    edge = F.edge_mask(b, S, b.mul(I['Edge Width'], inv))
    cav = F.cavity_mask(b, S, b.mul(inv, 0.3))
    has_geo = is_socket(edge)

    # base variation (z = standard deviations)
    zv1 = S.znoise(I['Variation Scale'], 1, detail=3.0, roughness=0.55, label='Color Variation')
    zv2 = S.znoise(b.mul(I['Variation Scale'], 3.1), 2, detail=4.0, roughness=0.6, label='Roughness Variation')
    color = b.color_scale(I['Metal Color'], b.madd(zv1, b.mul(I['Color Variation'], 0.12), 1.0))
    rough = b.madd(zv2, b.mul(I['Roughness Variation'], 0.07), I['Roughness'])

    # heat tint
    hz = S.znoise(I['Heat Tint Scale'], 3, detail=1.5, roughness=0.45, distortion=0.6, label='Heat Tint')
    heat = b.ramp(b.linstep(-2.2, 2.2, hz), HEAT_STOPS, label='Temper Colors')
    color = b.mix_color(I['Heat Tint'], color, heat)

    # brushed lines
    stretch = 1.0 / BRUSH_STRETCH
    if tile:
        dx, dy, dz = b.separate(I['Brush Direction'])
        horiz = b.math('GREATER_THAN', b.absolute(dx), b.maximum(b.absolute(dy), b.absolute(dz)))
        aniso = (b.mix(horiz, 1.0, stretch), b.mix(horiz, stretch, 1.0))
        base = None
        brush_dir = None
    else:
        base, brush_dir = F.stretched_base(b, S, I['Brush Direction'], BRUSH_STRETCH)
        aniso = None
    bz1 = S.znoise(I['Brush Scale'], 4, detail=3.0, roughness=0.6, aniso=aniso, base=base, label='Brush Lines')
    bz2 = S.znoise(b.mul(I['Brush Scale'], 0.15), 5, detail=3.0, roughness=0.5, aniso=aniso, base=base,
                   label='Brush Variation')
    streak = b.mul(b.madd(bz1, 0.75, b.mul(bz2, 0.35)), I['Brushed'])
    rough = b.madd(streak, 0.035, rough)
    color = b.color_scale(color, b.madd(streak, 0.025, 1.0))
    h_micro = b.mul(streak, 0.2)

    # hammered dents
    hv = S.voronoi(I['Hammer Scale'], 6, feature='SMOOTH_F1', smoothness=0.25, label='Hammer Dents')
    dent = b.smoothstep(0.0, 0.75, hv.outputs['Distance'])
    hammered = I['Hammered']
    color = b.color_scale(color, b.madd(b.sub(dent, 0.5), b.mul(hammered, 0.15), 1.0))
    rough = b.madd(b.sub(0.5, dent), b.mul(hammered, 0.08), rough)
    h_macro = b.madd(b.sub(dent, 0.5), b.mul(hammered, 0.8), 0.5)

    # grain and pits
    gz = S.znoise(b.mul(I['Pit Scale'], 2.5), 7, detail=1.5, roughness=0.5, label='Grain')
    pz = S.znoise(I['Pit Scale'], 8, detail=2.0, roughness=0.55, label='Pits')
    pits = F.cover(b, pz, b.mul(I['Pitting'], 0.2), 0.2)
    color = b.color_scale(color, b.madd(pits, -0.5, 1.0))
    rough = b.madd(pits, 0.25, rough)
    h_macro = b.madd(pits, -0.5, h_macro)
    h_micro = b.add(h_micro, b.add(b.mul(gz, b.mul(I['Grain'], 0.08)), b.mul(pz, b.mul(I['Pitting'], 0.03))))
    rough = b.madd(I['Grain'], 0.05, rough)

    # galvanized spangle
    sv = S.voronoi(I['Spangle Scale'], 9, label='Spangle')
    sr, sg, sb = b.separate_color(sv.outputs['Color'])
    spangle = I['Spangle']
    color = b.color_scale(color, b.madd(b.sub(sr, 0.5), b.mul(spangle, 0.35), 1.0))
    rough = b.madd(b.sub(sg, 0.5), b.mul(spangle, 0.3), rough)
    h_micro = b.madd(b.sub(sb, 0.5), b.mul(spangle, 0.15), h_micro)

    # scratches
    scr = F.scratch_mask(b, S, I['Scratches'], I['Scratch Scale'], 20)
    rough = b.mix(scr, rough, b.mix(0.5, rough, 0.25))
    color = b.color_scale(color, b.madd(scr, 0.2, 1.0))
    h_micro = b.madd(scr, -0.6, h_micro)

    # smudges / fingerprints
    smz = S.znoise(2.5, 10, detail=4.0, roughness=0.55, distortion=0.8, label='Smudges')
    smudge = F.cover(b, smz, b.mul(I['Smudges'], 0.45), 0.6)
    rough = b.madd(smudge, 0.15, rough)
    color = b.color_scale(color, b.madd(smudge, -0.08, 1.0))

    # tarnish
    tz = S.znoise(I['Tarnish Scale'], 11, detail=3.0, roughness=0.55, distortion=0.4, label='Tarnish')
    film = b.madd(b.smoothstep(-1.8, 1.8, tz), 0.45, 0.55)  # an uneven but continuous film
    if has_geo:
        film = b.madd(cav, 0.6, b.madd(edge, -0.8, film))
    tarnish = b.clamp01(b.mul(film, I['Tarnish']))
    color = b.mix_color(tarnish, color, b.mix_color(1.0, color, I['Tarnish Color'], blend='MULTIPLY'))
    rough = b.madd(tarnish, 0.2, rough)

    # rust / patina
    rz = S.znoise(I['Rust Scale'], 12, detail=8.0, roughness=0.62, distortion=0.25, label='Rust Coverage')
    rz_fine = S.znoise(b.mul(I['Rust Scale'], 9.0), 18, detail=3.0, roughness=0.6, label='Rust Edges')
    rz = b.madd(rz_fine, 0.45, b.mul(rz, 0.9))
    if has_geo:
        rz = b.madd(cav, 2.0, b.madd(edge, 0.6, rz))
    rust = F.cover(b, rz, I['Rust'], 0.12)
    halo = b.mul(F.cover(b, rz, I['Rust'], 0.45, bias=-0.45), b.one_minus(rust))
    rust_col, rust_rough, rust_h = F.rust_layer(b, S, I['Rust Scale'], I['Rust Color'], I['Rust Color 2'], 13)
    color = b.mix_color(b.mul(halo, 0.6), color, b.mix_color(1.0, color, (0.42, 0.33, 0.26), blend='MULTIPLY'))
    rough = b.madd(halo, 0.15, rough)
    color = b.mix_color(rust, color, rust_col)
    metallic = b.one_minus(rust)
    rough = b.mix(rust, rough, rust_rough)
    h_macro = b.add(h_macro, b.mul(rust, b.madd(rust_h, 0.4, 0.05)))

    # worn, polished edges
    edge_w = F.broken(b, S, edge, 15)
    polish = b.mul(edge_w, I['Edge Polish'])
    color = b.mix_color(polish, color, I['Edge Color'])
    metallic = b.mix(polish, metallic, 1.0)
    rough = b.mix(polish, rough, b.mul(rough, 0.4))

    # dirt
    dirt = dirt_mask(b, S, I['Dirt'], cav, edge_w, 16)
    color = b.mix_color(dirt, color, I['Dirt Color'])
    metallic = b.mix(dirt, metallic, 0.0)
    rough = b.mix(dirt, rough, 0.92)
    h_macro = b.madd(dirt, 0.04, h_macro)

    # anisotropic highlights for brushed metal
    geo = b.geometry()
    if tile:
        tangent = geo.outputs['Tangent']
    else:
        world_dir = b.vmath('NORMALIZE', b.vector_transform(brush_dir))
        tangent = b.vmath('NORMALIZE', b.vmath('CROSS_PRODUCT', geo.outputs['Normal'], world_dir))
    _finish(b, gout, I, color, metallic, rough, h_macro, h_micro,
            extra={'Anisotropic': b.mul(I['Brushed'], 0.65), 'Tangent': tangent})


# ----------------------------------------------------------------- paint
def build_paint(b, I, gout, tile):
    S = F.Space(b, tile, I['Scale'], I['Seed'], I['Tile Size'] if tile else 1.0)
    inv = b.div(1.0, I['Scale'])
    edge = F.edge_mask(b, S, b.mul(I['Edge Width'], inv))
    cav = F.cavity_mask(b, S, b.mul(inv, 0.3))
    has_geo = is_socket(edge)

    # paint base
    zp1 = S.znoise(I['Variation Scale'], 1, detail=4.0, roughness=0.55, label='Paint Variation')
    zp2 = S.znoise(b.mul(I['Variation Scale'], 4.3), 2, detail=4.0, roughness=0.55, label='Gloss Variation')
    variation = I['Paint Variation']
    paint = b.color_scale(I['Paint Color'], b.madd(zp1, b.mul(variation, 0.08), 1.0))
    p_rough = b.madd(zp2, b.mul(variation, 0.04), I['Paint Roughness'])

    # stripes
    if tile:
        count = b.maximum(1.0, b.math('ROUND', b.div(b.mul(I['Tile Size'], I['Scale']),
                                                      b.mul(I['Stripe Width'], 2.0))))
        x = b.mul(b.add(S.u, S.v), count)
    else:
        x = b.div(b.vmath('DOT_PRODUCT', S.P, b.vmath('NORMALIZE', I['Stripe Direction'])),
                  b.mul(I['Stripe Width'], 2.0))
    tri = b.mul(b.absolute(b.sub(b.math('FRACT', x), 0.5)), 2.0)
    stripe = b.smoothstep(0.47, 0.53, tri)
    paint = b.mix_color(b.mul(stripe, I['Stripes']), paint, I['Stripe Color'])

    # hammertone dimples
    hv = S.voronoi(I['Hammer Scale'], 3, feature='SMOOTH_F1', smoothness=0.3, label='Hammertone')
    dent = b.smoothstep(0.0, 0.75, hv.outputs['Distance'])
    hammered = I['Hammered']
    paint = b.color_scale(paint, b.madd(b.sub(dent, 0.5), b.mul(hammered, 0.6), 1.0))

    # sun fading
    fz = S.znoise(1.2, 4, detail=3.0, roughness=0.5, label='Fading')
    fade = b.clamp01(b.mul(I['Fading'], b.madd(fz, 0.25, 0.8)))
    faded = b.mix_color(0.2, b.hsv(paint, saturation=0.5, value=1.5), (0.5, 0.5, 0.48))
    paint = b.mix_color(fade, paint, faded)
    p_rough = b.madd(fade, 0.35, p_rough)

    # chips: z-field = noise + edges - cavities, thresholded by Wear
    detail = b.madd(I['Chip Detail'], 8.0, 2.0)
    cz = S.znoise(I['Chip Scale'], 5, detail=detail, roughness=b.madd(I['Chip Detail'], 0.25, 0.45),
                  label='Chips')
    clz = S.znoise(b.mul(I['Chip Scale'], 0.18), 6, detail=2.0, label='Chip Clusters')
    field = b.madd(clz, 0.5, b.mul(cz, 0.85))
    if has_geo:
        field = b.madd(edge, b.mul(I['Edge Wear'], 3.5), field)
        field = b.madd(cav, -1.0, field)
    threshold = F.amount_to_z(b, b.maximum(I['Wear'], 0.002))
    chip_gate = b.clamp01(b.mul(b.add(I['Wear'], I['Edge Wear']), 25.0))
    metal = b.mul(b.smoothstep(threshold, b.add(threshold, 0.15), field), chip_gate)
    primer_t = b.sub(threshold, b.mul(I['Primer'], 0.7))
    primer = b.mul(b.smoothstep(primer_t, b.add(primer_t, 0.15), field), chip_gate)
    scr = F.scratch_mask(b, S, I['Scratches'], I['Scratch Scale'], 20)
    metal = b.maximum(metal, b.smoothstep(0.35, 0.6, scr))
    primer = b.maximum(primer, b.smoothstep(0.1, 0.35, scr))

    # bare metal underneath
    zm = S.znoise(b.mul(I['Variation Scale'], 2.0), 8, detail=4.0, label='Metal Variation')
    m_col = b.color_scale(I['Metal Color'], b.madd(zm, 0.06, 1.0))
    m_rough = b.madd(zm, 0.04, I['Metal Roughness'])

    # rust
    rust_amt = I['Rust']
    rz = S.znoise(I['Rust Scale'], 9, detail=7.0, roughness=0.6, label='Rust')
    rust_chip = b.mul(metal, F.cover(b, rz, rust_amt, 0.3))
    spread = b.madd(I['Rust Spread'], 1.2, 0.01)
    halo = b.smoothstep(b.sub(threshold, spread), threshold, field)
    halo = b.mul(b.mul(halo, b.one_minus(primer)), b.mul(F.cover(b, rz, 0.6, 0.6, gate=False), rust_amt))
    sz = S.znoise(b.mul(I['Rust Scale'], 2.5), 10, detail=5.0, label='Rust Spots')
    spots = F.cover(b, sz, b.mul(b.mul(rust_amt, I['Rust Spread']), 0.12), 0.15)
    rust = b.maximum(rust_chip, spots)
    rust_col, rust_rough, rust_h = F.rust_layer(b, S, I['Rust Scale'], I['Rust Color'], I['Rust Color 2'], 11)

    # rust streaks running down
    aniso = (1.0, 1.0 / 14.0) if tile else (1.0, 1.0, 1.0 / 14.0)
    stz = S.znoise(4.0, 13, detail=4.0, roughness=0.6, aniso=aniso, label='Rust Streaks')
    smz = S.znoise(0.8, 14, detail=2.0, label='Streak Mask')
    streak = b.mul(F.cover(b, stz, b.mul(I['Rust Streaks'], 0.4), 0.5),
                   F.cover(b, smz, 0.6, 0.8, gate=False))
    streak_col = b.mix_color(0.35, I['Rust Color 2'], I['Rust Color'])

    # dirt
    dirt = dirt_mask(b, S, I['Dirt'], cav, edge, 15, extra=b.mul(metal, 0.3))

    # compose the layers
    color = b.mix_color(primer, paint, I['Primer Color'])
    color = b.mix_color(metal, color, m_col)
    color = b.mix_color(b.mul(halo, 0.75), color, b.color_scale(I['Rust Color 2'], 1.3))
    color = b.mix_color(rust, color, rust_col)
    color = b.mix_color(b.mul(streak, 0.6), color, streak_col)
    color = b.mix_color(dirt, color, I['Dirt Color'])

    metallic = b.mix(primer, I['Paint Metallic'], 0.0)
    metallic = b.mix(metal, metallic, 1.0)
    metallic = b.mix(b.maximum(rust, dirt), metallic, 0.0)

    rough = b.mix(primer, p_rough, 0.6)
    rough = b.mix(metal, rough, m_rough)
    rough = b.madd(halo, 0.2, rough)
    rough = b.mix(rust, rough, rust_rough)
    rough = b.madd(streak, 0.15, rough)
    rough = b.mix(dirt, rough, 0.92)

    paint_mask = b.one_minus(primer)
    coat = b.mul(b.mul(I['Clear Coat'], paint_mask), b.one_minus(dirt))

    # relief
    layers = b.sub(b.madd(primer, -0.45, 1.0), b.mul(metal, 0.55))
    h_macro = b.madd(b.sub(layers, 0.5), I['Paint Thickness'], 0.5)
    h_macro = b.add(h_macro, b.mul(rust, b.madd(rust_h, 0.3, 0.0)))
    h_macro = b.madd(spots, 0.15, h_macro)
    h_macro = b.madd(b.mul(b.sub(dent, 0.5), hammered), b.mul(paint_mask, 0.5), h_macro)
    opz = S.znoise(220.0, 16, detail=2.0, roughness=0.4, label='Orange Peel')
    fv = S.voronoi(3000.0, 17, label='Flakes')
    h_micro = b.mul(b.mul(opz, b.mul(I['Orange Peel'], 0.05)), paint_mask)
    h_micro = b.madd(b.mul(b.sub(fv.outputs['Distance'], 0.5), I['Flakes']), b.mul(paint_mask, 0.6), h_micro)
    h_micro = b.madd(scr, -0.6, h_micro)

    _finish(b, gout, I, color, metallic, rough, h_macro, h_micro, extra={'Coat': coat})


GENERATORS = {
    'METAL': dict(label='Bare Metal', params=METAL_PARAMS, outputs=METAL_OUTPUTS, build=build_metal),
    'PAINT': dict(label='Painted Metal', params=PAINT_PARAMS, outputs=PAINT_OUTPUTS, build=build_paint),
}


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
    tree['bpm_version'] = GENERATOR_VERSION
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
