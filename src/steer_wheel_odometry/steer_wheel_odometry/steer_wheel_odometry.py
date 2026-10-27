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
舵轮底盘 (4WIS) 轮式里程计.

真车的里程计由底盘单片机提供；本节点是**仿真里的替身**，用 /joint_states 里的
转向角 + 轮速做正运动学解算，积分出 odom 位姿，发布：

    /odom                       nav_msgs/Odometry
    odom -> base_footprint      TF

解算（每个车轮 i 的轮心在 base_link 系下为 (x_i, y_i)，转向角 delta_i）：

    s_i  = omega_i * r * direction_i        轮子沿自身朝向的滚动线速度
    v_ix = s_i * cos(delta_i)               轮心速度（车体坐标系）
    v_iy = s_i * sin(delta_i)

    车体平面速度 (vx, vy, wz) 满足：
        v_ix = vx - wz * y_i
        v_iy = vy + wz * x_i

    4 个车轮给出 8 个方程解 3 个未知量，用最小二乘（A 只与轮心位置有关，
    所以伪逆在启动时算一次）。再按平面刚体运动精确积分成 (x, y, yaw)。

direction_i 与转向/轮速约定见 steer_wheel_control/README.md：
`Joint_5=-1, Joint_6=+1, Joint_7=-1, Joint_8=-1`（右后轮与左轮同向）。

用法:
    ros2 run steer_wheel_odometry odometry
    ros2 launch steer_wheel_odometry odometry.launch.py
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple

import numpy as np
import rclpy
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.time import Time
from sensor_msgs.msg import JointState
from std_msgs.msg import Header
from tf2_ros import TransformBroadcaster

STEER_JOINTS = ('left_front', 'right_front', 'left_behind', 'right_behind')
WHEEL_JOINTS = ('Joint_5', 'Joint_6', 'Joint_7', 'Joint_8')

# 与 steer_wheel_kinematics.py 的 WHEEL_LAYOUT 保持一致（LF, RF, LR, RR）
DEFAULT_WHEEL_X = (0.37733, 0.33267, -0.33267, -0.37733)
DEFAULT_WHEEL_Y = (0.33470, -0.33470, 0.33470, -0.33470)
DEFAULT_DIRECTION = (-1.0, 1.0, -1.0, -1.0)


