# SPDX-License-Identifier: GPL-3.0-or-later
"""Biomechanical generator: H.R. Giger-style surfaces where bone, sinew,
tubing and machinery merge.

The relief is built from a few layers: ribs across a main axis (vertebrae,
ribbed hoses) grouped into segments, bundles of tubes along the axis, bony
plates, fleshy folds, veins and pores, all warped by noise so nothing looks
machine-made.  The colors are "airbrushed" from the relief: deep crevices go
almost black, raised parts catch a lighter tone.
"""

from . import features as F
from . import gencommon as C
from .nodebuilder import is_socket

ORGANIC_BUMP = 0.08  # relief depth of the full 0..1 height range (meters at Scale 1)

ORGANIC_PARAMS = [
    # -- Surface
    C.color('Base Color', (0.030, 0.032, 0.030), 'Surface', 'Main color of the surface', key=True),
    C.color('Highlight Color', (0.26, 0.25, 0.22), 'Surface', 'Color of the raised parts', key=True),
    C.color('Cavity Color', (0.003, 0.003, 0.0028), 'Surface', 'Color deep in the crevices'),
    C.fac('Roughness', 0.32, 'Surface', 'Glossiness (0 = glossy, 1 = matte)'),
    C.fac('Metallic', 0.35, 'Surface', 'Chrome-like biomechanical sheen', key=True),
    C.fac('Color Variation', 0.3, 'Surface', 'Uneven, mottled color'),
    C.fac('Subsurface', 0.0, 'Surface', 'Fleshy, translucent look (render only)'),
    # -- Structure
    C.axis('Axis', (0.0, 0.0, 1.0), 'Structure', 'Main direction: ribs run across it, tubes along it'),
    C.fac('Ribs', 0.6, 'Structure', 'Ridges across the axis, like vertebrae or a ribbed hose', key=True),
    C.scale('Rib Density', 9.0, 1.0, 500.0, 'Structure', 'Ribs per meter'),
    C.fac('Rib Sharpness', 0.25, 'Structure', 'Narrow, sharp ribs instead of round ones'),
    C.fac('Segments', 0.6, 'Structure', 'Groups of ribs separated by deep joints'),
    C.fac('Tubes', 0.6, 'Structure', 'Bundles of tubes and sinews along the axis', key=True),
    C.Param('Tube Width', 'FLOAT', 0.25, 0.005, 2.0, 'Structure', 'Thickness of the tubes', subtype='DISTANCE'),
    C.fac('Plates', 0.15, 'Structure', 'Bony plates with grooves between them', key=True),
    C.Param('Plate Size', 'FLOAT', 0.35, 0.01, 5.0, 'Structure', 'Size of the plates', subtype='DISTANCE'),
    C.fac('Folds', 0.25, 'Structure', 'Fleshy folds and sinews'),
    C.fac('Veins', 0.2, 'Structure', 'Raised veins'),
    C.fac('Pores', 0.15, 'Structure', 'Small holes'),
    C.fac('Distortion', 0.35, 'Structure', 'Organic warping of everything'),
    # -- Wet
    C.fac('Wetness', 0.35, 'Wet', 'Wet, glossy sheen, strongest in the crevices', key=True),
    C.fac('Slime', 0.0, 'Wet', 'Thick slime pooling in crevices and running down'),
    C.color('Slime Color', (0.26, 0.28, 0.10), 'Wet', 'Color of the slime'),
    C.fac('Iridescence', 0.0, 'Wet', 'Oily rainbow sheen (render only)'),
] + C.PATTERN_PARAMS

ORGANIC_OUTPUTS = C.COMMON_OUTPUTS + [('Coat', 'FLOAT'), ('Subsurface', 'FLOAT'), ('Thin Film', 'FLOAT')]


