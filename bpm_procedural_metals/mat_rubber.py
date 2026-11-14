# SPDX-License-Identifier: GPL-3.0-or-later
"""Rubber generator: tires, mats, flooring, soles, hoses, gaskets, foam and sponge.

Layers: the rubber (fine molded grain, colored granules as in gym flooring,
open pores for foam and sponge); a molded pattern (ribs, tire tread blocks with
sipes, tractor chevrons, off-road knobs, coin studs, diamond plate, waffle
grid); wear (tread worn down and polished, dry-rot cracks, grey chalking,
scuffs); dust and mud packed into the grooves.

The pattern is laid out in a 2D plane (features.Plane): the one the surface
faces most in object mode, a whole number of repeats across in tile mode.
"""

import math

from . import features as F
from . import gencommon as C

RUBBER_BUMP = 0.02  # relief depth of the full 0..1 height range (meters at Scale 1)

PATTERNS = (('Smooth', 0), ('Ribs', 1), ('Blocks', 2), ('Chevrons', 3), ('Knobs', 4), ('Coins', 5),
            ('Diamonds', 6), ('Waffle', 7))
SQRT_HALF = math.sqrt(0.5)


def _enum(name, default, items, panel, desc, key=False):
    return C.Param(name, 'FLOAT', float(default), float(items[0][1]), float(items[-1][1]), panel, desc,
                   ui=('ENUM', items), key=key)


RUBBER_PARAMS = [
    # -- Rubber
    C.color('Rubber Color', (0.018, 0.018, 0.019), 'Rubber', 'Color of the rubber', key=True),
    C.fac('Roughness', 0.7, 'Rubber', '0 = glossy (latex, silicone), 1 = dull', key=True),
    C.fac('Grain', 0.4, 'Rubber', 'Fine molded surface texture'),
    C.fac('Speckles', 0.0, 'Rubber', 'Colored granules (gym flooring, playground surfaces)', key=True),
    C.color('Speckle Color', (0.45, 0.45, 0.45), 'Rubber', 'Color of the granules'),
    C.Param('Speckle Size', 'FLOAT', 0.004, 0.0003, 0.2, 'Rubber', 'Size of the granules', subtype='DISTANCE'),
    C.fac('Foam', 0.0, 'Rubber', 'Open pores: foam rubber and sponge', key=True),
    C.Param('Pore Size', 'FLOAT', 0.004, 0.0003, 0.2, 'Rubber', 'Size of the pores', subtype='DISTANCE'),
    # -- Tread
    _enum('Pattern', 0, PATTERNS, 'Tread',
          'Molded pattern. Ribs: straight grooves. Blocks: car tire tread. Chevrons: tractor tire lugs. Knobs: '
          'off-road studs. Coins: round studs (floor mats). Diamonds: diamond plate. Waffle: square pockets '
          '(soles, anti-fatigue mats)', key=True),
    C.Param('Pattern Size', 'FLOAT', 0.03, 0.001, 5.0, 'Tread', 'Size of one rib, block or stud',
            subtype='DISTANCE', key=True),
    C.fac('Groove Width', 0.3, 'Tread', 'How much of the pattern is groove'),
    C.fac('Depth', 0.7, 'Tread', 'Depth of the grooves', key=True),
    C.fac('Rounding', 0.3, 'Tread', 'Soft, rounded edges (0 = crisp)'),
    C.fac('Sipes', 0.0, 'Tread', 'Thin zigzag cuts across the blocks (car tires)'),
    # -- Wear
    C.fac('Wear', 0.0, 'Wear', 'Pattern worn down, its tops polished smooth', key=True),
    C.fac('Cracking', 0.0, 'Wear', 'Dry rot: fine cracks in old rubber', key=True),
    C.fac('Chalking', 0.0, 'Wear', 'Grey, chalky bloom of old rubber'),
    C.fac('Scuffs', 0.1, 'Wear', 'Pale scuff marks'),
    C.fac('Dust', 0.1, 'Wear', 'Dust in the grooves and in patches', key=True),
    C.color('Dust Color', (0.24, 0.20, 0.15), 'Wear', 'Color of the dust and mud'),
    C.fac('Mud', 0.0, 'Wear', 'Mud packed into the grooves'),
] + C.PATTERN_PARAMS


