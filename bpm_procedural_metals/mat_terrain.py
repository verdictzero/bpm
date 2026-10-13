# SPDX-License-Identifier: GPL-3.0-or-later
"""Terrain generators: cratered ground (lunar surface, asteroids, shell-cratered
battlefields, rocky desert) and lava (molten, crusting, cooled pahoehoe and aa,
basalt, obsidian, magma).

Craters come in three sizes.  Each size is a Voronoi field: one possible crater
per cell, with a bowl, a raised rim, an ejecta blanket and (for the biggest
ones) a central peak and bright rays.  The Voronoi pattern is 3D in object
mode, so craters stay round on any surface (spheres, rocks), and 4D on a torus
for seamless tiles.  Every crater stays inside its cell, so the height never jumps.

Both generators have a Displacement output: with 'Real Displacement' turned up
the surface itself moves (craters get real depth and silhouettes) and the big
relief leaves the bump.  The Height output always holds all of the relief, for
baked height / displacement maps.

Every layer updates all channels right away, so finished layers don't keep
their masks on Cycles' shader stack.
"""

from . import features as F
from . import gencommon as C

TERRAIN_BUMP = 0.6  # relief depth of the full 0..1 height range (meters at Scale 1)
LAVA_BUMP = 0.25

SOOT = (0.012, 0.011, 0.010)
WATER = (0.035, 0.032, 0.024)
SULFUR = (0.72, 0.60, 0.07)
ASH = (0.30, 0.29, 0.28)

TERRAIN_PARAMS = [
    # -- Ground
    C.color('Ground Color', (0.16, 0.155, 0.15), 'Ground', 'Color of the dust and soil', key=True),
    C.fac('Color Variation', 0.4, 'Ground', 'Patchy, uneven color', key=True),
    C.fac('Dark Patches', 0.0, 'Ground', 'Big smooth areas of darker ground, like the lunar seas (maria)',
          key=True),
    C.color('Patch Color', (0.075, 0.073, 0.07), 'Ground', 'Color of the dark patches'),
    C.fac('Roughness', 0.92, 'Ground', '0 = glossy, 1 = rough and dull'),
    C.fac('Regolith', 0.6, 'Ground', 'Fine dusty grain all over'),
    C.fac('Hills', 0.3, 'Ground', 'Gentle rolling hills and dips', key=True),
    C.Param('Hill Size', 'FLOAT', 4.0, 0.1, 100.0, 'Ground', 'Width of the hills', subtype='DISTANCE'),
    C.fac('Metal Flecks', 0.0, 'Ground', 'Grains of metal (nickel-iron): metal asteroids, meteorites'),
    C.color('Metal Color', (0.53, 0.50, 0.46), 'Ground', 'Color of the metal grains'),
    # -- Craters
    C.fac('Craters', 0.6, 'Craters', 'How many craters', key=True),
    C.Param('Crater Size', 'FLOAT', 0.6, 0.01, 100.0, 'Craters', 'Radius of the biggest craters',
            subtype='DISTANCE', key=True),
    C.fac('Small Craters', 0.7, 'Craters', 'How many smaller craters fill the spaces in between', key=True),
    C.scale('Crater Depth', 1.0, 0.0, 3.0, 'Craters', 'Depth of the bowls (1 = like real impact craters)'),
    C.scale('Rim Height', 1.0, 0.0, 3.0, 'Craters', 'Height of the raised rims'),
    C.fac('Central Peaks', 0.3, 'Craters', 'Mountains in the middle of the biggest craters'),
    C.fac('Crater Age', 0.4, 'Craters', '0 = fresh and sharp, 1 = old, worn down and filled with dust'),
    C.fac('Ejecta', 0.5, 'Craters', 'Bright blankets of thrown-out material around fresh craters'),
    C.fac('Rays', 0.2, 'Craters', 'Bright streaks radiating from the biggest fresh craters'),
    # -- Rocks
    C.fac('Boulders', 0.2, 'Rocks', 'Scattered rocks and boulders', key=True),
    C.Param('Boulder Size', 'FLOAT', 0.08, 0.005, 10.0, 'Rocks', 'Size of the biggest rocks', subtype='DISTANCE'),
    C.fac('Bedrock', 0.0, 'Rocks', 'Bare, cracked rock showing through the dust'),
    C.color('Rock Color', (0.12, 0.115, 0.11), 'Rocks', 'Color of the rocks (each one varies)'),
    # -- Weathering
    C.fac('Scorch', 0.0, 'Weathering', 'Blackened, burnt craters (explosions)'),
    C.fac('Puddles', 0.0, 'Weathering', 'Water in the bottoms of the craters'),
    C.fac('Wetness', 0.0, 'Weathering', 'Wet ground: darker and shinier'),
    C.DISPLACE_PARAM,
] + C.PATTERN_PARAMS

