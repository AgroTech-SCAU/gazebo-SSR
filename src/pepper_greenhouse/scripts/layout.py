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
Layout definition and derived dimensions for the pepper greenhouse.

The rail gauge is taken from the 4WIS chassis wheel track (2 * wheel_y).
Every other dimension is either read from config/greenhouse.yaml or derived
here so that the generator, the checker and the tests share one source of
truth.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import yaml

Segment = Tuple[float, float]


@dataclass(frozen=True)
class Layout:
    """All scene dimensions, in metres."""

    # chassis / rails
    wheel_y: float
    wheel_width: float
    wheel_radius: float
    rail_width: float
    rail_height: float
    rail_embed: float
    rail_length: float
    rail_x_min: float
    # greenhouse shell
    site_size: float
    wall_height: float
    wall_thickness: float
    eave_height: float
    ridge_height: float
    roof_bay: float
    column_size: float
    column_grid: float
    roof_slope_thickness: float
    # aisle / beds
    aisle_clear_width: float
    gutter_width: float
    gutter_bottom: float
    gutter_top: float
    substrate_thickness: float
    leg_size: float
    leg_spacing: float
    bed_pitch: float
    rows_per_side: int
    bed_zone_length: float
    cross_aisle_width: float
    cross_aisle_center: float
    # plants
    plant_height: float
    plant_spacing_layout: float
    plant_spacing_visual: float
    canopy_width: float
    canopy_height: float
    canopy_bottom: float
    # overhead structure
    wire_height: float
    pipe_height: float
    pipe_radius: float
    pipe_offset: float
    cards_height: float
    cards_yellow_spacing: float
    cards_blue_spacing: float

    @classmethod
    def from_yaml(cls, path: Path) -> 'Layout':
        """Load a Layout from a YAML file."""
        data = yaml.safe_load(path.read_text(encoding='utf-8'))
        chassis = data['chassis']
        rails = data['rails']
        house = data['greenhouse']
        aisle = data['aisle']
        gutter = data['gutter']
        beds = data['beds']
        plants = data['plants']
        structure = data['structure']
        return cls(
            wheel_y=float(chassis['wheel_y']),
            wheel_width=float(chassis['wheel_width']),
            wheel_radius=float(chassis['wheel_radius']),
            rail_width=float(rails['width']),
            rail_height=float(rails['height']),
            rail_embed=float(rails['embed']),
            rail_length=float(rails['length']),
            rail_x_min=float(rails['x_min']),
            site_size=float(house['site_size']),
            wall_height=float(house['wall_height']),
            wall_thickness=float(house['wall_thickness']),
            eave_height=float(house['eave_height']),
            ridge_height=float(house['ridge_height']),
            roof_bay=float(house['roof_bay']),
            column_size=float(house['column_size']),
            column_grid=float(house['column_grid']),
            roof_slope_thickness=float(house['roof_slope_thickness']),
            aisle_clear_width=float(aisle['clear_width']),
            gutter_width=float(gutter['width']),
            gutter_bottom=float(gutter['bottom']),
            gutter_top=float(gutter['top']),
            substrate_thickness=float(gutter['substrate_thickness']),
            leg_size=float(gutter['leg_size']),
            leg_spacing=float(gutter['leg_spacing']),
            bed_pitch=float(beds['pitch']),
            rows_per_side=int(beds['rows_per_side']),
            bed_zone_length=float(beds['zone_length']),
            cross_aisle_width=float(beds['cross_aisle_width']),
            cross_aisle_center=float(beds['cross_aisle_center']),
            plant_height=float(plants['height']),
            plant_spacing_layout=float(plants['spacing_layout']),
            plant_spacing_visual=float(plants['spacing_visual']),
            canopy_width=float(plants['canopy_width']),
            canopy_height=float(plants['canopy_height']),
            canopy_bottom=float(plants['canopy_bottom']),
            wire_height=float(structure['wire_height']),
            pipe_height=float(structure['pipe_height']),
            pipe_radius=float(structure['pipe_radius']),
            pipe_offset=float(structure['pipe_offset']),
            cards_height=float(structure['cards_height']),
            cards_yellow_spacing=float(structure['cards_yellow_spacing']),
            cards_blue_spacing=float(structure['cards_blue_spacing']),
        )

    # ---------------------------------------------------------------- rails
    @property
    def rail_gauge(self) -> float:
        """Distance between the two rail centre lines."""
        return 2.0 * self.wheel_y

    @property
    def rail_centers(self) -> Tuple[float, float]:
        """Y coordinates of the two rails."""
        return (-self.wheel_y, self.wheel_y)

    @property
    def wheel_outer(self) -> float:
        """Absolute y of the outer tyre edge."""
        return self.wheel_y + self.wheel_width / 2.0

    @property
    def rail_outer(self) -> float:
        """Absolute y of the outer rail edge."""
        return self.wheel_y + self.rail_width / 2.0

    # ----------------------------------------------------------- greenhouse
    @property
    def wall_inner(self) -> float:
        """Absolute coordinate of the inner wall face."""
        return self.site_size / 2.0 - self.wall_thickness / 2.0

    @property
    def roof_bay_count(self) -> int:
        """Return the number of 5 m roof bays across the greenhouse."""
        return int(round(self.site_size / self.roof_bay))

    @property
    def roof_gutters(self) -> List[float]:
        """Y coordinates of the roof gutter lines, including the two eaves."""
        half = self.roof_bay_count // 2
        values = {0.0}
        values.update(s * k * self.roof_bay for k in range(1, half + 1) for s in (1, -1))
        return sorted(values)

    @property
    def roof_ridges(self) -> List[float]:
        """Y coordinates of the ridge lines (one per roof bay)."""
        half = self.roof_bay_count // 2
        values = {s * (k + 0.5) * self.roof_bay for k in range(half) for s in (1, -1)}
        return sorted(values)

    @property
    def column_x(self) -> List[float]:
        """X coordinates of the structural column lines."""
        n = int(round(self.site_size / (2.0 * self.column_grid)))
        values = {0.0}
        values.update(s * k * self.column_grid for k in range(1, n + 1) for s in (1, -1))
        return sorted(values)

    @property
    def column_y(self) -> List[float]:
        """Y coordinates of the structural column lines (the y=0 aisle is clear)."""
        n = int(round(self.site_size / (2.0 * self.column_grid)))
        values = {s * k * self.column_grid for k in range(1, n + 1) for s in (1, -1)}
        return sorted(values)

    @property
    def column_count(self) -> int:
        """Total number of structural columns (visual only)."""
        return len(self.column_x) * len(self.column_y)

    # --------------------------------------------------------------- aisles
    @property
    def gutter_inner(self) -> float:
        """Absolute y of the central aisle gutter inner faces."""
        return self.aisle_clear_width / 2.0

    @property
    def gutter_first_center(self) -> float:
        """Absolute y of the first gutter centre (closest to the aisle)."""
        return self.gutter_inner + self.gutter_width / 2.0

    @property
    def outermost_gutter_center(self) -> float:
        """Absolute y of the outer-most gutter centre."""
        return self.gutter_first_center + (self.rows_per_side - 1) * self.bed_pitch

    @property
    def outermost_gutter_face(self) -> float:
        """Absolute y of the outer-most gutter face."""
        return self.outermost_gutter_center + self.gutter_width / 2.0

    @property
    def side_aisle(self) -> float:
        """Width of the aisle between the outer-most gutter and the wall."""
        return self.wall_inner - self.outermost_gutter_face

    @property
    def bed_zone_half(self) -> float:
        """Half length of the planted zone along x."""
        return self.bed_zone_length / 2.0

    @property
    def headland(self) -> float:
        """Return the turning space between the planted zone and the end wall."""
        return self.wall_inner - self.bed_zone_half

    @property
    def cross_aisle_inner(self) -> float:
        """Inner edge of the positive cross aisle."""
        return self.cross_aisle_center - self.cross_aisle_width / 2.0

    @property
    def cross_aisle_outer(self) -> float:
        """Outer edge of the positive cross aisle."""
        return self.cross_aisle_center + self.cross_aisle_width / 2.0

    @property
    def segment_intervals(self) -> Tuple[Segment, Segment, Segment]:
        """X intervals of the three bed segments (west, middle, east)."""
        half = self.bed_zone_half
        c = self.cross_aisle_center
        half_aisle = self.cross_aisle_width / 2.0
        return (
            (-half, -(c + half_aisle)),
            (-(c - half_aisle), c - half_aisle),
            (c + half_aisle, half),
        )

    @property
    def cross_aisle_intervals(self) -> Tuple[Segment, Segment]:
        """X intervals of the two cross aisles."""
        return (
            (-self.cross_aisle_outer, -self.cross_aisle_inner),
            (self.cross_aisle_inner, self.cross_aisle_outer),
        )

    @property
    def segment_lengths(self) -> Tuple[float, float, float]:
        """Lengths of the three bed segments."""
        return tuple(b - a for a, b in self.segment_intervals)

    @property
    def row_centers(self) -> List[float]:
        """Y centres of all grow-gutter rows (positive side first)."""
        return [
            side * (self.gutter_first_center + i * self.bed_pitch)
            for side in (1.0, -1.0)
            for i in range(self.rows_per_side)
        ]

    @property
    def row_count(self) -> int:
        """Total number of gutter rows."""
        return len(self.row_centers)

    # --------------------------------------------------------------- plants
    @property
    def plant_spacing(self) -> float:
        """Sparse plant spacing used by the default layout profile."""
        return self.plant_spacing_layout

    @property
    def canopy_top(self) -> float:
        """Top of the continuous canopy strip."""
        return self.canopy_bottom + self.canopy_height

    @property
    def plant_top(self) -> float:
        """Top of an individual plant (absolute z)."""
        return self.plant_height

    def spacing_for_profile(self, profile: str) -> float:
        """Return the plant/string spacing for a profile name."""
        if profile == 'layout':
            return self.plant_spacing_layout
        if profile == 'visual':
            return self.plant_spacing_visual
        raise ValueError(f'unknown profile: {profile}')

    # ------------------------------------------------------------- overhead
    @property
    def walkway_centers(self) -> List[float]:
        """Y centres of the 59 inter-row walkways plus the central aisle."""
        walkways: List[float] = []
        for side in (1.0, -1.0):
            centers = [
                side * (self.gutter_first_center + i * self.bed_pitch)
                for i in range(self.rows_per_side)
            ]
            walkways.extend((a + b) / 2.0 for a, b in zip(centers, centers[1:]))
        walkways.append(0.0)
        return walkways

    @property
    def pipe_y_positions(self) -> List[float]:
        """Y coordinates of the two yellow pipes in every walkway."""
        return [
            y + offset
            for y in self.walkway_centers
            for offset in (-self.pipe_offset, self.pipe_offset)
        ]

    @property
    def transverse_wire_x(self) -> List[float]:
        """X coordinates of the transverse overhead wires."""
        step = self.column_grid
        count = int(round(self.bed_zone_length / step))
        start = -self.bed_zone_half + step / 2.0
        return [start + i * step for i in range(count)]

    # ------------------------------------------------------------- validate
    def validate(self) -> None:
        """Raise AssertionError when the layout is internally inconsistent."""
        assert math.isclose(self.rail_gauge, 0.6694, abs_tol=1e-9), self.rail_gauge
        assert math.isclose(self.rail_centers[0], -0.3347, abs_tol=1e-9)
        assert math.isclose(self.rail_centers[1], 0.3347, abs_tol=1e-9)
        assert self.wheel_outer < self.rail_outer + 1e-12
        assert self.gutter_inner - self.wheel_outer >= 0.20
        assert self.outermost_gutter_face < self.wall_inner
        assert len(self.segment_intervals) == 3
        assert math.isclose(
            sum(self.segment_lengths) + 2.0 * self.cross_aisle_width,
            self.bed_zone_length,
        )
        assert math.isclose(self.segment_lengths[0], self.segment_lengths[2])
        assert self.bed_zone_half + self.headland <= self.wall_inner + 1e-9
        assert self.row_count == 2 * self.rows_per_side
        assert len(self.roof_gutters) == self.roof_bay_count + 1
        assert len(self.roof_ridges) == self.roof_bay_count
        assert self.column_count == len(self.column_x) * len(self.column_y)
        assert 0.0 not in self.column_y
        assert len(self.pipe_y_positions) == 2 * (2 * (self.rows_per_side - 1) + 1)
        assert len(self.transverse_wire_x) >= 1
        self._assert_clear_aisles()

    def _assert_clear_aisles(self) -> None:
        """Assert that no structural column blocks a robot aisle."""
        half = self.column_size / 2.0
        # central aisle (y=0)
        for y in self.column_y:
            assert abs(y) > self.gutter_inner + half
        # cross aisles (x = +/- cross_aisle_center)
        for x in self.column_x:
            for lo, hi in self.cross_aisle_intervals:
                assert not (lo - half < x < hi + half)
        # headlands (x between bed zone and the inner wall face)
        for x in self.column_x:
            assert not (self.bed_zone_half - half < abs(x) < self.wall_inner)
        # rows must stay inside the wall
        assert self.outermost_gutter_face < self.wall_inner

    def summary(self) -> str:
        """Return a one-block human-readable summary."""
        return (
            f'rail gauge      : {self.rail_gauge:.4f} m\n'
            f'rails           : y = {self.rail_centers[0]:+.4f} / '
            f'{self.rail_centers[1]:+.4f}\n'
            f'central aisle   : {self.aisle_clear_width:.2f} m\n'
            f'gutter rows     : {self.row_count} '
            f'({self.rows_per_side} per side, pitch {self.bed_pitch:.2f} m)\n'
            f'outer gutter    : y = +/-{self.outermost_gutter_face:.3f} m\n'
            f'side aisle      : {self.side_aisle:.2f} m\n'
            f'bed segments    : '
            f'{self.segment_lengths[0]:.1f} + {self.cross_aisle_width:.1f} + '
            f'{self.segment_lengths[1]:.1f} + {self.cross_aisle_width:.1f} + '
            f'{self.segment_lengths[2]:.1f} = {self.bed_zone_length:.1f} m\n'
            f'headland        : {self.headland:.2f} m\n'
            f'columns         : {self.column_count}\n'
            f'pipes / wires   : {len(self.pipe_y_positions)} / '
            f'{self.row_count + len(self.transverse_wire_x)}\n'
            f'site            : {self.site_size:.1f} x {self.site_size:.1f} m'
        )


def default_config_path() -> Path:
    """Return the source-tree config path based on this file's location."""
    return Path(__file__).resolve().parents[1] / 'config' / 'greenhouse.yaml'
