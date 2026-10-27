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
Four-wheel independent steering (4WIS) chassis kinematics.

真车：底盘单片机解析 vx / vy / wz，本节点不需要上真车。
仿真：单片机不存在，本节点充当它的替身，把 /cmd_vel 解算成
      4 个转向关节的位置命令 + 4 个车轮关节的速度命令，
      让 Gazebo 里的底盘行为和真车一致。

解算（对每个车轮 i，轮心在 base_link 系下为 (x_i, y_i)）：
    轮心的速度矢量  v_ix = vx - wz * y_i
                    v_iy = vy + wz * x_i
    转向角          delta_i = atan2(v_iy, v_ix)
    滚动线速度      s_i = hypot(v_ix, v_iy)
    若 |delta_i| > 90°，则 delta_i -= sign(delta_i)*180°、s_i 取反
    （车轮对称，这样能把转向行程压到 ±90° 内，与真车单片机一致）
    轮关节速度      omega_i = s_i / r * direction_i
    direction_i 反映该轮关节轴在车体坐标系里的朝向：左轮 -1、右轮 +1。

这个公式同时覆盖三种典型工况（无需切换模式）：
    vx/vy        → 四轮同角度，斜行 crab
    纯 wz        → 前轮 +45° 级、后轮 -45° 级，原地自转
    vx/vy + wz   → 一般曲线运动，各轮角度与轮速独立

用法:
    ros2 run steer_wheel_control steer_wheel_kinematics
    ros2 launch steer_wheel_control sim.launch.py      # 连同 Gazebo 一起

    ros2 topic pub -r 20 /cmd_vel geometry_msgs/msg/Twist \\
      "{linear: {x: 0.3, y: 0.0}, angular: {z: 0.0}}"     # 前进
    ros2 topic pub -r 20 /cmd_vel geometry_msgs/msg/Twist \\
      "{linear: {x: 0.0, y: 0.3}, angular: {z: 0.0}}"     # 横移
    ros2 topic pub -r 20 /cmd_vel geometry_msgs/msg/Twist \\
      "{linear: {x: 0.0, y: 0.0}, angular: {z: 0.5}}"     # 原地自转
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Sequence, Tuple

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from rclpy.time import Time
from std_msgs.msg import Float64MultiArray


@dataclass(frozen=True)
class Wheel:
    """一个车轮的几何与关节信息（顺序与控制器命令数组一致）."""

    label: str
    steer_joint: str
    wheel_joint: str
    x: float
    y: float
    direction: float


# 轮心位置由 meshes + URDF 关节 origin 实测得到（详见 steer_wheel_chassis 包 README）。
# direction 是“正转 = 前进”所需的关节速度符号，取决于各轮 joint 轴的朝向：
#   Joint_5 (LF) 轴 -> base -y : -1
#   Joint_6 (RF) 轴 -> base +y : +1
#   Joint_7 (LR) 轴 -> base -y : -1
#   Joint_8 (RR) 轴 -> base -y : -1   <-- 注意右后轮的 rpy 与左轮相同，
#                                        不是右前轮那种朝向，符号不能用 +1，
#                                        否则右后轮会被反向驱动，车持续右偏。
WHEEL_LAYOUT: Sequence[Wheel] = (
    Wheel('left_front', 'left_front', 'Joint_5', 0.37733, 0.33470, -1.0),
    Wheel('right_front', 'right_front', 'Joint_6', 0.33267, -0.33470, 1.0),
    Wheel('left_rear', 'left_behind', 'Joint_7', -0.33267, 0.33470, -1.0),
    Wheel('right_rear', 'right_behind', 'Joint_8', -0.37733, -0.33470, -1.0),
)