def build_rubber(b, I, gout, tile):
    S = F.Space(b, tile, I['Scale'], I['Seed'], I['Tile Size'] if tile else 1.0)
    span = b.mul(I['Tile Size'], I['Scale']) if tile else None
    plane = F.Plane(b, S, span)
    P = I['Pattern Size']
    groove = I['Groove Width']

    # ---- the pattern: every shape gives the depth into its raised part (below 0: in a groove)
    s, t, _nw, _nh = plane.grid(P, P, 6.0, 2.0)
    x, y = b.div(s, P), b.div(t, P)
    odd = b.wrap(b.floor(y), 2.0)
    xo = b.madd(odd, 0.5, x)  # every other row shifted by half a cell
    ax, ay = b.absolute(b.sub(b.fract(x), 0.5)), b.absolute(b.sub(b.fract(y), 0.5))
    axo = b.absolute(b.sub(b.fract(xo), 0.5))
    half = b.mul(groove, 0.5)

    ribs = b.sub(b.sub(0.5, ax), half)
    # tread blocks: straight grooves along the tire, slanted narrower ones across, staggered from row to row
    slant = b.madd(b.sub(b.fract(x), 0.5), 0.45, b.madd(b.wrap(b.floor(x), 2.0), 0.5, b.mul(y, 1.5)))
    across = b.sub(b.fract(slant), 0.5)
    blocks = b.minimum(b.sub(b.sub(0.5, ax), half),
                       b.sub(b.div(b.sub(0.5, b.absolute(across)), 1.5), b.mul(half, 0.5)))
    arm = b.mul(b.absolute(b.sub(b.fract(b.div(x, 3.0)), 0.5)), 2.0)  # 0 at the point of a V, 1 at its ends
    lug = b.absolute(b.sub(b.fract(b.madd(arm, 1.1, b.mul(y, 0.5))), 0.5))
    chevrons = b.mul(b.sub(b.sub(0.5, lug), b.madd(groove, 0.35, 0.12)), 1.4)
    knobs = b.sub(b.sub(0.5, b.maximum(axo, ay)), b.madd(groove, 0.4, 0.06))
    coins = b.sub(b.madd(groove, -0.3, 0.42), b.math('SQRT', b.madd(axo, axo, b.mul(ay, ay))))
    fx, fy = b.sub(b.fract(x), 0.5), b.sub(b.fract(y), 0.5)
    turned = b.wrap(b.add(b.floor(x), b.floor(y)), 2.0)  # every other lozenge lies the other way
    du, dv = b.mul(b.add(fx, fy), SQRT_HALF), b.mul(b.sub(fx, fy), SQRT_HALF)
    lu, lv = b.mix(turned, du, dv), b.mix(turned, dv, du)
    ellipse = b.math('SQRT', b.madd(b.div(lu, 0.46), b.div(lu, 0.46), b.mul(b.div(lv, 0.14), b.div(lv, 0.14))))
    diamonds = b.mul(b.sub(1.0, ellipse), 0.14)
    waffle = b.sub(b.madd(groove, -0.3, 0.2), b.sub(0.5, b.maximum(ax, ay)))

    pattern = I['Pattern']
    into = 1.0  # smooth: all raised
    for index, shape in enumerate((ribs, blocks, chevrons, knobs, coins, diamonds, waffle), 1):
        into = b.mix(b.math('COMPARE', pattern, float(index), 0.5), into, shape)
    into = b.mul(into, P)  # pattern units
    wear = I['Wear']
    soft = b.maximum(b.mul(b.madd(wear, 0.5, b.madd(I['Rounding'], 0.25, 0.01)), P), 0.00005)
    raised = b.clamp01(b.div(into, soft))
    raised = b.one_minus(b.mul(b.one_minus(raised), b.one_minus(raised)))  # quarter-round edges
    top = b.smoothstep(0.6, 1.0, raised)
    zig = b.absolute(b.sub(b.fract(b.mul(x, 4.0)), 0.5))
    sipe = b.one_minus(b.smoothstep(0.03, 0.07, b.absolute(b.madd(b.sub(zig, 0.25), 0.3, across))))
    sipe = b.mul(b.mul(sipe, top), b.mul(I['Sipes'], b.math('COMPARE', pattern, 2.0, 0.5)))
    tall = b.mul(I['Depth'], b.madd(wear, -0.7, 1.0))  # worn patterns are shallower
    h = b.madd(raised, b.mul(tall, 0.5), b.madd(tall, -0.5, 0.75))
    h = b.madd(sipe, b.mul(tall, -0.3), h)
    low = b.one_minus(raised)

    # ---- the rubber: grain, granules, pores
    cloud = S.znoise(2.0, 1, detail=4.0, roughness=0.6, label='Clouds')
    fine = S.noise(420.0, 2, detail=2.0, roughness=0.5, label='Grain')
    grain = b.mul(b.sub(fine, 0.5), I['Grain'])
    col = b.color_scale(I['Rubber Color'], b.madd(cloud, 0.04, b.madd(grain, 0.5, 1.0)))
    rough = b.madd(cloud, 0.03, b.madd(grain, 0.2, I['Roughness']))
    hm = b.mul(grain, 2.0)

    granules = S.voronoi(b.div(1.0, I['Speckle Size']), 3, label='Granules')
    gr, gg, gb = b.separate_color(granules.outputs['Color'])
    granule = b.mul(b.one_minus(b.smoothstep(0.3, 0.42, granules.outputs['Distance'])),
                    b.math('LESS_THAN', gr, I['Speckles']))
    col = b.mix_color(granule, col, b.color_scale(I['Speckle Color'], b.madd(gg, 0.7, 0.6)))
    hm = b.madd(b.mul(b.sub(gb, 0.5), b.clamp01(b.mul(I['Speckles'], 4.0))), 0.6, hm)

    foam = I['Foam']
    pores = S.voronoi(b.div(1.0, I['Pore Size']), 4, label='Pores')
    pr, pg, _pb = b.separate_color(pores.outputs['Color'])
    cells = S.voronoi(b.div(0.4, I['Pore Size']), 5, label='Big Pores')
    cr, cg, _cb = b.separate_color(cells.outputs['Color'])
    pore = b.mul(b.one_minus(b.smoothstep(b.madd(pg, 0.15, 0.12), b.madd(pg, 0.2, 0.3), pores.outputs['Distance'])),
                 b.math('LESS_THAN', pr, b.mul(foam, 0.85)))
    big = b.mul(b.one_minus(b.smoothstep(b.madd(cg, 0.15, 0.1), b.madd(cg, 0.2, 0.28), cells.outputs['Distance'])),
                b.math('LESS_THAN', cr, b.mul(foam, 0.35)))
    hole = b.maximum(pore, big)
    col = b.color_scale(col, b.madd(hole, -0.72, 1.0))
    rough = b.madd(b.mul(foam, 0.2), 1.0, b.madd(hole, 0.1, rough))
    h = b.madd(big, -0.2, h)
    hm = b.madd(pore, -3.0, hm)

    # ---- wear: polished tops, scuffs, dry-rot cracks, chalking
    polished = b.mul(b.mul(top, wear), b.clamp01(b.madd(cloud, 0.3, 0.8)))
    rough = b.madd(polished, -0.25, rough)
    hm = b.mul(hm, b.madd(polished, -0.8, 1.0))
    scuff = F.scratch_mask(b, S, I['Scuffs'], 0.6, 6)
    col = b.mix_color(b.mul(scuff, 0.3), col, b.gray(0.3))
    rough = b.madd(scuff, 0.12, rough)

    crack_d = F.crack_distance(b, S, 120.0, 24, warp=0.3, label='Dry Rot')
    crack_on = F.cover(b, b.madd(low, 0.8, S.znoise(3.0, 18, detail=3.0, roughness=0.6, label='Crack Areas')),
                       b.mul(I['Cracking'], 0.85), 0.5)
    crack = b.mul(b.one_minus(b.smoothstep(0.02, 0.09, crack_d)), crack_on)
    col = b.color_scale(col, b.madd(crack, -0.6, 1.0))
    h = b.madd(crack, -0.08, h)
    rough = b.madd(crack, 0.1, rough)

    chalk_z = S.znoise(4.0, 19, detail=5.0, roughness=0.65, label='Chalking')
    chalk = b.mul(b.mul(I['Chalking'], b.clamp01(b.madd(chalk_z, 0.3, 0.6))), b.madd(polished, -0.7, 1.0))
    col = b.mix_color(b.mul(chalk, 0.5), col, b.gray(0.22))
    rough = b.madd(chalk, 0.2, rough)

    # ---- dust in the grooves, mud packed into them
    dz = S.znoise(2.5, 20, detail=5.0, roughness=0.6, label='Dust')
    dust = I['Dust']
    dusty = b.mul(F.cover(b, dz, b.mul(dust, 0.3), 0.9), 0.5)
    dusty = b.clamp01(b.maximum(dusty, b.mul(b.maximum(low, b.maximum(hole, sipe)), b.mul(dust, 0.85))))
    col = b.mix_color(dusty, col, b.color_scale(I['Dust Color'], b.madd(dz, 0.1, 1.0)))
    rough = b.mix(dusty, rough, 0.92)

    mud_z = S.znoise(9.0, 21, detail=5.0, roughness=0.65, label='Mud')
    packed = F.cover(b, b.madd(low, 2.5, b.madd(dz, 0.5, b.mul(mud_z, 0.5))), b.mul(I['Mud'], 0.75), 0.25)
    col = b.mix_color(packed, col, b.color_scale(I['Dust Color'], b.madd(mud_z, 0.12, 0.55)))
    rough = b.mix(packed, rough, 0.88)
    h = b.mix(packed, h, b.maximum(h, b.madd(mud_z, 0.03, b.madd(tall, -0.12, 0.7))))
    hm = b.mix(packed, hm, b.mul(mud_z, 0.6))

    C.finish(b, gout, I, col, 0.0, rough, b.clamp01(h), hm, distance=RUBBER_BUMP)


SPEC = dict(
    label='Rubber', category='RUBBER', params=RUBBER_PARAMS, outputs=C.COMMON_OUTPUTS, build=build_rubber,
    display=('Rubber Color', 0.0, 'Roughness'), bump=RUBBER_BUMP, fit=0.3,
)