def build_organic(b, I, gout, tile):
    S0 = F.Space(b, tile, I['Scale'], I['Seed'], I['Tile Size'] if tile else 1.0)
    inv = b.div(1.0, I['Scale'])
    cav = F.cavity_mask(b, S0, b.mul(inv, 0.15))
    dist = I['Distortion']

    # ---- organic warping of all coordinates
    if tile:
        span = b.mul(I['Tile Size'], I['Scale'])
        wu = S0.znoise(1.2, 1, detail=3.0, roughness=0.5, label='Warp U')
        wv = S0.znoise(1.2, 2, detail=3.0, roughness=0.5, label='Warp V')
        amp = b.div(b.mul(dist, 0.06), span)
        S = S0.warped((b.mul(wu, amp), b.mul(wv, amp)))
    else:
        wn = S0.noise(1.2, 1, detail=3.0, roughness=0.5, label='Warp').node.outputs['Color']
        wr, wg, wb = b.separate_color(wn)
        warp = b.combine(b.sub(wr, 0.5), b.sub(wg, 0.5), b.sub(wb, 0.5))
        S = S0.warped(b.vscale(warp, b.mul(dist, 0.35)))

    # ---- ribs across the axis, grouped into segments
    if tile:
        nr = b.mul(b.maximum(1.0, b.math('ROUND', b.div(b.mul(span, I['Rib Density']), 5.0))), 5.0)
        along = b.mul(S.u, nr)
        squash = None
    else:
        axis = b.vmath('NORMALIZE', I['Axis'])
        a = b.vmath('DOT_PRODUCT', S.P, axis)
        along = b.mul(a, I['Rib Density'])
        # coordinates squashed along the axis: tubes stay long and straight-ish
        squash = b.vmath('SUBTRACT', S.P, b.vscale(axis, b.mul(a, 0.95)))
    rz = S.znoise(2.0, 3, detail=2.0, roughness=0.5, label='Rib Wobble')
    rp = b.madd(rz, b.mul(dist, 0.25), along)
    tri = b.absolute(b.sub(b.mul(b.fract(rp), 2.0), 1.0))  # 0 at a rib's crest
    ridge = b.one_minus(b.smoothstep(0.0, b.mix(I['Rib Sharpness'], 0.95, 0.4), tri))
    seg = b.fract(b.mul(rp, 0.2))
    seg_d = b.minimum(seg, b.one_minus(seg))
    joint = b.mul(b.one_minus(b.smoothstep(0.0, 0.05, seg_d)), I['Segments'])
    ridge = b.mul(ridge, b.mix(I['Segments'], 1.0, b.smoothstep(0.03, 0.2, seg_d)))

    # ---- tubes along the axis (round cross-sections, like bundled hoses)
    tube_freq = b.div(0.5, I['Tube Width'])
    if tile:
        tv = S.voronoi(tube_freq, 4, aniso=(0.04, 1.0), label='Tubes')
    else:
        tv = S.voronoi(tube_freq, 4, base=squash, label='Tubes')
    td = b.div(tv.outputs['Distance'], 0.62)
    tube = b.math('SQRT', b.maximum(0.0, b.one_minus(b.mul(td, td))))
    # corrugated hoses: the ribs ride on the tubes
    ribbed = b.mul(tube, b.madd(ridge, b.mul(I['Ribs'], 0.25), 0.75))

    # ---- bony plates
    pv = S.voronoi(b.div(1.0, I['Plate Size']), 5, feature='DISTANCE_TO_EDGE', label='Plates')
    ped = pv.outputs['Distance']
    plate_dome = b.smoothstep(0.0, 0.45, ped)
    plate_groove = b.one_minus(b.smoothstep(0.015, 0.07, ped))

    # ---- folds, veins, pores
    fn = S.noise(3.5, 6, detail=3.0, roughness=0.55, distortion=0.4, label='Folds')
    fold = b.one_minus(b.absolute(b.sub(b.mul(fn, 2.0), 1.0)))
    fold = b.mul(fold, b.mul(fold, fold))
    vn = S.noise(9.0, 7, detail=2.0, roughness=0.5, distortion=0.6, label='Veins')
    vein = b.mul(b.one_minus(b.smoothstep(0.0, 0.03, b.absolute(b.sub(vn, 0.5)))), I['Veins'])
    pv2 = S.voronoi(60.0, 8, label='Pores')
    has_pore = b.math('LESS_THAN', b.separate_color(pv2.outputs['Color'])[0], b.mul(I['Pores'], 0.8))
    pore = b.mul(b.one_minus(b.smoothstep(0.08, 0.16, pv2.outputs['Distance'])), has_pore)

    # ---- relief
    h = b.madd(b.sub(ribbed, 0.5), b.mul(I['Tubes'], 0.6), 0.5)
    h = b.madd(b.sub(ridge, 0.5), b.mul(I['Ribs'], b.madd(I['Tubes'], -0.15, 0.3)), h)
    h = b.madd(joint, -0.3, h)
    h = b.madd(b.sub(plate_dome, 0.5), b.mul(I['Plates'], 0.3), h)
    h = b.madd(plate_groove, b.mul(I['Plates'], -0.3), h)
    h = b.madd(b.sub(fold, 0.3), b.mul(I['Folds'], 0.35), h)
    h = b.madd(vein, 0.1, h)
    h = b.madd(pore, -0.35, h)
    h = b.clamp01(h)

    # ---- airbrushed colors from the relief
    hn = b.smoothstep(0.15, 0.85, h)
    if is_socket(cav):
        hn = b.clamp01(b.madd(cav, -0.6, hn))
    mz = S0.znoise(1.5, 9, detail=4.0, roughness=0.55, label='Mottling')
    base = b.color_scale(I['Base Color'], b.madd(mz, b.mul(I['Color Variation'], 0.12), 1.0))
    col = b.mix_color(b.smoothstep(0.0, 0.35, hn), I['Cavity Color'], base)
    col = b.mix_color(b.mul(b.smoothstep(0.62, 1.0, hn), 0.9), col, I['Highlight Color'])
    low = b.one_minus(hn)

    # ---- wetness and slime
    wz = S0.znoise(2.0, 10, detail=4.0, roughness=0.6, label='Wetness')
    wet = b.clamp01(b.mul(I['Wetness'], b.madd(wz, 0.25, b.madd(low, 0.6, 0.6))))
    rough = b.madd(mz, 0.04, I['Roughness'])
    rough = b.mix(wet, rough, 0.04)
    slime = I['Slime']
    if tile:
        dz = S0.znoise(3.0, 11, detail=4.0, roughness=0.6, aniso=(1.0, 1.0 / 12.0), label='Drips')
    else:
        dz = S0.znoise(3.0, 11, detail=4.0, roughness=0.6, aniso=(1.0, 1.0, 1.0 / 12.0), label='Drips')
    pool = b.smoothstep(0.55, 0.85, low)
    drips = F.cover(b, dz, b.mul(slime, 0.15), 0.35)
    goo = b.mul(b.clamp01(b.maximum(pool, drips)), b.clamp01(b.mul(slime, 1.5)))
    col = b.mix_color(b.mul(goo, 0.85), col, I['Slime Color'])
    rough = b.mix(goo, rough, 0.02)
    metallic = b.mul(I['Metallic'], b.one_minus(goo))
    h = b.mix(b.mul(goo, 0.7), h, b.maximum(h, 0.42))

    film = b.mul(I['Iridescence'], b.madd(wz, 120.0, b.madd(wet, 250.0, 350.0)))

    skin = S.znoise(45.0, 12, detail=2.0, roughness=0.5, label='Skin')
    C.finish(b, gout, I, col, metallic, rough, h, b.mul(skin, 0.25), distance=ORGANIC_BUMP, extra={
        'Coat': b.maximum(b.mul(goo, 0.9), b.mul(wet, 0.3)),
        'Subsurface': I['Subsurface'],
        'Thin Film': film,
    })


SPEC = dict(
    label='Biomechanical', category='ORGANIC', params=ORGANIC_PARAMS, outputs=ORGANIC_OUTPUTS,
    build=build_organic,
    links={'Coat': 'Coat Weight', 'Subsurface': 'Subsurface Weight', 'Thin Film': 'Thin Film Thickness'},
    bsdf={'Coat Roughness': 0.03, 'Subsurface Scale': 0.02, 'Thin Film IOR': 1.4},
    display=('Base Color', 'Metallic', 'Roughness'), bump=ORGANIC_BUMP,
)
