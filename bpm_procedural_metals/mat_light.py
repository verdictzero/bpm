# SPDX-License-Identifier: GPL-3.0-or-later
"""Light generator: glowing neon tubes, fluorescent tubes, light panels, LED dots and strips
and screens, clean or dusty, grimy, full of dead bugs, blackened and burnt out.

Everything on top of the light (dust, grime, bugs, soot, cracks) also blocks its glow, so a
dirty light is dimmer and blotchy where the dirt is, and grime tints the light brown.  The
'Power' slider switches the light off: what is left is the look of the unlit tube or panel.
"""

from . import features as F
from . import gencommon as C
from .mat_gradient import _choose, _enum, _is
from .nodebuilder import is_socket

TYPES = (('Neon Tube', 0), ('Panel', 1), ('LED Dots', 2), ('Screen', 3), ('Strips', 4))
END_AXES = (('UV', 0), ('X', 1), ('Y', 2), ('Z', 3))

LIGHT_PARAMS = [
    # -- Light
    _enum('Type', 0, TYPES, 'Light',
          'Neon Tube: a glowing glass tube (brightest where it faces you). Panel: a glowing diffuser, '
          'optionally with the hot spots of the lamps behind it. LED Dots: a grid of glowing dots. '
          'Screen: red, green and blue pixels. Strips: rows of glowing lines', key=True),
    C.color('Light Color', (1.0, 0.08, 0.03), 'Light', 'Color of the light', key=True),
    C.Param('Emission Strength', 'FLOAT', 1.0, 0.0, 500.0, 'Light', 'Brightness of the glow', key=True),
    C.fac('Power', 1.0, 'Light', '1 = switched on, 0 = off (shows the unlit tube or panel)', key=True),
    C.fac('Core Falloff', 0.8, 'Light', 'Neon tubes: dimmer toward the sides of the tube, brighter in the core'),
    C.Param('Grid Size', 'FLOAT', 0.01, 0.0002, 1.0, 'Light',
            'Spacing of the dots, pixels, strips or panel hot spots', subtype='DISTANCE'),
    C.fac('Fill', 0.6, 'Light', 'Size of the dots or width of the strips, compared to their spacing'),
    C.fac('Hot Spots', 0.0, 'Light', 'Panels: the lamps behind the diffuser show as brighter spots'),
    C.fac('Scanlines', 0.0, 'Light', 'Screens: dark lines between the rows, like an old CRT monitor'),
    C.color('Surface Color', (0.75, 0.75, 0.72), 'Light',
            'Color of the glass, diffuser or board when unlit (and between the dots)'),
    C.fac('Roughness', 0.15, 'Light', '0 = glossy glass, 1 = frosted / matte'),
    # -- Faults
    C.fac('Unevenness', 0.15, 'Faults', 'Patchy brightness (aging gas, tired phosphor, cheap LEDs)'),
    C.fac('Dead Sections', 0.0, 'Faults', 'Parts that no longer light up (dead pixels on grids)', key=True),
    C.fac('End Blackening', 0.0, 'Faults', 'Dark, sooty tube ends, like old neon and fluorescent tubes',
          key=True),
    C.fac('End Length', 0.08, 'Faults', 'How far the blackening reaches into the tube (share of its length)'),
    _enum('Ends Along', 0, END_AXES, 'Faults',
          'Where the ends of the tube are: along the UV map (U, bent neon from curves) or along the '
          'object\'s X, Y or Z axis (straight tubes)'),
    C.fac('Yellowing', 0.0, 'Faults', 'Old, yellowed diffuser or glass: tints the light'),
    C.fac('Cracks', 0.0, 'Faults', 'Cracked glass or plastic cover'),
    C.scale('Crack Scale', 6.0, 0.5, 100.0, 'Faults', 'Size of the cracked pieces (higher = smaller)'),
    # -- Dirt
    C.fac('Dust', 0.0, 'Dirt', 'Grey dust lying on top, thickest on upward faces; blocks the light', key=True),
    C.color('Dust Color', (0.36, 0.34, 0.30), 'Dirt', 'Color of the dust'),
    C.fac('Grime', 0.0, 'Dirt', 'Greasy brown film: dims the light and tints it brown', key=True),
    C.color('Grime Color', (0.10, 0.065, 0.03), 'Dirt', 'Color of the grime'),
    C.fac('Bugs', 0.0, 'Dirt', 'Dead insects and fly specks: dark spots in the glow', key=True),
    C.fac('Smudges', 0.0, 'Dirt', 'Fingerprints and greasy smudges'),
    C.fac('Dirt', 0.0, 'Dirt', 'Grime in crevices and corners (needs Cycles or baking)'),
    C.color('Dirt Color', C.DIRT, 'Dirt', 'Color of the grime in crevices'),
] + C.PATTERN_PARAMS

