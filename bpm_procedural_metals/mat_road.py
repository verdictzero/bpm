# SPDX-License-Identifier: GPL-3.0-or-later
"""Road generator: asphalt, tarmac, gravel and dirt roads, car parks and runways.

Layers: asphalt (black binder with stones that show more as it ages); repair
patches; painted markings (lines, crosswalks, parking bays, hatching) that wear
off; cracks (long ones, fine "alligator" cracking, cracks sealed with tar);
potholes; loose gravel; dust, sand or dirt (up to a dirt road); oil stains and
tire marks; puddles and wetness.

Markings and patches are laid out in a 2D plane (features.Plane): the one the
surface faces most in object mode (lines run along Y on the ground), a whole
number of lanes across in tile mode.
"""

from . import features as F
from . import gencommon as C

ROAD_BUMP = 0.03  # relief depth of the full 0..1 height range (meters at Scale 1)

MARKINGS = (('None', 0), ('Solid Line', 1), ('Dashed Line', 2), ('Double Line', 3), ('Crosswalk', 4),
            ('Parking Bays', 5), ('Hatching', 6))
TAR = (0.008, 0.008, 0.009)
BASE = (0.16, 0.13, 0.10)  # the gravel bed under the asphalt
WATER = (0.02, 0.02, 0.018)


def _enum(name, default, items, panel, desc, key=False):
    return C.Param(name, 'FLOAT', float(default), float(items[0][1]), float(items[-1][1]), panel, desc,
                   ui=('ENUM', items), key=key)


ROAD_PARAMS = [
    # -- Surface
    C.color('Asphalt Color', (0.028, 0.028, 0.03), 'Surface', 'Color of the binder between the stones', key=True),
    C.fac('Age', 0.3, 'Surface', '0 = fresh, black and a little oily, 1 = old, grey and dry with bare stones',
          key=True),
    C.fac('Aggregate', 0.6, 'Surface', 'How much the stones in the asphalt show', key=True),
    C.Param('Aggregate Size', 'FLOAT', 0.012, 0.001, 0.5, 'Surface', 'Size of the stones', subtype='DISTANCE'),
    C.color('Aggregate Color', (0.26, 0.25, 0.23), 'Surface', 'Color of the stones (each one varies)'),
    C.fac('Roughness', 0.85, 'Surface', '0 = glossy, 1 = rough and dull'),
    C.fac('Unevenness', 0.3, 'Surface', 'Gentle bumps and dips (where puddles form)'),
    C.fac('Gravel', 0.0, 'Surface', 'Loose gravel on top (1 = a gravel road)', key=True),
    C.fac('Dirt', 0.0, 'Surface', 'Dust, sand or dirt on top (1 = a dirt road)', key=True),
    C.color('Dirt Color', (0.17, 0.12, 0.075), 'Surface', 'Color of the dirt'),
    # -- Damage
    C.fac('Cracks', 0.2, 'Damage', 'Long cracks', key=True),
    C.scale('Crack Scale', 1.5, 0.1, 50.0, 'Damage', 'Size of the cracked pieces (higher = smaller)'),
    C.fac('Alligator Cracks', 0.0, 'Damage', 'Areas of fine, dense cracking', key=True),
    C.fac('Crack Sealant', 0.0, 'Damage', 'Cracks sealed with shiny black tar'),
    C.fac('Potholes', 0.0, 'Damage', 'Holes down to the gravel bed', key=True),
    C.fac('Patches', 0.0, 'Damage', 'Rectangular repair patches of newer asphalt'),
    # -- Markings
    _enum('Marking', 0, MARKINGS, 'Markings', 'Painted road markings (they run along Y on the ground)', key=True),
    C.color('Marking Color', (0.72, 0.72, 0.68), 'Markings', 'Color of the paint'),
    C.Param('Line Width', 'FLOAT', 0.12, 0.005, 2.0, 'Markings', 'Width of the painted lines', subtype='DISTANCE'),
    C.Param('Lane Width', 'FLOAT', 3.0, 0.05, 50.0, 'Markings',
            'Distance from one line to the next (Parking Bays: the width of a bay)', subtype='DISTANCE'),
    C.fac('Marking Wear', 0.3, 'Markings', 'Paint worn off by traffic'),
    # -- Stains
    C.fac('Oil Stains', 0.1, 'Stains', 'Dark oil spots'),
    C.fac('Tire Marks', 0.0, 'Stains', 'Black rubber streaks along the road'),
    C.fac('Puddles', 0.0, 'Stains', 'Water standing in the dips', key=True),
    C.fac('Wetness', 0.0, 'Stains', 'Wet from rain: darker and shiny', key=True),
] + C.PATTERN_PARAMS


