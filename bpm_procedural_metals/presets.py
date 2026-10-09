# SPDX-License-Identifier: GPL-3.0-or-later
"""The material library: every preset is a generator plus slider values.

Only values that differ from the generator defaults need to be listed.
Colors are linear RGB (what Blender color pickers store internally).
A material preset can bring overlays (dirt, dust, wear) along; overlay
presets are layered on top of whatever material an object already has.
"""

# (id, label, description, short label for the category buttons, number stored in .blend files)
CATEGORIES = (
    ('METAL', 'Bare Metal', 'Polished, brushed, aged and rusty metals', 'Metal', 1),
    ('PAINT', 'Painted Metal', 'Painted, chipped and weathered metal', 'Painted', 2),
    ('MILITARY', 'Military', 'Military paint and camouflage with mud, dust and edge wear built in', 'Military', 10),
    ('WOOD', 'Wood', 'Raw, varnished, painted, weathered and charred wood', 'Wood', 3),
    ('PLASTIC', 'Plastic', 'Glossy, matte and textured plastic, new, old or dirty', 'Plastic', 4),
    ('GLASS', 'Glass', 'Clear, tinted, frosted, textured and stained glass, spotless or grimy', 'Glass', 9),
    ('LENS', 'Lenses & Visors', 'Camera lenses, coated optics, mirrored visors and reflectors: glossy and '
     'reflective, not see-through', 'Lenses', 11),
    ('LEATHER', 'Leather', 'Smooth, pebbled, suede, patent, croc and worn leather', 'Leather', 5),
    ('FABRIC', 'Fabric & Composites', 'Canvas, denim, nylon, carbon fiber, kevlar...', 'Fabric', 6),
    ('ORGANIC', 'Biomechanical', 'Giger-style organic machinery: ribs, tubes, bone, slime', 'Organic', 7),
    ('OVERLAY', 'Dirt & Dust', 'Layers of dirt or dust that go on top of any material', 'Dirt & Dust', 8),
    ('WEAR', 'Edge Wear & Scratches', 'Chipped or rubbed edges, scratches and swirl marks that go on top of any '
     'material', 'Wear', 12),
)
OVERLAY_CATEGORIES = ('OVERLAY', 'WEAR')  # presets of these categories go on top of other materials

# generator -> gallery category
GENERATOR_CATEGORY = {
    'METAL': 'METAL', 'PAINT': 'PAINT', 'CAMO': 'MILITARY', 'WOOD': 'WOOD', 'PLASTIC': 'PLASTIC', 'GLASS': 'GLASS',
    'LENS': 'LENS', 'LEATHER': 'LEATHER', 'FABRIC': 'FABRIC', 'ORGANIC': 'ORGANIC', 'DIRT': 'OVERLAY',
    'DUST': 'OVERLAY', 'WEAR': 'WEAR', 'SCRATCH': 'WEAR',
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


def by_category(category):
    return [p for p in PRESETS if category in {'ALL', p['category']}]


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
     Color_1=(0.40, 0.42, 0.43), Color_2=(0.02, 0.03, 0.06), Color_3=(0.015, 0.015, 0.015), Color_4=(0.10, 0.11, 0.12),
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
