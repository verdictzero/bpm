# SPDX-License-Identifier: GPL-3.0-or-later
"""Plastic generator: glossy, matte or textured molded plastic, new or worn and dirty, and
plastic that had a hard life: cracked, gouged, burnt, stained and sticky with old labels.

Marbling (bakelite, swirled recycled plastic) and glitter flakes widen the range of looks."""

from . import features as F
from . import gencommon as C
from .nodebuilder import is_socket

PLASTIC_PARAMS = [
    # -- Plastic
    C.color('Plastic Color', (0.55, 0.035, 0.025), 'Plastic', 'Color of the plastic', key=True),
    C.fac('Roughness', 0.35, 'Plastic', '0 = glossy, 1 = matte', key=True),
    C.fac('Color Variation', 0.1, 'Plastic', 'Subtle mottling (recycled / cheap plastic)'),
    C.fac('Speckles', 0.0, 'Plastic', 'Colored flecks, like recycled plastic'),
    C.color('Speckle Color', (0.75, 0.75, 0.72), 'Plastic', 'Color of the flecks'),
    C.scale('Speckle Scale', 60.0, 1.0, 2000.0, 'Plastic', 'Density of the flecks'),
    C.fac('Subsurface', 0.0, 'Plastic', 'Light shining through soft or thin plastic (render only)'),
    C.fac('Clear Coat', 0.0, 'Plastic', 'Glossy lacquer on top, like piano black (render only)'),
    C.fac('Marbling', 0.0, 'Plastic', 'Swirls of a second color, like bakelite or swirled recycled plastic'),
    C.color('Marble Color', (0.04, 0.012, 0.005), 'Plastic', 'Color of the swirls'),
    C.scale('Marble Scale', 3.0, 0.1, 100.0, 'Plastic', 'Size of the swirls (higher = smaller)'),
    C.fac('Glitter', 0.0, 'Plastic', 'Sparkling metal flakes in the plastic'),
    C.color('Glitter Color', (0.8, 0.8, 0.8), 'Plastic', 'Color of the flakes'),
    C.scale('Glitter Scale', 150.0, 10.0, 5000.0, 'Plastic', 'Density of the flakes (higher = finer)'),
    # -- Surface
    C.fac('Stipple', 0.0, 'Surface', 'Fine molded texture of matte plastic parts', key=True),
    C.scale('Stipple Scale', 300.0, 10.0, 5000.0, 'Surface', 'Fineness of the texture'),
    C.fac('Leather Grain', 0.0, 'Surface', 'Embossed leather-like grain (dashboards, cases)'),
    C.scale('Grain Scale', 120.0, 5.0, 2000.0, 'Surface', 'Size of the grain (higher = finer)'),
    C.fac('Ribs', 0.0, 'Surface', 'Parallel ridges (grips, ribbed panels)'),
    C.Param('Rib Spacing', 'FLOAT', 0.006, 0.0005, 0.5, 'Surface', 'Distance between the ridges',
            subtype='DISTANCE'),
    C.axis('Rib Direction', (0.0, 0.0, 1.0), 'Surface', 'Direction across the ridges'),
    # -- Wear
    C.fac('Scratches', 0.1, 'Wear', 'Fine, whitish scratches', key=True),
    C.scale('Scratch Scale', 2.5, 0.05, 20.0, 'Wear', 'Scratch size (higher = smaller, denser)'),
    C.fac('Scuffs', 0.15, 'Wear', 'Rubbed patches: duller on glossy plastic, shinier on textured', key=True),
    C.fac('Edge Whitening', 0.2, 'Wear', 'Pale, stressed edges (visible in Cycles and in baked textures)'),
    C.Param('Edge Width', 'FLOAT', 0.015, 0.001, 0.3, 'Wear', 'Width of the edge wear', subtype='DISTANCE'),
    C.fac('Smudges', 0.1, 'Wear', 'Fingerprints and greasy smudges'),
    # -- Aging
    C.fac('Fading', 0.0, 'Aging', 'Sun-faded, chalky plastic'),
    C.fac('Yellowing', 0.0, 'Aging', 'Old plastic turning yellow (retro computers, old toys)'),
    C.fac('Dirt', 0.1, 'Aging', 'Grime in crevices and corners (needs Cycles or baking)', key=True),
    C.fac('Grime', 0.0, 'Aging', 'Dirt stuck in the surface texture'),
    C.color('Dirt Color', C.DIRT, 'Aging', 'Color of the grime'),
    # -- Damage
    C.fac('Cracks', 0.0, 'Damage', 'Stress cracks with whitened plastic around them', key=True),
    C.scale('Crack Scale', 4.0, 0.2, 100.0, 'Damage', 'Size of the cracked pieces (higher = smaller)'),
    C.fac('Gouges', 0.0, 'Damage', 'Deep knife and tool cuts, pale and full of dirt (cutting boards)'),
    C.fac('Burns', 0.0, 'Damage', 'Melted, charred and blistered spots, with a brown scorched halo', key=True),
    C.scale('Burn Scale', 3.0, 0.1, 100.0, 'Damage', 'Size of the burns (higher = smaller)'),
    C.fac('Stains', 0.0, 'Damage', 'Blotchy stains with dark tide lines (food, coffee, oil)'),
    C.color('Stain Color', (0.45, 0.20, 0.06), 'Damage', 'Tint of the stains'),
    C.fac('Residue', 0.0, 'Damage', 'Scraped-off stickers and tape: torn paper and gummy glue catching dirt'),
] + C.PATTERN_PARAMS

