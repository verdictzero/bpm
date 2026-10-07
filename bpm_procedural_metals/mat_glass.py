# SPDX-License-Identifier: GPL-3.0-or-later
"""Glass generator: clear, tinted, frosted, textured and stained glass, from
spotless to filthy.

Glass is a Principled BSDF with transmission.  Everything that is not glass
(grime, dust, wire mesh, lead came) blocks the light, so the generator has an
extra Transmission output: 1 = see-through, 0 = opaque.  Overlays (dirt and
dust) lower it too, and baking writes it into a Transmission texture.
"""

from . import features as F
from . import gencommon as C
from .nodebuilder import is_socket

GLASS_BUMP = 0.012  # relief depth of the full 0..1 height range (meters at Scale 1)

GLASS_PARAMS = [
    # -- Glass
    C.color('Glass Color', (0.90, 0.96, 0.93), 'Glass', 'Tint of the glass (white = no tint)', key=True),
    C.fac('Roughness', 0.0, 'Glass', '0 = perfectly clear, higher = blurry', key=True),
    C.fac('Frosting', 0.0, 'Glass', 'Sandblasted or acid-etched frosted glass', key=True),
    C.fac('Milkiness', 0.0, 'Glass', 'Cloudy, opal-like glass that lets less light through'),
    C.Param('IOR', 'FLOAT', 1.5, 1.0, 2.5, 'Glass',
            'Index of refraction: 1.5 window glass, 1.52 bottles, 1.6 and more for crystal'),
    C.fac('Color Variation', 0.05, 'Glass', 'Uneven tint, like old or hand-made glass'),
    C.fac('Waviness', 0.0, 'Glass', 'Wavy, distorting surface of old window glass'),
    C.fac('Bubbles', 0.0, 'Glass', 'Tiny air bubbles (seeded, hand-blown glass)'),
    # -- Texture
    C.fac('Reeds', 0.0, 'Texture', 'Parallel rounded ribs (reeded / fluted glass)'),
    C.Param('Reed Width', 'FLOAT', 0.012, 0.001, 0.2, 'Texture', 'Width of each reed', subtype='DISTANCE'),
    C.axis('Reed Direction', (1.0, 0.0, 0.0), 'Texture', 'Direction across the reeds'),
    C.fac('Hammered', 0.0, 'Texture', 'Dimpled, hammered or pebbled privacy glass'),
    C.Param('Dimple Size', 'FLOAT', 0.01, 0.001, 0.2, 'Texture', 'Size of the dimples', subtype='DISTANCE'),
    C.fac('Wire Mesh', 0.0, 'Texture', 'Wire grid inside the glass (wired safety glass)'),
    C.Param('Wire Spacing', 'FLOAT', 0.0125, 0.002, 0.2, 'Texture', 'Distance between the wires',
            subtype='DISTANCE'),
    # -- Stained glass
    C.fac('Stained Glass', 0.0, 'Stained Glass', 'Colored pieces joined by lead lines, like church windows'),
    C.Param('Piece Size', 'FLOAT', 0.08, 0.01, 1.0, 'Stained Glass', 'Size of the colored pieces',
            subtype='DISTANCE'),
    C.Param('Lead Width', 'FLOAT', 0.005, 0.0005, 0.03, 'Stained Glass', 'Width of the lead lines',
            subtype='DISTANCE'),
    C.color('Color 1', (0.10, 0.25, 0.85), 'Stained Glass', 'First glass color'),
    C.color('Color 2', (0.85, 0.08, 0.06), 'Stained Glass', 'Second glass color'),
    C.color('Color 3', (0.95, 0.70, 0.10), 'Stained Glass', 'Third glass color'),
    C.color('Color 4', (0.20, 0.70, 0.18), 'Stained Glass', 'Fourth glass color'),
    # -- Wear
    C.fac('Scratches', 0.05, 'Wear', 'Fine, whitish scratches', key=True),
    C.scale('Scratch Scale', 2.5, 0.05, 20.0, 'Wear', 'Scratch size (higher = smaller, denser)'),
    C.fac('Chipped Edges', 0.0, 'Wear', 'Small chips knocked out of the edges (visible in Cycles and bakes)'),
    C.Param('Edge Width', 'FLOAT', 0.01, 0.001, 0.3, 'Wear', 'Width of the edge wear', subtype='DISTANCE'),
    C.fac('Cracks', 0.0, 'Wear', 'Network of fine cracks'),
    C.scale('Crack Scale', 6.0, 0.5, 100.0, 'Wear', 'Size of the cracked pieces (higher = smaller)'),
    C.fac('Weathering', 0.0, 'Wear', 'Worn, pitted and frosted by sand and water (sea glass)'),
    # -- Grime
    C.fac('Smudges', 0.05, 'Grime', 'Fingerprints and greasy smudges', key=True),
    C.fac('Dust', 0.0, 'Grime', 'Dust settled on top', key=True),
    C.color('Dust Color', (0.42, 0.40, 0.36), 'Grime', 'Color of the dust'),
    C.fac('Grime', 0.0, 'Grime', 'Dirty film, thickest in corners and low down', key=True),
    C.color('Grime Color', (0.11, 0.085, 0.05), 'Grime', 'Color of the grime'),
    C.fac('Water Spots', 0.0, 'Grime', 'Dried hard-water spots'),
    C.fac('Rain Streaks', 0.0, 'Grime', 'Dirty streaks running down'),
] + C.PATTERN_PARAMS

