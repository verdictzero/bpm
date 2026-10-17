# SPDX-License-Identifier: GPL-3.0-or-later
"""The material library: every preset is a generator plus slider values.

Only values that differ from the generator defaults need to be listed.
Colors are linear RGB (what Blender color pickers store internally).
A material preset can bring overlays (dirt, dust, wear) along; overlay
presets are layered on top of whatever material an object already has.
"""

import math

# (id, label, description, short label for the category buttons, number stored in .blend files)
CATEGORIES = (
    ('METAL', 'Bare Metal', 'Polished, brushed, aged and rusty metals', 'Metal', 1),
    ('PAINT', 'Painted Metal', 'Painted, chipped and weathered metal', 'Painted', 2),
    ('ENAMEL', 'Porcelain Enamel', 'Glassy enamel on steel: 1950s appliances, stoves, bathtubs, enamelware and '
     'signs, from showroom new to chipped, crazed and rusty', 'Enamel', 17),
    ('MILITARY', 'Military', 'Military paint and camouflage with mud, dust and edge wear built in', 'Military', 10),
    ('CONCRETE', 'Concrete', 'Cast, board-formed, polished, slab and block concrete, from fresh to ruined',
     'Concrete', 13),
    ('TERRAIN', 'Terrain & Lava', 'Cratered ground, lunar and asteroid surfaces, molten, crusting and cooled lava',
     'Terrain', 14),
    ('GRADIENT', 'Gradients', 'Linear, radial, angular, diamond, spiral and more: color ramps projected from any '
     'side, on the object, in world space, on UVs or on the screen', 'Gradients', 15),
    ('LIGHT', 'Lights & Neon', 'Glowing neon tubes, fluorescent tubes, light panels, LEDs and screens, clean '
     'or dusty, grimy, bug-filled and burnt out', 'Lights', 18),
    ('WOOD', 'Wood', 'Raw, varnished, painted, weathered and charred wood', 'Wood', 3),
    ('PLASTIC', 'Plastic', 'Glossy, matte, textured, marbled and glitter plastic, new, old, dirty, cracked, '
     'burnt or trashed', 'Plastic', 4),
    ('GLASS', 'Glass', 'Clear, tinted, frosted, textured and stained glass, spotless or grimy', 'Glass', 9),
    ('LENS', 'Lenses & Visors', 'Camera lenses, coated optics, mirrored visors and reflectors: glossy and '
     'reflective, not see-through', 'Lenses', 11),
    ('LEATHER', 'Leather', 'Smooth, pebbled, suede, patent, croc and worn leather', 'Leather', 5),
    ('FABRIC', 'Fabric & Composites', 'Canvas, denim, nylon, carbon fiber, kevlar...', 'Fabric', 6),
    ('ORGANIC', 'Biomechanical', 'Giger-style organic machinery: ribs, tubes, bone, slime', 'Organic', 7),
    ('OVERLAY', 'Dirt, Dust & Moss', 'Layers of dirt, dust, moss or lichen that go on top of any material',
     'Dirt & Moss', 8),
    ('WEAR', 'Edge Wear & Scratches', 'Chipped or rubbed edges, scratches and swirl marks that go on top of any '
     'material', 'Wear', 12),
    ('USER', 'My Presets', 'Materials you saved yourself (Adjust Material > Save Preset)', 'Mine', 16),
)
USER_CATEGORY = 'USER'
OVERLAY_CATEGORIES = ('OVERLAY', 'WEAR')  # presets of these categories go on top of other materials

# generator -> gallery category
GENERATOR_CATEGORY = {
    'METAL': 'METAL', 'PAINT': 'PAINT', 'ENAMEL': 'ENAMEL', 'LIGHT': 'LIGHT', 'CAMO': 'MILITARY', 'CONCRETE': 'CONCRETE', 'TERRAIN': 'TERRAIN',
    'LAVA': 'TERRAIN', 'GRADIENT': 'GRADIENT', 'WOOD': 'WOOD',
    'PLASTIC': 'PLASTIC', 'GLASS': 'GLASS', 'LENS': 'LENS', 'LEATHER': 'LEATHER', 'FABRIC': 'FABRIC',
    'ORGANIC': 'ORGANIC', 'DIRT': 'OVERLAY', 'DUST': 'OVERLAY', 'MOSS': 'OVERLAY', 'WEAR': 'WEAR', 'SCRATCH': 'WEAR',
}

PRESETS = []


def _names(values):
    return {key.replace('_', ' '): value for key, value in values.items()}


def _add(pid, name, generator, desc, overlays=(), thumb=None, **values):
    PRESETS.append(dict(id=pid, name=name, generator=generator, category=GENERATOR_CATEGORY[generator],
                        desc=desc, values=_names(values), overlays=list(overlays), thumb=thumb or {}))


def overlay(generator, **values):
    """An overlay that comes with a material preset: (generator, values)."""
    return (generator, _names(values))


def get(preset_id):
    for preset in PRESETS:
        if preset['id'] == preset_id:
            return preset
    raise KeyError(preset_id)


def find(name_or_id):
    """Look a preset up by id or (case-insensitive) display name."""
    key = name_or_id.strip().lower()
    for preset in PRESETS:
        if preset['id'] == key or preset['name'].lower() == key:
            return preset
    return None


def in_category(preset, category):
    """Your own presets show under 'My Presets' and under the category of their material."""
    if category in {'ALL', preset['category']}:
        return True
    return bool(preset.get('user')) and GENERATOR_CATEGORY.get(preset['generator']) == category


def by_category(category):
    return [p for p in PRESETS if in_category(p, category)]


def is_overlay(preset):
    return preset['category'] in OVERLAY_CATEGORIES


# Reflectance (F0) colors of real metals, linear RGB.
STEEL = (0.56, 0.57, 0.58)
STAINLESS = (0.60, 0.60, 0.59)
CHROME = (0.62, 0.63, 0.64)
ALUMINIUM = (0.91, 0.92, 0.92)
GOLD = (1.0, 0.766, 0.336)
SILVER = (0.972, 0.96, 0.915)
COPPER = (0.955, 0.638, 0.538)
BRASS = (0.91, 0.778, 0.423)
BRONZE = (0.78, 0.52, 0.30)
TITANIUM = (0.542, 0.497, 0.449)
NICKEL = (0.66, 0.61, 0.53)
ZINC = (0.70, 0.73, 0.76)

PATINA_A = (0.20, 0.45, 0.36)
PATINA_B = (0.05, 0.19, 0.14)
RED_OXIDE = (0.26, 0.055, 0.03)
GREY_PRIMER = (0.32, 0.32, 0.30)

# ------------------------------------------------------------------ bare metal
_add('chrome_polished', 'Polished Chrome', 'METAL',
     'Mirror-like chrome plating with faint smudges.',
     Metal_Color=CHROME, Roughness=0.03, Roughness_Variation=0.1, Color_Variation=0.03,
     Scratches=0.06, Scratch_Scale=2.0, Smudges=0.15)
_add('steel_polished', 'Polished Steel', 'METAL',
     'Clean, shiny steel with light scratches.',
     Metal_Color=STEEL, Roughness=0.1, Roughness_Variation=0.25, Color_Variation=0.08, Scratches=0.2)
_add('steel_brushed', 'Brushed Stainless Steel', 'METAL',
     'Kitchen-appliance style brushed stainless steel.',
     Metal_Color=STAINLESS, Roughness=0.28, Brushed=1.0, Scratches=0.1, Roughness_Variation=0.15,
     Color_Variation=0.05)
_add('aluminium_brushed', 'Brushed Aluminium', 'METAL',
     'Bright, finely brushed aluminium.',
     Metal_Color=ALUMINIUM, Roughness=0.32, Brushed=0.9, Brush_Scale=220.0, Scratches=0.12,
     Color_Variation=0.05)
_add('aluminium_sandblasted', 'Sandblasted Aluminium', 'METAL',
     'Matte, bead-blasted aluminium.',
     Metal_Color=(0.88, 0.89, 0.9), Roughness=0.45, Grain=1.0, Pit_Scale=300.0, Roughness_Variation=0.1,
     Scratches=0.05)
_add('aluminium_anodized_blue', 'Anodized Aluminium Blue', 'METAL',
     'Colored anodized aluminium with worn, bare edges.',
     Metal_Color=(0.10, 0.22, 0.65), Roughness=0.3, Brushed=0.35, Scratches=0.1, Edge_Polish=0.6,
     Edge_Color=ALUMINIUM)
_add('aluminium_anodized_red', 'Anodized Aluminium Red', 'METAL',
     'Red anodized aluminium with worn, bare edges.',
     Metal_Color=(0.62, 0.04, 0.05), Roughness=0.28, Brushed=0.3, Scratches=0.1, Edge_Polish=0.6,
     Edge_Color=ALUMINIUM)
_add('aluminium_anodized_black', 'Anodized Aluminium Black', 'METAL',
     'Black anodized aluminium, scuffed down to bare metal on edges.',
     Metal_Color=(0.03, 0.03, 0.035), Roughness=0.35, Edge_Polish=0.8, Scratches=0.25,
     Edge_Color=ALUMINIUM)
_add('gold_polished', 'Polished Gold', 'METAL',
     'Shiny yellow gold.',
     Metal_Color=GOLD, Roughness=0.08, Scratches=0.08, Smudges=0.1, Color_Variation=0.05)
_add('gold_brushed', 'Brushed Gold', 'METAL',
     'Satin brushed gold.',
     Metal_Color=GOLD, Roughness=0.25, Brushed=0.8, Scratches=0.05, Color_Variation=0.05)
_add('silver_tarnished', 'Tarnished Silver', 'METAL',
     'Old silverware: dark tarnish, polished edges.',
     Metal_Color=SILVER, Roughness=0.12, Tarnish=0.6, Tarnish_Color=(0.3, 0.24, 0.16), Edge_Polish=0.9,
     Edge_Color=SILVER, Scratches=0.15)
_add('copper_polished', 'Polished Copper', 'METAL',
     'Freshly polished copper with a hint of oxidation.',
     Metal_Color=COPPER, Roughness=0.1, Tarnish=0.15, Tarnish_Color=(0.55, 0.35, 0.28), Scratches=0.12)
_add('copper_hammered', 'Hammered Copper', 'METAL',
     'Hand-hammered copper, like a cooking pot.',
     Metal_Color=COPPER, Roughness=0.18, Hammered=1.0, Hammer_Scale=9.0, Tarnish=0.25,
     Tarnish_Color=(0.5, 0.32, 0.25))
_add('copper_verdigris', 'Copper Patina (Verdigris)', 'METAL',
     'Weathered copper roof with green patina.',
     Metal_Color=COPPER, Roughness=0.25, Tarnish=0.7, Tarnish_Color=(0.35, 0.2, 0.15), Rust=0.8,
     Rust_Color=PATINA_A, Rust_Color_2=PATINA_B, Rust_Scale=3.0, Dirt=0.2, Edge_Polish=0.3,
     Edge_Color=COPPER)
_add('brass_polished', 'Polished Brass', 'METAL',
     'Bright, polished brass.',
     Metal_Color=BRASS, Roughness=0.08, Scratches=0.1, Smudges=0.1)
_add('brass_aged', 'Aged Brass', 'METAL',
     'Old brass hardware: tarnished, grimy, shiny where touched.',
     Metal_Color=BRASS, Roughness=0.22, Tarnish=0.6, Tarnish_Color=(0.4, 0.32, 0.18), Dirt=0.3,
     Edge_Polish=0.7, Edge_Color=(0.95, 0.83, 0.5), Scratches=0.25)
_add('bronze_antique', 'Antique Bronze', 'METAL',
     'Statue bronze with dark tarnish and green patina spots.',
     Metal_Color=BRONZE, Roughness=0.35, Tarnish=0.7, Tarnish_Color=(0.3, 0.22, 0.13), Rust=0.12,
     Rust_Color=PATINA_A, Rust_Color_2=PATINA_B, Dirt=0.3, Edge_Polish=0.6, Edge_Color=(0.85, 0.6, 0.38))
_add('titanium_heat', 'Heat-Tinted Titanium', 'METAL',
     'Rainbow temper colors, like a titanium exhaust.',
     Metal_Color=TITANIUM, Roughness=0.2, Heat_Tint=1.0, Brushed=0.3)
_add('steel_exhaust', 'Burnt Exhaust Steel', 'METAL',
     'Heat-discolored steel with soot.',
     Metal_Color=STEEL, Roughness=0.35, Heat_Tint=0.6, Heat_Tint_Scale=0.35, Tarnish=0.35,
     Tarnish_Color=(0.25, 0.2, 0.18), Dirt=0.1)
_add('gunmetal', 'Gunmetal', 'METAL',
     'Dark grey metal with worn, shiny edges.',
     Metal_Color=(0.22, 0.23, 0.25), Roughness=0.3, Edge_Polish=0.6, Edge_Color=STEEL, Scratches=0.3)
_add('steel_blued', 'Blued Steel', 'METAL',
     'Gun-blued steel, silver where it is worn.',
     Metal_Color=(0.06, 0.08, 0.14), Roughness=0.18, Edge_Polish=1.0, Edge_Color=(0.6, 0.6, 0.6),
     Scratches=0.35)
_add('iron_cast', 'Cast Iron', 'METAL',
     'Rough, pitted cast iron like a pan or engine block.',
     Metal_Color=(0.18, 0.18, 0.18), Roughness=0.62, Pitting=0.8, Grain=0.9, Pit_Scale=60.0,
     Color_Variation=0.25, Rust=0.06, Dirt=0.2, Scratches=0.1)
_add('iron_wrought', 'Hammered Wrought Iron', 'METAL',
     'Dark, forged iron with hammer marks.',
     Metal_Color=(0.25, 0.25, 0.26), Roughness=0.45, Hammered=0.8, Hammer_Scale=6.0, Tarnish=0.6,
     Tarnish_Color=(0.45, 0.43, 0.42), Edge_Polish=0.7, Edge_Color=(0.5, 0.5, 0.5), Scratches=0.15)
_add('steel_galvanized', 'Galvanized Steel', 'METAL',
     'Hot-dip galvanized steel with crystal spangle.',
     Metal_Color=ZINC, Roughness=0.35, Spangle=1.0, Spangle_Scale=10.0, Dirt=0.2, Scratches=0.1)
_add('zinc_weathered', 'Weathered Zinc', 'METAL',
     'Dull zinc with white corrosion.',
     Metal_Color=(0.60, 0.62, 0.64), Roughness=0.55, Spangle=0.3, Rust=0.35,
     Rust_Color=(0.65, 0.66, 0.64), Rust_Color_2=(0.35, 0.36, 0.36), Rust_Scale=4.0, Dirt=0.3)
_add('steel_rust_light', 'Lightly Rusted Steel', 'METAL',
     'Steel starting to rust in patches.',
     Metal_Color=STEEL, Roughness=0.35, Rust=0.3, Dirt=0.3, Scratches=0.2)
_add('iron_rust_heavy', 'Heavily Rusted Iron', 'METAL',
     'Iron almost completely eaten by rust.',
     Metal_Color=STEEL, Roughness=0.5, Rust=0.85, Rust_Scale=2.5, Pitting=0.4, Dirt=0.4)
_add('steel_corten', 'Weathering Steel (Corten)', 'METAL',
     'Even, stable rust patina of architectural weathering steel.',
     Rust=1.0, Rust_Color=(0.20, 0.065, 0.02), Rust_Color_2=(0.09, 0.03, 0.012), Rust_Scale=4.0,
     Dirt=0.3, Scratches=0.0)
_add('nickel_satin', 'Satin Nickel', 'METAL',
     'Warm satin nickel, like bathroom fittings.',
     Metal_Color=NICKEL, Roughness=0.22, Brushed=0.3, Scratches=0.08)
_add('pewter', 'Pewter', 'METAL',
     'Soft grey pewter with dull tarnish and smudges.',
     Metal_Color=(0.58, 0.58, 0.57), Roughness=0.4, Tarnish=0.5, Tarnish_Color=(0.6, 0.6, 0.6),
     Smudges=0.3, Dirt=0.25)

# -- more metals
PLATINUM = (0.673, 0.637, 0.585)
PALLADIUM = (0.733, 0.697, 0.652)
RHODIUM = (0.79, 0.77, 0.74)
ROSE_GOLD = (0.97, 0.68, 0.56)
WHITE_GOLD = (0.86, 0.83, 0.75)
GOLD_24K = (1.0, 0.71, 0.26)
GOLD_14K = (0.94, 0.79, 0.47)
ELECTRUM = (0.95, 0.87, 0.58)
CHAMPAGNE = (0.86, 0.76, 0.56)
NICKEL_SILVER = (0.76, 0.74, 0.69)
TUNGSTEN = (0.504, 0.498, 0.478)
COBALT = (0.66, 0.65, 0.61)
MAGNESIUM = (0.86, 0.86, 0.85)
LEAD = (0.45, 0.46, 0.48)
TIN = (0.76, 0.76, 0.77)
WHITE_OXIDE = (0.62, 0.63, 0.62)
WHITE_OXIDE_2 = (0.36, 0.37, 0.37)
DARK_TARNISH = (0.06, 0.05, 0.045)
COPPER_BROWN = (0.16, 0.07, 0.045)
# precious
_add('platinum_polished', 'Polished Platinum', 'METAL',
     'Cool, heavy white metal of fine jewellery, mirror polished.',
     Metal_Color=PLATINUM, Roughness=0.05, Scratches=0.08, Smudges=0.08, Color_Variation=0.03)
_add('platinum_brushed', 'Brushed Platinum', 'METAL',
     'Satin brushed platinum, like a watch case.',
     Metal_Color=PLATINUM, Roughness=0.24, Brushed=0.9, Brush_Scale=300.0, Scratches=0.06, Color_Variation=0.04)
_add('palladium', 'Palladium', 'METAL',
     'Bright, slightly warm white metal, lighter than platinum.',
     Metal_Color=PALLADIUM, Roughness=0.09, Scratches=0.1, Color_Variation=0.04)
_add('rhodium_plated', 'Rhodium Plating', 'METAL',
     'Very bright, hard white plating used on jewellery and white gold.',
     Metal_Color=RHODIUM, Roughness=0.03, Scratches=0.04, Color_Variation=0.02)
_add('gold_rose', 'Rose Gold', 'METAL',
     'Pink copper-gold alloy, polished.',
     Metal_Color=ROSE_GOLD, Roughness=0.08, Scratches=0.08, Smudges=0.08, Color_Variation=0.04)
_add('gold_rose_brushed', 'Brushed Rose Gold', 'METAL',
     'Satin rose gold, like a phone or a watch.',
     Metal_Color=ROSE_GOLD, Roughness=0.26, Brushed=0.85, Brush_Scale=260.0, Scratches=0.05)
_add('gold_white', 'White Gold', 'METAL',
     'Pale, warm white gold, polished.',
     Metal_Color=WHITE_GOLD, Roughness=0.07, Scratches=0.08, Smudges=0.08)
_add('gold_24k', '24 Karat Gold', 'METAL',
     'Pure, deep orange-yellow gold: soft, so it is covered in fine scratches.',
     Metal_Color=GOLD_24K, Roughness=0.1, Scratches=0.35, Scratch_Scale=3.0, Color_Variation=0.06)
_add('gold_14k', '14 Karat Gold', 'METAL',
     'Paler, harder yellow gold of everyday jewellery.',
     Metal_Color=GOLD_14K, Roughness=0.08, Scratches=0.12, Smudges=0.06)
_add('gold_leaf', 'Gold Leaf', 'METAL',
     'Hand-laid gold leaf: crinkled, uneven and slightly broken up.',
     Metal_Color=GOLD, Roughness=0.2, Roughness_Variation=0.6, Color_Variation=0.35, Variation_Scale=8.0,
     Hammered=0.35, Hammer_Scale=30.0, Grain=0.3, Pit_Scale=400.0, Scratches=0.0)
_add('gold_antique', 'Antique Gold', 'METAL',
     'Old gilded metal: dark tarnish in the crevices, bright on the edges.',
     Metal_Color=(0.86, 0.62, 0.28), Roughness=0.3, Tarnish=0.65, Tarnish_Color=(0.25, 0.16, 0.06),
     Edge_Polish=0.8, Edge_Color=GOLD, Dirt=0.3, Scratches=0.2)
_add('gold_satin', 'Satin Gold', 'METAL',
     'Soft-glow bead-blasted gold.',
     Metal_Color=GOLD, Roughness=0.38, Grain=0.8, Pit_Scale=500.0, Scratches=0.03)
_add('silver_polished', 'Polished Sterling Silver', 'METAL',
     'Bright, freshly polished silver.',
     Metal_Color=SILVER, Roughness=0.05, Scratches=0.1, Smudges=0.1, Tarnish=0.05,
     Tarnish_Color=(0.6, 0.55, 0.45))
_add('silver_brushed', 'Brushed Silver', 'METAL',
     'Satin brushed silver.',
     Metal_Color=SILVER, Roughness=0.25, Brushed=0.85, Scratches=0.06)
_add('silver_oxidized', 'Oxidized Silver', 'METAL',
     'Blackened silver jewellery, polished bright only on the high points.',
     Metal_Color=SILVER, Roughness=0.2, Tarnish=1.0, Tarnish_Color=DARK_TARNISH, Tarnish_Scale=1.5,
     Edge_Polish=1.0, Edge_Color=SILVER, Edge_Width=0.05, Scratches=0.2)
_add('electrum', 'Electrum', 'METAL',
     'Pale greenish gold-silver alloy of ancient coins.',
     Metal_Color=ELECTRUM, Roughness=0.22, Hammered=0.3, Hammer_Scale=12.0, Tarnish=0.3,
     Tarnish_Color=(0.4, 0.33, 0.18), Scratches=0.2)
# copper, brass, bronze
_add('copper_brushed', 'Brushed Copper', 'METAL',
     'Satin brushed copper sheet.',
     Metal_Color=(0.93, 0.56, 0.42), Roughness=0.26, Brushed=0.9, Scratches=0.08, Tarnish=0.1,
     Tarnish_Color=(0.55, 0.35, 0.28))
_add('copper_aged_brown', 'Aged Copper (Brown)', 'METAL',
     'Copper a few years outdoors: dark chocolate brown before it turns green.',
     Metal_Color=(0.42, 0.2, 0.12), Roughness=0.4, Tarnish=0.95, Tarnish_Color=COPPER_BROWN, Tarnish_Scale=2.0,
     Color_Variation=0.3, Dirt=0.2, Scratches=0.05)
_add('copper_pipe', 'Copper Pipe', 'METAL',
     'Plumbing copper: dull, slightly tarnished, fingerprinted.',
     Metal_Color=(0.9, 0.5, 0.36), Roughness=0.3, Tarnish=0.35, Tarnish_Color=(0.45, 0.25, 0.18), Smudges=0.3,
     Scratches=0.15, Brushed=0.2)
_add('copper_antique', 'Antique Copper', 'METAL',
     'Darkened copper with bright worn edges, like an old kettle.',
     Metal_Color=(0.5, 0.25, 0.15), Roughness=0.3, Tarnish=0.8, Tarnish_Color=(0.2, 0.09, 0.05), Edge_Polish=0.9,
     Edge_Color=COPPER, Dirt=0.25, Scratches=0.2)
_add('copper_heat', 'Flame-Painted Copper', 'METAL',
     'Copper torched into reds, purples and blues.',
     Metal_Color=COPPER, Roughness=0.18, Heat_Tint=0.9, Heat_Tint_Scale=0.7, Tarnish=0.2,
     Tarnish_Color=(0.5, 0.25, 0.2))
_add('copper_verdigris_heavy', 'Heavy Verdigris', 'METAL',
     'Copper fully turned to chalky green, a little brown copper showing through.',
     Metal_Color=COPPER, Roughness=0.3, Tarnish=0.8, Tarnish_Color=COPPER_BROWN, Rust=1.0,
     Rust_Color=PATINA_A, Rust_Color_2=PATINA_B, Rust_Scale=5.0, Dirt=0.3)
_add('brass_brushed', 'Brushed Brass', 'METAL',
     'Satin brushed brass, like modern hardware.',
     Metal_Color=BRASS, Roughness=0.25, Brushed=0.9, Scratches=0.06)
_add('brass_champagne', 'Champagne Brass', 'METAL',
     'Pale, soft satin brass of modern fixtures.',
     Metal_Color=CHAMPAGNE, Roughness=0.3, Brushed=0.5, Grain=0.3, Scratches=0.04)
_add('brass_lacquered', 'Lacquered Brass', 'METAL',
     'Mirror-bright lacquered brass of a musical instrument.',
     Metal_Color=BRASS, Roughness=0.04, Smudges=0.25, Scratches=0.05)
_add('brass_casing', 'Brass Shell Casing', 'METAL',
     'Cartridge brass: warm, slightly uneven, tarnished in spots.',
     Metal_Color=(0.93, 0.74, 0.40), Roughness=0.16, Color_Variation=0.2, Tarnish=0.3,
     Tarnish_Color=(0.45, 0.3, 0.15), Tarnish_Scale=6.0, Scratches=0.15)
_add('brass_patina', 'Brass with Patina', 'METAL',
     'Weathered brass: dull, brown and spotted with green.',
     Metal_Color=BRASS, Roughness=0.4, Tarnish=0.75, Tarnish_Color=(0.3, 0.22, 0.1), Rust=0.3,
     Rust_Color=PATINA_A, Rust_Color_2=PATINA_B, Rust_Scale=6.0, Dirt=0.3)
