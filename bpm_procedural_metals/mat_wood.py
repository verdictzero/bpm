# SPDX-License-Identifier: GPL-3.0-or-later
"""Wood generator: solid wood or planks; raw, varnished, stained, painted,
weathered or charred.

The wood is a real 3D "solid texture": growth rings come from the distance to
the center line (pith) of the log each plank was cut from, so end grain, side
grain and flat-sawn arches all appear where they would on real lumber.
"""

from . import features as F
from . import gencommon as C
from .nodebuilder import is_socket

OAK = (0.50, 0.27, 0.11)
OAK_RING = (0.26, 0.11, 0.042)
CHAR = (0.010, 0.009, 0.008)
CHAR_TOP = (0.035, 0.032, 0.030)
SCORCH = (0.07, 0.028, 0.010)

WOOD_PARAMS = [
    # -- Wood
    C.color('Wood Color', OAK, 'Wood', 'Main (light) color of the wood', key=True),
    C.color('Ring Color', OAK_RING, 'Wood', 'Color of the darker growth rings', key=True),
    C.fac('Roughness', 0.6, 'Wood', 'Glossiness of the bare wood (0 = glossy, 1 = matte)'),
    C.fac('Color Variation', 0.3, 'Wood', 'Uneven, blotchy color'),
    # -- Grain
    C.axis('Grain Direction', (1.0, 0.0, 0.0), 'Grain', 'Direction the wood fibers run in'),
    C.scale('Ring Density', 80.0, 5.0, 2000.0, 'Grain', 'Growth rings per meter (higher = finer grain)'),
    C.fac('Ring Contrast', 0.6, 'Grain', 'How strongly the growth rings show', key=True),
    C.fac('Ring Arcs', 0.5, 'Grain', 'Arch-shaped grain of flat sawn boards (0 = straight lines)'),
    C.fac('Distortion', 0.4, 'Grain', 'Wavy, irregular grain'),
    C.fac('Fibers', 0.5, 'Grain', 'Fine streaks along the grain'),
    C.fac('Pores', 0.3, 'Grain', 'Open pores, as in oak and ash'),
    C.fac('Figure', 0.0, 'Grain', 'Shimmering stripes across the grain (curly / flame maple)'),
    C.fac('Knots', 0.15, 'Grain', 'How many knots', key=True),
    C.Param('Knot Size', 'FLOAT', 0.025, 0.002, 0.5, 'Grain', 'Size of the knots', subtype='DISTANCE'),
    # -- Planks
    C.fac('Planks', 1.0, 'Planks', 'Planks with seams between them (0 = one solid piece of wood)', key=True),
    C.Param('Plank Width', 'FLOAT', 0.14, 0.01, 5.0, 'Planks', 'Width of each plank', subtype='DISTANCE'),
    C.Param('Plank Length', 'FLOAT', 1.2, 0.05, 50.0, 'Planks', 'Length of each plank', subtype='DISTANCE'),
    C.axis('Plank Direction', (0.0, 1.0, 0.0), 'Planks', 'Direction in which the planks lie side by side'),
    C.Param('Gap Width', 'FLOAT', 0.002, 0.0, 0.05, 'Planks', 'Width of the gaps between planks',
            subtype='DISTANCE'),
    C.fac('Plank Variation', 0.5, 'Planks', 'Color differences between planks'),
    # -- Finish
    C.fac('Varnish', 0.0, 'Finish', 'Glossy varnish / lacquer on top', key=True),
    C.fac('Varnish Roughness', 0.08, 'Finish', 'Glossiness of the varnish'),
    C.fac('Stain', 0.0, 'Finish', 'Wood stain darkening and tinting the wood'),
    C.color('Stain Color', (0.20, 0.08, 0.025), 'Finish', 'Color of the stain'),
    C.fac('Paint', 0.0, 'Finish', 'Painted wood', key=True),
    C.color('Paint Color', (0.55, 0.06, 0.04), 'Finish', 'Color of the paint'),
    C.fac('Paint Roughness', 0.5, 'Finish', 'Glossiness of the paint'),
    C.fac('Paint Wear', 0.3, 'Finish', 'Paint chipped and peeled off along the grain'),
    # -- Aging
    C.fac('Weathering', 0.0, 'Aging', 'Sun and rain: grey, silvery wood with raised grain', key=True),
    C.color('Weathered Color', (0.26, 0.25, 0.23), 'Aging', 'Color of weathered wood'),
    C.fac('Cracks', 0.1, 'Aging', 'Cracks along the grain'),
    C.fac('Scratches', 0.1, 'Aging', 'Scratches and scuffs'),
    C.fac('Edge Wear', 0.3, 'Aging', 'Worn edges (visible in Cycles and in baked textures)'),
    C.Param('Edge Width', 'FLOAT', 0.02, 0.001, 0.3, 'Aging', 'Width of edge wear', subtype='DISTANCE'),
    C.fac('Burn', 0.0, 'Aging', 'Charred, cracked black wood (shou sugi ban)'),
    C.fac('Dirt', 0.2, 'Aging', 'Grime in gaps, cracks and corners', key=True),
    C.color('Dirt Color', C.DIRT, 'Aging', 'Color of the grime'),
] + C.PATTERN_PARAMS