PLASTIC_OUTPUTS = C.COMMON_OUTPUTS + [('Coat', 'FLOAT'), ('Subsurface', 'FLOAT')]

YELLOWED = (1.0, 0.78, 0.42)
CHAR = (0.012, 0.010, 0.008)
SCORCH = (0.30, 0.14, 0.05)  # brown halo around a burn (multiplied)
PAPER = (0.62, 0.60, 0.52)
GLUE = (0.55, 0.42, 0.20)  # yellowed adhesive (multiplied)
GOUGE_LAYERS = (
    # freq, half-width, stretch, strength
    (2.5, 0.022, 30.0, 1.0),
    (5.0, 0.015, 22.0, 0.8),
)


def build_plastic(b, I, gout, tile):
    S = F.Space(b, tile, I['Scale'], I['Seed'], I['Tile Size'] if tile else 1.0)
    inv = b.div(1.0, I['Scale'])
    edge = F.edge_mask(b, S, b.mul(I['Edge Width'], inv))
    cav = F.cavity_mask(b, S, b.mul(inv, 0.25))

    # ---- base
    zv = S.znoise(2.5, 1, detail=4.0, roughness=0.55, label='Color Variation')
    zr = S.znoise(6.0, 2, detail=3.0, roughness=0.55, label='Gloss Variation')
    col = b.color_scale(I['Plastic Color'], b.madd(zv, b.mul(I['Color Variation'], 0.08), 1.0))
    rough = b.madd(zr, 0.025, I['Roughness'])

    # flecks: some voronoi cells become colored chips
    sv = S.voronoi(I['Speckle Scale'], 3, label='Speckles')
    s_rand = b.separate_color(sv.outputs['Color'])
    fleck = b.one_minus(b.smoothstep(0.18, 0.26, sv.outputs['Distance']))
    fleck = b.mul(fleck, b.math('LESS_THAN', s_rand[0], b.mul(I['Speckles'], 0.8)))
    fleck_col = b.mix_color(s_rand[1], I['Speckle Color'], b.color_scale(I['Speckle Color'], 0.45))
    col = b.mix_color(fleck, col, fleck_col)

    # marbling: warped clouds of a second color, with streaky veins
    mz = S.znoise(I['Marble Scale'], 40, detail=4.0, roughness=0.55, distortion=1.5, label='Marbling')
    marble = F.cover(b, mz, b.mul(I['Marbling'], 0.6), 0.35)
    mv = S.noise(b.mul(I['Marble Scale'], 0.7), 41, detail=3.0, roughness=0.5, distortion=3.0, label='Marble Veins')
    vein = b.mul(b.one_minus(b.smoothstep(0.0, 0.025, b.absolute(b.sub(mv, 0.5)))), b.clamp01(b.mul(I['Marbling'], 2.0)))
    col = b.mix_color(b.maximum(marble, b.mul(vein, 0.6)), col, I['Marble Color'])

    # glitter: random cells become metal flakes, each tilted differently (bright or dark)
    gv = S.voronoi(I['Glitter Scale'], 42, label='Glitter')
    g_rand = b.separate_color(gv.outputs['Color'])
    flake = b.mul(b.one_minus(b.smoothstep(0.30, 0.38, gv.outputs['Distance'])),
                  b.math('LESS_THAN', g_rand[0], b.mul(I['Glitter'], 0.8)))
    tilt = b.mul(g_rand[1], b.mul(g_rand[1], g_rand[1]))  # few flakes catch the light: bright, most are dim
    col = b.mix_color(flake, col, b.color_scale(I['Glitter Color'], b.madd(tilt, 2.5, 0.12)))
    rough = b.mix(flake, rough, b.madd(g_rand[2], 0.2, 0.08))

    # ---- surface textures
    stz = S.znoise(I['Stipple Scale'], 4, detail=2.0, roughness=0.5, label='Stipple')
    stipple = I['Stipple']
    rough = b.madd(stipple, 0.14, rough)
    lv = S.voronoi(I['Grain Scale'], 5, feature='DISTANCE_TO_EDGE', label='Leather Grain')
    pebble = b.smoothstep(0.0, 0.3, lv.outputs['Distance'])
    grain = I['Leather Grain']
    if tile:
        span = b.mul(I['Tile Size'], I['Scale'])
        count = b.maximum(1.0, b.math('ROUND', b.div(span, I['Rib Spacing'])))
        x = b.mul(S.v, count)
    else:
        x = b.div(b.vmath('DOT_PRODUCT', S.P, b.vmath('NORMALIZE', I['Rib Direction'])), I['Rib Spacing'])
    t = b.sub(b.mul(b.fract(x), 2.0), 1.0)
    rib = b.one_minus(b.mul(t, t))  # rounded ridge, 0 in the grooves
    ribs = I['Ribs']
    # texture height (0..1-ish) used for grime and scuffs
    tex_h = b.madd(b.mul(stz, 0.15), stipple, b.madd(b.sub(pebble, 0.5), grain, b.madd(b.sub(rib, 0.5), ribs, 0.5)))

    # ---- wear
    e = b.mul(F.broken(b, S, edge, 10, 30.0), I['Edge Whitening']) if is_socket(edge) else 0.0
    scr = F.scratch_mask(b, S, I['Scratches'], I['Scratch Scale'], 20)
    scuff_z = S.znoise(3.0, 21, detail=5.0, roughness=0.6, label='Scuffs')
    if is_socket(edge):
        scuff_z = b.madd(edge, 2.0, scuff_z)
    scuff = b.mul(F.cover(b, scuff_z, b.mul(I['Scuffs'], 0.45), 0.6), 0.8)
    smz = S.znoise(5.0, 22, detail=4.0, roughness=0.6, label='Smudges')
    smudge = b.mul(F.cover(b, smz, b.mul(I['Smudges'], 0.4), 0.5), 0.7)

    pale = b.mix_color(0.55, col, (0.8, 0.8, 0.78))
    col = b.mix_color(b.maximum(b.mul(e, 0.7), b.mul(scr, 0.3)), col, pale)
    rough = b.mix(b.maximum(e, b.mul(scr, 0.7)), rough, b.add(rough, 0.2))
    # rubbing dulls glossy plastic but polishes textured plastic
    scuffed = b.mix(b.maximum(stipple, grain), b.add(I['Roughness'], 0.22), b.sub(I['Roughness'], 0.1))
    rough = b.mix(scuff, rough, scuffed)
    rough = b.mix(smudge, rough, 0.45)

    # ---- aging
    az = S.znoise(1.5, 23, detail=3.0, roughness=0.5, label='Aging')
    fade = b.clamp01(b.mul(I['Fading'], b.madd(az, 0.1, 1.0)))
    chalky = b.mix_color(0.25, b.hsv(col, saturation=0.6, value=1.45), (0.62, 0.62, 0.6))
    col = b.mix_color(fade, col, chalky)
    rough = b.madd(fade, 0.25, rough)
    yellow = b.clamp01(b.mul(I['Yellowing'], b.madd(az, -0.25, 1.0)))
    col = b.mix_color(b.mul(yellow, 0.75), col, b.color_scale(b.mix_color(1.0, col, YELLOWED, blend='MULTIPLY'), 0.92))

    # ---- damage
    # stress cracks: thin dark lines in a band of whitened plastic
    crack_d = F.crack_distance(b, S, I['Crack Scale'], 50, label='Cracks')
    crack_on = F.cover(b, S.znoise(b.mul(I['Crack Scale'], 0.35), 52, detail=3.0, roughness=0.6,
                                   label='Crack Patches'), b.mul(I['Cracks'], 0.85), 0.5)
    crack = b.mul(b.one_minus(b.smoothstep(0.003, 0.012, crack_d)), crack_on)
    stress = b.mul(b.one_minus(b.smoothstep(0.0, 0.06, crack_d)), crack_on)
    col = b.mix_color(b.mul(stress, 0.6), col, pale)
    # gouges: deep, wide cuts with frayed pale walls
    gp = S.znoise(b.mul(I['Scratch Scale'], 2.0), 60, detail=2.0, roughness=0.5, label='Gouge Patches')
    gt = F.amount_to_z(b, b.mul(I['Gouges'], 0.7))
    gouge = b.mul(F.scratch_lines(b, S, b.mul(I['Scratch Scale'], 0.5), 61, layers=GOUGE_LAYERS),
                  b.smoothstep(b.sub(gt, 0.4), b.add(gt, 0.4), gp))
    gouge = b.mul(gouge, b.clamp01(b.mul(I['Gouges'], 25.0)))
    col = b.mix_color(b.mul(gouge, 0.5), col, pale)
    rough = b.mix(gouge, rough, b.add(rough, 0.25))
    # burns: charred, blistered core in a melted brown halo
    bz = S.znoise(I['Burn Scale'], 70, detail=5.0, roughness=0.65, label='Burns')
    core = F.cover(b, bz, b.mul(I['Burns'], 0.22), 0.2)
    halo = F.cover(b, bz, b.mul(I['Burns'], 0.7), 0.9)
    blist = S.voronoi(b.mul(I['Burn Scale'], 12.0), 71, label='Blisters')
    bubble = b.one_minus(b.smoothstep(0.0, 0.55, blist.outputs['Distance']))
    scorched = b.mix_color(0.5, b.mix_color(1.0, col, SCORCH, blend='MULTIPLY'), b.color_scale(SCORCH, 0.6))
    col = b.mix_color(b.mul(halo, 0.9), col, scorched)
    col = b.mix_color(core, col, b.mix_color(bubble, CHAR, (0.05, 0.035, 0.025)))
    rough = b.mix(halo, rough, b.mul(rough, 0.6))  # melted skin is glossy
    rough = b.mix(core, rough, b.madd(bubble, -0.35, 0.75))
    # stains: soaked-in blotches with darker tide lines at their edge
    stz2 = S.znoise(1.8, 80, detail=4.0, roughness=0.55, label='Stains')
    stain = F.cover(b, stz2, b.mul(I['Stains'], 0.5), 0.5)
    tide = b.mul(b.mul(stain, b.one_minus(stain)), 4.0)
    stained = b.mix_color(1.0, col, I['Stain Color'], blend='MULTIPLY')
    col = b.mix_color(b.clamp01(b.madd(stain, 0.6, b.mul(tide, 0.5))), col, stained)
    # sticker residue: torn paper and yellowed glue in scraped patches
    rz = S.znoise(3.0, 90, detail=6.0, roughness=0.7, label='Residue')
    glue = F.cover(b, rz, b.mul(I['Residue'], 0.4), 0.15)
    paper = b.mul(glue, F.cover(b, S.znoise(14.0, 91, detail=5.0, roughness=0.7, label='Paper'), 0.25, 0.2))
    gummy = b.mix_color(0.45, b.mix_color(1.0, col, GLUE, blend='MULTIPLY'), b.color_scale(GLUE, 0.5))
    col = b.mix_color(b.mul(glue, 0.8), col, gummy)
    col = b.mix_color(paper, col, PAPER)
    rough = b.mix(glue, rough, 0.45)
    rough = b.mix(paper, rough, 0.9)

    # ---- dirt: crevices plus grime stuck in the low parts of the texture, cuts, cracks and glue
    stuck = b.mul(I['Grime'], b.one_minus(b.smoothstep(0.35, 0.55, tex_h)))
    stuck = b.maximum(stuck, b.maximum(b.mul(crack, 0.9), b.mul(gouge, 0.6)))
    stuck = b.maximum(stuck, b.mul(b.mul(glue, b.one_minus(paper)), 0.35))
    dirt = C.dirt_mask(b, S, I['Dirt'], cav, edge, 30, extra=stuck, spots=0.2)
    dirt = b.maximum(dirt, b.mul(stuck, 0.85))
    col = b.mix_color(dirt, col, I['Dirt Color'])
    rough = b.mix(dirt, rough, 0.85)

    coat = b.mul(I['Clear Coat'], b.one_minus(b.maximum(dirt, b.mul(scuff, 0.6))))

    # ---- relief
    flatten = b.one_minus(b.mul(scuff, 0.6))
    h_macro = b.madd(b.sub(pebble, 0.5), b.mul(grain, 0.05), 0.5)
    h_macro = b.madd(b.sub(rib, 0.5), b.mul(ribs, 0.25), h_macro)
    h_micro = b.mul(b.mul(stz, b.mul(stipple, 0.4)), flatten)
    h_micro = b.madd(scr, -0.5, h_micro)
    h_micro = b.madd(crack, -0.8, h_micro)
    h_micro = b.madd(gouge, -1.0, h_micro)
    h_micro = b.madd(b.sub(halo, core), 0.4, h_micro)  # melted rim
    h_micro = b.madd(core, b.madd(bubble, 0.8, -0.6), h_micro)  # sunken, blistered char
    h_micro = b.madd(glue, 0.15, b.madd(paper, 0.15, h_micro))
    h_micro = b.madd(flake, b.madd(g_rand[1], 0.3, -0.15), h_micro)
    metallic = b.mul(flake, b.one_minus(dirt))

    C.finish(b, gout, I, col, metallic, rough, h_macro, h_micro, extra={'Coat': coat, 'Subsurface': I['Subsurface']})


SPEC = dict(
    label='Plastic', category='PLASTIC', params=PLASTIC_PARAMS, outputs=PLASTIC_OUTPUTS, build=build_plastic,
    links={'Coat': 'Coat Weight', 'Subsurface': 'Subsurface Weight'},
    bsdf={'Coat Roughness': 0.03, 'Subsurface Scale': 0.01},
    display=('Plastic Color', 0.0, 'Roughness'),
    version=3,  # 3: marbling, glitter and damage
)
