# SPDX-License-Identifier: GPL-3.0-or-later
"""Bare metal generator: polished, brushed, hammered, galvanized, tarnished and rusty metals."""

from . import features as F
from . import gencommon as C
from .nodebuilder import is_socket

METAL_PARAMS = [
    # -- Base
    C.color('Metal Color', C.STEEL, 'Base', 'Reflection color of the metal', key=True),
    C.fac('Roughness', 0.25, 'Base', 'How blurry reflections are: 0 = mirror, 1 = matte', key=True),
    C.fac('Roughness Variation', 0.3, 'Base', 'Uneven, blotchy glossiness'),
    C.fac('Color Variation', 0.15, 'Base', 'Subtle uneven brightness of the metal'),
    C.scale('Variation Scale', 2.0, 0.05, 100.0, 'Base', 'Size of the blotches (higher = smaller)'),
    # -- Finish
    C.fac('Brushed', 0.0, 'Finish', 'Fine parallel brush lines (brushed steel / aluminium)', key=True),
    C.scale('Brush Scale', 150.0, 1.0, 2000.0, 'Finish', 'Fineness of the brush lines'),
    C.Param('Brush Direction', 'VECTOR', (1.0, 0.0, 0.0), -1.0, 1.0, 'Finish',
            'Direction of the brush lines (object axes)', ui='AXIS'),
    C.fac('Hammered', 0.0, 'Finish', 'Hand-hammered dents'),
    C.scale('Hammer Scale', 8.0, 0.5, 200.0, 'Finish', 'Dent density (higher = smaller dents)'),
    C.fac('Grain', 0.0, 'Finish', 'Sandblasted / cast micro texture'),
    C.fac('Pitting', 0.0, 'Finish', 'Small pits and pores (cast iron, corrosion pits)'),
    C.scale('Pit Scale', 150.0, 5.0, 5000.0, 'Finish', 'Density of grain and pits'),
    C.fac('Spangle', 0.0, 'Finish', 'Crystal flake pattern of hot-dip galvanized steel'),
    C.scale('Spangle Scale', 12.0, 1.0, 500.0, 'Finish', 'Density of the crystal flakes'),
    C.fac('Heat Tint', 0.0, 'Finish', 'Rainbow temper colors of heated steel / titanium'),
    C.scale('Heat Tint Scale', 0.5, 0.05, 50.0, 'Finish', 'Size of the heat color bands'),
    # -- Wear
    C.fac('Scratches', 0.2, 'Wear', 'How many scratches', key=True),
    C.scale('Scratch Scale', 1.0, 0.05, 20.0, 'Wear', 'Scratch size (higher = smaller, denser)'),
    C.fac('Smudges', 0.0, 'Wear', 'Fingerprints and greasy smudges'),
    C.fac('Edge Polish', 0.0, 'Wear',
         'Edges worn to bare shiny metal (visible in Cycles and in baked textures)'),
    C.color('Edge Color', (0.62, 0.62, 0.62), 'Wear', 'Color of the worn edges'),
    C.Param('Edge Width', 'FLOAT', 0.035, 0.001, 0.3, 'Wear', 'Width of edge wear', subtype='DISTANCE'),
    # -- Aging
    C.fac('Tarnish', 0.0, 'Aging', 'Dark oxidation film (silver, brass, copper); heavier in crevices'),
    C.color('Tarnish Color', (0.30, 0.22, 0.12), 'Aging', 'Tint of the tarnish'),
    C.scale('Tarnish Scale', 3.0, 0.05, 100.0, 'Aging', 'Size of tarnish patches'),
    C.fac('Rust', 0.0, 'Aging', 'Share of the surface covered in rust or patina', key=True),
    C.color('Rust Color', C.RUST_A, 'Aging', 'Bright rust / patina color'),
    C.color('Rust Color 2', C.RUST_B, 'Aging', 'Dark rust / patina color'),
    C.scale('Rust Scale', 3.0, 0.05, 100.0, 'Aging', 'Size of rust patches'),
    C.fac('Dirt', 0.0, 'Aging', 'Grime in crevices (crevices need Cycles or baking)', key=True),
    C.color('Dirt Color', C.DIRT, 'Aging', 'Color of the grime'),
] + C.PATTERN_PARAMS

METAL_OUTPUTS = C.COMMON_OUTPUTS + [('Anisotropic', 'FLOAT'), ('Tangent', 'VECTOR')]

