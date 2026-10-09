# SPDX-License-Identifier: GPL-3.0-or-later
"""Concrete generator: cast, board-formed, precast, polished, slab and block
concrete, from fresh to ruined.

Layers: the cement with sand, stones (aggregate) and air holes; the finish
(formwork boards, formwork panels with tie holes, broom grooves, cut joints,
blocks with mortar); damage (cracks, chipped edges, spalling with rusty
rebar, erosion, impact craters); stains (rust, water, salt, dirt, moss, oil,
soot, wetness).

Every layer updates all channels right away.  Cycles works through the nodes
in the order they were made, so a finished layer doesn't keep its masks on
Cycles' shader stack while the next ones are computed.
"""

from . import features as F
from . import gencommon as C
from .nodebuilder import is_socket

CONCRETE_BUMP = 0.04  # relief depth of the full 0..1 height range (meters at Scale 1)

RUST = (0.20, 0.065, 0.02)
RUST_DARK = (0.05, 0.02, 0.008)
REBAR = (0.11, 0.07, 0.045)
SALT = (0.80, 0.80, 0.78)
MOSS = (0.045, 0.075, 0.015)
MOSS_LIGHT = (0.09, 0.12, 0.03)
SOOT = (0.012, 0.011, 0.010)

CONCRETE_PARAMS = [
    # -- Concrete
    C.color('Concrete Color', (0.22, 0.215, 0.205), 'Concrete', 'Color of the cement', key=True),
    C.fac('Color Variation', 0.35, 'Concrete', 'Blotchy, uneven color from pouring and curing', key=True),
    C.fac('Roughness', 0.85, 'Concrete', '0 = glossy, 1 = rough and dull'),
    C.fac('Aggregate', 0.15, 'Concrete', 'Stones showing in the surface (exposed aggregate)', key=True),
    C.Param('Aggregate Size', 'FLOAT', 0.012, 0.002, 0.1, 'Concrete', 'Size of the stones', subtype='DISTANCE'),
    C.color('Aggregate Color', (0.30, 0.28, 0.25), 'Concrete', 'Color of the stones (each one varies)'),
    C.fac('Sand', 0.5, 'Concrete', 'Fine grains of sand'),
    C.fac('Pores', 0.3, 'Concrete', 'Small air holes (bug holes)', key=True),
    C.fac('Polish', 0.0, 'Concrete', 'Ground and polished: glossy, with the stones cut flat'),
    # -- Finish
    C.fac('Board Formed', 0.0, 'Finish', 'Imprint of wooden formwork boards: wood grain and seams'),
    C.Param('Board Width', 'FLOAT', 0.14, 0.02, 1.0, 'Finish', 'Width of the boards', subtype='DISTANCE'),
    C.axis('Finish Direction', (1.0, 0.0, 0.0), 'Finish', 'Direction of the boards and broom grooves'),
    C.fac('Form Panels', 0.0, 'Finish', 'Seams and tie holes of big formwork panels (brutalist walls)'),
    C.Param('Panel Size', 'FLOAT', 1.2, 0.2, 10.0, 'Finish', 'Width of the panels (they are twice as high)',
            subtype='DISTANCE'),
    C.fac('Broom Finish', 0.0, 'Finish', 'Fine parallel grooves of a broomed sidewalk'),
    C.fac('Joints', 0.0, 'Finish', 'Grid of cut joints: sidewalk slabs, floors'),
    C.Param('Joint Spacing', 'FLOAT', 1.5, 0.1, 10.0, 'Finish', 'Size of the slabs', subtype='DISTANCE'),
    C.fac('Blocks', 0.0, 'Finish', 'Concrete blocks with mortar joints (block wall)'),
    C.Param('Block Size', 'FLOAT', 0.4, 0.05, 2.0, 'Finish', 'Length of the blocks (they are half as high)',
            subtype='DISTANCE'),
    C.color('Mortar Color', (0.33, 0.32, 0.30), 'Finish', 'Color of the mortar between blocks'),
    # -- Damage
    C.fac('Cracks', 0.1, 'Damage', 'Cracks in the surface', key=True),
    C.scale('Crack Scale', 2.0, 0.1, 50.0, 'Damage', 'Size of the cracked pieces (higher = smaller)'),
    C.fac('Chipped Edges', 0.2, 'Damage', 'Broken edges and corners (Cycles and baked textures)', key=True),
    C.Param('Edge Width', 'FLOAT', 0.04, 0.001, 0.3, 'Damage', 'Width of the edge damage', subtype='DISTANCE'),
    C.fac('Spalling', 0.0, 'Damage', 'Pieces of the surface broken off: rough holes', key=True),
    C.fac('Rebar', 0.0, 'Damage', 'Rusty reinforcing bars showing where the concrete broke off'),
    C.Param('Rebar Spacing', 'FLOAT', 0.2, 0.05, 2.0, 'Damage', 'Distance between the bars', subtype='DISTANCE'),
    C.fac('Erosion', 0.0, 'Damage', 'Weathered: the cement washed away, stones and pits showing'),
    C.fac('Impacts', 0.0, 'Damage', 'Craters of impacts: bullets and shrapnel'),
    # -- Stains
    C.fac('Rust Stains', 0.0, 'Stains', 'Rust running down from the steel inside', key=True),
    C.fac('Water Stains', 0.15, 'Stains', 'Dark streaks and damp patches from rain water'),
    C.fac('Efflorescence', 0.0, 'Stains', 'White salt deposits along cracks and joints'),
    C.fac('Dirt', 0.2, 'Stains', 'Grime in corners, low down and in patches', key=True),
    C.color('Dirt Color', (0.07, 0.06, 0.045), 'Stains', 'Color of the dirt'),
    C.fac('Moss', 0.0, 'Stains', 'Green moss and algae in damp places'),
    C.fac('Oil Stains', 0.0, 'Stains', 'Dark oil blotches (garage floors, parking lots)'),
    C.fac('Soot', 0.0, 'Stains', 'Blackened by fire from below'),
    C.fac('Wetness', 0.0, 'Stains', 'Wet concrete: darker and shiny'),
] + C.PATTERN_PARAMS


