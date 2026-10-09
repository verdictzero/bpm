# SPDX-License-Identifier: GPL-3.0-or-later
"""Reusable procedural building blocks shared by the material generators.

Two coordinate modes are supported:

* Object mode: 3D coordinates that stick to the object, measured in real
  meters (unapplied object scale is compensated), so the pattern looks right
  on any model regardless of its UVs.
* Tile mode: the UV square is wrapped onto a torus in 4D noise space, which
  makes every texture lookup seamlessly periodic.  Used for baking tileable
  texture sets.
"""

import copy
import math

from .nodebuilder import TAU, is_socket

# Rotations (radians) used to give scratch layers different directions in 3D.
_SCRATCH_ROTATIONS = (
    (0.31, 1.13, 0.47),
    (1.27, 0.21, 2.09),
    (2.33, 0.83, 1.31),
    (0.71, 2.41, 0.17),
)
# Lattice-friendly directions that keep tiles seamless (integer combinations of U and V),
# picked to avoid an obvious horizontal/vertical grid.
_SCRATCH_DIRECTIONS = ('D21', 'D12', 'D1')


def _offset(index):
    """Deterministic, well separated offsets so features don't correlate."""
    i = float(index)
    return (
        (i * 37.17) % 97.0 + 3.1,
        (i * 53.11) % 89.0 + 7.3,
        (i * 71.37) % 83.0 + 11.7,
        (i * 29.83) % 79.0 + 5.9,
    )