_add('bronze_polished', 'Polished Bronze', 'METAL',
     'Freshly polished warm bronze.',
     Metal_Color=BRONZE, Roughness=0.1, Scratches=0.12, Color_Variation=0.06)
_add('bronze_oil_rubbed', 'Oil-Rubbed Bronze', 'METAL',
     'Very dark brown bronze of door hardware, with copper showing on the edges.',
     Metal_Color=(0.12, 0.07, 0.04), Roughness=0.32, Edge_Polish=0.8, Edge_Color=(0.72, 0.42, 0.24),
     Scratches=0.15, Color_Variation=0.2)
_add('bronze_verdigris', 'Statue Bronze (Verdigris)', 'METAL',
     'Outdoor statue: green patina streaked over dark bronze.',
     Metal_Color=BRONZE, Roughness=0.4, Tarnish=0.85, Tarnish_Color=(0.2, 0.13, 0.07), Rust=0.7,
     Rust_Color=PATINA_A, Rust_Color_2=PATINA_B, Rust_Scale=2.5, Dirt=0.3, Edge_Polish=0.3,
     Edge_Color=BRONZE)
_add('bronze_bell', 'Bell Bronze', 'METAL',
     'Cast bell metal: pale golden bronze with a fine cast grain.',
     Metal_Color=(0.82, 0.62, 0.38), Roughness=0.3, Grain=0.5, Pit_Scale=200.0, Tarnish=0.4,
     Tarnish_Color=(0.3, 0.2, 0.1), Scratches=0.1)
_add('nickel_polished', 'Polished Nickel', 'METAL',
     'Warm, bright nickel plating.',
     Metal_Color=NICKEL, Roughness=0.06, Scratches=0.08, Smudges=0.1)
_add('nickel_silver', 'Nickel Silver', 'METAL',
     'Silvery copper-nickel-zinc alloy of keys and instruments.',
     Metal_Color=NICKEL_SILVER, Roughness=0.16, Tarnish=0.2, Tarnish_Color=(0.35, 0.33, 0.25), Scratches=0.2)
# steel and iron
_add('steel_mirror', 'Mirror Stainless Steel', 'METAL',
     'Mirror-polished stainless steel.',
     Metal_Color=STAINLESS, Roughness=0.02, Scratches=0.05, Smudges=0.1, Color_Variation=0.02)
_add('steel_mill_scale', 'Hot-Rolled Steel (Mill Scale)', 'METAL',
     'Raw hot-rolled plate: blotchy blue-grey mill scale with spots of rust.',
     Metal_Color=(0.13, 0.14, 0.16), Roughness=0.45, Roughness_Variation=0.5, Color_Variation=0.45,
     Variation_Scale=1.5, Tarnish=0.4, Tarnish_Color=(0.2, 0.2, 0.22), Rust=0.1, Scratches=0.25)
_add('steel_cold_rolled', 'Cold-Rolled Steel', 'METAL',
     'Smooth, slightly hazy sheet steel straight from the mill.',
     Metal_Color=(0.50, 0.51, 0.52), Roughness=0.22, Roughness_Variation=0.35, Color_Variation=0.15,
     Smudges=0.2, Scratches=0.15)
_add('steel_machined', 'Machined Steel', 'METAL',
     'Freshly machined tool steel with fine tool marks.',
     Metal_Color=STEEL, Roughness=0.16, Brushed=0.6, Brush_Scale=400.0, Scratches=0.08, Color_Variation=0.04)
_add('steel_sandblasted', 'Sandblasted Steel', 'METAL',
     'Matte grey blasted steel, ready for paint.',
     Metal_Color=(0.48, 0.49, 0.5), Roughness=0.55, Grain=1.0, Pit_Scale=350.0, Scratches=0.03)
_add('steel_case_hardened', 'Case-Hardened Steel', 'METAL',
     'Mottled blues, browns and straw colors of a case-hardened gun receiver.',
     Metal_Color=STEEL, Roughness=0.12, Heat_Tint=1.0, Heat_Tint_Scale=2.5, Color_Variation=0.3,
     Variation_Scale=6.0, Scratches=0.1)
_add('steel_weld_heat', 'Heat-Affected Steel', 'METAL',
     'Stainless steel tinted straw and blue by welding heat.',
     Metal_Color=STAINLESS, Roughness=0.25, Heat_Tint=0.7, Heat_Tint_Scale=0.9, Brushed=0.5, Scratches=0.1)
_add('steel_parkerized', 'Parkerized Steel', 'METAL',
     'Dark grey, finely grainy phosphate finish of military hardware.',
     Metal_Color=(0.085, 0.09, 0.09), Roughness=0.68, Grain=1.0, Pit_Scale=500.0, Edge_Polish=0.4,
     Edge_Color=(0.4, 0.4, 0.4), Scratches=0.15)
_add('steel_scratched', 'Scratched Sheet Steel', 'METAL',
     'Steel sheet covered in scuffs and scratches from heavy use.',
     Metal_Color=STEEL, Roughness=0.3, Scratches=0.85, Scratch_Scale=1.5, Smudges=0.2, Dirt=0.2)
_add('steel_tea_stained', 'Tea-Stained Stainless', 'METAL',
     'Stainless steel by the sea: light brown rust staining on a dull finish.',
     Metal_Color=STAINLESS, Roughness=0.3, Brushed=0.6, Rust=0.18, Rust_Color=(0.35, 0.17, 0.07),
     Rust_Color_2=(0.2, 0.1, 0.05), Rust_Scale=5.0, Dirt=0.25)
_add('steel_ship_hull', 'Rusting Ship Steel', 'METAL',
     'Heavy plate steel bleeding rust in streaks and blooms.',
     Metal_Color=(0.3, 0.31, 0.32), Roughness=0.5, Rust=0.6, Rust_Scale=1.8, Pitting=0.3, Dirt=0.4,
     Scratches=0.2)
_add('iron_forged_black', 'Black Forged Iron', 'METAL',
     'Blacksmith iron: black scale, hammer marks, polished high points.',
     Metal_Color=(0.07, 0.07, 0.075), Roughness=0.5, Hammered=0.9, Hammer_Scale=5.0, Color_Variation=0.3,
     Edge_Polish=0.6, Edge_Color=(0.45, 0.45, 0.45), Scratches=0.1)
_add('iron_rusty_nail', 'Rusty Iron', 'METAL',
     'Old iron: orange rust in patches, dark iron between.',
     Metal_Color=(0.25, 0.25, 0.26), Roughness=0.55, Rust=0.55, Rust_Scale=4.0, Pitting=0.5, Pit_Scale=80.0,
     Dirt=0.3)
_add('iron_meteorite', 'Meteorite Iron', 'METAL',
     'Cut and polished iron-nickel meteorite: grainy, mottled and pitted.',
     Metal_Color=(0.52, 0.52, 0.5), Roughness=0.2, Color_Variation=0.5, Variation_Scale=12.0, Grain=0.6,
     Pitting=0.4, Pit_Scale=90.0, Tarnish=0.3, Tarnish_Color=(0.3, 0.25, 0.2))
# chrome
_add('chrome_satin', 'Satin Chrome', 'METAL',
     'Soft, brushed chrome of modern taps.',
     Metal_Color=CHROME, Roughness=0.2, Brushed=0.7, Scratches=0.05)
_add('chrome_black', 'Black Chrome', 'METAL',
     'Smoky dark mirror chrome.',
     Metal_Color=(0.17, 0.17, 0.18), Roughness=0.04, Scratches=0.08, Smudges=0.15)
_add('chrome_worn', 'Pitted Old Chrome', 'METAL',
     'Old car bumper chrome: pitted, scratched and spotted with rust.',
     Metal_Color=CHROME, Roughness=0.08, Pitting=0.5, Pit_Scale=200.0, Rust=0.2, Rust_Scale=8.0,
     Scratches=0.45, Dirt=0.25)
# other metals
_add('tungsten', 'Tungsten', 'METAL',
     'Dense, dark grey tungsten carbide, polished.',
     Metal_Color=TUNGSTEN, Roughness=0.08, Scratches=0.04, Color_Variation=0.03)
_add('cobalt', 'Cobalt Chrome', 'METAL',
     'Bright, hard cobalt-chrome alloy, slightly warm.',
     Metal_Color=COBALT, Roughness=0.1, Scratches=0.08)
_add('magnesium', 'Magnesium', 'METAL',
     'Light, matte magnesium casting with a dull oxide film.',
     Metal_Color=MAGNESIUM, Roughness=0.42, Grain=0.6, Tarnish=0.35, Tarnish_Color=(0.55, 0.55, 0.53),
     Scratches=0.1)
_add('lead_weathered', 'Weathered Lead', 'METAL',
     'Soft, dull lead flashing with white oxide bloom.',
     Metal_Color=LEAD, Roughness=0.55, Hammered=0.25, Hammer_Scale=4.0, Rust=0.35,
     Rust_Color=WHITE_OXIDE, Rust_Color_2=WHITE_OXIDE_2, Rust_Scale=3.0, Dirt=0.2, Scratches=0.1)
_add('tin', 'Tin', 'METAL',
     'Soft, satin silver-grey tin.',
     Metal_Color=TIN, Roughness=0.3, Color_Variation=0.1, Scratches=0.15)
_add('tinplate', 'Tinplate', 'METAL',
     'Shiny tin-coated steel of old cans and toys, faintly crystalline.',
     Metal_Color=TIN, Roughness=0.12, Spangle=0.2, Spangle_Scale=20.0, Scratches=0.12, Smudges=0.1)
_add('zinc_plated', 'Zinc Plating', 'METAL',
     'Bright blue-white zinc plating of screws and brackets.',
     Metal_Color=ZINC, Roughness=0.2, Color_Variation=0.08, Scratches=0.1)
_add('zinc_yellow', 'Yellow Zinc Chromate', 'METAL',
     'Gold-green iridescent passivated zinc of bolts and brackets.',
     Metal_Color=(0.78, 0.66, 0.30), Roughness=0.2, Heat_Tint=0.45, Heat_Tint_Scale=3.0,
     Color_Variation=0.25, Variation_Scale=5.0, Scratches=0.08)
_add('bismuth', 'Bismuth Crystal', 'METAL',
     'Iridescent oxide colors of a bismuth crystal.',
     Metal_Color=(0.65, 0.6, 0.62), Roughness=0.12, Heat_Tint=1.0, Heat_Tint_Scale=1.6, Scratches=0.0)
# aluminium
_add('aluminium_polished', 'Polished Aluminium', 'METAL',
     'Bright mirror-polished aluminium.',
     Metal_Color=ALUMINIUM, Roughness=0.05, Scratches=0.1, Smudges=0.1)
_add('aluminium_cast', 'Cast Aluminium', 'METAL',
     'Grainy, matte sand-cast aluminium.',
     Metal_Color=(0.8, 0.81, 0.82), Roughness=0.5, Grain=1.0, Pitting=0.3, Pit_Scale=120.0,
     Color_Variation=0.15, Dirt=0.2)
_add('aluminium_oxidized', 'Oxidized Aluminium', 'METAL',
     'Old aluminium: dull, with white powdery corrosion.',
     Metal_Color=(0.7, 0.71, 0.72), Roughness=0.5, Rust=0.4, Rust_Color=(0.75, 0.75, 0.74),
     Rust_Color_2=(0.45, 0.45, 0.45), Rust_Scale=5.0, Pitting=0.3, Dirt=0.3)
_add('aluminium_machined', 'Machined Aluminium', 'METAL',
     'Freshly milled aluminium with fine tool marks.',
     Metal_Color=ALUMINIUM, Roughness=0.18, Brushed=0.6, Brush_Scale=500.0, Scratches=0.05)
for _key, _name, _color in (('gold', 'Gold', (0.75, 0.48, 0.10)), ('green', 'Green', (0.06, 0.40, 0.10)),
                            ('purple', 'Purple', (0.30, 0.06, 0.55)), ('orange', 'Orange', (0.85, 0.25, 0.03)),
                            ('teal', 'Teal', (0.03, 0.42, 0.45)), ('pink', 'Pink', (0.85, 0.22, 0.42)),
                            ('champagne', 'Champagne', CHAMPAGNE), ('titanium', 'Grey', (0.32, 0.33, 0.35))):
    _add('aluminium_anodized_' + _key, 'Anodized Aluminium ' + _name, 'METAL',
         '%s anodized aluminium with worn, bare edges.' % _name,
         Metal_Color=_color, Roughness=0.3, Brushed=0.35, Scratches=0.1, Edge_Polish=0.6, Edge_Color=ALUMINIUM)
del _key, _name, _color
# titanium
_add('titanium_brushed', 'Brushed Titanium', 'METAL',
     'Warm grey satin titanium.',
     Metal_Color=TITANIUM, Roughness=0.28, Brushed=0.9, Scratches=0.06)
_add('titanium_bead', 'Bead-Blasted Titanium', 'METAL',
     'Soft matte grey titanium of watch cases and tools.',
     Metal_Color=TITANIUM, Roughness=0.48, Grain=1.0, Pit_Scale=450.0, Scratches=0.04)
_add('titanium_anodized_blue', 'Anodized Titanium Blue', 'METAL',
     'Deep electric blue anodized titanium.',
     Metal_Color=(0.10, 0.22, 0.75), Roughness=0.18, Heat_Tint=0.2, Heat_Tint_Scale=1.0, Scratches=0.06,
     Edge_Polish=0.3, Edge_Color=TITANIUM)
_add('titanium_anodized_purple', 'Anodized Titanium Purple', 'METAL',
     'Purple anodized titanium.',
     Metal_Color=(0.42, 0.12, 0.62), Roughness=0.18, Heat_Tint=0.2, Heat_Tint_Scale=1.0, Scratches=0.06,
     Edge_Polish=0.3, Edge_Color=TITANIUM)
_add('titanium_anodized_gold', 'Anodized Titanium Gold', 'METAL',
     'Gold anodized titanium.',
     Metal_Color=(0.85, 0.62, 0.22), Roughness=0.18, Heat_Tint=0.2, Heat_Tint_Scale=1.0, Scratches=0.06,
     Edge_Polish=0.3, Edge_Color=TITANIUM)

# --------------------------------------------------------------- painted metal
_add('paint_industrial_yellow', 'Chipped Industrial Yellow', 'PAINT',
     'Machinery yellow, chipped on the edges, a bit rusty.',
     Paint_Color=(0.75, 0.45, 0.0), Paint_Roughness=0.42, Wear=0.08, Edge_Wear=0.85, Primer=0.3,
     Rust=0.35, Dirt=0.45, Scratches=0.3)
_add('paint_military_olive', 'Military Olive Drab', 'PAINT',
     'Matte olive drab, worn and dusty.',
     Paint_Color=(0.085, 0.095, 0.04), Paint_Roughness=0.7, Wear=0.05, Edge_Wear=0.8, Primer=0.0,
     Dirt=0.55, Scratches=0.4, Rust=0.15)
_add('paint_desert_tan', 'Desert Tan Armor', 'PAINT',
     'Sandy military tan, dusty and scuffed.',
     Paint_Color=(0.42, 0.31, 0.17), Paint_Roughness=0.72, Wear=0.04, Edge_Wear=0.7, Primer=0.0,
     Dirt=0.6, Dirt_Color=(0.18, 0.13, 0.08), Scratches=0.35, Rust=0.05)
_add('paint_fire_red', 'Worn Fire-Engine Red', 'PAINT',
     'Glossy red paint with grey primer showing through.',
     Paint_Color=(0.55, 0.015, 0.01), Paint_Roughness=0.3, Wear=0.04, Edge_Wear=0.7, Primer=0.5,
     Scratches=0.25, Rust=0.1, Dirt=0.2)
_add('paint_car_blue', 'Metallic Car Paint Blue', 'PAINT',
     'Showroom-new metallic blue with clear coat.',
     Paint_Color=(0.02, 0.07, 0.35), Paint_Roughness=0.25, Paint_Metallic=0.55, Flakes=0.8,
     Clear_Coat=1.0, Orange_Peel=0.15, Paint_Variation=0.05, Wear=0.0, Edge_Wear=0.0, Scratches=0.0,
     Rust=0.0, Dirt=0.0)
_add('paint_car_red', 'Candy Red Car Paint', 'PAINT',
     'Deep red metallic paint with clear coat.',
     Paint_Color=(0.45, 0.01, 0.015), Paint_Roughness=0.2, Paint_Metallic=0.6, Flakes=0.8,
     Clear_Coat=1.0, Orange_Peel=0.15, Paint_Variation=0.05, Wear=0.0, Edge_Wear=0.0, Scratches=0.0,
     Rust=0.0, Dirt=0.0)
_add('paint_powder_black', 'Black Powder Coat', 'PAINT',
     'Textured black powder coating, lightly scuffed.',
     Paint_Color=(0.02, 0.02, 0.021), Paint_Roughness=0.5, Orange_Peel=0.8, Wear=0.01, Edge_Wear=0.3,
     Primer=0.0, Scratches=0.05, Rust=0.0, Dirt=0.15)
_add('paint_hammertone_green', 'Hammertone Green', 'PAINT',
     'Classic hammered-finish machine paint.',
     Paint_Color=(0.025, 0.13, 0.07), Paint_Metallic=0.55, Hammered=1.0, Paint_Roughness=0.3,
     Wear=0.01, Edge_Wear=0.35, Primer=0.0, Rust=0.1, Dirt=0.2,
     Scratches=0.05)

_add('paint_hammertone_silver', 'Hammertone Silver', 'PAINT',
     'Silver hammered-finish paint.',
     Paint_Color=(0.35, 0.36, 0.37), Paint_Metallic=0.7, Hammered=1.0, Paint_Roughness=0.3,
     Wear=0.01, Edge_Wear=0.35, Primer=0.0, Rust=0.05, Dirt=0.2,
     Scratches=0.05)

_add('paint_peeling_teal', 'Peeling Teal (Rusty)', 'PAINT',
     'Old teal paint peeling off rusty metal.',
     Paint_Color=(0.05, 0.25, 0.25), Wear=0.45, Edge_Wear=0.9, Primer=0.0, Rust=0.85, Rust_Spread=0.5,
     Rust_Streaks=0.4, Fading=0.55, Dirt=0.4)
_add('paint_ship_grey', 'Ship Hull Grey', 'PAINT',
     'Navy grey with red primer and rust streaks.',
     Paint_Color=(0.16, 0.18, 0.19), Paint_Roughness=0.5, Wear=0.06, Edge_Wear=0.6, Primer=0.4,
     Primer_Color=RED_OXIDE, Rust=0.6, Rust_Spread=0.4, Rust_Streaks=0.8, Dirt=0.3)
_add('paint_hazard_stripes', 'Hazard Stripes', 'PAINT',
     'Yellow and black warning stripes, worn.',
     Paint_Color=(0.78, 0.52, 0.0), Stripes=1.0, Stripe_Color=(0.015, 0.015, 0.015), Stripe_Width=0.1,
     Wear=0.07, Edge_Wear=0.8, Rust=0.25, Dirt=0.35, Scratches=0.3)
_add('paint_scifi_white', 'Sci-Fi White Panel', 'PAINT',
     'Clean white hull paint with scuffed edges.',
     Paint_Color=(0.78, 0.78, 0.76), Paint_Roughness=0.35, Wear=0.02, Edge_Wear=0.7, Primer=0.6,
     Rust=0.0, Dirt=0.35, Dirt_Color=(0.06, 0.06, 0.06), Scratches=0.2, Metal_Color=(0.91, 0.92, 0.92),
     Metal_Roughness=0.3)
_add('paint_safety_orange', 'Safety Orange', 'PAINT',
     'High-visibility orange, lightly worn.',
     Paint_Color=(0.85, 0.18, 0.0), Paint_Roughness=0.4, Wear=0.03, Edge_Wear=0.6, Primer=0.3,
     Rust=0.2, Dirt=0.3)
_add('paint_faded_blue', 'Sun-Faded Blue', 'PAINT',
     'Chalky, sun-bleached blue paint.',
     Paint_Color=(0.03, 0.12, 0.42), Fading=0.75, Paint_Roughness=0.55, Wear=0.08, Edge_Wear=0.7,
     Rust=0.3, Dirt=0.25)
_add('paint_cream_enamel', 'Vintage Cream Enamel', 'PAINT',
     'Glossy cream enamel chipped down to dark iron.',
     Paint_Color=(0.68, 0.6, 0.42), Paint_Roughness=0.18, Wear=0.03, Edge_Wear=0.6, Primer=0.0,
     Metal_Color=(0.18, 0.18, 0.18), Rust=0.5, Rust_Spread=0.3, Dirt=0.3)
_add('paint_matte_black_worn', 'Worn Matte Black', 'PAINT',
     'Black finish rubbed through to bright steel on every edge.',
     Paint_Color=(0.018, 0.018, 0.018), Paint_Roughness=0.55, Wear=0.02, Edge_Wear=1.0, Primer=0.0,
     Scratches=0.5, Rust=0.0, Dirt=0.1, Metal_Color=(0.6, 0.6, 0.6), Metal_Roughness=0.25)
_add('paint_tractor_green', 'Old Tractor Green', 'PAINT',
     'Faded farm-machine green with rust breaking through.',
     Paint_Color=(0.04, 0.22, 0.05), Paint_Roughness=0.45, Wear=0.15, Edge_Wear=0.8, Primer=0.3,
     Rust=0.6, Rust_Spread=0.4, Rust_Streaks=0.3, Fading=0.4, Dirt=0.5)
_add('paint_mint_vintage', 'Vintage Mint Green', 'PAINT',
     'Retro mint paint, chipped and a little rusty.',
     Paint_Color=(0.32, 0.58, 0.42), Paint_Roughness=0.3, Wear=0.08, Edge_Wear=0.7, Primer=0.0,
     Rust=0.5, Dirt=0.3, Fading=0.3)
_add('paint_navy_machinery', 'Navy Blue Machinery', 'PAINT',
     'Dark blue machine paint, oily and worn.',
     Paint_Color=(0.015, 0.03, 0.12), Paint_Roughness=0.4, Wear=0.05, Edge_Wear=0.8, Primer=0.4,
     Rust=0.3, Dirt=0.5)
_add('paint_red_primer', 'Red Oxide Primer', 'PAINT',
     'Bare red primer coat with light rust.',
     Paint_Color=(0.22, 0.045, 0.025), Paint_Roughness=0.75, Wear=0.06, Edge_Wear=0.6, Primer=0.0,
     Rust=0.4, Dirt=0.3)
_add('paint_rusted_through', 'Rusted-Through Paint', 'PAINT',
     'Grey paint that has mostly lost the fight against rust.',
     Paint_Color=(0.35, 0.33, 0.30), Wear=0.6, Edge_Wear=1.0, Primer=0.2, Rust=1.0, Rust_Spread=0.8,
     Rust_Streaks=0.6, Fading=0.4, Dirt=0.5)

# ------------------------------------------------------------------ tractor paints
# Glossy farm-machine enamels over cast iron, each from showroom new to a rusty relic in the field.
MUD = (0.055, 0.038, 0.022)
MUD_2 = (0.12, 0.085, 0.05)
FIELD_DUST = (0.36, 0.30, 0.22)
TRACTOR_STATES = (
    ('new', 'New', 'Showroom-new, deep glossy enamel',
     dict(Paint_Roughness=0.14, Orange_Peel=0.25, Paint_Variation=0.05, Wear=0.0, Edge_Wear=0.04,
          Scratches=0.02, Rust=0.0, Rust_Spread=0.0, Dirt=0.05), ()),
    ('worked', 'Working', 'Hard at work: glossy but scratched, chipped on the edges and muddy low down',
     dict(Paint_Roughness=0.3, Wear=0.02, Edge_Wear=0.55, Primer=0.2, Scratches=0.35, Rust=0.25,
          Rust_Spread=0.1, Dirt=0.5, Dirt_Color=MUD),
     (('DIRT', dict(Amount=0.65, Ground_Grime=0.85, Grime_Height=0.35, Splatter=0.6, Streaks=0.3,
                    Patches=0.2, Wetness=0.2, Dirt_Color=MUD, Dirt_Color_2=MUD_2)),)),
    ('faded', 'Sun-Faded', 'Decades in the sun: chalky, faded paint, worn edges and light rust',
     dict(Fading=0.4, Paint_Roughness=0.55, Wear=0.06, Edge_Wear=0.75, Primer=0.3, Scratches=0.3,
          Rust=0.45, Rust_Spread=0.3, Rust_Streaks=0.2, Dirt=0.35),
     (('DUST', dict(Amount=0.15, Dust_Color=FIELD_DUST)),)),
    ('barn', 'Barn Find', 'Parked in a barn for years: flaking paint, rust streaks and a thick coat of dust',
     dict(Fading=0.3, Paint_Roughness=0.55, Wear=0.25, Edge_Wear=0.95, Primer=0.35, Primer_Color=RED_OXIDE,
          Scratches=0.4, Rust=0.8, Rust_Spread=0.55, Rust_Streaks=0.5, Dirt=0.6),
     (('DUST', dict(Amount=0.35, Clumps=0.5, Dust_Color=FIELD_DUST)),)),
    ('relic', 'Field Relic', 'Left out in the field: mostly rust, the paint hanging on in patches, moss on top',
     dict(Fading=0.7, Paint_Roughness=0.7, Wear=0.55, Edge_Wear=1.0, Primer=0.2, Scratches=0.3, Rust=1.0,
          Rust_Spread=0.8, Rust_Streaks=0.7, Rust_Scale=3.0, Dirt=0.6),
     (('MOSS', dict(Amount=0.35, Patchiness=0.75, Side_Reach=0.2, Lichen=0.3, Dryness=0.25)),)),
)
TRACTOR_COLORS = (
    ('green', 'Tractor Green', (0.037, 0.202, 0.024), 'classic farm green'),
    ('yellow', 'Tractor Yellow', (0.86, 0.52, 0.0), 'wheel and stripe yellow'),
    ('red', 'Tractor Red', (0.462, 0.006, 0.011), 'classic tractor red'),
    ('orange', 'Tractor Orange', (0.807, 0.175, 0.004), 'bright tractor orange'),
    ('blue', 'Tractor Blue', (0.012, 0.078, 0.332), 'deep tractor blue'),
    ('grey', 'Tractor Grey', (0.254, 0.266, 0.275), 'light grey of the little grey tractors'),
    ('cream', 'Tractor Cream', (0.70, 0.60, 0.37), 'cream wheel and grille paint'),
    ('lime', 'Tractor Light Green', (0.114, 0.323, 0.023), 'lighter, yellowish tractor green'),
)
for _key, _name, _color, _what in TRACTOR_COLORS:
    for _state, _label, _desc, _values, _overlays in TRACTOR_STATES:
        _add('tractor_%s_%s' % (_key, _state), '%s (%s)' % (_name, _label), 'PAINT',
             '%s. %s.' % (_what[0].upper() + _what[1:], _desc),
             overlays=[overlay(g, **v) for g, v in _overlays], Paint_Color=_color,
             Metal_Color=(0.2, 0.2, 0.21), Metal_Roughness=0.5, **_values)
