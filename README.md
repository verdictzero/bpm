# BPM – Procedural Materials for Blender

346 ready-made materials for Blender — **bare metal, painted metal, porcelain enamel
(1950s fridges, stoves, bathtubs, graniteware, enamel signs), military paint and
camouflage, concrete, terrain (cratered moons, asteroids, Mars) and glowing lava and magma,
51 gradients (linear, radial, angular, spiral… projected from any side), glowing lights
(neon, fluorescent tubes, light panels, LEDs, screens — clean, dusty, bug-filled or burnt
out), wood, plastic (from showroom new to cracked, burnt and trashed), glass,
lenses and visors, leather, fabric & composites (carbon fiber, kevlar, ballistic nylon…), and
H.R. Giger-style biomechanical surfaces** — plus 26
**overlays (dirt, dust, edge wear and scratches)** that you can stack on top of *any*
material, and **decals**: put any image (with its normal, roughness, metallic and height
maps if it has them) on your model by dragging a box over it. Every material has plain sliders you can tweak, and
one click on **Auto Texture** turns it into normal image textures (Base Color,
Metallic, Roughness, Normal, Height, AO) for game engines or any other software: it
unwraps the UVs, packs them, bakes, saves the files and puts the textures on the
object — for one object, the selected ones or the whole scene.

You don't need to know anything about nodes, UVs or procedural materials. Click a
material, click **Apply**, move some sliders, click **Auto Texture**. Liked what you made?
**Save Preset** keeps it in the library, with its own thumbnail.

![Bare metal materials](docs/gallery_metal.png)
![Painted metal materials](docs/gallery_paint.png)
![Porcelain enamel](docs/gallery_enamel.png)
![Military paint and camouflage](docs/gallery_military.png)
![Concrete](docs/gallery_concrete.png)
![Terrain and lava](docs/gallery_terrain.png)
![Gradients](docs/gallery_gradient.png)
![Lights and neon](docs/gallery_light.png)
![Wood materials](docs/gallery_wood.png)
![Plastic materials](docs/gallery_plastic.png)
![Glass materials](docs/gallery_glass.png)
![Lenses and visors](docs/gallery_lens.png)
![Leather materials](docs/gallery_leather.png)
![Fabric and composite materials](docs/gallery_fabric.png)
![Biomechanical materials](docs/gallery_organic.png)
![Dirt and dust overlays](docs/gallery_overlay.png)
![Edge wear and scratch overlays](docs/gallery_wear.png)

Works with **Blender 4.2 or newer**. Tested on Blender 4.2 LTS, 4.5 LTS and 5.2 LTS
on Linux; it is pure Python, so Windows and macOS work the same way.

---

## 1. Install (once)

1. Download **[`dist/bpm_procedural_metals-1.8.1.zip`](dist/bpm_procedural_metals-1.8.1.zip)**
   (on GitHub, click the file, then the download button). **Don't unzip it.**
2. Open Blender and go to **Edit › Preferences › Get Extensions**.
3. Click the small **⌄ arrow** in the top-right corner and pick **Install from Disk…**
4. Select the zip file. Done: "BPM - Procedural Materials" now shows up as enabled.

> **Updating from an older version (1.0 – 1.7)?** Just install the new zip the same
> way, on top of the old one: it replaces the old version (no need to uninstall first
> or restart Blender), and your `.blend` files keep their materials and settings.

> Shortcut: you can also just drag the zip file into the Blender window.

## 2. Use it

![The BPM sidebar](docs/screenshot_main.png)

1. In the 3D view, **click your object** to select it.
2. Press **N** (with the mouse over the 3D view) to open the sidebar and click the
   **BPM** tab.
3. Pick a category (Metal, Enamel, Military, Terrain, Gradients, Lights, Wood, Plastic, Glass, Fabric, Dirt & Dust, Wear…),
   click the big picture to see its materials, pick one, then click
   **Apply to Selected**.
4. To see the material, switch the viewport to **Material Preview**: press **Z** and
   choose *Material Preview* (or click the third sphere icon at the top right of the
   3D view).
5. Change the look in **Adjust Material**. The most useful sliders are at the top;
   click the section names (*Base*, *Wear*, *Aging*, …) to see more.
   * **Scale** makes all the details bigger or smaller.
   * **Seed** (or the 🔄 button) gives a new random variation.
   * The ↶ button resets everything to the original preset.

In Edit Mode, *Apply* puts the material only on the **selected faces**.

### Save your own presets

Set up a material the way you like it (sliders, colors and the overlays on top of it),
then click **Save Preset** in *Adjust Material*, type a name (and a description if you
like) and click OK. It shows up in the library under **My Presets** and in the category of
its material (a saved gradient is listed with the gradients too), with a thumbnail of
how it looks. Apply it like any other preset; **Load Preset** and ↶ (reset) work with
it too.

* Saving under a name you already used **replaces** that preset (handy to update it).
* *Include Overlays* (on by default) saves the dirt, dust and wear layers with it.
  Decals stay with the model, and hidden layers are left out.
* To delete one, pick it in the library and click the 🗑 button next to *Your own preset*.
  Materials you made from it stay as they are.
* Your presets are kept in a file outside the add-on, so updating or reinstalling BPM
  keeps them. **Open Presets Folder** (in *My Presets*) shows it: copy
  `user_presets.json` and the `.png` thumbnails to another computer to take them along,
  then click the reload button.

### Dirt, dust, edge wear and scratches on top of anything

Two categories hold overlays, layers that go on top of another material:

* **Dirt & Dust** – grime, heavy grime, mud splatter, rain streaks, oily grime,
  light / heavy dust, dust with wipe marks, ash and soot, desert sand.
