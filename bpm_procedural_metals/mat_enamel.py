# SPDX-License-Identifier: GPL-3.0-or-later
"""Porcelain enamel generator: glass fused onto steel, like old stoves, bathtubs, enamelware
pots, enamel signs and the glossy appliances of the 1950s.

Enamel is a layer of glass, so it is deeply glossy (a clear coat on top) and does not wear
like paint: it chips.  A chip breaks through the colored cover coat to the dark blue-black
ground coat and, in its middle, to bare steel, which rusts and stains the enamel below.
Old enamel also crazes (a network of hairline cracks that catch dirt), dulls where it was
scoured and thins on sharp edges, where the dark ground coat shows through.
"""

from . import features as F
from . import gencommon as C
from .nodebuilder import is_socket

GROUND_COAT = (0.012, 0.016, 0.035)  # cobalt blue-black

ENAMEL_PARAMS = [
    # -- Enamel
    C.color('Enamel Color', (0.80, 0.78, 0.70), 'Enamel', 'Color of the enamel', key=True),
    C.fac('Roughness', 0.06, 'Enamel', '0 = mirror-like glass, higher = satin or worn', key=True),
    C.fac('Depth', 0.8, 'Enamel', 'Glassy depth of the enamel: a clear glaze on top (render only)', key=True),
    C.fac('Color Variation', 0.06, 'Enamel', 'Slightly uneven color of the firing'),
    C.fac('Waviness', 0.3, 'Enamel', 'Soft waves in the surface, seen in reflections (pressed steel)'),
    C.fac('Orange Peel', 0.15, 'Enamel', 'Fine dimpled texture of sprayed enamel'),
    # -- Pattern
    C.fac('Speckles', 0.0, 'Decoration', 'Graniteware: little flecks of another color', key=True),
    C.color('Speckle Color', (0.85, 0.85, 0.82), 'Decoration', 'Color of the flecks'),
    C.scale('Speckle Scale', 70.0, 2.0, 1000.0, 'Decoration', 'Density of the flecks'),
    C.fac('Marbling', 0.0, 'Decoration', 'Agateware: swirled clouds of a second color'),
    C.color('Marble Color', (0.06, 0.08, 0.20), 'Decoration', 'Second color of the swirls'),
    C.scale('Marble Scale', 3.0, 0.1, 50.0, 'Decoration', 'Size of the swirls (higher = smaller)'),
    C.fac('Rim', 0.0, 'Decoration', 'Colored rim on the edges, like enamel mugs and bowls (needs Cycles, '
          'baking or mesh maps)'),
    C.color('Rim Color', (0.010, 0.020, 0.070), 'Decoration', 'Color of the rim'),
    C.Param('Rim Width', 'FLOAT', 0.006, 0.0005, 0.1, 'Decoration', 'Width of the rim', subtype='DISTANCE'),
    # -- Wear
    C.fac('Chips', 0.01, 'Wear', 'Share of the enamel chipped off all over (dropped pans, knocks)', key=True),
    C.fac('Edge Chips', 0.3, 'Wear', 'Chips on edges and corners (visible in Cycles and in baked textures)',
          key=True),
    C.Param('Edge Width', 'FLOAT', 0.02, 0.001, 0.3, 'Wear', 'Width of the chipped edge band',
            subtype='DISTANCE'),
    C.scale('Chip Scale', 8.0, 0.2, 200.0, 'Wear', 'Chip size (higher = smaller chips)'),
    C.fac('Ground Coat', 0.5, 'Wear', 'How much of the dark ground coat shows around the bare steel of a chip'),
    C.color('Ground Coat Color', GROUND_COAT, 'Wear', 'Color of the enamel ground coat'),
    C.fac('Thin Edges', 0.2, 'Wear', 'Enamel thinning on sharp edges, where the ground coat shines through'),
    C.fac('Crazing', 0.0, 'Wear', 'Network of hairline cracks in old enamel', key=True),
    C.scale('Craze Scale', 18.0, 1.0, 300.0, 'Wear', 'Size of the crazed pieces (higher = smaller)'),
    C.fac('Scratches', 0.1, 'Wear', 'Fine scratches and grey marks left by metal pots and tools'),
    C.scale('Scratch Scale', 2.0, 0.05, 20.0, 'Wear', 'Scratch size (higher = smaller, denser)'),
    C.fac('Dulling', 0.1, 'Wear', 'Patches scoured dull by years of cleaning'),
    # -- Steel
    C.color('Steel Color', C.STEEL, 'Steel Underneath', 'Bare steel in the chips'),
    C.fac('Rust', 0.6, 'Steel Underneath', 'How much of the bare steel has rusted', key=True),
    C.fac('Rust Stains', 0.0, 'Steel Underneath', 'Rust bleeding around chips and running down the enamel'),
    C.color('Rust Color', C.RUST_A, 'Steel Underneath', 'Bright rust color'),
    C.color('Rust Color 2', C.RUST_B, 'Steel Underneath', 'Dark rust color'),
    # -- Aging
    C.fac('Yellowing', 0.0, 'Aging', 'Old enamel and appliance paint turning cream and yellow'),
    C.fac('Chalking', 0.0, 'Aging', 'Weathered, powdery, faded surface (outdoor signs)'),
    C.fac('Grease', 0.0, 'Aging', 'Sticky brown kitchen grease, thicker in corners'),
    C.fac('Dirt', 0.1, 'Aging', 'Grime in crevices and crazing (crevices need Cycles or baking)', key=True),
    C.color('Dirt Color', C.DIRT, 'Aging', 'Color of the grime'),
] + C.PATTERN_PARAMS

