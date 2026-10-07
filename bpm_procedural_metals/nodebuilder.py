# SPDX-License-Identifier: GPL-3.0-or-later
"""A tiny DSL for building shader node trees from Python.

Every helper accepts plain Python numbers / tuples or node sockets and returns
an output socket.  When all inputs of a math helper are constants the result is
computed in Python, so no node gets created for it.
"""

import math
from collections import defaultdict

import bpy

TAU = 2.0 * math.pi


def is_socket(value):
    return isinstance(value, bpy.types.NodeSocket)


def _all_const(*values):
    return not any(is_socket(v) for v in values)


def _clamp01(x):
    return min(max(x, 0.0), 1.0)


def color4(value):
    if isinstance(value, (int, float)):
        v = float(value)
        return (v, v, v, 1.0)
    value = tuple(float(c) for c in value)
    if len(value) == 3:
        return value + (1.0,)
    return value[:4]


def vec3(value):
    if isinstance(value, (int, float)):
        v = float(value)
        return (v, v, v)
    return tuple(float(c) for c in value[:3])


def _scalar(value):
    if isinstance(value, (int, float, bool)):
        return float(value)
    return float(value[0])


def set_socket_value(socket, value):
    """Assign a Python value to a socket, converting between shapes as needed."""
    kind = socket.type
    if kind == 'RGBA':
        socket.default_value = color4(value)
    elif kind == 'VECTOR':
        socket.default_value = vec3(value)
    elif kind == 'BOOLEAN':
        socket.default_value = bool(_scalar(value))
    elif kind == 'INT':
        socket.default_value = int(round(_scalar(value)))
    elif kind == 'VALUE':
        socket.default_value = _scalar(value)
    else:
        socket.default_value = value


def socket_value(socket):
    """Read a socket default value as plain Python data."""
    value = socket.default_value
    if socket.type in {'RGBA', 'VECTOR'}:
        return tuple(value)
    return value


def find_socket(sockets, identifier):
    for socket in sockets:
        if socket.identifier == identifier:
            return socket
    raise KeyError(identifier)


_FOLD = {
    'ADD': lambda a, b, c: a + b,
    'SUBTRACT': lambda a, b, c: a - b,
    'MULTIPLY': lambda a, b, c: a * b,
    'DIVIDE': lambda a, b, c: a / b if b != 0.0 else 0.0,
    'MULTIPLY_ADD': lambda a, b, c: a * b + c,
    'POWER': lambda a, b, c: a ** b if a > 0.0 else 0.0,
    'MINIMUM': lambda a, b, c: min(a, b),
    'MAXIMUM': lambda a, b, c: max(a, b),
    'ABSOLUTE': lambda a, b, c: abs(a),
    'SINE': lambda a, b, c: math.sin(a),
    'COSINE': lambda a, b, c: math.cos(a),
    'FRACT': lambda a, b, c: a - math.floor(a),
    'FLOOR': lambda a, b, c: float(math.floor(a)),
    'ROUND': lambda a, b, c: float(math.floor(a + 0.5)),
    'SQRT': lambda a, b, c: math.sqrt(a) if a > 0.0 else 0.0,
    'LOGARITHM': lambda a, b, c: math.log(a, b) if a > 0.0 and b > 0.0 and b != 1.0 else 0.0,
    'GREATER_THAN': lambda a, b, c: 1.0 if a > b else 0.0,
    'WRAP': lambda a, b, c: (a - c) - (b - c) * math.floor((a - c) / (b - c)) + c if b != c else c,
    'LESS_THAN': lambda a, b, c: 1.0 if a < b else 0.0,
}

_VECTOR_VALUE_OUTPUTS = {'DOT_PRODUCT', 'LENGTH', 'DISTANCE'}