class Space:
    """Hands out texture coordinates for object space or seamless tiles."""

    def __init__(self, b, tile, scale, seed, tile_size=1.0, salt=0):
        """`salt` (an integer) changes how the coordinates are computed, not their values.

        Cycles merges identical nodes of different node groups.  The merged
        coordinate nodes then stay alive on the shader stack for a long time,
        so a material with overlays on top could run out of stack.  Overlays
        use their own salt, which keeps their nodes apart.
        """
        self.b = b
        self.tile = tile
        self.salt = salt
        self.dims = '4D' if tile else '3D'
        self._trig = {}
        self._seed_vec = b.vscale((1.731, 2.337, 3.119), seed)
        self._seed_w = b.mul(seed, 1.913)
        if tile:
            u, v, _ = b.separate(b.texcoord().outputs['UV'])
            self.u, self.v = u, v
            # torus radius for one feature per meter at frequency 1
            self.k = b.div(b.mul(tile_size, scale), TAU)
            self.P = None
        else:
            obj = b.texcoord().outputs['Object']
            f = float(1 + salt)
            axes = [b.vmath('LENGTH', b.vector_transform(axis)) for axis in ((f, 0, 0), (0, f, 0), (0, 0, f))]
            meters = b.vmath('MULTIPLY', obj, b.combine(*axes))
            self.P = b.vscale(meters, scale if not salt else b.div(scale, f))

    def warped(self, offset):
        """A copy of this space with shifted coordinates (organic warping).

        offset: a vector (object mode, pattern units) or a (du, dv) pair of
        periodic UV shifts (tile mode, so the result stays seamless).
        """
        if self.tile:
            du, dv = offset
            return self.at(uv=(self.b.add(self.u, du), self.b.add(self.v, dv)))
        return self.at(P=self.b.vadd(self.P, offset))

    def at(self, P=None, uv=None):
        """A copy of this space using other coordinates: P (object mode) or (u, v) (tile mode)."""
        other = copy.copy(self)
        other._trig = {}
        if self.tile:
            other.u, other.v = uv
        else:
            other.P = P
        return other

    def pixelated(self, size, amount, span=None):
        """A copy whose coordinates snap to squares of `size` (pattern units): digital patterns.

        `amount` blends from smooth (0) to snapped (1) coordinates.  Tiles need
        `span` (pattern units across the tile) to fit a whole number of pixels.
        """
        b = self.b
        if self.tile:
            n = b.maximum(1.0, b.math('ROUND', b.div(span, size)))

            def snap(x):
                return b.div(b.add(b.floor(b.mul(x, n)), 0.5), n)
            return self.at(uv=(b.mix(amount, self.u, snap(self.u)), b.mix(amount, self.v, snap(self.v))))
        grid = (0.37, 0.61, 0.23)  # shifted grid: faces at round coordinates don't sit on a pixel border
        q = b.vadd(b.vscale(self.P, b.div(1.0, size)), grid)
        snapped = b.vscale(b.vadd(b.vmath('FLOOR', q), tuple(0.5 - g for g in grid)), size)
        return self.at(P=b.mix_vector(amount, self.P, snapped))

    def shattered(self, freq, offset, amount, aniso=None):
        """A copy whose coordinates snap to the cells of a Voronoi pattern.

        Every lookup inside a cell then returns the value at the cell's center,
        so patterns turn into straight-edged shards (splinter camouflage).
        `amount` blends from smooth (0) to snapped (1) coordinates.
        """
        b = self.b
        if self.tile:
            cu, cv = self._periodic_cells(freq, offset, aniso)

            def blend(a, c):  # the short way around the tile
                return b.madd(b.sub(b.wrap(b.add(b.sub(c, a), 0.5), 1.0), 0.5), amount, a)
            return self.at(uv=(blend(self.u, cu), blend(self.v, cv)))
        cells = self.voronoi(freq, offset, aniso=aniso, label='Shards')
        off, _off_w = self._offsets(offset)
        if aniso is None:  # the same frequencies as sample()
            f = b.combine(freq, freq, freq)
        else:
            f = b.vscale(tuple(aniso) + (1.0,) * (3 - len(aniso)), freq)
        center = b.vmath('DIVIDE', b.vmath('SUBTRACT', cells.outputs['Position'], off), f)
        return self.at(P=b.mix_vector(amount, self.P, center))

    def _periodic_cells(self, freq, offset, aniso=None):
        """Tiles: (u, v) of the nearest cell center of a seamless 2D Voronoi pattern.

        Blender's Voronoi texture does not repeat, so this one is built from a
        whole number of jittered cells across the tile, searching the 3 x 3
        cells around each point (cell numbers wrap around at the tile border).
        """
        b = self.b
        ax, ay = (aniso[0], aniso[1]) if aniso is not None else (1.0, 1.0)
        cells = b.mul(b.mul(self.k, TAU), freq)  # cells across the tile at `freq`
        nu = b.maximum(1.0, b.math('ROUND', b.mul(cells, ax)))
        nv = b.maximum(1.0, b.math('ROUND', b.mul(cells, ay)))
        x, y = b.mul(self.u, nu), b.mul(self.v, nv)
        cx, cy = b.floor(x), b.floor(y)
        key_w = b.add(self._seed_w, float(offset))
        best = None
        for dj in (-1.0, 0.0, 1.0):
            for di in (-1.0, 0.0, 1.0):
                i, j = b.add(cx, di), b.add(cy, dj)
                _value, rnd = b.white_noise(b.combine(b.wrap(i, nu), b.wrap(j, nv), key_w))
                jx, jy, _jz = b.separate_color(rnd)
                px, py = b.add(i, jx), b.add(j, jy)
                dx, dy = b.sub(px, x), b.sub(py, y)
                d = b.madd(dx, dx, b.mul(dy, dy))
                if best is None:
                    best = (d, px, py)
                    continue
                closer = b.math('LESS_THAN', d, best[0])
                best = (b.minimum(d, best[0]), b.mix(closer, best[1], px), b.mix(closer, best[2], py))
        return b.div(best[1], nu), b.div(best[2], nv)

    # -- internals ------------------------------------------------------------
    def _offsets(self, index):
        o = _offset(index)
        return self.b.vadd(self._seed_vec, o[:3]), self.b.add(self._seed_w, o[3])

    def trig(self, direction=None):
        key = direction or 'UV'
        cached = self._trig.get(key)
        if cached:
            return cached
        b, u, v = self.b, self.u, self.v
        if key == 'UV':
            a, c = u, v
        elif key == 'VU':
            a, c = v, u
        elif key == 'D1':
            a, c = b.add(u, v), b.sub(u, v)
        elif key == 'D2':
            a, c = b.sub(u, v), b.add(u, v)
        elif key == 'D21':  # lines at ~27 degrees
            a, c = b.madd(u, 2.0, v), b.madd(v, -2.0, u)
        elif key == 'D12':  # lines at ~-63 degrees
            a, c = b.madd(v, -2.0, u), b.madd(u, 2.0, v)
        else:
            raise ValueError(key)
        if self.salt:  # whole turns: same values, different nodes (see __init__)
            a, c = b.add(a, float(self.salt)), b.add(c, float(self.salt))
        au = b.mul(a, TAU)
        av = b.mul(c, TAU)
        result = (b.math('COSINE', au), b.math('SINE', au), b.math('COSINE', av), b.math('SINE', av))
        self._trig[key] = result
        return result

    # -- public ---------------------------------------------------------------
    def sample(self, freq, offset, aniso=None, base=None, direction=None, jitter=None):
        """Return (vector, w) for a texture lookup at `freq` features per meter.

        aniso     : per-axis frequency multipliers (x, y[, z]); in tile mode x maps
                    to U and y to V.
        base      : custom base coordinates (object mode only).
        direction : rotation (object mode) or lattice direction name (tile mode).
        jitter    : scalar that shifts the lookup into an unrelated part of the
                    noise; a different value per board / panel makes every one
                    look different (stays seamless in tile mode).
        """
        b = self.b
        off, off_w = self._offsets(offset)
        if not self.tile:
            p = base if base is not None else self.P
            if direction is not None:
                p = b.mapping_rotate(p, direction)
            if aniso is None:
                f = b.combine(freq, freq, freq)
            else:
                f = b.vscale(tuple(aniso) + (1.0,) * (3 - len(aniso)), freq)
            if jitter is not None:
                off = b.vadd(off, b.vscale((1.0, 1.618, 2.414), jitter))
            return b.vmadd(p, f, off), None
        cu, su, cv, sv = self.trig(direction if isinstance(direction, str) else None)
        radius = b.mul(self.k, freq)
        ax, ay = (aniso[0], aniso[1]) if aniso is not None else (1.0, 1.0)
        rx = b.mul(radius, ax)
        ry = b.mul(radius, ay)
        vec = b.vmadd(b.combine(cu, su, cv), b.combine(rx, rx, ry), off)
        w = b.madd(sv, ry, off_w if jitter is None else b.add(off_w, jitter))
        return vec, w

    def noise(self, freq, offset, detail=2.0, roughness=0.5, distortion=0.0, aniso=None, base=None,
              direction=None, lacunarity=2.0, kind='FBM', jitter=None, label=None):
        vec, w = self.sample(freq, offset, aniso, base, direction, jitter)
        return self.b.noise(vec, w=w, scale=1.0, detail=detail, roughness=roughness, distortion=distortion,
                            lacunarity=lacunarity, dims=self.dims, kind=kind, label=label)

    def znoise(self, freq, offset, detail=2.0, roughness=0.5, **kwargs):
        """Noise expressed in standard deviations (mean 0, std ~1)."""
        n = self.noise(freq, offset, detail=detail, roughness=roughness, **kwargs)
        return zscore(self.b, n, noise_sigma(detail))

    def voronoi(self, freq, offset, feature='F1', randomness=1.0, smoothness=1.0, aniso=None, base=None,
                jitter=None, label=None):
        vec, w = self.sample(freq, offset, aniso, base, None, jitter)
        return self.b.voronoi_node(vec, w=w, scale=1.0, feature=feature, randomness=randomness,
                                   smoothness=smoothness, dims=self.dims, label=label)