del _key, _name, _color, _what, _state, _label, _desc, _values, _overlays

# ------------------------------------------------------------------ porcelain enamel
ENAMEL_THUMB = dict(zoom=0.6)
WARE_THUMB = dict(shape='cylinder', zoom=0.4)  # pots, mugs and bowls
SIGN_THUMB = dict(shape='panel', zoom=0.6)
CLEAN = dict(Chips=0.0, Edge_Chips=0.0, Dirt=0.0, Scratches=0.03)  # showroom new


def _fridge(pid, name, color, desc, **values):
    vals = dict(CLEAN, Enamel_Color=color, Roughness=0.05, Depth=0.9, Waviness=0.35, Orange_Peel=0.25)
    vals.update(values)
    _add(pid, name, 'ENAMEL', desc, thumb=ENAMEL_THUMB, **vals)


_fridge('enamel_fridge_turquoise', 'Turquoise Fridge', (0.10, 0.52, 0.47),
        'The glossy turquoise of a 1950s refrigerator, fresh from the showroom.')
_fridge('enamel_fridge_seafoam', 'Seafoam Green Fridge', (0.42, 0.66, 0.50),
        'Pale mint-green 1950s kitchen appliance enamel.')
_fridge('enamel_fridge_pink', 'Pastel Pink Fridge', (0.80, 0.42, 0.46),
        'The famous pink of a 1950s kitchen.')
_fridge('enamel_fridge_yellow', 'Canary Yellow Fridge', (0.88, 0.70, 0.16),
        'Cheerful pastel yellow appliance enamel.')
_fridge('enamel_fridge_cream', 'Butter Cream Fridge', (0.78, 0.70, 0.48),
        'Warm cream enamel of a rounded vintage fridge.')
_fridge('enamel_fridge_white', 'Appliance White', (0.82, 0.82, 0.78),
        'Clean, glossy white kitchen appliance enamel.')
_fridge('enamel_fridge_red', 'Cherry Red Fridge', (0.55, 0.018, 0.020),
        'Glossy candy red, like a retro diner fridge or cooler.', Depth=1.0)
_fridge('enamel_fridge_coppertone', 'Coppertone', (0.30, 0.12, 0.045),
        'Brown-bronze 1960s appliance color.', Color_Variation=0.12)
_fridge('enamel_fridge_harvest_gold', 'Harvest Gold', (0.56, 0.34, 0.045),
        'The mustard gold of 1970s kitchen appliances.')
_fridge('enamel_fridge_avocado', 'Avocado Green', (0.20, 0.22, 0.035),
        'The olive green of 1970s kitchen appliances.')
_fridge('enamel_fridge_worn', 'Worn Turquoise Fridge', (0.10, 0.52, 0.47),
        'Decades of use: yellowed, chipped on the corners, grimy around the handle.',
        Edge_Chips=0.45, Chips=0.01, Yellowing=0.3, Scratches=0.25, Dulling=0.3, Dirt=0.35, Rust=0.7,
        Rust_Stains=0.2, Grease=0.15)
_fridge('enamel_fridge_barn_find', 'Barn-Find Fridge', (0.42, 0.66, 0.50),
        'Left in a barn for forty years: chalky, rust-stained, chipped and filthy.',
        Roughness=0.25, Depth=0.4, Edge_Chips=0.8, Chips=0.06, Chip_Scale=5.0, Chalking=0.6, Yellowing=0.4,
        Rust=1.0, Rust_Stains=0.7, Scratches=0.4, Dulling=0.6, Dirt=0.7, Crazing=0.2)

_add('enamel_stove_white', 'Greasy Stove Top', 'ENAMEL',
     'White enamel range: grey pot marks, burnt-on grease and a few chips.',
     thumb=ENAMEL_THUMB, Enamel_Color=(0.80, 0.79, 0.75), Grease=0.6, Scratches=0.55, Dulling=0.4,
     Edge_Chips=0.35, Chips=0.015, Dirt=0.4, Rust=0.8)
_add('enamel_stove_black', 'Black Enameled Grate', 'ENAMEL',
     'Satin black enamel on cast iron, like a stove grate or burner cap.',
     thumb=ENAMEL_THUMB, Enamel_Color=(0.012, 0.012, 0.013), Roughness=0.3, Depth=0.4, Orange_Peel=0.5,
     Waviness=0.6, Scratches=0.4, Edge_Chips=0.3, Grease=0.4, Dirt=0.3)
_add('enamel_tub', 'Cast Iron Bathtub', 'ENAMEL',
     'Old white bathtub enamel with rust stains running from the chips.',
     thumb=dict(shape='sphere'), Enamel_Color=(0.80, 0.80, 0.76), Waviness=0.5, Chips=0.02, Edge_Chips=0.4,
     Rust=1.0, Rust_Stains=0.7, Dulling=0.45, Yellowing=0.15, Dirt=0.25)
_add('enamel_tub_clawfoot', 'Antique Clawfoot Tub', 'ENAMEL',
     'A century-old tub: crazed all over, yellowed, dull and stained.',
     thumb=dict(shape='sphere'), Enamel_Color=(0.78, 0.76, 0.68), Roughness=0.12, Crazing=0.8, Craze_Scale=12.0,
     Yellowing=0.45, Dulling=0.6, Chips=0.015, Edge_Chips=0.4, Rust_Stains=0.4, Dirt=0.45)
_add('enamel_sink', 'Vintage Farmhouse Sink', 'ENAMEL',
     'White enamel sink, scratched grey by pots, a little chipped and crazed.',
     thumb=ENAMEL_THUMB, Enamel_Color=(0.81, 0.80, 0.76), Scratches=0.6, Dulling=0.5, Crazing=0.3,
     Edge_Chips=0.4, Rust_Stains=0.25, Dirt=0.3)

_add('enamel_ware_blue_granite', 'Blue Graniteware', 'ENAMEL',
     'Speckled blue camping enamelware with a dark rim.',
     thumb=WARE_THUMB, Enamel_Color=(0.03, 0.08, 0.30), Speckles=0.55, Speckle_Scale=90.0, Rim=1.0,
     Rim_Color=(0.006, 0.010, 0.035), Edge_Chips=0.4, Chips=0.01, Scratches=0.2, Dirt=0.1)
_add('enamel_ware_black_granite', 'Black Graniteware', 'ENAMEL',
     'Black enamel speckled with white, like an old roasting pan.',
     thumb=WARE_THUMB, Enamel_Color=(0.015, 0.015, 0.018), Speckles=0.5, Speckle_Scale=110.0,
     Edge_Chips=0.35, Scratches=0.25, Grease=0.2, Dirt=0.2)
_add('enamel_mug_white', 'White Enamel Mug', 'ENAMEL',
     'Classic white enamel mug with a navy-blue rim.',
     thumb=WARE_THUMB, Enamel_Color=(0.82, 0.82, 0.79), Rim=1.0, Rim_Color=(0.008, 0.015, 0.06),
     Rim_Width=0.004, Edge_Chips=0.15, Scratches=0.08)
_add('enamel_mug_chipped', 'Chipped Camping Mug', 'ENAMEL',
     'A well-traveled camping mug: chipped to rusty steel, stained and scratched.',
     thumb=WARE_THUMB, Enamel_Color=(0.03, 0.17, 0.08), Speckles=0.35, Rim=1.0, Rim_Color=(0.01, 0.01, 0.01),
     Chips=0.05, Chip_Scale=6.0, Edge_Chips=0.8, Rust=1.0, Rust_Stains=0.4, Scratches=0.4, Dulling=0.4,
     Dirt=0.4)
_add('enamel_ware_agate_red', 'Red Agateware', 'ENAMEL',
     'Swirled red and white marbled enamel.',
     thumb=WARE_THUMB, Enamel_Color=(0.50, 0.030, 0.025), Marbling=0.6, Marble_Color=(0.80, 0.78, 0.74),
     Marble_Scale=4.0, Edge_Chips=0.25, Scratches=0.1)
_add('enamel_ware_agate_blue', 'Blue Swirl Enamelware', 'ENAMEL',
     'Cloudy blue and white swirled enamel, like an antique coffee pot.',
     thumb=WARE_THUMB, Enamel_Color=(0.70, 0.72, 0.76), Marbling=0.6, Marble_Color=(0.03, 0.08, 0.28),
     Marble_Scale=3.0, Edge_Chips=0.4, Chips=0.02, Crazing=0.2, Yellowing=0.15, Dirt=0.25)
_add('enamel_cast_iron_orange', 'Enameled Cast Iron', 'ENAMEL',
     'Flame-orange enameled cast iron cookware, glossy and thick.',
     thumb=WARE_THUMB, Enamel_Color=(0.72, 0.13, 0.008), Depth=1.0, Waviness=0.6, Color_Variation=0.15,
     Edge_Chips=0.1, Scratches=0.1, Ground_Coat_Color=(0.02, 0.018, 0.016))

_add('enamel_sign_red', 'Red Enamel Sign', 'ENAMEL',
     'Glossy red porcelain enamel sign with a white rim and chipped edges.',
     thumb=SIGN_THUMB, Enamel_Color=(0.52, 0.020, 0.018), Rim=1.0, Rim_Color=(0.80, 0.80, 0.76),
     Rim_Width=0.01, Edge_Chips=0.4, Chips=0.01, Rust_Stains=0.2)
_add('enamel_sign_weathered', 'Weathered Enamel Sign', 'ENAMEL',
     'An old gas-station sign: chalky, shot through with chips and rust streaks.',
     thumb=SIGN_THUMB, Enamel_Color=(0.04, 0.10, 0.40), Rim=1.0, Rim_Color=(0.80, 0.78, 0.70), Rim_Width=0.01,
     Chalking=0.55, Chips=0.08, Chip_Scale=5.0, Edge_Chips=0.9, Rust=1.0, Rust_Stains=0.8, Dirt=0.5,
     Dulling=0.4)
_add('enamel_sign_street', 'Cobalt Street Sign', 'ENAMEL',
     'Deep cobalt blue enamel street sign, a little crazed.',
     thumb=SIGN_THUMB, Enamel_Color=(0.010, 0.04, 0.22), Rim=1.0, Rim_Color=(0.82, 0.82, 0.80),
     Rim_Width=0.008, Crazing=0.3, Edge_Chips=0.3, Rust_Stains=0.15, Dirt=0.2)
_add('enamel_crazed_antique', 'Crazed Antique Enamel', 'ENAMEL',
     'Cream enamel with a fine dirty craze network all over.',
     thumb=dict(zoom=0.3), Enamel_Color=(0.72, 0.64, 0.45), Crazing=1.0, Craze_Scale=25.0, Yellowing=0.4,
     Dulling=0.4, Dirt=0.5, Edge_Chips=0.3)

# -------------------------------------------------------------------- military
OLIVE_DRAB = (0.085, 0.095, 0.04)
NATO_GREEN = (0.055, 0.075, 0.04)
NATO_BROWN = (0.075, 0.045, 0.025)
NATO_BLACK = (0.012, 0.012, 0.012)
DARK_YELLOW = (0.44, 0.33, 0.14)  # German "Dunkelgelb"
OLIVE_GREEN = (0.065, 0.08, 0.035)
RED_BROWN = (0.10, 0.04, 0.025)
TAN = (0.45, 0.35, 0.21)
SAND_DUST = (0.48, 0.38, 0.24)
SOVIET_GREEN = (0.07, 0.10, 0.035)
ZINC_CHROMATE = (0.30, 0.34, 0.09)

_add('mil_olive_drab', 'Olive Drab', 'CAMO',
     'Classic matte olive drab: worn edges, mud low down.',
     Color_1=OLIVE_DRAB, Edge_Wear=0.5, Chips=0.02, Mud=0.35, Dust=0.15, Scratches=0.25, Rust=0.3)
_add('mil_nato_green', 'NATO Green', 'CAMO',
     'Modern flat NATO green, lightly used.',
     Color_1=NATO_GREEN, Paint_Roughness=0.78, Edge_Wear=0.35, Chips=0.01, Mud=0.25, Dust=0.1, Primer=0.1,
     Primer_Color=(0.15, 0.15, 0.14))
_add('mil_desert_tan', 'Desert Tan', 'CAMO',
     'Sand-colored paint, sun-faded and covered in fine desert dust.',
     Color_1=TAN, Fading=0.3, Edge_Wear=0.5, Chips=0.02, Mud=0.0, Splatter=0.0, Dust=0.45, Dust_Color=SAND_DUST,
     Grime=0.25, Rust=0.15)
_add('mil_panzer_grey', 'Panzer Grey', 'CAMO',
     'Dark grey with red oxide primer showing through the chips.',
     Color_1=(0.028, 0.032, 0.035), Edge_Wear=0.65, Chips=0.03, Primer=0.4, Mud=0.4, Dust=0.15, Rust=0.35,
     Scratches=0.3)
_add('mil_soviet_green', 'Soviet Green', 'CAMO',
     'Bright cold-war green, thick paint, muddy tracks.',
     Color_1=SOVIET_GREEN, Paint_Roughness=0.6, Edge_Wear=0.5, Mud=0.6, Splatter=0.5, Mud_Height=0.35, Dust=0.1)
_add('mil_navy_grey', 'Navy Haze Grey', 'CAMO',
     'Warship grey: salty, rust streaks running down.',
     Color_1=(0.22, 0.24, 0.25), Paint_Roughness=0.55, Edge_Wear=0.5, Chips=0.03, Primer=0.3, Rust=0.6,
     Rust_Streaks=0.6, Mud=0.0, Splatter=0.0, Dust=0.0, Grime=0.3, Rain_Streaks=0.35)
_add('mil_nato_3tone', 'NATO Three-Tone', 'CAMO',
     'Green, brown and black hard-edged camouflage of Cold War NATO vehicles.',
     Color_1=NATO_GREEN, Color_2=NATO_BROWN, Color_3=NATO_BLACK, Color_2_Amount=0.38, Color_3_Amount=0.17,
     Color_3_Size=0.9, Edge_Softness=0.03, Ragged_Edges=0.25, Mud=0.3, Dust=0.1)
_add('mil_woodland', 'Woodland Camo', 'CAMO',
     'Four-color woodland camouflage: green, brown, black and khaki.',
     Color_1=(0.15, 0.17, 0.075), Color_2=(0.11, 0.065, 0.035), Color_3=NATO_BLACK, Color_4=(0.36, 0.28, 0.15),
     Color_2_Amount=0.4, Color_3_Amount=0.15, Color_4_Amount=0.1, Color_3_Size=0.75, Color_4_Size=0.5,
     Edge_Softness=0.05)
_add('mil_ambush', 'WWII Ambush Camo', 'CAMO',
     'Dark yellow with soft sprayed green and red-brown, dotted with yellow.',
     Color_1=DARK_YELLOW, Color_2=OLIVE_GREEN, Color_3=RED_BROWN, Color_4=DARK_YELLOW, Color_2_Amount=0.32,
     Color_3_Amount=0.22, Color_4_Amount=0.05, Color_4_Size=0.08, Edge_Softness=0.6, Fading=0.15,
     Edge_Wear=0.6, Primer=0.35, Rust=0.3, Mud=0.4)
_add('mil_tiger', 'Tiger Stripes', 'CAMO',
     'Long sprayed stripes of green and brown over dark yellow.',
     Color_1=DARK_YELLOW, Color_2=OLIVE_GREEN, Color_3=RED_BROWN, Color_2_Amount=0.3, Color_3_Amount=0.15,
     Stretch=4.0, Edge_Softness=0.4, Ragged_Edges=0.5, Mud=0.35, Edge_Wear=0.5)
_add('mil_desert_3color', 'Desert Three-Color', 'CAMO',
     'Soft-edged desert camouflage in tan, light brown and dark brown.',
     Color_1=TAN, Color_2=(0.26, 0.17, 0.09), Color_3=(0.10, 0.065, 0.04), Color_2_Amount=0.35,
     Color_3_Amount=0.15, Edge_Softness=0.5, Dust=0.35, Dust_Color=SAND_DUST, Mud=0.0, Splatter=0.0, Fading=0.2)
_add('mil_digital_woodland', 'Digital Woodland', 'CAMO',
     'Pixelated woodland camouflage, like MARPAT.',
     Color_1=(0.30, 0.26, 0.17), Color_2=(0.09, 0.11, 0.05), Color_3=(0.16, 0.10, 0.055), Color_4=(0.02, 0.02, 0.018),
     Color_2_Amount=0.35, Color_3_Amount=0.25, Color_4_Amount=0.08, Color_4_Size=0.5, Digital=1.0,
     Edge_Softness=0.0, Ragged_Edges=0.5, Mud=0.3)
_add('mil_digital_desert', 'Digital Desert', 'CAMO',
     'Pixelated desert camouflage in tan, khaki and brown.',
     Color_1=(0.45, 0.37, 0.24), Color_2=(0.33, 0.27, 0.17), Color_3=(0.25, 0.17, 0.09), Color_4=(0.10, 0.07, 0.045),
     Color_2_Amount=0.35, Color_3_Amount=0.2, Color_4_Amount=0.06, Color_4_Size=0.5, Digital=1.0,
     Edge_Softness=0.0, Ragged_Edges=0.5, Dust=0.3, Dust_Color=SAND_DUST, Mud=0.0, Splatter=0.0)
_add('mil_urban', 'Urban Camo', 'CAMO',
     'City camouflage in greys, black and white.',
     Color_1=(0.42, 0.42, 0.41), Color_2=(0.17, 0.17, 0.17), Color_3=(0.05, 0.05, 0.05), Color_4=(0.75, 0.75, 0.74),
     Color_2_Amount=0.35, Color_3_Amount=0.18, Color_4_Amount=0.1, Edge_Softness=0.03, Mud=0.15,
     Dust_Color=(0.3, 0.3, 0.29), Grime=0.5)
_add('mil_splinter', 'Splinter Camo', 'CAMO',
     'Straight-edged shards of green and brown on tan.',
     Color_1=(0.22, 0.19, 0.11), Color_2=(0.06, 0.08, 0.04), Color_3=(0.12, 0.07, 0.04), Color_2_Amount=0.35,
     Color_3_Amount=0.25, Angular=1.0, Stretch=1.6, Stretch_Direction=(1.0, 0.0, 0.0), Ragged_Edges=0.0,
     Edge_Softness=0.0)
_add('mil_dazzle', 'Naval Dazzle', 'CAMO',
     'Bold geometric warship camouflage, salty and rust-streaked.',
     Color_1=(0.40, 0.42, 0.43), Color_2=(0.02, 0.03, 0.06), Color_3=(0.015, 0.015, 0.015), Color_4=(0.10, 0.11,
     0.12),
     Color_2_Amount=0.35, Color_3_Amount=0.15, Color_4_Amount=0.2, Angular=1.0, Camo_Scale=0.45,
     Ragged_Edges=0.0, Edge_Softness=0.0, Paint_Roughness=0.55, Rust=0.5, Rust_Streaks=0.5, Mud=0.0,
     Splatter=0.0, Dust=0.0, Rain_Streaks=0.3)
_add('mil_winter_whitewash', 'Winter Whitewash', 'CAMO',
     'Temporary white winter paint brushed over green and washing off.',
     Color_1=OLIVE_DRAB, Whitewash=1.0, Whitewash_Wear=0.4, Mud=0.45, Wet_Mud=0.5, Edge_Wear=0.5, Dust=0.0)
_add('mil_arctic', 'Arctic Camo', 'CAMO',
     'White camouflage with grey and black patches.',
     Color_1=(0.72, 0.73, 0.72), Color_2=(0.30, 0.31, 0.31), Color_3=(0.03, 0.03, 0.03), Color_2_Amount=0.3,
     Color_3_Amount=0.12, Edge_Softness=0.05, Mud=0.2, Dust=0.0, Grime=0.3, Primer=0.2,
     Primer_Color=(0.15, 0.15, 0.14))
_add('mil_ghost_grey', 'Ghost Grey Aircraft', 'CAMO',
     'Two soft-edged greys of a modern fighter jet, panel lines grimy.',
     Color_1=(0.24, 0.26, 0.28), Color_2=(0.12, 0.135, 0.155), Color_2_Amount=0.45, Camo_Scale=0.6,
     Edge_Softness=0.7, Paint_Roughness=0.55, Color_Variation=0.15, Mud=0.0, Splatter=0.0, Dust=0.0,
     Grime=0.35, Rain_Streaks=0.2, Edge_Wear=0.25, Chips=0.005, Primer=0.5, Primer_Color=ZINC_CHROMATE,
     Metal_Color=(0.91, 0.92, 0.92), Metal_Roughness=0.3, Rust=0.0, Scratches=0.1)
_add('mil_soviet_3tone', 'Soviet Three-Tone', 'CAMO',
     'Green, sand and dark brown camouflage with hard edges.',
     Color_1=SOVIET_GREEN, Color_2=(0.34, 0.26, 0.11), Color_3=(0.06, 0.04, 0.025), Color_2_Amount=0.3,
     Color_3_Amount=0.2, Edge_Softness=0.04, Mud=0.45, Splatter=0.4)
_add('mil_battle_worn', 'Battle-Worn Olive', 'CAMO',
     'Olive drab beaten down to primer and rusty steel, caked in mud.',
     Color_1=OLIVE_DRAB, Edge_Wear=1.0, Chips=0.15, Primer=0.4, Rust=0.7, Rust_Streaks=0.5, Mud=0.65,
     Splatter=0.6, Mud_Height=0.35, Dust=0.25, Scratches=0.6, Fading=0.4, Grime=0.6)
_add('mil_muddy_woodland', 'Muddy Woodland', 'CAMO',
     'Woodland camouflage fresh from the field: wet mud up the sides.',
     Color_1=(0.15, 0.17, 0.075), Color_2=(0.11, 0.065, 0.035), Color_3=NATO_BLACK, Color_4=(0.36, 0.28, 0.15),
     Color_2_Amount=0.4, Color_3_Amount=0.15, Color_4_Amount=0.1, Color_3_Size=0.75, Color_4_Size=0.5,
     Edge_Softness=0.05, Mud=0.9, Wet_Mud=0.6, Mud_Height=0.45, Splatter=0.8, Dust=0.0)

# ---------------------------------------------------------------------- concrete
CONCRETE_THUMB = dict(zoom=0.5)

_add('concrete_fresh', 'Fresh Concrete', 'CONCRETE',
     'Clean, new cast concrete with a few air holes.',
     thumb=CONCRETE_THUMB, Dirt=0.1, Water_Stains=0.0, Cracks=0.0, Chipped_Edges=0.05)
_add('concrete_precast', 'Smooth Precast Panel', 'CONCRETE',
     'Smooth, light factory-made concrete panel.',
     thumb=CONCRETE_THUMB, Concrete_Color=(0.52, 0.51, 0.48), Color_Variation=0.2, Roughness=0.75, Pores=0.15,
     Aggregate=0.0, Sand=0.3,
     Dirt=0.15, Water_Stains=0.1, Cracks=0.0, Chipped_Edges=0.1)
_add('concrete_white', 'White Architectural Concrete', 'CONCRETE',
     'Bright white concrete of modern architecture.',
     thumb=CONCRETE_THUMB, Concrete_Color=(0.66, 0.65, 0.62), Color_Variation=0.15, Pores=0.25, Aggregate=0.0,
     Sand=0.3, Dirt=0.05,
     Water_Stains=0.05, Cracks=0.0, Chipped_Edges=0.05)
_add('concrete_board_formed', 'Board-Formed Concrete', 'CONCRETE',
     'Concrete cast against wooden boards: wood grain and seams in the surface.',
     thumb=CONCRETE_THUMB, Board_Formed=1.0, Dirt=0.2, Water_Stains=0.25)
_add('concrete_brutalist', 'Brutalist Wall', 'CONCRETE',
     'Big formwork panels with tie holes, streaked by decades of rain.',
     thumb=CONCRETE_THUMB, Concrete_Color=(0.36, 0.35, 0.33), Form_Panels=1.0, Water_Stains=0.7, Dirt=0.4,
     Rust_Stains=0.2,
     Efflorescence=0.15, Cracks=0.15)
