# SPDX-License-Identifier: GPL-3.0-or-later
"""Plaster generator: plaster, stucco, painted walls and wallpaper, from fresh to derelict.

Layers: the plaster (sand finish, orange peel, roughcast, trowel marks,
knockdown, cloudy two-tone mottling for Venetian plaster and limewash); paint
or wallpaper on top (plain or with a printed pattern) that can peel; cracks;
plaster crumbling off the wall, showing brick, wooden lath or concrete behind
it; stains (water stains with tide lines, rising damp, mold, dirt, soot).

Wallpaper patterns and the wall behind the plaster are laid out in a 2D plane
(features.Plane): the one the surface faces most in object mode, a whole
number of repeats across in tile mode.
"""

from . import features as F
from . import gencommon as C
from .nodebuilder import is_socket

PLASTER_BUMP = 0.02  # relief depth of the full 0..1 height range (meters at Scale 1)

PATTERNS = (('None', 0), ('Stripes', 1), ('Dots', 2), ('Diamonds', 3), ('Trellis', 4), ('Quatrefoil', 5))
WALLS = (('Brick', 0), ('Lath', 1), ('Concrete', 2))

BRICK = (0.26, 0.085, 0.045)
MORTAR = (0.33, 0.31, 0.27)
LATH = (0.16, 0.10, 0.055)
CONCRETE = (0.30, 0.30, 0.29)
STAIN = (0.50, 0.33, 0.15)  # multiplied onto the wall
MOLD = (0.016, 0.022, 0.014)
SOOT = (0.014, 0.013, 0.012)
SALT = (0.80, 0.80, 0.77)


def _enum(name, default, items, panel, desc, key=False):
    return C.Param(name, 'FLOAT', float(default), float(items[0][1]), float(items[-1][1]), panel, desc,
                   ui=('ENUM', items), key=key)


PLASTER_PARAMS = [
    # -- Plaster
    C.color('Wall Color', (0.52, 0.49, 0.44), 'Plaster', 'Color of the plaster', key=True),
    C.fac('Color Variation', 0.2, 'Plaster', 'Patchy, uneven color'),
    C.fac('Mottling', 0.0, 'Plaster', 'Cloudy second color (Venetian plaster, limewash, old color wash)', key=True),
    C.color('Second Color', (0.45, 0.38, 0.28), 'Plaster', 'Color of the mottling'),
    C.fac('Roughness', 0.85, 'Plaster', '0 = polished and glossy, 1 = rough and dull'),
    C.fac('Sand', 0.3, 'Plaster', 'Fine sandy grain', key=True),
    C.fac('Orange Peel', 0.0, 'Plaster', 'Bumpy sprayed texture'),
    C.fac('Roughcast', 0.0, 'Plaster', 'Lumpy pebble-dash render', key=True),
    C.fac('Trowel Marks', 0.2, 'Plaster', 'Sweeping ridges and flat patches left by the trowel', key=True),
    C.fac('Knockdown', 0.0, 'Plaster', 'Flattened splatter islands (knockdown ceilings and walls)'),
    C.scale('Texture Size', 1.0, 0.1, 10.0, 'Plaster', 'Size of the trowel marks, lumps and islands'),
    # -- Paint
    C.fac('Paint', 0.0, 'Paint', 'Painted or wallpapered over', key=True),
    C.color('Paint Color', (0.42, 0.52, 0.50), 'Paint', 'Color of the paint or wallpaper'),
    C.fac('Paint Gloss', 0.3, 'Paint', '0 = matte emulsion or paper, 1 = glossy oil paint'),
    C.fac('Peeling', 0.0, 'Paint', 'Paint or wallpaper flaking off', key=True),
    _enum('Pattern', 0, PATTERNS, 'Paint', 'Printed wallpaper pattern (or stencilled paint)', key=True),
    C.color('Pattern Color', (0.60, 0.55, 0.40), 'Paint', 'Color of the pattern'),
    C.Param('Pattern Size', 'FLOAT', 0.12, 0.005, 5.0, 'Paint', 'Size of one repeat of the pattern',
            subtype='DISTANCE'),
    # -- Damage
    C.fac('Cracks', 0.1, 'Damage', 'Hairline cracks', key=True),
    C.scale('Crack Scale', 1.5, 0.1, 50.0, 'Damage', 'Size of the cracked pieces (higher = smaller)'),
    C.fac('Crumbling', 0.0, 'Damage', 'Plaster fallen off, showing the wall behind it', key=True),
    _enum('Wall Behind', 0, WALLS, 'Damage', 'What shows where the plaster is gone'),
    # -- Stains
    C.fac('Water Stains', 0.0, 'Stains', 'Brown stains with dark tide lines from leaks', key=True),
    C.fac('Damp', 0.0, 'Stains', 'Rising damp: dark, wet plaster and salt low on the wall'),
    C.fac('Mold', 0.0, 'Stains', 'Black and green mold spots', key=True),
    C.fac('Dirt', 0.1, 'Stains', 'Grime in corners, low on the wall and in patches'),
    C.fac('Soot', 0.0, 'Stains', 'Blackened by smoke, most near the top'),
] + C.PATTERN_PARAMS