LIGHT_OUTPUTS = C.COMMON_OUTPUTS + C.EMISSION_OUTPUTS

GRIME_FILTER = (0.75, 0.42, 0.16)  # light shining through brown grime
YELLOW_FILTER = (1.0, 0.80, 0.42)
SOOT = (0.025, 0.022, 0.020)
BUG = (0.025, 0.018, 0.012)


def build_light(b, I, gout, tile):
    S = F.Space(b, tile, I['Scale'], I['Seed'], I['Tile Size'] if tile else 1.0)
    inv = b.div(1.0, I['Scale'])
    edge = F.edge_mask(b, S, b.mul(0.01, inv))
    cav = F.cavity_mask(b, S, b.mul(inv, 0.2))
    kind = I['Type']
    tc = b.texcoord()

    # ---- grid coordinates (cells of 'Grid Size')
    if tile:
        n = b.maximum(1.0, b.math('ROUND', b.div(b.mul(I['Tile Size'], I['Scale']), I['Grid Size'])))
        gx, gy = b.mul(S.u, n), b.mul(S.v, n)
    else:
        s, t = F.box_coords(b, S)
        gx, gy = b.div(s, I['Grid Size']), b.div(t, I['Grid Size'])
    fx, fy = b.sub(b.fract(gx), 0.5), b.sub(b.fract(gy), 0.5)
    cell_d = b.math('SQRT', b.madd(fx, fx, b.mul(fy, fy)))
    cell_rand = b.white_noise(b.vadd(b.combine(b.floor(gx), b.floor(gy), 0.0), b.vscale((3.1, 7.3, 1.7), I['Seed'])),
                              label='Cell Random')[0]
    half = b.mul(I['Fill'], 0.5)

    # ---- the lit pattern per type: 0..1 (how much glows) and the color of the light
    light = I['Light Color']
    facing = b.node('ShaderNodeLayerWeight')
    b.feed(facing.inputs['Blend'], 0.5)
    grazing = facing.outputs['Facing']
    neon = b.one_minus(b.mul(I['Core Falloff'], b.mul(grazing, grazing)))
    spot = b.one_minus(b.smoothstep(0.0, 0.75, cell_d))
    panel = b.mix(I['Hot Spots'], 1.0, b.madd(spot, 1.1, 0.35))
    dots = b.one_minus(b.smoothstep(b.sub(half, 0.06), half, cell_d))
    strips = b.one_minus(b.smoothstep(b.sub(half, 0.04), half, b.absolute(fy)))
    # screen: three vertical red, green and blue stripes per pixel
    sub = b.mul(b.fract(gx), 3.0)
    lit_sub = b.one_minus(b.smoothstep(0.32, 0.45, b.absolute(b.sub(b.fract(sub), 0.5))))
    lr, lg, lb = b.separate_color(light)
    red = b.math('LESS_THAN', sub, 1.0)
    blue = b.math('GREATER_THAN', sub, 2.0)
    green = b.one_minus(b.add(red, blue))
    rgb = b.combine_color(b.mul(lr, red), b.mul(lg, green), b.mul(lb, blue))
    scan = b.mix(I['Scanlines'], 1.0, b.one_minus(b.smoothstep(0.25, 0.48, b.absolute(fy))))
    screen = b.mul(lit_sub, scan)
    glow = _choose(b, kind, {0: neon, 1: panel, 2: dots, 3: screen, 4: strips})
    is_screen = _is(b, kind, 3)
    light = b.mix_color(is_screen, light, rgb)
    gridded = b.mul(b.math('GREATER_THAN', kind, 1.5), b.math('LESS_THAN', kind, 4.5))  # dots, screen, strips
    element = _choose(b, kind, {0: 1.0, 1: 1.0, 2: dots, 3: lit_sub, 4: strips})  # what you see when unlit

    # ---- faults
    uz = S.znoise(1.5, 1, detail=3.0, roughness=0.5, label='Unevenness')
    glow = b.mul(glow, b.maximum(b.madd(uz, b.mul(I['Unevenness'], 0.3), 1.0), 0.0))
    dz = S.znoise(1.2, 2, detail=2.0, roughness=0.5, label='Dead Sections')
    dead = F.cover(b, dz, b.mul(I['Dead Sections'], 0.6), 0.25)
    dead_cell = b.mul(gridded, b.math('LESS_THAN', cell_rand, b.mul(I['Dead Sections'], 0.5)))
    dead = b.maximum(dead, dead_cell)

    if tile:
        along = S.u
    else:
        gen = tc.outputs['Generated']
        gxx, gyy, gzz = b.separate(gen)
        ux, _uy, _uz = b.separate(tc.outputs['UV'])
        along = _choose(b, I['Ends Along'], {0: ux, 1: gxx, 2: gyy, 3: gzz})
    to_end = b.minimum(along, b.one_minus(along))
    ez = S.znoise(30.0, 3, detail=2.0, roughness=0.5, label='Soot')
    soot = b.one_minus(b.smoothstep(b.mul(I['End Length'], 0.3), b.maximum(I['End Length'], 1e-4),
                                    b.madd(ez, b.mul(I['End Length'], 0.08), to_end)))
    soot = b.mul(soot, I['End Blackening'])

    crack_d = F.crack_distance(b, S, I['Crack Scale'], 4, label='Cracks')
    crack_on = F.cover(b, S.znoise(b.mul(I['Crack Scale'], 0.5), 6, detail=3.0, roughness=0.6,
                                   label='Crack Patches'), b.mul(I['Cracks'], 0.8), 0.5)
    crack = b.mul(b.one_minus(b.smoothstep(0.006, 0.03, crack_d)), crack_on)

    # ---- dirt on top
    # dust: a film, thicker on upward faces, with fluffy clumps
    up = b.clamp01(b.separate(b.geometry().outputs['Normal'])[2])
    dust_z = S.znoise(14.0, 7, detail=5.0, roughness=0.6, label='Dust')
    film = b.mul(b.mul(I['Dust'], b.madd(up, 0.6, 0.4)), b.madd(dust_z, 0.12, 0.85))
    clump_z = b.madd(up, 0.8, S.znoise(16.0, 14, detail=4.0, roughness=0.65, label='Dust Clumps'))
    if is_socket(cav):
        clump_z = b.madd(cav, 1.5, clump_z)
    clumps = b.mul(F.cover(b, clump_z, b.mul(I['Dust'], 0.2), 0.7), 0.8)
    dust = b.clamp01(b.maximum(b.mul(film, 0.9), clumps))
    gz = S.znoise(2.0, 8, detail=5.0, roughness=0.65, label='Grime')
    if is_socket(cav):
        gz = b.madd(cav, 1.5, gz)
    grime = b.mul(F.cover(b, gz, b.mul(I['Grime'], 0.8), 0.8), b.madd(I['Grime'], 0.4, 0.5))
    # bugs: fly specks and a few bigger dead insects, in clusters
    clz = F.cover(b, S.znoise(3.0, 9, detail=2.0, label='Bug Clusters'), 0.5, 0.8, gate=False)
    sv = S.voronoi(40.0, 10, label='Fly Specks')
    s_rand = b.separate_color(sv.outputs['Color'])
    speck = b.mul(b.one_minus(b.smoothstep(0.12, 0.2, sv.outputs['Distance'])),
                  b.math('LESS_THAN', s_rand[0], b.mul(I['Bugs'], 0.5)))
    bv = S.voronoi(5.0, 11, label='Dead Bugs')
    b_rand = b.separate_color(bv.outputs['Color'])
    body = b.mul(b.one_minus(b.smoothstep(0.14, 0.24, b.div(bv.outputs['Distance'], b.madd(b_rand[1], 0.8, 0.5)))),
                 b.math('LESS_THAN', b_rand[0], b.mul(I['Bugs'], 0.35)))
    bugs = b.mul(b.maximum(speck, body), clz)
    smz = S.znoise(5.0, 12, detail=4.0, roughness=0.6, label='Smudges')
    smudge = b.mul(F.cover(b, smz, b.mul(I['Smudges'], 0.4), 0.5), 0.7)
    dirt = C.dirt_mask(b, S, I['Dirt'], cav, edge, 13, spots=0.2)

    # ---- the light that gets through
    emit = b.mul(glow, b.one_minus(dead))
    emit = b.mul(emit, b.madd(soot, -0.95, 1.0))
    emit = b.mul(emit, b.madd(crack, -0.9, 1.0))
    emit = b.mul(emit, b.madd(dust, -0.8, 1.0))
    emit = b.mul(emit, b.madd(bugs, -0.97, 1.0))
    emit = b.mul(emit, b.madd(smudge, -0.2, 1.0))
    emit = b.mul(emit, b.madd(dirt, -0.9, 1.0))
    emit = b.mul(emit, I['Power'])
    color = b.mix_color(b.mul(I['Yellowing'], 0.8), light, b.mix_color(1.0, light, YELLOW_FILTER, blend='MULTIPLY'))
    color = b.mix_color(grime, color, b.mix_color(1.0, color, GRIME_FILTER, blend='MULTIPLY'))
    color = b.mix_color(b.mul(grime, 0.5), color, b.color_scale(color, 0.4))
    emission = b.mix_color(b.clamp01(emit), (0.0, 0.0, 0.0), color, clamp_result=True)

    # ---- the unlit surface
    col = b.mix_color(b.mul(element, 0.55), I['Surface Color'], b.mix_color(0.3, light, (1.0, 1.0, 1.0)))
    col = b.mix_color(b.mul(I['Yellowing'], 0.6), col, b.mix_color(1.0, col, YELLOW_FILTER, blend='MULTIPLY'))
    col = b.mix_color(soot, col, SOOT)
    col = b.mix_color(b.mul(crack, 0.6), col, b.color_scale(col, 0.4))
    col = b.mix_color(grime, col, I['Grime Color'])
    col = b.mix_color(dust, col, I['Dust Color'])
    col = b.mix_color(bugs, col, BUG)
    col = b.mix_color(dirt, col, I['Dirt Color'])
    col = b.mix_color(b.mul(glow, b.mul(I['Power'], 0.4)), col, b.color_scale(col, 0.3))  # lit: no lit-from-outside look

    rough = b.madd(uz, 0.01, I['Roughness'])
    rough = b.mix(smudge, rough, b.add(rough, 0.25))
    rough = b.mix(grime, rough, 0.55)
    rough = b.mix(soot, rough, b.add(rough, 0.2))
    rough = b.mix(dust, rough, 0.92)
    rough = b.mix(bugs, rough, 0.6)
    rough = b.mix(dirt, rough, 0.9)

    h = b.madd(b.mul(element, gridded), 0.15, 0.45)
    hm = b.madd(dust, 0.4, b.mul(dust_z, b.mul(dust, 0.05)))
    hm = b.madd(bugs, 0.6, hm)
    hm = b.madd(crack, -0.6, hm)
    hm = b.madd(grime, 0.15, hm)

    C.finish(b, gout, I, col, 0.0, rough, h, hm, extra={
        'Emission': emission,
        'Emission Strength': I['Emission Strength'],
    })


SPEC = dict(
    label='Light', category='LIGHT', params=LIGHT_PARAMS, outputs=LIGHT_OUTPUTS, build=build_light,
    links={'Emission': 'Emission Color', 'Emission Strength': 'Emission Strength'},
    display=('Light Color', 0.0, 'Roughness'), fit=0.3, glow='Power',
)
