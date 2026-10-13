# SPDX-License-Identifier: GPL-3.0-or-later
"""Gradient generator: linear, mirrored, radial, spherical, angular (conic), diamond,
square, cube, spiral, slope and facing gradients with up to five color stops.

Every gradient is computed in a 2D plane seen from the 'View Axis' (Front, Top,
Side or any direction) on the chosen projection: the object's bounding box,
object or world space, the UV map or the screen.  The plane's horizontal and
vertical directions are those of the matching Blender view (Front: X right,
Z up), so 'Angle' 90 degrees always means "bottom to top".

All choices (type, projection, repeat mode...) are number inputs of the node
group, so they can be changed live; the BPM panel shows them as buttons.
"""

import math

from . import gencommon as C

TYPES = (('Linear', 0), ('Mirrored', 1), ('Radial', 2), ('Spherical', 3), ('Angular', 4), ('Diamond', 5),
         ('Square', 6), ('Cube', 7), ('Spiral', 8), ('Slope', 9), ('Facing', 10))
PROJECTIONS = (('Bounds', 0), ('Object', 1), ('World', 2), ('UV', 3), ('Screen', 4))
REPEAT_MODES = (('Clamp', 0), ('Repeat', 1), ('Ping-Pong', 2))
INTERPOLATIONS = (('Linear', 0), ('Smooth', 1), ('Constant', 2))
STOP_COUNTS = (('2', 2), ('3', 3), ('4', 4), ('5', 5))
SPACINGS = (('Even', 0), ('Custom', 1))
MIXINGS = (('Perceptual', 0), ('Linear Light', 1))
ON_OFF = (('Normal', 0), ('Reversed', 1))
VIEWS = (('Front', (0.0, -1.0, 0.0)), ('Top', (0.0, 0.0, 1.0)), ('Side', (1.0, 0.0, 0.0)))

STOPS = 5
STOP_COLORS = ((0.02, 0.03, 0.10), (0.10, 0.25, 0.60), (0.60, 0.60, 0.65), (0.95, 0.55, 0.15), (1.0, 0.95, 0.80))


def _enum(name, default, items, panel, desc, key=False):
    return C.Param(name, 'FLOAT', float(default), float(items[0][1]), float(items[-1][1]), panel, desc,
                   ui=('ENUM', items), key=key)


