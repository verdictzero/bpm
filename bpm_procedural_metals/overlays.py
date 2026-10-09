# SPDX-License-Identifier: GPL-3.0-or-later
"""Overlay generators: dirt, dust, edge wear and scratches layered on top of
any material.

An overlay node group takes the PBR channels of the material below as inputs
(Base Color, Metallic, Roughness, Normal, Height, Coat, Transmission) and
outputs the same channels with its layer mixed on top.  Dirt and dust are
opaque: on glass they block the view through it.  It is inserted between the
material and its Principled BSDF, so overlays stack, work on non-BPM materials
too and end up in baked textures automatically.

Overlays use no Bump node: one Bump node in an overlay takes about 60 of the
255 slots of Cycles' shader stack (measured), so a stack of overlays would
overflow it.  Their relief goes into the Height output only (displacement,
height maps); in the Normal output they hide ("fill") the relief below where
they cover it, or let it through.

Overlays are switched off with their Opacity input, not by muting the node:
Blender passes muted group nodes through by socket type, which would send
Metallic into Roughness and so on.
"""

from . import features as F
from . import gencommon as C
from .nodebuilder import is_socket

# Channels passed through every overlay, in the order of the group sockets.
CHANNELS = (
    ('Base Color', 'COLOR', (0.5, 0.5, 0.5)),
    ('Metallic', 'FLOAT', 0.0),
    ('Roughness', 'FLOAT', 0.5),
    ('Normal', 'VECTOR', (0.0, 0.0, 0.0)),
    ('Height', 'FLOAT', 0.5),
    ('Coat', 'FLOAT', 0.0),
    ('Transmission', 'FLOAT', 0.0),
)
OVERLAY_VERSION = 3  # 2: Transmission channel (older overlay groups do not have it), 3: mesh maps
OUTPUTS = [(name, kind) for name, kind, _ in CHANNELS]
CHANNEL_NAMES = tuple(name for name, _kind, _default in CHANNELS)
BELOW = 'Material Below'


def _channel_params():
    params = []
    for name, kind, default in CHANNELS:
        desc = 'Connected automatically to the material underneath'
        if kind == 'FLOAT':
            params.append(C.Param(name, 'FLOAT', default, 0.0, 1.0, BELOW, desc))
        else:
            params.append(C.Param(name, kind, default, -1.0, 1.0, BELOW, desc))
    return params


OVERLAY_PATTERN = [
    C.Param('Scale', 'FLOAT', 1.0, 0.01, 100.0, 'Pattern', 'Size of the patterns. Higher = smaller details', key=True),
    C.Param('Seed', 'FLOAT', 0.0, 0.0, 100.0, 'Pattern', 'Change for a different random variation', key=True),
]

DIRT_PARAMS = [
    C.fac('Amount', 0.6, 'Dirt', 'How dirty everything is', key=True),
    C.fac('Opacity', 1.0, 'Dirt', 'Fade the whole layer in or out (0 = hidden)'),
    C.color('Dirt Color', (0.035, 0.028, 0.020), 'Dirt', 'Main dirt color', key=True),
    C.color('Dirt Color 2', (0.10, 0.075, 0.045), 'Dirt', 'Second, lighter dirt color'),
    C.fac('Dirt Roughness', 0.9, 'Dirt', 'Glossiness of the dirt (1 = completely dull)'),
    C.fac('Crevices', 0.8, 'Where', 'Dirt packed into corners and gaps (Cycles / bake)', key=True),
    C.fac('Patches', 0.25, 'Where', 'Faint dirty stains all over', key=True),
    C.fac('Ground Grime', 0.5, 'Where', 'Grime rising from the bottom of the object', key=True),
    C.fac('Grime Height', 0.25, 'Where', 'How high the ground grime reaches (part of the object height)'),
    C.fac('Streaks', 0.2, 'Where', 'Dirt running down in streaks', key=True),
    C.fac('Splatter', 0.0, 'Where', 'Mud splatter specks near the bottom'),
    C.fac('Wetness', 0.0, 'Look', 'Wet mud: darker and glossy'),
    C.fac('Fill', 0.6, 'Look', 'How much the dirt hides the surface relief below'),
    C.fac('Thickness', 0.5, 'Look', 'Thickness of the dirt in the height map'),
] + OVERLAY_PATTERN

