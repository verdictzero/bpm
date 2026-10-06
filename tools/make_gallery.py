# SPDX-License-Identifier: GPL-3.0-or-later
"""Make the gallery images in docs/ from the add-on thumbnails (needs Pillow).

    python3 tools/make_gallery.py
"""

import importlib.util
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THUMBS = os.path.join(ROOT, 'bpm_procedural_metals', 'thumbnails')
DOCS = os.path.join(ROOT, 'docs')

spec = importlib.util.spec_from_file_location('presets', os.path.join(ROOT, 'bpm_procedural_metals', 'presets.py'))
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)


def font(size):
    for name in ('DejaVuSans.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 'Arial.ttf'):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def sheet(presets, path, cols=6, cell=200, label_h=34):
    rows = (len(presets) + cols - 1) // cols
    img = Image.new('RGB', (cols * cell, rows * (cell + label_h)), (34, 34, 36))
    draw = ImageDraw.Draw(img)
    f = font(14)
    for i, preset in enumerate(presets):
        x, y = (i % cols) * cell, (i // cols) * (cell + label_h)
        thumb_path = os.path.join(THUMBS, preset['id'] + '.png')
        if os.path.exists(thumb_path):
            thumb = Image.open(thumb_path).convert('RGBA').resize((cell, cell), Image.LANCZOS)
            bg = Image.new('RGBA', thumb.size, (52, 52, 55, 255))
            bg.alpha_composite(thumb)
            img.paste(bg.convert('RGB'), (x, y))
        name = preset['name']
        w = draw.textlength(name, font=f)
        draw.text((x + (cell - w) / 2, y + cell + 8), name, fill=(225, 225, 225), font=f)
    img.save(path, optimize=True)
    print(path, img.size)


def main():
    os.makedirs(DOCS, exist_ok=True)
    for cat, label, _ in P.CATEGORIES:
        sheet(P.by_category(cat), os.path.join(DOCS, 'gallery_%s.png' % cat.lower()))


main()