LAVA_PARAMS = [
    # -- Heat
    C.fac('Heat', 0.8, 'Heat', '0 = cold rock, 1 = glowing hot', key=True),
    C.Param('Temperature', 'FLOAT', 1400.0, 800.0, 2500.0, 'Heat',
            'Color of the glow (kelvin): ~1000 dark red, ~1350 orange, ~1600+ yellow', key=True),
    C.Param('Emission Strength', 'FLOAT', 1.5, 0.0, 200.0, 'Heat', 'Brightness of the glow', key=True),
    C.fac('Heat Variation', 0.5, 'Heat', 'Hotter and cooler swirls in the molten lava'),
    C.fac('Turbulence', 0.5, 'Heat', 'How much the molten lava swirls and churns'),
    # -- Crust
    C.fac('Crust', 0.5, 'Crust', 'How much of the surface has cooled into a dark crust', key=True),
    C.color('Crust Color', (0.035, 0.032, 0.030), 'Crust', 'Color of the cooled rock'),
    C.Param('Plate Size', 'FLOAT', 0.5, 0.01, 20.0, 'Crust', 'Size of the crust plates', subtype='DISTANCE',
            key=True),
    C.fac('Crack Width', 0.3, 'Crust', 'Width of the glowing cracks between the plates'),
    C.fac('Crust Roughness', 0.8, 'Crust', 'Roughness of the cooled rock'),
    C.fac('Glassy', 0.0, 'Crust', 'Shiny glassy skin (fresh pahoehoe, obsidian)'),
    # -- Flow
    C.axis('Flow Direction', (1.0, 0.0, 0.0), 'Flow', 'Direction the lava flows (tiles: along U)'),
    C.scale('Flow Stretch', 2.0, 1.0, 10.0, 'Flow', 'How much the pattern stretches along the flow'),
    C.fac('Ropes', 0.0, 'Flow', 'Rope-like folds of pahoehoe lava, across the flow', key=True),
    C.Param('Rope Size', 'FLOAT', 0.06, 0.005, 2.0, 'Flow', 'Spacing of the ropes', subtype='DISTANCE'),
    C.fac('Clinker', 0.0, 'Flow', 'Rough, jagged rubble of aa lava', key=True),
    # -- Rock
    C.fac('Vesicles', 0.2, 'Rock', 'Gas bubble holes in the rock'),
    C.fac('Sulfur', 0.0, 'Rock', 'Yellow sulfur deposits in cracks and hollows'),
    C.fac('Ash', 0.0, 'Rock', 'Gray volcanic ash dusting the high points'),
    C.DISPLACE_PARAM,
] + C.PATTERN_PARAMS

TERRAIN_OUTPUTS = C.COMMON_OUTPUTS + C.DISPLACE_OUTPUTS
LAVA_OUTPUTS = C.COMMON_OUTPUTS + C.DISPLACE_OUTPUTS + C.EMISSION_OUTPUTS


# ------------------------------------------------------------------ craters
CRATER_RANDOMNESS = 0.65