DUST_PARAMS = [
    C.fac('Amount', 0.5, 'Dust', 'How dusty everything is', key=True),
    C.fac('Opacity', 1.0, 'Dust', 'Fade the whole layer in or out (0 = hidden)'),
    C.color('Dust Color', (0.42, 0.40, 0.36), 'Dust', 'Color of the dust', key=True),
    C.fac('Dust Roughness', 0.95, 'Dust', 'Glossiness of the dust (1 = completely dull)'),
    C.fac('Top Facing', 1.0, 'Where', 'Dust settles on surfaces that face up', key=True),
    C.fac('Crevices', 0.5, 'Where', 'Extra dust in corners (Cycles / bake)', key=True),
    C.fac('Clumps', 0.4, 'Where', 'Uneven, clumpy dust'),
    C.fac('Wipes', 0.15, 'Where', 'Clean wipe marks where something brushed the dust off', key=True),
    C.fac('Fill', 0.5, 'Look', 'How much the dust hides the surface relief below'),
    C.fac('Thickness', 0.3, 'Look', 'Thickness of the dust in the height map'),
] + OVERLAY_PATTERN


def _below(b, I):
    """Channels of the material below; an unconnected normal means the plain surface normal."""
    geo_n = b.geometry().outputs['Normal']
    n_in = I['Normal']
    has_n = b.math('GREATER_THAN', b.vmath('LENGTH', n_in), 0.5)
    normal = b.mix_vector(has_n, geo_n, n_in)
    return I['Base Color'], I['Metallic'], I['Roughness'], normal, I['Height'], I['Coat'], geo_n


def _finish(b, gout, I, mask, color, rough, fill, thickness, coat_keep, normal, height, geo_n):
    """Mix the layer (color/rough) onto the channels below with coverage `mask`."""
    mask = b.mul(mask, I['Opacity'])
    b.feed(gout.inputs['Base Color'], b.mix_color(mask, I['Base Color'], color))
    b.feed(gout.inputs['Metallic'], b.mul(I['Metallic'], b.one_minus(mask)))
    b.feed(gout.inputs['Roughness'], b.mix(mask, I['Roughness'], rough))
    flat = b.mul(mask, fill)
    b.feed(gout.inputs['Normal'], b.vmath('NORMALIZE', b.mix_vector(flat, normal, geo_n)))
    h = b.mix(b.mul(flat, 0.6), height, 0.5)
    b.feed(gout.inputs['Height'], b.clamp01(b.madd(mask, thickness, h)))
    b.feed(gout.inputs['Coat'], b.mul(I['Coat'], b.one_minus(b.mul(mask, coat_keep))))
    b.feed(gout.inputs['Transmission'], b.mul(I['Transmission'], b.one_minus(mask)))


def _space(b, I, tile, salt):
    """Coordinates for the overlay patterns.

    `salt` keeps the overlay's coordinate nodes from being merged with the
    identical ones of the material below.  Merged nodes stay alive on Cycles'
    fixed-size shader stack while the material's bump mapping is computed;
    keeping them apart lowers the peak of paint + dirt + dust from 230 to ~200.
    """
    return F.Space(b, tile, I['Scale'], I['Seed'], I['Tile Size'] if tile else 1.0, salt=salt)