_add('concrete_polished', 'Polished Concrete Floor', 'CONCRETE',
     'Ground and polished floor with cut stones, glossy.',
     thumb=CONCRETE_THUMB, Polish=1.0, Aggregate=0.6, Aggregate_Size=0.02, Roughness=0.15, Joints=1.0,
     Joint_Spacing=3.0, Dirt=0.05,
     Water_Stains=0.0, Cracks=0.05, Chipped_Edges=0.05, Pores=0.1)
_add('concrete_exposed_aggregate', 'Exposed Aggregate', 'CONCRETE',
     'Washed concrete with the pebbles showing.',
     thumb=CONCRETE_THUMB, Aggregate=0.9, Erosion=0.3, Aggregate_Color=(0.36, 0.30, 0.22), Aggregate_Size=0.025,
     Dirt=0.2)
_add('concrete_sidewalk', 'Sidewalk Slabs', 'CONCRETE',
     'Broomed sidewalk with cut joints, a little cracked, moss in the joints.',
     thumb=CONCRETE_THUMB, Broom_Finish=0.8, Joints=1.0, Joint_Spacing=1.5, Dirt=0.35, Cracks=0.15, Moss=0.15,
     Oil_Stains=0.05,
     Water_Stains=0.1)
_add('concrete_blocks', 'Concrete Block Wall', 'CONCRETE',
     'Grey concrete blocks with mortar joints.',
     thumb=CONCRETE_THUMB, Blocks=1.0, Concrete_Color=(0.45, 0.44, 0.42), Pores=0.6, Sand=0.8, Aggregate=0.3,
     Aggregate_Size=0.006,
     Dirt=0.2, Water_Stains=0.2)
_add('concrete_weathered', 'Weathered Concrete', 'CONCRETE',
     'Old concrete: washed out, stained, cracked and chipped.',
     thumb=CONCRETE_THUMB, Concrete_Color=(0.34, 0.33, 0.31), Erosion=0.5, Water_Stains=0.6, Dirt=0.5, Moss=0.2,
     Cracks=0.3,
     Chipped_Edges=0.5)
_add('concrete_cracked', 'Cracked Concrete', 'CONCRETE',
     'A web of cracks with white salt bleeding out.',
     thumb=CONCRETE_THUMB, Cracks=0.8, Crack_Scale=1.5, Efflorescence=0.3, Dirt=0.3, Water_Stains=0.3)
_add('concrete_spalled', 'Spalled Concrete with Rebar', 'CONCRETE',
     'Chunks broken off down to the rusty reinforcing bars, rust running down.',
     thumb=CONCRETE_THUMB, Spalling=0.6, Rebar=1.0, Rust_Stains=0.7, Cracks=0.4, Chipped_Edges=0.7, Dirt=0.4,
     Water_Stains=0.4)
_add('concrete_ruined', 'Ruined Concrete', 'CONCRETE',
     'Shattered, burnt and broken: rebar, craters and soot everywhere.',
     thumb=CONCRETE_THUMB, Spalling=0.9, Rebar=1.0, Impacts=0.6, Chipped_Edges=1.0, Cracks=0.8, Soot=0.4, Dirt=0.6,
     Rust_Stains=0.6,
     Erosion=0.3)
_add('concrete_bullet_holes', 'Bullet-Riddled Wall', 'CONCRETE',
     'War-damaged wall full of impact craters.',
     thumb=CONCRETE_THUMB, Impacts=1.0, Chipped_Edges=0.6, Spalling=0.2, Soot=0.1, Dirt=0.3, Water_Stains=0.3)
_add('concrete_bunker', 'Military Bunker', 'CONCRETE',
     'Cold, damp bunker concrete: board marks, moss, rust and chipped edges.',
     thumb=CONCRETE_THUMB, Concrete_Color=(0.30, 0.31, 0.28), Board_Formed=0.5, Moss=0.3, Water_Stains=0.6,
     Dirt=0.5, Cracks=0.3,
     Chipped_Edges=0.6, Rust_Stains=0.3, Spalling=0.15, Rebar=0.6)
_add('concrete_mossy', 'Mossy Concrete', 'CONCRETE',
     'Damp, shady concrete overgrown with moss and algae.',
     thumb=CONCRETE_THUMB, Moss=0.7, Water_Stains=0.6, Dirt=0.4, Erosion=0.3, Cracks=0.3)
_add('concrete_salt', 'Salt-Stained Concrete', 'CONCRETE',
     'White efflorescence streaks and patches from water seeping through.',
     thumb=CONCRETE_THUMB, Efflorescence=0.7, Water_Stains=0.5, Cracks=0.4)
_add('concrete_garage', 'Garage Floor', 'CONCRETE',
     'Smooth floor slab with oil stains, tire grime and cracks.',
     thumb=CONCRETE_THUMB, Oil_Stains=0.6, Joints=0.8, Joint_Spacing=4.0, Dirt=0.4, Roughness=0.7, Polish=0.15,
     Cracks=0.2,
     Water_Stains=0.0)
_add('concrete_wet', 'Wet Concrete', 'CONCRETE',
     'Rain-soaked concrete: dark and shiny.',
     thumb=CONCRETE_THUMB, Wetness=0.8, Water_Stains=0.4, Dirt=0.3)
_add('concrete_burnt', 'Fire-Damaged Concrete', 'CONCRETE',
     'Blackened by fire, spalled and cracked by the heat.',
     thumb=CONCRETE_THUMB, Soot=0.9, Spalling=0.4, Cracks=0.5, Chipped_Edges=0.5, Rebar=0.4)
_add('concrete_underpass', 'Dirty Underpass', 'CONCRETE',
     'Grimy, damp underpass walls with rust and salt streaks.',
     thumb=CONCRETE_THUMB, Concrete_Color=(0.30, 0.29, 0.27), Dirt=0.8, Water_Stains=0.8, Rust_Stains=0.4,
     Efflorescence=0.3,
     Cracks=0.3, Moss=0.1)
_add('concrete_bridge', 'Bridge Pier', 'CONCRETE',
     'Massive pier concrete: rust streaks, damp low down, rebar showing.',
     thumb=CONCRETE_THUMB, Form_Panels=0.6, Rust_Stains=0.6, Water_Stains=0.7, Moss=0.3, Efflorescence=0.3,
     Spalling=0.2, Rebar=0.8)


TERRAIN_THUMB = dict(shape='sphere', zoom=3.0)  # a moon-sized look: many craters
GROUND_THUMB = dict(shape='sphere')  # close-up ground
LAVA_THUMB = GROUND_THUMB

_add('terrain_lunar_highlands', 'Lunar Highlands', 'TERRAIN',
     'Bright, heavily cratered lunar highlands: craters on craters, worn down by age.',
     thumb=TERRAIN_THUMB, Ground_Color=(0.21, 0.205, 0.20), Craters=0.95, Small_Craters=1.0, Crater_Age=0.6,
     Hills=0.6, Ejecta=0.4, Rays=0.1, Boulders=0.15)
_add('terrain_lunar_mare', 'Lunar Mare', 'TERRAIN',
     'Dark, smooth lava plains of the lunar seas with fewer, smaller craters.',
     thumb=TERRAIN_THUMB, Ground_Color=(0.075, 0.073, 0.07), Craters=0.4, Small_Craters=0.8, Hills=0.1,
     Crater_Age=0.5, Ejecta=0.7, Rays=0.0, Boulders=0.1)
_add('terrain_lunar_surface', 'Lunar Surface', 'TERRAIN',
     'The Moon seen from orbit: bright cratered highlands and dark seas.',
     thumb=TERRAIN_THUMB, Ground_Color=(0.20, 0.195, 0.19), Dark_Patches=0.4, Craters=0.75, Small_Craters=0.9,
     Crater_Age=0.5, Ejecta=0.6, Rays=0.3)
_add('terrain_fresh_craters', 'Fresh Crater Field', 'TERRAIN',
     'Young, sharp impact craters with bright ejecta, rays and central peaks.',
     thumb=TERRAIN_THUMB, Ground_Color=(0.15, 0.147, 0.143), Craters=0.7, Crater_Age=0.0, Ejecta=0.9, Rays=0.8,
     Central_Peaks=0.8, Rim_Height=1.3, Boulders=0.3)
_add('terrain_regolith', 'Lunar Regolith (Close-Up)', 'TERRAIN',
     'Dusty ground seen up close: footprint-sized craters, pebbles and rocks.',
     thumb=GROUND_THUMB, Ground_Color=(0.17, 0.165, 0.16), Crater_Size=0.12, Craters=0.8, Small_Craters=1.0,
     Crater_Age=0.7, Hills=0.15, Hill_Size=1.0, Regolith=1.0, Boulders=0.5, Boulder_Size=0.04, Ejecta=0.3, Rays=0.0)
_add('terrain_asteroid_carbon', 'Carbonaceous Asteroid', 'TERRAIN',
     'Coal-dark C-type asteroid: battered by craters and strewn with boulders.',
     thumb=TERRAIN_THUMB, Ground_Color=(0.032, 0.031, 0.030), Rock_Color=(0.045, 0.043, 0.04), Craters=1.0,
     Small_Craters=1.0, Crater_Age=0.5, Hills=0.8, Hill_Size=2.0, Boulders=0.6, Boulder_Size=0.12, Ejecta=0.2,
     Rays=0.0, Color_Variation=0.25)
_add('terrain_asteroid_stony', 'Stony Asteroid', 'TERRAIN',
     'Brownish gray S-type asteroid: rubble, boulders and bare rock.',
     thumb=TERRAIN_THUMB, Ground_Color=(0.19, 0.16, 0.125), Rock_Color=(0.15, 0.13, 0.10), Craters=0.9,
     Crater_Age=0.6, Hills=0.8, Hill_Size=2.0, Boulders=0.5, Boulder_Size=0.15, Bedrock=0.3, Ejecta=0.3, Rays=0.0)
_add('terrain_asteroid_metal', 'Metallic Asteroid', 'TERRAIN',
     'M-type asteroid of nickel-iron: shiny metal showing through the dust.',
     thumb=TERRAIN_THUMB, Ground_Color=(0.12, 0.115, 0.11), Rock_Color=(0.10, 0.095, 0.09), Metal_Flecks=0.7,
     Craters=0.8, Crater_Age=0.4, Hills=0.6, Hill_Size=2.0, Boulders=0.3, Boulder_Size=0.1, Rays=0.0, Ejecta=0.2,
     Roughness=0.8)
_add('terrain_mars', 'Martian Ground', 'TERRAIN',
     'Rusty red dust and rocks with old, softened craters.',
     thumb=TERRAIN_THUMB, Ground_Color=(0.30, 0.12, 0.05), Rock_Color=(0.16, 0.075, 0.04),
     Patch_Color=(0.14, 0.065, 0.035), Dark_Patches=0.25, Craters=0.35, Crater_Age=0.85, Hills=0.5, Boulders=0.5,
     Boulder_Size=0.1, Bedrock=0.15, Ejecta=0.1, Rays=0.0)
_add('terrain_battlefield', 'Shell-Cratered Battlefield', 'TERRAIN',
     'Muddy ground torn up by shell craters: scorched, with water in the bottoms.',
     thumb=GROUND_THUMB, Ground_Color=(0.075, 0.058, 0.04), Rock_Color=(0.09, 0.08, 0.07), Crater_Size=1.2,
     Craters=0.85, Small_Craters=0.5, Crater_Age=0.15, Rim_Height=1.6, Central_Peaks=0.0, Ejecta=0.0, Rays=0.0,
     Scorch=0.5, Puddles=0.5, Wetness=0.4, Roughness=0.85, Regolith=0.4, Boulders=0.15, Color_Variation=0.5)
_add('terrain_desert_rock', 'Rocky Desert', 'TERRAIN',
     'Sandy ground with stones and cracked bedrock, no craters.',
     thumb=GROUND_THUMB, Ground_Color=(0.38, 0.26, 0.15), Rock_Color=(0.26, 0.17, 0.10), Craters=0.0,
     Hills=0.6, Boulders=0.5, Boulder_Size=0.06, Bedrock=0.4, Regolith=0.7)
_add('terrain_volcanic_ash', 'Volcanic Ash Plain', 'TERRAIN',
     'Black ash and cinders with scattered volcanic bombs.',
     thumb=GROUND_THUMB, Ground_Color=(0.05, 0.048, 0.046), Rock_Color=(0.03, 0.028, 0.027), Craters=0.15,
     Crater_Age=0.7, Rays=0.0, Ejecta=0.0, Hills=0.5, Boulders=0.35, Boulder_Size=0.1, Regolith=0.9)
_add('terrain_icy_moon', 'Icy Moon', 'TERRAIN',
     'Bright cracked ice crust with craters (Europa, Enceladus).',
     thumb=TERRAIN_THUMB, Ground_Color=(0.62, 0.62, 0.62), Rock_Color=(0.42, 0.36, 0.30), Patch_Color=(0.45, 0.38, 0.30),
     Dark_Patches=0.2, Craters=0.4, Crater_Age=0.3, Bedrock=0.7, Roughness=0.55, Boulders=0.05, Ejecta=0.2, Rays=0.4)

_add('lava_molten', 'Molten Lava', 'LAVA',
     'Bright, flowing molten lava with a few floating crust pieces.',
     thumb=LAVA_THUMB, Heat=1.0, Crust=0.25, Turbulence=0.7)
_add('lava_lake', 'Lava Lake', 'LAVA',
     'Churning lava lake: dark crust plates drifting on glowing melt.',
     thumb=LAVA_THUMB, Heat=1.0, Crust=0.55, Plate_Size=0.8, Crack_Width=0.4)
_add('lava_crusting', 'Cooling Lava Crust', 'LAVA',
     'Crust closing over the lava, glowing through wide cracks.',
     thumb=LAVA_THUMB, Heat=0.85, Crust=0.85, Crack_Width=0.35, Vesicles=0.3)
_add('lava_glowing_cracks', 'Glowing Cracks', 'LAVA',
     'Cooled black rock with dull red heat in the cracks.',
     thumb=LAVA_THUMB, Heat=0.6, Crust=1.0, Crack_Width=0.2, Temperature=1150.0, Vesicles=0.4)
_add('lava_magma', 'Magma', 'LAVA',
     'Very hot, yellow-orange magma: almost no crust.',
     thumb=LAVA_THUMB, Heat=1.0, Crust=0.05, Temperature=1650.0, Turbulence=0.9, Heat_Variation=0.4,
     Emission_Strength=1.8)
_add('lava_magma_churning', 'Churning Magma', 'LAVA',
     'Boiling magma with torn, glowing crust: volcano interiors and vents.',
     thumb=LAVA_THUMB, Heat=1.0, Crust=0.3, Temperature=1550.0, Turbulence=1.0, Heat_Variation=0.7,
     Plate_Size=0.3, Crack_Width=0.6, Emission_Strength=2.0)
_add('lava_pahoehoe_hot', 'Pahoehoe Flow (Hot)', 'LAVA',
     'Smooth, ropy pahoehoe lava, still glowing between the folds.',
     thumb=LAVA_THUMB, Heat=0.55, Crust=0.85, Ropes=1.0, Glassy=0.5, Plate_Size=1.2, Crack_Width=0.25)
_add('lava_pahoehoe', 'Pahoehoe (Cooled)', 'LAVA',
     'Cold ropy pahoehoe: smooth, glassy black-silver folds.',
     thumb=LAVA_THUMB, Heat=0.0, Crust=1.0, Ropes=1.0, Glassy=0.6, Crack_Width=0.05, Plate_Size=1.2,
     Crust_Color=(0.045, 0.043, 0.042))
_add('lava_aa_hot', 'Aa Flow (Advancing)', 'LAVA',
     'Rough aa lava rubble rolling forward, glowing underneath.',
     thumb=LAVA_THUMB, Heat=0.6, Crust=0.9, Clinker=1.0, Crack_Width=0.4, Crust_Roughness=0.95)
_add('lava_aa', 'Aa Lava (Cooled)', 'LAVA',
     'Cold, jagged clinker of aa lava: very rough, rusty brown-black.',
     thumb=LAVA_THUMB, Heat=0.0, Crust=1.0, Clinker=1.0, Crust_Roughness=0.95, Crack_Width=0.1,
     Crust_Color=(0.05, 0.038, 0.032))
_add('lava_basalt', 'Cooled Basalt', 'LAVA',
     'Dark gray basalt full of gas bubble holes.',
     thumb=LAVA_THUMB, Heat=0.0, Crust=1.0, Vesicles=0.7, Crack_Width=0.05, Crust_Color=(0.06, 0.058, 0.056))
_add('lava_obsidian', 'Obsidian', 'LAVA',
     'Glossy black volcanic glass.',
     thumb=LAVA_THUMB, Heat=0.0, Crust=1.0, Glassy=1.0, Vesicles=0.0, Crack_Width=0.02,
     Crust_Color=(0.008, 0.008, 0.01), Crust_Roughness=0.3)
_add('lava_sulfur', 'Sulfur Vent Rock', 'LAVA',
     'Volcanic rock with yellow sulfur crusts and a little heat left.',
     thumb=LAVA_THUMB, Heat=0.25, Crust=1.0, Sulfur=0.4, Temperature=1050.0, Crack_Width=0.15, Vesicles=0.4)
_add('lava_ash_field', 'Ash-Covered Lava Field', 'LAVA',
     'Old lava flow dusted with gray volcanic ash.',
     thumb=LAVA_THUMB, Heat=0.0, Crust=1.0, Ash=0.6, Clinker=0.4, Crack_Width=0.08)
# ------------------------------------------------------------------- gradients
def _hex(code):
    """sRGB hex color ('#ff8800') -> linear RGB."""
    code = code.lstrip('#')

    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return tuple(round(lin(int(code[i:i + 2], 16) / 255.0), 5) for i in (0, 2, 4))


# gradient choices (see mat_gradient.py)
LINEAR, MIRRORED, RADIAL, SPHERICAL, ANGULAR, DIAMOND, SQUARE, CUBE, SPIRAL, SLOPE, FACING = range(11)
BOUNDS, OBJECT, WORLD, UV, SCREEN = range(5)
CLAMP, REPEAT, PING_PONG = range(3)
SMOOTH, CONSTANT = 1.0, 2.0
TOP = (0.0, 0.0, 1.0)
SIDE = (1.0, 0.0, 0.0)
GRADIENT_THUMB = dict(shape='sphere')
PANEL_THUMB = dict(shape='panel')  # a flat slab facing the camera: gradients around a center
H = 0.0  # Angle: left to right
V = math.radians(90.0)  # Angle: bottom to top
D45 = math.radians(45.0)


def _grad(pid, name, desc, colors, positions=None, thumb=None, **values):
    """A gradient preset: `colors` are sRGB hex codes, `positions` (optional) where they sit."""
    stops = {'Color_Stops': float(len(colors))}
    for i, code in enumerate(colors):
        stops['Color_%d' % (i + 1)] = _hex(code)
    if positions:
        stops['Spacing'] = 1.0
        for i, pos in enumerate(positions):
            stops['Position_%d' % (i + 1)] = pos
    stops.update({k: float(v) if isinstance(v, int) else v for k, v in values.items()})
    if thumb is None:
        centered = values.get('Type') in (RADIAL, ANGULAR, DIAMOND, SQUARE, SPIRAL)
        thumb = PANEL_THUMB if centered and values.get('Projection', BOUNDS) == BOUNDS else GRADIENT_THUMB
    _add(pid, name, 'GRADIENT', desc, thumb=thumb, **stops)


# -- linear
_grad('grad_black_white', 'Black to White', 'Plain black to white, bottom to top: a mask or a start for your own.',
      ['#000000', '#ffffff'])
_grad('grad_sunset', 'Sunset Sky', 'Warm horizon glow up to a deep violet sky.',
      ['#ffd27a', '#f28a3c', '#c2427a', '#5b2a86', '#1d1442'], Bias=0.25, Roughness=0.6)
_grad('grad_daylight_sky', 'Daylight Sky', 'Hazy pale horizon up to a clear deep blue.',
      ['#eef4f8', '#a9cdea', '#5b9bd5', '#2a64ad'], Bias=0.3, Roughness=0.6)
_grad('grad_night_sky', 'Night Sky', 'Faint purple glow at the horizon fading into black night.',
      ['#3f2f63', '#141a3c', '#04060d'], Bias=-0.3)
_grad('grad_ocean_depth', 'Ocean Depths', 'Dark deep water up to bright turquoise shallows.',
      ['#011c33', '#014f86', '#2a6f97', '#61a5c2', '#a9d6e5'], Roughness=0.2)
_grad('grad_fire', 'Fire', 'Glowing flames: black smoke, deep red, orange and a white-hot base.',
      ['#fff3b0', '#ffa200', '#d43d00', '#5c0a00', '#000000'], Noise=0.35, Noise_Size=0.4, Glow=1.0,
      Emission_Strength=2.0)
_grad('grad_rainbow', 'Rainbow', 'The full spectrum, left to right.',
      ['#ff0000', '#ffee00', '#00d040', '#0050ff', '#8b00ff'], Angle=H)
_grad('grad_thermal', 'Thermal Camera', 'Heat-camera colors: black, purple, red, yellow, white.',
      ['#000000', '#5a189a', '#e01e37', '#ffba08', '#ffffff'])
_grad('grad_viridis', 'Viridis', 'The classic perceptual data colormap: purple, teal, yellow.',
      ['#440154', '#3b528b', '#21918c', '#5ec962', '#fde725'], Angle=H)
_grad('grad_magma', 'Magma', 'Black through purple and pink to pale yellow.',
      ['#000004', '#3b0f70', '#8c2981', '#de4968', '#fcfdbf'], Angle=H)
_grad('grad_turbo', 'Turbo (Jet)', 'Rainbow-like heatmap: deep blue, cyan, green, orange, dark red.',
      ['#30123b', '#4686fb', '#1ae4b6', '#faba39', '#7a0403'], Angle=H)
_grad('grad_teal_orange', 'Teal & Orange', 'Cinematic duotone, corner to corner.',
      ['#0b6e75', '#f2a541'], Angle=D45, Size=1.4)
_grad('grad_cyan_magenta', 'Cyan to Magenta', 'Bright synthwave duotone, corner to corner.',
      ['#00d4ff', '#ff2fd0'], Angle=D45, Size=1.4, Roughness=0.25)
_grad('grad_pastel', 'Pastel Dream', 'Soft pink, lavender and baby blue.',
      ['#ffd1dc', '#e0c3fc', '#c2e9fb'], Interpolation=SMOOTH)
_grad('grad_mint_peach', 'Mint & Peach', 'Fresh mint fading into warm peach.',
      ['#b8f2e6', '#ffa69e'], Angle=D45, Size=1.4)
_grad('grad_ombre_fabric', 'Hand-Dyed Ombre', 'Uneven, hand-dyed indigo fade with a wobbly edge.',
      ['#f2efe6', '#7d9cc4', '#1f3b70'], Noise=0.5, Noise_Size=0.25, Roughness=0.9, Roughness_End=0.9)
_grad('grad_retro_sunset', 'Retro Stepped Sunset', '80s poster sunset in flat bands.',
      ['#ffe66d', '#ff9f43', '#ff4f79', '#9b3fb5', '#2d1e5e'], Steps=8)
_grad('grad_stripes_hazard', 'Diagonal Stripes', 'Hard-edged yellow and black hazard stripes.',
      ['#111111', '#ffcc00'], positions=(0.0, 0.5), Interpolation=CONSTANT, Angle=D45, Repeat=8,
      Repeat_Mode=REPEAT, Roughness=0.4)
_grad('grad_soft_bands', 'Soft Bands', 'Gentle, wavy bands of soft color.',
      ['#a8dadc', '#f1faee'], Repeat=6, Repeat_Mode=PING_PONG, Interpolation=SMOOTH, Noise=0.15)
_grad('grad_neon_tube', 'Neon Tube', 'A glowing neon strip: white-hot core, pink glow fading out.',
      ['#ffffff', '#ff1aa8', '#12000a'], Type=MIRRORED, Size=0.35, Glow=1.0, Emission_Strength=4.0,
      Bias=-0.2)
_grad('grad_horizon_band', 'Horizon Glow', 'A bright band in the middle fading out above and below.',
      ['#ffffff', '#7fb3ff', '#08306b'], Type=MIRRORED, Bias=-0.2)
# -- metals
_grad('grad_heat_tint', 'Heat-Tinted Titanium', 'Burnt exhaust colors: straw, bronze, purple, blue.',
      ['#c9b47a', '#b07a3c', '#6a3d8f', '#2e5fbf', '#5fb7d6'], Angle=H, Metallic=1.0, Metallic_End=1.0,
      Roughness=0.25, Roughness_End=0.25, Noise=0.2)
_grad('grad_chrome_gold', 'Chrome to Gold', 'Polished metal turning from chrome into gold.',
      ['#e6e6e6', '#ffd27a'], Metallic=1.0, Metallic_End=1.0, Roughness=0.12, Roughness_End=0.12)
_grad('grad_copper_fade', 'Copper to Bronze', 'Warm metal shading from bright copper to dark bronze.',
      ['#fab49b', '#7a4a26'], Metallic=1.0, Metallic_End=1.0, Roughness=0.25, Roughness_End=0.4)
_grad('grad_paint_to_metal', 'Paint Fading to Metal', 'Matte red paint turning into bare polished steel.',
      ['#9b1b1b', '#c4c6c8'], positions=(0.4, 0.6), Interpolation=SMOOTH, Metallic=0.0, Metallic_End=1.0,
      Roughness=0.6, Roughness_End=0.15)