class Builder:
    """Creates nodes and links inside one node tree."""

    def __init__(self, tree):
        self.tree = tree
        self.nodes = tree.nodes
        self.links = tree.links
        self._singletons = {}
        self._memo = {}

    @staticmethod
    def _key(value):
        if is_socket(value):
            return ('S', value.as_pointer())
        if isinstance(value, (tuple, list)):
            return ('T',) + tuple(round(float(v), 9) for v in value)
        if isinstance(value, (int, float)):
            return ('F', round(float(value), 9))
        return ('O', repr(value))

    def _memoized(self, kind, args, make):
        """Reuse an identical node instead of creating a duplicate.

        Cycles merges duplicate nodes on its own, but the copy it keeps may sit
        after some of its users in the compile order, which makes big bump graphs
        run out of SVM stack.  Never creating duplicates avoids that.
        """
        key = (kind,) + tuple(self._key(a) for a in args)
        result = self._memo.get(key)
        if result is None:
            result = self._memo[key] = make()
        return result

    # ------------------------------------------------------------------ basics
    def node(self, idname, label=None, **props):
        node = self.nodes.new(idname)
        for key, value in props.items():
            setattr(node, key, value)
        if label:
            node.label = label
        return node

    def feed(self, socket, value):
        """Link a socket or assign a constant to `socket`."""
        if value is None:
            return
        if is_socket(value):
            self.links.new(value, socket)
        else:
            set_socket_value(socket, value)

    def singleton(self, idname):
        node = self._singletons.get(idname)
        if node is None:
            node = self._singletons[idname] = self.node(idname)
        return node

    def texcoord(self):
        return self.singleton('ShaderNodeTexCoord')

    def geometry(self):
        return self.singleton('ShaderNodeNewGeometry')

    # ------------------------------------------------------------- float math
    def math(self, op, a, b=0.0, c=0.0, clamp=False, label=None):
        if _all_const(a, b, c) and op in _FOLD:
            result = _FOLD[op](_scalar(a), _scalar(b), _scalar(c))
            return _clamp01(result) if clamp else result
        # Never use the node's own clamp option: Cycles expands it into an extra node
        # late in compilation, which makes big bump graphs run out of SVM stack.
        def make():
            node = self.node('ShaderNodeMath', label=label, operation=op)
            self.feed(node.inputs[0], a)
            self.feed(node.inputs[1], b)
            self.feed(node.inputs[2], c)
            return node.outputs[0]
        result = self._memoized('math' + op, (a, b, c), make)
        return self.clamp(result) if clamp else result

    def clamp(self, x, lo=0.0, hi=1.0):
        if _all_const(x, lo, hi):
            return min(max(_scalar(x), _scalar(lo)), _scalar(hi))
        def make():
            node = self.node('ShaderNodeClamp', clamp_type='MINMAX')
            self.feed(node.inputs['Value'], x)
            self.feed(node.inputs['Min'], lo)
            self.feed(node.inputs['Max'], hi)
            return node.outputs[0]
        return self._memoized('clamp', (x, lo, hi), make)

    def add(self, a, b, clamp=False):
        if not clamp:
            if not is_socket(b) and b == 0.0:
                return a
            if not is_socket(a) and a == 0.0:
                return b
        return self.math('ADD', a, b, clamp=clamp)

    def sub(self, a, b, clamp=False):
        if not clamp and not is_socket(b) and b == 0.0:
            return a
        return self.math('SUBTRACT', a, b, clamp=clamp)

    def mul(self, a, b, clamp=False):
        if not clamp:
            if not is_socket(b) and b == 1.0:
                return a
            if not is_socket(a) and a == 1.0:
                return b
        if (not is_socket(a) and a == 0.0) or (not is_socket(b) and b == 0.0):
            return 0.0
        return self.math('MULTIPLY', a, b, clamp=clamp)

    def div(self, a, b):
        return self.math('DIVIDE', a, b)

    def madd(self, a, b, c, clamp=False):
        """a * b + c"""
        return self.math('MULTIPLY_ADD', a, b, c, clamp=clamp)

    def maximum(self, a, b):
        return self.math('MAXIMUM', a, b)

    def minimum(self, a, b):
        return self.math('MINIMUM', a, b)

    def absolute(self, a):
        return self.math('ABSOLUTE', a)

    def power(self, a, b):
        return self.math('POWER', a, b)

    def clamp01(self, a):
        return self.clamp(a, 0.0, 1.0)

    def one_minus(self, a):
        return self.math('SUBTRACT', 1.0, a)

    def mix(self, fac, a, b):
        """Linear blend between floats a and b (fac is clamped to 0..1)."""
        if _all_const(fac, a, b):
            f = _clamp01(_scalar(fac))
            return _scalar(a) + (_scalar(b) - _scalar(a)) * f
        if not is_socket(fac) and fac <= 0.0:
            return a
        def make():
            node = self.node('ShaderNodeMix', data_type='FLOAT', clamp_factor=True)
            self.feed(find_socket(node.inputs, 'Factor_Float'), fac)
            self.feed(find_socket(node.inputs, 'A_Float'), a)
            self.feed(find_socket(node.inputs, 'B_Float'), b)
            return find_socket(node.outputs, 'Result_Float')
        return self._memoized('mix', (fac, a, b), make)

    def map_range(self, x, from_min, from_max, to_min=0.0, to_max=1.0, clamp=True, interp='LINEAR'):
        # The node's clamp option is avoided for the same reason as in math().
        # Smoothstep interpolation is bounded by itself, so it never needs clamping.
        def make():
            node = self.node('ShaderNodeMapRange', data_type='FLOAT', interpolation_type=interp, clamp=False)
            for ident, value in (('Value', x), ('From Min', from_min), ('From Max', from_max),
                                 ('To Min', to_min), ('To Max', to_max)):
                self.feed(find_socket(node.inputs, ident), value)
            return find_socket(node.outputs, 'Result')
        result = self._memoized('maprange' + interp, (x, from_min, from_max, to_min, to_max), make)
        if clamp and interp not in {'SMOOTHSTEP', 'SMOOTHERSTEP'}:
            lo, hi = (to_min, to_max) if _all_const(to_min, to_max) and to_min <= to_max else (to_max, to_min)
            result = self.clamp(result, lo, hi)
        return result

    def smoothstep(self, edge0, edge1, x):
        return self.map_range(x, edge0, edge1, 0.0, 1.0, True, 'SMOOTHSTEP')

    def linstep(self, edge0, edge1, x):
        return self.map_range(x, edge0, edge1, 0.0, 1.0, True, 'LINEAR')

    # ------------------------------------------------------------ color math
    def mix_color(self, fac, a, b, blend='MIX', clamp_result=False):
        if not is_socket(fac) and fac <= 0.0 and blend == 'MIX':
            return a
        def make():
            node = self.node('ShaderNodeMix', data_type='RGBA', blend_type=blend,
                             clamp_factor=True, clamp_result=clamp_result)
            self.feed(find_socket(node.inputs, 'Factor_Float'), fac)
            self.feed(find_socket(node.inputs, 'A_Color'), a)
            self.feed(find_socket(node.inputs, 'B_Color'), b)
            return find_socket(node.outputs, 'Result_Color')
        return self._memoized('mixc' + blend + str(clamp_result), (fac, a, b), make)

    def mix_vector(self, fac, a, b):
        node = self.node('ShaderNodeMix', data_type='VECTOR', clamp_factor=True)
        node.factor_mode = 'UNIFORM'
        self.feed(find_socket(node.inputs, 'Factor_Float'), fac)
        self.feed(find_socket(node.inputs, 'A_Vector'), a)
        self.feed(find_socket(node.inputs, 'B_Vector'), b)
        return find_socket(node.outputs, 'Result_Vector')

    def gray(self, value):
        """A color socket (value, value, value) without implicit conversions."""
        if not is_socket(value):
            return color4(value)
        def make():
            node = self.node('ShaderNodeCombineColor', mode='RGB')
            for i in range(3):
                self.feed(node.inputs[i], value)
            return node.outputs[0]
        return self._memoized('gray', (value,), make)

    def color_scale(self, color, factor):
        """Multiply a color by a scalar (stays a color socket)."""
        if not is_socket(factor) and factor == 1.0:
            return color
        return self.mix_color(1.0, color, self.gray(factor), blend='MULTIPLY')

    def hsv(self, color, hue=0.5, saturation=1.0, value=1.0, fac=1.0):
        node = self.node('ShaderNodeHueSaturation')
        self.feed(node.inputs['Hue'], hue)
        self.feed(node.inputs['Saturation'], saturation)
        self.feed(node.inputs['Value'], value)
        self.feed(node.inputs['Fac'], fac)
        self.feed(node.inputs['Color'], color)
        return node.outputs['Color']

    def ramp(self, fac, stops, interpolation='LINEAR', label=None):
        """Color ramp. stops = [(position, (r, g, b)), ...]"""
        node = self.node('ShaderNodeValToRGB', label=label)
        ramp = node.color_ramp
        ramp.interpolation = interpolation
        elements = ramp.elements
        stops = sorted(stops, key=lambda s: s[0])
        # elements stay sorted by position, so set both ends first, then insert
        elements[0].position, elements[0].color = stops[0][0], color4(stops[0][1])
        elements[-1].position, elements[-1].color = stops[-1][0], color4(stops[-1][1])
        for position, color in stops[1:-1]:
            elements.new(position).color = color4(color)
        self.feed(node.inputs['Fac'], fac)
        return node.outputs['Color']

    # ----------------------------------------------------------- vector math
    def vmath(self, op, a, b=None, c=None, scale=None, label=None):
        def make():
            node = self.node('ShaderNodeVectorMath', operation=op, label=label)
            self.feed(node.inputs[0], a)
            if b is not None:
                self.feed(node.inputs[1], b)
            if c is not None:
                self.feed(node.inputs[2], c)
            if scale is not None:
                self.feed(find_socket(node.inputs, 'Scale'), scale)
            return node.outputs['Value' if op in _VECTOR_VALUE_OUTPUTS else 'Vector']
        return self._memoized('vmath' + op, (a, b, c, scale), make)

    def vadd(self, a, b):
        if _all_const(a, b):
            return tuple(x + y for x, y in zip(vec3(a), vec3(b)))
        return self.vmath('ADD', a, b)

    def vscale(self, v, s):
        if _all_const(v, s):
            return tuple(x * _scalar(s) for x in vec3(v))
        return self.vmath('SCALE', v, scale=s)

    def vmadd(self, a, b, c):
        """a * b + c (component-wise)"""
        return self.vmath('MULTIPLY_ADD', a, b, c)

    def combine(self, x, y, z):
        if _all_const(x, y, z):
            return (_scalar(x), _scalar(y), _scalar(z))

        def make():
            node = self.node('ShaderNodeCombineXYZ')
            self.feed(node.inputs[0], x)
            self.feed(node.inputs[1], y)
            self.feed(node.inputs[2], z)
            return node.outputs[0]
        return self._memoized('combine', (x, y, z), make)

    def separate(self, v):
        def make():
            node = self.node('ShaderNodeSeparateXYZ')
            self.feed(node.inputs[0], v)
            return node.outputs[0], node.outputs[1], node.outputs[2]
        return self._memoized('separate', (v,), make)

    def separate_color(self, color):
        def make():
            node = self.node('ShaderNodeSeparateColor', mode='RGB')
            self.feed(node.inputs[0], color)
            return node.outputs[0], node.outputs[1], node.outputs[2]
        return self._memoized('separate_color', (color,), make)

    def vector_transform(self, vector, kind='VECTOR', src='OBJECT', dst='WORLD'):
        def make():
            node = self.node('ShaderNodeVectorTransform', vector_type=kind, convert_from=src, convert_to=dst)
            self.feed(node.inputs['Vector'], vector)
            return node.outputs['Vector']
        return self._memoized('vt' + kind + src + dst, (vector,), make)

    def mapping_rotate(self, vector, rotation):
        node = self.node('ShaderNodeMapping', vector_type='POINT')
        self.feed(node.inputs['Vector'], vector)
        self.feed(node.inputs['Rotation'], rotation)
        return node.outputs['Vector']

    # --------------------------------------------------------------- textures
    def noise_node(self, vector, w=None, scale=1.0, detail=2.0, roughness=0.5, lacunarity=2.0,
                   distortion=0.0, dims='3D', kind='FBM', normalize=True, label=None):
        node = self.node('ShaderNodeTexNoise', label=label, noise_dimensions=dims)
        node.noise_type = kind
        node.normalize = normalize
        inputs = node.inputs
        self.feed(find_socket(inputs, 'Vector'), vector)
        if w is not None:
            self.feed(find_socket(inputs, 'W'), w)
        self.feed(find_socket(inputs, 'Scale'), scale)
        self.feed(find_socket(inputs, 'Detail'), detail)
        self.feed(find_socket(inputs, 'Roughness'), roughness)
        self.feed(find_socket(inputs, 'Lacunarity'), lacunarity)
        self.feed(find_socket(inputs, 'Distortion'), distortion)
        return node

    def noise(self, vector, **kwargs):
        return self.noise_node(vector, **kwargs).outputs['Fac']

    def voronoi_node(self, vector, w=None, scale=1.0, feature='F1', metric='EUCLIDEAN', randomness=1.0,
                     smoothness=1.0, dims='3D', label=None):
        node = self.node('ShaderNodeTexVoronoi', label=label, voronoi_dimensions=dims,
                         feature=feature, distance=metric)
        inputs = node.inputs
        self.feed(find_socket(inputs, 'Vector'), vector)
        if w is not None:
            self.feed(find_socket(inputs, 'W'), w)
        self.feed(find_socket(inputs, 'Scale'), scale)
        self.feed(find_socket(inputs, 'Randomness'), randomness)
        if feature == 'SMOOTH_F1':
            self.feed(find_socket(inputs, 'Smoothness'), smoothness)
        return node

    def white_noise(self, vector, w=None, dims='3D', label=None):
        """Random value (and color) per distinct input: (value, color) sockets."""
        def make():
            node = self.node('ShaderNodeTexWhiteNoise', label=label, noise_dimensions=dims)
            self.feed(find_socket(node.inputs, 'Vector'), vector)
            if w is not None:
                self.feed(find_socket(node.inputs, 'W'), w)
            return node.outputs['Value'], node.outputs['Color']
        return self._memoized('white' + dims, (vector, w), make)

    def floor(self, a):
        return self.math('FLOOR', a)

    def fract(self, a):
        return self.math('FRACT', a)

    def wrap(self, a, period):
        """a modulo period (period > 0), always positive."""
        return self.math('WRAP', a, period, 0.0)

    def bump(self, height, strength=1.0, distance=1.0, normal=None, invert=False, label=None):
        node = self.node('ShaderNodeBump', label=label, invert=invert)
        self.feed(node.inputs['Strength'], strength)
        self.feed(node.inputs['Distance'], distance)
        self.feed(node.inputs['Height'], height)
        self.feed(node.inputs['Normal'], normal)
        return node.outputs['Normal']