GRADIENT_PARAMS = [
    # -- Gradient
    _enum('Type', 0, TYPES, 'Gradient',
          'Shape of the gradient. Linear: straight. Mirrored: from the middle out to both sides. Radial: '
          'circles. Spherical: balls in 3D. Angular: sweeps around the center. Diamond / Square: '
          'from the center out. Cube: boxes in 3D. Spiral. Slope: by how much the surface faces the view '
          'axis (tops vs. sides). Facing: by how much the surface faces the camera (edges vs. middle)',
          key=True),
    _enum('Projection', 0, PROJECTIONS, 'Gradient',
          'What the gradient is laid onto. Bounds: across the object\'s box (-1 to 1 on every axis). '
          'Object / World: in meters around the origin. UV: across the UV map. Screen: across the '
          'camera view. (Seamless tiles always use the tile)', key=True),
    C.Param('View Axis', 'VECTOR', (0.0, -1.0, 0.0), -1.0, 1.0, 'Gradient',
            'Direction the gradient is projected from (Front, Top, Side or any). UV and Screen always '
            'use their own plane', ui=('VIEW', VIEWS)),
    C.Param('Angle', 'FLOAT', math.radians(90.0), -2.0 * math.pi, 2.0 * math.pi, 'Gradient',
            'Direction of the gradient in the view: 0 = left to right, 90 = bottom to top', subtype='ANGLE',
            key=True),
    C.Param('Center', 'VECTOR', (0.0, 0.0, 0.0), -100.0, 100.0, 'Gradient',
            'Where the gradient is centered (Bounds, UV, Screen: -1 to 1; Object, World: meters)'),
    C.scale('Size', 1.0, 0.001, 1000.0, 'Gradient',
            'Distance from the center to the end of the gradient (Bounds: 1 = to the edge of the object)',
            key=True),
    C.scale('Aspect', 1.0, 0.05, 20.0, 'Gradient', 'Stretches the shape up and down (ellipses, rectangles)'),
    _enum('Reverse', 0, ON_OFF, 'Gradient', 'Runs the colors the other way'),
    # -- Colors
    _enum('Color Stops', 3, STOP_COUNTS, 'Colors', 'How many colors the gradient runs through', key=True),
] + [C.color('Color %d' % (i + 1), STOP_COLORS[i], 'Colors', 'Color stop %d' % (i + 1), key=i < 3)
     for i in range(STOPS)] + [
    _enum('Interpolation', 0, INTERPOLATIONS, 'Colors',
          'How the colors blend: Linear, Smooth (eased) or Constant (hard bands)'),
    _enum('Color Mixing', 0, MIXINGS, 'Colors',
          'Perceptual: colors blend evenly to the eye, like in paint and design apps. Linear Light: '
          'physically mixed light, like Blender\'s Color Ramp (the bright colors take up more room)'),
    _enum('Spacing', 0, SPACINGS, 'Colors',
          'Even: the colors are spread evenly. Custom: each color sits at its Position'),
] + [C.fac('Position %d' % (i + 1), i / (STOPS - 1), 'Colors', 'Position of color %d (Spacing: Custom)' % (i + 1))
     for i in range(STOPS)] + [
    # -- Shape
    C.scale('Shift', 0.0, -1.0, 1.0, 'Shape', 'Slides the gradient along'),
    C.scale('Bias', 0.0, -1.0, 1.0, 'Shape', 'Moves the middle of the gradient toward the start (-) or end (+)'),
    C.scale('Repeat', 1.0, 0.1, 100.0, 'Shape', 'How many times the gradient repeats (bands, rings, rays)',
            key=True),
    _enum('Repeat Mode', 0, REPEAT_MODES, 'Shape',
          'Clamp: past the end the last color stays. Repeat: starts over (sharp steps). '
          'Ping-Pong: runs back and forth (soft bands)', key=True),
    C.scale('Steps', 0.0, 0.0, 64.0, 'Shape', 'Splits the gradient into this many flat bands (0 = smooth)'),
    C.fac('Noise', 0.0, 'Shape', 'Wobbles the gradient with noise (natural, hand-made look)'),
    C.Param('Noise Size', 'FLOAT', 0.3, 0.001, 100.0, 'Shape', 'Size of the wobbles (same units as Center)'),
    # -- Surface
    C.fac('Metallic', 0.0, 'Surface', '0 = paint / plastic, 1 = metal (at the start of the gradient)'),
    C.fac('Metallic End', 0.0, 'Surface', 'Metallic at the end of the gradient'),
    C.fac('Roughness', 0.45, 'Surface', '0 = glossy, 1 = matte (at the start of the gradient)'),
    C.fac('Roughness End', 0.45, 'Surface', 'Roughness at the end of the gradient'),
    C.fac('Relief', 0.0, 'Surface', 'Raises the surface along the gradient (bump)'),
    C.fac('Glow', 0.0, 'Surface', 'Makes the colors glow (neon, skies, light panels)'),
    C.Param('Emission Strength', 'FLOAT', 1.0, 0.0, 200.0, 'Surface', 'Brightness of the glow'),
] + C.PATTERN_PARAMS

GRADIENT_OUTPUTS = C.COMMON_OUTPUTS + C.EMISSION_OUTPUTS + [('Factor', 'FLOAT')]


def _is(b, selector, value):
    """1 where the (rounded) choice `selector` equals `value`, else 0."""
    return b.math('COMPARE', selector, float(value), 0.5)


