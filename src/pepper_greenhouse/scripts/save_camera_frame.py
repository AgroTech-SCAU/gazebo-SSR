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

r"""
Save one RGB frame from a ROS 2 camera topic to a PNG file.

Usage:
    python3 scripts/save_camera_frame.py \
        /greenhouse/aisle_camera/image_raw /tmp/aisle.png
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Sequence

import numpy as np
import rclpy
from PIL import Image as PILImage
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


class FrameSaver(Node):
    """Subscribe to one image topic and save the first complete frame."""

    def __init__(self, topic: str, output: Path) -> None:
        super().__init__('save_camera_frame')
        self.output = output
        self.done = False
        self.create_subscription(
            Image, topic, self._on_image, qos_profile_sensor_data)

    def _on_image(self, msg: Image) -> None:
        if self.done:
            return
        row = msg.step
        array = np.frombuffer(bytes(msg.data), dtype=np.uint8)
        array = array.reshape((msg.height, row))
        array = array[:, :msg.width * 3].reshape((msg.height, msg.width, 3))
        if msg.encoding == 'bgr8':
            array = array[:, :, ::-1]
        elif msg.encoding != 'rgb8':
            self.get_logger().error(f'unsupported encoding {msg.encoding}')
            self.done = True
            return
        PILImage.fromarray(array, 'RGB').save(self.output)
        self.get_logger().info(f'saved {msg.width}x{msg.height} to {self.output}')
        self.done = True


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('topic', help='sensor_msgs/Image topic')
    parser.add_argument('output', type=Path, help='output PNG path')
    parser.add_argument('--timeout', type=float, default=15.0,
                        help='give up after this many seconds')
    args = parser.parse_args(argv)
    if args.output.suffix.lower() != '.png':
        parser.error('output must end with .png')
    rclpy.init()
    node = FrameSaver(args.topic, args.output)
    deadline = time.monotonic() + args.timeout
    try:
        while rclpy.ok() and not node.done and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.5)
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
    if not args.output.exists():
        print(f'no frame received from {args.topic}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