* **Wear** – edge wear (paint chipped to grey primer and steel, to bare shiny metal,
  rusty chips, heavy chips, worn to red primer, aircraft-style zinc chromate and
  aluminium, paint chipped to wood, edges just rubbed lighter for wood, leather or
  plastic, polished edges for metal) and scratches (light, heavy, through the paint to
  the metal, swirl marks, scuffs, scratches all in one direction, fine hairlines).

Picking one shows **Add on Top of Material** instead of *Apply*: the layer goes on top
of whatever material the object already has — a BPM material or any other material
that uses a Principled BSDF (most do). The **Add Overlay** button in the overlays
panel lists them all too.

The **Overlays** panel lists the layers of the active object's material:

<img src="docs/screenshot_overlays.png" width="300" alt="The Overlays panel">

* the 👁 button hides / shows a layer (compare with and without),
* the arrows change the order (the top layer covers the ones below),
* 🔄 gives the layer a new random variation, ✕ removes it,
* the sliders control how much dirt there is and where it goes: *Crevices* (corners
  and gaps), *Ground Grime* (rising from the bottom of the object), *Streaks*,
  *Splatter*, *Top Facing* (dust settles on top), *Wipes*, *Wetness*, *Fill* (how much
  the layer hides the relief below)…
* edge wear has *Amount*, *Edge Width* and *Chips* (all over), what shows through
  (*Underneath Color*, *Metallic*, *Roughness*, *Primer*) or *Rubbed* for edges that are
  only worn lighter; scratches have *Amount*, *Fine Scratches*, *Swirls*, *Scuffs*,
  *Straight* (all one way) and *Reveal* (cut through to the metal or just lighten).
  Edge wear needs Cycles or a bake to show, like all edge effects, unless the object
  had a **Shape Analysis** (below): then it shows everywhere, EEVEE included.

Overlays are baked into the textures automatically, in both bake modes. Some
materials (for example *Dirty White Plastic* or *Olive Canvas Tarp*) come with an
overlay already; it shows up in the panel like any other layer.

### Shape Analysis: edge wear and grime that land exactly

Without it, BPM finds edges and corners *live* while rendering: quick, but only in
Cycles, and dirt only creeps a little way into corners. **Shape Analysis** (its own
panel, like the *mesh maps* of 3D-Coat or Substance) looks at each object once and
stores three maps with it:

* **Convex**: how close every point is to an outer edge, so edge wear and chips sit
  exactly on the edges, with an even width all the way along;
* **Concave**: how close every point is to an inner corner or crease (also where the
  object touches another one, or the floor), so grime builds up solidly *into* every
  corner;
* **Occlusion**: how enclosed every point is, so pockets, insets, slots and the
  underside fill up with dirt.

<img src="docs/shape_analysis.png" width="640" alt="Heavy Grime (only its Crevices part) without and with Shape Analysis">

Every edge wear overlay, dirt overlay and built-in grime reads them automatically.
They also work in **EEVEE** and Material Preview, where the live edges don't.

1. Pick the **Objects** (Active, Selected or Scene).
2. Click **Analyze Shape** (about 10 s per object at the 1K default).
3. The panel says *Analyzed* for the active object. After you edit the mesh it says
   *the mesh changed*: click Analyze Shape again.

**Options**: *Map Size*, *Quality*, *Edge Reach* (the widest edge wear can get),
*Corner Reach* (how far dirt can build up out of a corner), *Occlusion Reach* (how far
away a surface still counts as enclosing), *Include Other Objects* (off: each object is
analyzed on its own, without the floor or its neighbours), *Device* (the same as for
baking, below) and **Remove Mesh Maps**.
Reaches are a share of the object's size, so they suit small and big objects alike.

**Auto Texture** analyzes every object without up-to-date maps first (*Analyze
Shape First*, on by default), so the baked textures get the precise version.

**It checks your mesh.** Thin plates and sheet metal get edges as wide as on solid
parts, smooth (shade smooth) low-poly surfaces don't turn into fake creases, and
the analysis tells you when something will spoil it: normals that point inwards
(it copes, but other tools won't), *mixed* normals (some faces flipped: use *Mesh >
Normals > Recalculate Outside*), maps too small for the edge reach (raise *Map Size*),
or Array / Mirror modifiers that make copies share one spot of the maps (apply them
first). Changing a modifier also marks the analysis as out of date.

#### View the Maps: check what the analysis found

Open **View the Maps** in the Shape Analysis panel and pick what to show on every
mesh in the scene (the viewport switches to Material Preview by itself):

* **All**: red = outer edges, green = inner corners, blue = occlusion;
* **Edges**, **Corners**, **Occlusion**: one map in gray (white = most);
* **UV Layout**: a checker in the maps' own UV layout; stretched or tiny squares
  show where the maps are blurry.

Objects without maps show **dark purple**. Your materials stay as they are: click
**Off** (or **Show Materials** in the Library panel, or apply any material) and
everything is back, viewport shading included. Baking and analyzing hide the view
while they run.

**Save as Images** writes the active (or selected) objects' maps as PNG files into
the folder below it (`//BPM_Mesh_Maps/` = next to the `.blend` file):
`<Object>_MeshMaps.png` (all three channels) and `_Edges`, `_Corners`, `_Occlusion.png`,
and shows them in an open Image Editor. The viewport colors pass through Blender's
color management (AgX/Filmic look); the saved images hold the exact values.

The maps live in a UV map called `BPM_Maps` and an image called `BPM Mesh Maps` packed
into the `.blend` file. Leave them be; **Remove Mesh Maps** removes both. Exports and
bakes always use your own UV maps, never `BPM_Maps`.

### Terrain: craters with real depth

