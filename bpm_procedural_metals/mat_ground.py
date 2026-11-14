# SPDX-License-Identifier: GPL-3.0-or-later
"""Ground generator: soil, mud, sand, gravel, rock, forest floor, snow and ice.

Layers, bottom to top: soil (clods, grain, gentle hills); bare rock (strata,
cracks); dried mud cracks; wind ripples; pebbles of two sizes, up to a gravel
bed; moss and low plants; fallen leaves; snow (fills the hollows first, then
covers everything); vehicle tracks pressed into whatever is on top; ice with
cracks, bubbles and frost; puddles and wetness.

Every layer updates all channels right away, so finished layers don't keep
their masks on Cycles' shader stack.  The Displacement output moves the surface
itself when 'Real Displacement' is turned up.
"""

from . import features as F
from . import gencommon as C
from .nodebuilder import TAU

GROUND_BUMP = 0.08  # relief depth of the full 0..1 height range (meters at Scale 1)

LEAF_GOLD = (0.38, 0.22, 0.03)
LEAF_BROWN = (0.07, 0.035, 0.015)
FROST = (0.66, 0.70, 0.75)

GROUND_PARAMS = [
    # -- Soil
    C.color('Soil Color', (0.085, 0.058, 0.036), 'Soil', 'Color of the soil, sand or mud', key=True),
    C.fac('Color Variation', 0.4, 'Soil', 'Patchy, uneven color'),
    C.fac('Roughness', 0.9, 'Soil', '0 = glossy, 1 = rough and dull'),
    C.fac('Clumps', 0.5, 'Soil', 'Lumpy clods of earth', key=True),
    C.fac('Grain', 0.6, 'Soil', 'Fine grain of sand'),
    C.fac('Hills', 0.3, 'Soil', 'Gentle humps and hollows (where water and snow collect)'),
    # -- Stones
    C.fac('Pebbles', 0.2, 'Stones', 'Scattered stones (1 = a gravel bed)', key=True),
    C.Param('Pebble Size', 'FLOAT', 0.03, 0.002, 2.0, 'Stones', 'Size of the biggest pebbles', subtype='DISTANCE'),
    C.color('Pebble Color', (0.20, 0.19, 0.17), 'Stones', 'Color of the pebbles (each one varies)'),
    C.fac('Smooth Pebbles', 0.2, 'Stones', 'Rounded, glossy pebbles washed by water'),
    C.fac('Rock', 0.0, 'Stones', 'Bare rock showing through (1 = solid rock)', key=True),
    C.color('Rock Color', (0.17, 0.16, 0.15), 'Stones', 'Color of the rock'),
    C.fac('Strata', 0.4, 'Stones', 'Layers of sediment in the rock: bands and ledges'),
    C.fac('Rock Cracks', 0.4, 'Stones', 'Cracks and joints in the rock'),
    # -- Sand and mud
    C.fac('Ripples', 0.0, 'Sand and Mud', 'Wind or water ripples in sand', key=True),
    C.Param('Ripple Size', 'FLOAT', 0.07, 0.005, 5.0, 'Sand and Mud', 'Distance from ripple to ripple',
            subtype='DISTANCE'),
    C.fac('Mud Cracks', 0.0, 'Sand and Mud', 'Dried mud cracked into plates', key=True),
    C.Param('Crack Size', 'FLOAT', 0.12, 0.01, 5.0, 'Sand and Mud', 'Size of the mud plates (and of the ice cracks)',
            subtype='DISTANCE'),
    C.fac('Tracks', 0.0, 'Sand and Mud', 'Vehicle tracks with tread marks, pressed in along Y', key=True),
    C.Param('Track Width', 'FLOAT', 0.22, 0.02, 3.0, 'Sand and Mud', 'Width of one track', subtype='DISTANCE'),
    # -- Cover
    C.fac('Moss', 0.0, 'Cover', 'Moss and low plants', key=True),
    C.color('Moss Color', (0.045, 0.085, 0.018), 'Cover', 'Color of the moss'),
    C.fac('Leaves', 0.0, 'Cover', 'Fallen leaves', key=True),
    C.color('Leaf Color', (0.26, 0.085, 0.02), 'Cover', 'Color of the leaves (they vary from gold to brown)'),
    C.Param('Leaf Size', 'FLOAT', 0.05, 0.005, 1.0, 'Cover', 'Size of the leaves', subtype='DISTANCE'),
    C.fac('Snow', 0.0, 'Cover', 'Snow: first in the hollows, then over everything', key=True),
    C.color('Snow Color', (0.62, 0.65, 0.70), 'Cover', 'Color of the snow'),
    C.fac('Ice', 0.0, 'Cover', 'Ice: frozen puddles, then a sheet of ice over everything', key=True),
    C.color('Ice Color', (0.10, 0.19, 0.22), 'Cover', 'Color of the ice'),
    # -- Water
    C.fac('Puddles', 0.0, 'Water', 'Water standing in the hollows', key=True),
    C.color('Water Color', (0.045, 0.035, 0.022), 'Water', 'Color of the water (muddy by default)'),
    C.fac('Wetness', 0.0, 'Water', 'Wet ground: darker and shiny', key=True),
    C.DISPLACE_PARAM,
] + C.PATTERN_PARAMS