# ------------------------------------------------------------------- masks
def mesh_maps(b):
    """Sockets of the analyzed mesh maps (meshmaps.py), made once per node group.

    Returns a dict: has (1 when the object's mesh was analyzed), convex, concave,
    occlusion (0..1 channels) and edge_reach / cavity_reach (meters).
    """
    maps = getattr(b, '_bpm_mesh_maps', None)
    if maps is not None:
        return maps
    from . import meshmaps as M  # meshmaps imports the material library

    uv = b.node('ShaderNodeUVMap', label='Mesh Maps UV')
    uv.uv_map = M.UV_NAME
    tex = b.node('ShaderNodeTexImage', label='Mesh Maps')
    tex.image = M.ensure_image()
    tex.interpolation = 'Linear'
    tex.extension = 'EXTEND'
    b.feed(tex.inputs['Vector'], uv.outputs['UV'])
    convex, concave, occlusion = b.separate_color(tex.outputs['Color'])

    def attribute(name):
        node = b.node('ShaderNodeAttribute', label=name)
        node.attribute_type = 'OBJECT'
        node.attribute_name = name
        return node.outputs['Fac']

    # reaches are stored in object units: convert to meters like the coordinates
    axes = [b.vmath('LENGTH', b.vector_transform(axis)) for axis in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]
    scale = b.mul(b.add(b.add(axes[0], axes[1]), axes[2]), 1.0 / 3.0)
    maps = b._bpm_mesh_maps = {
        'has': b.clamp01(attribute(M.FLAG)),
        'convex': convex,
        'concave': concave,
        'occlusion': occlusion,
        'edge_reach': b.maximum(b.mul(attribute(M.EDGE), scale), 1e-4),
        'cavity_reach': b.maximum(b.mul(attribute(M.CAVITY), scale), 1e-4),
    }
    return maps


