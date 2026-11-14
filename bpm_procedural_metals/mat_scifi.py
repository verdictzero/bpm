# SPDX-License-Identifier: GPL-3.0-or-later
"""Sci-fi hull generator: plated spaceship hulls, corridor walls, armor and machinery.

Layers: plates (a grid whose cells are split in two up to twice each way, or
hexagons) at slightly different heights with chamfered edges and seams between
them; per-plate paint (accent colors, dark plates, hazard stripes); details
(rows of rivets, louvered vents, trays of greebles, fine panel lines); lights
(small glowing windows and glowing seams); wear (bare metal on the plate edges,
scratches, rust, grime in the seams, leak streaks, scorch marks).

The plates are computed in a 2D plane (features.Plane): the one the surface
faces most in object mode, a whole number of plates across in tile mode.
"""

import math

from . import features as F
from . import gencommon as C
from .nodebuilder import is_socket

SCIFI_BUMP = 0.02  # relief depth of the full 0..1 height range (meters at Scale 1)

LAYOUTS = (('Plates', 0), ('Hexagons', 1))
SOOT = (0.010, 0.009, 0.009)
GRIME = (0.022, 0.018, 0.014)
SQRT3 = math.sqrt(3.0)


def _enum(name, default, items, panel, desc, key=False):
    return C.Param(name, 'FLOAT', float(default), float(items[0][1]), float(items[-1][1]), panel, desc,
                   ui=('ENUM', items), key=key)


SCIFI_PARAMS = [
    # -- Plates
    _enum('Layout', 0, LAYOUTS, 'Plates', 'Plates: rectangular hull plates of mixed sizes. Hexagons: '
          'honeycomb armor tiles', key=True),
    C.Param('Plate Size', 'FLOAT', 0.5, 0.01, 20.0, 'Plates', 'Size of the biggest plates', subtype='DISTANCE',
            key=True),
    C.fac('Plate Variation', 0.6, 'Plates', 'How many plates are split into smaller ones', key=True),
    C.Param('Seam Width', 'FLOAT', 0.006, 0.0, 0.1, 'Plates', 'Width of the gaps between the plates',
            subtype='DISTANCE'),
    C.fac('Seam Depth', 0.6, 'Plates', 'Depth of the gaps between the plates'),
    C.fac('Bevel', 0.3, 'Plates', 'Width of the chamfer around every plate'),
    C.fac('Height Variation', 0.4, 'Plates', 'Plates standing higher and lower than their neighbors', key=True),
    # -- Surface
    C.color('Hull Color', (0.45, 0.46, 0.48), 'Surface', 'Color of the hull', key=True),
    C.fac('Metallic', 0.0, 'Surface', '0 = painted or ceramic hull, 1 = bare metal', key=True),
    C.fac('Roughness', 0.45, 'Surface', '0 = glossy, 1 = rough and dull'),
    C.fac('Color Variation', 0.3, 'Surface', 'Lighter, darker, shinier and duller plates'),
    C.fac('Dark Plates', 0.1, 'Surface', 'Share of much darker plates'),
    C.fac('Accent Plates', 0.08, 'Surface', 'Share of plates painted in the accent color', key=True),
    C.color('Accent Color', (0.55, 0.12, 0.02), 'Surface', 'Color of the accent plates'),
    C.fac('Hazard Stripes', 0.0, 'Surface', 'Share of plates with diagonal warning stripes'),
    C.color('Stripe Color', (0.75, 0.52, 0.02), 'Surface', 'Color of the warning stripes (on black)'),
    # -- Details
    C.fac('Rivets', 0.5, 'Details', 'Share of plates with rows of rivets along their edges', key=True),
    C.Param('Rivet Spacing', 'FLOAT', 0.08, 0.005, 2.0, 'Details', 'Distance between the rivets',
            subtype='DISTANCE'),
    C.Param('Rivet Size', 'FLOAT', 0.008, 0.0005, 0.2, 'Details', 'Radius of the rivets', subtype='DISTANCE'),
    C.fac('Vents', 0.1, 'Details', 'Share of plates with louvered vents', key=True),
    C.fac('Greebles', 0.1, 'Details', 'Share of plates that are trays of small machinery blocks', key=True),
    C.fac('Fine Panels', 0.3, 'Details', 'Thin engraved lines dividing the plates further'),
    C.Param('Detail Size', 'FLOAT', 0.08, 0.002, 5.0, 'Details',
            'Size of the greebles, fine panels, vent slats and windows', subtype='DISTANCE'),
    # -- Lights
    C.fac('Lights', 0.0, 'Lights', 'Small glowing windows and indicator lights', key=True),
    C.fac('Seam Glow', 0.0, 'Lights', 'Light shining out of the seams between the plates', key=True),
    C.color('Light Color', (1.0, 0.75, 0.4), 'Lights', 'Color of the lights'),
    C.Param('Emission Strength', 'FLOAT', 8.0, 0.0, 500.0, 'Lights', 'Brightness of the lights'),
    # -- Wear
    C.fac('Edge Wear', 0.3, 'Wear', 'Paint worn down to bare metal on the edges of the plates', key=True),
    C.fac('Scratches', 0.2, 'Wear', 'Fine scratches'),
    C.fac('Grime', 0.3, 'Wear', 'Dirt in the seams, around rivets and in patches', key=True),
    C.fac('Streaks', 0.2, 'Wear', 'Dark leak streaks running down the hull'),
    C.fac('Rust', 0.0, 'Wear', 'Rust creeping out of the seams', key=True),
    C.fac('Scorch', 0.0, 'Wear', 'Black burn marks from weapons fire or re-entry'),
] + C.PATTERN_PARAMS