WOOD_OUTPUTS = C.COMMON_OUTPUTS + [('Coat', 'FLOAT')]


def build_wood(b, I, gout, tile):
    S = F.Space(b, tile, I['Scale'], I['Seed'], I['Tile Size'] if tile else 1.0)
    inv = b.div(1.0, I['Scale'])
    edge = F.edge_mask(b, S, b.mul(I['Edge Width'], inv))
    cav = F.cavity_mask(b, S, b.mul(inv, 0.3))

    # ---- frame: a = along the grain, c = across (plank direction), d = depth
    planks = I['Planks']
    use = b.math('GREATER_THAN', planks, 0.001)
    W, L = I['Plank Width'], I['Plank Length']
    if tile:
        span = b.mul(I['Tile Size'], I['Scale'])  # pattern units covered by one tile
        nv = b.maximum(1.0, b.math('ROUND', b.div(span, W)))
        nu = b.maximum(1.0, b.math('ROUND', b.div(span, L)))
        W, L = b.div(span, nv), b.div(span, nu)  # whole planks per tile keep it seamless
        a, c, d = b.mul(S.u, span), b.mul(S.v, span), 0.0
        grain = None
    else:
        g = b.vmath('NORMALIZE', I['Grain Direction'])
        q0 = I['Plank Direction']
        q_raw = b.vmath('SUBTRACT', q0, b.vscale(g, b.vmath('DOT_PRODUCT', q0, g)))
        alt = b.vmath('NORMALIZE', b.vmath('CROSS_PRODUCT', g, (0.267, 0.535, 0.802)))
        q = b.mix_vector(b.math('LESS_THAN', b.vmath('LENGTH', q_raw), 0.1), b.vmath('NORMALIZE', q_raw), alt)
        n = b.vmath('CROSS_PRODUCT', g, q)
        a = b.vmath('DOT_PRODUCT', S.P, g)
        c = b.vmath('DOT_PRODUCT', S.P, q)
        d = b.vmath('DOT_PRODUCT', S.P, n)
        grain = b.combine(a, c, d)

    def gnoise(freq, offset, aniso=(1.0, 1.0, 1.0), z=True, **kw):
        """Noise in the grain frame: aniso = (along the grain, across, depth)."""
        fn = S.znoise if z else S.noise
        if tile:
            return fn(freq, offset, aniso=aniso[:2], **kw)
        return fn(freq, offset, aniso=aniso, base=grain, **kw)

    # ---- planks: row i across, piece j along (staggered); local coordinates cl, al
    i_raw = b.floor(b.div(c, W))
    cl = b.sub(c, b.mul(i_raw, b.mul(W, use)))
    i = b.mul(b.wrap(i_raw, nv) if tile else i_raw, use)
    row_rand, _ = b.white_noise(b.combine(i, 0.37, b.mul(I['Seed'], 0.173)), label='Row Offset')
    a2 = b.madd(b.mul(row_rand, use), L, a)
    j_raw = b.floor(b.div(a2, L))
    al = b.sub(a2, b.mul(j_raw, b.mul(L, use)))
    j = b.mul(b.wrap(j_raw, nu) if tile else j_raw, use)
    _, plank_col = b.white_noise(b.combine(i, j, b.madd(I['Seed'], 0.311, 5.0)), label='Plank Random')
    r1, r2, r3 = b.separate_color(plank_col)
    jitter = b.mul(b.mul(r1, 61.0), use)

    # distance to the plank border -> gaps
    across = b.minimum(cl, b.sub(W, cl))
    along_d = b.minimum(al, b.sub(L, al))
    border = b.minimum(across, along_d)
    gap_w = b.mul(I['Gap Width'], 0.5)
    gap = b.one_minus(b.smoothstep(gap_w, b.add(gap_w, 0.0025), border))
    gap = b.mul(b.mul(gap, use), planks)

    # ---- growth rings: distance to the log's center line, different per plank
    arcs = I['Ring Arcs']
    cc = b.mul(b.sub(r2, 0.5), b.mul(W, 1.2))
    pith = b.mul(b.mul(W, b.mix(arcs, 6.0, 0.8)), b.add(r3, 0.5))
    taper = b.mul(b.sub(r1, 0.5), b.mul(arcs, 0.3))
    dc = b.madd(al, taper, pith)
    dd = b.sub(d, dc) if is_socket(d) else b.mul(dc, -1.0)
    radius = b.vmath('LENGTH', b.combine(b.sub(cl, cc), dd, 0.0))
    dist_z = gnoise(3.0, 1, (0.15, 1.0, 1.0), detail=3.0, roughness=0.5, jitter=jitter, label='Ring Distortion')
    density = I['Ring Density']
    wobble = b.mul(dist_z, b.mul(I['Distortion'], 1.6))
    phase = b.madd(radius, density, wobble)
    if tile:
        # solid wood (no planks) in a tile: ring lines must repeat across the tile
        nr = b.maximum(1.0, b.math('ROUND', b.mul(b.mul(density, span), 0.5)))
        arc_z = S.znoise(1.5, 14, aniso=(1.0, 0.3), detail=2.0, label='Ring Arcs')
        solid = b.madd(S.v, nr, b.madd(arc_z, b.mul(arcs, 2.5), wobble))
        phase = b.mix(use, solid, phase)

    # knots: some voronoi cells get one; rings bend around them
    knot_freq = b.div(0.1, I['Knot Size'])
    kv = S.voronoi(knot_freq, 2, aniso=(0.5, 1.0) if tile else (0.5, 1.0, 1.0), base=grain, label='Knots')
    kdist = kv.outputs['Distance']
    has_knot = b.math('LESS_THAN', b.separate_color(kv.outputs['Color'])[0], b.mul(I['Knots'], 0.7))
    k_infl = b.mul(b.one_minus(b.smoothstep(0.0, 0.5, kdist)), has_knot)
    phase = b.madd(b.mul(k_infl, k_infl), 4.0, phase)
    k_core = b.mul(b.one_minus(b.smoothstep(0.06, 0.1, kdist)), has_knot)

    ring_t = b.fract(phase)
    late = b.mul(b.smoothstep(0.5, 0.93, ring_t), b.one_minus(b.smoothstep(0.97, 1.0, ring_t)))
    late = b.mul(late, I['Ring Contrast'])
    # groups of lighter / darker rings: keeps the grain readable from far away
    band_t = b.fract(b.madd(phase, 0.14, b.mul(dist_z, 0.3)))
    band = b.mul(b.smoothstep(0.0, 0.5, band_t), b.one_minus(b.smoothstep(0.5, 1.0, band_t)))
    band = b.mul(b.sub(band, 0.5), I['Ring Contrast'])

    # fibers, pores and figure
    fz = gnoise(320.0, 3, (0.02, 1.0, 1.0), detail=3.0, roughness=0.6, jitter=jitter, label='Fibers')
    pz = gnoise(700.0, 4, (0.08, 1.0, 1.0), detail=1.5, jitter=jitter, label='Pores')
    pores = b.mul(b.mul(b.smoothstep(1.3, 2.1, pz), I['Pores']), b.madd(late, -0.6, 1.0))
    figz = gnoise(24.0, 5, (1.0, 0.04, 0.04), detail=2.0, jitter=jitter, label='Figure')

    # ---- base wood color
    col = b.mix_color(late, I['Wood Color'], I['Ring Color'])
    col = b.color_scale(col, b.madd(band, -0.3, 1.0))
    col = b.color_scale(col, b.madd(fz, b.mul(I['Fibers'], 0.07), 1.0))
    col = b.color_scale(col, b.madd(figz, b.mul(I['Figure'], 0.14), 1.0))
    col = b.mix_color(b.mul(pores, 0.8), col, b.color_scale(I['Ring Color'], 0.55))
    zc = S.znoise(1.5, 6, detail=4.0, roughness=0.55, label='Color Variation')
    col = b.color_scale(col, b.madd(zc, b.mul(I['Color Variation'], 0.09), 1.0))
    pv = b.mul(I['Plank Variation'], use)
    col = b.hsv(col, hue=b.madd(b.sub(r1, 0.5), b.mul(pv, 0.03), 0.5),
                saturation=b.madd(b.sub(r2, 0.5), b.mul(pv, 0.5), 1.0),
                value=b.madd(b.sub(r3, 0.5), b.mul(pv, 0.55), 1.0))
    col = b.mix_color(k_core, col, b.color_scale(I['Ring Color'], 0.6))
    rough = b.madd(fz, 0.03, b.madd(pores, 0.12, I['Roughness']))

    # ---- stain (soaks deeper into pores and fibers)
    stained = b.color_scale(b.mix_color(1.0, col, I['Stain Color'], blend='MULTIPLY'), 2.2)
    col = b.mix_color(b.clamp01(b.mul(I['Stain'], b.madd(pores, 0.5, 1.0))), col, stained)

    # ---- cracks along the grain
    crack_n = gnoise(6.0, 7, (0.04, 1.0, 1.0), z=False, detail=3.0, roughness=0.5, jitter=jitter, label='Cracks')
    crack_w = b.madd(I['Cracks'], 0.02, 0.004)
    crack_line = b.one_minus(b.smoothstep(0.0, crack_w, b.absolute(b.sub(crack_n, 0.5))))
    crack_on = F.cover(b, gnoise(1.5, 8, (0.3, 1.0, 1.0), detail=2.0), b.mul(I['Cracks'], 0.7), 0.4)
    crack = b.mul(crack_line, crack_on)

    # ---- weathering
    wz = S.znoise(2.5, 9, detail=4.0, roughness=0.6, label='Weathering')
    weather = b.clamp01(b.mul(I['Weathering'], b.madd(wz, 0.25, 1.1)))
    w_col = b.color_scale(I['Weathered Color'], b.madd(late, -0.5, b.madd(band, -0.25, b.madd(fz, 0.08, 1.1))))
    col = b.mix_color(weather, col, w_col)
    rough = b.mix(weather, rough, 0.85)

    # ---- edge wear (sanded, lighter edges)
    e = b.mul(F.broken(b, S, edge, 10, 30.0), I['Edge Wear']) if is_socket(edge) else 0.0
    col = b.color_scale(col, b.madd(e, 0.25, 1.0))
    rough = b.madd(e, 0.1, rough)

    # ---- scratches
    scr = F.scratch_mask(b, S, I['Scratches'], 1.0, 40)
    col = b.color_scale(col, b.madd(scr, 0.18, 1.0))

    # ---- varnish
    coat_amt = b.mul(I['Varnish'], b.one_minus(b.maximum(e, b.mul(scr, 0.6))))
    col = b.color_scale(b.hsv(col, saturation=b.madd(coat_amt, 0.15, 1.0)), b.madd(coat_amt, -0.12, 1.0))
    rough = b.mix(coat_amt, rough, b.madd(I['Varnish Roughness'], 1.6, 0.05))

    # ---- paint, peeling along the grain
    pzf = gnoise(14.0, 11, (0.12, 1.0, 1.0), detail=6.0, roughness=0.62, jitter=jitter, label='Paint Peel')
    field = b.madd(crack, 3.0, pzf)
    if is_socket(edge):
        field = b.madd(edge, 3.0, field)
    peel = F.cover(b, field, b.mul(I['Paint Wear'], 0.8), 0.25)
    paint = b.mul(I['Paint'], b.one_minus(peel))
    p_col = b.color_scale(I['Paint Color'], b.madd(zc, 0.04, 1.0))
    col = b.mix_color(paint, col, p_col)
    rough = b.mix(paint, rough, I['Paint Roughness'])
    coat_amt = b.mul(coat_amt, b.one_minus(paint))

    # ---- charring
    burn_z = S.znoise(1.2, 12, detail=3.0, label='Burn Patches')
    burn = b.clamp01(b.madd(burn_z, 0.15, b.madd(I['Burn'], 2.0, -0.5)))
    burn = b.mul(burn, b.clamp01(b.mul(I['Burn'], 25.0)))
    bv = S.voronoi(14.0, 13, feature='DISTANCE_TO_EDGE', aniso=(0.5, 1.0) if tile else (0.5, 1.0, 1.0),
                   base=grain, label='Char Cracks')
    edist = bv.outputs['Distance']
    groove = b.one_minus(b.smoothstep(0.03, 0.12, edist))
    dome = b.smoothstep(0.0, 0.5, edist)
    char_col = b.mix_color(groove, b.color_scale(CHAR_TOP, b.madd(fz, 0.1, 1.0)), CHAR)
    scorch = b.mul(b.smoothstep(0.0, 0.5, burn), b.one_minus(b.smoothstep(0.5, 1.0, burn)))
    col = b.mix_color(scorch, col, SCORCH)
    col = b.mix_color(b.smoothstep(0.45, 0.85, burn), col, char_col)
    burn_full = b.smoothstep(0.45, 0.85, burn)
    rough = b.mix(burn_full, rough, b.madd(groove, 0.4, 0.5))
    coat_amt = b.mul(coat_amt, b.one_minus(burn_full))

    # ---- dirt in gaps, cracks and corners
    dirt = C.dirt_mask(b, S, I['Dirt'], cav, edge, 45, extra=b.mul(b.maximum(gap, crack), 0.9))
    col = b.mix_color(b.maximum(gap, b.mul(crack, 0.85)), col, b.color_scale(col, 0.22))
    col = b.mix_color(dirt, col, I['Dirt Color'])
    rough = b.mix(dirt, rough, 0.9)
    coat_amt = b.mul(coat_amt, b.one_minus(dirt))

    # ---- relief
    h_macro = b.madd(gap, -0.45, 0.5)
    h_macro = b.madd(crack, -0.3, h_macro)
    h_macro = b.madd(k_core, 0.03, h_macro)
    h_macro = b.madd(b.mul(late, weather), 0.12, h_macro)
    h_macro = b.madd(paint, 0.06, h_macro)
    h_burn = b.madd(dome, 0.18, b.madd(groove, -0.35, 0.45))
    h_macro = b.mix(burn_full, h_macro, h_burn)
    h_micro = b.mul(fz, b.mul(b.add(I['Fibers'], weather), 0.25))
    h_micro = b.madd(pores, -0.5, h_micro)
    h_micro = b.madd(scr, -0.6, h_micro)
    h_micro = b.mul(h_micro, b.one_minus(b.mul(paint, 0.7)))

    C.finish(b, gout, I, col, 0.0, rough, h_macro, h_micro, extra={'Coat': coat_amt})


SPEC = dict(
    label='Wood', category='WOOD', params=WOOD_PARAMS, outputs=WOOD_OUTPUTS, build=build_wood,
    links={'Coat': 'Coat Weight'}, bsdf={'Coat Roughness': 0.06},
    display=('Wood Color', 0.0, 'Roughness'), fit=0.35,
)
