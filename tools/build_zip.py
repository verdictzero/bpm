# SPDX-License-Identifier: GPL-3.0-or-later
"""Build the installable add-on zip into dist/ using Blender's extension builder.

    python3 tools/build_zip.py /path/to/blender

The zip installs on Blender 4.2 and newer: Edit > Preferences > Get Extensions >
(arrow menu at the top right) > Install from Disk...
"""

import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, 'bpm_procedural_metals')
DIST = os.path.join(ROOT, 'dist')


def main():
    blender = sys.argv[1] if len(sys.argv) > 1 else shutil.which('blender')
    if not blender:
        raise SystemExit('usage: python3 tools/build_zip.py /path/to/blender')
    for root, dirs, _files in os.walk(SOURCE):
        for d in dirs:
            if d == '__pycache__':
                shutil.rmtree(os.path.join(root, d))
    os.makedirs(DIST, exist_ok=True)
    for name in os.listdir(DIST):
        if name.endswith('.zip'):
            os.remove(os.path.join(DIST, name))
    subprocess.run([blender, '--factory-startup', '--command', 'extension', 'validate', SOURCE], check=True)
    subprocess.run([blender, '--factory-startup', '--command', 'extension', 'build',
                    '--source-dir', SOURCE, '--output-dir', DIST], check=True)
    print('\n'.join(os.path.join(DIST, n) for n in os.listdir(DIST)))


main()
