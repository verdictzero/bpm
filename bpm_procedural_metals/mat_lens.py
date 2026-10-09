# SPDX-License-Identifier: GPL-3.0-or-later
"""Lens generator: camera lenses, coated optics, mirrored visors and reflectors.

These lenses are opaque: glossy, reflective surfaces that you cannot see
through (the dark inside of a camera lens is part of their color).  The colored
reflections of coated lenses come from the Principled BSDF's thin film, fed by
the Coating outputs; baking keeps the coating as a setting of the baked
material.
"""

from . import features as F
from . import gencommon as C

LENS_BUMP = 0.004  # relief depth of the full 0..1 height range (meters at Scale 1)
HEX = 1.7320508  # height of a row of hexagonal prisms (sqrt 3)

# coating thickness (nm) -> color of the reflections with the default coating IOR
COATINGS = (('None', 0.0), ('Amber', 250.0), ('Purple', 300.0), ('Blue', 350.0), ('Green', 400.0),
            ('Magenta', 500.0))

LENS_PARAMS = [
    # -- Lens
    C.color('Lens Color', (0.005, 0.006, 0.009), 'Lens',
            'Color deep inside the lens: almost black for camera lenses', key=True),
    C.fac('Roughness', 0.02, 'Lens', '0 = mirror-smooth, higher = blurry reflections', key=True),
    C.Param('IOR', 'FLOAT', 1.6, 1.0, 3.0, 'Lens',
            'Index of refraction: higher = brighter reflections (1.5 window glass, 1.6 to 1.9 lens glass)'),
    C.Param('Coating', 'FLOAT', 300.0, 0.0, 1500.0, 'Lens',
            'Coating thickness in nanometers: it colors the reflections (250 amber, 300 purple, 350 blue, '
            '400 green). 0 = no coating', ui=('CHOICES', COATINGS), key=True),
    C.Param('Coating IOR', 'FLOAT', 1.38, 1.0, 3.0, 'Lens',
            'Lower than the lens IOR: anti-reflection coating, dimmer reflections (camera lenses). '
            'Higher: brighter, more colorful reflections'),
    C.fac('Coating Variation', 0.25, 'Lens', 'Colors shifting across the lens'),
    C.fac('Mirror', 0.0, 'Lens', 'Mirror coating: 1 = metallic mirror (helmet visors, mirrored sunglasses)',
          key=True),
    C.color('Mirror Color', (0.9, 0.9, 0.9), 'Lens', 'Color of the mirror coating (gold for helmet visors...)'),
    C.fac('Depth', 0.3, 'Lens', 'Fake depth: a lighter rim and faint inner rings, like inside a camera lens'),
    C.axis('Lens Axis', (0.0, 0.0, 1.0), 'Lens', 'Axis the lens looks along (rings are centered on it)'),
    # -- Texture
    C.fac('Fresnel Rings', 0.0, 'Texture', 'Concentric ridges of a Fresnel lens (lighthouses, projectors, lamps)'),
    C.Param('Ring Spacing', 'FLOAT', 0.004, 0.0005, 0.1, 'Texture', 'Distance between the rings',
            subtype='DISTANCE'),
    C.fac('Prisms', 0.0, 'Texture', 'Hexagonal reflector prisms (tail lights, bike reflectors)'),
    C.Param('Prism Size', 'FLOAT', 0.005, 0.0005, 0.1, 'Texture', 'Size of the prisms', subtype='DISTANCE'),
    # -- Wear
    C.fac('Scratches', 0.03, 'Wear', 'Fine scratches', key=True),
    C.scale('Scratch Scale', 2.5, 0.05, 20.0, 'Wear', 'Scratch size (higher = smaller, denser)'),
    C.fac('Smudges', 0.05, 'Wear', 'Fingerprints and greasy smudges', key=True),
    C.fac('Dust', 0.0, 'Wear', 'Dust settled on top', key=True),
    C.color('Dust Color', (0.42, 0.40, 0.36), 'Wear', 'Color of the dust'),
    C.fac('Haze', 0.0, 'Wear', 'Milky haze of an old lens or a worn coating'),
    C.fac('Cracks', 0.0, 'Wear', 'Cracked lens'),
    C.scale('Crack Scale', 40.0, 1.0, 400.0, 'Wear', 'Size of the cracked pieces (higher = smaller)'),
] + C.PATTERN_PARAMS

LENS_OUTPUTS = C.COMMON_OUTPUTS + [('IOR', 'FLOAT'), ('Coating', 'FLOAT'), ('Coating IOR', 'FLOAT')]


