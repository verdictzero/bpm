# SPDX-License-Identifier: GPL-3.0-or-later
"""Woven fabric generator: canvas, denim, ballistic nylon, ripstop, satin...
and resin composites like carbon fiber and kevlar.

The weave is computed thread by thread: every cell of the thread grid knows
whether the lengthwise (warp) or the crosswise (weft) thread lies on top, and
both threads get a rounded profile, fibers and their own small irregularities.

Without UVs the weave is projected along the dominant axis of each face
(perfect on boxy shapes; on round shapes it changes direction at 45 degrees).
"""

import math

from . import features as F
from . import gencommon as C

WEAVES = (('Plain', 0.0), ('Twill', 1.0), ('Denim', 2.0), ('Basket', 3.0), ('Satin', 4.0))
FABRIC_BUMP = 0.004  # relief depth of the full 0..1 height range

FABRIC_PARAMS = [
    # -- Fabric
    C.color('Warp Color', (0.30, 0.25, 0.17), 'Fabric', 'Color of the lengthwise threads', key=True),
    C.color('Weft Color', (0.27, 0.22, 0.15), 'Fabric', 'Color of the crosswise threads', key=True),
    C.fac('Roughness', 0.8, 'Fabric', 'Glossiness (0 = glossy, 1 = matte)', key=True),
    C.fac('Thread Variation', 0.3, 'Fabric', 'Uneven threads and slubs'),
    C.fac('Color Variation', 0.15, 'Fabric', 'Blotchy, uneven dye'),
    C.fac('Fuzz', 0.35, 'Fabric', 'Soft, fuzzy sheen of cloth (render only)'),
    # -- Weave
    C.Param('Weave', 'FLOAT', 0.0, 0.0, 4.0, 'Weave',
            'Weave pattern: 0 = plain, 1 = twill (carbon fiber), 2 = denim twill, 3 = basket '
            '(ballistic nylon), 4 = satin', ui=('ENUM', WEAVES), key=True),
    C.Param('Thread Size', 'FLOAT', 0.0015, 0.0001, 0.05, 'Weave', 'Width of one thread', subtype='DISTANCE'),
    C.fac('Thread Gap', 0.15, 'Weave', 'Open gaps between the threads'),
    C.fac('Yarn Twist', 0.5, 'Weave', 'Twisted yarn (cotton, wool) instead of straight fibers (carbon, nylon)'),
    C.fac('Weave Depth', 0.6, 'Weave', 'Bumpiness of the weave'),
    C.Param('Weave Angle', 'FLOAT', 0.0, -90.0, 90.0, 'Weave',
            'Rotation of the weave in degrees (seamless tiles always use 0)'),
    C.fac('Ripstop', 0.0, 'Weave', 'Grid of thicker reinforcing threads (ripstop nylon)'),
    C.scale('Ripstop Every', 8.0, 2.0, 50.0, 'Weave', 'One thick thread every this many threads'),
    # -- Composite
    C.fac('Resin', 0.0, 'Composite', 'Glossy resin coating: carbon fiber / kevlar composite parts', key=True),
    C.fac('Fiber Shine', 0.0, 'Composite', 'Directional shine of the fibers (carbon fiber shimmer)'),
    # -- Wear
    C.fac('Fading', 0.0, 'Wear', 'Washed-out color, strongest on raised threads (worn denim)'),
    C.fac('Pilling', 0.0, 'Wear', 'Small fuzz balls'),
    C.fac('Stains', 0.0, 'Wear', 'Dark stains'),
    C.fac('Dirt', 0.1, 'Wear', 'Grime in folds and corners (needs Cycles or baking)', key=True),
    C.color('Dirt Color', C.DIRT, 'Wear', 'Color of the grime'),
] + C.PATTERN_PARAMS

FABRIC_OUTPUTS = C.COMMON_OUTPUTS + [('Sheen', 'FLOAT'), ('Coat', 'FLOAT'), ('Anisotropic', 'FLOAT'),
                                     ('Tangent', 'VECTOR')]


def _weave_top(b, ci, ri, weave):
    """1 where the weft (crosswise thread) lies on top of the warp."""
    w = b.math('ROUND', weave)
    diag = b.wrap(b.add(ci, ri), 4.0)
    patterns = (
        b.wrap(b.add(ci, ri), 2.0),                                              # plain
        b.math('GREATER_THAN', diag, 1.5),                                       # 2/2 twill
        b.math('GREATER_THAN', diag, 2.5),                                       # 3/1 twill (denim)
        b.wrap(b.add(b.floor(b.mul(ci, 0.5)), b.floor(b.mul(ri, 0.5))), 2.0),    # 2x2 basket
        b.math('LESS_THAN', b.wrap(b.madd(ci, 2.0, ri), 5.0), 0.5),              # 5 harness satin
    )
    selected = [b.mul(pattern, b.math('COMPARE', w, float(k), 0.25)) for k, pattern in enumerate(patterns)]
    top = selected[0]
    for sel in selected[1:]:
        top = b.add(top, sel)
    return top