class SteerWheelOdometry(Node):
    """4WIS 轮式里程计节点."""

    def __init__(self) -> None:
        super().__init__('steer_wheel_odometry')

        self.declare_parameter('wheel_radius', 0.0935)
        self.declare_parameter('wheel_x', list(DEFAULT_WHEEL_X))
        self.declare_parameter('wheel_y', list(DEFAULT_WHEEL_Y))
        self.declare_parameter('wheel_direction', list(DEFAULT_DIRECTION))
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('base_frame', 'base_footprint')
        self.declare_parameter('initial_x', 0.0)
        self.declare_parameter('initial_y', 0.0)
        self.declare_parameter('initial_yaw', 0.0)
        self.declare_parameter('max_dt', 0.5)  # 超过这个间隔不积分（掉帧/暂停后重新对齐）
        self.declare_parameter('publish_tf', True)

        self._radius: float = self.get_parameter('wheel_radius').value
        self._wheel_x: Tuple[float, ...] = tuple(self.get_parameter('wheel_x').value)
        self._wheel_y: Tuple[float, ...] = tuple(self.get_parameter('wheel_y').value)
        self._direction: Tuple[float, ...] = tuple(
            self.get_parameter('wheel_direction').value)
        self._odom_frame: str = self.get_parameter('odom_frame').value
        self._base_frame: str = self.get_parameter('base_frame').value
        self._max_dt: float = self.get_parameter('max_dt').value
        self._publish_tf: bool = self.get_parameter('publish_tf').value

        if not (len(self._wheel_x) == len(self._wheel_y) == len(self._direction) == 4):
            raise ValueError('wheel_x / wheel_y / wheel_direction 必须各有 4 个元素')

        # A 是 8x3：每个车轮 2 行 [1,0,-y_i] / [0,1,x_i]，只与轮心位置有关
        rows = []
        for x_i, y_i in zip(self._wheel_x, self._wheel_y):
            rows.append([1.0, 0.0, -y_i])
            rows.append([0.0, 1.0, x_i])
        self._pinv_a = np.linalg.pinv(np.array(rows, dtype=float))  # 3x8

        # launch 传入的参数是字符串，必须显式转 float
        self._x: float = float(self.get_parameter('initial_x').value)
        self._y: float = float(self.get_parameter('initial_y').value)
        self._yaw: float = float(self.get_parameter('initial_yaw').value)
        self._vx = 0.0
        self._vy = 0.0
        self._wz = 0.0
        self._last_stamp: Time | None = None

        self._odom_pub = self.create_publisher(Odometry, '/odom', 10)
        self._tf_broadcaster = TransformBroadcaster(self)
        self.create_subscription(JointState, '/joint_states', self._on_joint_state, 10)

        # 每个 /joint_states 消息更新一次并发布（约 100 Hz），不用定时器：
        # use_sim_time 下 rclpy 定时器的频率会被 /clock 的发布频率限制在 ~20 Hz。
        self._publish()

        self.get_logger().info(
            f'4WIS wheel odometry ready: r={self._radius:.4f} m, '
            f'{self._odom_frame} -> {self._base_frame}, '
            f'publish on /joint_states')

    # ------------------------------------------------------------------ 回调
    def _on_joint_state(self, msg: JointState) -> None:
        steer: Dict[str, float] = {}
        wheel_vel: Dict[str, float] = {}
        for name, pos, vel in zip(msg.name, msg.position, msg.velocity):
            if name in STEER_JOINTS:
                steer[name] = pos
            elif name in WHEEL_JOINTS:
                wheel_vel[name] = vel

        if len(steer) != 4 or len(wheel_vel) != 4:
            self.get_logger().warn(
                'joint_states 缺少转向角或轮速，跳过', throttle_duration_sec=2.0)
            return

        stamp = Time.from_msg(msg.header.stamp)
        if self._last_stamp is None:
            self._last_stamp = stamp
            self._publish()
            return
        dt = (stamp - self._last_stamp).nanoseconds * 1e-9
        self._last_stamp = stamp
        if dt <= 0.0 or dt > self._max_dt:
            self._publish()
            return

        # 每个轮子的轮心速度（车体坐标系）
        b: List[float] = []
        for idx, (steer_name, wheel_name) in enumerate(
                zip(STEER_JOINTS, WHEEL_JOINTS)):
            delta = steer[steer_name]
            s = wheel_vel[wheel_name] * self._radius * self._direction[idx]
            b.append(s * math.cos(delta))
            b.append(s * math.sin(delta))

        vx, vy, wz = self._pinv_a @ np.array(b, dtype=float)
        self._vx, self._vy, self._wz = float(vx), float(vy), float(wz)
        self._integrate(self._vx, self._vy, self._wz, dt)
        self._publish()

    def _integrate(self, vx: float, vy: float, wz: float, dt: float) -> None:
        """按平面刚体运动精确积分车体速度（常量 twist 假设）."""
        theta = self._yaw
        dtheta = wz * dt
        if abs(wz) < 1e-6:
            dx_b = vx * dt
            dy_b = vy * dt
        else:
            s = math.sin(theta + dtheta) - math.sin(theta)
            c = math.cos(theta + dtheta) - math.cos(theta)
            dx_b = (vx * s + vy * c) / wz
            dy_b = (-vx * c + vy * s) / wz

        self._x += math.cos(theta) * dx_b - math.sin(theta) * dy_b
        self._y += math.sin(theta) * dx_b + math.cos(theta) * dy_b
        self._yaw = math.atan2(math.sin(theta + dtheta), math.cos(theta + dtheta))

    # ------------------------------------------------------------------ 发布
    def _publish(self) -> None:
        stamp = self.get_clock().now().to_msg()

        odom = Odometry()
        odom.header = Header(stamp=stamp, frame_id=self._odom_frame)
        odom.child_frame_id = self._base_frame

        odom.pose.pose.position.x = self._x
        odom.pose.pose.position.y = self._y
        odom.pose.pose.position.z = 0.0
        odom.pose.pose.orientation.z = math.sin(self._yaw / 2.0)
        odom.pose.pose.orientation.w = math.cos(self._yaw / 2.0)

        # twist 按 REP-105 在 child frame (base_footprint) 下
        odom.twist.twist.linear.x = self._vx
        odom.twist.twist.linear.y = self._vy
        odom.twist.twist.angular.z = self._wz

        # 粗略协方差：轮式里程计横向（滑移）误差比纵向大
        odom.pose.covariance[0] = 0.02   # x
        odom.pose.covariance[7] = 0.05   # y
        odom.pose.covariance[35] = 0.03  # yaw
        odom.twist.covariance[0] = 0.01
        odom.twist.covariance[7] = 0.02
        odom.twist.covariance[35] = 0.02

        self._odom_pub.publish(odom)

        if self._publish_tf:
            tf = TransformStamped()
            tf.header.stamp = stamp
            tf.header.frame_id = self._odom_frame
            tf.child_frame_id = self._base_frame
            tf.transform.translation.x = self._x
            tf.transform.translation.y = self._y
            tf.transform.translation.z = 0.0
            tf.transform.rotation.z = math.sin(self._yaw / 2.0)
            tf.transform.rotation.w = math.cos(self._yaw / 2.0)
            self._tf_broadcaster.sendTransform(tf)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = SteerWheelOdometry()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