# ------------------------------------------------------------------ dirt
def build_dirt(b, I, gout, tile):
    S = _space(b, I, tile, 1)
    inv = b.div(1.0, I['Scale'])
    cav = F.cavity_mask(b, S, b.mul(inv, 0.35))
    _c, _m, _r, normal, height, _coat, geo_n = _below(b, I)

    dz = S.znoise(2.0, 31, detail=6.0, roughness=0.62, label='Dirt Patches')
    fine = S.znoise(18.0, 35, detail=4.0, roughness=0.6, label='Dirt Breakup')
    # stains: large, soft and faint
    masks = [b.mul(F.cover(b, dz, b.mul(I['Patches'], 0.45), 0.9), 0.65)]
    if is_socket(cav):
        # packed into corners: a soft gradient, broken up by noise
        packed = b.smoothstep(0.08, 0.75, b.madd(fine, 0.08, b.madd(dz, 0.06, cav)))
        masks.append(b.mul(packed, I['Crevices']))
        # rising from the bottom of the object
        gz = b.separate(b.texcoord().outputs['Generated'])[2]
        rim = b.madd(dz, 0.05, b.madd(fine, 0.015, gz))
        ground = b.one_minus(b.smoothstep(b.mul(I['Grime Height'], 0.15), I['Grime Height'], rim))
        masks.append(b.mul(ground, b.mul(I['Ground Grime'], 0.9)))
        near_ground = b.one_minus(b.smoothstep(0.0, b.mul(I['Grime Height'], 1.6), gz))
    else:
        near_ground = 0.5  # tiles have no "bottom": spread splatter thinly everywhere
    # streaks running down
    aniso = (1.0, 1.0 / 14.0) if tile else (1.0, 1.0, 1.0 / 14.0)
    stz = S.znoise(4.0, 32, detail=4.0, roughness=0.6, aniso=aniso, label='Dirt Streaks')
    streak_on = F.cover(b, S.znoise(1.0, 36, detail=2.0), 0.55, 0.8, gate=False)
    masks.append(b.mul(F.cover(b, stz, b.mul(I['Streaks'], 0.35), 0.45), b.mul(streak_on, 0.75)))
    # mud splatter
    spz = S.znoise(45.0, 33, detail=2.0, label='Splatter')
    masks.append(b.mul(F.cover(b, spz, b.mul(I['Splatter'], 0.2), 0.12), near_ground))
    mask = masks[0]
    for m in masks[1:]:
        mask = b.maximum(mask, m)
    breakup = b.clamp01(b.madd(fine, 0.18, 0.92))
    mask = b.clamp01(b.mul(b.mul(mask, breakup), b.mul(I['Amount'], 1.4)))

    cz = S.znoise(6.0, 34, detail=5.0, roughness=0.6, label='Dirt Color')
    col = b.mix_color(b.smoothstep(-1.2, 1.4, cz), I['Dirt Color'], I['Dirt Color 2'])
    col = b.mix_color(b.mul(b.one_minus(mask), 0.5), col, I['Dirt Color 2'])  # thin dirt looks lighter
    wet = I['Wetness']
    col = b.color_scale(col, b.madd(wet, -0.4, 1.0))
    rough = b.mix(wet, b.madd(cz, 0.03, I['Dirt Roughness']), 0.1)
    thickness = b.mul(I['Thickness'], 0.12)
    _finish(b, gout, I, mask, col, rough, I['Fill'], thickness, b.one_minus(wet), normal, height, geo_n)


