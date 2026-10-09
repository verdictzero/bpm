# SPDX-License-Identifier: GPL-3.0-or-later
"""Military paint generator: plain military colors and camouflage schemes, with
edge wear, chips, scratches, rust, mud, dust and grime built in.

Camouflage is up to four colors painted on top of each other.  The shapes of
the patches come from noise; three sliders change their character:

* Stretch turns blotches into stripes (tiger stripes, brush strokes),
* Digital snaps them to square pixels (MARPAT, CADPAT...),
* Angular snaps them to straight-edged shards (splinter camouflage, dazzle).
"""

from . import features as F
from . import gencommon as C
from .nodebuilder import is_socket

PRIMER = (0.26, 0.055, 0.03)
WHITEWASH = (0.72, 0.73, 0.71)
GRIME = (0.028, 0.024, 0.018)

CAMO_PARAMS = [
    # -- Camouflage
    C.color('Color 1', (0.085, 0.095, 0.04), 'Camouflage', 'Base color: everything the other colors leave free',
            key=True),
    C.color('Color 2', (0.10, 0.065, 0.035), 'Camouflage', 'Second color, painted over color 1', key=True),
    C.color('Color 3', (0.015, 0.015, 0.014), 'Camouflage', 'Third color, painted over colors 1 and 2', key=True),
    C.color('Color 4', (0.33, 0.27, 0.16), 'Camouflage', 'Fourth color, painted last', key=True),
    C.fac('Color 2 Amount', 0.0, 'Camouflage', 'Share of the surface in color 2 (0 = none, 0.4 = 40%)'),
    C.fac('Color 3 Amount', 0.0, 'Camouflage', 'Share of the surface in color 3'),
    C.fac('Color 4 Amount', 0.0, 'Camouflage', 'Share of the surface in color 4'),
    C.scale('Camo Scale', 1.0, 0.05, 50.0, 'Camouflage', 'Size of the camouflage patches (higher = smaller)'),
    C.scale('Color 2 Size', 1.0, 0.05, 5.0, 'Camouflage', 'Size of the color 2 patches compared to the others'),
    C.scale('Color 3 Size', 0.8, 0.05, 5.0, 'Camouflage', 'Size of the color 3 patches compared to the others'),
    C.scale('Color 4 Size', 0.6, 0.05, 5.0, 'Camouflage', 'Size of the color 4 patches compared to the others'),
    C.fac('Edge Softness', 0.08, 'Camouflage', '0 = crisp, hard edges; 1 = soft edges sprayed with an airbrush'),
    C.fac('Ragged Edges', 0.35, 'Camouflage', 'Rough, irregular borders between the colors'),
    C.Param('Stretch', 'FLOAT', 1.0, 1.0, 10.0, 'Camouflage',
            'Stretch the patches into stripes: 1 = round blotches, 3 to 5 = tiger stripes'),
    C.axis('Stretch Direction', (0.0, 0.0, 1.0), 'Camouflage', 'Direction the stripes run in'),
    C.fac('Digital', 0.0, 'Camouflage', '1 = square pixels, like digital camouflage (MARPAT, CADPAT)'),
    C.Param('Pixel Size', 'FLOAT', 0.05, 0.002, 1.0, 'Camouflage', 'Size of the digital pixels',
            subtype='DISTANCE'),
    C.fac('Angular', 0.0, 'Camouflage', '1 = straight-edged shards, like splinter camouflage or naval dazzle'),
    # -- Paint
    C.fac('Paint Roughness', 0.72, 'Paint', '0 = glossy, 1 = flat matte (military paint is matte)'),
    C.fac('Color Variation', 0.3, 'Paint', 'Uneven paint: touch-ups and different paint batches'),
    C.fac('Fading', 0.1, 'Paint', 'Sun-bleached, chalky old paint'),
    C.fac('Whitewash', 0.0, 'Paint', 'Winter whitewash brushed over the paint'),
    C.fac('Whitewash Wear', 0.35, 'Paint', 'How much of the whitewash has worn or washed off'),
    # -- Wear
    C.fac('Edge Wear', 0.45, 'Wear', 'Paint chipped off on edges (visible in Cycles and in baked textures)',
          key=True),
    C.Param('Edge Width', 'FLOAT', 0.03, 0.001, 0.3, 'Wear', 'Width of the edge wear', subtype='DISTANCE'),
    C.fac('Chips', 0.02, 'Wear', 'Share of the paint chipped off all over (0.1 = 10%)'),
    C.scale('Chip Scale', 5.0, 0.05, 100.0, 'Wear', 'Chip size (higher = smaller chips)'),
    C.fac('Primer', 0.25, 'Wear', 'Primer showing around the chips'),
    C.color('Primer Color', PRIMER, 'Wear', 'Color of the primer (red oxide, zinc chromate, grey...)'),
    C.fac('Scratches', 0.2, 'Wear', 'Scratches through the paint', key=True),
    C.scale('Scratch Scale', 1.0, 0.05, 20.0, 'Wear', 'Scratch size (higher = smaller, denser)'),
    C.fac('Paint Thickness', 0.5, 'Wear', 'Depth of the chip edges'),
    # -- Metal underneath
    C.color('Metal Color', (0.32, 0.32, 0.31), 'Metal Underneath', 'Bare metal under the paint (dark, worn steel)'),
    C.fac('Metal Roughness', 0.45, 'Metal Underneath', 'Glossiness of the bare metal'),
    C.fac('Rust', 0.25, 'Metal Underneath', 'How much of the bare metal (chips, scratches) has rusted'),
    C.fac('Rust Streaks', 0.0, 'Metal Underneath', 'Rust running down the paint'),
    # -- Dirt
    C.fac('Mud', 0.3, 'Dirt', 'Mud caked on the lower part of the object', key=True),
    C.fac('Mud Height', 0.3, 'Dirt', 'How high the mud reaches (part of the object height)'),
    C.color('Mud Color', (0.10, 0.072, 0.045), 'Dirt', 'Color of the mud'),
    C.fac('Splatter', 0.3, 'Dirt', 'Mud specks thrown up from the ground'),
    C.fac('Wet Mud', 0.0, 'Dirt', 'Fresh, wet mud: darker and glossy'),
    C.fac('Dust', 0.12, 'Dirt', 'Dust settled on top and a dusty film all over', key=True),
    C.color('Dust Color', (0.40, 0.33, 0.23), 'Dirt', 'Color of the dust'),
    C.fac('Grime', 0.4, 'Dirt', 'Dark grime in corners and crevices (Cycles and baked textures)'),
    C.fac('Rain Streaks', 0.1, 'Dirt', 'Dirt running down in streaks'),
] + C.PATTERN_PARAMS


