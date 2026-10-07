# SPDX-License-Identifier: GPL-3.0-or-later
"""The material library: every preset is a generator plus slider values.

Only values that differ from the generator defaults need to be listed.
Colors are linear RGB (what Blender color pickers store internally).
A material preset can bring overlays (dirt, dust) along; overlay presets
are layered on top of whatever material an object already has.
"""

# (id, label, description, short label for the category buttons)
CATEGORIES = (
    ('METAL', 'Bare Metal', 'Polished, brushed, aged and rusty metals', 'Metal'),
    ('PAINT', 'Painted Metal', 'Painted, chipped and weathered metal', 'Painted'),
    ('WOOD', 'Wood', 'Raw, varnished, painted, weathered and charred wood', 'Wood'),
    ('PLASTIC', 'Plastic', 'Glossy, matte and textured plastic, new, old or dirty', 'Plastic'),
    ('LEATHER', 'Leather', 'Smooth, pebbled, suede, patent, croc and worn leather', 'Leather'),
    ('FABRIC', 'Fabric & Composites', 'Canvas, denim, nylon, carbon fiber, kevlar...', 'Fabric'),
    ('ORGANIC', 'Biomechanical', 'Giger-style organic machinery: ribs, tubes, bone, slime', 'Organic'),
    ('OVERLAY', 'Dirt & Dust', 'Layers of dirt or dust that go on top of any material', 'Dirt & Dust'),
)

# generator -> gallery category
GENERATOR_CATEGORY = {
    'METAL': 'METAL', 'PAINT': 'PAINT', 'WOOD': 'WOOD', 'PLASTIC': 'PLASTIC', 'LEATHER': 'LEATHER',
    'FABRIC': 'FABRIC', 'ORGANIC': 'ORGANIC', 'DIRT': 'OVERLAY', 'DUST': 'OVERLAY',
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
    return preset['category'] == 'OVERLAY'


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
     thumb=FABRIC_THUMB, Weave=2.0, Warp_Color=(0.012, 0.03, 0.09), Weft_Color=(0.30, 0.30, 0.28),
     Thread_Size=0.0008, Fading=0.15, Yarn_Twist=0.6)
_add('fabric_denim_worn', 'Worn Denim', 'FABRIC',
     'Washed-out, faded denim.',
     thumb=FABRIC_THUMB, Weave=2.0, Warp_Color=(0.02, 0.05, 0.13), Weft_Color=(0.35, 0.35, 0.33),
     Thread_Size=0.0008, Fading=0.7, Pilling=0.2, Yarn_Twist=0.6)
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