# ------------------------------------------------------------------ dust
def build_dust(b, I, gout, tile):
    S = _space(b, I, tile, 2)
    inv = b.div(1.0, I['Scale'])
    cav = F.cavity_mask(b, S, b.mul(inv, 0.3))
    _c, _m, _r, normal, height, _coat, geo_n = _below(b, I)

    if tile:
        facing = 1.0  # a tile is treated like a surface that faces up
    else:
        up = b.madd(b.smoothstep(0.05, 0.9, b.separate(geo_n)[2]), 0.9, 0.1)
        facing = b.mix(I['Top Facing'], 1.0, up)
    amount = I['Amount']
    density = b.mul(amount, facing)
    if is_socket(cav):
        density = b.madd(b.mul(cav, I['Crevices']), b.mul(amount, 1.2), density)
    # soft, continuous variation (dust is a film, not blotches)
    clump = S.znoise(1.2, 42, detail=4.0, roughness=0.55, label='Dust Clumps')
    fluff = S.znoise(9.0, 41, detail=6.0, roughness=0.65, label='Dust Fluff')
    vary = b.madd(clump, b.mul(I['Clumps'], 0.3), b.madd(fluff, 0.12, 1.0))
    mask = b.clamp01(b.mul(b.mul(density, vary), 1.15))
    # specks of lint
    speck = b.smoothstep(2.4, 2.9, S.znoise(70.0, 45, detail=1.5, label='Lint'))
    mask = b.maximum(mask, b.mul(speck, b.mul(density, 0.9)))

    # wipes: soft, wide strokes where the dust was brushed off
    if tile:
        wz = S.znoise(2.0, 43, detail=2.0, roughness=0.5, aniso=(1.0 / 8.0, 1.0, 1.0), direction='D21')
    else:
        base, _ = F.stretched_base(b, S, (0.64, 0.42, 0.64), 8.0, fallback=False)
        wz = S.znoise(2.0, 43, detail=2.0, roughness=0.5, base=base, label='Wipes')
    stroke = b.one_minus(b.smoothstep(0.0, 0.5, b.absolute(wz)))
    patches = F.cover(b, S.znoise(1.0, 44, detail=2.0), b.mul(I['Wipes'], 0.6), 0.6)
    wipe = b.mul(b.mul(stroke, patches), b.clamp01(b.mul(I['Wipes'], 25.0)))
    mask = b.mul(mask, b.one_minus(b.mul(wipe, 0.9)))

    col = b.color_scale(I['Dust Color'], b.madd(fluff, 0.05, b.madd(mask, 0.08, 0.95)))
    thickness = b.mul(I['Thickness'], 0.03)
    _finish(b, gout, I, mask, col, I['Dust Roughness'], I['Fill'], thickness, 1.0, normal, height, geo_n)


# ------------------------------------------------------------------ edge wear
WEAR_PARAMS = [
    C.fac('Amount', 0.6, 'Edge Wear', 'How far the edges are worn (visible in Cycles and in baked textures)',
          key=True),
    C.fac('Opacity', 1.0, 'Edge Wear', 'Fade the whole layer in or out (0 = hidden)'),
    C.Param('Edge Width', 'FLOAT', 0.05, 0.001, 0.3, 'Edge Wear', 'Width of the worn band along the edges',
            subtype='DISTANCE', key=True),
    C.fac('Chips', 0.02, 'Edge Wear', 'Chips knocked off all over, not only on the edges (0.1 = 10%)', key=True),
    C.scale('Chip Scale', 5.0, 0.05, 100.0, 'Edge Wear', 'Chip size (higher = smaller chips)'),
    C.fac('Chip Detail', 0.6, 'Edge Wear', 'Ragged, detailed chip borders'),
    C.fac('Rubbed', 0.0, 'Underneath',
          '0 = chipped through to what is underneath (bare metal...); 1 = only rubbed: the same material, '
          'lighter and smoother (wood, plastic, leather)', key=True),
    C.color('Underneath Color', C.STEEL, 'Underneath', 'Color of what shows through the chips'),
    C.fac('Underneath Metallic', 1.0, 'Underneath', '1 = metal shows through, 0 = wood, primer, plastic...'),
    C.fac('Underneath Roughness', 0.3, 'Underneath', 'Glossiness of what shows through'),
    C.fac('Primer', 0.0, 'Underneath', 'Primer showing around the chips'),
    C.color('Primer Color', (0.32, 0.32, 0.30), 'Underneath', 'Color of the primer'),
    C.fac('Lighten', 0.5, 'Underneath', 'How much lighter rubbed edges get'),
    C.fac('Rust', 0.0, 'Look', 'Rust on the bare metal'),
    C.fac('Paint Thickness', 0.5, 'Look', 'Depth of the chip edges'),
] + OVERLAY_PATTERN

