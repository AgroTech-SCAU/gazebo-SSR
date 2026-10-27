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
Generate the 100 x 100 m pepper greenhouse world and its static models.

The generator writes binary STL meshes merged by material, three model SDFs
(shell, mid beds, end beds), one optional dense-plant overlay and two world
files.  It is deterministic: the same config always produces the same bytes.

Usage:
    python3 scripts/generate_world.py [--root PATH] [--check]
"""
from __future__ import annotations

import argparse
import io
import math
import random
import struct
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from layout import Layout  # noqa: E402

Point = Tuple[float, float, float]
Triangle = Tuple[Point, Point, Point]


# --------------------------------------------------------------------- math
def _sub(a: Point, b: Point) -> Point:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a: Point, b: Point) -> Point:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _dot(a: Point, b: Point) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(a: Point) -> Point:
    length = math.sqrt(_dot(a, a))
    if length < 1e-12:
        return (0.0, 0.0, 0.0)
    return (a[0] / length, a[1] / length, a[2] / length)


def _rot_x(p: Point, angle: float) -> Point:
    c, s = math.cos(angle), math.sin(angle)
    return (p[0], c * p[1] - s * p[2], s * p[1] + c * p[2])


class MeshBuilder:
    """Accumulate triangles for one material."""

    def __init__(self) -> None:
        self.triangles: List[Triangle] = []

    def add_triangle(self, a: Point, b: Point, c: Point) -> None:
        self.triangles.append((a, b, c))

    def add_triangle_oriented(self, a: Point, b: Point, c: Point, ref: Point) -> None:
        normal = _cross(_sub(b, a), _sub(c, a))
        center = (
            (a[0] + b[0] + c[0]) / 3.0,
            (a[1] + b[1] + c[1]) / 3.0,
            (a[2] + b[2] + c[2]) / 3.0,
        )
        if _dot(normal, _sub(center, ref)) < 0.0:
            b, c = c, b
        self.add_triangle(a, b, c)

    def add_quad(self, a: Point, b: Point, c: Point, d: Point) -> None:
        self.add_triangle(a, b, c)
        self.add_triangle(a, c, d)

    def add_box(
        self,
        center: Point,
        size: Point,
        rot_x: float = 0.0,
    ) -> None:
        hx, hy, hz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0
        local = [
            (-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
            (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz),
        ]
        pts = []
        for p in local:
            if rot_x:
                p = _rot_x(p, rot_x)
            pts.append((p[0] + center[0], p[1] + center[1], p[2] + center[2]))
        faces = (
            (0, 3, 2, 1),  # -z
            (4, 5, 6, 7),  # +z
            (0, 1, 5, 4),  # -y
            (3, 7, 6, 2),  # +y
            (0, 4, 7, 3),  # -x
            (1, 2, 6, 5),  # +x
        )
        for a, b, c, d in faces:
            self.add_quad(pts[a], pts[b], pts[c], pts[d])

    def add_cylinder_x(
        self,
        center: Point,
        radius: float,
        length: float,
        sides: int = 8,
    ) -> None:
        cx, cy, cz = center
        x0, x1 = cx - length / 2.0, cx + length / 2.0
        ring = [
            (cy + radius * math.cos(2.0 * math.pi * i / sides),
             cz + radius * math.sin(2.0 * math.pi * i / sides))
            for i in range(sides)
        ]
        for i in range(sides):
            j = (i + 1) % sides
            y0, z0 = ring[i]
            y1, z1 = ring[j]
            a = (x0, y0, z0)
            b = (x1, y0, z0)
            c = (x1, y1, z1)
            d = (x0, y1, z1)
            self.add_triangle(a, d, c)
            self.add_triangle(a, c, b)
        for x, sign in ((x0, -1.0), (x1, 1.0)):
            ctr = (x, cy, cz)
            for i in range(sides):
                j = (i + 1) % sides
                p0 = (x, ring[i][0], ring[i][1])
                p1 = (x, ring[j][0], ring[j][1])
                if sign > 0:
                    self.add_triangle_oriented(ctr, p0, p1, (cx, cy, cz))
                else:
                    self.add_triangle_oriented(ctr, p1, p0, (cx, cy, cz))

    def add_octahedron(self, center: Point, radii: Point) -> None:
        rx, ry, rz = radii
        vertices = (
            (center[0] + rx, center[1], center[2]),
            (center[0] - rx, center[1], center[2]),
            (center[0], center[1] + ry, center[2]),
            (center[0], center[1] - ry, center[2]),
            (center[0], center[1], center[2] + rz),
            (center[0], center[1], center[2] - rz),
        )
        faces = (
            (0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4),
            (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5),
        )
        for i, j, k in faces:
            self.add_triangle_oriented(vertices[i], vertices[j], vertices[k], center)

    def add_tri_prism_x(
        self,
        x_center: float,
        yz_triangle: Sequence[Tuple[float, float]],
        thickness: float,
    ) -> None:
        x0 = x_center - thickness / 2.0
        x1 = x_center + thickness / 2.0
        (y0, z0), (y1, z1), (y2, z2) = yz_triangle
        ref = (x_center, (y0 + y1 + y2) / 3.0, (z0 + z1 + z2) / 3.0)
        p0 = (x0, y0, z0)
        p1 = (x0, y1, z1)
        p2 = (x0, y2, z2)
        q0 = (x1, y0, z0)
        q1 = (x1, y1, z1)
        q2 = (x1, y2, z2)
        self.add_triangle_oriented(q0, q1, q2, ref)
        self.add_triangle_oriented(p0, p2, p1, ref)
        for a, b, c, d in ((p0, p1, q1, q0), (p1, p2, q2, q1), (p2, p0, q0, q2)):
            self.add_triangle_oriented(a, b, c, ref)
            self.add_triangle_oriented(a, c, d, ref)


# ----------------------------------------------------------------- materials
@dataclass(frozen=True)
class Material:
    """SDF material definition for one merged mesh."""

    ambient: Tuple[float, float, float, float]
    diffuse: Tuple[float, float, float, float]
    specular: Tuple[float, float, float, float] = (0.1, 0.1, 0.1, 1.0)
    transparency: float = 0.0
    cast_shadows: bool = True


def _rgba(r: float, g: float, b: float) -> Tuple[float, float, float, float]:
    return (r, g, b, 1.0)


MATERIALS: Dict[str, Material] = {
    'concrete': Material(_rgba(0.62, 0.61, 0.58), _rgba(0.62, 0.61, 0.58)),
    'floor': Material(_rgba(0.62, 0.61, 0.58), _rgba(0.62, 0.61, 0.58)),
    'rail_steel': Material(
        _rgba(0.45, 0.47, 0.50), _rgba(0.60, 0.62, 0.65), (0.5, 0.5, 0.5, 1.0)),
    'frame_white': Material(
        _rgba(0.88, 0.90, 0.91), _rgba(0.88, 0.90, 0.91), (0.3, 0.3, 0.3, 1.0)),
    'glass': Material(
        _rgba(0.85, 0.90, 0.92), _rgba(0.85, 0.90, 0.92),
        (0.4, 0.4, 0.4, 1.0), transparency=0.80, cast_shadows=False),
    'equipment_dark': Material(
        _rgba(0.25, 0.27, 0.28), _rgba(0.25, 0.27, 0.28), (0.2, 0.2, 0.2, 1.0)),
    'pipes_yellow': Material(_rgba(0.95, 0.75, 0.05), _rgba(0.95, 0.75, 0.05)),
    'overhead_wires': Material(
        _rgba(0.90, 0.90, 0.88), _rgba(0.90, 0.90, 0.88), (0.05, 0.05, 0.05, 1.0)),
    'joints_dark': Material(_rgba(0.35, 0.35, 0.35), _rgba(0.35, 0.35, 0.35)),
    'gutter_white': Material(_rgba(0.92, 0.92, 0.90), _rgba(0.92, 0.92, 0.90)),
    'legs_grey': Material(_rgba(0.72, 0.72, 0.72), _rgba(0.72, 0.72, 0.72)),
    'substrate_brown': Material(_rgba(0.28, 0.18, 0.10), _rgba(0.28, 0.18, 0.10)),
    'drip_black': Material(_rgba(0.06, 0.06, 0.06), _rgba(0.06, 0.06, 0.06)),
    'canopy_dark': Material(_rgba(0.14, 0.42, 0.14), _rgba(0.14, 0.42, 0.14)),
    'canopy_mid': Material(_rgba(0.22, 0.58, 0.20), _rgba(0.22, 0.58, 0.20)),
    'canopy_dense': Material(_rgba(0.18, 0.50, 0.16), _rgba(0.18, 0.50, 0.16)),
    'fruit_red': Material(_rgba(0.85, 0.08, 0.04), _rgba(0.85, 0.08, 0.04)),
    'fruit_green': Material(_rgba(0.40, 0.65, 0.15), _rgba(0.40, 0.65, 0.15)),
    'strings_white': Material(_rgba(0.90, 0.90, 0.88), _rgba(0.90, 0.90, 0.88)),
    'cards_yellow': Material(_rgba(0.95, 0.85, 0.10), _rgba(0.95, 0.85, 0.10)),
    'cards_blue': Material(_rgba(0.10, 0.55, 0.85), _rgba(0.10, 0.55, 0.85)),
    'markers_pink': Material(_rgba(0.90, 0.20, 0.55), _rgba(0.90, 0.20, 0.55)),
}


def stl_bytes(triangles: Sequence[Triangle], name: str) -> bytes:
    """Return a binary STL file as bytes."""
    buffer = io.BytesIO()
    header = f'{name} ({len(triangles)} triangles)'.encode('ascii')[:80]
    buffer.write(header.ljust(80, b' '))
    buffer.write(struct.pack('<I', len(triangles)))
    for a, b, c in triangles:
        normal = _norm(_cross(_sub(b, a), _sub(c, a)))
        buffer.write(struct.pack(
            '<12fH',
            normal[0], normal[1], normal[2],
            a[0], a[1], a[2],
            b[0], b[1], b[2],
            c[0], c[1], c[2],
            0,
        ))
    return buffer.getvalue()


# -------------------------------------------------------------------- models
def _sub_element(parent: ET.Element, tag: str, text: str) -> ET.Element:
    element = ET.SubElement(parent, tag)
    element.text = text
    return element


def _pose(parent: ET.Element, x: float, y: float, z: float,
          roll: float = 0.0, pitch: float = 0.0, yaw: float = 0.0) -> None:
    _sub_element(
        parent, 'pose',
        f'{x:.6f} {y:.6f} {z:.6f} {roll:.6f} {pitch:.6f} {yaw:.6f}')


def _material(parent: ET.Element, material: Material) -> None:
    element = ET.SubElement(parent, 'material')
    for tag, values in (
        ('ambient', material.ambient),
        ('diffuse', material.diffuse),
        ('specular', material.specular),
    ):
        _sub_element(element, tag, ' '.join(f'{v:.4f}' for v in values))


def _visual(parent: ET.Element, name: str, uri: str, material: Material) -> None:
    visual = ET.SubElement(parent, 'visual')
    visual.set('name', name)
    _sub_element(visual, 'cast_shadows', 'true' if material.cast_shadows else 'false')
    if material.transparency > 0.0:
        _sub_element(visual, 'transparency', f'{material.transparency:.3f}')
    geometry = ET.SubElement(visual, 'geometry')
    mesh = ET.SubElement(geometry, 'mesh')
    _sub_element(mesh, 'uri', uri)
    _material(visual, material)


def _collision(
    parent: ET.Element,
    name: str,
    pose: Sequence[float],
    size: Tuple[float, float, float],
    kd: float = 100.0,
) -> None:
    collision = ET.SubElement(parent, 'collision')
    collision.set('name', name)
    _pose(collision, *pose)
    geometry = ET.SubElement(collision, 'geometry')
    box = ET.SubElement(geometry, 'box')
    _sub_element(box, 'size', ' '.join(f'{v:.6f}' for v in size))
    surface = ET.SubElement(collision, 'surface')
    friction = ET.SubElement(surface, 'friction')
    ode = ET.SubElement(friction, 'ode')
    _sub_element(ode, 'mu', '1.0')
    _sub_element(ode, 'mu2', '1.0')
    contact = ET.SubElement(surface, 'contact')
    ode = ET.SubElement(contact, 'ode')
    _sub_element(ode, 'kp', '1000000.0')
    _sub_element(ode, 'kd', f'{kd:.1f}')
    _sub_element(ode, 'max_vel', '0.1')
    _sub_element(ode, 'min_depth', '0.001')


def _model_root(name: str) -> Tuple[ET.Element, ET.Element]:
    sdf = ET.Element('sdf', {'version': '1.6'})
    model = ET.SubElement(sdf, 'model')
    model.set('name', name)
    _sub_element(model, 'static', 'true')
    link = ET.SubElement(model, 'link')
    link.set('name', 'link')
    return sdf, link


def _write_xml(path: Path, root: ET.Element, check: bool) -> bool:
    ET.indent(root, space='  ')
    data = ET.tostring(root, encoding='utf-8', xml_declaration=True) + b'\n'
    return _write_bytes(path, data, check)


def _write_bytes(path: Path, data: bytes, check: bool) -> bool:
    if check:
        if not path.exists() or path.read_bytes() != data:
            print(f'MISMATCH {path}')
            return False
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return True


def _model_config(name: str, description: str) -> ET.Element:
    model = ET.Element('model')
    _sub_element(model, 'name', name)
    _sub_element(model, 'version', '1.0')
    _sub_element(model, 'sdf', 'model.sdf').set('version', '1.6')
    author = ET.SubElement(model, 'author')
    _sub_element(author, 'name', 'funfun')
    _sub_element(author, 'email', 'funfun@example.com')
    _sub_element(model, 'description', description)
    return model


def _write_model(
    root: Path,
    name: str,
    builders: Dict[str, MeshBuilder],
    collisions: Sequence[Tuple[str, Sequence[float], Tuple[float, float, float]]],
    description: str,
    check: bool,
) -> bool:
    model_dir = root / 'models' / name
    ok = True
    for material_name, builder in builders.items():
        if not builder.triangles:
            continue
        path = model_dir / 'meshes' / f'{material_name}.stl'
        ok = _write_bytes(path, stl_bytes(builder.triangles, material_name), check) and ok
    sdf, link = _model_root(name)
    for material_name, builder in builders.items():
        if not builder.triangles:
            continue
        uri = f'model://{name}/meshes/{material_name}.stl'
        _visual(link, material_name, uri, MATERIALS[material_name])
    for collision_name, pose, size in collisions:
        _collision(link, collision_name, pose, size)
    ok = _write_xml(model_dir / 'model.sdf', sdf, check) and ok
    ok = _write_xml(
        model_dir / 'model.config',
        _model_config(name, description),
        check,
    ) and ok
    return ok


# --------------------------------------------------------------- greenhouse
def _roof_panels(layout: Layout) -> List[Tuple[float, float, float, float]]:
    """Return (center_y, center_z, rot_x, length) for every roof slope panel."""
    gutters = {round(y, 6) for y in layout.roof_gutters}
    profile = sorted(set(layout.roof_gutters + layout.roof_ridges))

    def height(y: float) -> float:
        return layout.eave_height if round(y, 6) in gutters else layout.ridge_height

    panels: List[Tuple[float, float, float, float]] = []
    for y0, y1 in zip(profile, profile[1:]):
        z0, z1 = height(y0), height(y1)
        run, rise = y1 - y0, z1 - z0
        panels.append(
            ((y0 + y1) / 2.0, (z0 + z1) / 2.0,
             math.atan2(rise, run), math.hypot(run, rise)))
    return panels


def _shell_collisions(
        layout: Layout) -> List[Tuple[str, Sequence[float], Tuple[float, float, float]]]:
    """
    Return every static collision of the greenhouse shell.

    Gazebo ray sensors (the MID-360 plugin) only intersect collision
    geometry, so columns, fans, pipes, wires and the roof use simple
    proxy boxes instead of the (visual) meshes.
    """
    half = layout.site_size / 2.0
    collisions: List[Tuple[str, Sequence[float], Tuple[float, float, float]]] = [
        ('wall_x_neg', (-half, 0.0, layout.wall_height / 2.0),
         (layout.wall_thickness, layout.site_size, layout.wall_height)),
        ('wall_x_pos', (half, 0.0, layout.wall_height / 2.0),
         (layout.wall_thickness, layout.site_size, layout.wall_height)),
        ('wall_y_neg', (0.0, -half, layout.wall_height / 2.0),
         (layout.site_size, layout.wall_thickness, layout.wall_height)),
        ('wall_y_pos', (0.0, half, layout.wall_height / 2.0),
         (layout.site_size, layout.wall_thickness, layout.wall_height)),
    ]

    # Sloped roof panels (see _roof_panels for the gutter/ridge profile).
    collisions.extend(
        (f'roof_panel_{index:02d}',
         (0.0, center_y, center_z, angle, 0.0, 0.0),
         (layout.site_size, length, max(layout.roof_slope_thickness, 0.02)))
        for index, (center_y, center_z, angle, length)
        in enumerate(_roof_panels(layout))
    )

    # Structural columns (vertical, 5 m grid; the y=0 aisle line is clear).
    for ix, x in enumerate(layout.column_x):
        for iy, y in enumerate(layout.column_y):
            collisions.append((
                f'column_{ix:02d}_{iy:02d}',
                (x, y, layout.wall_height / 2.0),
                (layout.column_size, layout.column_size, layout.wall_height)))

    # End-wall exhaust fans (approximate each fan by a thin disc box).
    fan_ys = [-42.0 + i * 12.0 for i in range(8)]
    for wall, x in enumerate((-half + 0.08, half - 0.08)):
        for index, y in enumerate(fan_ys):
            collisions.append((
                f'fan_end_{wall}_{index:02d}',
                (x, y, 2.80),
                (0.12, 1.20, 1.20)))

    # Circulation fans along the central aisle.
    for index in range(9):
        collisions.append((
            f'fan_circulation_{index}',
            (-40.0 + index * 10.0, 0.0, 3.60),
            (0.20, 0.80, 0.80)))

    # Ridge vents.
    for index, y in enumerate(layout.roof_ridges):
        collisions.append((
            f'ridge_vent_{index:02d}',
            (0.0, y, layout.ridge_height + 0.04),
            (layout.site_size - 1.0, 0.12, 0.05)))

    # Yellow heating / rail pipes (long cylinders approximated by boxes).
    pipe_side = 2.0 * layout.pipe_radius
    for index, y in enumerate(layout.pipe_y_positions):
        collisions.append((
            f'pipe_{index:03d}',
            (0.0, y, layout.pipe_height),
            (layout.bed_zone_length, pipe_side, pipe_side)))

    # Overhead support wires.
    for index, y in enumerate(layout.row_centers):
        collisions.append((
            f'wire_row_{index:02d}',
            (0.0, y, layout.wire_height),
            (layout.bed_zone_length, 0.006, 0.006)))
    for index, x in enumerate(layout.transverse_wire_x):
        collisions.append((
            f'wire_x_{index:02d}',
            (x, 0.0, layout.wire_height),
            (0.006, layout.site_size, 0.006)))

    return collisions


def build_shell(layout: Layout) -> Dict[str, MeshBuilder]:
    """Build the greenhouse shell, glass, equipment and overhead meshes."""
    builders = {
        name: MeshBuilder()
        for name in (
            'frame_white', 'glass', 'equipment_dark', 'pipes_yellow',
            'overhead_wires', 'joints_dark',
        )
    }
    frame = builders['frame_white']
    glass = builders['glass']
    equipment = builders['equipment_dark']
    pipes = builders['pipes_yellow']
    wires = builders['overhead_wires']
    joints = builders['joints_dark']

    # Columns (visual only).  The y=0 line is omitted so the central aisle
    # stays free.
    for x in layout.column_x:
        for y in layout.column_y:
            frame.add_box(
                (x, y, layout.wall_height / 2.0),
                (layout.column_size, layout.column_size, layout.wall_height),
            )

    # Bottom chords of the transverse trusses.
    for x in layout.column_x:
        frame.add_box(
            (x, 0.0, layout.eave_height - 0.06),
            (0.10, layout.site_size, 0.10),
        )

    # Roof rafters and glass panels.  The slope sign alternates
    # gutter -> ridge -> gutter, so compute it from the actual heights.
    for center_y, center_z, angle, length in _roof_panels(layout):
        for x in layout.column_x:
            frame.add_box((x, center_y, center_z), (0.08, length, 0.08), rot_x=angle)
        glass.add_box(
            (0.0, center_y, center_z),
            (layout.site_size - 0.02, length, layout.roof_slope_thickness),
            rot_x=angle,
        )

    # Longitudinal gutter and ridge beams (purlins).
    for y in layout.roof_gutters:
        frame.add_box(
            (0.0, y, layout.eave_height),
            (layout.site_size, 0.14, 0.14),
        )
    for y in layout.roof_ridges:
        frame.add_box(
            (0.0, y, layout.ridge_height),
            (layout.site_size, 0.10, 0.10),
        )

    # Wall mullions at y=0 on the x walls and wall girts.
    half = layout.site_size / 2.0
    for x in (-half, half):
        frame.add_box((x, 0.0, layout.wall_height / 2.0),
                      (0.10, 0.10, layout.wall_height))
    for z in (0.20, 2.20, 4.30):
        for x in (-half, half):
            frame.add_box((x, 0.0, z), (0.08, layout.site_size, 0.08))
        for y in (-half, half):
            frame.add_box((0.0, y, z), (layout.site_size, 0.08, 0.08))

    # Walls (glass) and gable triangles.
    glass.add_box((0.0, -half, layout.wall_height / 2.0),
                  (layout.site_size, 0.02, layout.wall_height))
    glass.add_box((0.0, half, layout.wall_height / 2.0),
                  (layout.site_size, 0.02, layout.wall_height))
    glass.add_box((-half, 0.0, layout.wall_height / 2.0),
                  (0.02, layout.site_size, layout.wall_height))
    glass.add_box((half, 0.0, layout.wall_height / 2.0),
                  (0.02, layout.site_size, layout.wall_height))
    for x in (-half, half):
        for g0, r, g1 in zip(
            layout.roof_gutters[:-1],
            layout.roof_ridges,
            layout.roof_gutters[1:],
        ):
            glass.add_tri_prism_x(
                x,
                ((g0, layout.eave_height),
                 (r, layout.ridge_height),
                 (g1, layout.eave_height)),
                0.02,
            )

    # End-wall exhaust fans and circulation fans.
    fan_ys = [-42.0 + i * 12.0 for i in range(8)]
    for x in (-half + 0.08, half - 0.08):
        for y in fan_ys:
            equipment.add_cylinder_x((x, y, 2.80), 0.60, 0.12, sides=16)
            equipment.add_cylinder_x((x, y, 2.80), 0.12, 0.18, sides=8)
    for i in range(9):
        x = -40.0 + i * 10.0
        equipment.add_box((x, 0.0, 3.60), (0.20, 0.80, 0.80))
        equipment.add_cylinder_x((x, 0.0, 3.60), 0.30, 0.20, sides=12)

    # Ridge vents.
    for y in layout.roof_ridges:
        equipment.add_box(
            (0.0, y, layout.ridge_height + 0.04),
            (layout.site_size - 1.0, 0.12, 0.05),
        )

    # Yellow heating / rail pipes.
    for y in layout.pipe_y_positions:
        pipes.add_cylinder_x(
            (0.0, y, layout.pipe_height),
            layout.pipe_radius,
            layout.bed_zone_length,
            sides=6,
        )

    # Overhead support wires.
    for y in layout.row_centers:
        wires.add_box(
            (0.0, y, layout.wire_height),
            (layout.bed_zone_length, 0.006, 0.006),
        )
    for x in layout.transverse_wire_x:
        wires.add_box(
            (x, 0.0, layout.wire_height),
            (0.006, layout.site_size, 0.006),
        )

    # Floor expansion joints.
    positions = [-half + 5.0 * i for i in range(21)]
    for y in positions:
        joints.add_box((0.0, y, 0.0005), (layout.site_size, 0.02, 0.001))
    for x in positions:
        joints.add_box((x, 0.0, 0.0005), (0.02, layout.site_size, 0.001))

    return builders


def _plant_positions(length: float, spacing: float) -> List[float]:
    count = int(length // spacing)
    if count <= 0:
        return []
    start = -length / 2.0 + spacing / 2.0
    return [start + i * spacing for i in range(count)]


def build_beds(layout: Layout, length: float, seed: int) -> Dict[str, MeshBuilder]:
    """Build one bed segment (mid or end) with sparse plants."""
    builders = {
        name: MeshBuilder()
        for name in (
            'gutter_white', 'legs_grey', 'substrate_brown', 'drip_black',
            'canopy_dark', 'canopy_mid', 'fruit_red', 'fruit_green',
            'strings_white', 'cards_yellow', 'cards_blue', 'markers_pink',
        )
    }
    rng = random.Random(seed)
    spacing = layout.plant_spacing
    for row, y in enumerate(layout.row_centers):
        builders['gutter_white'].add_box(
            (0.0, y, (layout.gutter_bottom + layout.gutter_top) / 2.0),
            (length, layout.gutter_width, layout.gutter_top - layout.gutter_bottom),
        )
        builders['substrate_brown'].add_box(
            (0.0, y, layout.gutter_top - layout.substrate_thickness / 2.0),
            (length, layout.gutter_width - 0.04, layout.substrate_thickness),
        )
        builders['drip_black'].add_cylinder_x(
            (0.0, y, layout.gutter_top + 0.005), 0.008, length, sides=6)
        leg_count = max(2, int(length / layout.leg_spacing))
        for i in range(leg_count + 1):
            x = -length / 2.0 + i * (length / leg_count)
            builders['legs_grey'].add_box(
                (x, y, layout.gutter_bottom / 2.0),
                (layout.leg_size, layout.leg_size, layout.gutter_bottom),
            )
        builders['canopy_dark'].add_box(
            (0.0, y, layout.canopy_bottom + layout.canopy_height / 2.0),
            (length, layout.canopy_width, layout.canopy_height),
        )
        for x in _plant_positions(length, spacing):
            jitter_x = rng.uniform(-0.10, 0.10)
            jitter_y = rng.uniform(-0.05, 0.05)
            px = x + jitter_x
            py = y + jitter_y
            canopy_low = layout.canopy_bottom
            canopy_ch = layout.canopy_height
            canopy_cw = layout.canopy_width
            builders['canopy_mid'].add_octahedron(
                (px, py, canopy_low + 0.30 * canopy_ch),
                (0.80 * canopy_cw, 0.60 * canopy_cw, 0.47 * canopy_ch))
            builders['canopy_mid'].add_octahedron(
                (px + rng.uniform(-0.08, 0.08), py,
                 canopy_low + 0.72 * canopy_ch),
                (0.63 * canopy_cw, 0.50 * canopy_cw, 0.37 * canopy_ch))
            builders['strings_white'].add_box(
                (px, y, (layout.wire_height + layout.plant_top) / 2.0),
                (0.004, 0.004, layout.wire_height - layout.plant_top),
            )
            for k in range(2):
                material = 'fruit_red' if rng.random() > 0.2 else 'fruit_green'
                builders[material].add_octahedron(
                    (px + rng.uniform(-0.06, 0.06),
                     py + rng.uniform(-0.12, 0.12),
                     canopy_low + canopy_ch * (0.12 + 0.25 * k)),
                    (0.15 * canopy_cw, 0.15 * canopy_cw, 0.09 * canopy_ch),
                )
        for material, period in (
            ('cards_yellow', layout.cards_yellow_spacing),
            ('cards_blue', layout.cards_blue_spacing),
        ):
            for x in _plant_positions(length, period):
                card_top = layout.cards_height + 0.14
                # Plate hangs at the row centre from the overhead wire.
                builders[material].add_box(
                    (x, y, layout.cards_height),
                    (0.005, 0.20, 0.28),
                )
                builders['strings_white'].add_box(
                    (x, y, (layout.wire_height + card_top) / 2.0),
                    (0.004, 0.004, layout.wire_height - card_top),
                )
        # Bed-end marker stakes are pushed into the substrate (inside the
        # 0.35 m gutter), not floating beside it.
        for x in (-length / 2.0 + 0.3, length / 2.0 - 0.3):
            builders['markers_pink'].add_box(
                (x, y + 0.10, 0.44), (0.03, 0.05, 0.15))
    return builders


def build_dense_plants(layout: Layout) -> Dict[str, MeshBuilder]:
    """Build the optional dense plant overlay (visual profile only)."""
    builders = {
        name: MeshBuilder()
        for name in ('canopy_dense', 'fruit_red', 'strings_white')
    }
    rng = random.Random(20261024)
    spacing = layout.plant_spacing_visual
    for y in layout.row_centers:
        for x0, x1 in layout.segment_intervals:
            length = x1 - x0
            for offset in _plant_positions(length, spacing):
                x = x0 + length / 2.0 + offset
                jitter_x = rng.uniform(-0.03, 0.03)
                jitter_y = rng.uniform(-0.05, 0.05)
                px = x + jitter_x
                py = y + jitter_y
                low = layout.canopy_bottom
                ch = layout.canopy_height
                cw = layout.canopy_width
                builders['canopy_dense'].add_octahedron(
                    (px, py, low + 0.55 * ch),
                    (0.67 * cw, 0.53 * cw, 0.43 * ch))
                builders['strings_white'].add_box(
                    (px, y, (layout.wire_height + layout.plant_top) / 2.0),
                    (0.004, 0.004, layout.wire_height - layout.plant_top),
                )
                if rng.random() > 0.55:
                    builders['fruit_red'].add_octahedron(
                        (px + rng.uniform(-0.05, 0.05),
                         py + rng.uniform(-0.10, 0.10),
                         rng.uniform(low + 0.10 * ch, low + 0.75 * ch)),
                        (0.13 * cw, 0.13 * cw, 0.08 * ch),
                    )
    return builders


# --------------------------------------------------------------------- world
def _world_root() -> Tuple[ET.Element, ET.Element]:
    sdf = ET.Element('sdf', {'version': '1.6'})
    world = ET.SubElement(sdf, 'world')
    world.set('name', 'pepper_greenhouse')
    _sub_element(world, 'gravity', '0 0 -9.81')
    scene = ET.SubElement(world, 'scene')
    _sub_element(scene, 'ambient', '0.75 0.75 0.75 1')
    _sub_element(scene, 'background', '0.75 0.85 0.95 1')
    _sub_element(scene, 'shadows', 'true')
    gui = ET.SubElement(world, 'gui', {'fullscreen': '0'})
    camera = ET.SubElement(gui, 'camera', {'name': 'user_camera'})
    _sub_element(camera, 'pose', '30 0 4.5 0 0.18 3.14159')
    _sub_element(camera, 'view_controller', 'orbit')
    _sub_element(camera, 'projection_type', 'perspective')
    physics = ET.SubElement(world, 'physics', {'name': 'ode_1ms', 'type': 'ode'})
    _sub_element(physics, 'max_step_size', '0.001')
    _sub_element(physics, 'real_time_update_rate', '1000')
    _sub_element(physics, 'real_time_factor', '1.0')
    ode = ET.SubElement(physics, 'ode')
    solver = ET.SubElement(ode, 'solver')
    _sub_element(solver, 'type', 'quick')
    _sub_element(solver, 'iters', '50')
    _sub_element(solver, 'sor', '1.3')
    constraints = ET.SubElement(ode, 'constraints')
    _sub_element(constraints, 'cfm', '0.0')
    _sub_element(constraints, 'erp', '0.2')
    _sub_element(constraints, 'contact_max_correcting_vel', '100.0')
    _sub_element(constraints, 'contact_surface_layer', '0.001')
    return sdf, world


def _include(world: ET.Element, uri: str, name: str,
             pose: Tuple[float, float, float] = (0.0, 0.0, 0.0)) -> None:
    include = ET.SubElement(world, 'include')
    _sub_element(include, 'uri', uri)
    _sub_element(include, 'name', name)
    if any(pose):
        _pose(include, *pose)


def _add_camera(
    world: ET.Element,
    name: str,
    pose: Tuple[float, float, float, float, float, float],
    width: int = 1280,
    height: int = 720,
    fov: float = 1.20,
) -> None:
    """Add a static inspection camera with a ROS 2 image topic."""
    model = ET.SubElement(world, 'model')
    model.set('name', f'greenhouse_{name}')
    _sub_element(model, 'static', 'true')
    _sub_element(model, 'pose', ' '.join(f'{v:.6f}' for v in pose))
    link = ET.SubElement(model, 'link')
    link.set('name', 'link')
    sensor = ET.SubElement(link, 'sensor')
    sensor.set('type', 'camera')
    sensor.set('name', 'camera')
    _sub_element(sensor, 'always_on', 'true')
    _sub_element(sensor, 'update_rate', '1')
    camera = ET.SubElement(sensor, 'camera')
    _sub_element(camera, 'horizontal_fov', f'{fov:.4f}')
    image = ET.SubElement(camera, 'image')
    _sub_element(image, 'width', str(width))
    _sub_element(image, 'height', str(height))
    _sub_element(image, 'format', 'R8G8B8')
    clip = ET.SubElement(camera, 'clip')
    _sub_element(clip, 'near', '0.1')
    _sub_element(clip, 'far', '250.0')
    plugin = ET.SubElement(sensor, 'plugin')
    plugin.set('name', f'{name}_controller')
    plugin.set('filename', 'libgazebo_ros_camera.so')
    ros = ET.SubElement(plugin, 'ros')
    _sub_element(ros, 'namespace', '/greenhouse')
    _sub_element(ros, 'remapping', 'image_raw:=image_raw')
    _sub_element(plugin, 'camera_name', name)
    _sub_element(plugin, 'frame_name', f'{name}_link')


def build_world(layout: Layout, visual: bool) -> ET.Element:
    """Build the world SDF for one profile."""
    sdf, world = _world_root()
    _include(world, 'model://sun', 'sun', (0.0, 0.0, 10.0))
    fill = ET.SubElement(world, 'light', {'type': 'directional', 'name': 'fill_light'})
    _sub_element(fill, 'cast_shadows', 'false')
    _pose(fill, 0.0, 0.0, 10.0)
    _sub_element(fill, 'diffuse', '0.35 0.35 0.35 1')
    _sub_element(fill, 'specular', '0.05 0.05 0.05 1')
    _sub_element(fill, 'direction', '0.3 0.5 -0.8')

    # Floor.
    floor = ET.SubElement(world, 'model')
    floor.set('name', 'floor')
    _sub_element(floor, 'static', 'true')
    link = ET.SubElement(floor, 'link')
    link.set('name', 'link')
    _collision(link, 'floor_collision', (0.0, 0.0, -0.05),
               (layout.site_size, layout.site_size, 0.10), kd=100.0)

    # Rails (physical).
    rails = ET.SubElement(world, 'model')
    rails.set('name', 'rails')
    _sub_element(rails, 'static', 'true')
    link = ET.SubElement(rails, 'link')
    link.set('name', 'link')
    center_z = (layout.rail_height - layout.rail_embed) / 2.0
    rail_size = (layout.rail_height + layout.rail_embed)
    for name, y in (('left', -layout.wheel_y), ('right', layout.wheel_y)):
        _collision(
            link, f'rail_{name}',
            (0.0, y, center_z),
            (layout.rail_length, layout.rail_width, rail_size),
            kd=10.0,
        )
        rail_visual = ET.SubElement(link, 'visual')
        rail_visual.set('name', f'rail_{name}')
        _sub_element(rail_visual, 'cast_shadows', 'true')
        _pose(rail_visual, 0.0, y, center_z)
        geometry = ET.SubElement(rail_visual, 'geometry')
        box = ET.SubElement(geometry, 'box')
        _sub_element(box, 'size',
                     f'{layout.rail_length:.6f} {layout.rail_width:.6f} '
                     f'{rail_size:.6f}')
        _material(rail_visual, MATERIALS['rail_steel'])

    _add_camera(
        world, 'aisle_camera',
        (30.0, 0.0, 4.5, 0.0, 0.18, math.pi),
    )
    _add_camera(
        world, 'bed_camera',
        (2.5, -18.0, 5.5, 0.0, 0.18, math.pi / 2.0),
    )

    _include(world, 'model://pepper_greenhouse_shell', 'greenhouse_shell')
    _include(world, 'model://pepper_beds_mid', 'beds_mid')
    for name, x in (('beds_west', -34.75), ('beds_east', 34.75)):
        _include(world, 'model://pepper_beds_end', name, (x, 0.0, 0.0))
    if visual:
        _include(world, 'model://pepper_plants_dense', 'plants_dense')
    return sdf


def floor_mesh(layout: Layout) -> MeshBuilder:
    """Build the floor mesh referenced by the world model."""
    builder = MeshBuilder()
    builder.add_box(
        (0.0, 0.0, -0.05),
        (layout.site_size, layout.site_size, 0.10),
    )
    return builder


# ---------------------------------------------------------------------- main
def generate(root: Path, check: bool) -> bool:
    """Generate (or verify) every asset under root."""
    layout = Layout.from_yaml(root / 'config' / 'greenhouse.yaml')
    layout.validate()
    ok = True

    shell = build_shell(layout)
    shell['floor'] = floor_mesh(layout)
    shell_collisions = _shell_collisions(layout)
    ok = _write_model(
        root, 'pepper_greenhouse_shell', shell, shell_collisions,
        'Venlo greenhouse shell, glass, equipment and overhead structure.',
        check,
    ) and ok

    for name, length, seed in (
        ('pepper_beds_mid', 43.0, 4300),
        ('pepper_beds_end', 22.5, 2250),
    ):
        beds = build_beds(layout, length, seed)
        collisions = [
            (f'gutter_{i}', (0.0, y, layout.gutter_top / 2.0),
             (length, layout.gutter_width, layout.gutter_top))
            for i, y in enumerate(layout.row_centers)
        ]
        # Canopy: ray sensors must see the plant rows for relocalisation.
        collisions.extend(
            (f'canopy_{i}',
             (0.0, y, layout.canopy_bottom + layout.canopy_height / 2.0),
             (length, layout.canopy_width, layout.canopy_height))
            for i, y in enumerate(layout.row_centers)
        )
        ok = _write_model(
            root, name, beds, collisions,
            f'Grow gutters, substrate, canopy and plants ({length:.1f} m).',
            check,
        ) and ok

    dense = build_dense_plants(layout)
    ok = _write_model(
        root, 'pepper_plants_dense', dense, [],
        'Dense plant overlay for the visual profile.', check,
    ) and ok

    for visual, filename in (
        (False, 'pepper_greenhouse.world'),
        (True, 'pepper_greenhouse_visual.world'),
    ):
        ok = _write_xml(root / 'worlds' / filename, build_world(layout, visual), check) and ok

    return ok


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path,
                        default=Path(__file__).resolve().parents[1],
                        help='package root (default: parent of scripts/)')
    parser.add_argument('--check', action='store_true',
                        help='verify the checked-in assets instead of writing')
    args = parser.parse_args(argv)
    ok = generate(args.root.resolve(), args.check)
    if args.check:
        print('assets OK' if ok else 'assets DIFFER')
    else:
        print('assets written')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
