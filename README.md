# BPM – Procedural Metals for Blender

52 ready-made **metal** and **painted metal** materials for Blender, with plain
sliders you can tweak, and a **one-click bake** that turns them into normal image
textures (Base Color, Metallic, Roughness, Normal, Height, AO) for game engines or
any other software.

You don't need to know anything about nodes or procedural materials. Click a
material, click **Apply**, move some sliders, click **Bake**.

![Bare metal materials](docs/gallery_metal.png)
![Painted metal materials](docs/gallery_paint.png)

Works with **Blender 4.2 or newer**. Tested on Blender 4.2 LTS, 4.5 LTS and 5.2 LTS
on Linux; it is pure Python, so Windows and macOS work the same way.

---

## 1. Install (once)

1. Download **[`dist/bpm_procedural_metals-1.0.0.zip`](dist/bpm_procedural_metals-1.0.0.zip)**
   (on GitHub, click the file, then the download button). **Don't unzip it.**
2. Open Blender and go to **Edit › Preferences › Get Extensions**.
3. Click the small **⌄ arrow** in the top-right corner and pick **Install from Disk…**
4. Select the zip file. Done: "BPM - Procedural Metals" now shows up as enabled.

> Shortcut: you can also just drag the zip file into the Blender window.

## 2. Use it

![The BPM sidebar](docs/screenshot_main.png)

1. In the 3D view, **click your object** to select it.
2. Press **N** (with the mouse over the 3D view) to open the sidebar and click the
   **BPM** tab.
3. Click the big picture to see all materials, pick one, then click
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

## 3. Bake to textures

Open the **Bake Textures** panel (scroll down in the BPM tab) and choose a mode:

| Mode | What you get | Use it for |
|---|---|---|
| **Objects** | Textures that fit your selected objects' UVs, including edge wear and dirt from its shape | Exporting a model to Unity, Unreal, Godot, Sketchfab, glTF/FBX… |
| **Seamless Tile** | Square textures of the active material that repeat with no visible seams | Texture libraries, walls, floors, other 3D programs |

<img src="docs/screenshot_bake.png" width="300" alt="Bake panel">

Pick a **Resolution** (2K is a good start) and **Quality**, then click **Bake**.
The status bar at the bottom shows the progress; press **Esc** to cancel.

* **Where are the files?** In a `BPM_Textures` folder next to your `.blend` file.
  If you never saved the `.blend` file, they go to `BPM_Textures` in your home
  folder. Click **Open Folder** after baking.
* **UVs are handled for you.** Objects without UVs (or with broken or overlapping
  UVs) get a new UV map called `BPM_Bake` automatically.
* **Your object switches to the baked material** so you can check the result. Your
  procedural material is kept: click **Back to Procedural** to keep editing, then
  bake again any time. *Use Baked Textures* switches back.
* It works for **any** material that uses a Principled BSDF, not only BPM ones.

Files (for an object called `Crate`):

| File | Content | Color space in other programs |
|---|---|---|
| `Crate_BaseColor.png` | Color | sRGB |
| `Crate_Metallic.png` | White = metal, black = paint, rust, dirt | Linear / non-color |
| `Crate_Roughness.png` | White = matte, black = glossy | Linear / non-color |
| `Crate_Normal.png` | Surface detail (normal map) | Linear / non-color, type *Normal map* |
| `Crate_Height.png` | Height (16-bit) for parallax/displacement | Linear / non-color |
| `Crate_AO.png` | Soft shadows in crevices | Linear / non-color |
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
  is set up so the glTF exporter picks everything up.

### More options

* **Normal Map Format** – OpenGL (Blender, Unity, Godot, glTF) or DirectX (Unreal).
* **Bit Depth** – 16-bit PNGs are smoother but bigger (Height is always 16-bit).
* **Always Make New UVs** – ignore the object's own UVs.
* **Device** – *Auto* uses your graphics card if it is set up in
  *Edit › Preferences › System › Cycles Render Devices*; otherwise the CPU.
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

Everything is built from two adjustable "generators" (bare metal and painted metal),
so every material has the full set of sliders: brushed lines, hammer dents, grain
and pits, galvanized spangle, heat tint, scratches, fingerprints, polished edges,
tarnish, rust or patina, dirt, chipped paint with primer, stripes, metallic flakes,
clear coat, sun fading and rust streaks.

Patterns are placed in 3D around your object (no UVs needed, no seams) and sized in
real meters, so they look the same whatever the object's scale is. *Fit Pattern Size
to Object* adapts them to small or large objects when you apply a material.

## 5. Fully automated (command line)

`bpm_cli.py` (in this repository) runs everything without opening Blender's window.
Replace `blender` with the path to your Blender program.

```bash
# list all materials
blender -b -P bpm_cli.py -- list

# seamless texture sets for every material, 1K, into ./textures
blender -b -P bpm_cli.py -- tile --preset all --size 1024 --out ./textures

# one material for Unreal: DirectX normals + packed ORM
blender -b -P bpm_cli.py -- tile --preset "Hazard Stripes" --size 2048 --directx --orm

# put a material on objects of a .blend file, then bake them
blender -b model.blend -P bpm_cli.py -- apply --preset steel_brushed --objects Body,Lid --save
blender -b model.blend -P bpm_cli.py -- bake --objects Body,Lid --size 2048 --out ./textures --save
```

Add `--help` after a command for all options (`--quality`, `--maps`, `--16bit`,
`--unity`, `--gpu`, `--tile-size`, `--scale`, `--seed`, …).

## 6. Troubleshooting

* **I can't find the BPM tab.** Hover the mouse over the 3D view and press **N**. If it
  isn't there, check *Edit › Preferences › Add-ons* that "BPM - Procedural Metals" is
  enabled.
* **The object looks grey/flat.** The viewport is in *Solid* mode: press **Z** ›
  *Material Preview*.
* **Details are much too big or too small.** Use the **Scale** slider or
  **Fit to Object Size**.
* **I see no worn edges.** Edge wear needs edges: it shows on corners and bevels, not
  on smooth spheres. Raise *Edge Wear* (painted) or *Edge Polish* (bare metal), or
  *Edge Width* in the *Wear* section.
* **Baking takes long.** Use a lower resolution or *Fast* quality first. A set-up GPU
  (see *Device* above) is much faster.
* **Strange smeared patches in baked textures.** The object's UVs overlap in a way
  that can't be detected automatically. Tick **Always Make New UVs** and bake again.
* **Textures look wrong in my game engine.** Only the Base Color is sRGB; all other
  maps must be imported as *linear / non-color* data, and the normal map as a *normal
  map*. Unreal needs *DirectX* normals.
* **Changing one object also changes another.** They share the material. Click the
  number button next to the material name in *Adjust Material* (Make Unique).

## 7. For developers

```
bpm_procedural_metals/   the add-on (Blender extension)
  generators.py          the two node-group generators and their sliders
  features.py            shared pattern building blocks (scratches, rust, edge masks...)
  nodebuilder.py         small Python DSL that writes shader node trees
  presets.py             the 52 presets (generator + slider values)
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
sRGB 188), that tiles are seamless, that the computed tile normal maps match Cycles'
own bump mapping, that every setting the bake changes is restored, and that no
shader comes close to Cycles' fixed shader-stack limit.

License: GPL-3.0-or-later (like Blender itself).