_grad('grad_copper_verdigris', 'Copper to Verdigris', 'Bright copper turning into chalky blue-green verdigris.',
      ['#c77a4f', '#7a5236', '#3f8a70', '#86c9ad'], positions=(0.0, 0.35, 0.65, 1.0), Noise=0.35,
      Noise_Size=0.15, Metallic=1.0, Metallic_End=0.0, Roughness=0.3, Roughness_End=0.85)
_grad('grad_bronze_patina', 'Bronze Patina', 'Dark statue bronze with green patina gathering higher up.',
      ['#4a2f17', '#6e4a26', '#4f6b4a', '#6fa38a'], Noise=0.45, Noise_Size=0.1, Metallic=1.0,
      Metallic_End=0.1, Roughness=0.4, Roughness_End=0.8)
_grad('grad_conic_chrome', 'Conic Chrome', 'Spun-metal highlights sweeping around the center.',
      ['#4a4a4a', '#f0f0f0'], Type=ANGULAR, Repeat=4, Repeat_Mode=PING_PONG, Interpolation=SMOOTH,
      Metallic=1.0, Metallic_End=1.0, Roughness=0.15, Roughness_End=0.15)
# -- more metals (all metallic unless noted)


def _metal(pid, name, desc, colors, positions=None, rough=0.2, rough_end=None, **values):
    values.setdefault('Metallic', 1.0)
    values.setdefault('Metallic_End', 1.0)
    _grad(pid, name, desc, colors, positions, Roughness=rough,
          Roughness_End=rough if rough_end is None else rough_end, **values)


# precious
_metal('grad_gold_shine', 'Gold Shine', 'Deep old gold rising into bright polished yellow gold.',
       ['#8a5a12', '#c89520', '#f5c84c', '#fff0b0'], rough=0.15)
_metal('grad_rose_gold', 'Rose Gold', 'Soft pink rose gold shading from coppery to pale blush.',
       ['#b0705a', '#e0a08a', '#f6cdbd'], rough=0.15)
_metal('grad_white_gold', 'White Gold', 'Warm white gold with a faint champagne tint.',
       ['#a69c88', '#ddd5c3', '#f4efe4'], rough=0.12)
_metal('grad_platinum', 'Platinum', 'Cool, slightly grey platinum from shadow to sheen.',
       ['#7d7f83', '#c4c6c9', '#e9eaec'], rough=0.15)
_metal('grad_silver_sheen', 'Silver Sheen', 'Bright sterling silver with soft bands of sheen.',
       ['#9aa0a6', '#f4f6f8'], Repeat=3, Repeat_Mode=PING_PONG, Interpolation=SMOOTH, rough=0.1)
_metal('grad_silver_to_gold', 'Silver to Gold', 'Sterling silver warming into yellow gold.',
       ['#d6d9dc', '#e9d9a8', '#f2c14e'], rough=0.15)
_metal('grad_gold_to_rose', 'Gold to Rose Gold', 'Yellow gold blushing into pink rose gold.',
       ['#f2c14e', '#eab08a', '#d98c78'], Angle=H, rough=0.15)
_metal('grad_gold_fresnel', 'Gold Fresnel', 'Rich orange gold in the middle, pale bright gold at the edges.',
       ['#fff0b8', '#f0b93a', '#a8700f'], Type=FACING, rough=0.12)
_metal('grad_tarnished_silver', 'Tarnishing Silver', 'Clean silver at the top, tarnish creeping up dark and '
       'golden-brown from below.', ['#2e2620', '#6e5a3e', '#a69c88', '#e6e8ea'],
       positions=(0.0, 0.4, 0.62, 0.85), Noise=0.35, Noise_Size=0.15, rough=0.55, rough_end=0.12)
# chrome and steel
_metal('grad_chrome_bands', 'Chrome Bands', 'Mirror chrome reflections: hard bands of black and white.',
       ['#141414', '#f8f8f8', '#5a5a5a', '#ffffff'], positions=(0.0, 0.45, 0.55, 1.0), Repeat=2,
       Repeat_Mode=PING_PONG, rough=0.04)
_metal('grad_chrome_fresnel', 'Chrome Fresnel', 'Dark chrome face with bright mirror edges.',
       ['#f0f0f0', '#8a8a8a', '#3a3a3a'], Type=FACING, rough=0.05)
_metal('grad_black_chrome', 'Black Chrome', 'Smoky, dark mirror finish fading to plain chrome.',
       ['#121316', '#3a3c40', '#9a9ca0'], rough=0.06)
_metal('grad_polished_steel', 'Polished Steel', 'Cool blue-grey steel from shadow to bright polish.',
       ['#55606b', '#a7b0b8', '#e2e6ea'], rough=0.15)
_metal('grad_gunmetal', 'Gunmetal', 'Dark blued gunmetal grey, almost black at the bottom.',
       ['#1a1d22', '#3a3f47', '#6a7079'], rough=0.3)
_metal('grad_gunmetal_chrome', 'Gunmetal to Chrome', 'Dark satin gunmetal brightening into polished chrome.',
       ['#2a2e34', '#6d737b', '#eef0f2'], Angle=H, rough=0.35, rough_end=0.06)
_metal('grad_liquid_metal', 'Liquid Metal', 'Mercury-like flowing chrome with soft wobbling reflections.',
       ['#2a2c30', '#d8dadc', '#6e7076', '#f6f6f6'], Repeat=2, Repeat_Mode=PING_PONG, Interpolation=SMOOTH,
       Noise=0.6, Noise_Size=0.35, rough=0.03)
_metal('grad_spun_disc', 'Spun Metal Disc', 'Turned metal: fine highlights sweeping around the center like '
       'a spun hubcap.', ['#7a7d82', '#e8eaec'], Type=ANGULAR, Repeat=12, Repeat_Mode=PING_PONG,
       Interpolation=SMOOTH, rough=0.2)
_metal('grad_brushed_rings', 'Machined Rings', 'Concentric lathe rings on bare aluminium.',
       ['#9a9ea3', '#d8dbde'], Type=RADIAL, Repeat=30, Repeat_Mode=PING_PONG, rough=0.25)
_metal('grad_aluminium', 'Aluminium Sheen', 'Soft, bright aluminium with a satin sheen.',
       ['#8f959b', '#c9cdd1', '#eceef0'], rough=0.3)
# copper, brass and bronze
_metal('grad_bright_copper', 'Bright Copper', 'Freshly polished copper, deep red-orange to pink highlights.',
       ['#7a2e14', '#c4602f', '#f2a684'], rough=0.15)
_metal('grad_copper_tarnish', 'Copper Tarnishing', 'Bright copper darkening to brown and nearly black.',
       ['#f2a684', '#a85a34', '#5a2e1a', '#2a1810'], Angle=H, Noise=0.3, Noise_Size=0.2, rough=0.15,
       rough_end=0.5)
_metal('grad_brass', 'Polished Brass', 'Warm yellow brass from shadow to bright polish.',
       ['#6e5414', '#c8a03c', '#f2dc8a'], rough=0.15)
_metal('grad_antique_brass', 'Antique Brass', 'Dark, mellowed brass with a muted golden glow.',
       ['#3a2a10', '#7a5e26', '#b08f4a'], Noise=0.2, Noise_Size=0.2, rough=0.4)
_metal('grad_brass_to_copper', 'Brass to Copper', 'Yellow brass turning into red copper.',
       ['#e0c068', '#d8925a', '#c4602f'], Angle=H, rough=0.2)
_metal('grad_bronze', 'Bronze', 'Rich brown-gold bronze from dark to warm highlights.',
       ['#4a2e14', '#8a5a2a', '#c8945a'], rough=0.25)
_metal('grad_oil_rubbed_bronze', 'Oil-Rubbed Bronze', 'Near-black bronze with copper glints showing through.',
       ['#1a120c', '#3a2618', '#7a4a2a'], Noise=0.3, Noise_Size=0.1, rough=0.35)
_metal('grad_champagne', 'Champagne Metal', 'Pale champagne gold, like a modern faucet finish.',
       ['#9a8a6a', '#d8c8a2', '#f0e6cc'], rough=0.25)
# heat and color
_metal('grad_temper_colors', 'Temper Colors', 'The colors steel takes as it is heated, in bands: straw, '
       'bronze, purple, blue, grey.', ['#e0c88a', '#b07a3c', '#7a3a8a', '#2e4fb0', '#8a9298'], Steps=5,
       rough=0.25)
_metal('grad_weld_heat', 'Weld Heat Tint', 'Rainbow heat tint on both sides of a weld line, fading to bare '
       'steel.', ['#3a4a6a', '#6a3a7a', '#b07a3c', '#d8c890', '#a7adb2'], Type=MIRRORED, Size=0.5,
       Noise=0.25, Noise_Size=0.05, rough=0.3)
_metal('grad_exhaust_heat', 'Exhaust Pipe Heat', 'Burnt pipe: blue and purple near the engine, golden '
       'further out, bare steel at the tip.', ['#2a3a7a', '#6a2a7a', '#b0783a', '#d8c8a0', '#b0b4b8'],
       Angle=H, Noise=0.3, Noise_Size=0.25, rough=0.25)
_metal('grad_case_hardened', 'Case Hardened', 'Mottled blue, purple and straw colors of case-hardened '
       'steel.', ['#2a3a6a', '#7a5a9a', '#c8a060', '#3a5a8a', '#b8bcc0'], Noise=1.0, Noise_Size=0.08,
       Repeat=3, Repeat_Mode=PING_PONG, rough=0.15)
_metal('grad_bismuth', 'Bismuth Crystal', 'Stepped iridescent bands like a bismuth crystal: gold, pink, '
       'blue, green.', ['#e8c040', '#d0508a', '#4060d0', '#30b0a0', '#e8c040'], Type=SQUARE, Steps=10,
       Repeat=3, Repeat_Mode=REPEAT, rough=0.08)
_metal('grad_oil_slick', 'Oil Slick', 'Iridescent oil-on-steel film shifting color with the viewing angle.',
       ['#2a1a4a', '#3a6ab0', '#3aa070', '#d0a030', '#a03a8a'], Type=FACING, Repeat=2,
       Repeat_Mode=PING_PONG, rough=0.1)
_metal('grad_anodized_fade', 'Anodized Fade', 'Anodized aluminium fading from deep blue to purple.',
       ['#1a3aa0', '#5a2ab0', '#a02a9a'], rough=0.3)
_metal('grad_anodized_sunset', 'Anodized Sunset', 'Anodized fade from red through orange into gold.',
       ['#b0182a', '#e0602a', '#e8b83a'], Angle=H, rough=0.3)
_metal('grad_aluminium_anodized', 'Bare to Anodized', 'Bare aluminium dipping into teal anodizing at the '
       'bottom.', ['#1a8a8a', '#1a8a8a', '#c9cdd1'], positions=(0.0, 0.4, 0.6), Interpolation=SMOOTH,
       rough=0.3)
# candy and flake
_metal('grad_candy_red', 'Candy Apple Red', 'Deep metallic candy red, almost black in the shadows.',
       ['#2a0408', '#8a0a14', '#e8202a'], rough=0.15)
_metal('grad_candy_blue', 'Candy Blue', 'Deep metallic candy blue brightening to electric blue.',
       ['#040a2a', '#0a2a9a', '#2a7aff'], rough=0.15)
_metal('grad_candy_purple', 'Candy Purple', 'Metallic candy purple fading into magenta.',
       ['#14042a', '#5a0a9a', '#d02ab0'], rough=0.15)
_metal('grad_candy_green', 'Candy Green', 'Metallic lime green deepening to emerald.',
       ['#022a10', '#0a8a3a', '#7ae83a'], rough=0.15)
# -- rust and oxides
STEEL_HEX = '#8c9196'
_grad('grad_rust_bleed', 'Rust Bleed', 'Rust spreading down over bare steel from the top, with a ragged edge.',
      [STEEL_HEX, '#7a6a5e', '#a24a1c', '#5e260d'], positions=(0.0, 0.35, 0.55, 1.0), Noise=0.55,
      Noise_Size=0.08, Metallic=1.0, Metallic_End=0.0, Roughness=0.35, Roughness_End=0.9)
_grad('grad_rust_creep', 'Rust Creeping Up', 'Steel rusting from the ground up: heavy rust low, clean metal on top.',
      ['#3d1a0a', '#8a3a14', '#b0622f', STEEL_HEX], positions=(0.0, 0.25, 0.45, 0.7), Noise=0.5,
      Noise_Size=0.1, Metallic=0.0, Metallic_End=1.0, Roughness=0.9, Roughness_End=0.35)
_grad('grad_rusty_steel', 'Steel to Rust', 'Left to right from bright steel through orange rust to dark flaking scale.',
      ['#9a9fa4', '#b8642a', '#7a3212', '#2e1308'], Angle=H, Noise=0.3, Noise_Size=0.2, Metallic=1.0,
      Metallic_End=0.0, Roughness=0.3, Roughness_End=0.95)
_grad('grad_iron_oxide', 'Iron Oxide', 'Deep red-brown to bright orange oxide, like old mining spoil.',
      ['#3a1405', '#7a2e0e', '#b5541f', '#d88a3d'], Noise=0.3, Noise_Size=0.3, Roughness=0.9, Roughness_End=0.85)
_grad('grad_corten', 'Weathering Steel', 'Even, velvety brown rust of Cor-Ten steel, darker at the base.',
      ['#2e140a', '#5f2a12', '#8a3f1a', '#9c5126'], Noise=0.25, Noise_Size=0.05, Roughness=0.85,
      Roughness_End=0.8)
_grad('grad_burnt_orange', 'Burnt Orange', 'Deep burnt orange to warm amber.',
      ['#4f1a05', '#b34a0c', '#e8862a'], Roughness=0.6, Roughness_End=0.5)
_grad('grad_rust_spot', 'Rust Spot', 'A round rust bloom on steel: dark pitted center, orange halo, clean metal outside.',
      ['#3a1607', '#9a3f15', '#c4743b', STEEL_HEX], positions=(0.0, 0.35, 0.6, 0.85), Type=RADIAL, Noise=0.4,
      Noise_Size=0.08, Metallic=0.0, Metallic_End=1.0, Roughness=0.95, Roughness_End=0.35)
_grad('grad_rust_waterline', 'Rust Waterline', 'A rusty band around the middle where water stood, steel above and below.',
      ['#5a250c', '#a8521f', STEEL_HEX], positions=(0.0, 0.3, 0.75), Type=MIRRORED, Size=0.5, Noise=0.45,
      Noise_Size=0.06, Metallic=0.0, Metallic_End=1.0, Roughness=0.9, Roughness_End=0.35)
_grad('grad_rust_top', 'Rust on Top', 'Rust where rain sits: on the faces that look up, bare steel on the sides.',
      [STEEL_HEX, STEEL_HEX, '#a24a1c', '#6b2c10'], positions=(0.0, 0.62, 0.78, 0.95), Type=SLOPE,
      Projection=WORLD, View_Axis=TOP, Noise=0.4, Noise_Size=0.06, Metallic=1.0, Metallic_End=0.0,
      Roughness=0.35, Roughness_End=0.9)
_grad('grad_rust_bands', 'Rust Bands', 'Hard bands of rust colors, from fresh orange to black scale.',
      ['#1f0d05', '#5a240c', '#94401a', '#c4682e', '#dd9b55'], Steps=7, Noise=0.2, Noise_Size=0.2,
      Roughness=0.9, Roughness_End=0.8)
_grad('grad_scorched_rust', 'Scorched Rust', 'Fire-blackened metal fading into heat-reddened rust.',
      ['#0c0907', '#2e130a', '#7a2a10', '#b0582a'], Noise=0.35, Noise_Size=0.15, Metallic=0.6,
      Metallic_End=0.0, Roughness=0.7, Roughness_End=0.9)
_grad('grad_rusty_sheen', 'Rusty Sheen', 'Rust in the middle of each face, still-metallic brown at the grazing edges.',
      ['#b0562a', '#8a3c16', '#5a3a28'], Type=FACING, Metallic=0.0, Metallic_End=0.8, Roughness=0.9,
      Roughness_End=0.5)
# -- earth tones
_grad('grad_terracotta', 'Terracotta', 'Fired clay from deep brick red to sun-baked pale terracotta.',
      ['#7a3420', '#b55a3c', '#d98a68'], Roughness=0.85, Roughness_End=0.85)
_grad('grad_ochre', 'Ochre', 'Dark yellow-brown earth to bright golden ochre pigment.',
      ['#5e3c0e', '#a8761f', '#d9aa4a'], Roughness=0.85, Roughness_End=0.85)
_grad('grad_sienna', 'Burnt Sienna', 'Rich red-brown earth pigment, dark to light.',
      ['#3f190a', '#8a3b1c', '#c0653a'], Roughness=0.8, Roughness_End=0.8)
_grad('grad_umber', 'Raw to Burnt Umber', 'Cool dark brown warming into raw umber.',
      ['#1f150d', '#4a3220', '#7a5c3c'], Angle=H, Roughness=0.8, Roughness_End=0.8)
_grad('grad_red_clay', 'Red Clay', 'Wet dark clay at the bottom drying to pale orange on top.',
      ['#4a1e10', '#8f3f22', '#c27a52'], Noise=0.3, Noise_Size=0.2, Roughness=0.3, Roughness_End=0.9)
_grad('grad_drying_mud', 'Drying Mud', 'Glossy wet mud low down, dull and pale where it has dried.',
      ['#1c130b', '#3a2a1a', '#7a6650', '#a39079'], positions=(0.0, 0.3, 0.55, 1.0), Noise=0.5,
      Noise_Size=0.12, Roughness=0.15, Roughness_End=0.95)
_grad('grad_wet_sand', 'Wet Sand Shore', 'Dark wet sand at the waterline drying into pale beach sand.',
      ['#4f4030', '#8a7558', '#d6c09a', '#ead8b4'], positions=(0.0, 0.3, 0.6, 1.0), Noise=0.35,
      Noise_Size=0.2, Roughness=0.25, Roughness_End=0.9)
_grad('grad_desert_dunes', 'Desert Dunes', 'Warm dune sand from shaded orange to pale sunlit crest.',
      ['#8a4a22', '#c9874c', '#e9c48c', '#f5e0b8'], Noise=0.3, Noise_Size=0.5, Roughness=0.9, Roughness_End=0.9)
_grad('grad_sand_top', 'Sand on Top', 'Pale sand drifted onto the faces that look up, dark rock on the sides.',
      ['#4a3b2e', '#4a3b2e', '#c9a873', '#e2c793'], positions=(0.0, 0.7, 0.82, 1.0), Type=SLOPE,
      Projection=WORLD, View_Axis=TOP, Noise=0.35, Noise_Size=0.08, Roughness=0.75, Roughness_End=0.95)
_grad('grad_dirt_top', 'Soil on Top', 'Brown soil caked on the top faces, grey stone below.',
      ['#6b6862', '#6b6862', '#4a3524', '#2e2016'], positions=(0.0, 0.66, 0.8, 1.0), Type=SLOPE,
      Projection=WORLD, View_Axis=TOP, Noise=0.45, Noise_Size=0.08, Roughness=0.7, Roughness_End=0.95)
_grad('grad_canyon_strata', 'Canyon Strata', 'Wavy layered canyon rock: rust red, salmon, cream and brown.',
      ['#7a2e16', '#c2643a', '#e3a77a', '#f0d6b0', '#8a4a2a'], Repeat=4, Repeat_Mode=PING_PONG, Noise=0.3,
      Noise_Size=0.6, Roughness=0.85, Roughness_End=0.85)
_grad('grad_sandstone', 'Sandstone Bands', 'Fine, wavy bands of buff and rose sandstone.',
      ['#c29a6e', '#e2c39b', '#b87a56', '#ead2ae'], Repeat=7, Repeat_Mode=PING_PONG, Interpolation=SMOOTH,
      Noise=0.25, Noise_Size=0.35, Roughness=0.9, Roughness_End=0.9, Relief=0.25)
_grad('grad_red_rock', 'Red Rock Mesa', 'Dark rust-red base under bright red cliffs and a pale cap rock.',
      ['#4a1a0e', '#9a3b1e', '#c4552c', '#d98e5e', '#ecd2b0'], positions=(0.0, 0.25, 0.55, 0.8, 0.9),
      Noise=0.2, Noise_Size=0.4, Roughness=0.85, Roughness_End=0.85)
_grad('grad_badlands', 'Badlands', 'Striped badlands clay: mauve, ochre, grey and white in hard layers.',
      ['#6b4f5c', '#c79a5a', '#9a958e', '#e6ddd0', '#8a5a3a'], Repeat=3, Repeat_Mode=REPEAT, Steps=10,
      Noise=0.3, Noise_Size=0.5, Roughness=0.9, Roughness_End=0.9)
_grad('grad_soil_layers', 'Soil Layers', 'A dug-out soil profile: bedrock, orange clay, brown subsoil, black topsoil.',
      ['#7d7a72', '#b8743a', '#6b4626', '#2a1b10', '#1a120a'], positions=(0.0, 0.25, 0.5, 0.78, 0.92),
      Interpolation=SMOOTH, Noise=0.4, Noise_Size=0.15, Roughness=0.8, Roughness_End=0.95)
_grad('grad_sediment', 'River Sediment', 'Many thin silt and sand layers, gently wavy.',
      ['#4a3e32', '#8a7a62', '#b8a684', '#6e5a44'], Repeat=5, Repeat_Mode=PING_PONG, Steps=14, Noise=0.35,
      Noise_Size=0.3, Roughness=0.85, Roughness_End=0.85, Relief=0.3)
_grad('grad_peat', 'Peat Bog', 'Black wet peat rising into fibrous brown and dry straw.',
      ['#0d0907', '#2e1f12', '#5a3d1e', '#9a7a42'], positions=(0.0, 0.4, 0.75, 1.0), Noise=0.45, Noise_Size=0.1,
      Roughness=0.3, Roughness_End=0.95)
_grad('grad_loam', 'Garden Loam', 'Dark, rich garden soil with a lighter, dry crust.',
      ['#140d08', '#2e1e13', '#4f3b2a'], Noise=0.5, Noise_Size=0.05, Roughness=0.85, Roughness_End=0.95)
_grad('grad_adobe', 'Adobe Wall', 'Dusty adobe: darker, dirtier near the ground, pale sun-bleached higher up.',
      ['#5a3f2a', '#a37a54', '#d2b08a', '#e3c9a6'], positions=(0.0, 0.2, 0.5, 1.0), Noise=0.3, Noise_Size=0.2,
      Roughness=0.9, Roughness_End=0.9)
_grad('grad_brick_dust', 'Brick Dust', 'Crushed brick red fading to dusty pink.',
      ['#6a2214', '#a8452c', '#d2917a'], Angle=D45, Size=1.4, Roughness=0.9, Roughness_End=0.9)
_grad('grad_volcanic_soil', 'Volcanic Soil', 'Black basalt grit into dark red-brown scoria.',
      ['#0e0c0b', '#2a1a14', '#5a2a1a'], Noise=0.4, Noise_Size=0.1, Roughness=0.85, Roughness_End=0.9)
_grad('grad_mars_dust', 'Martian Dust', 'Butterscotch dust over rusty red regolith.',
      ['#5a2412', '#a24a24', '#c97a44', '#dba878'], Noise=0.3, Noise_Size=0.4, Roughness=0.9, Roughness_End=0.9)
_grad('grad_desert_dusk', 'Desert Dusk', 'Dusty orange horizon up to a brown-violet evening sky.',
      ['#e8a35a', '#c46a3c', '#7a3e3a', '#3a2232'], Bias=0.2, Roughness=0.6)
_grad('grad_earth_palette', 'Earth Palette', 'Five earth pigments side by side: umber, sienna, ochre, olive, sand.',
      ['#3e2a1a', '#8a3b1c', '#b07d24', '#5c5a2a', '#d9c49a'], Angle=H, Steps=5, Roughness=0.8, Roughness_End=0.8)
_grad('grad_clay_pot', 'Sun-Baked Clay', 'A pale sun-baked center darkening to shaded red clay outside.',
      ['#e0a87e', '#b8683f', '#6a2c18'], Type=RADIAL, Interpolation=SMOOTH, Roughness=0.85, Roughness_End=0.85)
# -- plants and natural browns
_grad('grad_autumn', 'Autumn Leaves', 'The turn of the leaves: green, gold, orange, red and brown.',
      ['#4a6b1f', '#c9a12a', '#d9701c', '#9a2a14', '#4a2a14'], Angle=H, Noise=0.25, Noise_Size=0.2,
      Roughness=0.6, Roughness_End=0.7)
_grad('grad_forest_floor', 'Forest Floor', 'Dark humus, brown leaf litter and green moss on top.',
      ['#140e09', '#4a3220', '#7a5a34', '#4f5f22'], positions=(0.0, 0.35, 0.65, 1.0), Noise=0.5,
      Noise_Size=0.08, Roughness=0.85, Roughness_End=0.9)
_grad('grad_savanna', 'Savanna Grass', 'Dry golden grass at the tips, olive green at the roots.',
      ['#3e4a1c', '#7a7a2e', '#c4a54e', '#e2c97a'], Noise=0.2, Noise_Size=0.2, Roughness=0.8, Roughness_End=0.8)
_grad('grad_wheat', 'Wheat Field', 'Ripe wheat: warm straw gold to pale cream.',
      ['#8a5e1e', '#c9973e', '#ead09a'], Roughness=0.75, Roughness_End=0.75)