def _crater_size(b, S, freq, offset, density, depth, rim, age, peaks, rays, label):
    """One size of craters.  Returns (height, fresh_outside, inside) in height units / masks.

    `freq` is cells per pattern unit; a crater's radius is 0.18..0.45 of a cell.
    Each crater (with its rim, ejecta and rays) is kept inside the circle around
    its cell's center that touches the nearest other center: that circle lies
    inside the cell, so nothing is ever cut off at the cell's border.
    """
    vec, w = S.sample(freq, offset)
    # fairly even cells: every crater gets room (the gaps are filled by the next size)
    cells = b.voronoi_node(vec, w=w, randomness=CRATER_RANDOMNESS, dims=S.dims, label=label)
    center = cells.outputs['Position']
    at_center = b.voronoi_node(center, w=cells.outputs['W'] if S.tile else None, feature='F2',
                               randomness=CRATER_RANDOMNESS, dims=S.dims, label=label + ' Room')
    room = b.mul(at_center.outputs['Distance'], 0.5)  # radius of the free circle around the center
    dist = cells.outputs['Distance']
    rr, rg, rb = b.separate_color(cells.outputs['Color'])
    old = b.clamp01(b.madd(rb, 0.7, b.sub(age, 0.35)))
    soft = b.madd(old, 0.5, 0.15)  # old craters have soft, slumped walls
    reach = b.madd(soft, 0.6, 1.3)  # the rim falls off out to this many radii
    radius = b.minimum(b.madd(b.mul(rg, rg), 0.27, 0.18), b.div(room, reach))  # mostly small ones
    x = b.div(dist, radius)  # 0 in the middle, 1 on the rim
    on = b.math('LESS_THAN', rr, density)
    # depth ~ 0.4 x radius (a fifth of the diameter), in units of the height range
    d = b.mul(b.mul(b.div(radius, freq), b.mul(depth, 0.4 / TERRAIN_BUMP)), b.madd(old, -0.5, 1.0))
    r = b.mul(b.mul(d, b.mul(rim, 0.3)), b.madd(old, -0.5, 1.0))
    xi = b.minimum(x, 1.0)
    xi2 = b.mul(xi, xi)
    bowl = b.mul(b.sub(b.mix(b.mul(soft, 1.4), xi2, b.smoothstep(0.0, 1.0, xi)), 1.0), d)  # 0 on the rim
    h = b.add(bowl, b.sub(b.mul(r, b.mul(xi2, xi2)), b.mul(r, b.smoothstep(1.0, reach, x))))
    if peaks is not None:
        h = b.madd(b.mul(b.one_minus(b.smoothstep(0.0, 0.25, x)), b.mul(d, 0.6)), peaks, h)
    inside_room = b.one_minus(b.smoothstep(0.75, 1.0, b.div(dist, room)))
    fresh = b.mul(b.mul(on, b.one_minus(old)), inside_room)
    outside = b.mul(fresh, b.one_minus(b.smoothstep(1.0, 2.2, x)))
    if rays is not None:
        # angular noise around the crater: streaks reaching out to the edge of the free circle
        to_center = b.vmath('SUBTRACT', center, vec)
        if S.tile:
            dw = b.sub(cells.outputs['W'], w)
            norm = b.math('INVERSE_SQRT', b.madd(dw, dw, b.vmath('DOT_PRODUCT', to_center, to_center)))
            streak = b.noise(b.vscale(to_center, b.mul(norm, 6.0)), w=b.madd(dw, b.mul(norm, 6.0), b.mul(rg, 17.0)),
                             detail=3.0, dims='4D', label=label + ' Rays')
        else:
            streak = b.noise(b.vmadd(b.vmath('NORMALIZE', to_center), (6.0, 6.0, 6.0), b.vscale((3.1, 5.3, 7.7), rg)),
                             detail=3.0, label=label + ' Rays')
        ray = b.mul(b.mul(b.smoothstep(0.56, 0.7, streak), b.smoothstep(0.6, 1.2, x)), b.mul(fresh, rays))
        outside = b.maximum(outside, ray)
    inside = b.mul(on, b.one_minus(b.smoothstep(0.85, 1.0, x)))
    return b.mul(h, on), outside, inside