def build_fabric(b, I, gout, tile):
    S = F.Space(b, tile, I['Scale'], I['Seed'], I['Tile Size'] if tile else 1.0)
    inv = b.div(1.0, I['Scale'])
    cav = F.cavity_mask(b, S, b.mul(inv, 0.2))
    ts = I['Thread Size']
    every = b.maximum(2.0, b.math('ROUND', I['Ripstop Every']))
    rip_on = b.math('GREATER_THAN', I['Ripstop'], 0.001)
    geo = b.geometry()

    # ---- thread coordinates (in threads): s across the warp, t across the weft
    if tile:
        span = b.mul(I['Tile Size'], I['Scale'])
        repeat = b.mul(20.0, b.mix(rip_on, 1.0, every))  # whole weave + ripstop repeats per tile
        count = b.mul(b.maximum(1.0, b.math('ROUND', b.div(span, b.mul(ts, repeat)))), repeat)
        s, t = b.mul(S.u, count), b.mul(S.v, count)
        tangent_warp = tangent_weft = geo.outputs['Tangent']
    else:
        x, y, z = b.separate(S.P)
        ax, ay, az = b.separate(b.vmath('ABSOLUTE', b.texcoord().outputs['Normal']))
        isz = b.mul(b.math('GREATER_THAN', az, b.mul(ax, 0.999)), b.math('GREATER_THAN', az, b.mul(ay, 0.999)))
        isy = b.mul(b.one_minus(isz), b.math('GREATER_THAN', ay, b.mul(ax, 0.999)))
        isx = b.one_minus(b.add(isz, isy))
        s0 = b.add(b.mul(x, b.add(isz, isy)), b.mul(y, isx))
        t0 = b.add(b.mul(y, isz), b.mul(z, b.add(isy, isx)))
        angle = b.mul(I['Weave Angle'], math.pi / 180.0)
        ca, sa = b.math('COSINE', angle), b.math('SINE', angle)
        s = b.div(b.sub(b.mul(s0, ca), b.mul(t0, sa)), ts)
        t = b.div(b.madd(s0, sa, b.mul(t0, ca)), ts)
        s_dir = b.combine(b.add(isz, isy), isx, 0.0)
        t_dir = b.combine(0.0, isz, b.add(isy, isx))
        weft_dir = b.vmath('SUBTRACT', b.vscale(s_dir, ca), b.vscale(t_dir, sa))
        warp_dir = b.vadd(b.vscale(s_dir, sa), b.vscale(t_dir, ca))
        n = geo.outputs['Normal']
        tangent_warp = b.vmath('NORMALIZE', b.vmath('CROSS_PRODUCT', n, b.vector_transform(warp_dir)))
        tangent_weft = b.vmath('NORMALIZE', b.vmath('CROSS_PRODUCT', n, b.vector_transform(weft_dir)))
    ci, ri = b.floor(s), b.floor(t)
    if tile:
        ci, ri = b.wrap(ci, count), b.wrap(ri, count)
    fs, ft = b.fract(s), b.fract(t)

    top = _weave_top(b, ci, ri, I['Weave'])

    # ---- per-thread irregularities
    rc, _ = b.white_noise(b.combine(ci, 1.37, I['Seed']), label='Warp Threads')
    rr, _ = b.white_noise(b.combine(2.71, ri, I['Seed']), label='Weft Threads')
    tv = I['Thread Variation']
    width = b.one_minus(b.mul(I['Thread Gap'], 0.6))
    w_warp = b.mul(width, b.madd(b.sub(rc, 0.5), b.mul(tv, 0.25), 1.0))
    w_weft = b.mul(width, b.madd(b.sub(rr, 0.5), b.mul(tv, 0.25), 1.0))

    def profile(f, w):
        x = b.div(b.sub(b.mul(f, 2.0), 1.0), w)
        return b.math('SQRT', b.maximum(0.0, b.one_minus(b.mul(x, x))))

    hw = b.mul(profile(fs, w_warp), b.madd(b.math('SINE', b.mul(ft, math.pi)), 0.2, 0.8))
    hf = b.mul(profile(ft, w_weft), b.madd(b.math('SINE', b.mul(fs, math.pi)), 0.2, 0.8))
    # ripstop: thicker threads every few threads
    rip = b.mul(I['Ripstop'], rip_on)
    rip_c = b.mul(b.math('LESS_THAN', b.wrap(ci, every), 1.5), rip)  # doubled threads
    rip_r = b.mul(b.math('LESS_THAN', b.wrap(ri, every), 1.5), rip)
    hw = b.mul(hw, b.madd(rip_c, 0.35, b.madd(top, -0.7, 1.0)))
    hf = b.mul(hf, b.madd(rip_r, 0.35, b.madd(top, 0.7, 0.3)))
    weft_vis = b.math('GREATER_THAN', hf, hw)
    h = b.maximum(hw, hf)
    rip_vis = b.mix(weft_vis, rip_c, rip_r)  # a thick thread is the visible one

    # fibers: straight along the thread, tilted when the yarn is twisted
    twist = I['Yarn Twist']
    lines = b.mix(twist, 7.0, 3.0)
    tilt = b.mul(twist, 2.5)
    stri_w = b.madd(b.math('SINE', b.mul(b.madd(fs, lines, b.mul(ft, tilt)), 2.0 * math.pi)), 0.5, 0.5)
    stri_f = b.madd(b.math('SINE', b.mul(b.madd(ft, lines, b.mul(fs, tilt)), 2.0 * math.pi)), 0.5, 0.5)
    stri = b.mix(weft_vis, stri_w, stri_f)

    # ---- color
    col_w = b.color_scale(I['Warp Color'], b.madd(b.sub(rc, 0.5), b.mul(tv, 0.35), 1.0))
    col_f = b.color_scale(I['Weft Color'], b.madd(b.sub(rr, 0.5), b.mul(tv, 0.35), 1.0))
    # fiber shine: threads lying in different directions catch the light differently
    shine = I['Fiber Shine']
    col_f = b.color_scale(col_f, b.madd(shine, 0.7, 1.0))
    col = b.mix_color(weft_vis, col_w, col_f)
    col = b.color_scale(col, b.madd(rip_vis, 0.4, 1.0))
    shade = b.madd(b.smoothstep(0.0, 0.6, h), 0.65, 0.35)  # gaps and thread edges are darker
    col = b.color_scale(col, b.mul(shade, b.madd(stri, 0.12, 0.94)))
    zc = S.znoise(2.5, 1, detail=4.0, roughness=0.55, label='Dye Variation')
    col = b.color_scale(col, b.madd(zc, b.mul(I['Color Variation'], 0.1), 1.0))
    rough = b.madd(stri, 0.05, b.madd(b.sub(weft_vis, 0.5), b.mul(shine, 0.25), I['Roughness']))

    # ---- wear
    fz = S.znoise(1.8, 2, detail=4.0, roughness=0.6, label='Fading')
    fade = b.clamp01(b.mul(I['Fading'], b.madd(fz, 0.3, b.madd(h, 0.6, 0.5))))
    col = b.mix_color(fade, col, b.hsv(col, saturation=0.55, value=2.2))
    pz = S.znoise(b.div(0.25, ts), 3, detail=1.0, label='Pilling')
    pill = b.mul(b.smoothstep(2.0, 2.6, pz), I['Pilling'])
    col = b.mix_color(b.mul(pill, 0.6), col, b.hsv(col, saturation=0.7, value=1.4))
    sz = S.znoise(2.0, 4, detail=5.0, roughness=0.6, label='Stains')
    stain = F.cover(b, sz, b.mul(I['Stains'], 0.4), 0.35)
    col = b.color_scale(col, b.madd(stain, -0.45, 1.0))
    rough = b.madd(stain, -0.1, rough)

    # ---- resin composites (carbon fiber, kevlar)
    resin = I['Resin']
    rough = b.mix(resin, rough, b.madd(stri, 0.06, 0.28))
    col = b.color_scale(col, b.madd(resin, -0.15, 1.0))
    dirt = C.dirt_mask(b, S, I['Dirt'], cav, 0.0, 30, spots=0.25)
    col = b.mix_color(dirt, col, I['Dirt Color'])
    rough = b.mix(dirt, rough, 0.9)

    # ---- relief (resin is smooth on the outside)
    relief = b.mul(b.mul(I['Weave Depth'], b.madd(resin, -0.85, 1.0)), b.div(b.mul(ts, 0.35), FABRIC_BUMP))
    h_macro = b.madd(b.sub(h, 0.5), relief, b.madd(rip_vis, 0.12, 0.5))
    h_micro = b.mul(b.mul(b.sub(stri, 0.5), 0.3), b.mul(I['Weave Depth'], b.madd(resin, -0.85, 1.0)))
    h_micro = b.madd(pill, 0.4, h_micro)

    tangent = b.mix_vector(weft_vis, tangent_warp, tangent_weft) if not tile else tangent_warp
    C.finish(b, gout, I, col, 0.0, rough, h_macro, h_micro, distance=FABRIC_BUMP, extra={
        'Sheen': b.mul(I['Fuzz'], b.one_minus(resin)),
        'Coat': resin,
        'Anisotropic': b.mul(I['Fiber Shine'], 0.9),
        'Tangent': tangent,
    })


SPEC = dict(
    label='Fabric', category='FABRIC', params=FABRIC_PARAMS, outputs=FABRIC_OUTPUTS, build=build_fabric,
    links={'Sheen': 'Sheen Weight', 'Coat': 'Coat Weight', 'Anisotropic': 'Anisotropic', 'Tangent': 'Tangent',
           'Base Color': 'Sheen Tint'},  # cloth sheen takes the color of the fibers
    bsdf={'Coat Roughness': 0.02, 'Sheen Roughness': 0.35},
    display=('Warp Color', 0.0, 'Roughness'), fit=0.3, bump=FABRIC_BUMP,
)