_grad('grad_olive_khaki', 'Olive to Khaki', 'Drab olive green to dusty khaki.',
      ['#3b3d1c', '#6b6a3a', '#b5a476'], Angle=H, Roughness=0.75, Roughness_End=0.75)
_grad('grad_tobacco', 'Tobacco Leaf', 'Cured tobacco browns: deep mahogany to golden leaf.',
      ['#3a1e0e', '#7a4420', '#b8803e'], Noise=0.2, Noise_Size=0.15, Roughness=0.6, Roughness_End=0.7)
_grad('grad_saddle_tan', 'Saddle Tan', 'Worn saddle leather: dark brown to honey tan, glossy where it is darker.',
      ['#2e170b', '#7a4422', '#c08850'], Interpolation=SMOOTH, Roughness=0.35, Roughness_End=0.6)
_grad('grad_coffee', 'Coffee & Cream', 'Espresso brown swirling up into milky cream.',
      ['#1f120a', '#5a3620', '#b08a64', '#e8d6bc'], Roughness=0.3, Roughness_End=0.4)
_grad('grad_cinnamon', 'Cinnamon Spice', 'Cinnamon, nutmeg and ginger browns.',
      ['#5a2a12', '#9a5226', '#c88a52'], Angle=D45, Size=1.4, Roughness=0.8, Roughness_End=0.8)
_grad('grad_honey', 'Honey Amber', 'Dark amber honey to glowing golden honey.',
      ['#4a1e04', '#a8560c', '#e8a42a'], Roughness=0.15, Roughness_End=0.15)
# -- radial and spherical
_grad('grad_spotlight', 'Spotlight', 'Bright white center fading to black.',
      ['#ffffff', '#000000'], Type=RADIAL, Interpolation=SMOOTH)
_grad('grad_vignette', 'Vignette', 'Soft darkening toward the edges.',
      ['#bfbfbf', '#bfbfbf', '#141414'], positions=(0.0, 0.45, 1.0), Type=RADIAL, Size=1.3,
      Interpolation=SMOOTH)
_grad('grad_sun_orb', 'Glowing Orb', 'A glowing ball: white-hot core, orange and red outside.',
      ['#fff6d5', '#ffb347', '#ff5e13', '#3a0b00'], Type=RADIAL, Glow=1.0, Emission_Strength=3.0)
_grad('grad_target', 'Target Rings', 'Hard red and white rings, like a target.',
      ['#d62828', '#f5f5f5'], positions=(0.0, 0.5), Type=RADIAL, Interpolation=CONSTANT, Repeat=5,
      Repeat_Mode=REPEAT)
_grad('grad_ripples', 'Ripples', 'Soft rings spreading out like ripples on water, with relief.',
      ['#0b3c5d', '#5fa8d3'], Type=RADIAL, Repeat=8, Repeat_Mode=PING_PONG, Interpolation=SMOOTH,
      Relief=0.6, Roughness=0.1, Roughness_End=0.1)
_grad('grad_neon_ring', 'Neon Ring', 'A glowing ring of light.',
      ['#000000', '#ffd166', '#000000'], positions=(0.45, 0.7, 0.95), Type=RADIAL, Glow=1.0,
      Emission_Strength=3.0, Interpolation=SMOOTH)
_grad('grad_ellipse', 'Soft Ellipse', 'An oval glow, wider than tall.',
      ['#f6bd60', '#84a59d'], Type=RADIAL, Aspect=0.5, Interpolation=SMOOTH)
_grad('grad_bubble', 'Soap Bubble', 'Shimmering bubble colors in rings (Spherical).',
      ['#ffd6ff', '#c8b6ff', '#b8f2e6', '#ffd6a5'], Type=SPHERICAL, Size=1.75, Repeat=3, Repeat_Mode=PING_PONG, thumb=dict(shape='cube'),
      Roughness=0.05, Roughness_End=0.05)
# -- angular and spirals
_grad('grad_color_wheel', 'Color Wheel', 'All hues sweeping around the center.',
      ['#ff0000', '#ffd000', '#00e070', '#2050ff', '#ff0000'], Type=ANGULAR, Angle=H)
_grad('grad_sunburst', 'Sunburst', 'Alternating rays shining out from the center.',
      ['#ffcf3f', '#ff9f1c'], positions=(0.0, 0.5), Type=ANGULAR, Interpolation=CONSTANT, Repeat=16,
      Repeat_Mode=REPEAT)
_grad('grad_radar', 'Radar Sweep', 'A green radar beam sweeping around with a fading trail.',
      ['#000000', '#00ff66'], Type=ANGULAR, Bias=0.6, Glow=1.0, Emission_Strength=2.0)
_grad('grad_candy_spiral', 'Candy Spiral', 'Red and white swirl, like a lollipop.',
      ['#f5f5f5', '#e63946'], positions=(0.0, 0.5), Type=SPIRAL, Interpolation=CONSTANT, Repeat=3,
      Repeat_Mode=REPEAT, Size=0.5, Roughness=0.15, Roughness_End=0.15)
_grad('grad_hypno', 'Hypnotic Spiral', 'Soft black and white spiral.',
      ['#000000', '#ffffff'], Type=SPIRAL, Repeat=2, Repeat_Mode=PING_PONG, Size=0.4, Interpolation=SMOOTH)
# -- diamond, square and cube
_grad('grad_diamond', 'Diamond', 'Diamond-shaped glow from the center out.',
      ['#f84aa7', '#a74482', '#693668', '#1b1b3a'], Type=DIAMOND)
_grad('grad_pyramid', 'Pyramid Panel', 'A raised four-sided pyramid in relief.',
      ['#9a9a9a', '#5c5c5c'], Type=SQUARE, Reverse=1, Relief=1.0, Roughness=0.5, Roughness_End=0.5)
_grad('grad_tunnel', 'Retro Tunnel', 'Glowing neon squares running into the distance.',
      ['#0d0221', '#ff2a6d'], Type=SQUARE, Repeat=8, Repeat_Mode=PING_PONG, Bias=0.5, Glow=0.6,
      Emission_Strength=2.0)
_grad('grad_box_falloff', 'Box Falloff', 'Bright in the middle, darker toward every face of the object.',
      ['#ffffff', '#202020'], Type=CUBE, Interpolation=SMOOTH)
# -- by surface direction and view
_grad('grad_snow_top', 'Snow on Top', 'White snow on the upward faces, rock on the sides.',
      ['#5a4a3a', '#5a4a3a', '#f4f6f8'], positions=(0.0, 0.78, 0.86), Type=SLOPE, Projection=WORLD,
      View_Axis=TOP, Roughness=0.8, Roughness_End=0.5)
_grad('grad_moss_top', 'Moss on Top', 'Green moss growing on the tops, bare stone underneath.',
      ['#3d3a36', '#4c5a2a', '#5f7d24'], positions=(0.5, 0.7, 0.9), Type=SLOPE, Projection=WORLD,
      View_Axis=TOP, Noise=0.4, Noise_Size=0.1, Roughness=0.7, Roughness_End=0.9)
_grad('grad_rim_glow', 'Rim Glow', 'Glowing edges where the surface turns away from the camera.',
      ['#000000', '#00c8ff'], Type=FACING, Bias=0.5, Glow=1.0, Emission_Strength=3.0)
_grad('grad_chameleon', 'Color-Shift Paint', 'Chameleon car paint: the color shifts with the viewing angle.',
      ['#3a0ca3', '#4cc9f0', '#f72585'], Type=FACING, Metallic=0.7, Metallic_End=0.7, Roughness=0.2,
      Roughness_End=0.2)
_grad('grad_holographic', 'Holographic Foil', 'Rainbow foil that changes with the viewing angle.',
      ['#ff9ff3', '#feca57', '#48dbfb', '#1dd1a1', '#ff6b6b'], Type=FACING, Repeat=2,
      Repeat_Mode=PING_PONG, Metallic=1.0, Metallic_End=1.0, Roughness=0.12, Roughness_End=0.12)
# -- other projections
_grad('grad_studio_backdrop', 'Studio Backdrop', 'Light-gray studio sweep from the bottom of the frame to dark gray '
      'at the top (Screen projection: follows the camera).',
      ['#c8c8c8', '#3a3a3a'], Projection=SCREEN, Roughness=0.8, Roughness_End=0.8)
_grad('grad_uv_ramp', 'UV Ramp', 'Black to white along the UV map (V): for masks and texture painting.',
      ['#000000', '#ffffff'], Projection=UV)
_grad('grad_height_fade', 'Height Fade (World)', 'Dark at ground level (Z = 0) to pale 3 m up: in world '
      'space, so it stays put when objects move.',
      ['#2f2f2f', '#c8d2dc'], Projection=WORLD, Center=(0.0, 0.0, 1.5), Size=1.5)
# ---------------------------------------------------------------------- lights
NEON_THUMB = dict(shape='tube', world=0.25, view='Standard')
TUBE_THUMB = dict(shape='rod', world=0.3, view='Standard')  # straight fluorescent tube, ends along Z
LIGHT_PANEL_THUMB = dict(shape='panel', zoom=0.5, world=0.3, view='Standard')
NEON_RED = (1.0, 0.10, 0.02)
NEON_PINK = (1.0, 0.02, 0.35)
NEON_BLUE = (0.02, 0.25, 1.0)
NEON_GREEN = (0.10, 1.0, 0.05)
COOL_WHITE = (0.85, 0.92, 1.0)
WARM_WHITE = (1.0, 0.72, 0.42)


def _neon(pid, name, color, desc, **values):
    vals = dict(Type=0, Light_Color=color, Surface_Color=(0.7, 0.7, 0.68), Roughness=0.1, Ends_Along=0)
    vals.update(values)
    _add(pid, name, 'LIGHT', desc, thumb=NEON_THUMB, **vals)


_neon('light_neon_red', 'Red Neon', NEON_RED, 'A clean, glowing red neon tube.')
_neon('light_neon_pink', 'Dirty Pink Neon', NEON_PINK,
      'Hot pink neon with grime and dust on the glass.', Dust=0.35, Grime=0.3, Smudges=0.3,
      End_Blackening=0.4)
_neon('light_neon_blue', 'Dusty Blue Neon', NEON_BLUE,
      'Blue neon under a thick coat of dust, with blackened tube ends.', Dust=0.7, End_Blackening=0.8,
      End_Length=0.12, Unevenness=0.3)
_neon('light_neon_green_dead', 'Failing Green Neon', NEON_GREEN,
      'Green neon with sections that have gone dark.', Dead_Sections=0.5, End_Blackening=0.6,
      Unevenness=0.5, Grime=0.2)
_neon('light_neon_diner', 'Old Diner Neon', (1.0, 0.25, 0.03),
      'Orange diner sign neon: decades of kitchen grease, dust and fly specks.', Grime=0.6, Dust=0.4,
      Bugs=0.3, End_Blackening=0.7, Unevenness=0.35, Yellowing=0.2)
_neon('light_neon_abandoned', 'Abandoned Neon', NEON_PINK,
      'A neon tube in a derelict building: filthy, cracked, half dead and full of dead bugs.',
      Emission_Strength=0.8, Dust=0.8, Grime=0.7, Bugs=0.6, Cracks=0.5, Dead_Sections=0.6,
      End_Blackening=1.0, End_Length=0.15, Unevenness=0.6)
_neon('light_neon_argon', 'Argon Purple Neon', (0.45, 0.10, 1.0),
      'Violet-blue argon tube, slightly uneven.', Unevenness=0.3, End_Blackening=0.3)
_neon('light_neon_white', 'White Neon', (1.0, 0.92, 0.85), 'Soft white neon tube.', Emission_Strength=0.8)
_neon('light_neon_off', 'Unlit Neon Tube', NEON_RED,
      'A switched-off neon tube: the tinted glass and its sooty ends.', Power=0.0, Dust=0.3,
      End_Blackening=0.7, Surface_Color=(0.6, 0.6, 0.58))

_add('light_fluorescent', 'Fluorescent Tube', 'LIGHT',
     'A clean, cool-white fluorescent tube.',
     thumb=TUBE_THUMB, Type=1, Light_Color=COOL_WHITE, Emission_Strength=1.5, Surface_Color=(0.8, 0.8, 0.8),
     Roughness=0.4, Ends_Along=3, End_Blackening=0.2, End_Length=0.06)
_add('light_fluorescent_old', 'Blackened Fluorescent Tube', 'LIGHT',
     'An old, flickering-looking tube: black ends, dusty top, uneven glow.',
     thumb=TUBE_THUMB, Type=1, Light_Color=(0.9, 0.95, 0.85), Emission_Strength=1.2,
     Surface_Color=(0.75, 0.75, 0.72), Roughness=0.45, Ends_Along=3, End_Blackening=1.0, End_Length=0.12,
     Unevenness=0.5, Dust=0.5, Bugs=0.15)
_add('light_panel_bugs', 'Bug-Filled Light Cover', 'LIGHT',
     'A ceiling light diffuser full of dead insects and dust, the lamps showing through.',
     thumb=LIGHT_PANEL_THUMB, Type=1, Light_Color=WARM_WHITE, Emission_Strength=1.5, Hot_Spots=0.6,
     Grid_Size=0.4, Surface_Color=(0.78, 0.76, 0.70), Roughness=0.6, Bugs=0.8, Dust=0.4, Yellowing=0.3)
_add('light_panel_office', 'Yellowed Office Panel', 'LIGHT',
     'A tired office ceiling panel: yellowed diffuser, uneven glow, grimy.',
     thumb=LIGHT_PANEL_THUMB, Type=1, Light_Color=COOL_WHITE, Emission_Strength=1.5, Hot_Spots=0.4,
     Grid_Size=0.3, Surface_Color=(0.78, 0.77, 0.72), Roughness=0.7, Yellowing=0.7, Grime=0.3,
     Unevenness=0.4, Dust=0.2)
_add('light_panel_hospital', 'Failing Hospital Panel', 'LIGHT',
     'Cold, greenish panel light with dead patches and cracks.',
     thumb=LIGHT_PANEL_THUMB, Type=1, Light_Color=(0.75, 1.0, 0.85), Emission_Strength=1.3, Hot_Spots=0.3,
     Grid_Size=0.35, Surface_Color=(0.75, 0.78, 0.75), Roughness=0.6, Dead_Sections=0.4, Cracks=0.4,
     Unevenness=0.6, Dust=0.3, Smudges=0.3)
_add('light_lightbox', 'Grimy Lightbox Sign', 'LIGHT',
     'A backlit sign face, stained with grime and dirty rain.',
     thumb=LIGHT_PANEL_THUMB, Type=1, Light_Color=(1.0, 0.85, 0.55), Emission_Strength=1.5, Hot_Spots=0.5,
     Grid_Size=0.25, Surface_Color=(0.8, 0.78, 0.7), Roughness=0.3, Grime=0.6, Dirt=0.4, Bugs=0.3,
     Cracks=0.2, overlays=[overlay('DIRT', Amount=0.5, Streaks=0.8)])
_add('light_exit_sign', 'Emergency Exit Light', 'LIGHT',
     'A green emergency light: dusty, with fly specks.',
     thumb=LIGHT_PANEL_THUMB, Type=1, Light_Color=(0.05, 1.0, 0.15), Emission_Strength=1.5,
     Surface_Color=(0.6, 0.75, 0.6), Roughness=0.3, Dust=0.4, Bugs=0.3, Grime=0.2)

_add('light_led_matrix', 'LED Matrix', 'LIGHT',
     'A grid of glowing amber LEDs, like a scoreboard or bus sign.',
     thumb=LIGHT_PANEL_THUMB, Type=2, Light_Color=(1.0, 0.45, 0.02), Emission_Strength=3.0, Grid_Size=0.03,
     Fill=0.6, Surface_Color=(0.02, 0.02, 0.02), Roughness=0.4, Unevenness=0.3)
_add('light_led_dirty', 'Dirty LED Sign', 'LIGHT',
     'An outdoor LED sign: dead pixels, grime and dust.',
     thumb=LIGHT_PANEL_THUMB, Type=2, Light_Color=(1.0, 0.05, 0.02), Emission_Strength=3.0, Grid_Size=0.03,
     Fill=0.55, Surface_Color=(0.02, 0.02, 0.02), Roughness=0.5, Dead_Sections=0.4, Grime=0.5, Dust=0.4,
     Bugs=0.2, Unevenness=0.5)
_add('light_led_strip', 'Warm LED Strip', 'LIGHT',
     'Rows of warm glowing lines, like LED strips behind a cover.',
     thumb=LIGHT_PANEL_THUMB, Type=4, Light_Color=WARM_WHITE, Emission_Strength=2.0, Grid_Size=0.08,
     Fill=0.35, Surface_Color=(0.08, 0.08, 0.08), Roughness=0.3, Unevenness=0.2)
_add('light_scifi_strips', 'Sci-Fi Glow Strips', 'LIGHT',
     'Cyan glowing strips in a dark panel, a bit dusty.',
     thumb=LIGHT_PANEL_THUMB, Type=4, Light_Color=(0.05, 0.6, 1.0), Emission_Strength=2.5, Grid_Size=0.12,
     Fill=0.18, Surface_Color=(0.05, 0.055, 0.06), Roughness=0.35, Dust=0.25, Smudges=0.3)
_add('light_scifi_grimy', 'Grimy Sci-Fi Panel', 'LIGHT',
     'Failing orange warning strips on a filthy industrial panel.',
     thumb=LIGHT_PANEL_THUMB, Type=4, Light_Color=(1.0, 0.30, 0.02), Emission_Strength=2.5, Grid_Size=0.1,
     Fill=0.25, Surface_Color=(0.06, 0.06, 0.06), Roughness=0.5, Dead_Sections=0.4, Grime=0.7, Dust=0.5,
     Dirt=0.6, Unevenness=0.5)

_add('light_screen_crt', 'Green CRT Screen', 'LIGHT',
     'A glowing green monochrome monitor with scanlines.',
     thumb=LIGHT_PANEL_THUMB, Type=3, Light_Color=(0.15, 1.0, 0.2), Emission_Strength=4.5,
     Grid_Size=0.02, Scanlines=0.8, Surface_Color=(0.05, 0.07, 0.06), Roughness=0.08, Unevenness=0.3,
     Dust=0.2)
_add('light_screen_grimy', 'Grimy Old Monitor', 'LIGHT',
     'A dusty, finger-smudged color screen with dead pixels.',
     thumb=LIGHT_PANEL_THUMB, Type=3, Light_Color=(0.9, 0.85, 1.0), Emission_Strength=4.5, Grid_Size=0.015,
     Scanlines=0.4, Surface_Color=(0.03, 0.03, 0.035), Roughness=0.1, Dust=0.5, Smudges=0.6,
     Dead_Sections=0.2, Unevenness=0.3)
_add('light_screen_cracked', 'Cracked Screen', 'LIGHT',
     'A smashed LCD with dark cracks and dead patches.',
     thumb=LIGHT_PANEL_THUMB, Type=3, Light_Color=(0.7, 0.85, 1.0), Emission_Strength=4.5, Grid_Size=0.012,
     Surface_Color=(0.02, 0.02, 0.025), Roughness=0.05, Cracks=0.9, Crack_Scale=3.0, Dead_Sections=0.15,
     Smudges=0.4)

# ------------------------------------------------------------------------ wood
OAK = (0.50, 0.27, 0.11)
OAK_RING = (0.26, 0.11, 0.042)
PINE = (0.72, 0.47, 0.21)
PINE_RING = (0.42, 0.20, 0.065)
WALNUT = (0.15, 0.068, 0.03)
WALNUT_RING = (0.055, 0.024, 0.01)
WOOD_THUMB = dict(zoom=0.5)
SOLID_THUMB = dict(zoom=0.3)

_add('wood_oak_floor', 'Oak Floorboards', 'WOOD',
     'Satin varnished oak planks, like a living room floor.',
     thumb=WOOD_THUMB, Varnish=0.6, Varnish_Roughness=0.15, Pores=0.4, Dirt=0.15)
_add('wood_walnut', 'Varnished Walnut', 'WOOD',
     'Dark, glossy walnut furniture wood.',
     thumb=SOLID_THUMB, Wood_Color=WALNUT, Ring_Color=WALNUT_RING, Planks=0.0, Varnish=1.0, Pores=0.5,
     Ring_Contrast=0.85, Knots=0.05, Dirt=0.05)
_add('wood_pine_raw', 'Knotty Pine', 'WOOD',
     'Raw, light pine boards with knots.',
     thumb=WOOD_THUMB, Wood_Color=PINE, Ring_Color=PINE_RING, Knots=0.5, Pores=0.0, Ring_Contrast=0.7,
     Plank_Width=0.2, Gap_Width=0.003, Roughness=0.65)
_add('wood_maple_curly', 'Curly Maple', 'WOOD',
     'Lacquered flame maple with shimmering stripes, like a guitar top.',
     thumb=SOLID_THUMB, Wood_Color=(0.70, 0.45, 0.20), Ring_Color=(0.55, 0.32, 0.12), Figure=1.0,
     Planks=0.0, Varnish=1.0, Pores=0.0, Ring_Contrast=0.25, Knots=0.0, Dirt=0.0, Edge_Wear=0.0)
_add('wood_cherry', 'Cherry Furniture', 'WOOD',
     'Warm reddish cherry wood with a satin finish.',
     thumb=SOLID_THUMB, Wood_Color=(0.40, 0.13, 0.05), Ring_Color=(0.20, 0.05, 0.016), Planks=0.0,
     Varnish=0.8, Varnish_Roughness=0.12, Pores=0.15, Knots=0.03, Dirt=0.05, Ring_Contrast=0.8)
_add('wood_mahogany', 'Polished Mahogany', 'WOOD',
     'Deep red-brown mahogany with a mirror polish.',
     thumb=SOLID_THUMB, Wood_Color=(0.25, 0.07, 0.03), Ring_Color=(0.10, 0.025, 0.01), Planks=0.0,
     Varnish=1.0, Varnish_Roughness=0.04, Pores=0.6, Figure=0.3, Knots=0.0, Dirt=0.0, Ring_Contrast=0.8)
_add('wood_ebony', 'Ebony', 'WOOD',
     'Nearly black, dense, polished ebony.',
     thumb=SOLID_THUMB, Wood_Color=(0.022, 0.016, 0.013), Ring_Color=(0.006, 0.005, 0.004),
     Ring_Contrast=0.6, Planks=0.0, Varnish=1.0, Pores=0.2, Knots=0.0, Dirt=0.0)
_add('wood_teak_deck', 'Teak Boat Deck', 'WOOD',
     'Narrow teak deck planks with dark caulked seams.',
     thumb=WOOD_THUMB, Wood_Color=(0.33, 0.17, 0.06), Ring_Color=(0.18, 0.08, 0.025), Plank_Width=0.06,
     Plank_Length=4.0, Gap_Width=0.004, Weathering=0.25, Knots=0.05, Dirt=0.3)
_add('wood_pallet', 'Shipping Pallet Wood', 'WOOD',
     'Rough, cheap, dirty planks of a shipping pallet or crate.',
     thumb=WOOD_THUMB, Wood_Color=(0.55, 0.38, 0.20), Ring_Color=(0.35, 0.20, 0.08), Roughness=0.75,
     Plank_Width=0.1, Gap_Width=0.008, Knots=0.4, Fibers=0.8, Cracks=0.3, Edge_Wear=0.5, Dirt=0.4,
     Plank_Variation=0.8, Weathering=0.15)
_add('wood_barn_red', 'Peeling Barn Red', 'WOOD',
     'Old barn boards with flaking red paint over grey wood.',
     thumb=WOOD_THUMB, Grain_Direction=(0.0, 0.0, 1.0), Plank_Direction=(1.0, 0.0, 0.0), Plank_Width=0.2,
     Plank_Length=6.0, Gap_Width=0.004, Paint=1.0, Paint_Color=(0.33, 0.035, 0.022), Paint_Wear=0.45,
     Paint_Roughness=0.7, Weathering=0.7, Cracks=0.4, Dirt=0.35, Knots=0.3)
_add('wood_white_painted', 'White Painted Planks', 'WOOD',
     'Off-white painted wood paneling, slightly worn.',
     thumb=WOOD_THUMB, Grain_Direction=(0.0, 0.0, 1.0), Plank_Direction=(1.0, 0.0, 0.0), Plank_Width=0.12,
     Plank_Length=6.0, Paint=1.0, Paint_Color=(0.78, 0.77, 0.72), Paint_Wear=0.06, Paint_Roughness=0.45,
     Weathering=0.3, Dirt=0.2)
_add('wood_weathered', 'Weathered Grey Wood', 'WOOD',
     'Silver-grey fence boards bleached by sun and rain.',
     thumb=WOOD_THUMB, Weathering=1.0, Cracks=0.5, Plank_Width=0.18, Knots=0.3, Dirt=0.3, Edge_Wear=0.4,
     Roughness=0.8)
_add('wood_driftwood', 'Driftwood', 'WOOD',
     'Pale, smooth, sea-washed wood with raised grain.',
     thumb=WOOD_THUMB, Weathering=1.0, Weathered_Color=(0.45, 0.42, 0.37), Planks=0.0, Cracks=0.3,
     Distortion=0.8, Fibers=1.0, Edge_Wear=0.6, Knots=0.25, Dirt=0.1)
_add('wood_charred', 'Charred Wood (Shou Sugi Ban)', 'WOOD',
     'Deeply burnt black boards with crackled, alligator-skin char.',
     thumb=WOOD_THUMB, Burn=1.0, Plank_Width=0.15, Gap_Width=0.003, Dirt=0.0)