ENAMEL_OUTPUTS = C.COMMON_OUTPUTS + [('Coat', 'FLOAT')]

YELLOWED = (1.0, 0.80, 0.50)
GREASE = (0.30, 0.17, 0.05)
POT_MARK = (0.22, 0.22, 0.23)


def build_enamel(b, I, gout, tile):
    S = F.Space(b, tile, I['Scale'], I['Seed'], I['Tile Size'] if tile else 1.0)
    inv = b.div(1.0, I['Scale'])
    edge = F.edge_mask(b, S, b.mul(I['Edge Width'], inv))
    rim_edge = F.edge_mask(b, S, b.mul(I['Rim Width'], inv))
    cav = F.cavity_mask(b, S, b.mul(inv, 0.25))
    has_geo = is_socket(edge)

    # ---- enamel color: firing variation, agateware swirls, graniteware flecks
    zv = S.znoise(2.0, 1, detail=3.0, roughness=0.5, label='Color Variation')
    col = b.color_scale(I['Enamel Color'], b.madd(zv, b.mul(I['Color Variation'], 0.1), 1.0))
    mz = S.znoise(I['Marble Scale'], 2, detail=5.0, roughness=0.6, distortion=1.5, label='Marbling')
    swirl = b.mul(b.smoothstep(-0.4, 0.6, mz), I['Marbling'])
    col = b.mix_color(swirl, col, I['Marble Color'])
    sv = S.voronoi(I['Speckle Scale'], 3, label='Speckles')
    s_rand = b.separate_color(sv.outputs['Color'])
    fleck = b.one_minus(b.smoothstep(0.16, 0.24, b.div(sv.outputs['Distance'], b.madd(s_rand[2], 0.8, 0.6))))
    fleck = b.mul(fleck, b.math('LESS_THAN', s_rand[0], b.mul(I['Speckles'], 0.9)))
    col = b.mix_color(fleck, col, b.mix_color(s_rand[1], I['Speckle Color'], b.color_scale(I['Speckle Color'], 0.7)))

    if has_geo:
        rim = b.mul(b.smoothstep(0.35, 0.6, rim_edge), I['Rim'])
        col = b.mix_color(rim, col, I['Rim Color'])
        thin = b.mul(F.broken(b, S, edge, 4, 40.0), b.mul(I['Thin Edges'], 0.65))
        col = b.mix_color(thin, col, b.mix_color(0.25, I['Ground Coat Color'], col))

    rough = b.madd(zv, 0.01, I['Roughness'])

    # ---- chips: ragged flakes, mostly on edges, plus round impact chips
    field = F.chip_field(b, S, I['Chip Scale'], 0.25, edge, cav, I['Edge Chips'], 5)
    bare, ground = F.chip_layers(b, field, b.mul(I['Chips'], 0.5), I['Edge Chips'], I['Ground Coat'])
    iv = S.voronoi(b.mul(I['Chip Scale'], 0.6), 7, label='Impact Chips')
    i_rand = b.separate_color(iv.outputs['Color'])
    radius = b.madd(i_rand[1], 0.25, 0.12)
    hit = b.math('LESS_THAN', i_rand[0], b.mul(I['Chips'], 1.5))
    dist = iv.outputs['Distance']
    i_ground = b.mul(b.one_minus(b.smoothstep(b.sub(radius, 0.02), radius, dist)), hit)
    core = b.mul(radius, b.madd(I['Ground Coat'], -0.55, 0.9))
    i_bare = b.mul(b.one_minus(b.smoothstep(b.sub(core, 0.03), core, dist)), hit)
    bare = b.maximum(bare, i_bare)
    ground = b.maximum(ground, b.maximum(i_ground, bare))

    # ---- steel and rust in the chips
    zm = S.znoise(6.0, 8, detail=3.0, label='Steel Variation')
    rz = S.znoise(5.0, 9, detail=6.0, roughness=0.6, label='Rust')
    rust = b.mul(bare, F.cover(b, rz, I['Rust'], 0.35))
    rust_col, rust_rough, rust_h = F.rust_layer(b, S, 3.0, I['Rust Color'], I['Rust Color 2'], 10)
    # stains: rust bleeding into the enamel around chips and running down from them (object Z)
    near = b.smoothstep(b.sub(F.amount_to_z(b, b.maximum(b.mul(I['Chips'], 0.5), 0.002)), 0.9),
                        F.amount_to_z(b, b.maximum(b.mul(I['Chips'], 0.5), 0.002)), field)
    halo = b.mul(b.mul(near, b.one_minus(ground)), b.mul(I['Rust Stains'], 0.7))
    halo = b.maximum(halo, b.mul(b.one_minus(b.smoothstep(radius, b.mul(radius, 1.8), dist)),
                                 b.mul(hit, b.mul(I['Rust Stains'], 0.6))))
    aniso = (1.0, 1.0 / 12.0) if tile else (1.0, 1.0, 1.0 / 12.0)
    stz = S.znoise(5.0, 11, detail=4.0, roughness=0.6, aniso=aniso, label='Rust Streaks')
    smz = S.znoise(1.0, 12, detail=2.0, label='Streak Mask')
    streak = b.mul(F.cover(b, stz, b.mul(I['Rust Stains'], 0.3), 0.5), F.cover(b, smz, 0.5, 0.8, gate=False))
    stain = b.clamp01(b.mul(b.maximum(halo, b.mul(streak, 0.7)), b.one_minus(ground)))
    stain_col = b.mix_color(0.5, I['Rust Color'], b.color_scale(I['Rust Color'], 1.6))

    # ---- crazing: hairline cracks with dirt in them
    craze_d = F.crack_distance(b, S, I['Craze Scale'], 13, warp=0.6, label='Crazing')
    craze_on = F.cover(b, S.znoise(b.mul(I['Craze Scale'], 0.12), 15, detail=3.0, roughness=0.6,
                                   label='Craze Patches'), I['Crazing'], 0.6)
    craze = b.mul(b.one_minus(b.smoothstep(0.004, 0.014, craze_d)), craze_on)

    # ---- scratches (grey pot marks) and scoured, dull patches
    scr = F.scratch_mask(b, S, I['Scratches'], I['Scratch Scale'], 16)
    dz = S.znoise(2.5, 18, detail=4.0, roughness=0.6, label='Dulling')
    if has_geo:
        dz = b.madd(edge, 1.0, b.madd(cav, -1.0, dz))
    dull = b.mul(F.cover(b, dz, b.mul(I['Dulling'], 0.6), 0.7), 0.9)

    # ---- aging
    az = S.znoise(1.2, 19, detail=3.0, roughness=0.5, label='Aging')
    yellow = b.clamp01(b.mul(I['Yellowing'], b.madd(az, 0.2, 0.9)))
    col = b.mix_color(b.mul(yellow, 0.8), col, b.mix_color(1.0, col, YELLOWED, blend='MULTIPLY'))
    chalk = b.clamp01(b.mul(I['Chalking'], b.madd(az, 0.25, 1.0)))
    col = b.mix_color(b.mul(chalk, 0.6), col, b.mix_color(0.35, b.hsv(col, saturation=0.55, value=1.35),
                                                         (0.62, 0.62, 0.6)))
    gz = S.znoise(1.8, 20, detail=4.0, roughness=0.6, label='Grease')
    if has_geo:
        gz = b.madd(cav, 2.0, gz)
    grease = b.mul(F.cover(b, gz, b.mul(I['Grease'], 0.7), 0.9), b.madd(I['Grease'], 0.5, 0.4))
    dirt = C.dirt_mask(b, S, I['Dirt'], cav, edge, 22, extra=b.mul(craze, 2.0), spots=0.2)
    dirt = b.maximum(dirt, b.mul(craze, b.madd(I['Dirt'], 0.6, 0.3)))

    # ---- compose
    col = b.mix_color(stain, col, stain_col)
    col = b.mix_color(b.mul(scr, 0.6), col, b.mix_color(0.5, col, POT_MARK))
    col = b.mix_color(b.mul(dull, 0.25), col, b.hsv(col, saturation=0.85, value=1.08))
    col = b.mix_color(ground, col, I['Ground Coat Color'])
    steel = b.color_scale(I['Steel Color'], b.madd(zm, 0.06, 1.0))
    col = b.mix_color(bare, col, steel)
    col = b.mix_color(rust, col, rust_col)
    col = b.mix_color(b.mul(grease, 0.7), col, b.mix_color(1.0, col, GREASE, blend='MULTIPLY'))
    col = b.mix_color(dirt, col, I['Dirt Color'])

    metallic = b.mul(bare, b.one_minus(b.maximum(rust, dirt)))

    rough = b.madd(chalk, 0.5, rough)
    rough = b.mix(dull, rough, b.add(I['Roughness'], 0.3))
    rough = b.mix(b.mul(scr, 0.7), rough, b.add(I['Roughness'], 0.35))
    rough = b.mix(stain, rough, b.add(rough, 0.15))
    rough = b.mix(ground, rough, 0.12)
    rough = b.mix(bare, rough, b.madd(zm, 0.05, 0.4))
    rough = b.mix(rust, rough, rust_rough)
    rough = b.mix(grease, rough, 0.3)
    rough = b.mix(dirt, rough, 0.85)

    glaze = b.one_minus(b.maximum(b.maximum(ground, dirt), b.maximum(b.mul(dull, 0.7), chalk)))
    coat = b.mul(b.mul(I['Depth'], glaze), b.madd(grease, -0.4, 1.0))

    # ---- relief: the glassy layer, steps down into the chips, waves and orange peel
    wz = S.znoise(0.8, 23, detail=2.0, roughness=0.4, label='Waviness')
    layers = b.sub(b.madd(ground, -0.4, 1.0), b.mul(bare, 0.4))
    h_macro = b.madd(b.sub(layers, 0.5), 0.6, 0.5)
    h_macro = b.madd(wz, b.mul(I['Waviness'], 0.025), h_macro)
    h_macro = b.add(h_macro, b.mul(rust, b.madd(rust_h, 0.3, -0.1)))
    opz = S.znoise(180.0, 24, detail=2.0, roughness=0.4, label='Orange Peel')
    h_micro = b.mul(b.mul(opz, b.mul(I['Orange Peel'], 0.05)), b.one_minus(ground))
    h_micro = b.madd(craze, -0.5, h_micro)
    h_micro = b.madd(scr, -0.3, h_micro)
    h_micro = b.madd(fleck, b.mul(I['Speckles'], 0.08), h_micro)

    C.finish(b, gout, I, col, metallic, rough, h_macro, h_micro, extra={'Coat': coat})


SPEC = dict(
    label='Porcelain Enamel', category='ENAMEL', params=ENAMEL_PARAMS, outputs=ENAMEL_OUTPUTS,
    build=build_enamel, links={'Coat': 'Coat Weight'}, bsdf={'Coat Roughness': 0.02, 'Coat IOR': 1.52},
    display=('Enamel Color', 0.0, 'Roughness'),
)
