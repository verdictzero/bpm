# SPDX-License-Identifier: GPL-3.0-or-later
"""Painted metal generator: chipped, scratched, rusty and dirty paint over metal."""

from . import features as F
from . import gencommon as C
from .nodebuilder import is_socket

PAINT_PARAMS = [
    # -- Paint
    C.color('Paint Color', (0.80, 0.42, 0.02), 'Paint', 'Main paint color', key=True),
    C.fac('Paint Roughness', 0.4, 'Paint', '0 = glossy, 1 = flat matte', key=True),
    C.fac('Paint Metallic', 0.0, 'Paint', 'Metallic paint (car paint, hammertone)'),
    C.fac('Paint Variation', 0.2, 'Paint', 'Uneven, blotchy paint'),
    C.scale('Variation Scale', 2.0, 0.05, 100.0, 'Paint', 'Size of the blotches'),
    C.fac('Orange Peel', 0.15, 'Paint', 'Fine bumpy texture of sprayed paint'),
    C.fac('Flakes', 0.0, 'Paint', 'Sparkly metallic flakes'),
    C.fac('Hammered', 0.0, 'Paint', 'Hammertone paint dimples'),
    C.scale('Hammer Scale', 30.0, 0.5, 300.0, 'Paint', 'Dimple density'),
    C.fac('Clear Coat', 0.0, 'Paint', 'Glossy varnish layer on top (render only, not baked)'),
    C.fac('Fading', 0.0, 'Paint', 'Sun-bleached, chalky old paint'),
    # -- Stripes
    C.fac('Stripes', 0.0, 'Stripes', 'Hazard-style stripes in a second color'),
    C.color('Stripe Color', (0.02, 0.02, 0.02), 'Stripes', 'Color of the stripes'),
    C.Param('Stripe Width', 'FLOAT', 0.12, 0.005, 10.0, 'Stripes', 'Width of each stripe', subtype='DISTANCE'),
    C.Param('Stripe Direction', 'VECTOR', (0.7071, 0.0, 0.7071), -1.0, 1.0, 'Stripes',
          'Direction across the stripes (object axes)'),
    # -- Wear
    C.fac('Wear', 0.04, 'Wear', 'Share of the paint chipped off all over (0.1 = 10%)', key=True),
    C.fac('Edge Wear', 0.6, 'Wear',
         'Paint chipped off on edges (visible in Cycles and in baked textures)', key=True),
    C.Param('Edge Width', 'FLOAT', 0.035, 0.001, 0.3, 'Wear', 'Width of edge wear', subtype='DISTANCE'),
    C.scale('Chip Scale', 5.0, 0.05, 100.0, 'Wear', 'Chip size (higher = smaller chips)'),
    C.fac('Chip Detail', 0.6, 'Wear', 'Ragged, detailed chip borders'),
    C.fac('Primer', 0.4, 'Wear', 'Visible primer layer around chips'),
    C.color('Primer Color', (0.32, 0.32, 0.30), 'Wear', 'Color of the primer'),
    C.fac('Paint Thickness', 0.5, 'Wear', 'Depth of chip edges'),
    C.fac('Scratches', 0.2, 'Wear', 'Scratches through the paint', key=True),
    C.scale('Scratch Scale', 1.0, 0.05, 20.0, 'Wear', 'Scratch size (higher = smaller, denser)'),
    # -- Metal
    C.color('Metal Color', C.STEEL, 'Metal Underneath', 'Bare metal under the paint'),
    C.fac('Metal Roughness', 0.35, 'Metal Underneath', 'Glossiness of the bare metal'),
    # -- Aging
    C.fac('Rust', 0.3, 'Aging', 'How much of the bare metal (chips, scratches) has rusted', key=True),
    C.fac('Rust Spread', 0.3, 'Aging', 'Rust creeping under the paint and rust spots'),
    C.fac('Rust Streaks', 0.0, 'Aging', 'Rust running down the paint (along object Z)'),
    C.color('Rust Color', C.RUST_A, 'Aging', 'Bright rust color'),
    C.color('Rust Color 2', C.RUST_B, 'Aging', 'Dark rust color'),
    C.scale('Rust Scale', 4.0, 0.05, 100.0, 'Aging', 'Size of rust patches'),
    C.fac('Dirt', 0.2, 'Aging', 'Grime in crevices (crevices need Cycles or baking)', key=True),
    C.color('Dirt Color', C.DIRT, 'Aging', 'Color of the grime'),
] + C.PATTERN_PARAMS

PAINT_OUTPUTS = C.COMMON_OUTPUTS + [('Coat', 'FLOAT')]


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
    dirt = C.dirt_mask(b, S, I['Dirt'], cav, edge, 15, extra=b.mul(metal, 0.3))

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

    C.finish(b, gout, I, color, metallic, rough, h_macro, h_micro, extra={'Coat': coat})


SPEC = dict(
    label='Painted Metal', category='PAINT', params=PAINT_PARAMS, outputs=PAINT_OUTPUTS, build=build_paint,
    links={'Coat': 'Coat Weight'}, bsdf={'Coat Roughness': 0.03},
    display=('Paint Color', 0.0, 'Paint Roughness'),
)