def _lighter(b, color, amount):
    """`color` rubbed lighter (worn wood, plastic or leather edges)."""
    light = b.mix_color(0.3, b.hsv(color, saturation=0.8, value=2.2), (0.55, 0.54, 0.52))
    return b.mix_color(amount, color, light)


def build_wear(b, I, gout, tile):
    S = _space(b, I, tile, 3)
    inv = b.div(1.0, I['Scale'])
    edge = F.edge_mask(b, S, b.mul(I['Edge Width'], inv))
    cav = F.cavity_mask(b, S, b.mul(inv, 0.3))
    col, metal, rough, normal, height, _coat, geo_n = _below(b, I)

    field = F.chip_field(b, S, I['Chip Scale'], I['Chip Detail'], edge, cav, I['Amount'], 51, edge_weight=4.5)
    bare, primer = F.chip_layers(b, field, I['Chips'], I['Amount'], I['Primer'])
    opacity = I['Opacity']
    rubbed = I['Rubbed']
    chipped = b.one_minus(rubbed)
    bare = b.mul(bare, opacity)
    primer = b.mul(b.mul(primer, opacity), chipped)  # rubbed edges have no primer

    # what shows through: something underneath, or the same material rubbed lighter
    zu = S.znoise(10.0, 52, detail=3.0, roughness=0.5, label='Underneath Variation')
    under = b.color_scale(I['Underneath Color'], b.madd(zu, 0.06, 1.0))
    shown = b.mix_color(rubbed, under, _lighter(b, col, I['Lighten']))
    shown_metal = b.mix(rubbed, I['Underneath Metallic'], metal)
    shown_rough = b.mix(rubbed, b.madd(zu, 0.04, I['Underneath Roughness']), b.mul(rough, 0.7))
    rz = S.znoise(4.0, 53, detail=6.0, roughness=0.6, label='Rust')
    rust = b.mul(b.mul(bare, F.cover(b, rz, I['Rust'], 0.3)), b.mul(chipped, shown_metal))
    rust_col = b.mix_color(b.smoothstep(-0.8, 1.4, b.mul(rz, 0.7)), C.RUST_B, C.RUST_A)

    color = b.mix_color(primer, col, I['Primer Color'])
    color = b.mix_color(bare, color, shown)
    color = b.mix_color(rust, color, rust_col)
    b.feed(gout.inputs['Base Color'], color)
    metallic = b.mix(bare, b.mul(metal, b.one_minus(primer)), shown_metal)
    b.feed(gout.inputs['Metallic'], b.mul(metallic, b.one_minus(rust)))
    rough = b.mix(bare, b.mix(primer, rough, 0.6), shown_rough)
    b.feed(gout.inputs['Roughness'], b.mix(rust, rough, b.madd(rz, 0.04, 0.85)))
    b.feed(gout.inputs['Coat'], b.mul(I['Coat'], b.one_minus(b.mul(primer, chipped))))
    b.feed(gout.inputs['Transmission'], b.mul(I['Transmission'], b.one_minus(primer)))

    # chips step down through the paint (in the Height output only, see the module docstring);
    # the revealed surface is smooth: no relief of the paint above
    depth = b.mul(b.madd(primer, 0.45, b.mul(bare, 0.55)), b.mul(I['Paint Thickness'], chipped))
    b.feed(gout.inputs['Height'], b.clamp01(b.madd(depth, -0.4, height)))
    b.feed(gout.inputs['Normal'], b.vmath('NORMALIZE', b.mix_vector(b.mul(bare, chipped), normal, geo_n)))