def build_terrain(b, I, gout, tile):
    S = F.Space(b, tile, I['Scale'], I['Seed'], I['Tile Size'] if tile else 1.0)

    # ---- ground: color, dark patches, hills, regolith
    vz = S.znoise(0.35, 1, detail=5.0, roughness=0.6, label='Color Blotches')
    vz2 = S.znoise(2.5, 2, detail=4.0, roughness=0.6, label='Mottling')
    variation = I['Color Variation']
    col = b.color_scale(I['Ground Color'], b.madd(b.madd(vz, 0.16, b.mul(vz2, 0.08)), variation, 1.0))
    mare_z = S.znoise(0.06, 3, detail=3.0, roughness=0.55, label='Dark Patches')
    mare = F.cover(b, mare_z, I['Dark Patches'], 0.35)
    col = b.mix_color(mare, col, b.color_scale(I['Patch Color'], b.madd(vz2, 0.06, 1.0)))
    rough = b.madd(vz2, 0.02, I['Roughness'])
    hill_freq = b.div(1.0, I['Hill Size'])
    hz = S.znoise(hill_freq, 4, detail=4.0, roughness=0.5, label='Hills')
    h = b.madd(b.madd(hz, 0.07, b.mul(mare, -0.06)), I['Hills'], 0.55)
    grain = S.noise(260.0, 5, detail=2.0, roughness=0.6, label='Regolith')
    col = b.color_scale(col, b.madd(b.sub(grain, 0.5), b.mul(I['Regolith'], 0.4), 1.0))
    hm = b.mul(b.sub(grain, 0.5), b.mul(I['Regolith'], 2.0))

    # ---- craters: five sizes, from big ones to pits (fewer on the dark patches, like the lunar seas)
    crater_freq = b.div(1.0, b.mul(I['Crater Size'], 3.0))  # the biggest radius is ~1/3 of a cell
    age = I['Crater Age']
    depth = I['Crater Depth']
    rim = I['Rim Height']
    small = I['Small Craters']
    fresh = 0.0
    inside = 0.0
    for i, (mult, share, offset) in enumerate(((1.0, 0.75, 10), (2.2, 0.85, 11), (4.8, 1.0, 12), (10.5, 1.0, 13), (23.0, 1.0, 14))):
        density = b.mul(I['Craters'], share if i == 0 else b.mul(small, share))
        ch, cf, ci = _crater_size(b, S, b.mul(crater_freq, mult), offset, density, depth, rim,
                                  age if i == 0 else b.clamp01(b.add(age, 0.08 * i)),
                                  I['Central Peaks'] if i == 0 else None, I['Rays'] if i == 0 else None,
                                  'Craters %d' % (i + 1))
        h = b.madd(ch, b.madd(mare, -0.6, 1.0), h)
        fresh = b.maximum(fresh, cf)
        inside = b.maximum(inside, ci)
    ejecta = b.mul(fresh, I['Ejecta'])
    col = b.color_scale(col, b.madd(ejecta, 0.6, 1.0))
    hm = b.mul(hm, b.madd(ejecta, -0.5, 1.0))  # fresh ejecta: finer grain

    # ---- rocks: boulders around, bare bedrock
    rock_freq = b.div(1.0, b.mul(I['Boulder Size'], 2.5))
    rocks = S.voronoi(rock_freq, 20, label='Boulders')
    br, bg, bb = b.separate_color(rocks.outputs['Color'])
    jag = S.noise(b.mul(rock_freq, 5.0), 21, detail=3.0, roughness=0.6, label='Boulder Shape')
    rx = b.div(b.madd(jag, 0.18, rocks.outputs['Distance']), b.madd(bg, 0.22, 0.2))
    boulder_on = b.math('LESS_THAN', br, b.mul(I['Boulders'], b.madd(fresh, 0.6, 0.6)))
    dome = b.mul(b.math('SQRT', b.clamp01(b.one_minus(b.mul(rx, rx)))), boulder_on)
    boulder = b.smoothstep(0.0, 0.25, dome)
    rock_col = b.color_scale(I['Rock Color'], b.madd(bb, 0.8, b.madd(jag, 0.4, 0.4)))
    col = b.mix_color(boulder, col, rock_col)
    rough = b.mix(boulder, rough, b.madd(bb, 0.1, 0.78))
    boulder_h = b.mul(b.div(I['Boulder Size'], TERRAIN_BUMP), b.madd(bg, 0.25, 0.2))
    h = b.madd(dome, boulder_h, h)
    hm = b.madd(boulder, b.sub(jag, 0.5), hm)

    bed_z = S.znoise(b.mul(hill_freq, 3.0), 22, detail=5.0, roughness=0.6, label='Bedrock')
    bed = F.cover(b, b.madd(hz, 0.6, bed_z), I['Bedrock'], 0.25)
    cracks = S.voronoi(b.mul(hill_freq, 25.0), 23, feature='DISTANCE_TO_EDGE', label='Bedrock Cracks')
    crack = b.mul(b.one_minus(b.smoothstep(0.0, 0.06, cracks.outputs['Distance'])), bed)
    bed_col = b.color_scale(I['Rock Color'], b.madd(bed_z, 0.12, 1.0))
    col = b.mix_color(bed, col, bed_col)
    col = b.mix_color(b.mul(crack, 0.7), col, b.color_scale(I['Rock Color'], 0.3))
    rough = b.mix(bed, rough, 0.8)
    h = b.madd(bed, b.madd(bed_z, 0.015, 0.02), h)
    h = b.madd(crack, -0.025, h)

    # ---- metal grains (asteroids)
    flecks = S.noise(120.0, 24, detail=2.0, roughness=0.5, label='Metal Flecks')
    flecks_big = S.znoise(8.0, 25, detail=3.0, roughness=0.6, label='Metal Patches')
    metal = F.cover(b, b.madd(flecks, 6.0, b.mul(flecks_big, 0.6)), I['Metal Flecks'], 0.4, bias=3.0)
    col = b.mix_color(metal, col, b.color_scale(I['Metal Color'], b.madd(flecks, 0.6, 0.7)))
    rough = b.mix(metal, rough, b.madd(flecks, 0.3, 0.25))
    hm = b.madd(metal, 0.3, hm)

    # ---- weathering: scorched craters, puddles in the bowls, wet ground
    scorch = b.mul(b.maximum(inside, b.mul(fresh, 0.7)), I['Scorch'])
    col = b.mix_color(b.mul(scorch, 0.9), col, SOOT)
    level = b.madd(I['Puddles'], 0.22, 0.3)
    has_water = b.clamp01(b.mul(I['Puddles'], 25.0))
    puddle = b.mul(b.one_minus(b.smoothstep(b.sub(level, 0.005), b.add(level, 0.005), h)), has_water)
    damp = b.mul(b.one_minus(b.smoothstep(level, b.add(level, 0.04), h)), has_water)  # wet banks
    wet = b.maximum(b.mul(I['Wetness'], b.smoothstep(-0.8, 1.0, vz)), damp)
    col = b.color_scale(col, b.madd(wet, -0.5, 1.0))
    rough = b.mix(wet, rough, b.mul(rough, 0.35))
    col = b.mix_color(puddle, col, WATER)
    rough = b.mix(puddle, rough, 0.03)
    h = b.mix(puddle, h, level)
    hm = b.mul(hm, b.one_minus(puddle))

    C.finish(b, gout, I, col, b.mul(metal, b.one_minus(puddle)), rough, h, hm, distance=TERRAIN_BUMP,
             displace=I['Real Displacement'])


