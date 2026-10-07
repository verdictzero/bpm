# SPDX-License-Identifier: GPL-3.0-or-later
"""Leather generator: pebbled, smooth, suede, patent or croc-embossed leather;
new, worn, cracked or dirty, optionally with stitched seams."""

from . import features as F
from . import gencommon as C
from .nodebuilder import is_socket

BROWN = (0.10, 0.036, 0.014)
BROWN_DARK = (0.028, 0.010, 0.005)

LEATHER_PARAMS = [
    # -- Leather
    C.color('Leather Color', BROWN, 'Leather', 'Main color of the leather', key=True),
    C.color('Crease Color', BROWN_DARK, 'Leather', 'Darker color in creases and between the grain'),
    C.fac('Roughness', 0.55, 'Leather', 'Glossiness (0 = glossy, 1 = matte)', key=True),
    C.fac('Color Variation', 0.3, 'Leather', 'Mottled, uneven color of the hide'),
    # -- Grain
    C.fac('Grain', 0.6, 'Grain', 'Depth of the pebbled grain', key=True),
    C.scale('Grain Scale', 280.0, 10.0, 5000.0, 'Grain', 'Size of the grain (higher = finer)'),
    C.fac('Wrinkles', 0.4, 'Grain', 'Soft creases and folds', key=True),
    C.scale('Wrinkle Scale', 10.0, 0.5, 200.0, 'Grain', 'Size of the wrinkles (higher = smaller)'),
    C.fac('Pores', 0.3, 'Grain', 'Tiny pores'),
    C.fac('Croc', 0.0, 'Grain', 'Embossed crocodile-style scales'),
    C.scale('Croc Scale', 25.0, 1.0, 500.0, 'Grain', 'Size of the scales (higher = smaller)'),
    # -- Finish
    C.fac('Suede', 0.0, 'Finish', 'Velvety suede / nubuck: matte with a soft sheen'),
    C.fac('Patent', 0.0, 'Finish', 'High-gloss patent leather'),
    C.fac('Stitching', 0.0, 'Finish', 'Stitched seams between leather panels'),
    C.Param('Panel Size', 'FLOAT', 0.25, 0.02, 5.0, 'Finish', 'Distance between the seams', subtype='DISTANCE'),
    C.color('Thread Color', (0.55, 0.45, 0.30), 'Finish', 'Color of the stitching thread'),
    # -- Wear
    C.fac('Wear', 0.2, 'Wear', 'Rubbed areas: lighter, smoother and shinier', key=True),
    C.fac('Edge Wear', 0.4, 'Wear', 'Worn, lighter edges (visible in Cycles and in baked textures)'),
    C.Param('Edge Width', 'FLOAT', 0.02, 0.001, 0.3, 'Wear', 'Width of the edge wear', subtype='DISTANCE'),
    C.fac('Cracks', 0.0, 'Wear', 'Dry, cracked old leather'),
    C.fac('Scratches', 0.1, 'Wear', 'Light scratches'),
    C.fac('Fading', 0.0, 'Wear', 'Sun-faded, dried-out leather'),
    C.fac('Dirt', 0.1, 'Wear', 'Grime in creases and corners', key=True),
    C.color('Dirt Color', C.DIRT, 'Wear', 'Color of the grime'),
] + C.PATTERN_PARAMS

LEATHER_OUTPUTS = C.COMMON_OUTPUTS + [('Coat', 'FLOAT'), ('Sheen', 'FLOAT')]


def _seams(b, S, tile, I):
    """(groove, stitches) masks for straight seams every `Panel Size`."""
    size = I['Panel Size']
    if tile:
        span = b.mul(I['Tile Size'], I['Scale'])
        count = b.maximum(1.0, b.math('ROUND', b.div(span, size)))
        size = b.div(span, count)
        coords = ((b.mul(S.u, span), b.mul(S.v, span)), (b.mul(S.v, span), b.mul(S.u, span)))
        weights = (1.0, 1.0)
    else:
        x, y, z = b.separate(S.P)
        n = b.vmath('ABSOLUTE', b.vmath('NORMALIZE', b.texcoord().outputs['Normal']))
        nx, ny, nz = b.separate(n)
        # seams of one axis only show on faces that the axis runs along
        coords = ((x, b.add(y, z)), (y, b.add(x, z)), (z, b.add(x, y)))
        weights = tuple(b.one_minus(b.smoothstep(0.7, 0.9, c)) for c in (nx, ny, nz))
    groove, stitch = 0.0, 0.0
    for (across, along), weight in zip(coords, weights):
        f = b.fract(b.div(across, size))
        dist = b.mul(b.minimum(f, b.one_minus(f)), size)  # distance to the seam (pattern units)
        g = b.mul(b.one_minus(b.smoothstep(0.0005, 0.0016, dist)), weight)
        # two rows of stitches, 5 mm from the seam, 4 mm long dashes
        row = b.one_minus(b.smoothstep(0.0006, 0.0011, b.absolute(b.sub(dist, 0.005))))
        dash = b.one_minus(b.smoothstep(0.55, 0.7, b.fract(b.div(along, 0.004))))
        s = b.mul(b.mul(row, dash), weight)
        groove = b.maximum(groove, g) if is_socket(groove) else g
        stitch = b.maximum(stitch, s) if is_socket(stitch) else s
    on = I['Stitching']
    return b.mul(groove, on), b.mul(stitch, b.clamp01(b.mul(on, 25.0)))