_add('wood_scorched', 'Scorched Planks', 'WOOD',
     'Planks with burnt, blackened patches.',
     thumb=WOOD_THUMB, Burn=0.55, Plank_Width=0.15, Dirt=0.25, Weathering=0.2)

# --------------------------------------------------------------------- plastic
PLASTIC_THUMB = dict(zoom=0.5)
DIRTY_THUMB = dict(zoom=0.5, shape='steps')

_add('plastic_glossy_red', 'Glossy Red Plastic', 'PLASTIC',
     'Shiny, new injection-molded plastic.',
     thumb=PLASTIC_THUMB, Roughness=0.15, Scratches=0.05, Scuffs=0.05, Dirt=0.0)
_add('plastic_matte_black', 'Textured Black Plastic', 'PLASTIC',
     'Matte black plastic with a fine molded texture, like electronics.',
     thumb=dict(zoom=0.2), Plastic_Color=(0.018, 0.018, 0.019), Roughness=0.5, Stipple=0.8, Scuffs=0.2,
     Scratches=0.1)
_add('plastic_white_abs', 'White ABS', 'PLASTIC',
     'Clean white plastic housing.',
     thumb=PLASTIC_THUMB, Plastic_Color=(0.75, 0.75, 0.72), Roughness=0.3, Scratches=0.08, Smudges=0.15)
_add('plastic_toy_yellow', 'Toy Brick Yellow', 'PLASTIC',
     'Bright, glossy toy plastic.',
     thumb=PLASTIC_THUMB, Plastic_Color=(0.85, 0.55, 0.0), Roughness=0.12, Scratches=0.08, Smudges=0.1,
     Scuffs=0.05, Dirt=0.0)
_add('plastic_piano_black', 'Piano Black', 'PLASTIC',
     'Deep, glossy lacquered black with fingerprints.',
     thumb=PLASTIC_THUMB, Plastic_Color=(0.01, 0.01, 0.01), Roughness=0.05, Clear_Coat=1.0, Smudges=0.35,
     Scratches=0.15, Scuffs=0.0, Dirt=0.0)
_add('plastic_dashboard', 'Car Dashboard', 'PLASTIC',
     'Soft-touch black plastic with an embossed leather grain.',
     thumb=dict(zoom=0.15), Plastic_Color=(0.03, 0.03, 0.032), Leather_Grain=1.0, Grain_Scale=150.0,
     Roughness=0.6, Scuffs=0.2, Dirt=0.15)
_add('plastic_rubber_grip', 'Ribbed Rubber Grip', 'PLASTIC',
     'Matte black rubber with grip ridges.',
     thumb=dict(zoom=0.07), Plastic_Color=(0.02, 0.02, 0.02), Roughness=0.8, Ribs=1.0, Rib_Spacing=0.004,
     Stipple=0.3, Scuffs=0.3, Scratches=0.0, Dirt=0.2)
_add('plastic_translucent', 'Translucent Orange', 'PLASTIC',
     'Glowing, see-through looking orange plastic.',
     thumb=PLASTIC_THUMB, Plastic_Color=(0.8, 0.25, 0.02), Subsurface=0.8, Roughness=0.25, Dirt=0.0)
_add('plastic_recycled', 'Recycled Plastic', 'PLASTIC',
     'Mottled green plastic with colored flecks.',
     thumb=dict(zoom=0.25), Plastic_Color=(0.10, 0.25, 0.12), Speckles=0.6, Speckle_Color=(0.7, 0.7, 0.6),
     Color_Variation=0.5, Roughness=0.5, Stipple=0.3)
_add('plastic_faded_blue', 'Sun-Faded Blue Plastic', 'PLASTIC',
     'Chalky outdoor plastic bleached by the sun.',
     thumb=PLASTIC_THUMB, Plastic_Color=(0.03, 0.12, 0.42), Fading=0.6, Roughness=0.45, Scuffs=0.3,
     Dirt=0.2)
_add('plastic_retro_beige', 'Yellowed Retro Beige', 'PLASTIC',
     'An old computer case: yellowed, scuffed and a bit dusty.',
     thumb=DIRTY_THUMB, Plastic_Color=(0.62, 0.58, 0.48), Yellowing=0.7, Roughness=0.45, Stipple=0.3,
     Scratches=0.15, Dirt=0.35, Grime=0.4, overlays=[overlay('DUST', Amount=0.35)])
_add('plastic_dirty_white', 'Dirty White Plastic', 'PLASTIC',
     'Scuffed white plastic with grime in every corner.',
     thumb=DIRTY_THUMB, Plastic_Color=(0.7, 0.7, 0.66), Roughness=0.4, Scuffs=0.4, Scratches=0.3, Dirt=0.6,
     Grime=0.5, Edge_Whitening=0.4, overlays=[overlay('DIRT', Amount=0.55, Streaks=0.3)])
_add('plastic_dirty_bin', 'Grimy Garbage Bin', 'PLASTIC',
     'Faded green bin plastic covered in grime and streaks.',
     thumb=DIRTY_THUMB, Plastic_Color=(0.04, 0.08, 0.04), Stipple=0.5, Roughness=0.55, Dirt=0.7, Grime=0.8,
     Fading=0.3, Scuffs=0.5, overlays=[overlay('DIRT', Amount=0.8, Streaks=0.6, Ground_Grime=0.8)])
_add('plastic_dirty_toy', 'Old Dusty Toy', 'PLASTIC',
     'A faded, scratched toy that sat in the attic.',
     thumb=DIRTY_THUMB, Plastic_Color=(0.6, 0.1, 0.05), Roughness=0.35, Fading=0.4, Scuffs=0.5,
     Scratches=0.4, Dirt=0.5, Grime=0.4, overlays=[overlay('DUST', Amount=0.5, Wipes=0.2)])
_add('plastic_garden_chair', 'Weathered Garden Chair', 'PLASTIC',
     'White outdoor plastic, sun-faded with dirty rain streaks.',
     thumb=DIRTY_THUMB, Plastic_Color=(0.7, 0.7, 0.68), Fading=0.4, Roughness=0.45, Dirt=0.5, Grime=0.6,
     Scuffs=0.3, overlays=[overlay('DIRT', Amount=0.6, Streaks=0.8, Patches=0.3)])

_add('plastic_bakelite_brown', 'Brown Bakelite', 'PLASTIC',
     'Glossy, swirled brown bakelite, like an old radio or telephone.',
     thumb=PLASTIC_THUMB, Plastic_Color=(0.10, 0.035, 0.010), Marbling=0.55, Marble_Color=(0.025, 0.008, 0.003),
     Marble_Scale=4.0, Roughness=0.12, Scratches=0.15, Scuffs=0.1, Dirt=0.1)
_add('plastic_bakelite_red', 'Marbled Red Catalin', 'PLASTIC',
     'Cherry-red marbled vintage plastic, like old radio cases and dice.',
     thumb=PLASTIC_THUMB, Plastic_Color=(0.45, 0.025, 0.015), Marbling=0.5, Marble_Color=(0.65, 0.30, 0.10),
     Marble_Scale=3.0, Roughness=0.1, Subsurface=0.3, Yellowing=0.2, Scratches=0.1)
_add('plastic_swirled', 'Swirled Recycled Plastic', 'PLASTIC',
     'Chunky multi-colored swirls of melted-down plastic.',
     thumb=PLASTIC_THUMB, Plastic_Color=(0.03, 0.10, 0.30), Marbling=0.5, Marble_Color=(0.60, 0.50, 0.04),
     Marble_Scale=2.0, Speckles=0.4, Speckle_Color=(0.6, 0.06, 0.04), Roughness=0.4, Stipple=0.2)
_add('plastic_glitter', 'Glitter Plastic', 'PLASTIC',
     'Sparkly purple plastic full of metal flakes, under a glossy coat.',
     thumb=dict(shape='sphere', zoom=0.4), Plastic_Color=(0.12, 0.02, 0.25), Glitter=0.6,
     Glitter_Color=(0.8, 0.6, 1.0), Roughness=0.15, Clear_Coat=1.0, Scratches=0.05)
_add('plastic_pearl', 'Pearl White Plastic', 'PLASTIC',
     'Pearly white plastic with a fine silver shimmer.',
     thumb=dict(shape='sphere', zoom=0.4), Plastic_Color=(0.75, 0.73, 0.70), Glitter=0.5, Glitter_Scale=500.0,
     Glitter_Color=(0.85, 0.82, 0.78), Roughness=0.2, Clear_Coat=0.6, Subsurface=0.2)
_add('plastic_cracked', 'Cracked Old Plastic', 'PLASTIC',
     'Brittle yellowed plastic, split with whitened stress cracks.',
     thumb=DIRTY_THUMB, Plastic_Color=(0.62, 0.58, 0.48), Yellowing=0.6, Cracks=0.7, Roughness=0.4,
     Scuffs=0.4, Scratches=0.3, Dirt=0.4, Grime=0.3)
_add('plastic_sun_rotted', 'Sun-Rotted Plastic', 'PLASTIC',
     'Outdoor plastic destroyed by UV: chalky, crumbling and cracked all over.',
     thumb=DIRTY_THUMB, Plastic_Color=(0.55, 0.06, 0.03), Fading=0.85, Cracks=0.9, Crack_Scale=7.0,
     Roughness=0.6, Scuffs=0.4, Dirt=0.5, Grime=0.5, Edge_Whitening=0.6,
     overlays=[overlay('DIRT', Amount=0.5, Streaks=0.6)])
_add('plastic_burnt', 'Burnt Plastic', 'PLASTIC',
     'White plastic with melted, blistered and charred burn marks.',
     thumb=PLASTIC_THUMB, Plastic_Color=(0.72, 0.72, 0.70), Burns=0.55, Roughness=0.3, Scuffs=0.2, Dirt=0.2)
_add('plastic_scorched', 'Scorched Black Plastic', 'PLASTIC',
     'Black plastic housing scorched by an electrical fire.',
     thumb=DIRTY_THUMB, Plastic_Color=(0.02, 0.02, 0.021), Stipple=0.6, Burns=0.7, Burn_Scale=2.0,
     Roughness=0.5, Dirt=0.5, Grime=0.5, overlays=[overlay('DUST', Amount=0.3)])
_add('plastic_cutting_board', 'Gouged Cutting Board', 'PLASTIC',
     'White HDPE cutting board: covered in knife cuts with grime in them, a bit stained.',
     thumb=dict(shape='panel', zoom=0.5), Plastic_Color=(0.78, 0.78, 0.75), Roughness=0.55, Gouges=0.8,
     Scratches=0.7, Scratch_Scale=4.0, Stains=0.25, Stain_Color=(0.75, 0.45, 0.30), Grime=0.4, Scuffs=0.3)
_add('plastic_food_container', 'Stained Food Container', 'PLASTIC',
     'Translucent white tub stained orange by tomato sauce.',
     thumb=PLASTIC_THUMB, Plastic_Color=(0.70, 0.70, 0.66), Subsurface=0.6, Roughness=0.35,
     Stains=0.75, Stain_Color=(0.85, 0.40, 0.12), Scratches=0.4, Scuffs=0.4)
_add('plastic_sticker_residue', 'Sticker Residue', 'PLASTIC',
     'Black plastic where labels and tape were scraped off: torn paper and dirty glue.',
     thumb=PLASTIC_THUMB, Plastic_Color=(0.02, 0.02, 0.02), Roughness=0.4, Stipple=0.4, Residue=0.6,
     Scratches=0.3, Dirt=0.2)
_add('plastic_trashed', 'Trashed Plastic', 'PLASTIC',
     'Beaten to death: cracked, gouged, burnt, stained, faded and caked in grime.',
     thumb=DIRTY_THUMB, Plastic_Color=(0.03, 0.10, 0.32), Cracks=0.6, Gouges=0.5, Burns=0.35, Stains=0.5,
     Residue=0.35, Scuffs=0.7, Scratches=0.6, Fading=0.4, Dirt=0.7, Grime=0.7, Edge_Whitening=0.6,
     overlays=[overlay('DIRT', Amount=0.6, Streaks=0.4)])
_add('plastic_playground', 'Abandoned Playground Slide', 'PLASTIC',
     'Faded red playground plastic: sun-bleached, cracked, scratched and rain-streaked.',
     thumb=DIRTY_THUMB, Plastic_Color=(0.50, 0.05, 0.03), Fading=0.65, Cracks=0.4, Crack_Scale=3.0,
     Scratches=0.6, Scuffs=0.6, Residue=0.15, Dirt=0.6, Grime=0.6,
     overlays=[overlay('DIRT', Amount=0.6, Streaks=0.8, Patches=0.3)])
_add('plastic_oily_shop', 'Oily Shop Plastic', 'PLASTIC',
     'Garage plastic soaked with oil stains and black greasy grime.',
     thumb=DIRTY_THUMB, Plastic_Color=(0.55, 0.30, 0.02), Stipple=0.4, Roughness=0.3, Stains=0.7,
     Stain_Color=(0.10, 0.08, 0.05), Scratches=0.4, Scuffs=0.5, Dirt=0.7, Grime=0.8,
     Dirt_Color=(0.02, 0.018, 0.015))
_add('plastic_smoker', 'Smoker-Yellowed Plastic', 'PLASTIC',
     'Off-white plastic turned brown-yellow by years of tobacco smoke, with tide-line stains.',
     thumb=DIRTY_THUMB, Plastic_Color=(0.70, 0.68, 0.62), Yellowing=0.9, Stains=0.4,
     Stain_Color=(0.65, 0.42, 0.12), Roughness=0.4, Grime=0.5, Dirt=0.5, Burns=0.12, Burn_Scale=10.0)

# ----------------------------------------------------------------------- glass
GLASS_THUMB = dict(zoom=0.25)
CLOSE_THUMB = dict(zoom=0.12)
CLEAR = (0.90, 0.96, 0.93)

_add('glass_clear', 'Clear Glass', 'GLASS',
     'Clean, colorless window glass.',
     thumb=GLASS_THUMB, Scratches=0.02, Smudges=0.03)
_add('glass_frosted', 'Frosted Glass', 'GLASS',
     'Sandblasted glass that blurs everything behind it.',
     thumb=GLASS_THUMB, Glass_Color=(0.93, 0.95, 0.94), Frosting=1.0, Scratches=0.0, Smudges=0.1)
_add('glass_green_bottle', 'Green Bottle Glass', 'GLASS',
     'Deep green glass, like wine bottles.',
     thumb=GLASS_THUMB, Glass_Color=(0.10, 0.42, 0.12), IOR=1.52, Color_Variation=0.15, Bubbles=0.15,
     Scratches=0.1)
_add('glass_amber_bottle', 'Amber Bottle Glass', 'GLASS',
     'Brown glass, like beer and medicine bottles.',
     thumb=GLASS_THUMB, Glass_Color=(0.62, 0.24, 0.035), IOR=1.52, Color_Variation=0.15, Scratches=0.1)
_add('glass_cobalt', 'Cobalt Blue Glass', 'GLASS',
     'Rich blue glass for vases and old bottles.',
     thumb=GLASS_THUMB, Glass_Color=(0.07, 0.17, 0.80), IOR=1.52, Color_Variation=0.1, Scratches=0.05)
_add('glass_smoked', 'Smoked Glass', 'GLASS',
     'Dark grey tinted glass, like car windows or a smoked table top.',
     thumb=GLASS_THUMB, Glass_Color=(0.12, 0.13, 0.13), Color_Variation=0.0, Smudges=0.15, Dust=0.1)
_add('glass_milk', 'Milk Glass', 'GLASS',
     'Opal white glass for lamp shades and vintage dishes.',
     thumb=GLASS_THUMB, Glass_Color=(0.95, 0.95, 0.93), Milkiness=0.85, Roughness=0.08, Scratches=0.05)
_add('glass_reeded', 'Reeded Glass', 'GLASS',
     'Fluted glass with rounded ribs, for doors and cabinets.',
     thumb=CLOSE_THUMB, Reeds=1.0, Reed_Direction=(1.0, 1.0, 0.0), Scratches=0.02)
_add('glass_hammered', 'Hammered Glass', 'GLASS',
     'Dimpled privacy glass, like bathroom windows.',
     thumb=CLOSE_THUMB, Hammered=1.0, Dimple_Size=0.012, Scratches=0.02)
_add('glass_wired', 'Wired Safety Glass', 'GLASS',
     'Glass with a wire grid inside, for fire doors and skylights.',
     thumb=CLOSE_THUMB, Wire_Mesh=1.0, Glass_Color=(0.86, 0.95, 0.90), Smudges=0.25, Grime=0.12,
     Scratches=0.1)
_add('glass_stained', 'Stained Glass Window', 'GLASS',
     'Colored pieces held together by lead, like church windows.',
     thumb=GLASS_THUMB, Stained_Glass=1.0, Piece_Size=0.07, Color_Variation=0.4, Waviness=0.5,
     Bubbles=0.2, Grime=0.1)
_add('glass_antique', 'Antique Window Glass', 'GLASS',
     'Old wavy glass with tiny bubbles and a faint haze.',
     thumb=GLASS_THUMB, Glass_Color=(0.84, 0.95, 0.87), Color_Variation=0.2, Waviness=1.0, Bubbles=0.6,
     Scratches=0.2, Grime=0.12, Water_Spots=0.2)
_add('glass_smudged', 'Smudged Glass', 'GLASS',
     'A display case covered in fingerprints and greasy smears.',
     thumb=CLOSE_THUMB, Smudges=1.0, Dust=0.08, Scratches=0.08)
_add('glass_dusty', 'Dusty Glass', 'GLASS',
     'Glass that nobody has cleaned for months.',
     thumb=GLASS_THUMB, Dust=0.55, Smudges=0.3, Water_Spots=0.25, Scratches=0.1)
_add('glass_dirty_window', 'Dirty Window', 'GLASS',
     'Grimy window glass with rain streaks and water spots.',
     thumb=GLASS_THUMB, Grime=0.4, Rain_Streaks=0.9, Water_Spots=0.4, Dust=0.05, Smudges=0.3,
     Scratches=0.15)
_add('glass_abandoned', 'Abandoned Window', 'GLASS',
     'Cracked, filthy glass from a building left empty for decades.',
     thumb=GLASS_THUMB, Grime=0.85, Grime_Color=(0.07, 0.055, 0.035), Rain_Streaks=0.6, Cracks=0.8,
     Crack_Scale=7.0, Dust=0.25, Chipped_Edges=0.6, Water_Spots=0.4, Scratches=0.4, Waviness=0.3)
_add('glass_scratched', 'Scratched Glass', 'GLASS',
     'Heavily scratched, worn glass, like an old shop window.',
     thumb=GLASS_THUMB, Scratches=0.9, Scratch_Scale=1.5, Chipped_Edges=0.5, Smudges=0.3, Grime=0.1)
_add('glass_cracked', 'Cracked Glass', 'GLASS',
     'Shattered safety glass that still holds together.',
     thumb=GLASS_THUMB, Cracks=1.0, Crack_Scale=25.0, Chipped_Edges=0.3, Smudges=0.2, Dust=0.1)
_add('glass_sea', 'Sea Glass', 'GLASS',
     'Frosted, pitted glass worn smooth by sand and waves.',
     thumb=dict(zoom=0.25, shape='sphere'), Glass_Color=(0.42, 0.78, 0.55), Weathering=1.0,
     Color_Variation=0.25, Bubbles=0.2, Scratches=0.0, Smudges=0.0)

# ----------------------------------------------------------------------- lenses
LENS_THUMB = dict(shape='dome', zoom=0.03)
GOLD_VISOR = (1.0, 0.766, 0.336)

_add('lens_camera', 'Camera Lens', 'LENS',
     'Multi-coated camera lens: deep black with purple and green reflections.',
     thumb=LENS_THUMB)
_add('lens_vintage_amber', 'Vintage Amber Lens', 'LENS',
     'Old single-coated lens with warm amber reflections, a little hazy.',
     thumb=LENS_THUMB, Coating=250.0, Lens_Color=(0.008, 0.006, 0.004), Haze=0.1, Scratches=0.08)
_add('lens_blue_coated', 'Blue-Coated Lens', 'LENS',
     'Optics with a cool blue coating.',
     thumb=LENS_THUMB, Coating=350.0)
_add('lens_night_vision', 'Night Vision Lens', 'LENS',
     'Green-coated lens of night vision goggles or a sniper scope.',
     thumb=LENS_THUMB, Coating=400.0, Lens_Color=(0.003, 0.010, 0.005))
_add('lens_ruby', 'Ruby Scope Lens', 'LENS',
     'Strong red-orange reflections, like a ruby-coated rifle scope.',
     thumb=LENS_THUMB, Coating=200.0, IOR=2.5, Coating_IOR=1.6, Lens_Color=(0.012, 0.004, 0.003))
_add('lens_iridescent', 'Iridescent Coating', 'LENS',
     'Oily rainbow reflections, like a dichroic or holographic coating.',
     thumb=LENS_THUMB, Coating=450.0, IOR=3.0, Coating_IOR=2.0, Coating_Variation=1.0, Depth=0.0)
_add('lens_gold_visor', 'Gold Visor', 'LENS',
     'Gold-coated helmet visor, like an astronaut or pilot helmet.',
     thumb=LENS_THUMB, Mirror=1.0, Mirror_Color=GOLD_VISOR, Coating=0.0, Roughness=0.03, Depth=0.0)
_add('lens_mirror_silver', 'Mirrored Sunglasses', 'LENS',
     'Silver mirror lenses.',
     thumb=LENS_THUMB, Mirror=0.85, Mirror_Color=(0.70, 0.71, 0.73), Coating=0.0, Depth=0.0)
_add('lens_mirror_blue', 'Blue Mirror Visor', 'LENS',
     'Blue mirrored visor or ski goggles.',
     thumb=LENS_THUMB, Mirror=0.9, Mirror_Color=(0.10, 0.30, 0.85), Coating=0.0, Depth=0.0)
_add('lens_smoked_visor', 'Smoked Visor', 'LENS',
     'Dark tinted visor: glossy and black.',
     thumb=LENS_THUMB, Lens_Color=(0.010, 0.010, 0.012), Coating=0.0, IOR=1.55, Depth=0.0)
_add('lens_black_glass', 'Black Glass Panel', 'LENS',
     'Glossy black glass, like a switched-off screen or sensor window, with fingerprints.',
     thumb=LENS_THUMB, Lens_Color=(0.004, 0.004, 0.005), Coating=120.0, IOR=1.52, Depth=0.0, Smudges=0.35,
     Roughness=0.01)
_add('lens_sensor_red', 'Red Sensor Eye', 'LENS',
     'Deep red robot or security camera eye.',
     thumb=LENS_THUMB, Lens_Color=(0.25, 0.005, 0.003), Depth=0.6)
_add('lens_tail_light', 'Red Tail Light', 'LENS',
     'Red reflector with hexagonal prisms, like a car tail light.',
     thumb=LENS_THUMB, Lens_Color=(0.30, 0.004, 0.004), Prisms=1.0, Coating=0.0, IOR=1.5, Depth=0.0)
_add('lens_amber_reflector', 'Amber Reflector', 'LENS',
     'Orange prism reflector of a turn signal or a bike.',
     thumb=LENS_THUMB, Lens_Color=(0.50, 0.17, 0.0), Prisms=1.0, Prism_Size=0.004, Coating=0.0, IOR=1.5,
     Depth=0.0)
_add('lens_fresnel', 'Fresnel Lens', 'LENS',
     'Grey lens with concentric Fresnel ridges, like a lighthouse or projector lens.',
     thumb=LENS_THUMB, Lens_Color=(0.04, 0.045, 0.05), Fresnel_Rings=1.0, Coating=0.0, IOR=1.5, Depth=0.0)
_add('lens_dusty', 'Dusty Old Lens', 'LENS',
     'Neglected lens: dust, smudges, scratches and a hazy coating.',
     thumb=LENS_THUMB, Dust=0.15, Smudges=0.4, Scratches=0.3, Haze=0.2)
_add('lens_cracked', 'Cracked Lens', 'LENS',
     'Broken lens with a web of cracks.',
     thumb=LENS_THUMB, Cracks=0.8, Scratches=0.2, Smudges=0.2)

# --------------------------------------------------------------------- leather
LEATHER_THUMB = dict(zoom=0.15)

_add('leather_brown', 'Brown Leather', 'LEATHER',
     'Classic pebbled brown leather, like a jacket or bag.',
     thumb=LEATHER_THUMB)
_add('leather_black', 'Black Leather', 'LEATHER',
     'Soft black leather with creases.',
     thumb=LEATHER_THUMB, Leather_Color=(0.012, 0.011, 0.011), Crease_Color=(0.003, 0.003, 0.003),
     Roughness=0.45, Wrinkles=0.6)
_add('leather_saddle', 'Smooth Saddle Leather', 'LEATHER',
     'Smooth, warm tan leather, burnished where it is used.',
     thumb=LEATHER_THUMB, Leather_Color=(0.25, 0.10, 0.035), Crease_Color=(0.08, 0.03, 0.01), Grain=0.15,
     Roughness=0.4, Wear=0.35, Wrinkles=0.25)
_add('leather_oxblood', 'Oxblood Leather', 'LEATHER',
     'Deep red-brown polished leather, like dress shoes.',
     thumb=LEATHER_THUMB, Leather_Color=(0.12, 0.012, 0.012), Crease_Color=(0.03, 0.003, 0.003),
     Roughness=0.32, Grain=0.3, Wear=0.25)