def edge_mask(b, space, radius):
    """~1 on convex edges (a band about `radius` meters wide), 0 on flat areas.

    Analyzed objects (mesh maps) get an exact band that works in EEVEE too.
    Others use two live detectors (Cycles and baking only):
    * the Bevel node catches sharp edges (also on thin sheets),
    * "inside" ambient occlusion catches rounded / bevelled edges.  Its result is
      faded out again when (nearly) every ray is blocked, which is what happens
      on thin plates, so those don't light up completely.
    """
    if space.tile:
        return 0.0
    bevel = b.node('ShaderNodeBevel', label='Sharp Edges')
    bevel.samples = 8
    b.feed(bevel.inputs['Radius'], radius)
    d = b.vmath('DOT_PRODUCT', bevel.outputs['Normal'], b.geometry().outputs['Normal'])
    sharp = b.smoothstep(0.004, 0.09, b.one_minus(d))
    ao = b.node('ShaderNodeAmbientOcclusion', label='Rounded Edges')
    ao.samples = 8
    ao.inside = True
    ao.only_local = True
    b.feed(ao.inputs['Distance'], b.mul(radius, 3.0))
    occlusion = b.one_minus(ao.outputs['AO'])
    rounded = b.mul(b.smoothstep(0.13, 0.4, occlusion), b.one_minus(b.smoothstep(0.8, 0.97, occlusion)))
    live = b.maximum(sharp, rounded)

    maps = mesh_maps(b)
    reach = maps['edge_reach']
    x = b.mul(b.one_minus(maps['convex']), reach)  # meters to the nearest edge
    w = b.minimum(radius, b.mul(reach, 0.52))      # the map knows nothing past its reach
    baked = b.one_minus(b.smoothstep(b.mul(w, 0.45), b.mul(w, 1.9), x))
    return b.mix(maps['has'], live, baked)