def _split_cells(b, I, s, t, size, nw, nh, vary, key):
    """Cells of `size` in the (s, t) plane, each split in two up to twice along each axis.
    Returns (fx, fy: 0..1 across the cell, w, h: its size, cell number as a vector)."""
    x, y = b.div(s, size), b.div(t, size)
    i, j = b.floor(x), b.floor(y)
    fx, fy = b.sub(x, i), b.sub(y, j)
    if nw is not None:  # tiles: the same cells on both sides of a seam
        i, j = b.wrap(i, nw), b.wrap(j, nh)
    sx = sy = 1.0
    for level, share in ((1, 0.8), (2, 0.6)):
        _value, rnd = b.white_noise(b.combine(i, j, b.add(I['Seed'], key + 0.17 * level)))
        ra, rb, _rc = b.separate_color(rnd)
        nx = b.add(b.math('LESS_THAN', ra, b.mul(vary, share)), 1.0)
        ny = b.add(b.math('LESS_THAN', rb, b.mul(vary, share)), 1.0)
        lx, ly = b.mul(fx, nx), b.mul(fy, ny)
        kx, ky = b.floor(lx), b.floor(ly)
        fx, fy = b.sub(lx, kx), b.sub(ly, ky)
        i, j = b.madd(kx, 0.5 ** level, i), b.madd(ky, 0.5 ** level, j)
        sx, sy = b.div(sx, nx), b.div(sy, ny)
    return fx, fy, b.mul(sx, size), b.mul(sy, size), b.combine(i, j, key)


def _to_sides(b, f, size):
    """Distance (pattern units) to the nearer of the two sides of a cell (f: 0..1 across it)."""
    return b.mul(b.sub(0.5, b.absolute(b.sub(f, 0.5))), size)