def build_plaster(b, I, gout, tile):
    S = F.Space(b, tile, I['Scale'], I['Seed'], I['Tile Size'] if tile else 1.0)
    inv = b.div(1.0, I['Scale'])
    span = b.mul(I['Tile Size'], I['Scale']) if tile else None
    edge = F.edge_mask(b, S, b.mul(0.03, inv))
    cav = F.cavity_mask(b, S, b.mul(inv, 0.3))
    has_geo = is_socket(edge)
    up = b.separate(b.texcoord().outputs['Generated'])[2] if has_geo else None  # 0 at the bottom, 1 at the top
    plane = F.Plane(b, S, span)
    ts = b.div(1.0, I['Texture Size'])

    # ---- plaster: color and finish
    wall = S.znoise(0.6, 1, detail=4.0, roughness=0.6, label='Wall Variation')
    clouds = S.znoise(b.mul(ts, 2.2), 2, detail=6.0, roughness=0.65, distortion=1.0, label='Mottling')
    col = b.color_scale(I['Wall Color'], b.madd(wall, b.mul(I['Color Variation'], 0.09), 1.0))
    col = b.mix_color(b.mul(b.smoothstep(-1.2, 1.4, clouds), I['Mottling']), col, I['Second Color'])
    rough = b.madd(clouds, b.madd(I['Mottling'], 0.05, 0.02), I['Roughness'])
    sand = S.noise(280.0, 3, detail=2.0, roughness=0.5, label='Sand')
    grain = b.mul(b.sub(sand, 0.5), I['Sand'])
    col = b.color_scale(col, b.madd(grain, 0.35, 1.0))
    hm = b.mul(grain, 1.6)
    peel_tex = S.znoise(b.mul(ts, 45.0), 4, detail=2.0, roughness=0.4, label='Orange Peel')
    hm = b.madd(b.smoothstep(-1.0, 1.0, peel_tex), b.mul(I['Orange Peel'], 2.5), hm)
    lumps = S.voronoi(b.mul(ts, 50.0), 5, label='Roughcast')
    lump = b.one_minus(b.smoothstep(0.1, 0.55, lumps.outputs['Distance']))
    h = b.madd(lump, b.mul(I['Roughcast'], 0.4), 0.5)
    col = b.color_scale(col, b.madd(b.mul(b.sub(lump, 0.5), I['Roughcast']), 0.18, 1.0))
    sweep = S.znoise(b.mul(ts, 5.0), 6, detail=3.0, roughness=0.55, distortion=1.6, label='Trowel Marks')
    ridge = b.one_minus(b.smoothstep(0.0, 0.45, b.absolute(sweep)))  # the edge of every sweep of the trowel
    h = b.madd(b.madd(ridge, 0.5, b.mul(b.smoothstep(-0.2, 0.3, sweep), 0.5)), b.mul(I['Trowel Marks'], 0.3), h)
    islands = S.znoise(b.mul(ts, 10.0), 7, detail=3.0, roughness=0.6, label='Knockdown')
    island = b.smoothstep(0.0, 0.35, islands)
    h = b.madd(island, b.mul(I['Knockdown'], 0.3), h)
    col = b.color_scale(col, b.madd(b.mul(b.sub(island, 0.6), I['Knockdown']), 0.06, 1.0))

    # ---- cracks
    crack_d = F.crack_distance(b, S, I['Crack Scale'], 8)
    crack_on = F.cover(b, S.znoise(b.mul(I['Crack Scale'], 0.6), 10, detail=3.0, roughness=0.6,
                                   label='Crack Areas'), b.mul(I['Cracks'], 0.8), 0.5)
    crack = b.mul(b.one_minus(b.smoothstep(0.0015, 0.006, crack_d)), crack_on)
    crack_zone = b.mul(b.one_minus(b.smoothstep(0.01, 0.1, crack_d)), crack_on)

    # ---- paint or wallpaper, with a printed pattern, peeling
    size = I['Pattern Size']
    ps, pt, _nw, _nh = plane.grid(size, size, 2.0, 2.0)
    x, y = b.div(ps, size), b.div(pt, size)
    stripes = b.math('LESS_THAN', b.fract(x), 0.5)
    odd = b.wrap(b.floor(y), 2.0)
    ax, ay = b.sub(b.fract(b.madd(odd, 0.5, x)), 0.5), b.sub(b.fract(y), 0.5)  # from the middle of a cell
    radius = b.math('SQRT', b.madd(ax, ax, b.mul(ay, ay)))
    dots = b.one_minus(b.smoothstep(0.2, 0.24, radius))
    cx, cy = b.absolute(b.sub(b.fract(x), 0.5)), b.absolute(b.sub(b.fract(y), 0.5))
    diamonds = b.math('LESS_THAN', b.add(cx, cy), 0.5)
    d1 = b.absolute(b.sub(b.fract(b.add(x, y)), 0.5))
    d2 = b.absolute(b.sub(b.fract(b.sub(x, y)), 0.5))
    trellis = b.one_minus(b.smoothstep(0.05, 0.08, b.minimum(d1, d2)))
    lobe_x = b.math('SQRT', b.madd(b.sub(cx, 0.2), b.sub(cx, 0.2), b.mul(cy, cy)))
    lobe_y = b.math('SQRT', b.madd(b.sub(cy, 0.2), b.sub(cy, 0.2), b.mul(cx, cx)))
    lobes = b.minimum(lobe_x, lobe_y)
    corner = b.math('SQRT', b.madd(b.sub(cx, 0.5), b.sub(cx, 0.5), b.mul(b.sub(cy, 0.5), b.sub(cy, 0.5))))
    quatrefoil = b.maximum(b.mul(b.one_minus(b.smoothstep(0.17, 0.2, lobes)), b.smoothstep(0.09, 0.12, lobes)),
                           b.one_minus(b.smoothstep(0.07, 0.1, corner)))
    printed = 0.0
    for index, shape in enumerate((stripes, dots, diamonds, trellis, quatrefoil), 1):
        printed = b.mix(b.math('COMPARE', I['Pattern'], float(index), 0.5), printed, shape)
    paint_col = b.mix_color(printed, I['Paint Color'], I['Pattern Color'])
    paint_col = b.color_scale(paint_col, b.madd(wall, 0.03, b.madd(grain, 0.1, 1.0)))

    peel_z = S.znoise(1.6, 11, detail=5.0, roughness=0.65, label='Peeling')
    peel_where = b.madd(crack_zone, 1.2, peel_z)
    if has_geo:
        peel_where = b.madd(edge, 1.2, peel_where)
    threshold = F.amount_to_z(b, b.mul(I['Peeling'], 0.85))
    gate = b.clamp01(b.mul(I['Peeling'], 25.0))
    peeled = b.mul(b.smoothstep(b.sub(threshold, 0.03), b.add(threshold, 0.03), peel_where), gate)
    lip = b.mul(b.mul(b.smoothstep(b.sub(threshold, 0.22), b.sub(threshold, 0.03), peel_where),
                      b.one_minus(peeled)), gate)  # curling edges of the paint that is left
    paint = b.mul(I['Paint'], b.one_minus(peeled))
    bare = b.mul(I['Paint'], peeled)  # plaster that was under the paint: dustier, with glue and paint left
    col = b.color_scale(col, b.madd(bare, b.madd(peel_z, 0.04, -0.1), 1.0))
    col = b.mix_color(paint, col, paint_col)
    rough = b.mix(paint, rough, b.madd(I['Paint Gloss'], -0.65, 0.8))
    hm = b.madd(b.mul(paint, hm), -0.6, hm)
    h = b.madd(paint, 0.012, h)
    lifted = b.mul(lip, I['Paint'])
    h = b.madd(lifted, 0.03, h)
    col = b.color_scale(col, b.madd(lifted, 0.1, 1.0))

    col = b.color_scale(col, b.madd(crack, -0.7, 1.0))
    h = b.madd(crack, -0.15, h)

    # ---- crumbling: the plaster gone, the wall behind it showing
    fall_z = S.znoise(1.0, 12, detail=5.0, roughness=0.6, label='Crumbling')
    ragged = S.znoise(22.0, 13, detail=3.0, roughness=0.6, label='Broken Edge')
    fall_where = b.madd(crack_zone, 0.9, b.madd(ragged, 0.12, fall_z))
    if has_geo:
        fall_where = b.add(fall_where, b.madd(edge, 1.0, b.mul(b.one_minus(up), 0.8)))
    gone = F.cover(b, fall_where, b.mul(I['Crumbling'], 0.7), 0.04)
    near = b.mul(F.cover(b, fall_where, b.madd(I['Crumbling'], 0.7, 0.06), 0.1), b.one_minus(gone))

    bs, bt, bnw, bnh = plane.grid(0.25, 0.085, 1.0, 2.0)
    by = b.div(bt, 0.085)
    brow = plane.wrapped(b.floor(by), bnh)
    bx = b.madd(b.wrap(brow, 2.0), 0.5, b.div(bs, 0.25))
    bcol = plane.wrapped(b.floor(bx), bnw)
    joint = b.minimum(b.mul(b.sub(0.5, b.absolute(b.sub(b.fract(bx), 0.5))), 0.25),
                      b.mul(b.sub(0.5, b.absolute(b.sub(b.fract(by), 0.5))), 0.085))
    is_brick = b.smoothstep(0.005, 0.009, b.madd(ragged, 0.001, joint))
    b1, bc = b.white_noise(b.combine(bcol, brow, b.add(I['Seed'], 0.43)))
    brick_col = b.color_scale(BRICK, b.madd(b1, 0.7, b.madd(sand, 0.3, 0.5)))
    brick_col = b.mix_color(is_brick, b.color_scale(MORTAR, b.madd(sand, 0.3, 0.85)), brick_col)
    brick_h = b.madd(is_brick, 0.06, b.mul(b.separate_color(bc)[0], 0.03))

    ls, lt, _lnw, lnh = plane.grid(1.0, 0.05)
    ly = b.div(lt, 0.05)
    lrow = plane.wrapped(b.floor(ly), lnh)
    slat = b.smoothstep(0.1, 0.16, b.sub(0.5, b.absolute(b.sub(b.fract(ly), 0.5))))
    l1, _lc = b.white_noise(b.combine(lrow, I['Seed'], 0.77))
    fibers = S.znoise(14.0, 14, detail=3.0, roughness=0.6, aniso=(0.08, 1.0) if tile else (0.08, 0.08, 1.0),
                      jitter=b.mul(l1, 31.0), label='Lath Grain')
    lath_col = b.color_scale(LATH, b.madd(l1, 0.6, b.madd(fibers, 0.12, 0.7)))
    lath_col = b.mix_color(slat, (0.012, 0.010, 0.008), lath_col)
    lath_h = b.madd(slat, 0.1, b.mul(l1, 0.02))

    conc_z = S.znoise(9.0, 15, detail=5.0, roughness=0.65, label='Concrete')
    conc_col = b.color_scale(CONCRETE, b.madd(conc_z, 0.08, b.madd(sand, 0.35, 0.82)))
    behind, behind_h = brick_col, brick_h
    for index, (other, other_h) in enumerate(((lath_col, lath_h), (conc_col, b.madd(conc_z, 0.02, 0.05))), 1):
        pick = b.math('COMPARE', I['Wall Behind'], float(index), 0.5)
        behind, behind_h = b.mix_color(pick, behind, other), b.mix(pick, behind_h, other_h)
    col = b.color_scale(col, b.madd(near, 0.12, 1.0))  # the broken edge of the plaster: fresh and pale
    col = b.mix_color(gone, col, behind)
    rough = b.mix(gone, rough, 0.92)
    h = b.mix(gone, h, b.add(behind_h, 0.12))
    hm = b.mix(gone, hm, b.mul(b.sub(sand, 0.5), 1.5))
    there = b.one_minus(gone)  # stains below are on the plaster, fainter on the wall behind

    # ---- stains: water with tide lines, rising damp and salt, mold, dirt, soot
    leak_z = S.znoise(0.9, 16, detail=4.0, roughness=0.55, distortion=0.8, label='Water Stains')
    leak = b.add(leak_z, b.mul(up, 0.7)) if has_geo else leak_z
    level = F.amount_to_z(b, b.mul(I['Water Stains'], 0.5))
    on = b.clamp01(b.mul(I['Water Stains'], 25.0))
    body = b.mul(b.smoothstep(b.sub(level, 0.05), b.add(level, 0.9), leak), on)
    tide = b.mul(b.mul(b.smoothstep(b.sub(level, 0.08), level, leak),
                       b.one_minus(b.smoothstep(level, b.add(level, 0.16), leak))), on)
    stain = b.mul(b.clamp01(b.madd(tide, 0.8, b.mul(body, 0.75))), b.madd(there, 0.6, 0.4))
    col = b.mix_color(stain, col, STAIN, blend='MULTIPLY')

    damp_z = S.znoise(1.3, 17, detail=4.0, roughness=0.6, label='Damp')
    rise = b.madd(I['Damp'], 0.55, b.madd(damp_z, 0.06, -0.05))
    if has_geo:
        damp = b.mul(b.one_minus(b.smoothstep(b.mul(rise, 0.6), rise, up)), b.clamp01(b.mul(I['Damp'], 25.0)))
        salt_line = b.mul(b.one_minus(b.smoothstep(0.0, 0.07, b.absolute(b.sub(up, rise)))),
                          b.clamp01(b.mul(I['Damp'], 25.0)))
    else:
        damp = F.cover(b, damp_z, b.mul(I['Damp'], 0.6), 0.5)
        salt_line = b.mul(b.mul(damp, b.one_minus(damp)), 3.0)
    col = b.color_scale(col, b.madd(damp, -0.5, 1.0))
    rough = b.madd(damp, -0.25, rough)
    salt = b.mul(salt_line, b.clamp01(b.madd(sand, 1.4, b.madd(damp_z, 0.3, 0.1))))
    col = b.mix_color(b.mul(salt, 0.8), col, SALT)

    spots = S.voronoi(55.0, 18, label='Mold Spots')
    sr, sg, _sb = b.separate_color(spots.outputs['Color'])
    mold_z = S.znoise(1.8, 19, detail=5.0, roughness=0.65, label='Mold')
    mold_where = b.madd(damp, 1.5, b.madd(stain, 1.0, mold_z))
    if has_geo:
        mold_where = b.madd(cav, 1.5, mold_where)
    colony = F.cover(b, mold_where, b.mul(I['Mold'], 0.55), 0.6)
    spot = b.one_minus(b.smoothstep(b.madd(sg, 0.25, 0.1), b.madd(sg, 0.3, 0.3), spots.outputs['Distance']))
    mold = b.mul(colony, b.clamp01(b.madd(spot, b.madd(colony, 0.5, 0.5), b.mul(b.smoothstep(0.4, 1.0, colony), 0.85))))
    col = b.mix_color(b.mul(mold, 0.92), col, b.mix_color(b.mul(sr, 0.6), MOLD, (0.03, 0.05, 0.02)))
    rough = b.mix(mold, rough, 0.95)

    dz = S.znoise(2.2, 20, detail=5.0, roughness=0.6, label='Dirt')
    dirt = I['Dirt']
    grime = b.mul(F.cover(b, dz, b.mul(dirt, 0.3), 0.9), 0.5)
    grime = b.maximum(grime, b.mul(crack_zone, b.mul(dirt, 0.4)))
    if has_geo:
        grime = b.maximum(grime, b.mul(b.smoothstep(0.1, 0.7, b.madd(dz, 0.06, cav)), dirt))
        grime = b.maximum(grime, b.mul(b.one_minus(b.smoothstep(0.0, 0.2, b.madd(dz, 0.03, up))), b.mul(dirt, 0.7)))
    grime = b.clamp01(grime)
    col = b.mix_color(grime, col, b.color_scale(C.DIRT, b.madd(dz, 0.15, 1.3)))
    rough = b.mix(grime, rough, 0.92)

    smoke_z = S.znoise(1.1, 21, detail=4.0, roughness=0.6, label='Soot')
    smoke = b.madd(up, 1.6, b.add(smoke_z, -0.8)) if has_geo else smoke_z
    soot = b.mul(F.cover(b, smoke, b.mul(I['Soot'], 0.7), 1.0), b.clamp01(b.madd(I['Soot'], 0.5, 0.45)))
    col = b.mix_color(soot, col, b.color_scale(SOOT, b.madd(dz, 0.2, 1.2)))
    rough = b.mix(soot, rough, 0.95)

    C.finish(b, gout, I, col, 0.0, rough, b.clamp01(h), hm, distance=PLASTER_BUMP)


SPEC = dict(
    label='Plaster', category='PLASTER', params=PLASTER_PARAMS, outputs=C.COMMON_OUTPUTS, build=build_plaster,
    display=('Wall Color', 0.0, 'Roughness'), bump=PLASTER_BUMP, fit=0.3,
)