def cavity_mask(b, space, distance):
    """~1 in crevices, inner corners and enclosed areas (`distance`: meters they reach out).

    Analyzed objects (mesh maps) get solid fills that work in EEVEE too; others
    use live ambient occlusion (Cycles; approximate in EEVEE).
    """
    if space.tile:
        return 0.0
    ao = b.node('ShaderNodeAmbientOcclusion', label='Cavity')
    ao.samples = 8
    ao.only_local = True
    b.feed(ao.inputs['Distance'], distance)
    live = b.smoothstep(0.05, 0.5, b.one_minus(ao.outputs['AO']))

    maps = mesh_maps(b)
    reach = maps['cavity_reach']
    x = b.mul(b.one_minus(maps['concave']), reach)   # meters to the nearest inner corner
    d = b.minimum(distance, reach)
    crease = b.one_minus(b.smoothstep(0.0, b.mul(d, 0.8), x))
    deep = b.mul(b.smoothstep(0.3, 0.75, maps['occlusion']), 0.85)  # insets, pockets, contact areas
    baked = b.maximum(crease, deep)
    return b.mix(maps['has'], live, baked)


_SIGMA_BY_DETAIL = ((1.5, 0.090), (2.0, 0.082), (3.0, 0.076), (4.0, 0.069), (5.0, 0.068),
                    (6.0, 0.064), (8.0, 0.062), (16.0, 0.060))


def noise_sigma(detail):
    """Standard deviation of Blender's normalized FBM noise (measured)."""
    if is_socket(detail):
        return 0.068
    d = float(detail)
    table = _SIGMA_BY_DETAIL
    if d <= table[0][0]:
        return table[0][1]
    for (d0, s0), (d1, s1) in zip(table, table[1:]):
        if d <= d1:
            return s0 + (s1 - s0) * (d - d0) / (d1 - d0)
    return table[-1][1]


def zscore(b, n, sigma):
    """Turn a noise value (mean 0.5) into standard deviations from the mean."""
    return b.madd(n, 1.0 / sigma, -0.5 / sigma)


def amount_to_z(b, amount):
    """Threshold (in standard deviations) above which ~`amount` of a normal field lies."""
    if not is_socket(amount):
        a = min(max(float(amount), 0.002), 0.998)
        return math.log((1.0 - a) / a) / 1.702
    a = b.map_range(amount, 0.0, 1.0, 0.002, 0.998)
    return b.div(b.math('LOGARITHM', b.div(b.one_minus(a), a), math.e), 1.702)


def cover(b, z, amount, softness, bias=0.0, gate=True):
    """Mask covering roughly `amount` (0..1) of the surface, picked where `z` is highest."""
    threshold = b.add(amount_to_z(b, amount), bias)
    mask = b.smoothstep(b.sub(threshold, softness), b.add(threshold, softness), z)
    if gate:
        mask = b.mul(mask, b.clamp01(b.mul(amount, 25.0)))
    return mask


def broken(b, space, mask, offset, freq=28.0):
    """Break up a smooth mask with noise (for chipped / worn edges)."""
    if not is_socket(mask):
        return mask
    z = space.znoise(freq, offset, detail=3.0, roughness=0.6)
    return b.clamp01(b.mul(mask, b.madd(z, 0.45, 0.85)))


def _rotate_x_axis(euler):
    """Unit vector: the X axis rotated by an XYZ Euler rotation (radians)."""
    ax, ay, az = euler
    v = (1.0, 0.0, 0.0)
    # rotate around X (no effect on the X axis), then Y, then Z
    x, y, z = v
    y, z = y * math.cos(ax) - z * math.sin(ax), y * math.sin(ax) + z * math.cos(ax)
    x, z = x * math.cos(ay) + z * math.sin(ay), -x * math.sin(ay) + z * math.cos(ay)
    x, y = x * math.cos(az) - y * math.sin(az), x * math.sin(az) + y * math.cos(az)
    return (x, y, z)