# ---------------------------------------------------------------- node groups
SOCKET_TYPES = {
    'FLOAT': 'NodeSocketFloat',
    'COLOR': 'NodeSocketColor',
    'VECTOR': 'NodeSocketVector',
    'BOOL': 'NodeSocketBool',
}


def create_group(name, params, outputs):
    """Create a shader node group whose interface is described by `params`.

    `params`  : sequence of objects with name/kind/default/min/max/panel/desc/subtype
    `outputs` : sequence of (name, kind) tuples
    Returns (tree, group_input_node, group_output_node).
    """
    tree = bpy.data.node_groups.new(name, 'ShaderNodeTree')
    iface = tree.interface
    for out_name, kind in outputs:
        iface.new_socket(out_name, in_out='OUTPUT', socket_type=SOCKET_TYPES[kind])
    panels = {}
    for p in params:
        parent = None
        if p.panel:
            parent = panels.get(p.panel)
            if parent is None:
                parent = panels[p.panel] = iface.new_panel(p.panel, default_closed=p.panel != params[0].panel)
        sock = iface.new_socket(p.name, in_out='INPUT', socket_type=SOCKET_TYPES[p.kind], parent=parent)
        if p.desc:
            sock.description = p.desc
        if p.kind == 'FLOAT':
            if p.subtype:
                sock.subtype = p.subtype
            sock.min_value = p.min
            sock.max_value = p.max
            sock.default_value = p.default
        elif p.kind == 'VECTOR':
            sock.min_value = p.min
            sock.max_value = p.max
            sock.default_value = vec3(p.default)
        elif p.kind == 'COLOR':
            sock.default_value = color4(p.default)
        elif p.kind == 'BOOL':
            sock.default_value = bool(p.default)
    gin = tree.nodes.new('NodeGroupInput')
    gout = tree.nodes.new('NodeGroupOutput')
    return tree, gin, gout


