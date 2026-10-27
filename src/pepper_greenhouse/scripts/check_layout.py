#!/usr/bin/env python3
# Copyright 2026 funfun
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Verify the generated greenhouse assets against the layout definition.

Run after scripts/generate_world.py:

    python3 scripts/check_layout.py
    python3 scripts/check_layout.py --root /path/to/pepper_greenhouse
"""
from __future__ import annotations

import argparse
import math
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))
from layout import Layout  # noqa: E402

MAX_LAYOUT_TRIANGLES = 250_000
MAX_VISUAL_TRIANGLES = 600_000


def stl_triangle_count(path: Path) -> int:
    """Return the triangle count of a valid binary STL file."""
    data = path.read_bytes()
    assert len(data) >= 84, f'{path}: too short'
    count = struct.unpack_from('<I', data, 80)[0]
    expected = 84 + 50 * count
    assert len(data) == expected, f'{path}: size {len(data)} != {expected}'
    return count


def model_triangles(model_dir: Path) -> int:
    """Sum the triangles of every mesh in a model directory."""
    meshes = sorted((model_dir / 'meshes').glob('*.stl'))
    assert meshes, f'{model_dir}: no meshes'
    return sum(stl_triangle_count(path) for path in meshes)


def check_model(model_dir: Path, name: str, collision_count: int) -> None:
    """Check one generated model directory."""
    assert model_dir.is_dir(), f'missing model {model_dir}'
    config = ET.parse(model_dir / 'model.config').getroot()
    assert config.findtext('name') == name, f'{model_dir}/model.config name'
    sdf = ET.parse(model_dir / 'model.sdf').getroot()
    model = sdf.find('model')
    assert model is not None, f'{model_dir}/model.sdf has no model'
    assert model.get('name') == name
    assert model.findtext('static') == 'true'
    collisions = model.findall('.//collision')
    assert len(collisions) == collision_count, (
        f'{model_dir}: {len(collisions)} collisions, expected {collision_count}'
    )
    for mesh in model.findall('.//mesh/uri'):
        assert mesh.text and mesh.text.startswith(f'model://{name}/meshes/')


def roof_panel_count(layout: Layout) -> int:
    """Return the number of sloped roof panels between gutters/ridges."""
    profile = sorted(set(layout.roof_gutters + layout.roof_ridges))
    return len(profile) - 1


def shell_collision_count(layout: Layout) -> int:
    """Return the expected static collisions of the shell model."""
    return (4                                   # walls
            + roof_panel_count(layout)          # roof slopes
            + len(layout.column_x) * len(layout.column_y)  # columns
            + 16                                # end-wall fans
            + 9                                 # circulation fans
            + len(layout.roof_ridges)           # ridge vents
            + len(layout.pipe_y_positions)      # yellow pipes
            + len(layout.row_centers)           # row wires
            + len(layout.transverse_wire_x))    # transverse wires


def bed_collision_count(layout: Layout) -> int:
    """Return the expected collisions of one bed segment (gutter + canopy)."""
    return 2 * len(layout.row_centers)


def check_shell(model_dir: Path, layout: Layout) -> None:
    """Check the shell glass, wall and roof collision settings."""
    sdf = ET.parse(model_dir / 'model.sdf').getroot()
    glass = sdf.find(".//visual[@name='glass']")
    assert glass is not None, 'shell has no glass visual'
    transparency = glass.findtext('transparency')
    assert transparency is not None
    assert 0.7 <= float(transparency) <= 0.9, transparency
    assert glass.findtext('cast_shadows') == 'false'
    collisions = sdf.findall('.//collision')
    panels = [c for c in collisions
              if (c.get('name') or '').startswith('roof_panel_')]
    names = {c.get('name') or '' for c in collisions}
    assert any(n.startswith('column_') for n in names), 'shell: no columns'
    assert any(n.startswith('pipe_') for n in names), 'shell: no pipes'
    assert any(n.startswith('wire_row_') for n in names), 'shell: no wires'
    assert len(collisions) == shell_collision_count(layout), (
        f'shell: {len(collisions)} collisions, '
        f'expected {shell_collision_count(layout)}')
    assert len(panels) == roof_panel_count(layout), (
        f'shell: {len(panels)} roof collisions, '
        f'expected {roof_panel_count(layout)}')
    # Roof panels must carry a rotated pose so ray sensors see a sloped roof.
    for panel in panels:
        pose = panel.findtext('pose').split()
        assert len(pose) == 6, f'{panel.get("name")}: pose {pose}'
        assert abs(float(pose[3])) > 0.1, f'{panel.get("name")}: no rot_x'
        size = panel.findtext('geometry/box/size').split()
        assert math.isclose(float(size[0]), layout.site_size, abs_tol=1e-6)
        assert math.isclose(float(size[2]), 0.02, abs_tol=1e-6)


def check_world(path: Path, layout: Layout, visual: bool) -> None:
    """Check one generated world."""
    assert path.is_file(), f'missing world {path}'
    world = ET.parse(path).getroot().find('world')
    assert world is not None, f'{path} has no world'
    uris = [include.findtext('uri') for include in world.findall('include')]
    for uri in (
        'model://pepper_greenhouse_shell',
        'model://pepper_beds_mid',
        'model://pepper_beds_end',
    ):
        assert uri in uris, f'{path}: missing {uri}'
    assert uris.count('model://pepper_beds_end') == 2
    dense = 'model://pepper_plants_dense' in uris
    assert dense == visual, f'{path}: dense overlay flag {dense} != {visual}'

    rails = world.find("model[@name='rails']")
    assert rails is not None, f'{path}: no rails model'
    collisions = rails.findall('.//collision')
    assert len(collisions) == 2
    for collision in collisions:
        size = [float(v) for v in collision.findtext('geometry/box/size').split()]
        assert math.isclose(size[0], layout.rail_length, abs_tol=1e-6)
        assert math.isclose(size[1], layout.rail_width, abs_tol=1e-6)
    poses = [collision.findtext('pose').split() for collision in collisions]
    ys = sorted(float(pose[1]) for pose in poses)
    assert math.isclose(ys[0], -layout.wheel_y, abs_tol=1e-6)
    assert math.isclose(ys[1], layout.wheel_y, abs_tol=1e-6)

    floor = world.find("model[@name='floor']")
    assert floor is not None, f'{path}: no floor model'
    size = [float(v) for v in floor.findtext('.//collision/geometry/box/size').split()]
    assert math.isclose(size[0], layout.site_size, abs_tol=1e-6)
    assert math.isclose(size[1], layout.site_size, abs_tol=1e-6)


def check(root: Path) -> None:
    """Run every layout and asset check."""
    layout = Layout.from_yaml(root / 'config' / 'greenhouse.yaml')
    layout.validate()
    models = root / 'models'

    check_model(models / 'pepper_greenhouse_shell', 'pepper_greenhouse_shell',
                shell_collision_count(layout))
    check_shell(models / 'pepper_greenhouse_shell', layout)
    check_model(models / 'pepper_beds_mid', 'pepper_beds_mid',
                bed_collision_count(layout))
    check_model(models / 'pepper_beds_end', 'pepper_beds_end',
                bed_collision_count(layout))
    check_model(models / 'pepper_plants_dense', 'pepper_plants_dense', 0)

    check_world(root / 'worlds' / 'pepper_greenhouse.world', layout, False)
    check_world(root / 'worlds' / 'pepper_greenhouse_visual.world', layout, True)

    shell = model_triangles(models / 'pepper_greenhouse_shell')
    mid = model_triangles(models / 'pepper_beds_mid')
    end = model_triangles(models / 'pepper_beds_end')
    dense = model_triangles(models / 'pepper_plants_dense')
    layout_total = shell + mid + 2 * end
    visual_total = layout_total + dense
    assert layout_total < MAX_LAYOUT_TRIANGLES, layout_total
    assert visual_total < MAX_VISUAL_TRIANGLES, visual_total

    print(layout.summary())
    print(f'shell / mid / end / dense triangles: '
          f'{shell} / {mid} / {end} / {dense}')
    print(f'layout total : {layout_total} triangles '
          f'(budget {MAX_LAYOUT_TRIANGLES})')
    print(f'visual total : {visual_total} triangles '
          f'(budget {MAX_VISUAL_TRIANGLES})')
    print('assets OK')


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path,
                        default=Path(__file__).resolve().parents[1],
                        help='package root (default: parent of scripts/)')
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        check(root)
    except AssertionError as error:
        print(f'CHECK FAILED: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