def _choose(b, selector, options):
    """options: {value: socket or constant}; the first one is the fallback."""
    items = list(options.items())
    result = items[0][1]
    for value, option in items[1:]:
        result = b.mix(_is(b, selector, value), result, option)
    return result


def _choose_vector(b, selector, options):
    items = list(options.items())
    result = items[0][1]
    for value, option in items[1:]:
        result = b.mix_vector(_is(b, selector, value), result, option)
    return result


def _dot(b, a, c):
    return b.vmath('DOT_PRODUCT', a, c)


def build_gradient(b, I, gout, tile):
    tc = b.texcoord()
    geo = b.geometry()
    proj = I['Projection']

    # ---- coordinates (centered) and the normal used by Slope
    def centered(vec):  # 0..1 -> -1..1
        return b.vmadd(vec, (2.0, 2.0, 2.0), (-1.0, -1.0, -1.0))

    uv = b.vmath('MULTIPLY', centered(tc.outputs['UV']), (1.0, 1.0, 0.0))
    if tile:
        p = uv
        flat = 1.0
        normal = (0.0, 0.0, 1.0)
    else:
        screen = b.vmath('MULTIPLY', centered(tc.outputs['Window']), (1.0, 1.0, 0.0))
        p = _choose_vector(b, proj, {0: centered(tc.outputs['Generated']), 1: tc.outputs['Object'],
                                     2: geo.outputs['Position'], 3: uv, 4: screen})
        flat = b.math('GREATER_THAN', proj, 2.5)  # UV, Screen: their own plane
        normal = b.mix_vector(_is(b, proj, 2), tc.outputs['Normal'], geo.outputs['Normal'])
    p = b.vscale(b.vmath('SUBTRACT', p, I['Center']), I['Scale'])

    # ---- the view plane: right (U), up (V) and depth (A) directions
    axis = b.vmath('NORMALIZE', b.mix_vector(flat, I['View Axis'], (0.0, 0.0, 1.0)))
    _ax, _ay, az = b.separate(axis)
    polar = b.math('GREATER_THAN', b.absolute(az), 0.999)  # seen from the top or bottom: up is +Y
    up = b.mix_vector(polar, (0.0, 0.0, 1.0), (0.0, 1.0, 0.0))
    v_dir = b.vmath('NORMALIZE', b.vmath('SUBTRACT', up, b.vscale(axis, _dot(b, up, axis))))
    u_dir = b.vmath('CROSS_PRODUCT', v_dir, axis)
    u0, v0, w = _dot(b, p, u_dir), _dot(b, p, v_dir), _dot(b, p, axis)
    angle = I['Angle']
    cos_a, sin_a = b.math('COSINE', angle), b.math('SINE', angle)
    u = b.madd(u0, cos_a, b.mul(v0, sin_a))  # along the gradient
    v = b.div(b.sub(b.mul(v0, cos_a), b.mul(u0, sin_a)), I['Aspect'])  # across it
    size = I['Size']
    au, av, aw = b.absolute(u), b.absolute(v), b.absolute(w)

    # ---- the raw gradient (0 at the start / center, 1 at the end)
    radius = b.math('SQRT', b.madd(u, u, b.mul(v, v)))
    sweep = b.madd(b.math('ARCTAN2', v, u), 0.5 / math.pi, 0.5)  # 0..1 around the center
    facing = b.node('ShaderNodeLayerWeight')
    b.feed(facing.inputs['Blend'], 0.5)
    shapes = {
        0: b.madd(b.div(u, size), 0.5, 0.5),
        1: b.div(au, size),
        2: b.div(radius, size),
        3: b.div(b.math('SQRT', b.madd(w, w, b.mul(radius, radius))), size),
        4: sweep,
        5: b.div(b.add(au, av), size),
        6: b.div(b.maximum(au, av), size),
        7: b.div(b.maximum(b.maximum(au, av), aw), size),
        8: b.add(sweep, b.div(radius, size)),
        9: b.madd(_dot(b, b.vmath('NORMALIZE', normal), axis), 0.5, 0.5),
        10: facing.outputs['Facing'],
    }
    t = _choose(b, I['Type'], shapes)

    # ---- shaping: noise, shift, repeat, reverse, bias, steps
    noise_vec = b.vmadd(b.vscale(p, b.div(1.0, I['Noise Size'])), (1.0, 1.0, 1.0),
                        b.vscale((1.731, 2.337, 3.119), I['Seed']))
    wobble = b.noise(noise_vec, detail=3.0, roughness=0.55, label='Noise')
    t = b.madd(b.sub(wobble, 0.5), b.mul(I['Noise'], 0.6), t)
    t = b.mul(b.add(t, I['Shift']), I['Repeat'])
    mode = I['Repeat Mode']
    t = _choose(b, mode, {0: b.clamp01(t), 1: b.fract(t), 2: b.math('PINGPONG', t, 1.0)})
    t = b.mix(I['Reverse'], t, b.one_minus(t))
    t = b.power(b.maximum(t, 0.0), b.math('EXPONENT', b.mul(I['Bias'], 2.0 * math.log(2.0))))
    steps = b.math('ROUND', I['Steps'])
    banded = b.div(b.minimum(b.floor(b.mul(t, steps)), b.sub(steps, 1.0)), b.maximum(b.sub(steps, 1.0), 1.0))
    t = b.mix(b.math('GREATER_THAN', steps, 1.5), t, banded)

    # ---- colors: walk through the stops
    count = b.math('ROUND', I['Color Stops'])
    last = b.maximum(b.sub(count, 1.0), 1.0)
    interp = I['Interpolation']
    custom = I['Spacing']
    gamma = b.mix(I['Color Mixing'], 1.0 / 2.2, 1.0)  # perceptual: blend gamma-encoded colors

    def encode(color, power):
        node = b.node('ShaderNodeGamma')
        b.feed(node.inputs['Color'], color)
        b.feed(node.inputs['Gamma'], power)
        return node.outputs['Color']

    col = encode(I['Color 1'], gamma)
    prev = b.mix(custom, 0.0, I['Position 1'])
    for i in range(1, STOPS):
        pos = b.mix(custom, b.minimum(b.div(float(i), last), 1.0), I['Position %d' % (i + 1)])
        span = b.maximum(b.sub(pos, prev), 1e-5)
        lin = b.clamp01(b.div(b.sub(t, prev), span))
        smooth = b.mul(b.mul(lin, lin), b.madd(lin, -2.0, 3.0))
        const = b.math('GREATER_THAN', t, b.sub(pos, 1e-5))
        weight = _choose(b, interp, {0: lin, 1: smooth, 2: const})
        if i >= 2:
            weight = b.mul(weight, b.math('GREATER_THAN', count, i + 0.5))  # this stop is used
        col = b.mix_color(weight, col, encode(I['Color %d' % (i + 1)], gamma))
        prev = pos
    col = encode(col, b.div(1.0, gamma))

    metallic = b.mix(t, I['Metallic'], I['Metallic End'])
    rough = b.mix(t, I['Roughness'], I['Roughness End'])
    h = b.madd(b.sub(t, 0.5), I['Relief'], 0.5)
    emission = b.mix_color(b.clamp01(I['Glow']), (0.0, 0.0, 0.0), col, clamp_result=True)
    C.finish(b, gout, I, col, metallic, rough, h, 0.0, extra={
        'Emission': emission,
        'Emission Strength': I['Emission Strength'],
        'Factor': t,
    })


SPEC = dict(
    label='Gradient', category='GRADIENT', params=GRADIENT_PARAMS, outputs=GRADIENT_OUTPUTS,
    build=build_gradient, links={'Emission': 'Emission Color', 'Emission Strength': 'Emission Strength'},
    display=('Color 2', 'Metallic', 'Roughness'), fit=0.0, glow='Glow',
)
