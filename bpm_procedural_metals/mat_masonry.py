# SPDX-License-Identifier: GPL-3.0-or-later
"""Masonry generator: brick, block, cut stone, fieldstone, cobble and tile walls and floors.

Layers: the layout (running bond with any row offset, random ashlar courses,
English and Flemish bond, herringbone, basketweave, random stones, hexagons);
every unit with its own color, mottling, sandy face, specks, pores, rounded or
split (rock-faced) face, domes for cobbles and fieldstone, glaze, and stone
faces (marble veins, sediment layers, granite crystals); mortar joints from
flush to deeply raked and crumbling; damage (chipped edges and corners,
cracks, broken and missing units, weathering); coatings (paint that peels,
limewash); stains (salt, water, dirt, moss, soot, wetness).

All layouts are computed in a 2D plane: in object mode the one the surface
faces most (walls: X or Y and Z, floors: X and Y), as tiles across a whole
number of units, so they stay seamless.  Random stones are 3D cells instead.
"""

import math

from . import features as F
from . import gencommon as C
from .nodebuilder import is_socket

MASONRY_BUMP = 0.03  # relief depth of the full 0..1 height range (meters at Scale 1)

LAYOUTS = (('Running', 0), ('English', 1), ('Flemish', 2), ('Herringbone', 3), ('Basketweave', 4),
           ('Stone', 5), ('Hexagon', 6))
OFFSETS = (('Stack', 0.0), ('Quarter', 0.25), ('Third', 1.0 / 3.0), ('Half', 0.5))

BROKEN = (0.42, 0.25, 0.17)  # inside of a broken brick (scaled by the unit color)
SALT = (0.80, 0.80, 0.78)
LIME = (0.78, 0.77, 0.72)
MOSS = (0.045, 0.075, 0.015)
MOSS_LIGHT = (0.09, 0.12, 0.03)
SOOT = (0.012, 0.011, 0.010)
HOLE = (0.006, 0.005, 0.004)
SQRT3 = math.sqrt(3.0)


def _enum(name, default, items, panel, desc, key=False):
    return C.Param(name, 'FLOAT', float(default), float(items[0][1]), float(items[-1][1]), panel, desc,
                   ui=('ENUM', items), key=key)