def build_ground(b, I, gout, tile):
    S = F.Space(b, tile, I['Scale'], I['Seed'], I['Tile Size'] if tile else 1.0)
    span = b.mul(I['Tile Size'], I['Scale']) if tile else None
    plane = F.Plane(b, S, span)

    # ---- soil
    hills = S.znoise(0.45, 1, detail=3.0, roughness=0.5, label='Hills')
    level = b.madd(hills, b.mul(I['Hills'], 0.1), 0.45)  # the smooth ground: water, snow and ice lie on it
    patches = S.znoise(1.3, 2, detail=5.0, roughness=0.65, label='Patches')
    clods = S.znoise(22.0, 3, detail=4.0, roughness=0.65, label='Clods')
    sand = S.noise(300.0, 4, detail=2.0, roughness=0.5, label='Grain')
    grain = b.mul(b.sub(sand, 0.5), I['Grain'])
    col = b.color_scale(I['Soil Color'], b.madd(patches, b.mul(I['Color Variation'], 0.14),
                                                 b.madd(clods, b.mul(I['Clumps'], 0.1), b.madd(grain, 0.5, 1.0))))
    rough = b.madd(patches, 0.02, I['Roughness'])
    h = b.madd(clods, b.mul(I['Clumps'], 0.035), level)
    hm = b.mul(grain, 1.5)

    # ---- bare rock: strata, blocky relief, cracks
    strata_aniso = (0.05, 1.0) if tile else (0.05, 0.05, 1.0)
    bands = S.znoise(7.0, 5, detail=4.0, roughness=0.7, aniso=strata_aniso, label='Strata')
    blocks = S.znoise(2.5, 6, detail=6.0, roughness=0.72, label='Rock Relief')
    rock_d = F.crack_distance(b, S, 3.0, 7, label='Rock Cracks')
    joint = b.mul(b.one_minus(b.smoothstep(0.004, b.madd(blocks, 0.006, 0.03), rock_d)), I['Rock Cracks'])
    rock = F.cover(b, b.madd(blocks, 0.5, b.madd(hills, 0.6, patches)), I['Rock'], 0.2)
    strata = I['Strata']
    rock_col = b.color_scale(I['Rock Color'], b.madd(bands, b.mul(strata, 0.2), b.madd(blocks, 0.1, 1.0)))
    rock_col = b.color_scale(rock_col, b.madd(joint, -0.7, b.madd(grain, 0.25, 1.0)))
    rock_h = b.madd(b.smoothstep(-0.4, 0.4, bands), b.mul(strata, 0.08), b.madd(blocks, 0.07, b.add(level, 0.08)))
    col = b.mix_color(rock, col, rock_col)
    rough = b.mix(rock, rough, b.madd(blocks, 0.03, 0.8))
    h = b.mix(rock, h, b.madd(joint, -0.1, rock_h))
    soil = b.one_minus(rock)

    # ---- dried mud: plates with curled edges between cracks
    cracks = I['Mud Cracks']
    plate_d = F.crack_distance(b, S, b.div(1.0, I['Crack Size']), 9, warp=0.25, label='Mud Cracks')
    gap = b.mul(b.mul(b.one_minus(b.smoothstep(0.02, b.madd(clods, 0.012, 0.07), plate_d)), cracks), soil)
    curl = b.mul(b.mul(b.smoothstep(0.05, 0.3, plate_d), b.one_minus(b.smoothstep(0.3, 0.5, plate_d))),
                 b.mul(cracks, soil))  # the plates dish: their rims stand a little higher
    col = b.color_scale(col, b.madd(gap, -0.7, b.madd(b.mul(cracks, soil), 0.12, b.madd(curl, -0.05, 1.0))))
    h = b.madd(gap, -0.18, b.madd(curl, -0.02, h))

    # ---- ripples
    size = I['Ripple Size']
    wave_warp = S.znoise(b.div(0.25, size), 11, detail=2.0, roughness=0.5, label='Ripple Warp')
    if tile:
        count = b.maximum(1.0, b.math('ROUND', b.div(span, size)))
        phase = b.madd(S.u, count, b.mul(wave_warp, 0.45))
    else:
        phase = b.madd(wave_warp, 0.45, b.div(b.separate(S.P)[0], size))
    wave = b.math('SINE', b.mul(phase, TAU))
    crest = b.madd(b.absolute(wave), -1.0, 1.0)  # sharp crests, round troughs
    rippled = b.mul(I['Ripples'], soil)
    h = b.madd(b.sub(0.5, crest), b.mul(rippled, 0.09), h)
    col = b.color_scale(col, b.madd(b.sub(0.5, crest), b.mul(rippled, 0.16), 1.0))

    # ---- pebbles: big ones, and small ones between them when there are many
    amount = I['Pebbles']
    smooth = I['Smooth Pebbles']
    for index, (size_factor, share, lift) in enumerate(((2.6, 0.7, 0.06), (1.0, 1.0, 0.16))):
        stones = S.voronoi(b.div(size_factor, I['Pebble Size']), 12 + index, label='Pebbles')
        pr, pg, pb = b.separate_color(stones.outputs['Color'])
        present = b.math('LESS_THAN', pr, b.mul(amount, share) if index else b.madd(amount, 1.4, -0.5))
        reach = b.madd(pg, 0.2, 0.26)
        ratio = b.div(stones.outputs['Distance'], reach)
        dome = b.mul(b.math('SQRT', b.clamp01(b.sub(1.0, b.mul(ratio, ratio)))), present)
        pebble = b.mul(b.smoothstep(0.0, 0.25, dome), present)
        tint = b.mix_color(b.mul(pb, 0.6), I['Pebble Color'], b.color_scale(I['Soil Color'], 2.2))
        col = b.mix_color(pebble, col, b.color_scale(tint, b.madd(pg, 1.0, b.madd(grain, 0.3, 0.45))))
        rough = b.mix(pebble, rough, b.madd(smooth, -0.5, 0.85))
        h = b.madd(dome, lift, h)
        hm = b.mul(hm, b.madd(b.mul(pebble, smooth), -0.9, 1.0))

    # ---- moss and low plants
    moss_z = S.znoise(1.5, 14, detail=5.0, roughness=0.65, label='Moss')
    tufts = S.znoise(60.0, 15, detail=3.0, roughness=0.7, label='Moss Tufts')
    moss = F.cover(b, b.madd(b.sub(h, level), -6.0, b.madd(tufts, 0.15, moss_z)), I['Moss'], 0.3)
    col = b.mix_color(moss, col, b.color_scale(I['Moss Color'], b.madd(tufts, 0.22, b.madd(moss_z, 0.1, 1.0))))
    rough = b.mix(moss, rough, 0.95)
    h = b.madd(moss, b.madd(tufts, 0.01, 0.03), h)
    hm = b.mix(moss, hm, b.mul(tufts, 0.8))

    # ---- fallen leaves: two layers, lying crosswise
    for index, aniso in enumerate(((1.0, 1.9), (1.9, 1.0))):
        leaves = S.voronoi(b.div(0.75, I['Leaf Size']), 16 + index, aniso=aniso if tile else aniso + (1.4,),
                           label='Leaves')
        lr, lg, lb = b.separate_color(leaves.outputs['Color'])
        leaf = b.mul(b.one_minus(b.smoothstep(0.4, 0.47, leaves.outputs['Distance'])),
                     b.math('LESS_THAN', lr, b.mul(I['Leaves'], 0.95)))
        leaf_col = b.mix_color(lg, b.mix_color(b.smoothstep(0.5, 1.0, lb), I['Leaf Color'], LEAF_GOLD), LEAF_BROWN)
        vein = b.smoothstep(0.0, 0.4, leaves.outputs['Distance'])  # darker towards the rim
        col = b.mix_color(leaf, col, b.color_scale(leaf_col, b.madd(vein, -0.35, 1.1)))
        rough = b.mix(leaf, rough, 0.7)
        h = b.madd(leaf, b.madd(vein, -0.015, 0.035), h)
        hm = b.mul(hm, b.madd(leaf, -0.8, 1.0))

    # ---- snow: in the hollows first, then over everything, smoothing what it covers
    drift = S.znoise(0.9, 18, detail=3.0, roughness=0.5, label='Snow Drifts')
    snow = F.cover(b, b.madd(b.sub(h, level), -9.0, b.madd(hills, -0.5, drift)), I['Snow'], 0.25)
    sparkle = b.smoothstep(0.72, 0.8, S.noise(900.0, 19, detail=1.0, roughness=0.5, label='Sparkle'))
    col = b.mix_color(snow, col, b.color_scale(I['Snow Color'], b.madd(drift, 0.03, 1.0)))
    rough = b.mix(snow, rough, b.madd(sparkle, -0.45, 0.62))
    h = b.mix(snow, h, b.madd(b.sub(h, level), 0.35, b.madd(drift, 0.02, b.add(level, 0.06))))
    hm = b.mix(snow, hm, b.mul(b.sub(sand, 0.5), 0.5))

    # ---- vehicle tracks pressed into the ground
    spacing = b.mul(I['Track Width'], 5.0)
    ts, tt, _tnw, _tnh = plane.grid(spacing, I['Track Width'])
    across = b.sub(b.wrap(b.madd(drift, b.mul(I['Track Width'], 0.25), ts), spacing), b.mul(spacing, 0.5))
    off = b.div(b.absolute(across), b.mul(I['Track Width'], 0.5))  # 0 in the middle of a track, 1 at its edge
    track = b.mul(b.one_minus(b.smoothstep(0.85, 1.0, off)), I['Tracks'])
    berm = b.mul(b.mul(b.smoothstep(0.85, 1.05, off), b.one_minus(b.smoothstep(1.05, 1.5, off))), I['Tracks'])
    lug = b.math('LESS_THAN', b.fract(b.add(b.div(tt, I['Track Width']), b.mul(off, 0.35))), 0.5)
    h = b.madd(track, b.madd(lug, -0.14, -0.16), b.madd(berm, 0.07, h))
    col = b.color_scale(col, b.madd(track, b.madd(snow, 0.18, b.madd(lug, -0.12, -0.3)), 1.0))
    rough = b.madd(b.mul(track, b.one_minus(snow)), -0.12, rough)
    hm = b.mul(hm, b.madd(track, -0.5, 1.0))

    # ---- ice: frozen puddles first, with cracks, bubbles and frost
    low = b.madd(b.sub(level, h), 9.0, b.madd(hills, -0.9, b.mul(patches, 0.3)))  # high in the hollows
    ice = F.cover(b, low, I['Ice'], 0.08)
    ice_d = F.crack_distance(b, S, b.div(0.35, I['Crack Size']), 20, warp=0.6, label='Ice Cracks')
    fracture = b.one_minus(b.smoothstep(0.0, 0.012, ice_d))
    glow = b.mul(b.one_minus(b.smoothstep(0.0, 0.12, ice_d)), 0.35)  # the cracks show as sheets inside the ice
    bubbles = S.voronoi(170.0, 22, label='Bubbles')
    ur, ug, _ub = b.separate_color(bubbles.outputs['Color'])
    bubble = b.mul(b.one_minus(b.smoothstep(0.1, b.madd(ug, 0.2, 0.15), bubbles.outputs['Distance'])),
                   b.math('LESS_THAN', ur, b.clamp01(b.madd(patches, 0.25, 0.3))))
    frost = F.cover(b, b.madd(clods, 0.4, drift), 0.3, 0.6, gate=False)
    white = b.clamp01(b.maximum(b.maximum(fracture, glow), b.maximum(b.mul(bubble, 0.7), b.mul(frost, 0.6))))
    col = b.mix_color(ice, col, b.mix_color(white, b.color_scale(I['Ice Color'], b.madd(patches, 0.12, 1.0)), FROST))
    rough = b.mix(ice, rough, b.madd(frost, 0.4, b.madd(fracture, 0.2, 0.05)))

    # ---- water: puddles in the hollows, wetness
    puddle = b.mul(F.cover(b, low, b.mul(I['Puddles'], 0.55), 0.1), b.one_minus(ice))
    wet = b.mul(b.maximum(I['Wetness'], b.smoothstep(0.0, 0.5, puddle)), b.one_minus(b.maximum(snow, ice)))
    col = b.color_scale(col, b.madd(wet, -0.4, 1.0))
    rough = b.mix(wet, rough, b.madd(sand, 0.2, 0.25))
    col = b.mix_color(b.mul(puddle, 0.9), col, I['Water Color'])
    rough = b.mix(puddle, rough, 0.02)
    flat = b.maximum(ice, puddle)

    C.finish(b, gout, I, col, 0.0, rough, b.clamp01(h), hm, distance=GROUND_BUMP, cover=(flat, level),
             displace=I['Real Displacement'])


SPEC = dict(
    label='Ground', category='GROUND', params=GROUND_PARAMS, outputs=C.COMMON_OUTPUTS + C.DISPLACE_OUTPUTS,
    build=build_ground, display=('Soil Color', 0.0, 'Roughness'), bump=GROUND_BUMP, fit=0.4,
)