def surface_direction(b, direction, fallback=True):
    """`direction` (object space) projected onto the surface and normalized.

    With `fallback`, a perpendicular direction is used where the surface faces
    `direction` itself, so stretched patterns never collapse into blotches.
    """
    n = b.vmath('NORMALIZE', b.texcoord().outputs['Normal'])
    if not fallback:
        d = direction
        return b.vmath('NORMALIZE', b.vmath('SUBTRACT', d, b.vscale(n, b.vmath('DOT_PRODUCT', d, n))))
    d = b.vmath('NORMALIZE', direction)
    if is_socket(direction):
        _, _, dz = b.separate(d)
        up = b.mix_vector(b.math('GREATER_THAN', b.absolute(dz), 0.9), (0.0, 0.0, 1.0), (0.0, 1.0, 0.0))
    else:
        up = (0.0, 1.0, 0.0) if abs(direction[2]) > 0.9 else (0.0, 0.0, 1.0)
    d2 = b.vmath('NORMALIZE', b.vmath('CROSS_PRODUCT', up, d))

    def project(v):
        return b.vmath('SUBTRACT', v, b.vscale(n, b.vmath('DOT_PRODUCT', v, n)))

    facing = b.smoothstep(0.55, 0.8, b.absolute(b.vmath('DOT_PRODUCT', d, n)))
    return b.vmath('NORMALIZE', b.mix_vector(facing, project(d), project(d2)))


def box_coords(b, space):
    """2D coordinates (pattern units) in the plane the surface faces most (object mode):
    x / y on top and bottom, x / z on front and back, y / z on the sides."""
    x, y, z = b.separate(space.P)
    ax, ay, az = b.separate(b.vmath('ABSOLUTE', b.texcoord().outputs['Normal']))
    isz = b.mul(b.math('GREATER_THAN', az, b.mul(ax, 0.999)), b.math('GREATER_THAN', az, b.mul(ay, 0.999)))
    isy = b.mul(b.one_minus(isz), b.math('GREATER_THAN', ay, b.mul(ax, 0.999)))
    isx = b.one_minus(b.add(isz, isy))
    s = b.add(b.mul(x, b.add(isz, isy)), b.mul(y, isx))
    t = b.add(b.mul(y, isz), b.mul(z, b.add(isy, isx)))
    return s, t


def squashed(b, p, direction, stretch):
    """Coordinates squashed along `direction`: patterns get `stretch` times longer that way."""
    d = b.vmath('NORMALIZE', direction)
    along = b.mul(b.vmath('DOT_PRODUCT', p, d), b.one_minus(b.div(1.0, stretch)))
    return b.vmath('SUBTRACT', p, b.vscale(d, along))


def chip_field(b, space, scale, detail, edge, cav, edge_wear, offset, edge_weight=3.5):
    """Where paint chips off first (highest values): ragged clusters, edges, never crevices."""
    cz = space.znoise(scale, offset, detail=b.madd(detail, 8.0, 2.0), roughness=b.madd(detail, 0.25, 0.45),
                      label='Chips')
    clz = space.znoise(b.mul(scale, 0.18), offset + 1, detail=2.0, label='Chip Clusters')
    field = b.madd(clz, 0.5, b.mul(cz, 0.85))
    if is_socket(edge):
        field = b.madd(edge, b.mul(edge_wear, edge_weight), field)
        field = b.madd(cav, -1.0, field)
    return field


def chip_layers(b, field, wear, edge_wear, primer):
    """(bare, primer) masks of chipped paint: `wear` is the share chipped off all over,
    `primer` how far the primer shows around the chips."""
    threshold = amount_to_z(b, b.maximum(wear, 0.002))
    gate = b.clamp01(b.mul(b.add(wear, edge_wear), 25.0))
    bare = b.mul(b.smoothstep(threshold, b.add(threshold, 0.15), field), gate)
    primer_t = b.sub(threshold, b.mul(primer, 0.7))
    under = b.mul(b.smoothstep(primer_t, b.add(primer_t, 0.15), field), gate)
    return bare, under