HEAT_STOPS = [
    (0.00, (0.75, 0.60, 0.35)),   # straw
    (0.22, (0.55, 0.33, 0.15)),   # bronze
    (0.42, (0.32, 0.13, 0.30)),   # purple
    (0.60, (0.12, 0.16, 0.42)),   # deep blue
    (0.80, (0.32, 0.45, 0.60)),   # light blue
    (1.00, (0.60, 0.60, 0.62)),   # grey
]


def build_metal(b, I, gout, tile):
    S = F.Space(b, tile, I['Scale'], I['Seed'], I['Tile Size'] if tile else 1.0)
    inv = b.div(1.0, I['Scale'])
    edge = F.edge_mask(b, S, b.mul(I['Edge Width'], inv))
    cav = F.cavity_mask(b, S, b.mul(inv, 0.3))
    has_geo = is_socket(edge)

    # base variation (z = standard deviations)
    zv1 = S.znoise(I['Variation Scale'], 1, detail=3.0, roughness=0.55, label='Color Variation')
    zv2 = S.znoise(b.mul(I['Variation Scale'], 3.1), 2, detail=4.0, roughness=0.6, label='Roughness Variation')
    color = b.color_scale(I['Metal Color'], b.madd(zv1, b.mul(I['Color Variation'], 0.12), 1.0))
    rough = b.madd(zv2, b.mul(I['Roughness Variation'], 0.07), I['Roughness'])

    # heat tint
    hz = S.znoise(I['Heat Tint Scale'], 3, detail=1.5, roughness=0.45, distortion=0.6, label='Heat Tint')
    heat = b.ramp(b.linstep(-2.2, 2.2, hz), HEAT_STOPS, label='Temper Colors')
    color = b.mix_color(I['Heat Tint'], color, heat)

    # brushed lines
    stretch = 1.0 / C.BRUSH_STRETCH
    if tile:
        dx, dy, dz = b.separate(I['Brush Direction'])
        horiz = b.math('GREATER_THAN', b.absolute(dx), b.maximum(b.absolute(dy), b.absolute(dz)))
        aniso = (b.mix(horiz, 1.0, stretch), b.mix(horiz, stretch, 1.0))
        base = None
        brush_dir = None
    else:
        base, brush_dir = F.stretched_base(b, S, I['Brush Direction'], C.BRUSH_STRETCH)
        aniso = None
    bz1 = S.znoise(I['Brush Scale'], 4, detail=3.0, roughness=0.6, aniso=aniso, base=base, label='Brush Lines')
    bz2 = S.znoise(b.mul(I['Brush Scale'], 0.15), 5, detail=3.0, roughness=0.5, aniso=aniso, base=base,
                   label='Brush Variation')
    streak = b.mul(b.madd(bz1, 0.75, b.mul(bz2, 0.35)), I['Brushed'])
    rough = b.madd(streak, 0.035, rough)
    color = b.color_scale(color, b.madd(streak, 0.025, 1.0))
    h_micro = b.mul(streak, 0.2)

    # hammered dents
    hv = S.voronoi(I['Hammer Scale'], 6, feature='SMOOTH_F1', smoothness=0.25, label='Hammer Dents')
    dent = b.smoothstep(0.0, 0.75, hv.outputs['Distance'])
    hammered = I['Hammered']
    color = b.color_scale(color, b.madd(b.sub(dent, 0.5), b.mul(hammered, 0.15), 1.0))
    rough = b.madd(b.sub(0.5, dent), b.mul(hammered, 0.08), rough)
    h_macro = b.madd(b.sub(dent, 0.5), b.mul(hammered, 0.8), 0.5)

    # grain and pits
    gz = S.znoise(b.mul(I['Pit Scale'], 2.5), 7, detail=1.5, roughness=0.5, label='Grain')
    pz = S.znoise(I['Pit Scale'], 8, detail=2.0, roughness=0.55, label='Pits')
    pits = F.cover(b, pz, b.mul(I['Pitting'], 0.2), 0.2)
    color = b.color_scale(color, b.madd(pits, -0.5, 1.0))
    rough = b.madd(pits, 0.25, rough)
    h_macro = b.madd(pits, -0.5, h_macro)
    h_micro = b.add(h_micro, b.add(b.mul(gz, b.mul(I['Grain'], 0.08)), b.mul(pz, b.mul(I['Pitting'], 0.03))))
    rough = b.madd(I['Grain'], 0.05, rough)

    # galvanized spangle
    sv = S.voronoi(I['Spangle Scale'], 9, label='Spangle')
    sr, sg, sb = b.separate_color(sv.outputs['Color'])
    spangle = I['Spangle']
    color = b.color_scale(color, b.madd(b.sub(sr, 0.5), b.mul(spangle, 0.35), 1.0))
    rough = b.madd(b.sub(sg, 0.5), b.mul(spangle, 0.3), rough)
    h_micro = b.madd(b.sub(sb, 0.5), b.mul(spangle, 0.15), h_micro)

    # scratches
    scr = F.scratch_mask(b, S, I['Scratches'], I['Scratch Scale'], 20)
    rough = b.mix(scr, rough, b.mix(0.5, rough, 0.25))
    color = b.color_scale(color, b.madd(scr, 0.2, 1.0))
    h_micro = b.madd(scr, -0.6, h_micro)

    # smudges / fingerprints
    smz = S.znoise(2.5, 10, detail=4.0, roughness=0.55, distortion=0.8, label='Smudges')
    smudge = F.cover(b, smz, b.mul(I['Smudges'], 0.45), 0.6)
    rough = b.madd(smudge, 0.15, rough)
    color = b.color_scale(color, b.madd(smudge, -0.08, 1.0))

    # tarnish
    tz = S.znoise(I['Tarnish Scale'], 11, detail=3.0, roughness=0.55, distortion=0.4, label='Tarnish')
    film = b.madd(b.smoothstep(-1.8, 1.8, tz), 0.45, 0.55)  # an uneven but continuous film
    if has_geo:
        film = b.madd(cav, 0.6, b.madd(edge, -0.8, film))
    tarnish = b.clamp01(b.mul(film, I['Tarnish']))
    color = b.mix_color(tarnish, color, b.mix_color(1.0, color, I['Tarnish Color'], blend='MULTIPLY'))
    rough = b.madd(tarnish, 0.2, rough)

    # rust / patina
    rz = S.znoise(I['Rust Scale'], 12, detail=8.0, roughness=0.62, distortion=0.25, label='Rust Coverage')
    rz_fine = S.znoise(b.mul(I['Rust Scale'], 9.0), 18, detail=3.0, roughness=0.6, label='Rust Edges')
    rz = b.madd(rz_fine, 0.45, b.mul(rz, 0.9))
    if has_geo:
        rz = b.madd(cav, 2.0, b.madd(edge, 0.6, rz))
    rust = F.cover(b, rz, I['Rust'], 0.12)
    halo = b.mul(F.cover(b, rz, I['Rust'], 0.45, bias=-0.45), b.one_minus(rust))
    rust_col, rust_rough, rust_h = F.rust_layer(b, S, I['Rust Scale'], I['Rust Color'], I['Rust Color 2'], 13)
    color = b.mix_color(b.mul(halo, 0.6), color, b.mix_color(1.0, color, (0.42, 0.33, 0.26), blend='MULTIPLY'))
    rough = b.madd(halo, 0.15, rough)
    color = b.mix_color(rust, color, rust_col)
    metallic = b.one_minus(rust)
    rough = b.mix(rust, rough, rust_rough)
    h_macro = b.add(h_macro, b.mul(rust, b.madd(rust_h, 0.4, 0.05)))

    # worn, polished edges
    edge_w = F.broken(b, S, edge, 15)
    polish = b.mul(edge_w, I['Edge Polish'])
    color = b.mix_color(polish, color, I['Edge Color'])
    metallic = b.mix(polish, metallic, 1.0)
    rough = b.mix(polish, rough, b.mul(rough, 0.4))

    # dirt
    dirt = C.dirt_mask(b, S, I['Dirt'], cav, edge_w, 16)
    color = b.mix_color(dirt, color, I['Dirt Color'])
    metallic = b.mix(dirt, metallic, 0.0)
    rough = b.mix(dirt, rough, 0.92)
    h_macro = b.madd(dirt, 0.04, h_macro)

    # anisotropic highlights for brushed metal
    geo = b.geometry()
    if tile:
        tangent = geo.outputs['Tangent']
    else:
        world_dir = b.vmath('NORMALIZE', b.vector_transform(brush_dir))
        tangent = b.vmath('NORMALIZE', b.vmath('CROSS_PRODUCT', geo.outputs['Normal'], world_dir))
    C.finish(b, gout, I, color, metallic, rough, h_macro, h_micro,
            extra={'Anisotropic': b.mul(I['Brushed'], 0.65), 'Tangent': tangent})


SPEC = dict(
    label='Bare Metal', category='METAL', params=METAL_PARAMS, outputs=METAL_OUTPUTS, build=build_metal,
    links={'Anisotropic': 'Anisotropic', 'Tangent': 'Tangent'},
    display=('Metal Color', 1.0, 'Roughness'),
)