def build_scifi(b, I, gout, tile):
    S = F.Space(b, tile, I['Scale'], I['Seed'], I['Tile Size'] if tile else 1.0)
    inv = b.div(1.0, I['Scale'])
    span = b.mul(I['Tile Size'], I['Scale']) if tile else None
    edge = F.edge_mask(b, S, b.mul(0.02, inv))
    cav = F.cavity_mask(b, S, b.mul(inv, 0.2))
    has_geo = is_socket(edge)
    plane = F.Plane(b, S, span)
    P = I['Plate Size']
    seam = I['Seam Width']
    half = b.mul(seam, 0.5)

    # ---- plates: rectangles of mixed sizes, or hexagons
    s, t, nw, nh = plane.grid(P)
    fx, fy, w, h, plate_id = _split_cells(b, I, s, t, P, nw, nh, I['Plate Variation'], 1.0)
    dx, dy = _to_sides(b, fx, w), _to_sides(b, fy, h)

    hexes = b.math('COMPARE', I['Layout'], 1.0, 0.5)
    hs_, ht, hnw, hnh = plane.grid(P, b.mul(P, SQRT3))
    x, y = b.div(hs_, P), b.div(ht, P)
    ax, ay = b.sub(b.wrap(x, 1.0), 0.5), b.sub(b.wrap(y, SQRT3), SQRT3 / 2.0)
    bx = b.sub(b.wrap(b.sub(x, 0.5), 1.0), 0.5)
    by = b.sub(b.wrap(b.sub(y, SQRT3 / 2.0), SQRT3), SQRT3 / 2.0)
    other = b.math('LESS_THAN', b.madd(bx, bx, b.mul(by, by)), b.madd(ax, ax, b.mul(ay, ay)))
    gx, gy = b.mix(other, ax, bx), b.mix(other, ay, by)  # from the nearest center
    hd = b.maximum(b.absolute(gx), b.madd(b.absolute(gx), 0.5, b.mul(b.absolute(gy), SQRT3 / 2.0)))
    hex_d = b.mul(b.sub(0.5, hd), P)
    hex_i = plane.wrapped(b.math('ROUND', b.mul(b.sub(x, gx), 2.0)), b.mul(hnw, 2.0) if tile else None)
    hex_j = plane.wrapped(b.math('ROUND', b.mul(b.sub(y, gy), 2.0 / SQRT3)), b.mul(hnh, 2.0) if tile else None)
    plate_id = b.mix_vector(hexes, plate_id, b.combine(hex_i, hex_j, 5.0))
    d = b.mix(hexes, b.minimum(dx, dy), hex_d)
    rect = b.one_minus(hexes)  # rivet rows, vents and stripes need the rectangle's own coordinates
    small = b.minimum(w, h)

    # random numbers of each plate
    r1, rc1 = b.white_noise(b.vadd(plate_id, b.combine(I['Seed'], 0.37, 0.61)))
    r2, r3, r4 = b.separate_color(rc1)
    r5, rc2 = b.white_noise(b.vadd(plate_id, b.combine(b.add(I['Seed'], 0.53), 0.11, 0.83)))
    r6, r7, r8 = b.separate_color(rc2)

    # ---- small cells: greebles, fine panel lines, windows
    D = I['Detail Size']
    s2, t2, nw2, nh2 = plane.grid(D)
    gfx, gfy, gw, gh, cell_id = _split_cells(b, I, s2, t2, D, nw2, nh2, 0.7, 2.0)
    gd = b.minimum(_to_sides(b, gfx, gw), _to_sides(b, gfy, gh))
    g1, gc = b.white_noise(b.vadd(cell_id, b.combine(I['Seed'], 0.71, 0.29)))
    g2, g3, _g4 = b.separate_color(gc)

    # ---- shape: seams, chamfers, plates at different heights
    fd = b.sub(d, half)  # depth into the plate's face
    bevel_w = b.maximum(b.mul(I['Bevel'], b.mul(P, 0.04)), 0.0002)
    prof = b.clamp01(b.div(fd, bevel_w))
    face = b.smoothstep(0.0, b.mul(bevel_w, 0.5), fd)  # 1 on the plates, 0 in the seams
    inside = b.smoothstep(0.0, 0.004, b.sub(fd, b.madd(small, 0.06, bevel_w)))  # the plate without its border
    step = b.mul(b.sub(b.floor(b.mul(r1, 3.0)), 1.0), 0.5)  # -0.5, 0 or 0.5
    h_plate = b.madd(step, b.mul(I['Height Variation'], 0.3), 0.6)
    h_seam = b.sub(0.5, b.mul(I['Seam Depth'], 0.3))
    hh = b.mix(prof, h_seam, h_plate)

    # ---- color: hull paint, per-plate variation, dark and accent plates, hazard stripes
    variation = I['Color Variation']
    col = b.color_scale(I['Hull Color'], b.madd(b.sub(r2, 0.5), b.mul(variation, 0.5), 1.0))
    dark = b.math('LESS_THAN', r3, I['Dark Plates'])
    col = b.color_scale(col, b.madd(dark, -0.6, 1.0))
    accent = b.math('LESS_THAN', r4, I['Accent Plates'])
    col = b.mix_color(accent, col, b.color_scale(I['Accent Color'], b.madd(b.sub(r2, 0.5), 0.2, 1.0)))
    striped = b.mul(b.mul(b.math('LESS_THAN', r5, I['Hazard Stripes']), rect), inside)
    band = b.math('LESS_THAN', b.fract(b.div(b.add(s, t), b.maximum(b.mul(D, 1.2), 0.001))), 0.5)
    col = b.mix_color(striped, col, b.mix_color(band, (0.012, 0.012, 0.012), I['Stripe Color']))
    painted = b.maximum(accent, striped)
    metal = b.mul(I['Metallic'], b.one_minus(painted))
    cloud = S.znoise(3.0, 10, detail=4.0, roughness=0.6, label='Clouds')
    rough = b.madd(b.sub(r6, 0.5), b.mul(variation, 0.25), b.madd(cloud, 0.03, I['Roughness']))
    col = b.color_scale(col, b.madd(cloud, 0.03, 1.0))
    hm = b.mul(S.znoise(180.0, 11, detail=2.0, roughness=0.5, label='Grain'), 0.15)

    # ---- fine panel lines: thin grooves between the small cells
    line = b.one_minus(b.smoothstep(0.0, b.maximum(b.mul(D, 0.03), 0.0006), gd))
    fine = b.mul(b.mul(line, inside), b.mul(I['Fine Panels'], b.math('LESS_THAN', r7, 0.6)))
    hh = b.madd(fine, -0.05, hh)
    col = b.color_scale(col, b.madd(fine, -0.45, 1.0))

    # ---- rivets: rows along the sides of the rectangular plates
    rr = I['Rivet Size']
    inset = b.madd(rr, 2.5, bevel_w)

    def row(f, size, across):  # distance to the nearest rivet of the rows along one pair of sides
        run = b.maximum(b.sub(size, b.mul(inset, 2.0)), 0.0001)
        count = b.maximum(1.0, b.math('ROUND', b.div(run, I['Rivet Spacing'])))
        pitch = b.div(run, count)
        a = b.div(b.sub(b.mul(f, size), inset), pitch)
        along = b.mul(b.sub(a, b.clamp(b.math('ROUND', a), 0.0, count)), pitch)
        off = b.sub(across, inset)
        return b.math('SQRT', b.madd(along, along, b.mul(off, off)))
    rivet_d = b.div(b.minimum(row(fx, w, dy), row(fy, h, dx)), b.maximum(rr, 0.00001))
    riveted = b.mul(b.math('LESS_THAN', r8, I['Rivets']), rect)
    rivet = b.mul(b.clamp01(b.sub(1.0, b.mul(rivet_d, rivet_d))), riveted)
    ring = b.mul(b.mul(b.one_minus(b.smoothstep(1.0, 2.2, rivet_d)), riveted), b.one_minus(b.clamp01(rivet)))
    hh = b.madd(rivet, 0.1, hh)
    col = b.color_scale(col, b.madd(rivet, 0.12, 1.0))

    # ---- vents: louvered slats in the middle of some plates
    slat = b.fract(b.div(b.mul(fy, h), b.maximum(b.mul(D, 0.35), 0.0005)))
    vent_in = b.mul(b.smoothstep(0.0, 0.003, b.sub(dx, b.madd(w, 0.12, bevel_w))),
                    b.smoothstep(0.0, 0.003, b.sub(dy, b.madd(h, 0.18, bevel_w))))
    vent = b.mul(b.mul(b.math('LESS_THAN', r7, I['Vents']), rect), vent_in)
    hh = b.mix(vent, hh, b.madd(slat, 0.14, b.sub(h_plate, 0.2)))
    gap = b.mul(vent, b.one_minus(b.smoothstep(0.0, 0.4, slat)))
    col = b.color_scale(col, b.madd(gap, -0.85, 1.0))
    rough = b.madd(gap, 0.3, rough)

    # ---- greebles: trays of small blocks of different heights
    tray = b.mul(b.mul(b.math('LESS_THAN', r6, I['Greebles']), inside), b.one_minus(vent))
    block = b.clamp01(b.div(b.sub(gd, b.mul(D, 0.03)), b.maximum(b.mul(D, 0.04), 0.0003)))
    level = b.mul(b.floor(b.mul(g1, 4.0)), 1.0 / 3.0)
    hh = b.mix(tray, hh, b.madd(block, b.madd(level, 0.26, 0.04), b.sub(h_plate, 0.14)))
    col = b.color_scale(col, b.madd(tray, b.madd(b.sub(g2, 0.5), 0.5, b.madd(block, 0.3, -0.3)), 1.0))

    # ---- wear: bare metal on the edges, scratches
    wear_z = S.znoise(45.0, 12, detail=4.0, roughness=0.65, label='Wear')
    rim = b.mul(b.one_minus(b.smoothstep(0.0, b.madd(bevel_w, 1.5, 0.003), fd)), face)
    rim = b.maximum(rim, b.maximum(b.mul(rivet, 0.8), b.mul(tray, b.smoothstep(0.75, 1.0, block))))
    if has_geo:
        rim = b.maximum(rim, edge)
    worn = F.cover(b, b.madd(rim, 3.2, b.madd(cloud, 0.3, b.mul(wear_z, 0.7))), b.mul(I['Edge Wear'], 0.2), 0.3)
    worn = b.mul(worn, b.one_minus(b.maximum(vent, b.one_minus(face))))
    scratch = F.scratch_mask(b, S, I['Scratches'], 1.0, 13)
    bare = b.maximum(worn, b.mul(scratch, 0.7))
    col = b.mix_color(bare, col, b.color_scale(C.STEEL, b.madd(wear_z, 0.04, 0.85)))
    metal = b.mix(bare, metal, 1.0)
    rough = b.mix(bare, rough, b.madd(wear_z, 0.03, 0.34))
    hm = b.madd(bare, -0.6, hm)

    # ---- rust out of the seams and edges
    rust_col, rust_rough, rust_h = F.rust_layer(b, S, 1.0, C.RUST_A, C.RUST_B, 14)
    rust_z = S.znoise(5.0, 16, detail=5.0, roughness=0.65, label='Rust Patches')
    rust_where = b.madd(b.maximum(b.one_minus(face), b.maximum(rim, ring)), 2.2, rust_z)
    rust = F.cover(b, rust_where, b.mul(I['Rust'], 0.5), 0.35)
    col = b.mix_color(rust, col, rust_col)
    metal = b.mix(rust, metal, 0.0)
    rough = b.mix(rust, rough, rust_rough)
    hm = b.madd(rust, b.sub(rust_h, 0.3), hm)

    # ---- grime: in the seams, around rivets, in corners, in patches and streaks
    grime_amount = I['Grime']
    dz = S.znoise(2.5, 17, detail=5.0, roughness=0.6, label='Grime Patches')
    grime = b.mul(F.cover(b, dz, b.mul(grime_amount, 0.3), 0.9), 0.55)
    packed = b.maximum(b.one_minus(face), b.maximum(ring, b.maximum(gap, b.mul(tray, b.one_minus(block)))))
    grime = b.maximum(grime, b.mul(packed, b.mul(grime_amount, 0.9)))
    if has_geo:
        grime = b.maximum(grime, b.mul(b.smoothstep(0.1, 0.7, b.madd(dz, 0.05, cav)), grime_amount))
    streak_aniso = (1.0, 1.0 / 20.0) if tile else (1.0, 1.0, 1.0 / 20.0)
    stz = S.znoise(5.0, 18, detail=4.0, roughness=0.6, aniso=streak_aniso, label='Streaks')
    streak_on = F.cover(b, S.znoise(0.9, 19, detail=2.0, label='Streak Areas'), 0.55, 0.8, gate=False)
    streaks = b.mul(b.mul(F.cover(b, stz, b.mul(I['Streaks'], 0.35), 0.5), streak_on), 0.75)
    grime = b.clamp01(b.maximum(grime, streaks))
    col = b.mix_color(grime, col, b.color_scale(GRIME, b.madd(dz, 0.15, 1.0)))
    metal = b.mix(grime, metal, 0.0)
    rough = b.mix(grime, rough, 0.85)

    # ---- scorch marks
    burn_z = S.znoise(1.3, 20, detail=5.0, roughness=0.7, distortion=0.6, label='Scorch')
    burnt = b.mul(F.cover(b, burn_z, b.mul(I['Scorch'], 0.45), 0.7), b.clamp01(b.madd(wear_z, 0.2, 0.85)))
    col = b.mix_color(burnt, col, b.color_scale(SOOT, b.madd(wear_z, 0.2, 1.1)))
    metal = b.mix(burnt, metal, 0.0)
    rough = b.mix(burnt, rough, 0.92)

    # ---- lights: windows in the small cells, light out of the seams
    window_in = b.smoothstep(0.0, b.maximum(b.mul(D, 0.02), 0.0004), b.sub(gd, b.mul(b.minimum(gw, gh), 0.22)))
    lit = b.mul(b.math('LESS_THAN', g3, b.mul(I['Lights'], 0.3)), b.mul(window_in, inside))
    lit = b.mul(lit, b.one_minus(b.maximum(vent, tray)))
    power = b.mul(lit, b.madd(g2, 0.7, 0.3))  # every window its own brightness
    seam_light = b.mul(b.one_minus(b.smoothstep(b.mul(half, 0.3), b.madd(half, 1.0, 0.0005), d)), I['Seam Glow'])
    glow = b.mul(b.clamp01(b.add(power, seam_light)), b.one_minus(b.mul(b.maximum(grime, burnt), 0.8)))
    col = b.mix_color(lit, col, b.color_scale(I['Light Color'], 0.5))
    metal = b.mix(lit, metal, 0.0)
    rough = b.mix(lit, rough, 0.12)
    hh = b.madd(lit, -0.04, hh)

    C.finish(b, gout, I, col, metal, rough, b.clamp01(hh), hm, distance=SCIFI_BUMP, extra={
        'Emission': b.color_scale(I['Light Color'], glow),
        'Emission Strength': I['Emission Strength'],
    })


SPEC = dict(
    label='Sci-Fi Hull', category='SCIFI', params=SCIFI_PARAMS, outputs=C.COMMON_OUTPUTS + C.EMISSION_OUTPUTS,
    build=build_scifi, links={'Emission': 'Emission Color', 'Emission Strength': 'Emission Strength'},
    display=('Hull Color', 'Metallic', 'Roughness'), bump=SCIFI_BUMP, fit=0.5, glow=('Lights', 'Seam Glow'),
)