The **Terrain & Lava** category makes ground you can fly over: moons, asteroids, Mars,
battlefields, deserts, and lava from molten to cold basalt. Craters come in two sizes
(*Craters* and *Small Craters*) with *Crater Depth*, *Rim Height*, *Central Peaks*,
*Ejecta* (the blanket of thrown-out rock), bright *Rays* and *Crater Age* (fresh and
sharp, or worn soft); then *Hills*, *Boulders*, *Bedrock*, *Regolith* (powdery soil),
*Dark Patches* (lunar seas), *Metal Flecks*, *Scorch*, *Puddles* and *Wetness*.

Lava has *Heat* (0 = cold rock), *Temperature* (the color of the glow, from dull red to
yellow-white), *Emission Strength*, *Crust* with *Plate Size* and glowing *Crack Width*,
*Flow Direction* and *Stretch*, *Ropes* (pahoehoe), *Clinker* (rubbly aa), *Vesicles*
(gas bubbles), *Glassy* (obsidian), *Sulfur* and *Ash*. Lava really lights up the scene
in Cycles, and the glow is baked into an `_Emission.png` map.

By default, craters are drawn with bump (shading only), which is fast and fine from
above. For craters that really dent the surface (and show on the outline of a planet):

1. Open the **Displacement** section of *Adjust Material* and click **Displace
   Geometry**. It adds a *BPM Displacement* modifier (a Simple Subdivision, so the shape
   stays the same) that divides the mesh finely enough, and turns *Real Displacement* up.
2. *Real Displacement* sets how much of the relief moves the surface (0 = bump only,
   1 = full depth). It works in Cycles and EEVEE.
3. **Remove Displacement** takes the modifier off again.

Use a mesh with enough faces to start with (a subdivided plane for ground, a UV sphere
or an Ico Sphere for a moon): the modifier picks its level from the face count. Baking
gives a 16-bit `_Height.png` with all the relief, ready for a game engine's displacement
or parallax, whether or not *Real Displacement* is on.

### Gradients: from any side, in any shape

Pick a gradient, then shape it in *Adjust Material*:

* **Type** – *Linear*, *Mirrored* (from the middle out to both sides), *Radial*
  (circles), *Spherical* (balls in 3D), *Angular* (sweeps around like a clock hand),
  *Diamond*, *Square*, *Cube* (boxes in 3D), *Spiral*, *Slope* (tops vs. sides: snow or
  moss on top) and *Facing* (how much the surface faces the camera: rim glow,
  color-shift paint).
* **Projection** – what it is laid onto: *Bounds* (across the object's box, so it fits
  any object), *Object* or *World* (in meters: world space stays put when the object
  moves), *UV* (across the UV map) or *Screen* (across the camera view).
* **View Axis** – the side the gradient is projected from: **Front**, **Top**, **Side**,
  or type any direction. *Angle* turns it within that view (0° = left to right,
  90° = bottom to top); *Center*, *Size* and *Aspect* place it and stretch it.