def _cells(b, S, tile, span, size_s, size_t):
    """Coordinates in cells of `size_s` x `size_t` (pattern units).  Object mode: on the plane the
    surface faces most; tiles: a whole number of cells across, so they stay seamless."""
    if tile:
        ns = b.maximum(1.0, b.math('ROUND', b.div(span, size_s)))
        nt = b.maximum(1.0, b.math('ROUND', b.div(span, size_t)))
        return b.mul(S.u, ns), b.mul(S.v, nt)
    s, t = F.box_coords(b, S)
    return b.div(s, size_s), b.div(t, size_t)


def _seam(b, x, half_width):
    """1 on lines at whole numbers of `x` (a groove `half_width` wide, in units of x)."""
    f = b.fract(x)
    return b.one_minus(b.smoothstep(half_width, b.mul(half_width, 2.0), b.minimum(f, b.one_minus(f))))


def build_concrete(b, I, gout, tile):
    S = F.Space(b, tile, I['Scale'], I['Seed'], I['Tile Size'] if tile else 1.0)
    inv = b.div(1.0, I['Scale'])
    span = b.mul(I['Tile Size'], I['Scale']) if tile else None
    edge = F.edge_mask(b, S, b.mul(I['Edge Width'], inv))
    cav = F.cavity_mask(b, S, b.mul(inv, 0.3))
    has_geo = is_socket(edge)
    height_obj = b.separate(b.texcoord().outputs['Generated'])[2] if has_geo else None

    # ---- cement: blotchy color, sand grains
    vz = S.znoise(1.2, 1, detail=5.0, roughness=0.6, label='Color Blotches')
    vz2 = S.znoise(6.0, 2, detail=4.0, roughness=0.6, label='Mottling')
    variation = I['Color Variation']
    speck = S.znoise(40.0, 26, detail=3.0, roughness=0.6, label='Speckle')
    col = b.color_scale(I['Concrete Color'],
                        b.madd(b.madd(vz, 0.14, b.madd(vz2, 0.07, b.mul(speck, 0.035))), variation, 1.0))
    col = b.mix_color(b.mul(b.clamp01(b.mul(vz, 0.5)), variation), col, b.color_scale(I['Concrete Color'], 0.78))
    polish = I['Polish']
    rough = b.mix(polish, b.madd(vz2, 0.03, I['Roughness']), b.madd(vz2, 0.015, 0.07))
    metal = 0.0
    sand = S.noise(320.0, 3, detail=2.0, roughness=0.5, label='Sand')
    col = b.color_scale(col, b.madd(b.sub(sand, 0.5), b.mul(I['Sand'], 0.5), 1.0))
    h = 0.5
    hm = b.mul(b.sub(sand, 0.5), b.mul(I['Sand'], b.madd(polish, -0.9, 1.0)))

    # ---- stones and air holes; erosion washes the cement off the stones
    erosion = I['Erosion']
    agg_freq = b.div(1.0, I['Aggregate Size'])
    stones = S.voronoi(agg_freq, 4, label='Aggregate')
    sr, sg, sb = b.separate_color(stones.outputs['Color'])
    radius = b.madd(sg, 0.2, 0.25)
    shape = b.one_minus(b.div(stones.outputs['Distance'], radius))
    exposed = b.clamp01(b.madd(erosion, 0.6, I['Aggregate']))
    stone = b.mul(b.smoothstep(0.0, 0.12, shape), b.math('LESS_THAN', sr, exposed))
    stone_col = b.color_scale(I['Aggregate Color'], b.madd(sb, 0.9, 0.55))
    stone_col = b.mix_color(b.mul(sg, 0.5), stone_col, b.color_scale((0.35, 0.27, 0.20), b.madd(sb, 0.6, 0.6)))
    col = b.mix_color(stone, col, stone_col)
    rough = b.mix(stone, rough, b.mix(polish, 0.6, 0.08))
    h = b.madd(b.mul(stone, b.clamp01(shape)), b.mul(b.one_minus(polish), 0.05), h)

    pores = S.voronoi(b.mul(agg_freq, 1.6), 5, label='Air Holes')
    pr, pg, _pb = b.separate_color(pores.outputs['Color'])
    hole = b.one_minus(b.smoothstep(b.madd(pg, 0.1, 0.05), b.madd(pg, 0.15, 0.2), pores.outputs['Distance']))
    hole = b.mul(hole, b.math('LESS_THAN', pr, b.mul(b.add(I['Pores'], b.mul(erosion, 0.5)), 0.35)))
    col = b.color_scale(col, b.madd(hole, -0.45, 1.0))
    rough = b.madd(hole, 0.1, rough)
    hm = b.madd(hole, -2.5, hm)

    pits = b.smoothstep(1.0, 2.2, S.znoise(90.0, 6, detail=2.0, roughness=0.5, label='Pits'))
    hm = b.madd(b.mul(pits, erosion), -1.5, hm)
    col = b.color_scale(col, b.madd(b.madd(pits, -0.5, b.madd(speck, 0.08, -0.12)), erosion, 1.0))
    rough = b.madd(erosion, 0.1, rough)

    # ---- finish
    d = b.vmath('NORMALIZE', I['Finish Direction'])
    if tile:
        boards_n = b.maximum(1.0, b.math('ROUND', b.div(span, I['Board Width'])))
        across = b.mul(S.v, boards_n)
    else:
        # across the boards: up (Z), or X for boards that run up and down
        _dx, _dy, dz = b.separate(d)
        up = b.mix_vector(b.math('GREATER_THAN', b.absolute(dz), 0.9), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0))
        side = b.vmath('NORMALIZE', b.vmath('CROSS_PRODUCT', d, b.vmath('CROSS_PRODUCT', up, d)))
        across = b.div(b.vmath('DOT_PRODUCT', S.P, side), I['Board Width'])
    boards = I['Board Formed']
    board = b.floor(across)
    board_rand, _c = b.white_noise(b.combine(board, I['Seed'], 0.37), dims='3D')
    grain_base = None if tile else F.squashed(b, S.P, d, 20.0)
    grain = S.noise(14.0, 7, detail=4.0, roughness=0.6, aniso=(1.0 / 20.0, 1.0) if tile else None,
                    base=grain_base, jitter=b.mul(board, 1.37), label='Board Grain')
    seam = _seam(b, across, 0.02)
    col = b.color_scale(col, b.madd(b.madd(b.sub(board_rand, 0.5), 0.12, b.mul(seam, -0.25)), boards, 1.0))
    h = b.madd(b.madd(b.sub(grain, 0.5), 0.12, b.mul(seam, -0.25)), boards, h)
    rough = b.madd(b.mul(seam, boards), 0.05, rough)

    panels = I['Form Panels']
    ps, pt = _cells(b, S, tile, span, I['Panel Size'], b.mul(I['Panel Size'], 2.0))
    panel_seam = b.maximum(_seam(b, ps, 0.003), _seam(b, pt, 0.0015))
    hs, ht = b.sub(b.fract(b.mul(ps, 2.0)), 0.5), b.sub(b.fract(b.mul(pt, 4.0)), 0.5)
    tie_r = b.div(b.mul(0.02, 2.0), I['Panel Size'])  # 2 cm holes, in units of half a panel
    tie = b.one_minus(b.smoothstep(b.mul(tie_r, 0.6), tie_r, b.math('SQRT', b.madd(hs, hs, b.mul(ht, ht)))))
    col = b.color_scale(col, b.madd(b.maximum(b.mul(panel_seam, 0.2), b.mul(tie, 0.55)), b.mul(panels, -1.0), 1.0))
    h = b.madd(b.maximum(b.mul(panel_seam, 0.15), b.mul(tie, 0.4)), b.mul(panels, -1.0), h)

    broom = S.noise(160.0, 8, detail=2.0, roughness=0.5, aniso=(1.0, 1.0 / 30.0) if tile else None,
                    base=None if tile else F.squashed(b, S.P, d, 30.0), label='Broom Grooves')
    hm = b.madd(b.sub(broom, 0.5), b.mul(I['Broom Finish'], 1.5), hm)
    rough = b.madd(I['Broom Finish'], 0.04, rough)

    js, jt = _cells(b, S, tile, span, I['Joint Spacing'], I['Joint Spacing'])
    joint_w = b.div(0.004, I['Joint Spacing'])  # 8 mm saw cuts
    joint = b.mul(b.maximum(_seam(b, js, joint_w), _seam(b, jt, joint_w)), I['Joints'])
    col = b.color_scale(col, b.madd(joint, -0.5, 1.0))
    h = b.madd(joint, -0.3, h)

    blocks = I['Blocks']
    bs, bt = _cells(b, S, tile, span, I['Block Size'], b.mul(I['Block Size'], 0.5))
    row = b.floor(bt)
    bs = b.madd(row, 0.5, bs)  # running bond
    block_rand, _c2 = b.white_noise(b.combine(b.floor(bs), row, b.add(I['Seed'], 0.71)), dims='3D')
    mortar_w = b.div(0.005, I['Block Size'])
    mortar = b.mul(b.maximum(_seam(b, bs, mortar_w), _seam(b, bt, b.mul(mortar_w, 2.0))), blocks)
    col = b.color_scale(col, b.madd(b.mul(b.sub(block_rand, 0.5), blocks), 0.16, 1.0))
    col = b.mix_color(mortar, col, b.color_scale(I['Mortar Color'], b.madd(vz2, 0.04, 1.0)))
    h = b.madd(mortar, -0.12, h)
    rough = b.madd(mortar, 0.05, rough)

    # ---- damage: cracks, broken edges and spalls with rebar, impact craters
    if tile:
        crack_v = S.voronoi(I['Crack Scale'], 10, feature='DISTANCE_TO_EDGE', label='Cracks')
    else:  # bent, so the cracks don't look like straight polygon edges
        warp = S.noise(3.0, 9, detail=2.0, roughness=0.5, label='Crack Warp').node.outputs['Color']
        wr, wg, wb = b.separate_color(warp)
        bent = b.vadd(S.P, b.vscale(b.combine(b.sub(wr, 0.5), b.sub(wg, 0.5), b.sub(wb, 0.5)),
                                    b.div(0.45, I['Crack Scale'])))
        crack_v = S.voronoi(I['Crack Scale'], 10, feature='DISTANCE_TO_EDGE', base=bent, label='Cracks')
    crack_on = F.cover(b, S.znoise(b.mul(I['Crack Scale'], 0.6), 11, detail=3.0, roughness=0.6,
                                   label='Crack Patches'), b.mul(I['Cracks'], 0.8), 0.5)
    crack_d = crack_v.outputs['Distance']
    crack = b.mul(b.one_minus(b.smoothstep(0.004, 0.018, crack_d)), crack_on)
    crack_zone = b.mul(b.one_minus(b.smoothstep(0.01, 0.08, crack_d)), crack_on)  # where salt and rust leak
    col = b.color_scale(col, b.madd(crack, -0.6, 1.0))
    h = b.madd(crack, -0.25, h)

    field = F.chip_field(b, S, 3.0, 0.7, edge, cav, I['Chipped Edges'], 12, edge_weight=4.0)
    field = b.madd(crack_zone, 1.0, field)  # cracked concrete breaks off first
    spall, _rim = F.chip_layers(b, field, b.mul(I['Spalling'], 0.3), I['Chipped Edges'], 0.0)
    deep = b.smoothstep(0.6, 0.95, b.mul(spall, b.clamp01(b.madd(field, 0.5, 0.2))))
    broken = S.znoise(25.0, 14, detail=4.0, roughness=0.7, label='Broken Surface')
    broken_col = b.color_scale(I['Concrete Color'], b.madd(broken, 0.12, b.madd(deep, -0.2, 0.72)))
    broken_col = b.mix_color(0.3, broken_col, b.color_scale((0.24, 0.21, 0.17), b.madd(broken, 0.1, 1.0)))
    col = b.mix_color(spall, col, broken_col)
    inside = b.mul(spall, b.smoothstep(0.0, 0.12, shape))  # every stone shows in the broken concrete
    col = b.mix_color(b.mul(inside, 0.85), col, stone_col)
    rough = b.mix(spall, rough, 0.95)
    h = b.madd(spall, b.madd(broken, 0.06, b.madd(deep, -0.15, -0.35)), h)
    h = b.madd(inside, 0.04, h)

    rs, rt = _cells(b, S, tile, span, I['Rebar Spacing'], I['Rebar Spacing'])
    bar_r = b.div(0.008, I['Rebar Spacing'])  # 16 mm bars

    def bar(x):  # round profile of a bar along whole numbers of x
        f = b.absolute(b.sub(b.fract(b.add(x, 0.5)), 0.5))
        return b.math('SQRT', b.clamp01(b.one_minus(b.mul(b.div(f, bar_r), b.div(f, bar_r)))))
    bars = b.maximum(bar(rs), bar(rt))
    ribs = b.madd(b.math('SINE', b.mul(b.add(rs, rt), 250.0)), 0.5, 0.5)
    rebar = b.mul(b.mul(b.smoothstep(0.0, 0.3, bars), deep), I['Rebar'])
    rebar_rust = b.smoothstep(-0.5, 1.2, S.znoise(30.0, 15, detail=3.0, label='Rebar Rust'))
    col = b.mix_color(rebar, col, b.mix_color(rebar_rust, REBAR, RUST))
    metal = b.mul(rebar, b.madd(rebar_rust, -0.5, 0.6))
    rough = b.mix(rebar, rough, b.madd(rebar_rust, 0.2, 0.6))
    h = b.madd(rebar, b.madd(bars, 0.3, b.mul(ribs, 0.03)), h)
    # rust bleeding around the bars
    halo = b.mul(b.mul(b.smoothstep(0.0, 1.0, bars), spall), b.mul(I['Rebar'], 0.6))
    col = b.mix_color(b.mul(halo, b.one_minus(rebar)), col, b.mix_color(0.5, RUST_DARK, RUST))

    # craters: one per cell of a 25 cm grid at most, jittered (cells line up with tiles: seamless)
    cs, ct = _cells(b, S, tile, span, 0.25, 0.25)
    cell_rand, cell_col = b.white_noise(b.combine(b.floor(cs), b.floor(ct), b.add(I['Seed'], 0.53)), dims='3D')
    cr, cg, cb = b.separate_color(cell_col)
    crater_r = b.madd(b.mul(cell_rand, cell_rand), 0.24, 0.08)  # mostly small, a few big ones
    dx = b.sub(b.fract(cs), b.madd(cg, 0.3, 0.35))
    dy = b.sub(b.fract(ct), b.madd(cb, 0.3, 0.35))
    cd = b.div(b.math('SQRT', b.madd(dx, dx, b.mul(dy, dy))), crater_r)  # 0 in the middle, 1 at the rim
    hit = b.math('LESS_THAN', cr, b.mul(I['Impacts'], 0.6))
    crater = b.mul(b.mul(b.one_minus(b.smoothstep(0.55, 1.0, b.madd(broken, 0.12, cd))), hit),
                   b.clamp01(b.mul(I['Impacts'], 20.0)))
    hole = b.mul(b.one_minus(b.smoothstep(0.1, 0.3, cd)), crater)
    col = b.mix_color(crater, col, b.color_scale(I['Concrete Color'], b.madd(broken, 0.08, 1.12)))
    col = b.mix_color(b.mul(b.mul(crater, b.smoothstep(0.0, 0.12, shape)), 0.7), col, stone_col)
    col = b.mix_color(b.mul(hole, 0.9), col, b.color_scale(I['Concrete Color'], 0.25))
    rough = b.mix(crater, rough, 0.95)
    h = b.madd(crater, b.madd(cd, 0.3, b.madd(broken, 0.05, -0.45)), h)

    # ---- stains: color and gloss only
    streak_aniso = (1.0, 1.0 / 16.0) if tile else (1.0, 1.0, 1.0 / 16.0)
    stz = S.znoise(5.0, 20, detail=4.0, roughness=0.6, aniso=streak_aniso, label='Streaks')
    stz2 = S.znoise(3.0, 21, detail=4.0, roughness=0.6, aniso=streak_aniso, label='Streaks 2')
    streak_on = F.cover(b, S.znoise(0.8, 22, detail=2.0, label='Streak Areas'), 0.6, 0.8, gate=False)

    rust = b.maximum(b.mul(F.cover(b, stz, b.mul(I['Rust Stains'], 0.3), 0.5), streak_on),
                     b.mul(crack_zone, b.mul(I['Rust Stains'], 0.6)))
    col = b.mix_color(b.mul(rust, 0.7), col, b.mix_color(b.smoothstep(-1.0, 1.5, stz2), RUST_DARK, RUST))

    wet_low = b.one_minus(b.smoothstep(0.0, 0.25, b.madd(vz, 0.04, height_obj))) if has_geo else 0.3
    water = b.maximum(b.mul(F.cover(b, stz2, b.mul(I['Water Stains'], 0.4), 0.6), streak_on),
                      b.mul(wet_low, b.mul(I['Water Stains'], 0.7)))
    col = b.color_scale(col, b.madd(water, -0.35, 1.0))
    rough = b.madd(water, -0.08, rough)

    salt = b.maximum(b.mul(crack_zone, I['Efflorescence']),
                     b.mul(F.cover(b, b.madd(stz, 0.7, stz2), b.mul(I['Efflorescence'], 0.2), 0.6), streak_on))
    if has_geo:
        salt = b.maximum(salt, b.mul(b.mul(wet_low, I['Efflorescence']), b.clamp01(b.madd(vz2, 0.3, 0.3))))
    salt = b.mul(salt, b.clamp01(b.madd(sand, 1.2, 0.2)))
    col = b.mix_color(b.mul(salt, 0.85), col, SALT)
    rough = b.mix(salt, rough, 0.95)

    dz = S.znoise(2.0, 23, detail=5.0, roughness=0.6, label='Dirt Patches')
    dirt = I['Dirt']
    grime = b.mul(F.cover(b, dz, b.mul(dirt, 0.35), 0.9), 0.55)
    grime = b.maximum(grime, b.mul(b.mul(b.maximum(joint, mortar), dirt), 0.8))
    if has_geo:
        grime = b.maximum(grime, b.mul(b.smoothstep(0.1, 0.7, b.madd(vz2, 0.08, cav)), dirt))
        grime = b.maximum(grime, b.mul(b.one_minus(b.smoothstep(0.0, 0.18, b.madd(dz, 0.03, height_obj))),
                                       b.mul(dirt, 0.8)))
    grime = b.clamp01(grime)
    col = b.mix_color(grime, col, b.color_scale(I['Dirt Color'], b.madd(dz, 0.15, 1.0)))
    rough = b.mix(grime, rough, 0.9)

    moss = I['Moss']
    mz = S.znoise(4.0, 24, detail=6.0, roughness=0.65, label='Moss')
    moss_where = b.madd(mz, 0.8, b.mul(b.maximum(crack_zone, b.maximum(joint, mortar)), 2.0))
    if has_geo:
        up = b.separate(b.geometry().outputs['Normal'])[2]
        moss_where = b.add(moss_where, b.madd(cav, 2.0, b.madd(up, 0.6, b.mul(wet_low, 1.2))))
    moss_mask = F.cover(b, moss_where, b.mul(moss, 0.4), 0.35)
    moss_col = b.mix_color(b.smoothstep(-1.0, 1.5, b.madd(sand, 2.0, mz)), MOSS, MOSS_LIGHT)
    col = b.mix_color(moss_mask, col, moss_col)
    rough = b.mix(moss_mask, rough, 0.92)
    hm = b.madd(moss_mask, b.madd(sand, 1.5, 0.5), hm)

    oil = b.mul(F.cover(b, S.znoise(1.6, 25, detail=5.0, roughness=0.55, label='Oil'),
                        b.mul(I['Oil Stains'], 0.3), 0.5), b.clamp01(b.madd(vz2, 0.2, 0.85)))
    col = b.color_scale(col, b.madd(oil, -0.65, 1.0))
    rough = b.mix(oil, rough, 0.3)

    soot_where = b.madd(dz, 0.9, b.mul(b.one_minus(height_obj), 1.4)) if has_geo else dz
    soot = F.cover(b, soot_where, b.mul(I['Soot'], 0.55), 0.9)
    col = b.mix_color(soot, col, b.color_scale(SOOT, b.madd(vz2, 0.3, 1.2)))
    rough = b.mix(soot, rough, 0.95)

    wet = I['Wetness']
    col = b.color_scale(col, b.madd(wet, -0.4, 1.0))
    rough = b.mix(wet, rough, b.madd(sand, 0.1, 0.12))

    C.finish(b, gout, I, col, metal, rough, b.clamp01(h), hm, distance=CONCRETE_BUMP)


SPEC = dict(
    label='Concrete', category='CONCRETE', params=CONCRETE_PARAMS, outputs=C.COMMON_OUTPUTS, build=build_concrete,
    display=('Concrete Color', 0.0, 'Roughness'), bump=CONCRETE_BUMP,
)