# --------------------------------------------------------------- auto layout
def _estimate_height(node):
    visible = sum(1 for s in node.inputs if s.enabled and not s.hide)
    visible += sum(1 for s in node.outputs if s.enabled and not s.hide)
    extra = 0
    if node.bl_idname in {'ShaderNodeValToRGB'}:
        extra = 120
    elif node.bl_idname.startswith('ShaderNodeTex') or node.bl_idname in {
            'ShaderNodeMix', 'ShaderNodeMapRange', 'ShaderNodeMath', 'ShaderNodeVectorMath',
            'ShaderNodeVectorTransform', 'ShaderNodeMapping', 'ShaderNodeAmbientOcclusion'}:
        extra = 50
    return 40 + 22 * visible + extra


def auto_layout(tree, x_spacing=60.0, y_spacing=20.0):
    """Arrange nodes in columns by their distance to the output node."""
    nodes = [n for n in tree.nodes if n.bl_idname != 'NodeFrame']
    downstream = defaultdict(set)
    upstream = defaultdict(set)
    for link in tree.links:
        downstream[link.from_node].add(link.to_node)
        upstream[link.to_node].add(link.from_node)

    # longest distance to a sink, computed iteratively (Kahn on reversed graph)
    depth = {n: 0 for n in nodes}
    pending = {n: len(downstream[n]) for n in nodes}
    queue = [n for n in nodes if pending[n] == 0]
    while queue:
        node = queue.pop()
        for src in upstream[node]:
            depth[src] = max(depth[src], depth[node] + 1)
            pending[src] -= 1
            if pending[src] == 0:
                queue.append(src)

    columns = defaultdict(list)
    for node in nodes:
        columns[depth[node]].append(node)

    x = 0.0
    y_of = {}
    for col in sorted(columns):
        col_nodes = columns[col]

        def key(n):
            ys = [y_of[d] for d in downstream[n] if d in y_of]
            return -(sum(ys) / len(ys)) if ys else 0.0

        col_nodes.sort(key=key)
        width = max(n.width for n in col_nodes)
        heights = [_estimate_height(n) for n in col_nodes]
        total = sum(heights) + y_spacing * (len(col_nodes) - 1)
        y = total / 2.0
        for node, h in zip(col_nodes, heights):
            node.location = (x - node.width, y)
            y_of[node] = y - h / 2.0
            y -= h + y_spacing
        x -= width + x_spacing