# ------------------------------------------------------------------ scratches
SCRATCH_PARAMS = [
    C.fac('Amount', 0.5, 'Scratches', 'How scratched the surface is', key=True),
    C.fac('Opacity', 1.0, 'Scratches', 'Fade the whole layer in or out (0 = hidden)'),
    C.scale('Scratch Scale', 1.0, 0.05, 20.0, 'Scratches', 'Scratch size (higher = smaller, denser)', key=True),
    C.fac('Straight', 0.0, 'Scratches', '0 = scratches in every direction, 1 = all along the Scratch Direction'),
    C.axis('Scratch Direction', (1.0, 0.0, 0.0), 'Scratches', 'Direction of straight scratches'),
    C.fac('Fine Scratches', 0.4, 'Scratches', 'Dense hairline scratches that show in reflections', key=True),
    C.fac('Swirls', 0.0, 'Scratches', 'Circular polishing marks (car paint, polished metal)', key=True),
    C.fac('Scuffs', 0.0, 'Scratches', 'Dull, rubbed patches', key=True),
    C.fac('Reveal', 0.0, 'Look',
          '0 = scratches only lighten the surface (plastic, glass, wood); 1 = deep scratches cut through to '
          'the color underneath (paint over metal)', key=True),
    C.color('Scratch Color', (0.62, 0.62, 0.62), 'Look', 'Color revealed by deep scratches (with Reveal)'),
    C.fac('Scratch Metallic', 1.0, 'Look', '1 = metal under the scratches (with Reveal)'),
    C.fac('Lighten', 0.5, 'Look', 'How much lighter the scratches are (without Reveal)'),
    C.fac('Scratch Roughness', 0.4, 'Look', 'Glossiness inside the scratches'),
    C.fac('Depth', 0.5, 'Look', 'Depth of the scratches in the relief'),
] + OVERLAY_PATTERN