GLASS_OUTPUTS = C.COMMON_OUTPUTS + [('Transmission', 'FLOAT'), ('IOR', 'FLOAT')]

LEAD = (0.10, 0.10, 0.105)
WIRE = (0.45, 0.45, 0.46)
MINERAL = (0.75, 0.74, 0.70)


def _lines(b, x, half_width, soft=0.02):
    """1 on lines at whole numbers of `x`, `half_width` wide (in units of x)."""
    f = b.fract(x)
    d = b.minimum(f, b.one_minus(f))
    return b.one_minus(b.smoothstep(half_width, b.add(half_width, soft), d))


def build_glass(b, I, gout, tile):
    S = F.Space(b, tile, I['Scale'], I['Seed'], I['Tile Size'] if tile else 1.0)
    inv = b.div(1.0, I['Scale'])
    edge = F.edge_mask(b, S, b.mul(I['Edge Width'], inv))
    cav = F.cavity_mask(b, S, b.mul(inv, 0.2))
    span = b.mul(I['Tile Size'], I['Scale']) if tile else None

    # ---- the glass itself
    cz = S.znoise(1.5, 1, detail=3.0, roughness=0.5, label='Color Variation')
    col = b.color_scale(I['Glass Color'], b.madd(cz, b.mul(I['Color Variation'], 0.06), 1.0))
    milk = I['Milkiness']
    col = b.mix_color(b.mul(milk, 0.75), col, (0.86, 0.86, 0.85))
    trans = b.one_minus(b.mul(milk, 0.8))
    frost_z = S.znoise(220.0, 2, detail=2.0, roughness=0.5, label='Frost Grain')
    rough = b.maximum(I['Roughness'], b.mul(I['Frosting'], b.madd(frost_z, 0.03, 0.32)))
    rough = b.madd(milk, 0.25, rough)

    # ---- stained glass: colored pieces with lead came between them
    stained = I['Stained Glass']
    piece_freq = b.div(1.0, I['Piece Size'])
    pieces = S.voronoi(piece_freq, 6, label='Glass Pieces')
    pr, pg, _pb = b.separate_color(pieces.outputs['Color'])
    piece_col = b.mix_color(b.math('GREATER_THAN', pr, 0.25), I['Color 1'], I['Color 2'])
    piece_col = b.mix_color(b.math('GREATER_THAN', pr, 0.5), piece_col, I['Color 3'])
    piece_col = b.mix_color(b.math('GREATER_THAN', pr, 0.75), piece_col, I['Color 4'])
    piece_col = b.color_scale(piece_col, b.madd(pg, 0.5, b.madd(cz, 0.08, 0.75)))
    col = b.mix_color(stained, col, piece_col)
    joints = S.voronoi(piece_freq, 6, feature='DISTANCE_TO_EDGE', label='Lead Came')
    lead_half = b.mul(b.mul(I['Lead Width'], piece_freq), 0.5)
    lead_d = joints.outputs['Distance']
    lead = b.mul(b.one_minus(b.smoothstep(lead_half, b.add(lead_half, 0.015), lead_d)),
                 b.math('GREATER_THAN', stained, 0.001))
    lead_profile = b.math('SQRT', b.clamp01(b.one_minus(b.div(lead_d, b.maximum(lead_half, 1e-4)))))

    # ---- surface textures
    if tile:
        count = b.maximum(1.0, b.math('ROUND', b.div(span, I['Reed Width'])))
        x = b.mul(S.u, count)
    else:
        x = b.div(b.vmath('DOT_PRODUCT', S.P, b.vmath('NORMALIZE', I['Reed Direction'])), I['Reed Width'])
    t = b.sub(b.mul(b.fract(x), 2.0), 1.0)
    reed = b.math('SQRT', b.clamp01(b.one_minus(b.mul(t, t))))
    dimples = S.voronoi(b.div(1.0, I['Dimple Size']), 5, label='Dimples')
    dimple = b.smoothstep(0.0, 0.75, dimples.outputs['Distance'])
    wz = S.znoise(4.0, 3, detail=2.0, roughness=0.5, label='Waviness')
    bubbles = S.voronoi(260.0, 4, label='Bubbles')
    br, bg, _bb = b.separate_color(bubbles.outputs['Color'])
    radius = b.madd(bg, 0.2, 0.1)
    bubble = b.mul(b.one_minus(b.smoothstep(b.mul(radius, 0.4), radius, bubbles.outputs['Distance'])),
                   b.math('LESS_THAN', br, b.mul(I['Bubbles'], 0.6)))

    # wire mesh (in wired safety glass the wires sit inside the glass)
    if tile:
        wires = b.maximum(1.0, b.math('ROUND', b.div(span, I['Wire Spacing'])))
        ws, wt = b.mul(S.u, wires), b.mul(S.v, wires)
    else:
        ws, wt = F.box_coords(b, S)
        ws, wt = b.div(ws, I['Wire Spacing']), b.div(wt, I['Wire Spacing'])
    wire_half = b.div(b.mul(0.00025, I['Scale']), I['Wire Spacing'])  # 0.5 mm thick wire
    wire = b.mul(b.maximum(_lines(b, ws, wire_half), _lines(b, wt, wire_half)),
                 b.math('GREATER_THAN', I['Wire Mesh'], 0.001))
    wire = b.mul(wire, b.clamp01(b.mul(I['Wire Mesh'], 2.0)))

    # ---- wear
    scr = F.scratch_mask(b, S, I['Scratches'], I['Scratch Scale'], 20)
    chip = b.mul(F.broken(b, S, edge, 11, 40.0), I['Chipped Edges']) if is_socket(edge) else 0.0
    chip = b.smoothstep(0.35, 0.6, chip) if is_socket(chip) else 0.0
    if tile:
        crack_v = S.voronoi(I['Crack Scale'], 8, feature='DISTANCE_TO_EDGE', label='Cracks')
    else:  # bent a little, so the cracks don't look like straight polygon edges
        warp = S.noise(4.0, 7, detail=2.0, roughness=0.5, label='Crack Warp').node.outputs['Color']
        wr, wg, wb_ = b.separate_color(warp)
        bent = b.vadd(S.P, b.vscale(b.combine(b.sub(wr, 0.5), b.sub(wg, 0.5), b.sub(wb_, 0.5)),
                                    b.div(0.35, I['Crack Scale'])))
        crack_v = S.voronoi(I['Crack Scale'], 8, feature='DISTANCE_TO_EDGE', base=bent, label='Cracks')
    crack_z = S.znoise(b.mul(I['Crack Scale'], 0.7), 9, detail=2.0, roughness=0.5, label='Crack Patches')
    crack_on = F.cover(b, crack_z, b.mul(I['Cracks'], 0.8), 0.5)
    crack = b.mul(b.one_minus(b.smoothstep(0.004, 0.02, crack_v.outputs['Distance'])), crack_on)
    weather = I['Weathering']
    pits_z = S.znoise(160.0, 10, detail=2.0, roughness=0.5, label='Pits')
    pits = b.mul(b.smoothstep(1.2, 2.2, pits_z), weather)
    if is_socket(edge):  # edges wear most
        weather_frost = b.clamp01(b.mul(weather, b.madd(edge, 0.4, 0.8)))
    else:
        weather_frost = b.clamp01(b.mul(weather, 0.85))

    rough = b.mix(weather_frost, rough, b.madd(frost_z, 0.04, 0.42))
    col = b.mix_color(b.mul(weather_frost, 0.1), col, (0.85, 0.85, 0.84))
    trans = b.mul(trans, b.one_minus(b.mul(weather_frost, 0.06)))
    white = b.maximum(b.mul(scr, 0.6), b.mul(chip, 0.7))
    col = b.mix_color(white, col, (0.85, 0.86, 0.86))
    rough = b.mix(b.maximum(b.mul(scr, 0.8), chip), rough, 0.4)
    trans = b.mul(trans, b.one_minus(b.maximum(b.mul(scr, 0.3), b.maximum(b.mul(chip, 0.5), b.mul(crack, 0.4)))))

    # ---- metal inside / between the glass: opaque
    metal = b.maximum(wire, lead)
    col = b.mix_color(wire, col, WIRE)
    col = b.mix_color(lead, col, LEAD)
    rough = b.mix(metal, rough, b.mix(lead, 0.35, 0.55))
    metallic = b.mul(metal, 0.85)
    trans = b.mul(trans, b.one_minus(metal))

    # ---- grime on top of everything
    # fingerprints: little whorls of ridges, plus greasy smears
    smz = S.znoise(5.0, 22, detail=4.0, roughness=0.6, label='Smudges')
    smear = b.mul(F.cover(b, smz, b.mul(I['Smudges'], 0.4), 0.5), 0.6)
    prints = S.voronoi(45.0, 23, label='Fingerprints')
    pr2, _pg2, _pb2 = b.separate_color(prints.outputs['Color'])
    pd = prints.outputs['Distance']
    whorl = b.madd(b.math('COSINE', b.mul(pd, 56.0)), 0.5, 0.5)
    finger = b.mul(b.one_minus(b.smoothstep(0.25, 0.45, pd)), b.math('LESS_THAN', pr2, b.mul(I['Smudges'], 0.5)))
    finger = b.mul(finger, b.madd(whorl, 0.6, 0.4))
    grease = b.maximum(smear, finger)
    rough = b.mix(b.mul(grease, 0.9), rough, 0.4)
    trans = b.mul(trans, b.one_minus(b.mul(grease, 0.12)))

    # hard-water spots: rings of minerals
    spots = S.voronoi(70.0, 25, label='Water Spots')
    sr, sg, _sb = b.separate_color(spots.outputs['Color'])
    sd = spots.outputs['Distance']
    sradius = b.madd(sg, 0.25, 0.15)
    ring = b.mul(b.smoothstep(b.sub(sradius, 0.06), sradius, sd),
                 b.one_minus(b.smoothstep(sradius, b.add(sradius, 0.02), sd)))
    spot = b.mul(b.maximum(ring, b.mul(b.one_minus(b.smoothstep(0.0, sradius, sd)), 0.3)),
                 b.math('LESS_THAN', sr, b.mul(I['Water Spots'], 0.7)))
    col = b.mix_color(b.mul(spot, 0.7), col, MINERAL)
    rough = b.mix(spot, rough, 0.6)
    trans = b.mul(trans, b.one_minus(b.mul(spot, 0.45)))

    # grime: a dirty film, patches, corners, low down and streaks running down
    gz = S.znoise(2.0, 30, detail=5.0, roughness=0.6, label='Grime')
    gfine = S.znoise(14.0, 31, detail=3.0, roughness=0.6, label='Grime Breakup')
    grime = I['Grime']
    film = b.mul(grime, b.clamp01(b.madd(gz, 0.05, 0.22)))
    gmask = b.maximum(film, b.mul(F.cover(b, gz, b.mul(grime, 0.35), 0.8), b.mul(grime, 0.55)))
    if is_socket(cav):
        gmask = b.maximum(gmask, b.mul(b.smoothstep(0.1, 0.7, b.madd(gfine, 0.06, cav)), grime))
        gz_obj = b.separate(b.texcoord().outputs['Generated'])[2]
        low = b.one_minus(b.smoothstep(0.0, 0.18, b.madd(gfine, 0.02, gz_obj)))
        gmask = b.maximum(gmask, b.mul(low, b.mul(grime, 0.6)))
    aniso = (1.0, 1.0 / 14.0) if tile else (1.0, 1.0, 1.0 / 14.0)
    stz = S.znoise(4.0, 32, detail=4.0, roughness=0.6, aniso=aniso, label='Rain Streaks')
    streaks = b.mul(F.cover(b, stz, b.mul(I['Rain Streaks'], 0.35), 0.45), 0.55)
    gmask = b.clamp01(b.mul(b.maximum(gmask, streaks), b.clamp01(b.madd(gfine, 0.15, 0.95))))
    gcol = b.mix_color(b.smoothstep(-1.0, 1.5, gfine), I['Grime Color'], b.color_scale(I['Grime Color'], 1.8))
    col = b.mix_color(gmask, col, gcol)
    rough = b.mix(gmask, rough, 0.8)
    metallic = b.mul(metallic, b.one_minus(gmask))
    trans = b.mul(trans, b.one_minus(gmask))

    # cracks catch the light even through the grime
    col = b.mix_color(b.mul(crack, 0.6), col, (0.85, 0.86, 0.86))
    rough = b.mix(crack, rough, 0.25)

    # dust settles on surfaces that face up
    if tile:
        facing = 1.0
    else:
        facing = b.madd(b.smoothstep(0.05, 0.9, b.separate(b.geometry().outputs['Normal'])[2]), 0.85, 0.15)
    clump = S.znoise(1.2, 42, detail=4.0, roughness=0.55, label='Dust Clumps')
    dust = b.clamp01(b.mul(b.mul(I['Dust'], facing), b.madd(clump, 0.25, b.madd(gfine, 0.1, 1.15))))
    col = b.mix_color(dust, col, I['Dust Color'])
    rough = b.mix(dust, rough, 0.95)
    metallic = b.mul(metallic, b.one_minus(dust))
    trans = b.mul(trans, b.one_minus(dust))

    # ---- relief
    h = b.madd(b.sub(reed, 0.5), b.mul(I['Reeds'], 0.15), 0.5)
    h = b.madd(b.sub(dimple, 0.5), b.mul(I['Hammered'], 0.12), h)
    h = b.madd(wz, b.mul(I['Waviness'], 0.05), h)
    h = b.madd(lead_profile, b.mul(lead, 0.25), h)
    h = b.madd(chip, -0.25, h)
    h = b.madd(crack, -0.06, h)
    h_micro = b.madd(bubble, 0.5, b.mul(pits, -0.5))
    h_micro = b.madd(scr, -0.4, h_micro)
    h_micro = b.madd(b.maximum(gmask, dust), 0.15, h_micro)
    h_micro = b.madd(b.mul(frost_z, 0.04), b.maximum(I['Frosting'], weather_frost), h_micro)

    C.finish(b, gout, I, col, metallic, rough, b.clamp01(h), h_micro, distance=GLASS_BUMP, extra={
        'Transmission': b.clamp01(trans),
        'IOR': I['IOR'],
    })


SPEC = dict(
    label='Glass', category='GLASS', params=GLASS_PARAMS, outputs=GLASS_OUTPUTS, build=build_glass,
    links={'Transmission': 'Transmission Weight', 'IOR': 'IOR'},
    display=('Glass Color', 0.0, 'Roughness', 0.25), fit=0.3, bump=GLASS_BUMP, glass=True,
)