def build_road(b, I, gout, tile):
    S = F.Space(b, tile, I['Scale'], I['Seed'], I['Tile Size'] if tile else 1.0)
    span = b.mul(I['Tile Size'], I['Scale']) if tile else None
    plane = F.Plane(b, S, span)
    age = I['Age']

    # ---- asphalt: binder and stones
    bumps = S.znoise(0.5, 1, detail=3.0, roughness=0.5, label='Unevenness')
    level = b.madd(bumps, b.mul(I['Unevenness'], 0.07), 0.6)
    h = level
    cloud = S.znoise(1.7, 2, detail=4.0, roughness=0.6, label='Clouds')
    sand = S.noise(260.0, 3, detail=2.0, roughness=0.5, label='Sand')
    binder = b.mix_color(b.mul(age, 0.55), I['Asphalt Color'], b.color_scale(b.gray(0.11), b.madd(cloud, 0.06, 1.0)))
    binder = b.color_scale(binder, b.madd(b.sub(sand, 0.5), 0.5, b.madd(cloud, 0.05, 1.0)))
    stones = S.voronoi(b.div(1.0, I['Aggregate Size']), 4, label='Aggregate')
    sr, sg, _sb = b.separate_color(stones.outputs['Color'])
    stone = b.one_minus(b.smoothstep(b.madd(sg, 0.12, 0.2), b.madd(sg, 0.14, 0.4), stones.outputs['Distance']))
    shown = b.mul(b.mul(stone, I['Aggregate']), b.madd(age, 0.7, b.madd(sr, 0.25, 0.05)))
    col = b.mix_color(shown, binder, b.color_scale(I['Aggregate Color'], b.madd(sr, 0.9, 0.5)))
    rough = b.madd(age, 0.12, b.madd(stone, 0.04, b.sub(I['Roughness'], 0.12)))
    hm = b.madd(stone, b.mul(I['Aggregate'], b.madd(age, 0.8, 0.6)), b.mul(b.sub(sand, 0.5), 0.6))

    # ---- repair patches: rectangles of newer asphalt with a sealed border
    ps, pt, pnw, pnh = plane.grid(1.6)
    px, py = b.div(ps, 1.6), b.div(pt, 1.6)
    pi, pj = plane.wrapped(b.floor(px), pnw), plane.wrapped(b.floor(py), pnh)
    p1, pc = b.white_noise(b.combine(pi, pj, b.add(I['Seed'], 0.31)))
    m0, m1, m2 = b.separate_color(pc)
    fx, fy = b.sub(px, b.floor(px)), b.sub(py, b.floor(py))
    inner = b.minimum(b.minimum(b.sub(fx, b.madd(m0, 0.3, 0.06)), b.sub(b.madd(m1, -0.3, 0.94), fx)),
                      b.minimum(b.sub(fy, b.madd(m2, 0.3, 0.06)), b.sub(b.madd(m0, -0.3, 0.94), fy)))
    inner = b.mul(inner, 1.6)  # distance into the patch (pattern units)
    patched = b.mul(b.math('LESS_THAN', p1, b.mul(I['Patches'], 0.45)), b.smoothstep(0.0, 0.006, inner))
    border = b.mul(patched, b.one_minus(b.smoothstep(0.0, b.madd(sand, 0.03, 0.025), inner)))
    col = b.mix_color(patched, col, b.color_scale(b.mix_color(b.mul(shown, 0.35), I['Asphalt Color'],
                                                              I['Aggregate Color']), b.madd(m1, 0.6, 0.7)))
    col = b.mix_color(b.mul(border, 0.9), col, TAR)
    rough = b.madd(patched, -0.06, rough)
    rough = b.mix(border, rough, 0.4)
    h = b.madd(patched, 0.012, h)
    old = b.one_minus(patched)  # where the old surface (with its cracks and markings) still is

    # ---- painted markings
    lane, lw = I['Lane Width'], I['Line Width']
    hw = b.mul(lw, 0.5)
    ms, mt, _mnw, _mnh = plane.grid(lane, lane, 1.0, 2.0)
    xs = b.sub(b.wrap(ms, lane), b.mul(lane, 0.5))  # from the middle of a lane

    def line(distance, width=hw):  # 1 within `width` of 0
        return b.one_minus(b.smoothstep(b.mul(width, 0.92), b.mul(width, 1.08), b.absolute(distance)))
    solid = line(xs)
    dashed = b.mul(solid, b.math('LESS_THAN', b.fract(b.div(mt, lane)), 0.45))
    double = line(b.sub(b.absolute(xs), lw))
    bar = b.mul(lw, 8.0)
    cs, _ct, _cnw, _cnh = plane.grid(bar, lane)
    cross = b.mul(b.math('LESS_THAN', b.fract(b.div(cs, bar)), 0.5),
                  line(b.sub(b.wrap(mt, lane), b.mul(lane, 0.5)), b.mul(lane, 0.3)))
    side = b.sub(b.mul(lane, 0.5), b.absolute(xs))  # to the edge of a bay
    row = b.wrap(mt, b.mul(lane, 2.0))
    bays = b.maximum(line(side), line(b.minimum(row, b.sub(b.mul(lane, 2.0), row))))
    hatch_w = b.mul(lw, 6.0)
    hs, ht, _hnw, _hnh = plane.grid(hatch_w)
    hatch = b.math('LESS_THAN', b.fract(b.div(b.add(hs, ht), hatch_w)), 0.35)
    marking = 0.0
    for index, shape in enumerate((solid, dashed, double, cross, bays, hatch), 1):
        marking = b.mix(b.math('COMPARE', I['Marking'], float(index), 0.5), marking, shape)
    paint_z = S.znoise(55.0, 5, detail=3.0, roughness=0.6, label='Paint Wear')
    worn_off = F.cover(b, b.madd(stone, -0.9, b.madd(cloud, 0.6, paint_z)), b.mul(I['Marking Wear'], 0.75), 0.35)
    marking = b.mul(b.mul(marking, old), b.one_minus(worn_off))
    col = b.mix_color(marking, col, b.color_scale(I['Marking Color'], b.madd(cloud, 0.05, b.madd(sand, 0.2, 0.9))))
    rough = b.mix(marking, rough, 0.6)
    h = b.madd(marking, 0.012, h)
    hm = b.madd(b.mul(marking, hm), -0.5, hm)

    # ---- cracks: long ones, alligator cracking, tar sealant
    scale = I['Crack Scale']
    crack_d = F.crack_distance(b, S, scale, 6)
    crack_on = F.cover(b, S.znoise(b.mul(scale, 0.5), 8, detail=3.0, roughness=0.6, label='Crack Areas'),
                       b.mul(I['Cracks'], 0.85), 0.5)
    width = b.madd(cloud, 0.002, 0.006)
    crack = b.mul(b.mul(b.one_minus(b.smoothstep(b.mul(width, 0.4), width, crack_d)), crack_on), old)
    fine_d = F.crack_distance(b, S, b.mul(scale, 9.0), 9, label='Alligator Cracks')
    fine_on = F.cover(b, b.madd(crack, 1.5, S.znoise(b.mul(scale, 0.7), 11, detail=3.0, roughness=0.6,
                                                     label='Alligator Areas')), b.mul(I['Alligator Cracks'], 0.6), 0.3)
    fine = b.mul(b.mul(b.one_minus(b.smoothstep(0.004, 0.012, fine_d)), fine_on), old)
    sealed = b.mul(b.mul(b.one_minus(b.smoothstep(0.012, 0.02, b.madd(sand, 0.01, crack_d))), crack_on),
                   b.mul(old, I['Crack Sealant']))
    open_crack = b.mul(b.maximum(crack, fine), b.one_minus(sealed))
    col = b.color_scale(col, b.madd(open_crack, -0.8, 1.0))
    h = b.madd(open_crack, -0.3, b.madd(fine_on, -0.02, h))
    col = b.mix_color(sealed, col, TAR)
    rough = b.mix(sealed, rough, 0.3)
    h = b.madd(sealed, 0.01, h)
    hm = b.madd(b.mul(sealed, hm), -0.8, hm)

    # ---- potholes: ragged holes down to the gravel bed
    holes = S.voronoi(0.9, 12, label='Potholes')
    hr, hg, _hb = b.separate_color(holes.outputs['Color'])
    ragged = S.znoise(14.0, 13, detail=4.0, roughness=0.65, label='Pothole Edge')
    reach = b.madd(ragged, 0.03, b.madd(hg, 0.14, 0.1))
    depth = b.mul(b.one_minus(b.smoothstep(b.mul(reach, 0.55), reach, holes.outputs['Distance'])),
                  b.math('LESS_THAN', hr, b.mul(I['Potholes'], 0.6)))
    rim = b.mul(b.one_minus(b.smoothstep(reach, b.mul(reach, 1.5), holes.outputs['Distance'])),
                b.math('LESS_THAN', hr, b.mul(I['Potholes'], 0.6)))
    col = b.color_scale(col, b.madd(b.mul(rim, b.clamp01(b.madd(fine_d, -40.0, 1.0))), -0.5, 1.0))
    col = b.mix_color(depth, col, b.color_scale(BASE, b.madd(sr, 0.8, b.madd(ragged, 0.1, 0.55))))
    rough = b.mix(depth, rough, 0.95)
    h = b.madd(depth, -0.4, h)
    hm = b.madd(depth, b.madd(stone, 1.2, 0.0), hm)

    # ---- loose gravel
    pebbles = S.voronoi(b.div(0.4, I['Aggregate Size']), 14, label='Gravel')
    gr, gg, gb = b.separate_color(pebbles.outputs['Color'])
    gravel_on = F.cover(b, b.madd(depth, 2.0, b.madd(cloud, 0.8, b.mul(bumps, -0.6))), I['Gravel'], 0.5)
    pebble = b.mul(b.one_minus(b.smoothstep(0.3, b.madd(gg, 0.15, 0.48), pebbles.outputs['Distance'])),
                   b.mul(gravel_on, b.math('LESS_THAN', gb, b.madd(gravel_on, 0.75, 0.2))))
    dusty = b.mul(gravel_on, b.mul(I['Gravel'], 0.8))  # the fines between the pebbles
    col = b.mix_color(dusty, col, b.color_scale(I['Aggregate Color'], b.madd(sand, 0.3, 0.45)))
    pebble_col = b.mix_color(b.mul(gg, 0.5), I['Aggregate Color'], BASE)
    col = b.mix_color(pebble, col, b.color_scale(pebble_col, b.madd(gr, 1.1, 0.5)))
    rough = b.mix(b.maximum(pebble, dusty), rough, 0.92)
    h = b.madd(pebble, 0.2, h)

    # ---- dust, sand, dirt
    dirt_z = S.znoise(1.1, 15, detail=5.0, roughness=0.65, label='Dirt')
    dirt = F.cover(b, b.madd(open_crack, 1.5, b.madd(bumps, -0.5, dirt_z)), I['Dirt'], 0.7)
    dirt = b.mul(dirt, b.one_minus(b.mul(pebble, 0.6)))
    clods = S.znoise(30.0, 16, detail=4.0, roughness=0.65, label='Clods')
    col = b.mix_color(dirt, col, b.color_scale(I['Dirt Color'], b.madd(clods, 0.08, b.madd(dirt_z, 0.07, 1.0))))
    rough = b.mix(dirt, rough, 0.95)
    hm = b.mix(dirt, hm, b.madd(clods, 0.5, b.mul(b.sub(sand, 0.5), 0.8)))
    h = b.madd(dirt, b.madd(clods, 0.012, 0.01), h)

    # ---- stains: oil, tire marks
    oil_z = S.znoise(1.4, 17, detail=3.0, roughness=0.5, distortion=1.2, label='Oil')
    oil = F.cover(b, oil_z, b.mul(I['Oil Stains'], 0.2), 0.35)
    col = b.color_scale(col, b.madd(oil, -0.6, 1.0))
    rough = b.madd(oil, -0.3, rough)
    tire_aniso = (1.0, 1.0 / 40.0) if tile else (1.0, 1.0 / 40.0, 1.0)
    tire_z = S.znoise(11.0, 18, detail=3.0, roughness=0.6, aniso=tire_aniso, label='Tire Marks')
    tire_on = F.cover(b, S.znoise(1.6, 19, detail=2.0, aniso=tire_aniso, label='Tire Mark Runs'), 0.55, 0.5,
                      gate=False)
    tires = b.mul(b.mul(F.cover(b, tire_z, b.mul(I['Tire Marks'], 0.45), 0.3), tire_on),
                  b.madd(stone, 0.3, 0.65))
    col = b.mix_color(tires, col, TAR)
    rough = b.madd(tires, -0.08, rough)

    # ---- water: puddles in the dips, wetness
    low = b.madd(b.sub(level, h), 18.0, b.madd(bumps, -0.85, b.mul(cloud, 0.3)))  # high in dips and holes
    puddle = F.cover(b, low, b.mul(I['Puddles'], 0.4), 0.12)
    wet = b.maximum(I['Wetness'], b.smoothstep(0.0, 0.5, puddle))
    col = b.color_scale(col, b.madd(wet, -0.45, 1.0))
    rough = b.mix(wet, rough, b.madd(stone, 0.12, 0.2))
    col = b.mix_color(b.mul(puddle, 0.85), col, WATER)
    rough = b.mix(puddle, rough, 0.02)

    C.finish(b, gout, I, col, 0.0, rough, b.clamp01(h), hm, distance=ROAD_BUMP, cover=(puddle, 0.55))


SPEC = dict(
    label='Road', category='ROAD', params=ROAD_PARAMS, outputs=C.COMMON_OUTPUTS, build=build_road,
    display=('Asphalt Color', 0.0, 'Roughness'), bump=ROAD_BUMP, fit=0.3,
)