def _hex_corners(b, s, t):
    """Hexagonal cube-corner prisms: 0 at the deep center of each prism, 1 at its outer corners.

    The prism centers form two rectangular lattices (1 x sqrt 3) shifted by half
    a cell; each prism has three flat facets at 120 degrees, like a real reflector.
    """
    def nearest(du, dv):
        x = b.sub(b.fract(b.add(s, du)), 0.5)
        y = b.mul(b.sub(b.fract(b.add(b.div(t, HEX), dv)), 0.5), HEX)
        return x, y, b.madd(x, x, b.mul(y, y))
    ax, ay, da = nearest(0.0, 0.0)
    bx, by, db = nearest(0.5, 0.5)
    pick_b = b.math('LESS_THAN', db, da)
    x, y = b.mix(pick_b, ax, bx), b.mix(pick_b, ay, by)
    f1 = b.madd(x, 0.8660254, b.mul(y, 0.5))
    f2 = b.madd(x, -0.8660254, b.mul(y, 0.5))
    h = b.maximum(b.maximum(f1, f2), b.mul(y, -1.0))
    return b.clamp01(b.div(h, 0.5773503))


def build_lens(b, I, gout, tile):
    S = F.Space(b, tile, I['Scale'], I['Seed'], I['Tile Size'] if tile else 1.0)
    span = b.mul(I['Tile Size'], I['Scale']) if tile else None

    # ---- where on the lens: distance from the axis (object mode)
    if tile:
        rn = 0.5
    else:
        axis = b.vmath('NORMALIZE', I['Lens Axis'])
        p = S.P
        radius = b.vmath('LENGTH', b.vmath('SUBTRACT', p, b.vscale(axis, b.vmath('DOT_PRODUCT', p, axis))))
        g = b.vmath('SUBTRACT', b.texcoord().outputs['Generated'], (0.5, 0.5, 0.5))
        g_off = b.vmath('SUBTRACT', g, b.vscale(axis, b.vmath('DOT_PRODUCT', g, axis)))
        rn = b.clamp01(b.mul(b.vmath('LENGTH', g_off), 2.0))  # 0 = center, 1 = rim of the object

    # ---- the lens: dark inside, a lighter rim and faint rings of the elements inside
    depth = I['Depth']
    if tile:
        inside = 0.0
    else:
        rim = b.smoothstep(0.6, 1.0, rn)
        ring = b.absolute(b.math('SINE', b.mul(rn, 22.0)))
        rings = b.mul(b.smoothstep(0.93, 1.0, ring), b.smoothstep(0.15, 0.4, rn))
        inside = b.mul(depth, b.madd(rings, 2.5, b.mul(rim, 5.0)))
    col = b.color_scale(I['Lens Color'], b.add(inside, 1.0))
    col = b.mix_color(I['Mirror'], col, I['Mirror Color'])
    metallic = I['Mirror']
    rough = I['Roughness']

    cvz = S.znoise(1.5, 3, detail=2.0, roughness=0.5, label='Coating Variation')
    spread = b.madd(cvz, 0.15, b.mul(b.sub(rn, 0.5), 0.5)) if not tile else b.mul(cvz, 0.2)
    coating = b.mul(I['Coating'], b.madd(spread, I['Coating Variation'], 1.0))

    # ---- Fresnel rings (tiles: straight ridges) and reflector prisms
    if tile:
        x = b.mul(S.u, b.maximum(1.0, b.math('ROUND', b.div(span, I['Ring Spacing']))))
    else:
        x = b.div(radius, I['Ring Spacing'])
    ridge = b.fract(x)
    ridge_depth = b.minimum(b.div(b.mul(I['Ring Spacing'], 0.35), LENS_BUMP), 0.9)
    if tile:
        nx = b.maximum(1.0, b.math('ROUND', b.div(span, I['Prism Size'])))
        ny = b.maximum(1.0, b.math('ROUND', b.div(span, b.mul(I['Prism Size'], HEX))))
        ps, pt = b.mul(S.u, nx), b.mul(b.mul(S.v, ny), HEX)
    else:
        ps, pt = F.box_coords(b, S)
        ps, pt = b.div(ps, I['Prism Size']), b.div(pt, I['Prism Size'])
    prism = _hex_corners(b, ps, pt)
    prism_depth = b.minimum(b.div(b.mul(I['Prism Size'], 0.5), LENS_BUMP), 0.9)

    # ---- wear
    scr = F.scratch_mask(b, S, I['Scratches'], I['Scratch Scale'], 20)
    smz = S.znoise(5.0, 22, detail=4.0, roughness=0.6, label='Smudges')
    smear = b.mul(F.cover(b, smz, b.mul(I['Smudges'], 0.4), 0.5), 0.6)
    prints = S.voronoi(45.0, 23, label='Fingerprints')
    pr, _pg, _pb = b.separate_color(prints.outputs['Color'])
    pd = prints.outputs['Distance']
    whorl = b.madd(b.math('COSINE', b.mul(pd, 56.0)), 0.5, 0.5)
    finger = b.mul(b.one_minus(b.smoothstep(0.25, 0.45, pd)), b.math('LESS_THAN', pr, b.mul(I['Smudges'], 0.5)))
    grease = b.maximum(smear, b.mul(finger, b.madd(whorl, 0.6, 0.4)))

    if tile:
        crack_v = S.voronoi(I['Crack Scale'], 8, feature='DISTANCE_TO_EDGE', label='Cracks')
    else:  # bent a little, so the cracks don't look like straight polygon edges
        warp = S.noise(4.0, 7, detail=2.0, roughness=0.5, label='Crack Warp').node.outputs['Color']
        wr, wg, wb_ = b.separate_color(warp)
        bent = b.vadd(S.P, b.vscale(b.combine(b.sub(wr, 0.5), b.sub(wg, 0.5), b.sub(wb_, 0.5)),
                                    b.div(0.35, I['Crack Scale'])))
        crack_v = S.voronoi(I['Crack Scale'], 8, feature='DISTANCE_TO_EDGE', base=bent, label='Cracks')
    crack_on = F.cover(b, S.znoise(b.mul(I['Crack Scale'], 0.7), 9, detail=2.0, label='Crack Patches'),
                       b.mul(I['Cracks'], 0.9), 0.5)
    crack = b.mul(b.one_minus(b.smoothstep(0.003, 0.015, crack_v.outputs['Distance'])), crack_on)

    haze = I['Haze']
    hz = S.znoise(3.0, 24, detail=3.0, roughness=0.5, label='Haze')
    haze = b.clamp01(b.mul(haze, b.madd(hz, 0.2, 1.0)))
    col = b.mix_color(b.mul(haze, 0.35), col, (0.45, 0.45, 0.44))
    rough = b.madd(haze, 0.3, rough)
    coating = b.mul(coating, b.one_minus(b.mul(haze, 0.6)))

    white = b.maximum(b.mul(scr, 0.5), b.mul(crack, 0.8))
    col = b.mix_color(white, col, (0.75, 0.76, 0.76))
    metallic = b.mul(metallic, b.one_minus(white))
    rough = b.mix(b.maximum(b.mul(scr, 0.8), crack), rough, 0.35)
    rough = b.mix(b.mul(grease, 0.9), rough, 0.35)
    coating = b.mul(coating, b.one_minus(b.mul(grease, 0.5)))

    # dust settles on surfaces that face up
    if tile:
        facing = 1.0
    else:
        facing = b.madd(b.smoothstep(0.05, 0.9, b.separate(b.geometry().outputs['Normal'])[2]), 0.85, 0.15)
    clump = S.znoise(1.2, 42, detail=4.0, roughness=0.55, label='Dust Clumps')
    fluff = S.znoise(14.0, 41, detail=3.0, roughness=0.6, label='Dust Fluff')
    dust = b.clamp01(b.mul(b.mul(I['Dust'], facing), b.madd(clump, 0.25, b.madd(fluff, 0.1, 1.15))))
    col = b.mix_color(dust, col, I['Dust Color'])
    rough = b.mix(dust, rough, 0.95)
    metallic = b.mul(metallic, b.one_minus(dust))
    coating = b.mul(coating, b.one_minus(dust))

    # ---- relief
    h = b.madd(b.sub(ridge, 0.5), b.mul(I['Fresnel Rings'], ridge_depth), 0.5)
    h = b.madd(b.sub(prism, 0.5), b.mul(I['Prisms'], prism_depth), h)
    h = b.madd(crack, -0.1, h)
    h_micro = b.madd(scr, -0.4, b.madd(dust, 0.15, b.mul(grease, 0.05)))

    C.finish(b, gout, I, col, metallic, rough, b.clamp01(h), h_micro, distance=LENS_BUMP, extra={
        'IOR': I['IOR'],
        'Coating': coating,
        'Coating IOR': I['Coating IOR'],
    })


SPEC = dict(
    label='Lens', category='LENS', params=LENS_PARAMS, outputs=LENS_OUTPUTS, build=build_lens,
    links={'IOR': 'IOR', 'Coating': 'Thin Film Thickness', 'Coating IOR': 'Thin Film IOR'},
    display=('Lens Color', 'Mirror', 'Roughness'), fit=0.2, bump=LENS_BUMP,
)