_add('leather_white', 'White Leather', 'LEATHER',
     'Clean white leather, like sneakers or car seats.',
     thumb=LEATHER_THUMB, Leather_Color=(0.70, 0.68, 0.62), Crease_Color=(0.50, 0.48, 0.44), Roughness=0.5,
     Dirt=0.2, Wear=0.1, Wrinkles=0.2, Color_Variation=0.15)
_add('leather_vintage', 'Worn Vintage Leather', 'LEATHER',
     'Well-loved old leather: rubbed, faded and lightly cracked.',
     thumb=LEATHER_THUMB, Leather_Color=(0.12, 0.05, 0.02), Wear=0.6, Edge_Wear=0.8, Cracks=0.35,
     Fading=0.3, Scratches=0.3, Dirt=0.3)
_add('leather_cracked', 'Cracked Old Leather', 'LEATHER',
     'Dried-out, cracked and faded leather.',
     thumb=LEATHER_THUMB, Leather_Color=(0.10, 0.045, 0.02), Cracks=0.9, Fading=0.5, Wear=0.4, Dirt=0.4,
     Roughness=0.7)
_add('leather_suede', 'Tan Suede', 'LEATHER',
     'Velvety, matte suede.',
     thumb=LEATHER_THUMB, Suede=1.0, Leather_Color=(0.18, 0.09, 0.04), Grain=0.2, Wrinkles=0.3)
_add('leather_patent', 'Red Patent Leather', 'LEATHER',
     'Mirror-glossy patent leather.',
     thumb=LEATHER_THUMB, Patent=1.0, Leather_Color=(0.35, 0.0, 0.01), Crease_Color=(0.1, 0.0, 0.003),
     Grain=0.1, Wrinkles=0.2, Dirt=0.0)
_add('leather_croc', 'Crocodile Embossed', 'LEATHER',
     'Green-black leather embossed with crocodile scales.',
     thumb=dict(zoom=0.3), Croc=1.0, Leather_Color=(0.03, 0.05, 0.02), Crease_Color=(0.005, 0.008, 0.003),
     Grain=0.3, Roughness=0.35)
_add('leather_croc_black', 'Black Croc Leather', 'LEATHER',
     'Glossy black croc-embossed leather.',
     thumb=dict(zoom=0.3), Croc=1.0, Croc_Scale=30.0, Leather_Color=(0.012, 0.011, 0.011),
     Crease_Color=(0.002, 0.002, 0.002), Grain=0.2, Roughness=0.25)
_add('leather_sofa', 'Stitched Sofa Leather', 'LEATHER',
     'Cognac leather panels with stitched seams.',
     thumb=dict(zoom=0.3), Stitching=1.0, Panel_Size=0.2, Leather_Color=(0.22, 0.09, 0.03),
     Crease_Color=(0.07, 0.025, 0.01), Thread_Color=(0.5, 0.4, 0.25), Wear=0.25, Wrinkles=0.35)

# ---------------------------------------------------------------------- fabric
FABRIC_THUMB = dict(zoom=0.03)
COARSE_THUMB = dict(zoom=0.08)
CARBON_THUMB = dict(zoom=0.07)
BLACK = (0.012, 0.012, 0.012)
KEVLAR = (0.79, 0.51, 0.045)

_add('fabric_canvas', 'Canvas', 'FABRIC',
     'Sturdy beige cotton canvas.',
     thumb=FABRIC_THUMB)
_add('fabric_canvas_olive', 'Olive Canvas Tarp', 'FABRIC',
     'Army green canvas, stained and dirty.',
     thumb=FABRIC_THUMB, Warp_Color=(0.07, 0.08, 0.035), Weft_Color=(0.06, 0.07, 0.03), Thread_Size=0.0018,
     Stains=0.4, Dirt=0.5, Fading=0.2, overlays=[overlay('DIRT', Amount=0.4, Patches=0.4)])
_add('fabric_denim', 'Blue Denim', 'FABRIC',
     'Indigo denim twill.',
     thumb=FABRIC_THUMB, Weave=2.0, Warp_Color=(0.02, 0.045, 0.13), Weft_Color=(0.22, 0.22, 0.20),
     Thread_Size=0.0008, Fading=0.1, Yarn_Twist=0.6, Fuzz=0.25)
_add('fabric_denim_worn', 'Worn Denim', 'FABRIC',
     'Washed-out, faded denim.',
     thumb=FABRIC_THUMB, Weave=2.0, Warp_Color=(0.03, 0.07, 0.18), Weft_Color=(0.28, 0.28, 0.26),
     Thread_Size=0.0008, Fading=0.55, Pilling=0.2, Yarn_Twist=0.6)
_add('fabric_carbon_twill', 'Carbon Fiber (Twill)', 'FABRIC',
     'Glossy 2x2 twill carbon fiber in clear resin.',
     thumb=CARBON_THUMB, Weave=1.0, Warp_Color=(0.02, 0.02, 0.022), Weft_Color=(0.02, 0.02, 0.022),
     Thread_Size=0.004, Resin=1.0, Fiber_Shine=0.8, Yarn_Twist=0.0, Thread_Gap=0.05, Fuzz=0.0, Roughness=0.3,
     Thread_Variation=0.15, Dirt=0.0)
_add('fabric_carbon_plain', 'Carbon Fiber (Plain)', 'FABRIC',
     'Plain weave carbon fiber in clear resin.',
     thumb=dict(zoom=0.05), Weave=0.0, Warp_Color=(0.02, 0.02, 0.022), Weft_Color=(0.02, 0.02, 0.022),
     Thread_Size=0.003, Resin=1.0, Fiber_Shine=0.8, Yarn_Twist=0.0, Thread_Gap=0.05, Fuzz=0.0, Roughness=0.3,
     Thread_Variation=0.15, Dirt=0.0)
_add('fabric_carbon_dry', 'Dry Carbon Fiber', 'FABRIC',
     'Matte carbon fiber cloth without resin.',
     thumb=CARBON_THUMB, Weave=1.0, Warp_Color=(0.025, 0.025, 0.027), Weft_Color=(0.025, 0.025, 0.027),
     Thread_Size=0.004, Fiber_Shine=0.8, Yarn_Twist=0.0, Thread_Gap=0.05, Fuzz=0.1, Roughness=0.45,
     Dirt=0.0)
_add('fabric_kevlar', 'Kevlar (Aramid)', 'FABRIC',
     'Golden yellow aramid fabric.',
     thumb=dict(zoom=0.05), Warp_Color=KEVLAR, Weft_Color=(0.75, 0.48, 0.04), Thread_Size=0.003,
     Yarn_Twist=0.0, Fiber_Shine=0.5, Roughness=0.55, Thread_Gap=0.08, Fuzz=0.3)
_add('fabric_kevlar_resin', 'Kevlar Composite', 'FABRIC',
     'Twill aramid fabric in glossy resin.',
     thumb=CARBON_THUMB, Weave=1.0, Warp_Color=(0.6, 0.38, 0.03), Weft_Color=(0.58, 0.36, 0.03),
     Thread_Size=0.004, Resin=1.0, Fiber_Shine=0.6, Yarn_Twist=0.0, Thread_Gap=0.05, Fuzz=0.0, Dirt=0.0)
_add('fabric_ballistic_black', 'Ballistic Nylon (Black)', 'FABRIC',
     'Tough basket-weave nylon of bags and tactical gear.',
     thumb=FABRIC_THUMB, Weave=3.0, Warp_Color=BLACK, Weft_Color=BLACK, Thread_Size=0.0009,
     Yarn_Twist=0.1, Fiber_Shine=0.4, Roughness=0.45, Fuzz=0.2)
_add('fabric_ballistic_coyote', 'Ballistic Nylon (Coyote)', 'FABRIC',
     'Coyote brown basket-weave nylon.',
     thumb=FABRIC_THUMB, Weave=3.0, Warp_Color=(0.30, 0.21, 0.11), Weft_Color=(0.28, 0.19, 0.10),
     Thread_Size=0.0009, Yarn_Twist=0.1, Fiber_Shine=0.4, Roughness=0.5, Fuzz=0.2, Dirt=0.2)
_add('fabric_ripstop', 'Ripstop Nylon (Olive)', 'FABRIC',
     'Light nylon with a reinforcing grid.',
     thumb=FABRIC_THUMB, Ripstop=1.0, Warp_Color=(0.08, 0.12, 0.05), Weft_Color=(0.08, 0.12, 0.05),
     Thread_Size=0.0006, Roughness=0.5, Yarn_Twist=0.1, Fiber_Shine=0.3)
_add('fabric_burlap', 'Burlap (Jute)', 'FABRIC',
     'Coarse, open jute sack cloth.',
     thumb=COARSE_THUMB, Warp_Color=(0.30, 0.20, 0.09), Weft_Color=(0.27, 0.18, 0.08), Thread_Size=0.004,
     Thread_Gap=0.45, Yarn_Twist=1.0, Thread_Variation=0.8, Fuzz=0.8, Dirt=0.2)
_add('fabric_wool_twill', 'Grey Wool Twill', 'FABRIC',
     'Soft, fuzzy suit wool.',
     thumb=FABRIC_THUMB, Weave=1.0, Warp_Color=(0.10, 0.10, 0.10), Weft_Color=(0.22, 0.21, 0.19),
     Thread_Size=0.0012, Yarn_Twist=1.0, Fuzz=0.9, Thread_Variation=0.6)
_add('fabric_satin', 'Red Satin', 'FABRIC',
     'Smooth, shiny satin.',
     thumb=dict(zoom=0.02), Weave=4.0, Warp_Color=(0.4, 0.02, 0.05), Weft_Color=(0.3, 0.01, 0.03),
     Thread_Size=0.0005, Roughness=0.3, Fiber_Shine=0.7, Yarn_Twist=0.0, Fuzz=0.0, Dirt=0.0)

# ---------------------------------------------------------------- biomechanical
BIO_THUMB = dict(shape='cylinder')

_add('bio_ribbed_hull', 'Biomech Ribbed Hull', 'ORGANIC',
     'Glossy dark alien machinery: ribs, tubes and bone merged into one.',
     thumb=BIO_THUMB)
_add('bio_xeno_tubes', 'Xeno Tubes', 'ORGANIC',
     'Bundles of ribbed, hose-like tubes.',
     thumb=BIO_THUMB, Tubes=1.0, Ribs=1.0, Plates=0.0, Folds=0.1)
_add('bio_chrome_spine', 'Chrome Vertebrae', 'ORGANIC',
     'Polished, chrome-like vertebrae segments.',
     thumb=BIO_THUMB, Metallic=0.9, Highlight_Color=(0.6, 0.6, 0.62), Base_Color=(0.08, 0.08, 0.085),
     Ribs=0.9, Segments=1.0, Tubes=0.3, Roughness=0.2, Plates=0.0)
_add('bio_bone_plates', 'Bone Armor Plates', 'ORGANIC',
     'Interlocking plates of pale, bony armor.',
     thumb=BIO_THUMB, Plates=1.0, Base_Color=(0.25, 0.22, 0.17), Highlight_Color=(0.6, 0.55, 0.45),
     Cavity_Color=(0.03, 0.025, 0.02), Metallic=0.0, Roughness=0.45, Tubes=0.2, Ribs=0.2, Wetness=0.1)
_add('bio_flesh_wall', 'Flesh Wall', 'ORGANIC',
     'Wet, veiny folds of living tissue.',
     thumb=BIO_THUMB, Base_Color=(0.07, 0.025, 0.02), Highlight_Color=(0.38, 0.14, 0.11),
     Cavity_Color=(0.012, 0.002, 0.002), Metallic=0.0, Subsurface=0.5, Folds=0.8, Veins=0.8, Ribs=0.2,
     Tubes=0.2, Wetness=0.7, Roughness=0.4)
_add('bio_slime_hive', 'Slime Hive', 'ORGANIC',
     'Alien nest wall dripping with glossy, oily slime.',
     thumb=BIO_THUMB, Slime=0.6, Wetness=0.8, Iridescence=0.6, Base_Color=(0.02, 0.025, 0.02),
     Highlight_Color=(0.15, 0.17, 0.12), Metallic=0.2)
_add('bio_obsidian', 'Obsidian Biomech', 'ORGANIC',
     'Black, glassy biomechanical surface with an oily sheen.',
     thumb=BIO_THUMB, Base_Color=(0.01, 0.01, 0.012), Highlight_Color=(0.1, 0.1, 0.12), Metallic=0.2,
     Roughness=0.08, Iridescence=0.3, Wetness=0.2)
_add('bio_rusted', 'Rusted Biomech', 'ORGANIC',
     'Corroded alien machinery in rust and dark iron.',
     thumb=BIO_THUMB, Base_Color=(0.08, 0.03, 0.012), Highlight_Color=(0.3, 0.12, 0.04),
     Cavity_Color=(0.01, 0.005, 0.003), Metallic=0.5, Roughness=0.65, Wetness=0.0, Color_Variation=0.8)
_add('bio_sinew', 'Sinew Cables', 'ORGANIC',
     'Thin, muscle-like cables and tendons.',
     thumb=BIO_THUMB, Tubes=1.0, Tube_Width=0.06, Ribs=0.3, Rib_Density=30.0, Folds=0.5, Veins=0.5,
     Base_Color=(0.09, 0.04, 0.03), Highlight_Color=(0.4, 0.2, 0.15), Metallic=0.0, Subsurface=0.3,
     Wetness=0.6)
_add('bio_alien_skin', 'Alien Skin', 'ORGANIC',
     'Pitted, folded grey-green skin.',
     thumb=BIO_THUMB, Pores=0.8, Folds=0.9, Ribs=0.1, Tubes=0.1, Plates=0.1, Distortion=0.9,
     Base_Color=(0.05, 0.06, 0.045), Highlight_Color=(0.22, 0.25, 0.18), Metallic=0.0, Roughness=0.5,
     Wetness=0.3, Subsurface=0.2)
_add('bio_hive_resin', 'Hive Resin', 'ORGANIC',
     'Dark, glossy resin walls with tubes and ribs.',
     thumb=BIO_THUMB, Base_Color=(0.02, 0.025, 0.03), Highlight_Color=(0.15, 0.2, 0.22), Tubes=0.8,
     Ribs=0.6, Wetness=0.9, Iridescence=0.2, Metallic=0.1)

# ---------------------------------------------------------------- overlays
DUST_THUMB = dict(shape='steps', base='plastic_piano_black')
DIRT_THUMB = dict(shape='steps', base='plastic_white_abs')

_add('dust_light', 'Light Dust', 'DUST',
     'A thin film of dust on top surfaces.',
     thumb=DUST_THUMB, Amount=0.3)
_add('dust_heavy', 'Heavy Dust', 'DUST',
     'Thick, clumpy dust, as if untouched for years.',
     thumb=DUST_THUMB, Amount=0.85, Clumps=0.6, Crevices=0.8)
_add('dust_wiped', 'Dust with Wipe Marks', 'DUST',
     'Dusty surfaces with clean streaks where something brushed past.',
     thumb=DUST_THUMB, Amount=0.6, Wipes=0.5)
_add('dust_ash', 'Ash and Soot', 'DUST',
     'Dark grey ash settled everywhere.',
     thumb=dict(shape='steps', base='plastic_white_abs'), Amount=0.6, Dust_Color=(0.05, 0.05, 0.05),
     Crevices=0.8)
_add('dust_sand', 'Desert Sand', 'DUST',
     'Fine sandy dust.',
     thumb=DUST_THUMB, Amount=0.6, Dust_Color=(0.45, 0.33, 0.18), Clumps=0.5)
_add('dirt_grime', 'Grime', 'DIRT',
     'Everyday grime in corners, low on the object and in faint stains.',
     thumb=DIRT_THUMB)
_add('dirt_heavy', 'Heavy Grime', 'DIRT',
     'Filthy: grime everywhere, thick in corners.',
     thumb=DIRT_THUMB, Amount=1.0, Patches=0.6, Crevices=1.0, Ground_Grime=0.8, Streaks=0.4)
_add('dirt_mud', 'Mud Splatter', 'DIRT',
     'Wet mud thrown up from the ground.',
     thumb=DIRT_THUMB, Amount=0.9, Splatter=0.8, Ground_Grime=0.9, Grime_Height=0.35, Wetness=0.4,
     Dirt_Color=(0.06, 0.04, 0.025), Dirt_Color_2=(0.13, 0.09, 0.05), Patches=0.1)
_add('dirt_streaks', 'Rain Streaks', 'DIRT',
     'Dirty streaks running down from the top.',
     thumb=DIRT_THUMB, Streaks=0.9, Patches=0.1, Crevices=0.5, Ground_Grime=0.3)
_add('dirt_oil', 'Oily Grime', 'DIRT',
     'Black, greasy grime, like in an engine bay.',
     thumb=DIRT_THUMB, Wetness=0.8, Dirt_Color=(0.008, 0.008, 0.008), Dirt_Color_2=(0.03, 0.028, 0.025),
     Crevices=1.0, Patches=0.35)

# Moss grows on top: on the faces that look up, over the edges and into the cracks.
MOSS_THUMB = dict(shape='steps', base='concrete_precast')
ORANGE_LICHEN = (0.40, 0.15, 0.025)

_add('moss_light', 'Light Moss', 'MOSS',
     'A thin green fuzz of moss on the top surfaces.',
     thumb=MOSS_THUMB, Amount=0.35, Thickness=0.4)
_add('moss_cushions', 'Moss Cushions', 'MOSS',
     'Thick, round cushions of moss sitting on top.',
     thumb=MOSS_THUMB, Amount=0.7, Patchiness=0.85, Thickness=1.0, Side_Reach=0.4, Fuzz=0.7)
_add('moss_carpet', 'Moss Carpet', 'MOSS',
     'A dense, even carpet of moss over the tops and down the sides.',
     thumb=MOSS_THUMB, Amount=0.92, Patchiness=0.15, Side_Reach=0.65, Thickness=0.8, Crevices=0.9)
_add('moss_patchy', 'Patchy Moss', 'MOSS',
     'Scattered clumps of moss with bare surface between them.',
     thumb=MOSS_THUMB, Amount=0.4, Patchiness=1.0, Clump_Size=0.6, Crevices=0.4)
_add('moss_wet', 'Wet Moss', 'MOSS',
     'Soaked, deep green moss that glistens a little.',
     thumb=MOSS_THUMB, Amount=0.7, Wetness=0.8, Moss_Color=(0.02, 0.06, 0.012),
     Moss_Color_2=(0.07, 0.15, 0.02), Side_Reach=0.45)
_add('moss_dry', 'Dried Moss', 'MOSS',
     'Moss dried out by the sun: brown and straw-colored with a few green bits.',
     thumb=MOSS_THUMB, Amount=0.6, Dryness=0.75, Moss_Roughness=0.95, Thickness=0.4, Patchiness=0.6)
_add('moss_cracks', 'Moss in the Cracks', 'MOSS',
     'Moss only in corners, gaps and cracks (Cycles or baked mesh maps).',
     thumb=MOSS_THUMB, Amount=0.15, Crevices=1.0, Patchiness=0.3, Side_Reach=0.0)
_add('moss_damp_wall', 'Damp Wall Moss', 'MOSS',
     'Moss and algae rising from the ground up a damp wall, thinning out higher up.',
     thumb=MOSS_THUMB, Amount=0.2, Top_Facing=0.4, Ground_Growth=0.9, Patchiness=0.4,
     Moss_Color=(0.03, 0.06, 0.02), Moss_Color_2=(0.09, 0.14, 0.04), Thickness=0.3)
_add('moss_overgrown', 'Overgrown', 'MOSS',
     'Reclaimed by nature: thick moss everywhere, heaviest on top and at the bottom.',
     thumb=MOSS_THUMB, Amount=0.95, Top_Facing=0.6, Side_Reach=1.0, Ground_Growth=0.8, Patchiness=0.4,
     Crevices=1.0, Thickness=1.0, Lichen=0.3)
_add('moss_lichen', 'Lichen Spots', 'MOSS',
     'Pale grey-green crusty lichen spots on every side, a little moss on top.',
     thumb=MOSS_THUMB, Amount=0.12, Lichen=0.8, Patchiness=0.8, Thickness=0.3)
_add('moss_lichen_orange', 'Orange Lichen', 'MOSS',
     'Bright orange lichen crusts, like on old roof tiles and seaside rocks.',
     thumb=MOSS_THUMB, Amount=0.0, Crevices=0.0, Lichen=0.75, Lichen_Color=ORANGE_LICHEN)
_add('moss_rusty_metal', 'Moss on Rusty Metal', 'MOSS',
     'Moss and lichen taking over abandoned, rusting steel.',
     thumb=dict(shape='steps', base='iron_rust_heavy'), Amount=0.55, Patchiness=0.7, Side_Reach=0.35,
     Lichen=0.35, Dryness=0.2)

# Edge wear and scratches go on top of any material too.
EDGE_THUMB = dict(base='paint_car_red')
SCRATCH_THUMB = dict(base='plastic_piano_black')
RED_OXIDE_PRIMER = (0.26, 0.055, 0.03)

_add('wear_chipped_paint', 'Chipped Paint Edges', 'WEAR',
     'Paint chipped off the edges down to grey primer and bare steel.',
     thumb=EDGE_THUMB, Amount=0.7, Chips=0.02, Primer=0.3)
_add('wear_bare_metal', 'Edges Worn to Bare Metal', 'WEAR',
     'Shiny bare metal along every edge, worn smooth by hands and tools.',
     thumb=EDGE_THUMB, Amount=0.8, Chips=0.0, Chip_Detail=0.3, Underneath_Roughness=0.2)
_add('wear_rusty_chips', 'Rusty Chipped Edges', 'WEAR',
     'Chipped edges and spots, rusted where the steel shows.',
     thumb=EDGE_THUMB, Amount=0.8, Chips=0.05, Rust=0.8, Primer=0.2, Primer_Color=RED_OXIDE_PRIMER)
_add('wear_heavy_chips', 'Heavily Chipped', 'WEAR',
     'Big chips all over and on every edge.',
     thumb=EDGE_THUMB, Amount=1.0, Chips=0.15, Chip_Scale=3.0, Primer=0.4)
_add('wear_primer', 'Worn to Primer', 'WEAR',
     'Top coat worn off the edges, showing red oxide primer.',
     thumb=EDGE_THUMB, Amount=0.7, Underneath_Color=RED_OXIDE_PRIMER, Underneath_Metallic=0.0,
     Underneath_Roughness=0.7)
_add('wear_aluminium', 'Chipped to Aluminium', 'WEAR',
     'Aircraft-style chips: green zinc chromate primer and bright aluminium.',
     thumb=EDGE_THUMB, Amount=0.6, Chips=0.01, Primer=0.5, Primer_Color=(0.30, 0.34, 0.09),
     Underneath_Color=(0.91, 0.92, 0.92), Underneath_Roughness=0.35)
_add('wear_wood', 'Paint Chipped to Wood', 'WEAR',
     'Painted wood chipped down to the bare wood.',
     thumb=dict(base='plastic_white_abs'), Amount=0.8, Chips=0.03, Underneath_Color=(0.32, 0.18, 0.07),
     Underneath_Metallic=0.0, Underneath_Roughness=0.75, Paint_Thickness=0.7)
_add('wear_rubbed', 'Rubbed Edges', 'WEAR',
     'Edges rubbed lighter and smoother: for wood, leather and plastic.',
     thumb=dict(base='wood_walnut'), Rubbed=1.0, Amount=0.7, Chips=0.0, Chip_Detail=0.3)
_add('wear_polished', 'Polished Edges', 'WEAR',
     'Edges polished bright: for bare and dark metals.',
     thumb=dict(base='gunmetal'), Rubbed=1.0, Lighten=0.4, Amount=0.8, Chips=0.0, Chip_Detail=0.2)
_add('scratch_light', 'Light Scratches', 'SCRATCH',
     'A few fine scratches.',
     thumb=SCRATCH_THUMB, Amount=0.3, Fine_Scratches=0.3)
_add('scratch_heavy', 'Heavy Scratches', 'SCRATCH',
     'Deep scratches everywhere, some through to the metal.',
     thumb=SCRATCH_THUMB, Amount=0.9, Fine_Scratches=0.6, Reveal=0.6, Depth=0.7)
_add('scratch_to_metal', 'Scratched to Metal', 'SCRATCH',
     'Scratches through the paint showing bare steel.',
     thumb=dict(base='paint_car_red'), Amount=0.6, Reveal=1.0, Fine_Scratches=0.2)
_add('scratch_swirls', 'Swirl Marks', 'SCRATCH',
     'Circular polishing marks that show in reflections: car paint, polished metal.',
     thumb=dict(base='paint_car_blue', zoom=0.35), Amount=0.1, Fine_Scratches=0.2, Swirls=0.8)
_add('scratch_scuffs', 'Scuffs', 'SCRATCH',
     'Dull scuffed patches and scratches: plastic, floors, furniture.',
     thumb=SCRATCH_THUMB, Amount=0.3, Fine_Scratches=0.5, Scuffs=0.7)
_add('scratch_sliding', 'Sliding Scratches', 'SCRATCH',
     'Scratches all in one direction, where something slid across.',
     thumb=SCRATCH_THUMB, Amount=0.6, Straight=1.0, Fine_Scratches=0.3)
_add('scratch_hairline', 'Hairline Scratches', 'SCRATCH',
     'Dense, very fine scratches: screens, glass, lenses, polished metal.',
     thumb=SCRATCH_THUMB, Amount=0.05, Fine_Scratches=0.9, Lighten=0.3, Depth=0.3)