def _camo_space(b, S, I, tile, span):
    """Coordinates for the camouflage shapes: pixelated, stretched and shattered as asked."""
    space = S.pixelated(I['Pixel Size'], I['Digital'], span)
    if tile:
        aniso = (b.div(1.0, I['Stretch']), 1.0)  # tiles: stripes run along U
    else:
        space = space.at(P=F.squashed(b, space.P, I['Stretch Direction'], I['Stretch']))
        aniso = None
    freq = b.mul(I['Camo Scale'], 0.6)
    space = space.shattered(b.mul(freq, 3.5), 60, I['Angular'], aniso=aniso)
    return space, freq, aniso


def build_camo(b, I, gout, tile):
    S = F.Space(b, tile, I['Scale'], I['Seed'], I['Tile Size'] if tile else 1.0)
    inv = b.div(1.0, I['Scale'])
    edge = F.edge_mask(b, S, b.mul(I['Edge Width'], inv))
    cav = F.cavity_mask(b, S, b.mul(inv, 0.3))
    has_geo = is_socket(edge)
    span = b.mul(I['Tile Size'], I['Scale']) if tile else None

    # ---- camouflage: colors 2, 3 and 4 painted over color 1
    CS, freq, aniso = _camo_space(b, S, I, tile, span)
    ragged = I['Ragged Edges']
    rz = CS.znoise(b.mul(freq, 6.0), 64, detail=2.0, roughness=0.6, aniso=aniso, label='Ragged Edges')
    norm = b.power(b.madd(ragged, ragged, 1.0), -0.5)  # keeps the mixed field at ~1 standard deviation
    soft = b.mix(I['Edge Softness'], 0.025, 0.7)
    paint = I['Color 1']
    for k in (2, 3, 4):
        amount = I['Color %d Amount' % k]
        z = CS.znoise(b.div(freq, I['Color %d Size' % k]), 60 + k, detail=3.0, roughness=0.55, aniso=aniso,
                      label='Camo Color %d' % k)
        z = b.mul(b.madd(rz, ragged, z), norm)
        mask = F.cover(b, z, amount, soft)
        paint = b.mix_color(mask, paint, I['Color %d' % k])

    # uneven paint: touch-ups and batches
    vz = S.znoise(1.6, 1, detail=4.0, roughness=0.55, label='Paint Variation')
    gz_ = S.znoise(6.0, 2, detail=4.0, roughness=0.55, label='Gloss Variation')
    variation = I['Color Variation']
    paint = b.color_scale(paint, b.madd(vz, b.mul(variation, 0.08), 1.0))
    p_rough = b.madd(gz_, b.mul(variation, 0.05), I['Paint Roughness'])

    # sun fading
    fz = S.znoise(1.2, 4, detail=3.0, roughness=0.5, label='Fading')
    fade = b.clamp01(b.mul(I['Fading'], b.madd(fz, 0.25, 0.8)))
    faded = b.mix_color(0.25, b.hsv(paint, saturation=0.55, value=1.45), (0.45, 0.43, 0.38))
    paint = b.mix_color(fade, paint, faded)
    p_rough = b.madd(fade, 0.15, p_rough)

    # winter whitewash: brushed on, worn off on edges and in streaks
    ww = I['Whitewash']
    if tile:
        wwz = S.znoise(3.0, 70, detail=4.0, roughness=0.6, aniso=(1.0, 1.0 / 5.0), label='Whitewash Strokes')
    else:
        wwz = S.znoise(3.0, 70, detail=4.0, roughness=0.6, base=F.squashed(b, S.P, (0.0, 0.0, 1.0), 5.0),
                       label='Whitewash Strokes')
    ww_field = b.madd(edge, 2.5, wwz) if has_geo else wwz
    ww_cover = b.one_minus(F.cover(b, ww_field, I['Whitewash Wear'], 0.35, gate=False))
    ww_mask = b.mul(b.mul(ww, ww_cover), b.clamp01(b.madd(wwz, 0.08, 0.92)))
    paint = b.mix_color(ww_mask, paint, b.color_scale(WHITEWASH, b.madd(wwz, 0.03, 1.0)))
    p_rough = b.mix(ww_mask, p_rough, 0.85)

    # ---- chips and scratches through the paint
    field = F.chip_field(b, S, I['Chip Scale'], 0.6, edge, cav, I['Edge Wear'], 5)
    metal, primer = F.chip_layers(b, field, I['Chips'], I['Edge Wear'], I['Primer'])
    scr = F.scratch_mask(b, S, I['Scratches'], I['Scratch Scale'], 20)
    metal = b.maximum(metal, b.smoothstep(0.35, 0.6, scr))
    primer = b.maximum(primer, b.smoothstep(0.1, 0.35, scr))

    zm = S.znoise(10.0, 8, detail=4.0, label='Metal Variation')
    m_col = b.color_scale(I['Metal Color'], b.madd(zm, 0.06, 1.0))
    m_rough = b.madd(zm, 0.04, I['Metal Roughness'])

    # rust on the bare metal and running down
    rust_z = S.znoise(4.0, 9, detail=6.0, roughness=0.6, label='Rust')
    rust = b.mul(metal, F.cover(b, rust_z, I['Rust'], 0.3))
    rust_col, rust_rough, rust_h = F.rust_layer(b, S, 4.0, C.RUST_A, C.RUST_B, 11)
    streak_aniso = (1.0, 1.0 / 14.0) if tile else (1.0, 1.0, 1.0 / 14.0)
    stz = S.znoise(4.0, 13, detail=4.0, roughness=0.6, aniso=streak_aniso, label='Streaks')
    streak_on = F.cover(b, S.znoise(0.8, 14, detail=2.0, label='Streak Mask'), 0.6, 0.8, gate=False)
    rust_streak = b.mul(F.cover(b, stz, b.mul(I['Rust Streaks'], 0.4), 0.5), streak_on)

    # ---- dirt: grime in crevices and streaks, mud from the ground, dust on top
    dz = S.znoise(2.0, 31, detail=5.0, roughness=0.6, label='Dirt Patches')
    fine = S.znoise(18.0, 35, detail=3.0, roughness=0.6, label='Dirt Breakup')
    breakup = b.clamp01(b.madd(fine, 0.18, 0.92))
    grime = I['Grime']
    gmask = b.mul(F.cover(b, dz, b.mul(grime, 0.3), 0.9), 0.5)
    if has_geo:
        packed = b.smoothstep(0.08, 0.75, b.madd(fine, 0.08, b.madd(dz, 0.06, cav)))
        gmask = b.maximum(gmask, b.mul(packed, grime))
    gmask = b.maximum(gmask, b.mul(F.cover(b, stz, b.mul(I['Rain Streaks'], 0.35), 0.45), b.mul(streak_on, 0.7)))
    gmask = b.clamp01(b.mul(gmask, breakup))

    mud_amt = I['Mud']
    spz = S.znoise(45.0, 33, detail=2.0, label='Splatter')
    if has_geo:
        height = b.separate(b.texcoord().outputs['Generated'])[2]
        top = I['Mud Height']
        rim = b.madd(dz, 0.06, b.madd(fine, 0.02, height))  # ragged mud line
        caked = b.one_minus(b.smoothstep(b.sub(top, 0.08), b.add(top, 0.01), rim))
        near_ground = b.one_minus(b.smoothstep(0.0, b.mul(top, 2.0), height))
        mud = b.mul(caked, b.clamp01(b.mul(mud_amt, b.madd(fine, 0.3, 1.7))))
        mud = b.maximum(mud, b.mul(b.mul(cav, near_ground), b.clamp01(b.mul(mud_amt, 1.5))))  # packed in corners
    else:  # tiles have no bottom: patches of mud all over
        near_ground = 0.5
        mud = b.mul(F.cover(b, dz, b.mul(mud_amt, 0.3), 0.5), 0.9)
    splatter = b.mul(F.cover(b, spz, b.mul(I['Splatter'], 0.2), 0.12), near_ground)
    mud = b.clamp01(b.maximum(mud, splatter))
    mz = S.znoise(7.0, 34, detail=4.0, roughness=0.6, label='Mud Lumps')
    wet = I['Wet Mud']
    mud_col = b.mix_color(b.smoothstep(-1.2, 1.4, mz), I['Mud Color'], b.color_scale(I['Mud Color'], 1.5))
    mud_col = b.mix_color(b.mul(b.one_minus(mud), 0.6), mud_col, b.color_scale(I['Mud Color'], 1.8))  # thin = dry
    mud_col = b.color_scale(mud_col, b.madd(wet, -0.45, 1.0))
    mud_rough = b.mix(wet, b.madd(mz, 0.03, 0.9), 0.15)

    if tile:
        facing = 0.4  # tiles have no top: a light film all over
    else:
        facing = b.madd(b.smoothstep(0.05, 0.9, b.separate(b.geometry().outputs['Normal'])[2]), 0.85, 0.15)
    clump = S.znoise(1.2, 42, detail=4.0, roughness=0.55, label='Dust Clumps')
    dust_amt = I['Dust']
    dust = b.mul(b.mul(dust_amt, facing), b.madd(clump, 0.25, b.madd(fine, 0.08, 0.85)))
    if has_geo:
        dust = b.madd(b.mul(cav, dust_amt), 0.6, dust)
    dust = b.clamp01(dust)

    # ---- compose the layers
    color = b.mix_color(primer, paint, I['Primer Color'])
    color = b.mix_color(metal, color, m_col)
    color = b.mix_color(rust, color, rust_col)
    color = b.mix_color(b.mul(rust_streak, 0.55), color, b.mix_color(0.35, C.RUST_B, C.RUST_A))
    color = b.mix_color(gmask, color, b.color_scale(GRIME, b.madd(dz, 0.15, 1.0)))
    color = b.mix_color(mud, color, mud_col)
    color = b.mix_color(dust, color, b.color_scale(I['Dust Color'], b.madd(fine, 0.04, 1.0)))

    metallic = b.mul(metal, b.one_minus(b.maximum(b.maximum(rust, gmask), b.maximum(mud, dust))))

    rough = b.mix(primer, p_rough, 0.65)
    rough = b.mix(metal, rough, m_rough)
    rough = b.mix(rust, rough, rust_rough)
    rough = b.madd(rust_streak, 0.1, rough)
    rough = b.mix(gmask, rough, 0.88)
    rough = b.mix(mud, rough, mud_rough)
    rough = b.mix(dust, rough, 0.95)

    # ---- relief: chipped paint and rust crust; mud covers it (outside the bump: see C.finish)
    layers = b.sub(b.madd(primer, -0.45, 1.0), b.mul(metal, 0.55))
    h_macro = b.madd(b.sub(layers, 0.5), I['Paint Thickness'], 0.5)
    h_macro = b.add(h_macro, b.mul(rust, b.mul(rust_h, 0.3)))
    pz = S.znoise(160.0, 16, detail=2.0, roughness=0.5, label='Paint Texture')
    h_micro = b.madd(scr, -0.6, b.mul(pz, 0.06))

    C.finish(b, gout, I, color, metallic, rough, h_macro, h_micro,
             cover=(b.mul(mud, 0.9), b.madd(mz, 0.05, b.madd(mud, 0.2, 0.5))))


SPEC = dict(
    label='Military Paint', category='MILITARY', params=CAMO_PARAMS, outputs=C.COMMON_OUTPUTS, build=build_camo,
    display=('Color 1', 0.0, 'Paint Roughness'),
)