* **Colors** – 2 to 5 *Color Stops*, *Interpolation* (Linear, Smooth or Constant for
  hard bands), *Spacing* (Even, or Custom with a *Position* per color) and *Color
  Mixing* (*Perceptual* blends evenly to the eye, like design apps; *Linear Light* is
  Blender's Color Ramp, where bright colors take more room).
* **Shape** – *Shift*, *Bias*, *Repeat* with *Repeat Mode* (Clamp, Repeat, Ping-Pong)
  for bands, rings and rays, *Steps* for flat bands, *Noise* for a hand-made wobble.
* **Surface** – *Metallic* and *Roughness* at both ends (paint fading to metal), *Relief*
  and *Glow* (neon tubes, skies, light panels; baked into `_Emission.png`).

### Porcelain enamel: 1950s appliances, tubs and enamelware

Porcelain (or vitreous) enamel is glass fused onto steel: stoves, cast iron bathtubs,
sinks, enamel pots and mugs, and enamel signs. The glossy 1950s refrigerators were
mostly baked *synthetic* enamel on steel rather than true porcelain, but they look the
same up close, so they are here too (turquoise, seafoam, pink, canary yellow, the 70s
coppertone, harvest gold and avocado…). Enamel doesn't wear like paint — it chips:

* **Enamel** – *Enamel Color*, *Roughness*, *Depth* (the glassy clear glaze on top),
  *Waviness* of pressed steel and *Orange Peel*.
* **Decoration** – *Speckles* (graniteware), *Marbling* (agateware swirls) and a colored
  *Rim* on edges like enamel mugs.
* **Wear** – *Chips* all over and *Edge Chips* on edges and corners, which break through to
  the dark blue-black *Ground Coat* and to bare steel; *Thin Edges*, *Crazing* (hairline
  cracks full of dirt), pot *Scratches* and *Dulling* from scouring.
* **Steel Underneath** – *Rust* in the chips and *Rust Stains* running down the enamel.
* **Aging** – *Yellowing*, *Chalking* (sun-bleached signs), kitchen *Grease* and *Dirt*.

### Lights & neon: dirty glowing things

Pick a *Type* — **Neon Tube**, **Panel** (with optional *Hot Spots* of the lamps
behind), **LED Dots**, **Screen** (red, green and blue pixels, *Scanlines* for an old CRT)
or **Strips** — then set its *Light Color* and *Emission Strength*. *Power* switches it
off: 0 shows the unlit tube or panel. Then make it old:

* **Faults** – *Unevenness*, *Dead Sections* (or dead pixels), *End Blackening* of old
  neon and fluorescent tubes (*Ends Along* says where the ends are: along the UV map for
  neon bent from a curve, or along X, Y or Z for straight tubes), *Yellowing* and
  *Cracks*.
* **Dirt** – *Dust*, brown *Grime* that tints the light, dead *Bugs* and fly specks,
  *Smudges* and dirt in crevices. All of it blocks the glow, so a dirty light is dimmer
  and blotchy where the dirt is.

The glow is baked into `_Emission.png`. For a halo around the tubes, add a *Glare*
(Bloom) node in the compositor, or turn on bloom in your game engine.

### Decals: logos, stencils, signs

<img src="docs/screenshot_decals.png" width="600" alt="A decal on a model and the Decals panel">

1. In the **Decals** panel, click **Open** and pick an image (a PNG with a transparent
   background works best). PBR maps saved next to it with the same name are used too:
   `Logo_Normal.png`, `Logo_Roughness.png`, `Logo_Metallic.png`, `Logo_Height.png`
   (and the image itself may be called `Logo_BaseColor.png`).
2. Click **Place Decal: Drag a Box** and drag a rectangle over your model in the 3D view.
   A box is made on the surface under the rectangle, and everything inside the box gets
   the decal. You can still orbit and zoom while placing; right-click or Esc cancels.
3. The box is selected: **move** (G), **scale** (S) or **rotate** (R) it, and the decal
   follows. Surfaces turned away from the box don't get it (*Angle Limit*), so it doesn't
   smear down the sides.
4. The panel shows its settings: *Opacity*, *Wear* (chipped away, like an old stencil),
   *Angle Limit*, *Roughness* and *Metallic* (when it has no maps for them), *Normal
   Strength*, *DirectX Normal Map*, *Relief*, *Tint*, and its images.
5. **Auto Texture** bakes decals into the textures like everything else. If you moved a
   box onto another object, baking puts the decal on it by itself (or click
   **Update Decal**).

A decal is a layer of the material, listed with the overlays as *Decal: …*: dirt or dust
added afterwards goes on top of it, and the arrows move it up or down; ✕ there takes it
off that one material (until you click **Update Decal**). The trash button in the
Decals panel deletes a decal (deleting its box does too); duplicating a box (Shift+D)
makes a second decal. The `.blend` file keeps its decals even on a computer without BPM.

## 3. Turn it into textures

Open the **Bake Textures** panel (scroll down in the BPM tab) and choose a mode:

| Mode | What you get | Use it for |
|---|---|---|
| **Objects** | Textures that fit your objects' UVs, including edge wear and dirt from their shape | Exporting a model to Unity, Unreal, Godot, Sketchfab, glTF/FBX… |
| **Seamless Tile** | Square textures of the active material that repeat with no visible seams | Texture libraries, walls, floors, other 3D programs |

<img src="docs/screenshot_bake.png" width="300" alt="Bake panel">

### Auto Texture: everything in one click

1. Pick a **Resolution** (2K is a good start) and **Quality**.
2. Pick which **Objects**: **Active** (just the one you clicked last), **Selected**
   (all selected objects) or **Scene** (every visible mesh in the scene).
3. Click **Auto Texture**. It first runs a **Shape Analysis** of objects that don't have
   one yet (see above), then, for every object, it:
   1. unwraps the UVs with **Smart UV Project** (Blender's default settings),
   2. packs them with Blender's own **Pack Islands** (with a small gap between the
      pieces, so colors don't bleed),
   3. bakes every ticked map,
   4. saves the textures as PNG files,
   5. switches the object to a material that uses them.

The status bar at the bottom shows the progress; press **Esc** to cancel (objects that
were already finished keep their textures; the others stay exactly as they were).
**Ctrl+Z** undoes the whole thing.

* **Where are the files?** In a `BPM_Textures` folder next to your `.blend` file.
  If you never saved the `.blend` file, they go to `BPM_Textures` in your home
  folder. Click **Open Folder** after baking.
* **The new UVs** go into a UV map called `BPM_Bake`. It becomes the *first* UV map, so
  FBX / glTF exports and game engines (which read the first one) use it. Your old UV
  maps stay, untouched.
* **Your procedural material is kept**: click **Back to Procedural** to keep editing,
  then click Auto Texture again any time. *Use Baked Textures* switches back.
* **Linked duplicates** (Alt+D copies that share a mesh and material) share one set of
  textures. Objects with no material, or that can't be baked, are skipped; the reason
  is listed under the result.
* It works for **any** material that uses a Principled BSDF, not only BPM ones.

### Bake with Current UVs

**Bake with Current UVs** does the same, but keeps the UVs your objects already have —
for models you unwrapped by hand. Objects without UVs (or with broken or overlapping
UVs) still get a new `BPM_Bake` UV map automatically.

Files (for an object called `Crate`):

| File | Content | Color space in other programs |
|---|---|---|
| `Crate_BaseColor.png` | Color | sRGB |
| `Crate_Metallic.png` | White = metal, black = paint, rust, dirt | Linear / non-color |
| `Crate_Roughness.png` | White = matte, black = glossy | Linear / non-color |
| `Crate_Normal.png` | Surface detail (normal map) | Linear / non-color, type *Normal map* |
| `Crate_Height.png` | Height (16-bit) for parallax/displacement | Linear / non-color |
| `Crate_AO.png` | Soft shadows in crevices | Linear / non-color |
| `Crate_Transmission.png` *(glass only)* | White = see-through, black = opaque (dirt, lead, wire) | Linear / non-color |
| `Crate_Opacity.png` *(glass only)* | The same, inverted, for an engine's alpha / opacity | Linear / non-color |
| `Crate_Emission.png` *(lava, glowing gradients)* | Glow color (black = no glow); use it as the emissive map, with the *Emission Strength* of the material | sRGB |
| `Crate_ORM.png` *(option)* | R = AO, G = Roughness, B = Metallic | Linear / non-color |
| `Crate_MetallicSmoothness.png` *(option)* | Unity: RGB = Metallic, A = Smoothness | Linear / non-color |

### Game engine cheat sheet

* **Unreal Engine** – in *More Options* choose **Normal Map Format: DirectX** and tick
  **Packed ORM**. Connect ORM red to *Ambient Occlusion*, green to *Roughness* and blue
  to *Metallic*, and turn **sRGB off** for the ORM texture.
* **Unity** – keep **OpenGL** normals, tick **Unity Metallic/Smoothness** and use it as
  the *Metallic Map* (Source: Metallic Alpha). Set the normal texture's type to *Normal map*.
* **Godot 4** – keep **OpenGL** normals. Use the maps directly, or the ORM texture with
  an *ORMMaterial3D*.
* **glTF / GLB export from Blender** – just export: the baked material, including AO,
  is set up so the glTF exporter picks everything up (glass too: transmission and IOR).
* **Glass in Unity / Unreal / Godot** – make the material transparent (translucent) and
  use `_Opacity.png` as its alpha / opacity.

### More options

* **Normal Map Format** – OpenGL (Blender, Unity, Godot, glTF) or DirectX (Unreal).
* **Bit Depth** – 16-bit PNGs are smoother but bigger (Height is always 16-bit).
* **Use Baked Material** / **Auto UV Unwrap** – for *Bake with Current UVs* (Auto
  Texture always unwraps and always switches to the textures).
* **Device** – *Auto* uses your graphics card if it is set up in
  *Edit › Preferences › System › Cycles Render Devices*; otherwise the CPU. If the
  graphics card fails (out of memory, a driver reset), the CPU finishes the job and is
  used until you restart Blender. Also used by Shape Analysis.
* **Tile Size** – how many meters of surface one seamless tile shows.

## 4. The materials

**Bare metal (30):** polished chrome, steel, brushed stainless steel, brushed and
sandblasted aluminium, anodized aluminium (blue, red, black), polished and brushed
gold, tarnished silver, polished, hammered and verdigris copper, polished and aged
brass, antique bronze, heat-tinted titanium, burnt exhaust steel, gunmetal, blued
steel, cast iron, hammered wrought iron, galvanized steel, weathered zinc, lightly
rusted steel, heavily rusted iron, Corten weathering steel, satin nickel, pewter.

**Painted metal (22):** chipped industrial yellow, military olive drab, desert tan,
worn fire-engine red, metallic car paint (blue, candy red), black powder coat,
hammertone (green, silver), peeling teal, ship hull grey, hazard stripes, sci-fi
white, safety orange, sun-faded blue, vintage cream enamel, worn matte black, old
tractor green, vintage mint, navy machinery, red oxide primer, rusted-through paint.

**Porcelain enamel (28):** 1950s refrigerators (turquoise, seafoam green, pastel pink,
canary yellow, butter cream, appliance white, cherry red), the 70s coppertone, harvest
gold and avocado green, a worn turquoise fridge and a rusty barn-find fridge, greasy stove
top, black enameled grate, cast iron bathtub, antique clawfoot tub, vintage farmhouse
sink, blue and black graniteware, white enamel mug, chipped camping mug, red agateware,
blue swirl enamelware, enameled cast iron, red, weathered and cobalt street enamel signs,
crazed antique enamel.

**Military (22):** plain colors (olive drab, NATO green, desert tan, panzer grey,
Soviet green, navy haze grey) and camouflage schemes (NATO three-tone, woodland,
WWII ambush, tiger stripes, desert three-color, digital woodland and desert, urban,
splinter, naval dazzle, winter whitewash, arctic, ghost grey aircraft, Soviet
three-tone, battle-worn olive, muddy woodland). Mud, dust, grime, rain streaks, edge
wear, chips, scratches, primer and rust are built in: every one has its own slider.

**Concrete (22):** fresh, smooth precast, white architectural, board-formed, brutalist
wall (formwork panels and tie holes), polished floor, exposed aggregate, sidewalk slabs,
block wall — and the worn and damaged ones: weathered, cracked, spalled with rusty rebar,
ruined, bullet-riddled, military bunker, mossy, salt-stained, garage floor (oil), wet,
fire-damaged, dirty underpass, bridge pier.

**Wood (15):** oak floorboards, varnished walnut, knotty pine, curly maple, cherry,
polished mahogany, ebony, teak boat deck, shipping pallet, peeling barn red, white
painted planks, weathered grey wood, driftwood, charred wood (shou sugi ban),
scorched planks.

**Plastic (31):** glossy red, textured black, white ABS, toy brick yellow, piano
black, car dashboard (leather grain), ribbed rubber grip, translucent orange,
recycled (flecked), swirled recycled, sun-faded blue, brown Bakelite, marbled red
Catalin, glitter, pearl white — and the dirty and wrecked ones: yellowed retro beige,
smoker-yellowed, dirty white plastic, grimy garbage bin, old dusty toy, weathered garden
chair, cracked old plastic, sun-rotted, burnt, scorched black, gouged cutting board,
stained food container, sticker residue, oily shop plastic, abandoned playground slide,
trashed plastic.

**Glass (19):** clear, frosted, green bottle, amber bottle, cobalt blue, smoked, milk
glass, reeded, hammered, wired safety glass, stained glass window, antique window
glass — and the worn and grimy ones: smudged, dusty, dirty window, abandoned window,
scratched, cracked, sea glass.

**Lenses & visors (17):** reflective, glossy surfaces you can't see through: camera
lens (purple and green coating), vintage amber lens, blue-coated lens, night vision
lens, ruby scope lens, iridescent (dichroic) coating, gold visor, mirrored sunglasses,
blue mirror visor, smoked visor, black glass panel, red sensor eye, red tail light and
amber reflector (with prisms), Fresnel lens, dusty old lens, cracked lens.

**Leather (12):** brown, black, smooth saddle, oxblood, white, worn vintage, cracked
old leather, tan suede, red patent, crocodile embossed (green, black), stitched sofa
leather.

**Fabric & composites (15):** canvas, olive canvas tarp, blue denim, worn denim,
carbon fiber (twill, plain, dry), kevlar (aramid fabric and resin composite),
ballistic nylon (black, coyote), ripstop nylon, burlap, grey wool twill, red satin.

**Terrain & lava (27):** lunar highlands, lunar mare, lunar surface, fresh crater
field, lunar regolith close-up, carbonaceous, stony and metallic asteroids, Martian
ground, shell-cratered battlefield, rocky desert, volcanic ash plain, icy moon — and
lava: molten lava, lava lake, cooling lava crust, glowing cracks, magma, churning magma,
pahoehoe (hot and cooled), aa lava (advancing and cooled), cooled basalt, obsidian,
sulfur vent rock, ash-covered lava field.

**Gradients (51):** black to white, sunset, daylight and night skies, ocean depths,
fire, rainbow, thermal camera, viridis, magma, turbo, teal & orange, cyan to magenta,
pastel dream, mint & peach, hand-dyed ombre, retro stepped sunset, diagonal stripes,
soft bands, neon tube, horizon glow, heat-tinted titanium, chrome to gold, copper to
bronze, paint fading to metal, conic chrome, spotlight, vignette, glowing orb, target
rings, ripples, neon ring, soft ellipse, soap bubble, color wheel, sunburst, radar
sweep, candy and hypnotic spirals, diamond, pyramid panel, retro tunnel, box falloff,
snow and moss on top, rim glow, color-shift paint, holographic foil, studio backdrop,
UV ramp, height fade (world).

**Lights & neon (24):** red neon, dirty pink neon, dusty blue neon, failing green neon,
old diner neon, abandoned neon, argon purple neon, white neon, unlit neon tube,
fluorescent tube, blackened fluorescent tube, bug-filled light cover, yellowed office
panel, failing hospital panel, grimy lightbox sign, emergency exit light, LED matrix,
dirty LED sign, warm LED strip, sci-fi glow strips, grimy sci-fi panel, green CRT
screen, grimy old monitor, cracked screen.

**Biomechanical (11):** H.R. Giger-style surfaces where bone, sinew, tubing and
machinery merge: biomech ribbed hull, xeno tubes, chrome vertebrae, bone armor
plates, flesh wall, slime hive, obsidian biomech, rusted biomech, sinew cables, alien
skin, hive resin.

**Overlays (26):** 10 dirt and dust, 9 edge wear and 7 scratches — see above.

Everything is built from a handful of adjustable "generators", so every material of
a family has the full set of sliders. A few examples:

* **Wood** – growth rings that are really 3D (end grain, side grain and the arches of
  flat-sawn boards appear where they would on real lumber), knots, pores, curly figure,
  planks with gaps, varnish, stain, paint that peels along the grain, weathering,
  cracks, charring.
* **Plastic** – molded stipple texture, leather grain, grip ribs, recycled flecks,
  marbling (Bakelite, Catalin), glitter, translucency, scratches, scuffs, stress-whitened
  edges, fingerprints, sun fading, yellowing, grime stuck in the texture — and damage:
  cracks, knife gouges, burns (melted, blistered char with a scorched halo), stains with
  tide lines and sticky sticker residue with paper bits.
* **Porcelain enamel** and **Lights** – see their sections above.
* **Military paint** – up to four camouflage colors with their amounts and patch sizes;
  *Stretch* turns blotches into stripes, *Digital* snaps them to square pixels,
  *Angular* to straight-edged shards (splinter, dazzle); hard or soft (sprayed)
  edges; sun fading; winter whitewash that wears off; edge wear and chips down to
  primer and steel, scratches, rust and rust streaks; mud caked on the lower part,
  splatter, wet mud, dust, grime in crevices and rain streaks.
* **Concrete** – cement color and blotches, sand, stones (aggregate) and air holes,
  polish; finishes: formwork boards with wood grain, formwork panels with tie holes,
  broom grooves, cut joints, blocks with mortar; damage: cracks, chipped edges, spalling
  with rusty reinforcing bars, erosion, impact craters; stains: rust streaks, water
  stains, white salt (efflorescence), dirt, moss, oil, soot, wetness.
* **Lenses** – lens color, roughness, IOR, the colored reflections of lens coatings
  (*Coating* buttons: amber, purple, blue, green, magenta), mirror coatings (gold,
  silver, blue…), fake inner depth, Fresnel lens rings, hexagonal reflector prisms,
  scratches, fingerprints, dust, haze and cracks.
* **Glass** – tint, frosting, milkiness, refraction (IOR), the waves and bubbles of
  old glass, reeded and hammered textures, wire mesh, stained glass with lead came,
  scratches, chipped edges, cracks, sea-glass weathering, fingerprints, dust, grime
  film, hard-water spots and rain streaks. Dirt and dust are opaque: they block the
  view through the glass (the dirt & dust overlays do too).
* **Leather** – pebbled grain, wrinkles, pores, croc scales, suede, patent gloss,
  stitched seams, rubbed and worn areas, cracks, fading.
* **Fabric** – real thread-by-thread weaves (plain, twill, denim, basket, satin),
  ripstop grid, twisted or straight fibers, fuzz, resin coating with directional fiber
  shine for carbon fiber and kevlar, fading, pilling, stains.
* **Terrain** – two sizes of craters with depth, rims, central peaks, ejecta, rays and
  age, hills, boulders, bedrock, regolith, dark patches, metal flecks, scorch marks,
  puddles; real displacement (see *Terrain* above).
* **Lava** – heat and glow color by temperature, crust plates with glowing cracks, flow
  direction and stretch, pahoehoe ropes, aa clinker, gas bubbles, glassy obsidian,
  sulfur and ash; real displacement.
* **Biomechanical** – ribs (vertebrae, ribbed hoses) grouped into segments, bundles of
  tubes, bony plates, folds, veins, pores, organic distortion, wetness, slime and an
  oily rainbow sheen.

Patterns are placed in 3D around your object (no UVs needed) and sized in real
meters, so they look the same whatever the object's scale is. *Fit Pattern Size to
Object* adapts them to small or large objects when you apply a material. (Fabric
weaves are projected from the side each face points to: perfect on boxy shapes; on
round shapes, or for clothes with UV maps, bake a seamless tile — see below.)

## 5. Fully automated (command line)

`bpm_cli.py` (in this repository) runs everything without opening Blender's window.
Replace `blender` with the path to your Blender program.

```bash
# list all materials
blender -b -P bpm_cli.py -- list

# seamless texture sets for every material, 1K, into ./textures
blender -b -P bpm_cli.py -- tile --preset all --size 1024 --out ./textures

# carbon fiber with a layer of dust on top
blender -b -P bpm_cli.py -- tile --preset "Carbon Fiber (Twill)" --overlay dust_light --size 2048

# one material for Unreal: DirectX normals + packed ORM
blender -b -P bpm_cli.py -- tile --preset "Hazard Stripes" --size 2048 --directx --orm

# put a material on objects of a .blend file (add --overlay dirt_grime for dirt), then bake them
blender -b model.blend -P bpm_cli.py -- apply --preset steel_brushed --objects Body,Lid --save
blender -b model.blend -P bpm_cli.py -- apply --preset dust_heavy --objects all --save
blender -b model.blend -P bpm_cli.py -- bake --objects Body,Lid --size 2048 --out ./textures --save

# Auto Texture every mesh of a .blend file (new UVs, bake, save, apply) and save it
blender -b model.blend -P bpm_cli.py -- auto --objects all --size 2048 --save

# only analyze the shape of every mesh (Shape Analysis), then save
blender -b model.blend -P bpm_cli.py -- maps --objects all --save

# ... and also write the maps as PNG images to check them
blender -b model.blend -P bpm_cli.py -- maps --objects all --images ./mesh_maps
```

`auto` analyzes shapes first; `--no-shape-analysis` skips that and `--maps-size`,
`--maps-quality` set it up. Add `--help` after a command for all options (`--quality`, `--maps`, `--16bit`,
`--unity`, `--gpu`, `--tile-size`, `--scale`, `--seed`, `--overlay`, …).

## 6. Troubleshooting

* **I can't find the BPM tab.** Hover the mouse over the 3D view and press **N**. If it
  isn't there, check *Edit › Preferences › Add-ons* that "BPM - Procedural Materials" is
  enabled.
* **The object looks grey/flat.** The viewport is in *Solid* mode: press **Z** ›
  *Material Preview*.
* **Details are much too big or too small.** Use the **Scale** slider or
  **Fit to Object Size**.
* **I see no worn edges.** Edge wear needs edges: it shows on corners and bevels, not
  on smooth spheres. Raise *Edge Wear* (painted) or *Edge Polish* (bare metal), or
  *Edge Width* in the *Wear* section.
* **Baking takes long.** Use a lower resolution or *Fast* quality first. A set-up GPU
  (see *Device* above) is much faster. Very detailed meshes also take a few seconds
  each to unwrap and pack.
* **"Out of GPU memory", "device lost" or "UR_RESULT_ERROR_DEVICE_LOST" in the console
  (Shape Analysis or baking).** The graphics card ran out of memory or its driver
  stopped a job that took too long. The add-on notices, does that object again on the
  CPU and stays on the CPU until you **restart Blender** (a crashed graphics card stays
  unusable until then). If it keeps happening: update the graphics driver, lower *Map
  Size* or *Quality*, close other programs that use the graphics card, switch the 3D
  view out of *Material Preview* / *Rendered* while analyzing, or set **Device** to
  *CPU*. Laptop and integrated GPUs (e.g. Intel Arc laptop chips, which share memory
  with the system) hit this most often.
* **Strange smeared patches in baked textures.** The object's UVs overlap in a way
  that can't be detected automatically. Use **Auto Texture**: it always makes fresh UVs.
* **Auto Texture skipped an object.** The reason is listed under the result: it has no
  material (apply one first), it isn't a mesh (*Object › Convert › Mesh*), it is
  disabled in viewports, or it already has the maximum of 8 UV maps (delete one in
  *Properties › Object Data › UV Maps*). **Scene** only includes visible objects.
* **One half of my mirrored model has the other half's textures.** A *Mirror*
  modifier (or *Array*) reuses the same UVs for the copies, so they share textures.
  Apply the modifier first if each half needs its own.
* **Textures look wrong in my game engine.** Only the Base Color is sRGB; all other
  maps must be imported as *linear / non-color* data, and the normal map as a *normal
  map*. Unreal needs *DirectX* normals.
* **Changing one object also changes another.** They share the material. Click the
  number button next to the material name in *Adjust Material* (Make Unique).
* **"Add Overlay" says the material has no Principled BSDF.** Overlays need a
  material built on a Principled BSDF node (the default for new materials). Apply a
  BPM material or a new default material first.
* **I can't see the weave / leather grain / wood rings.** They have real-world sizes
  (threads are about a millimeter), so they only show up close. Lower **Scale** to make
  them bigger, or raise the bake resolution.
* **Dirt doesn't collect in the corners in the viewport.** Click **Analyze Shape** in
  *Shape Analysis*: then corners and insets fill up in every view. Without it, crevice
  and edge effects need Cycles (or baking); click **Preview in Cycles** in *Adjust
  Material*.
* **Dirt doesn't build up far enough into a corner.** Raise the overlay's *Crevices*
  slider, or *Corner Reach* in the Shape Analysis options (then analyze again).
* **The edge wear overlay shows nothing.** Run **Analyze Shape**, or preview it in
  Cycles (**Preview in Cycles**), or just Auto Texture. It shows on corners and bevels,
  not on smooth spheres.
* **Edge wear or dirt is in the wrong place after I edited the mesh.** Shape Analysis
  remembers the old shape: the panel says *the mesh or its modifiers changed*. Click
  Analyze Shape again.
* **Edge wear or dirt looks wrong even right after analyzing.** Open *View the Maps*
  (Shape Analysis panel) and look at *Edges* / *Corners*: a whole side white or
  missing usually means flipped normals (*Mesh > Normals > Recalculate Outside*); blocky
  edges mean the maps are too small (raise *Map Size*). Read the analysis' warnings.
* **Lens coating colors are missing in my game engine.** They come from Blender's
  *thin film* setting, which game engines don't have; the baked material in Blender
  keeps it. The engine still gets the glossy, dark (or mirrored) lens.
* **A decal is stretched over the side of my model.** Lower its *Angle Limit*, or make
  the box thinner (scale it along its depth).
* **A decal doesn't show on an object I moved its box onto.** Click **Update Decal** in
  the Decals panel (baking does it by itself).
* **Camouflage patches are too big or too small.** Change *Camo Scale* in the
  *Camouflage* section (or *Scale* for everything).
* **Craters look flat from the side.** Bump only shades the surface. Click **Displace
  Geometry** in the *Displacement* section (see *Terrain* above).
* **Displacement looks blocky or jagged.** The mesh needs more faces: subdivide it
  (or start from a denser mesh), then click Displace Geometry again.
* **Lava, neon or a glowing gradient looks washed out.** Very bright glow turns white
  (and saturated neon turns pastel) in the default *AgX* view; lower *Emission
  Strength*, or *Heat* for lava, or pick *Render Properties › Color Management › View
  Transform › Standard*.
* **The blackened ends of a fluorescent tube are in the wrong place.** Set *Ends Along*
  (in *Faults*) to the axis the tube runs along; *UV* is for neon made from curves.
* **Enamel mugs have no rim, or enamel has no chipped edges.** Rims and edge chips need
  edges: preview in Cycles, click **Analyze Shape** or bake.
* **A material from an older version has no *Cracks*, *Burns*… sliders.** Materials keep
  the node setup they were made with, so old files look exactly the same after an update.
  Click **Update Material** in *Adjust Material* to get the new sliders (all settings are
  kept); loading a preset does it by itself.
* **My saved presets are gone after reinstalling.** They live outside the add-on and
  stay; click the reload button in *My Presets*. If you moved the files, put them back
  in the folder **Open Presets Folder** shows.
* **Glass doesn't show what is behind it in Material Preview.** EEVEE needs
  *Render Properties › Raytracing* turned on for that; Cycles (**Preview in Cycles**)
  always shows it.
* **A glass window looks warped.** Give the pane some thickness (*Add Modifier ›
  Solidify*), like real glass: a single flat plane bends the view like the surface of
  a swimming pool.

## 7. For developers

```
bpm_procedural_metals/   the add-on (Blender extension)
  generators.py          registry of all generators
  mat_*.py               one generator per family: metal, paint, enamel, camo
                         (military), concrete, terrain (terrain + lava), gradient,
                         light, wood, plastic, glass, lens, leather, fabric, organic
                         (sliders + node tree)
  overlays.py            dirt, dust, edge wear and scratch overlays (layer on any
                         material)
  decals.py              box-projected decals (each one is an overlay with its own
                         node group)
  gencommon.py           shared sliders and helpers of the generators
  features.py            shared pattern building blocks (scratches, rust, edge masks...)
  nodebuilder.py         small Python DSL that writes shader node trees
  presets.py             the 372 presets: 346 materials + 26 overlays
  user_presets.py        your own saved presets (a JSON file outside the add-on)
  library.py             creating / editing materials and overlay stacks
  bake.py                baking engine (object + seamless tile)
  ui.py, operators.py    sidebar panels and buttons
  cli.py                 command line interface (used by bpm_cli.py)
tests/run_tests.py       headless test suite
tools/                   thumbnail renderer, gallery maker, zip builder
```

```bash
# tests (run with every Blender version you care about)
blender -b --factory-startup --python-exit-code 1 -P tests/run_tests.py
# re-render gallery thumbnails, then the README gallery images (needs Pillow)
blender -b --factory-startup -P tools/render_thumbnails.py -- --size 256 --samples 64
python3 tools/make_gallery.py
# build the installable zip into dist/
python3 tools/build_zip.py /path/to/blender
```

The tests check, among other things, that baked colors are exact (linear 0.5 →
sRGB 188), that tiles of every family (with overlays) are seamless, that the computed
tile normal maps match Cycles' own bump mapping, that overlays stack, reorder and come
off cleanly and end up in the bake, that baked glass stays see-through (dirt on it
doesn't), that Auto Texture's UVs are packed without overlaps
while materials keep reading their old UVs during the bake, that every setting the bake
changes is restored,
that baked lenses keep their coating, that gradients run the right way and only glow when
asked to, that lights bake their glow (and none when switched off), that chipped enamel
and damaged plastic really change the bake, that older plastic materials upgrade without
losing their settings, that saved presets come back (with their overlays) after a restart, that digital camouflage really is made of
square pixels, that decals land where their box is, follow it, come off when it is
deleted and get baked, and that no shader — not even a material with four overlays — comes
close to Cycles' fixed shader-stack limit.

License: GPL-3.0-or-later (like Blender itself).