MASONRY_PARAMS = [
    # -- Layout
    _enum('Layout', 0, LAYOUTS, 'Layout',
          'How the units are laid. Running: rows shifted by the Row Offset (bricks, blocks, ashlar, tiles). '
          'English: rows of long sides and rows of ends. Flemish: long sides and ends taking turns in every '
          'row. Herringbone and Basketweave: paving patterns. Stone: random stones (fieldstone, rubble, '
          'cobbles, flagstones). Hexagon: hexagonal pavers and tiles', key=True),
    C.Param('Unit Width', 'FLOAT', 0.215, 0.005, 5.0, 'Layout',
            'Length of one brick, block or stone, without the mortar (Stone: the stone size, Hexagon: the '
            'width across the flats)', subtype='DISTANCE', key=True),
    C.Param('Unit Height', 'FLOAT', 0.065, 0.005, 5.0, 'Layout',
            'Height of one brick, block or stone, without the mortar (Herringbone and Basketweave: the width '
            'of a paver; Stone: lower = flatter stones)', subtype='DISTANCE', key=True),
    C.Param('Row Offset', 'FLOAT', 0.5, 0.0, 1.0, 'Layout',
            'How far each row is shifted (Running): Half = classic brick wall, Stack = straight joints',
            ui=('CHOICES', OFFSETS)),
    C.fac('Random Offset', 0.0, 'Layout', 'Every row shifted by a random amount (ashlar, rustic walls)'),
    C.fac('Length Variation', 0.0, 'Layout', 'Units split in two of random lengths (random ashlar, stone blocks)'),
    C.fac('Irregularity', 0.0, 'Layout', 'Hand-laid look: wavy rows and joints (Stone: irregular shapes)'),
    # -- Units
    C.color('Unit Color', (0.30, 0.075, 0.035), 'Units', 'Color of the bricks, blocks or stones', key=True),
    C.color('Unit Color 2', (0.17, 0.05, 0.03), 'Units', 'Second color: each unit lies between the two'),
    C.fac('Color Variation', 0.5, 'Units', 'How far the units vary between the two colors', key=True),
    C.fac('Brightness Variation', 0.3, 'Units', 'Lighter and darker units'),
    C.fac('Dark Units', 0.0, 'Units', 'Share of very dark, overfired units (clinker bricks)'),
    C.fac('Dark Headers', 0.0, 'Units', 'Darker brick ends (English and Flemish bond patterns)'),
    C.fac('Mottling', 0.4, 'Units', 'Cloudy, uneven color inside each unit'),
    C.fac('Roughness', 0.85, 'Units', '0 = glossy, 1 = rough and dull'),
    C.fac('Face Texture', 0.5, 'Units', 'Sandy, grainy face'),
    C.fac('Speckles', 0.15, 'Units', 'Dark specks of iron or aggregate'),
    C.fac('Pores', 0.0, 'Units', 'Small holes in the face (cinder blocks, travertine, lava stone)'),
    C.fac('Edge Rounding', 0.2, 'Units', 'Soft, rounded edges (0 = crisp, sharp edges)'),
    C.fac('Bulge', 0.0, 'Units', 'Domed faces: cobbles and fieldstones bulge out of the mortar', key=True),
    C.fac('Split Face', 0.0, 'Units', 'Rough, chiseled face (split-face block, rock-faced stone)'),
    C.fac('Glaze', 0.0, 'Units', 'Glossy glazed face (glazed bricks, ceramic tiles)'),
    # -- Stone
    C.fac('Veins', 0.0, 'Stone', 'Marble veins'),
    C.color('Vein Color', (0.62, 0.60, 0.56), 'Stone', 'Color of the veins'),
    C.fac('Layers', 0.0, 'Stone', 'Bands of sediment (sandstone, limestone, slate)'),
    C.fac('Crystals', 0.0, 'Stone', 'Dark and light crystal grains (granite)'),
    C.color('Crystal Color', (0.02, 0.02, 0.022), 'Stone', 'Color of the dark grains'),
    # -- Mortar
    C.Param('Mortar Width', 'FLOAT', 0.01, 0.0, 0.2, 'Mortar', 'Width of the joints (0 = dry-laid, no mortar)',
            subtype='DISTANCE', key=True),
    C.color('Mortar Color', (0.30, 0.29, 0.26), 'Mortar', 'Color of the mortar or grout', key=True),
    C.fac('Mortar Depth', 0.3, 'Mortar', '0 = flush with the face, 1 = deeply raked joints'),
    C.fac('Mortar Texture', 0.5, 'Mortar', 'Sandy, uneven mortar'),
    C.fac('Mortar Erosion', 0.0, 'Mortar', 'Crumbled and washed out mortar'),
    # -- Damage
    C.fac('Chipped Edges', 0.15, 'Damage', 'Chipped edges and corners of the units', key=True),
    C.fac('Cracks', 0.0, 'Damage', 'Cracks through the units', key=True),
    C.scale('Crack Scale', 2.0, 0.1, 50.0, 'Damage', 'Size of the cracked pieces (higher = smaller)'),
    C.fac('Broken Units', 0.0, 'Damage', 'Share of units with a broken, crumbled face'),
    C.fac('Missing Units', 0.0, 'Damage', 'Share of units fallen out: dark holes'),
    C.fac('Weathering', 0.0, 'Damage', 'Worn by the weather: rounded, pitted, softened faces'),
    # -- Coating
    C.fac('Paint', 0.0, 'Coating', 'Painted over (units and mortar)', key=True),
    C.color('Paint Color', (0.75, 0.74, 0.70), 'Coating', 'Color of the paint'),
    C.fac('Peeling', 0.0, 'Coating', 'Paint flaking off'),
    C.fac('Limewash', 0.0, 'Coating', 'Thin, patchy white limewash'),
    # -- Stains
    C.fac('Efflorescence', 0.0, 'Stains', 'White salt deposits on the joints and low down'),
    C.fac('Water Stains', 0.1, 'Stains', 'Dark streaks and damp patches from rain water'),
    C.fac('Dirt', 0.2, 'Stains', 'Grime in the joints, in corners and low down', key=True),
    C.color('Dirt Color', (0.06, 0.05, 0.04), 'Stains', 'Color of the dirt'),
    C.fac('Moss', 0.0, 'Stains', 'Green moss in the joints and on damp tops'),
    C.fac('Soot', 0.0, 'Stains', 'Blackened by smoke and fire'),
    C.fac('Wetness', 0.0, 'Stains', 'Wet: darker and shiny'),
] + C.PATTERN_PARAMS + [C.DISPLACE_PARAM]