class ChassisKinematics(Node):
    """把 /cmd_vel 解算成转向位置命令与轮速命令."""

    def __init__(self) -> None:
        super().__init__('steer_wheel_kinematics')

        self.declare_parameter('wheel_radius', 0.0935)
        self.declare_parameter('max_linear_velocity', 1.5)      # m/s，超出直接截断
        self.declare_parameter('max_angular_velocity', 2.0)     # rad/s
        self.declare_parameter('max_wheel_velocity', 20.0)      # rad/s，与 URDF limit 一致
        self.declare_parameter('max_steer_angle', 3.14159)      # rad
        self.declare_parameter('cmd_vel_timeout', 0.5)          # s，超时轮速归零
        self.declare_parameter('publish_rate', 50.0)            # Hz
        self.declare_parameter('stop_linear_threshold', 0.005)  # m/s 以下视为不动
        self.declare_parameter('stop_angular_threshold', 0.010)  # rad/s 以下视为不转

        self._radius: float = self.get_parameter('wheel_radius').value
        self._max_v: float = self.get_parameter('max_linear_velocity').value
        self._max_w: float = self.get_parameter('max_angular_velocity').value
        self._max_wheel: float = self.get_parameter('max_wheel_velocity').value
        self._max_steer: float = self.get_parameter('max_steer_angle').value
        self._timeout: float = self.get_parameter('cmd_vel_timeout').value
        self._stop_v: float = self.get_parameter('stop_linear_threshold').value
        self._stop_w: float = self.get_parameter('stop_angular_threshold').value

        self._steering_cmd: List[float] = [0.0] * len(WHEEL_LAYOUT)
        self._last_cmd: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._last_cmd_time: Time | None = None

        # 控制器命令订阅端是 BEST_EFFORT，这里也用 BEST_EFFORT（兼容性最好）
        cmd_qos = QoSProfile(depth=1,
                             reliability=ReliabilityPolicy.BEST_EFFORT,
                             durability=DurabilityPolicy.VOLATILE,
                             history=HistoryPolicy.KEEP_LAST)

        self._pub_steering = self.create_publisher(
            Float64MultiArray, '/steering_position_controller/commands', cmd_qos)
        self._pub_wheel = self.create_publisher(
            Float64MultiArray, '/wheel_velocity_controller/commands', cmd_qos)
        self.create_subscription(Twist, '/cmd_vel', self._on_cmd_vel, cmd_qos)

        rate = float(self.get_parameter('publish_rate').value)
        self.create_timer(1.0 / rate, self._on_timer)

        self.get_logger().info(
            f'4WIS chassis kinematics ready: r={self._radius:.4f} m, '
            f'v_max={self._max_v} m/s, w_max={self._max_w} rad/s, '
            f'timeout={self._timeout} s, rate={rate} Hz')

    # ------------------------------------------------------------------ 回调
    def _on_cmd_vel(self, msg: Twist) -> None:
        self._last_cmd = (msg.linear.x, msg.linear.y, msg.angular.z)
        self._last_cmd_time = self.get_clock().now()

    def _on_timer(self) -> None:
        now = self.get_clock().now()
        if self._last_cmd_time is None or \
                (now - self._last_cmd_time).nanoseconds * 1e-9 > self._timeout:
            # 没有 /cmd_vel 或已超时：轮速归零，转向保持不动
            self._publish(self._steering_cmd, [0.0] * len(WHEEL_LAYOUT))
            return

        steering, wheels = self.solve(*self._last_cmd)
        self._publish(steering, wheels)

    # ------------------------------------------------------------------ 解算
    def solve(self, vx: float, vy: float, wz: float) -> Tuple[List[float], List[float]]:
        """把车体速度解算成 (转向角列表, 轮关节速度列表)."""
        vx = max(-self._max_v, min(self._max_v, vx))
        vy = max(-self._max_v, min(self._max_v, vy))
        wz = max(-self._max_w, min(self._max_w, wz))

        moving = (math.hypot(vx, vy) > self._stop_v or abs(wz) > self._stop_w)
        if not moving:
            # 完全静止：保持当前转向角，只把轮速清零
            return list(self._steering_cmd), [0.0] * len(WHEEL_LAYOUT)

        steering: List[float] = []
        wheels: List[float] = []
        for idx, wheel in enumerate(WHEEL_LAYOUT):
            vix = vx - wz * wheel.y
            viy = vy + wz * wheel.x
            speed = math.hypot(vix, viy)
            if speed < 1e-6:
                # 该轮在瞬时旋转中心上，速度为 0、角度无定义，保持原角度
                steering.append(self._steering_cmd[idx])
                wheels.append(0.0)
                continue

            delta = math.atan2(viy, vix)
            if delta > math.pi / 2.0:
                delta -= math.pi
                speed = -speed
            elif delta < -math.pi / 2.0:
                delta += math.pi
                speed = -speed

            delta = max(-self._max_steer, min(self._max_steer, delta))
            omega = speed / self._radius * wheel.direction
            omega = max(-self._max_wheel, min(self._max_wheel, omega))
            steering.append(delta)
            wheels.append(omega)

        self._steering_cmd = steering
        return steering, wheels

    # ------------------------------------------------------------------ 发布
    def _publish(self, steering: Sequence[float], wheels: Sequence[float]) -> None:
        msg = Float64MultiArray()
        msg.data = [float(v) for v in steering]
        self._pub_steering.publish(msg)

        msg = Float64MultiArray()
        msg.data = [float(v) for v in wheels]
        self._pub_wheel.publish(msg)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = ChassisKinematics()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