def build_leather(b, I, gout, tile):
    S = F.Space(b, tile, I['Scale'], I['Seed'], I['Tile Size'] if tile else 1.0)
    inv = b.div(1.0, I['Scale'])
    edge = F.edge_mask(b, S, b.mul(I['Edge Width'], inv))
    cav = F.cavity_mask(b, S, b.mul(inv, 0.25))

    # ---- pebbled grain: cells of uneven size, depth varies over the hide
    gs = I['Grain Scale']
    gv = S.voronoi(gs, 1, label='Grain')
    gv2 = S.voronoi(b.mul(gs, 0.43), 2, feature='DISTANCE_TO_EDGE', label='Grain Large')
    gd = S.znoise(3.0, 3, detail=3.0, label='Grain Depth')
    fine = b.smoothstep(0.0, 0.7, gv.outputs['Distance'])  # 0 at pebble centers
    large = b.smoothstep(0.0, 0.35, gv2.outputs['Distance'])  # 0 in the grooves
    pebble = b.mul(b.one_minus(b.mul(fine, 0.45)), large)  # 1 on pebble tops
    grain = b.mul(I['Grain'], b.clamp01(b.madd(gd, 0.2, 1.0)))

    # ---- wrinkles: a network of soft creases
    ws = I['Wrinkle Scale']
    wn = S.noise(ws, 4, detail=3.0, roughness=0.55, distortion=0.3, label='Wrinkles')
    wn2 = S.noise(b.mul(ws, 2.3), 5, detail=2.0, roughness=0.5, label='Fine Wrinkles')
    crease = b.maximum(b.one_minus(b.smoothstep(0.0, 0.05, b.absolute(b.sub(wn, 0.5)))),
                       b.mul(b.one_minus(b.smoothstep(0.0, 0.035, b.absolute(b.sub(wn2, 0.5)))), 0.6))
    crease = b.mul(crease, I['Wrinkles'])
    bulge = b.mul(b.sub(wn, 0.5), I['Wrinkles'])

    # ---- pores
    pz = S.znoise(b.mul(gs, 2.7), 6, detail=1.0, label='Pores')
    pores = b.mul(b.smoothstep(1.7, 2.3, pz), I['Pores'])

    # ---- croc scales
    cv = S.voronoi(I['Croc Scale'], 7, feature='DISTANCE_TO_EDGE', label='Croc Scales')
    cd = cv.outputs['Distance']
    croc = I['Croc']
    c_groove = b.mul(b.one_minus(b.smoothstep(0.02, 0.09, cd)), croc)
    c_dome = b.mul(b.smoothstep(0.0, 0.45, cd), croc)

    # ---- seams
    seam, stitch = _seams(b, S, tile, I)

    # ---- color
    zv = S.znoise(2.0, 8, detail=5.0, roughness=0.6, label='Mottling')
    col = b.color_scale(I['Leather Color'], b.madd(zv, b.mul(I['Color Variation'], 0.12), 1.0))
    low = b.clamp01(b.add(b.mul(b.one_minus(pebble), b.mul(grain, 0.7)),
                          b.add(b.mul(crease, 0.8), b.add(b.mul(pores, 0.6), b.mul(c_groove, 0.9)))))
    col = b.mix_color(low, col, I['Crease Color'])
    rough = b.madd(low, 0.12, b.madd(zv, 0.03, I['Roughness']))

    # ---- wear: rubbed areas get lighter, smoother and glossier (burnished)
    wz = S.znoise(2.5, 9, detail=4.0, roughness=0.6, label='Wear')
    field = b.madd(pebble, 0.6, wz)
    if is_socket(edge):
        field = b.madd(edge, b.mul(I['Edge Wear'], 3.0), field)
    worn = b.mul(F.cover(b, field, b.mul(I['Wear'], 0.5), 0.8), b.clamp01(b.mul(b.add(I['Wear'], I['Edge Wear']), 25.0)))
    worn = b.maximum(worn, b.mul(c_dome, b.mul(I['Wear'], 0.6)))
    light = b.hsv(col, saturation=0.85, value=1.6)
    col = b.mix_color(b.mul(worn, 0.8), col, light)
    rough = b.mix(worn, rough, b.mul(rough, 0.7))

    # ---- cracks in old leather
    kv = S.voronoi(b.mul(gs, 0.12), 10, feature='DISTANCE_TO_EDGE', label='Cracks')
    crack_on = F.cover(b, S.znoise(1.5, 11, detail=3.0), b.mul(I['Cracks'], 0.7), 0.4)
    crack = b.mul(b.one_minus(b.smoothstep(0.01, 0.035, kv.outputs['Distance'])), crack_on)
    col = b.mix_color(b.mul(crack, 0.7), col, b.hsv(col, saturation=0.6, value=1.6))
    rough = b.madd(crack, 0.3, rough)

    # ---- scratches and fading
    scr = F.scratch_mask(b, S, I['Scratches'], 2.0, 20)
    col = b.mix_color(b.mul(scr, 0.4), col, light)
    fz = S.znoise(1.2, 12, detail=3.0, label='Fading')
    fade = b.clamp01(b.mul(I['Fading'], b.madd(fz, 0.15, 1.0)))
    col = b.mix_color(fade, col, b.hsv(col, saturation=0.55, value=1.55))
    rough = b.madd(fade, 0.2, rough)

    # ---- suede and patent finishes
    suede = I['Suede']
    sz = S.znoise(b.mul(gs, 4.0), 13, detail=2.0, label='Suede Nap')
    col = b.mix_color(suede, col, b.color_scale(b.hsv(col, saturation=0.8, value=1.35), b.madd(sz, 0.04, 1.0)))
    rough = b.mix(suede, rough, 0.95)
    patent = I['Patent']
    rough = b.mix(patent, rough, 0.04)
    coat = b.mul(patent, b.one_minus(b.mul(worn, 0.5)))

    # ---- stitching
    col = b.mix_color(b.mul(seam, 0.7), col, I['Crease Color'])
    col = b.mix_color(stitch, col, I['Thread Color'])
    rough = b.mix(stitch, rough, 0.75)

    # ---- dirt
    dirt = C.dirt_mask(b, S, I['Dirt'], cav, edge, 30, extra=b.mul(b.maximum(crease, seam), 0.6), spots=0.25)
    col = b.mix_color(dirt, col, I['Dirt Color'])
    rough = b.mix(dirt, rough, 0.85)

    # ---- relief (smooth finishes flatten the grain)
    flat = b.one_minus(b.mul(b.maximum(patent, b.mul(suede, 0.6)), 0.7))
    h_macro = b.madd(bulge, 0.25, 0.5)
    h_macro = b.madd(crease, -0.2, h_macro)
    h_macro = b.madd(b.sub(c_dome, b.mul(croc, 0.5)), 0.35, h_macro)
    h_macro = b.madd(c_groove, -0.2, h_macro)
    h_macro = b.madd(seam, -0.25, h_macro)
    h_macro = b.madd(stitch, 0.1, h_macro)
    h_micro = b.mul(b.mul(b.sub(pebble, 0.5), b.mul(grain, 1.5)), flat)
    h_micro = b.madd(pores, -0.4, h_micro)
    h_micro = b.madd(crack, -0.6, h_micro)
    h_micro = b.madd(scr, -0.4, h_micro)
    h_micro = b.madd(sz, b.mul(suede, 0.08), h_micro)

    C.finish(b, gout, I, col, 0.0, rough, h_macro, h_micro, extra={'Coat': coat, 'Sheen': b.mul(suede, 0.8)})


SPEC = dict(
    label='Leather', category='LEATHER', params=LEATHER_PARAMS, outputs=LEATHER_OUTPUTS, build=build_leather,
    links={'Coat': 'Coat Weight', 'Sheen': 'Sheen Weight'}, bsdf={'Coat Roughness': 0.02, 'Sheen Roughness': 0.4},
    display=('Leather Color', 0.0, 'Roughness'), fit=0.5,
)