def stretched_base(b, space, direction, stretch, fallback=True):
    """Object-space coordinates squashed along a surface direction (long features)."""
    t = surface_direction(b, direction, fallback)
    along = b.mul(b.vmath('DOT_PRODUCT', space.P, t), 1.0 - 1.0 / stretch)
    return b.vmath('SUBTRACT', space.P, b.vscale(t, along)), t


def scratch_mask(b, space, amount, scale, offset):
    """Thin, randomly oriented scratch lines.  Returns 0..1."""
    if not is_socket(amount) and amount <= 0.0:
        return 0.0
    # where scratches appear at all (shared by every layer to keep the shader small)
    seg_z = space.znoise(b.mul(scale, 4.0), offset + 10, detail=2.0, roughness=0.5, label='Scratch Patches')
    threshold = amount_to_z(b, b.mul(amount, 0.5))
    patches = b.smoothstep(b.sub(threshold, 0.4), b.add(threshold, 0.4), seg_z)
    mask = scratch_lines(b, space, scale, offset)
    gate = b.clamp01(b.mul(amount, 25.0))
    return b.mul(b.mul(mask, patches), gate)


SCRATCH_LAYERS = (
    # freq, half-width, stretch, strength
    (6.0, 0.011, 45.0, 1.0),
    (11.0, 0.008, 32.0, 0.8),
    (30.0, 0.005, 22.0, 0.45),  # fine hairlines
)
HAIRLINE_LAYERS = (
    (55.0, 0.006, 28.0, 0.8),
    (90.0, 0.005, 22.0, 0.6),
)


def scratch_lines(b, space, scale, offset, direction=None, layers=SCRATCH_LAYERS, first=0):
    """Scratch lines everywhere (0..1): in random directions, or all along `direction`
    (object mode; tiles: along U).  `first` picks other random directions for other layers."""
    mask = None
    for i, (freq, width, stretch, strength) in enumerate(layers):
        k = first + i
        if space.tile:
            n = space.noise(b.mul(scale, freq), offset + i, detail=2.0, roughness=0.5,
                            aniso=(1.0 / stretch, 1.0, 1.0),
                            direction=_SCRATCH_DIRECTIONS[k % 3] if direction is None else 'UV',
                            label='Scratch Lines')
        else:
            if direction is None:
                # random directions are never exactly perpendicular to a face, so no fallback needed
                base, _ = stretched_base(b, space, _rotate_x_axis(_SCRATCH_ROTATIONS[k % 4]), stretch,
                                         fallback=False)
            else:
                base, _ = stretched_base(b, space, direction, stretch)
            n = space.noise(b.mul(scale, freq), offset + i, detail=2.0, roughness=0.5, base=base,
                            label='Scratch Lines')
        line = b.one_minus(b.smoothstep(0.0, width, b.absolute(b.sub(n, 0.5))))
        layer = b.mul(line, strength)
        mask = layer if mask is None else b.maximum(mask, layer)
    return mask


def rust_layer(b, space, scale, color_a, color_b, offset):
    """Rust/patina color, roughness and crust height for a corroded surface."""
    rz = space.znoise(b.mul(scale, 6.0), offset, detail=6.0, roughness=0.6)
    speck = b.smoothstep(1.5, 2.2, space.znoise(b.mul(scale, 28.0), offset + 1, detail=2.0))
    col = b.mix_color(b.smoothstep(-0.8, 1.4, rz), color_b, color_a)
    col = b.mix_color(b.mul(speck, 0.35), col, b.color_scale(color_a, 1.35))
    rough = b.madd(rz, 0.05, 0.82)
    height = b.madd(rz, 0.12, b.madd(speck, 0.2, 0.5))
    return col, rough, height