def build_masonry(b, I, gout, tile):
    S = F.Space(b, tile, I['Scale'], I['Seed'], I['Tile Size'] if tile else 1.0)
    inv = b.div(1.0, I['Scale'])
    span = b.mul(I['Tile Size'], I['Scale']) if tile else None
    edge = F.edge_mask(b, S, b.mul(0.03, inv))
    cav = F.cavity_mask(b, S, b.mul(inv, 0.3))
    has_geo = is_socket(edge)
    height_obj = b.separate(b.texcoord().outputs['Generated'])[2] if has_geo else None

    m = I['Mortar Width']
    half = b.mul(m, 0.5)
    W = b.add(I['Unit Width'], m)  # cells: a unit and one joint
    H = b.add(I['Unit Height'], m)
    irr = I['Irregularity']

    # ---- the plane of the layouts, with wavy rows for hand-laid walls
    warp = S.noise(b.div(0.35, W), 30, detail=2.0, roughness=0.5, label='Wobble').node.outputs['Color']
    wr, wg, _wb = b.separate_color(warp)
    if tile:
        wob = b.div(b.mul(irr, 0.25), span)
        u = b.madd(b.sub(wr, 0.5), b.mul(wob, W), S.u)
        v = b.madd(b.sub(wg, 0.5), b.mul(wob, H), S.v)
        s0 = t0 = None
    else:
        s0, t0 = F.box_coords(b, S)
        s0 = b.madd(b.sub(wr, 0.5), b.mul(b.mul(irr, 0.25), W), s0)
        t0 = b.madd(b.sub(wg, 0.5), b.mul(b.mul(irr, 0.25), H), t0)

    def grid(cell_w, cell_h, mult_w=1.0, mult_h=1.0):
        """(s, t, nw, nh): pattern units in the plane; tiles: nw x nh cells (multiples of mult) across."""
        if not tile:
            return s0, t0, None, None
        nw = b.mul(b.maximum(1.0, b.math('ROUND', b.div(b.div(span, cell_w), mult_w))), mult_w)
        nh = b.mul(b.maximum(1.0, b.math('ROUND', b.div(b.div(span, cell_h), mult_h))), mult_h)
        return b.mul(u, b.mul(nw, cell_w)), b.mul(v, b.mul(nh, cell_h)), nw, nh

    def wrapped(i, n):  # unit numbers repeat with the tile: the same unit on both sides of a seam
        return b.wrap(i, n) if tile else i

    def tri(f):  # distance to the nearest whole number (f: the fractional part)
        return b.sub(0.5, b.absolute(b.sub(f, 0.5)))

    # Every layout gives: distances to the unit's sides (dx) and to its top and bottom (dy),
    # a number for the unit (vector), its half size and whether it is a header (brick end).
    def running():
        s, t, nw, nh = grid(W, H)
        y = b.div(t, H)
        row = wrapped(b.floor(y), nh)
        offset = I['Row Offset']
        if tile:  # a whole number of shifts up the tile
            offset = b.div(b.math('ROUND', b.mul(offset, nh)), nh)
        r_row, _c = b.white_noise(b.combine(row, I['Seed'], 0.13))
        x = b.add(b.div(s, W), b.madd(r_row, I['Random Offset'], b.mul(row, offset)))
        col = wrapped(b.floor(x), nw)
        fx = b.fract(x)
        r_split, split_col = b.white_noise(b.combine(col, row, b.add(I['Seed'], 0.29)))
        split = b.math('LESS_THAN', r_split, b.mul(I['Length Variation'], 0.8))
        at = b.madd(b.separate_color(split_col)[0], 0.5, 0.25)  # where the unit is split
        right = b.mul(split, b.math('GREATER_THAN', fx, at))
        lo = b.mul(right, at)
        hi = b.one_minus(b.mul(b.mul(split, b.one_minus(right)), b.one_minus(at)))
        dx = b.mul(b.minimum(b.sub(fx, lo), b.sub(hi, fx)), W)
        dy = b.mul(tri(b.fract(y)), H)
        hs = b.mul(b.minimum(b.mul(b.sub(hi, lo), W), H), 0.5)
        return dx, dy, b.combine(b.madd(right, 0.5, col), row, 0.0), hs, 0.0

    def english():
        s, t, nw, nh = grid(W, H, 1.0, 2.0)
        y = b.div(t, H)
        row = wrapped(b.floor(y), nh)
        hdr = b.wrap(row, 2.0)  # odd rows: brick ends (headers)
        cell = b.mul(W, b.madd(hdr, -0.5, 1.0))
        x = b.madd(hdr, 0.5, b.div(s, cell))
        col = wrapped(b.floor(x), b.mul(nw, b.add(hdr, 1.0)) if tile else None)
        dx = b.mul(tri(b.fract(x)), cell)
        dy = b.mul(tri(b.fract(y)), H)
        return dx, dy, b.combine(col, row, 2.0), b.mul(b.minimum(cell, H), 0.5), hdr

    def flemish():
        period = b.mul(W, 1.5)  # a long side and an end
        s, t, nw, nh = grid(period, H, 1.0, 2.0)
        y = b.div(t, H)
        row = wrapped(b.floor(y), nh)
        q = b.madd(b.wrap(row, 2.0), 0.5, b.div(s, period))  # ends centered over the long sides below
        k = wrapped(b.floor(q), nw)
        f = b.mul(b.fract(q), 1.5)
        hdr = b.math('GREATER_THAN', f, 1.0)
        hi = b.madd(hdr, 0.5, 1.0)
        dx = b.mul(b.minimum(b.sub(f, hdr), b.sub(hi, f)), W)
        dy = b.mul(tri(b.fract(y)), H)
        hs = b.mul(b.minimum(b.mul(W, b.madd(hdr, -0.5, 1.0)), H), 0.5)
        return dx, dy, b.combine(b.madd(k, 2.0, hdr), row, 3.0), hs, hdr

    pavers = b.maximum(2.0, b.math('ROUND', b.div(W, H)))  # paver length in paver widths

    def herringbone():
        k = pavers
        s, t, nw, nh = grid(H, H, b.mul(k, 2.0), b.mul(k, 2.0))
        x, y = b.div(s, H), b.div(t, H)
        a, c = b.floor(x), b.floor(y)
        tt = b.wrap(b.sub(a, c), b.mul(k, 2.0))
        hz = b.math('LESS_THAN', tt, k)  # lying pavers: [a - tt, a - tt + k) x [c, c + 1)
        hx = b.add(b.sub(x, a), tt)
        bottom = b.sub(c, b.sub(b.madd(k, 2.0, -1.0), tt))  # standing ones: [a, a + 1) x [bottom, bottom + k)
        vy = b.sub(y, bottom)
        dx = b.mul(b.mix(hz, tri(b.fract(x)), b.minimum(hx, b.sub(k, hx))), H)
        dy = b.mul(b.mix(hz, b.minimum(vy, b.sub(k, vy)), tri(b.fract(y))), H)
        idx = wrapped(b.mix(hz, a, b.sub(a, tt)), nw)
        idy = wrapped(b.mix(hz, bottom, c), nh)
        return dx, dy, b.combine(idx, idy, b.add(hz, 4.0)), b.mul(H, 0.5), 0.0

    def basketweave():
        k = pavers
        s, t, nw, nh = grid(H, H, b.mul(k, 2.0), b.mul(k, 2.0))
        x, y = b.div(s, H), b.div(t, H)
        bi, bj = b.floor(b.div(x, k)), b.floor(b.div(y, k))
        hz = b.math('LESS_THAN', b.wrap(b.add(bi, bj), 2.0), 0.5)  # squares of k pavers, turned every other
        lx, ly = b.sub(x, b.mul(bi, k)), b.sub(y, b.mul(bj, k))
        dx = b.mul(b.mix(hz, tri(b.fract(x)), b.minimum(lx, b.sub(k, lx))), H)
        dy = b.mul(b.mix(hz, b.minimum(ly, b.sub(k, ly)), tri(b.fract(y))), H)
        idx = wrapped(b.madd(bi, k, b.mul(b.one_minus(hz), b.floor(lx))), nw)
        idy = wrapped(b.madd(bj, k, b.mul(hz, b.floor(ly))), nh)
        return dx, dy, b.combine(idx, idy, b.add(hz, 6.0)), b.mul(H, 0.5), 0.0

    def stones():
        freq = b.div(1.0, W)
        ratio = b.clamp(b.div(I['Unit Width'], I['Unit Height']), 0.25, 4.0)
        bend = S.noise(b.mul(freq, 1.3), 31, detail=2.0, roughness=0.5, label='Stone Shapes').node.outputs['Color']
        br, bg, bb = b.separate_color(bend)
        amount = b.madd(irr, 0.6, 0.08)
        if tile:
            shift = b.div(b.mul(amount, W), span)
            space = S.warped((b.mul(b.sub(br, 0.5), shift), b.mul(b.sub(bg, 0.5), shift)))
            aniso, base = (1.0, ratio), None
        else:
            space = S
            bent = b.vadd(S.P, b.vscale(b.combine(b.sub(br, 0.5), b.sub(bg, 0.5), b.sub(bb, 0.5)), b.mul(amount, W)))
            aniso, base = None, b.vmath('MULTIPLY', bent, b.combine(1.0, 1.0, ratio))  # flatter stones in walls
        cells = space.voronoi(freq, 32, aniso=aniso, base=base, label='Stones')
        sides = space.voronoi(freq, 32, feature='DISTANCE_TO_EDGE', aniso=aniso, base=base, label='Stone Joints')
        d = b.div(sides.outputs['Distance'], freq)
        return d, d, cells.outputs['Color'], b.mul(W, 0.4), 0.0

    def hexagons():
        s, t, nw, nh = grid(W, b.mul(W, SQRT3))
        x, y = b.div(s, W), b.div(t, W)
        ax, ay = b.sub(b.wrap(x, 1.0), 0.5), b.sub(b.wrap(y, SQRT3), SQRT3 / 2.0)
        bx = b.sub(b.wrap(b.sub(x, 0.5), 1.0), 0.5)
        by = b.sub(b.wrap(b.sub(y, SQRT3 / 2.0), SQRT3), SQRT3 / 2.0)
        other = b.math('LESS_THAN', b.madd(bx, bx, b.mul(by, by)), b.madd(ax, ax, b.mul(ay, ay)))
        gx, gy = b.mix(other, ax, bx), b.mix(other, ay, by)  # from the nearest center
        hd = b.maximum(b.absolute(gx), b.madd(b.absolute(gx), 0.5, b.mul(b.absolute(gy), SQRT3 / 2.0)))
        d = b.mul(b.sub(0.5, hd), W)
        idx = wrapped(b.math('ROUND', b.mul(b.sub(x, gx), 2.0)), b.mul(nw, 2.0) if tile else None)
        idy = wrapped(b.math('ROUND', b.mul(b.sub(y, gy), 2.0 / SQRT3)), b.mul(nh, 2.0) if tile else None)
        return d, d, b.combine(idx, idy, 8.0), b.mul(W, 0.5), 0.0

    # one layout after the other, each picked where 'Layout' says (keeps few values alive at once)
    dx, dy, unit_id, hs, hdr = running()
    for index, layout in enumerate((english, flemish, herringbone, basketweave, stones, hexagons), 1):
        pick = b.math('COMPARE', I['Layout'], float(index), 0.5)
        ldx, ldy, lid, lhs, lhdr = layout()
        dx, dy = b.mix(pick, dx, ldx), b.mix(pick, dy, ldy)
        unit_id = b.mix_vector(pick, unit_id, lid)
        hs = b.mix(pick, hs, lhs)
        hdr = b.mix(pick, hdr, lhdr) if is_socket(lhdr) or is_socket(hdr) else hdr

    # ---- random values of each unit
    r1, rc1 = b.white_noise(b.vadd(unit_id, b.combine(I['Seed'], 0.37, 0.61)))
    r2, r3, r4 = b.separate_color(rc1)
    r5, rc2 = b.white_noise(b.vadd(unit_id, b.combine(b.add(I['Seed'], 0.53), 0.11, 0.83)))
    r6, r7, _r8 = b.separate_color(rc2)
    jitter = b.mul(r1, 53.7)  # every unit gets its own part of the noise

    # ---- shape: joints, rounded and chipped edges, domes, rough faces
    d = b.minimum(dx, dy)
    fine = S.noise(b.div(1.0, b.maximum(b.mul(m, 4.0), b.mul(W, 0.04))), 33, detail=3.0, roughness=0.6,
                   label='Joint Edges')
    jag = b.madd(b.mul(irr, hs), 0.3, b.mul(m, 0.5))  # how ragged the joints are
    fd = b.sub(b.madd(b.sub(fine, 0.5), jag, d), half)  # depth into the unit's face
    corner = b.one_minus(b.smoothstep(0.0, b.mul(hs, 0.9), b.sub(b.add(dx, dy), m)))
    weathering = I['Weathering']
    chip_z = S.znoise(b.div(3.0, H), 34, detail=4.0, roughness=0.65, jitter=jitter, label='Chips')
    chip_w = b.mul(b.mul(b.add(I['Chipped Edges'], b.mul(weathering, 0.3)), hs),
                   b.madd(corner, 0.9, b.madd(edge, 0.8, 0.25)) if has_geo else b.madd(corner, 0.9, 0.25))
    chip_reach = b.maximum(b.mul(chip_w, b.clamp01(b.madd(chip_z, 0.35, 0.5))), 0.00001)
    chip = b.mul(b.one_minus(b.smoothstep(0.0, chip_reach, fd)),
                 b.clamp01(b.mul(I['Chipped Edges'], 30.0)))
    round_w = b.madd(b.mul(b.add(I['Edge Rounding'], b.mul(weathering, 0.5)), hs), 0.5, b.mul(m, 0.05))
    prof = b.clamp01(b.div(fd, b.maximum(round_w, 0.0002)))
    prof = b.one_minus(b.mul(b.one_minus(prof), b.one_minus(prof)))  # quarter-round edges
    dome = b.clamp01(b.div(fd, b.maximum(b.sub(hs, half), 0.001)))
    dome = b.one_minus(b.mul(b.one_minus(dome), b.one_minus(dome)))

    face_level = 0.6
    split_z = S.znoise(b.div(2.5, H), 35, detail=6.0, roughness=0.7, jitter=jitter, label='Split Face')
    h_face = b.madd(b.sub(dome, 1.0), b.mul(I['Bulge'], 0.3), face_level)
    h_face = b.madd(I['Split Face'], b.madd(split_z, 0.06, 0.05), h_face)
    # mortar: flush to raked, sandy, crumbling
    mz = S.znoise(b.div(1.0, b.maximum(m, 0.002)), 37, detail=4.0, roughness=0.6, label='Mortar')
    erosion = I['Mortar Erosion']
    h_mortar = b.sub(face_level - 0.04, b.mul(I['Mortar Depth'], 0.35))
    h_mortar = b.madd(mz, b.madd(I['Mortar Texture'], 0.02, b.mul(erosion, 0.05)),
                      b.madd(erosion, -0.15, h_mortar))

    broken_z = S.znoise(b.div(1.5, H), 36, detail=5.0, roughness=0.7, jitter=jitter, label='Broken Face')
    broken = b.mul(b.math('LESS_THAN', r5, I['Broken Units']), b.smoothstep(-0.8, 0.2, broken_z))
    broken = b.maximum(broken, chip)
    # (broken faces stay just above the mortar, so they still show the unit)
    h_face = b.mix(broken, h_face, b.maximum(b.madd(broken_z, 0.05, face_level - 0.18), b.add(h_mortar, 0.02)))
    h_unit = b.mix(prof, b.sub(h_mortar, 0.2), h_face)
    h = b.maximum(h_mortar, h_unit)
    unit = b.smoothstep(-0.006, 0.006, b.sub(h_unit, h_mortar))  # 1 on the units, 0 on the mortar

    missing = b.mul(b.math('LESS_THAN', r6, I['Missing Units']), b.smoothstep(0.0, b.mul(m, 0.3), fd))
    h = b.mix(missing, h, b.madd(mz, 0.03, 0.1))

    # ---- color of the units
    col = b.mix_color(b.mul(r2, I['Color Variation']), I['Unit Color'], I['Unit Color 2'])
    col = b.color_scale(col, b.madd(b.sub(r3, 0.5), b.mul(I['Brightness Variation'], 0.9), 1.0))
    dark = b.maximum(b.math('LESS_THAN', r4, I['Dark Units']), b.mul(hdr, I['Dark Headers']))
    col = b.color_scale(col, b.madd(dark, -0.62, 1.0))
    wall = S.znoise(b.div(0.12, W), 38, detail=3.0, roughness=0.6, label='Wall Variation')
    mottle = S.znoise(b.div(2.0, W), 39, detail=4.0, roughness=0.6, jitter=jitter, label='Mottling')
    col = b.color_scale(col, b.madd(mottle, b.mul(I['Mottling'], 0.12), b.madd(wall, 0.05, 1.0)))
    rough = b.madd(mottle, 0.03, I['Roughness'])

    sand = S.noise(300.0, 40, detail=2.0, roughness=0.5, label='Sand')
    face_tex = I['Face Texture']
    col = b.color_scale(col, b.madd(b.sub(sand, 0.5), b.mul(face_tex, 0.5), 1.0))
    hm = b.mul(b.sub(sand, 0.5), b.madd(face_tex, 1.0, b.mul(weathering, 0.8)))

    speck = b.smoothstep(1.7, 2.3, S.znoise(110.0, 41, detail=2.0, roughness=0.5, label='Specks'))
    col = b.mix_color(b.mul(speck, b.mul(I['Speckles'], 0.85)), col, b.color_scale(col, 0.18))

    pores = S.voronoi(220.0, 42, label='Pores')
    pr, pg, _pb = b.separate_color(pores.outputs['Color'])
    hole = b.one_minus(b.smoothstep(b.madd(pg, 0.1, 0.08), b.madd(pg, 0.15, 0.24), pores.outputs['Distance']))
    hole = b.mul(hole, b.math('LESS_THAN', pr, b.mul(b.add(I['Pores'], b.mul(weathering, 0.3)), 0.5)))
    col = b.color_scale(col, b.madd(hole, -0.5, 1.0))
    hm = b.madd(hole, -2.5, hm)

    # stone faces: marble veins, sediment layers, granite grains
    veins_n = S.noise(b.div(1.2, W), 43, detail=6.0, roughness=0.6, distortion=1.5, jitter=jitter, label='Veins')
    vein = b.one_minus(b.smoothstep(0.0, 0.025, b.absolute(b.sub(veins_n, 0.5))))
    halo = b.one_minus(b.smoothstep(0.0, 0.12, b.absolute(b.sub(veins_n, 0.5))))
    col = b.mix_color(b.mul(b.madd(halo, 0.35, b.mul(vein, 0.65)), I['Veins']), col, I['Vein Color'])
    layer_aniso = (0.06, 1.0) if tile else (0.06, 0.06, 1.0)
    layers = S.znoise(b.div(0.6, H), 44, detail=5.0, roughness=0.7, aniso=layer_aniso, jitter=jitter,
                      label='Layers')
    col = b.mix_color(b.mul(b.smoothstep(-0.6, 0.9, layers), b.mul(I['Layers'], 0.7)), col,
                      b.color_scale(I['Unit Color 2'], b.madd(layers, 0.1, 1.0)))
    hm = b.madd(layers, b.mul(I['Layers'], 0.5), hm)
    grains = S.voronoi(400.0, 45, label='Crystals')
    gr, gg, _gb = b.separate_color(grains.outputs['Color'])
    crystals = I['Crystals']
    col = b.mix_color(b.mul(b.math('LESS_THAN', gr, 0.3), crystals), col,
                      b.color_scale(I['Crystal Color'], b.madd(gg, 0.6, 0.7)))
    col = b.mix_color(b.mul(b.math('GREATER_THAN', gr, 0.85), b.mul(crystals, 0.8)), col,
                      b.color_scale(b.gray(0.62), b.madd(gg, 0.3, 0.85)))

    glaze = I['Glaze']
    col = b.color_scale(col, b.madd(glaze, -0.08, 1.0))
    rough = b.mix(glaze, rough, b.madd(mottle, 0.01, 0.06))
    hm = b.mul(hm, b.madd(glaze, -0.85, 1.0))
    rough = b.madd(I['Split Face'], 0.06, rough)

    # broken faces, pitted by the weather
    col = b.mix_color(broken, col, b.color_scale(b.mix_color(0.5, col, BROKEN), b.madd(broken_z, 0.08, 1.05)))
    rough = b.mix(broken, rough, 0.95)
    pits = b.smoothstep(1.0, 2.2, S.znoise(60.0, 46, detail=2.0, roughness=0.5, label='Pits'))
    hm = b.madd(b.mul(pits, weathering), -1.5, hm)
    col = b.color_scale(col, b.madd(b.madd(pits, -0.4, 0.06), weathering, 1.0))

    # ---- mortar color, holes of missing units
    mortar_col = b.color_scale(I['Mortar Color'], b.madd(mz, b.madd(I['Mortar Texture'], 0.05, 0.02),
                                                          b.madd(wall, 0.03, b.madd(erosion, -0.2, 1.0))))
    col = b.mix_color(unit, mortar_col, col)
    rough = b.mix(unit, b.madd(mz, 0.02, 0.92), rough)
    col = b.mix_color(missing, col, b.mix_color(b.smoothstep(-1.0, 1.0, mz), HOLE, b.color_scale(mortar_col, 0.2)))
    rough = b.mix(missing, rough, 0.95)

    # cracks through the units
    crack_d = F.crack_distance(b, S, I['Crack Scale'], 47)
    crack_on = F.cover(b, S.znoise(b.mul(I['Crack Scale'], 0.6), 49, detail=3.0, roughness=0.6,
                                   label='Crack Patches'), b.mul(I['Cracks'], 0.8), 0.5)
    crack = b.mul(b.mul(b.one_minus(b.smoothstep(0.003, 0.014, crack_d)), crack_on), unit)
    crack_zone = b.mul(b.one_minus(b.smoothstep(0.01, 0.08, crack_d)), crack_on)
    col = b.color_scale(col, b.madd(crack, -0.7, 1.0))
    h = b.madd(crack, -0.2, h)

    # ---- coatings: paint (peeling at the edges first), limewash
    peel_z = S.znoise(b.div(0.8, W), 50, detail=5.0, roughness=0.65, label='Peeling')
    peel_where = b.madd(chip, 1.5, b.madd(edge, 1.5, peel_z) if has_geo else peel_z)
    peeled = F.cover(b, peel_where, I['Peeling'], 0.25)
    paint = b.mul(I['Paint'], b.one_minus(peeled))
    paint_col = b.color_scale(I['Paint Color'], b.madd(wall, 0.03, b.madd(mz, 0.01, 1.0)))
    col = b.mix_color(paint, col, paint_col)
    rough = b.mix(paint, rough, 0.6)
    hm = b.madd(b.mul(paint, hm), -0.6, hm)
    lip = b.mul(b.mul(I['Paint'], b.smoothstep(0.0, 0.25, peeled)), b.one_minus(b.smoothstep(0.25, 0.6, peeled)))
    h = b.madd(lip, 0.015, h)
    lime = b.mul(I['Limewash'], b.clamp01(b.madd(S.znoise(b.div(0.5, W), 51, detail=5.0, roughness=0.7,
                                                         label='Limewash'), 0.25, b.madd(unit, -0.25, 0.75))))
    col = b.mix_color(lime, col, b.color_scale(LIME, b.madd(sand, 0.1, 0.95)))
    rough = b.mix(lime, rough, 0.95)

    # ---- stains: color and gloss only
    streak_aniso = (1.0, 1.0 / 16.0) if tile else (1.0, 1.0, 1.0 / 16.0)
    stz = S.znoise(4.0, 52, detail=4.0, roughness=0.6, aniso=streak_aniso, label='Streaks')
    stz2 = S.znoise(2.5, 53, detail=4.0, roughness=0.6, aniso=streak_aniso, label='Streaks 2')
    streak_on = F.cover(b, S.znoise(0.8, 54, detail=2.0, label='Streak Areas'), 0.6, 0.8, gate=False)
    wet_low = b.one_minus(b.smoothstep(0.0, 0.25, b.madd(wall, 0.04, height_obj))) if has_geo else 0.3
    joints = b.one_minus(unit)

    water = b.maximum(b.mul(F.cover(b, stz2, b.mul(I['Water Stains'], 0.4), 0.6), streak_on),
                      b.mul(wet_low, b.mul(I['Water Stains'], 0.7)))
    col = b.color_scale(col, b.madd(water, -0.35, 1.0))
    rough = b.madd(water, -0.08, rough)

    eff = I['Efflorescence']
    salt = b.maximum(b.mul(joints, b.mul(eff, b.clamp01(b.madd(mz, 0.4, 0.7)))),
                     b.mul(F.cover(b, b.madd(stz, 0.7, stz2), b.mul(eff, 0.25), 0.6), streak_on))
    salt = b.maximum(salt, b.mul(crack_zone, eff))
    if has_geo:
        salt = b.maximum(salt, b.mul(b.mul(wet_low, eff), b.clamp01(b.madd(mottle, 0.3, 0.3))))
    salt = b.mul(salt, b.clamp01(b.madd(sand, 1.2, 0.2)))
    col = b.mix_color(b.mul(salt, 0.85), col, SALT)
    rough = b.mix(salt, rough, 0.95)

    dz = S.znoise(2.0, 55, detail=5.0, roughness=0.6, label='Dirt Patches')
    dirt = I['Dirt']
    grime = b.mul(F.cover(b, dz, b.mul(dirt, 0.35), 0.9), 0.5)
    grime = b.maximum(grime, b.mul(b.maximum(joints, b.mul(chip, 0.6)), b.mul(dirt, 0.75)))
    if has_geo:
        grime = b.maximum(grime, b.mul(b.smoothstep(0.1, 0.7, b.madd(mottle, 0.08, cav)), dirt))
        grime = b.maximum(grime, b.mul(b.one_minus(b.smoothstep(0.0, 0.18, b.madd(dz, 0.03, height_obj))),
                                       b.mul(dirt, 0.8)))
    grime = b.clamp01(grime)
    col = b.mix_color(grime, col, b.color_scale(I['Dirt Color'], b.madd(dz, 0.15, 1.0)))
    rough = b.mix(grime, rough, 0.9)

    moss = I['Moss']
    moss_z = S.znoise(4.0, 56, detail=6.0, roughness=0.65, label='Moss')
    moss_where = b.madd(moss_z, 0.8, b.mul(b.maximum(joints, b.maximum(crack_zone, chip)), 2.0))
    if has_geo:
        up = b.separate(b.geometry().outputs['Normal'])[2]
        moss_where = b.add(moss_where, b.madd(cav, 2.0, b.madd(up, 0.6, b.mul(wet_low, 1.2))))
    moss_mask = F.cover(b, moss_where, b.mul(moss, 0.4), 0.35)
    moss_col = b.mix_color(b.smoothstep(-1.0, 1.5, b.madd(sand, 2.0, moss_z)), MOSS, MOSS_LIGHT)
    col = b.mix_color(moss_mask, col, moss_col)
    rough = b.mix(moss_mask, rough, 0.92)
    hm = b.madd(moss_mask, b.madd(sand, 1.5, 0.5), hm)
    h = b.madd(moss_mask, b.mul(joints, 0.1), h)

    soot_where = b.madd(dz, 0.9, b.mul(b.one_minus(height_obj), 1.4)) if has_geo else dz
    soot = F.cover(b, b.madd(joints, 0.4, soot_where), b.mul(I['Soot'], 0.55), 0.9)
    col = b.mix_color(soot, col, b.color_scale(SOOT, b.madd(mottle, 0.3, 1.2)))
    rough = b.mix(soot, rough, 0.95)

    wet = I['Wetness']
    col = b.color_scale(col, b.madd(wet, -0.4, 1.0))
    rough = b.mix(wet, rough, b.madd(sand, 0.1, 0.12))

    C.finish(b, gout, I, col, 0.0, rough, b.clamp01(h), hm, distance=MASONRY_BUMP, displace=I['Real Displacement'])


SPEC = dict(
    label='Masonry', category='MASONRY', params=MASONRY_PARAMS, outputs=C.COMMON_OUTPUTS + C.DISPLACE_OUTPUTS,
    build=build_masonry, display=('Unit Color', 0.0, 'Roughness'), bump=MASONRY_BUMP, fit=0.3,
)