def build_scratches(b, I, gout, tile):
    S = _space(b, I, tile, 4)
    col, metal, rough, normal, height, _coat, geo_n = _below(b, I)
    scale = I['Scratch Scale']
    amount = I['Amount']
    opacity = I['Opacity']

    # deep scratches: in patches, in random directions or all one way
    seg_z = S.znoise(b.mul(scale, 4.0), 70, detail=2.0, roughness=0.5, label='Scratch Patches')
    threshold = F.amount_to_z(b, b.mul(amount, 0.5))
    patches = b.smoothstep(b.sub(threshold, 0.4), b.add(threshold, 0.4), seg_z)
    lines = b.mix(I['Straight'], F.scratch_lines(b, S, scale, 71),
                  F.scratch_lines(b, S, scale, 74, direction=I['Scratch Direction']))
    deep = b.mul(b.mul(lines, patches), b.mul(b.clamp01(b.mul(amount, 25.0)), opacity))

    # hairlines all over, a little denser where the deep scratches are
    hz = S.znoise(b.mul(scale, 2.0), 77, detail=2.0, roughness=0.5, label='Hairline Patches')
    hair_on = F.cover(b, b.madd(seg_z, 0.4, hz), b.mul(I['Fine Scratches'], 0.8), 0.6)
    hair = b.mul(b.mul(F.scratch_lines(b, S, scale, 78, layers=F.HAIRLINE_LAYERS, first=1), hair_on), opacity)

    # swirls: arcs around random centers, like a polishing pad leaves them
    sv = S.voronoi(b.mul(scale, 2.0), 80, label='Swirl Centers')
    d = sv.outputs['Distance']
    sr, _sg, _sb = b.separate_color(sv.outputs['Color'])
    ring = b.fract(b.madd(d, 14.0, b.mul(sr, 7.0)))
    ring = b.one_minus(b.smoothstep(0.05, 0.16, b.minimum(ring, b.one_minus(ring))))
    az = S.znoise(b.mul(scale, 9.0), 81, detail=2.0, roughness=0.5, label='Swirl Arcs')
    arcs = b.mul(ring, b.smoothstep(0.2, 1.2, az))
    swirl = b.mul(b.mul(arcs, b.one_minus(b.smoothstep(0.25, 0.55, d))), b.mul(I['Swirls'], opacity))

    # scuffs: dull, rubbed patches with faint streaks
    scz = S.znoise(b.mul(scale, 1.5), 82, detail=4.0, roughness=0.6, label='Scuffs')
    scuff = b.mul(F.cover(b, scz, b.mul(I['Scuffs'], 0.5), 0.6), opacity)
    scuff = b.mul(scuff, b.clamp01(b.madd(hair, 0.5, 0.75)))

    reveal = I['Reveal']
    cut = b.mul(deep, reveal)
    marks = b.maximum(b.maximum(b.mul(deep, 0.85), b.mul(hair, 0.35)), b.mul(swirl, 0.6))
    light = b.mul(b.mul(marks, b.one_minus(reveal)), I['Lighten'])
    color = b.mix_color(b.mul(scuff, 0.35), col, _lighter(b, col, 0.5))
    color = b.mix_color(light, color, _lighter(b, col, 1.0))
    color = b.mix_color(cut, color, I['Scratch Color'])
    b.feed(gout.inputs['Base Color'], color)
    b.feed(gout.inputs['Metallic'], b.mix(cut, metal, I['Scratch Metallic']))
    rough = b.mix(scuff, rough, b.maximum(rough, 0.65))
    rough = b.madd(hair, 0.12, b.madd(swirl, 0.25, rough))
    b.feed(gout.inputs['Roughness'], b.clamp01(b.mix(deep, rough, I['Scratch Roughness'])))
    # marks in a clear coat (car paint) show as duller lines in its reflection
    b.feed(gout.inputs['Coat'], b.mul(I['Coat'], b.one_minus(b.maximum(cut, b.maximum(b.mul(marks, 0.6),
                                                                                       b.mul(swirl, 0.7))))))
    b.feed(gout.inputs['Transmission'], b.mul(I['Transmission'], b.one_minus(b.maximum(cut, b.mul(marks, 0.3)))))

    groove = b.mul(b.maximum(b.maximum(deep, b.mul(hair, 0.3)), b.mul(swirl, 0.2)), I['Depth'])
    b.feed(gout.inputs['Height'], b.clamp01(b.madd(groove, -0.08, height)))
    b.feed(gout.inputs['Normal'], normal)


DIRT_SPEC = dict(
    label='Dirt Overlay', category='OVERLAY', kind='overlay', params=_channel_params() + DIRT_PARAMS,
    outputs=OUTPUTS, build=build_dirt, version=OVERLAY_VERSION,
)
DUST_SPEC = dict(
    label='Dust Overlay', category='OVERLAY', kind='overlay', params=_channel_params() + DUST_PARAMS,
    outputs=OUTPUTS, build=build_dust, version=OVERLAY_VERSION,
)
# Decals (decals.py) are overlays too, but every decal has a node group of its own.
DECAL_SPEC = dict(
    label='Decal', category='OVERLAY', kind='overlay', custom=True, outputs=OUTPUTS, build=None,
    params=_channel_params() + [C.fac('Opacity', 1.0, 'Decal', 'Fade this decal in or out (0 = hidden)')],
    version=OVERLAY_VERSION,
)
WEAR_SPEC = dict(
    label='Edge Wear Overlay', category='WEAR', kind='overlay', params=_channel_params() + WEAR_PARAMS,
    outputs=OUTPUTS, build=build_wear, version=OVERLAY_VERSION,
)
SCRATCH_SPEC = dict(
    label='Scratches Overlay', category='WEAR', kind='overlay', params=_channel_params() + SCRATCH_PARAMS,
    outputs=OUTPUTS, build=build_scratches, version=OVERLAY_VERSION,
)