# --------------------------------------------------------------------- lava
def build_lava(b, I, gout, tile):
    S0 = F.Space(b, tile, I['Scale'], I['Seed'], I['Tile Size'] if tile else 1.0)
    # wobbly coordinates: crust plates with ragged, not straight, edges
    plate_size = I['Plate Size']
    warp_freq = b.div(1.2, plate_size)
    if tile:
        amp = b.div(b.mul(plate_size, 0.1), b.mul(I['Tile Size'], I['Scale']))
        wu = S0.znoise(warp_freq, 11, detail=3.0, roughness=0.55, label='Warp U')
        wv = S0.znoise(warp_freq, 12, detail=3.0, roughness=0.55, label='Warp V')
        S = S0.warped((b.mul(wu, amp), b.mul(wv, amp)))
    else:
        wn = S0.noise(warp_freq, 11, detail=3.0, roughness=0.55, label='Warp').node.outputs['Color']
        wr, wg, wb = b.separate_color(wn)
        warp = b.combine(b.sub(wr, 0.5), b.sub(wg, 0.5), b.sub(wb, 0.5))
        S = S0.warped(b.vscale(warp, b.mul(plate_size, 0.7)))
    stretch = I['Flow Stretch']
    if tile:  # flowing along U
        flow = dict(aniso=(b.div(1.0, stretch), 1.0))
        across = dict(aniso=(4.0, 1.0))
    else:
        direction = F.surface_direction(b, I['Flow Direction'])
        flow = dict(base=F.squashed(b, S.P, direction, stretch))
        across = dict(base=F.squashed(b, S.P, direction, 0.25))

    # ---- molten lava: swirling hot and cooler streaks
    swirl = S.noise(1.2, 1, detail=6.0, roughness=0.55, distortion=b.mul(I['Turbulence'], 2.5),
                    label='Swirls', **flow)
    skin = S.noise(4.0, 2, detail=4.0, roughness=0.6, distortion=b.mul(I['Turbulence'], 1.0),
                   label='Skin', **flow)
    var = I['Heat Variation']
    q = b.clamp01(b.madd(b.madd(b.sub(swirl, 0.5), 3.4, b.mul(b.sub(skin, 0.5), 1.4)), var, 0.72))
    hot = b.clamp01(b.mul(I['Heat'], 3.0))  # cold melt looks like the crust
    col = b.mix_color(b.mul(q, 0.5), (0.05, 0.012, 0.006), (0.12, 0.03, 0.01))
    col = b.mix_color(hot, b.color_scale(I['Crust Color'], 0.6), col)
    rough = b.mix(hot, I['Crust Roughness'], b.madd(skin, 0.2, 0.18))
    h = b.madd(swirl, 0.05, 0.38)
    hm = b.mul(b.sub(skin, 0.5), 0.5)

    # ---- crust: plates floating on the melt, glowing cracks between them
    plate_freq = b.div(1.0, plate_size)
    plates = S.voronoi(plate_freq, 3, label='Crust Plates', **flow)
    edges = S.voronoi(plate_freq, 3, feature='DISTANCE_TO_EDGE', label='Crust Cracks', **flow)
    pr, pg, pb = b.separate_color(plates.outputs['Color'])
    crust_z = S.znoise(b.mul(plate_freq, 0.3), 4, detail=3.0, roughness=0.5, label='Crust Areas', **flow)
    crust_amount = I['Crust']
    crust_area = F.cover(b, b.madd(b.sub(pr, 0.5), 2.0, crust_z), crust_amount, 0.15, gate=False)
    crust_area = b.mul(crust_area, b.clamp01(b.mul(crust_amount, 25.0)))
    crack_w = b.madd(I['Crack Width'], 0.16, 0.01)
    gap = b.smoothstep(b.mul(crack_w, 0.4), crack_w, edges.outputs['Distance'])
    crust = b.mul(crust_area, gap)
    crust_rough = S.noise(b.mul(plate_freq, 6.0), 5, detail=5.0, roughness=0.65, label='Crust Detail')
    crust_col = b.color_scale(I['Crust Color'], b.madd(pg, 0.5, b.madd(crust_rough, 0.6, 0.5)))
    col = b.mix_color(crust, col, crust_col)
    rough = b.mix(crust, rough, b.madd(crust_rough, 0.2, b.sub(I['Crust Roughness'], 0.1)))
    # thin crust near the cracks still glows dull red
    rim_glow = b.mul(b.one_minus(b.smoothstep(crack_w, b.mul(crack_w, 3.0), edges.outputs['Distance'])), 0.45)
    q = b.mix(crust, q, b.mul(rim_glow, b.madd(pb, 0.5, 0.5)))
    tilt = b.madd(pb, 0.06, b.madd(crust_rough, 0.03, 0.52))
    h = b.mix(crust, h, tilt)
    hm = b.mix(crust, hm, b.sub(crust_rough, 0.5))

    # ---- pahoehoe ropes (across the flow) and aa clinker
    ropes_n = S.noise(b.div(0.25, I['Rope Size']), 6, detail=2.0, roughness=0.5, distortion=0.4,
                      label='Ropes', **across)
    rope = b.absolute(b.sub(b.mul(b.fract(b.mul(ropes_n, 6.0)), 2.0), 1.0))  # triangle wave: ridges
    rope = b.smoothstep(0.1, 0.9, rope)
    rope_on = b.mul(I['Ropes'], crust)
    h = b.madd(b.mul(rope, rope_on), 0.06, h)
    hm = b.madd(b.mul(b.sub(rope, 0.5), rope_on), 0.6, hm)
    rough = b.mix(b.mul(rope_on, 0.5), rough, b.mul(rough, b.madd(rope, 0.4, 0.5)))

    clinker = S.voronoi(b.mul(plate_freq, 8.0), 7, label='Clinker')
    cl_r, cl_g, _cl_b = b.separate_color(clinker.outputs['Color'])
    cl_shape = S.noise(b.mul(plate_freq, 30.0), 8, detail=4.0, roughness=0.7, label='Clinker Detail')
    chunk = b.clamp01(b.one_minus(b.div(b.madd(cl_shape, 0.4, clinker.outputs['Distance']), b.madd(cl_g, 0.3, 0.5))))
    cl_on = b.mul(I['Clinker'], crust)
    h = b.madd(b.mul(chunk, cl_on), b.madd(cl_r, 0.08, 0.06), h)
    hm = b.madd(b.mul(b.sub(cl_shape, 0.5), cl_on), 1.5, hm)
    col = b.mix_color(b.mul(cl_on, b.mul(cl_r, 0.6)), col, b.color_scale((0.09, 0.045, 0.03), b.madd(cl_shape, 0.8, 0.6)))
    rough = b.mix(cl_on, rough, b.madd(cl_shape, 0.1, 0.9))

    # ---- glassy skin, gas bubbles, sulfur and ash
    glassy = b.mul(I['Glassy'], crust)
    rough = b.mix(glassy, rough, b.madd(crust_rough, 0.12, 0.08))
    col = b.mix_color(b.mul(glassy, 0.3), col, b.color_scale(col, 1.8))
    ves = S.voronoi(b.mul(plate_freq, 40.0), 9, label='Vesicles')
    vr, vg, _vb = b.separate_color(ves.outputs['Color'])
    hole = b.mul(b.one_minus(b.smoothstep(b.madd(vg, 0.15, 0.1), b.madd(vg, 0.15, 0.25), ves.outputs['Distance'])),
                 b.math('LESS_THAN', vr, b.mul(I['Vesicles'], 0.8)))
    hole = b.mul(hole, crust)
    col = b.mix_color(b.mul(hole, 0.8), col, b.color_scale(col, 0.3))
    hm = b.madd(hole, -0.8, hm)

    low = b.one_minus(b.smoothstep(0.42, 0.55, h))
    sulfur = b.mul(F.cover(b, b.madd(low, 2.0, b.mul(crust_rough, 2.0)), I['Sulfur'], 0.3), crust)
    sulfur = b.mul(sulfur, b.one_minus(b.smoothstep(0.1, 0.3, q)))  # burns off where it is hot
    col = b.mix_color(sulfur, col, b.color_scale(SULFUR, b.madd(crust_rough, 0.5, 0.75)))
    rough = b.mix(sulfur, rough, 0.85)
    ash_z = b.madd(b.sub(h, 0.5), 8.0, S.znoise(b.mul(plate_freq, 2.0), 10, detail=4.0, label='Ash'))
    ash = b.mul(F.cover(b, ash_z, I['Ash'], 0.6), b.one_minus(b.smoothstep(0.15, 0.4, q)))
    col = b.mix_color(ash, col, b.color_scale(ASH, b.madd(crust_rough, 0.4, 0.8)))
    rough = b.mix(ash, rough, 0.95)
    hm = b.mul(hm, b.madd(ash, -0.6, 1.0))

    # ---- glow: blackbody color of the local temperature, fading fast as it cools
    q = b.mul(q, I['Heat'])
    temp = b.mul(I['Temperature'], b.madd(q, 0.45, 0.55))
    body = b.node('ShaderNodeBlackbody', label='Glow Color')
    b.feed(body.inputs['Temperature'], temp)
    glow = b.mul(b.mul(q, q), q)
    emission = b.mix_color(b.clamp01(glow), (0.0, 0.0, 0.0), body.outputs['Color'], clamp_result=True)
    col = b.mix_color(b.clamp01(b.mul(q, 1.5)), col, b.color_scale(col, 0.35))  # glowing parts: no lit look

    C.finish(b, gout, I, col, 0.0, rough, h, hm, distance=LAVA_BUMP, displace=I['Real Displacement'], extra={
        'Emission': emission,
        'Emission Strength': I['Emission Strength'],
    })


EMISSION_LINKS = {'Emission': 'Emission Color', 'Emission Strength': 'Emission Strength'}

TERRAIN_SPEC = dict(
    label='Terrain', category='TERRAIN', params=TERRAIN_PARAMS, outputs=TERRAIN_OUTPUTS, build=build_terrain,
    display=('Ground Color', 0.0, 'Roughness'), bump=TERRAIN_BUMP, fit=0.5,
)
LAVA_SPEC = dict(
    label='Lava', category='TERRAIN', params=LAVA_PARAMS, outputs=LAVA_OUTPUTS, build=build_lava,
    links=EMISSION_LINKS, display=('Crust Color', 0.0, 'Crust Roughness'), bump=LAVA_BUMP, fit=0.5, glow='Heat',
)
