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
Gazebo simulation with the 4WIS chassis kinematics node.

= steer_wheel_chassis 包的 gazebo.launch.py（Gazebo + 生成 + 8 关节 ros2_control）
  + steer_wheel_control 的 steer_wheel_kinematics（/cmd_vel → 转向角 + 轮速）
  + steer_wheel_odometry 的轮式里程计（/joint_states → /odom + odom→base_footprint）

这样仿真里的底盘接口和真车一致：只给 /cmd_vel 的 vx / vy / wz。

用法:
    ros2 launch steer_wheel_control sim.launch.py
    ros2 launch steer_wheel_control sim.launch.py gui:=false rviz:=true

    ros2 topic pub -r 20 /cmd_vel geometry_msgs/msg/Twist \\
      "{linear: {x: 0.3, y: 0.0}, angular: {z: 0.0}}"     # 前进 0.3 m/s
    ros2 topic pub -r 20 /cmd_vel geometry_msgs/msg/Twist \\
      "{linear: {x: 0.0, y: 0.3}, angular: {z: 0.0}}"     # 横移 0.3 m/s
    ros2 topic pub -r 20 /cmd_vel geometry_msgs/msg/Twist \\
      "{linear: {x: 0.0, y: 0.0}, angular: {z: 0.5}}"     # 原地自转 0.5 rad/s
"""
from __future__ import annotations

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    robot_launch = os.path.join(
        get_package_share_directory('steer_wheel_chassis'), 'launch', 'gazebo.launch.py')

    # 只透传常用的几个参数，其余用 steer_wheel_chassis 包 gazebo.launch.py 的默认值
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(robot_launch),
        launch_arguments={
            'gui': LaunchConfiguration('gui'),
            'rviz': LaunchConfiguration('rviz'),
            'world': LaunchConfiguration('world'),
            'x': LaunchConfiguration('x'),
            'y': LaunchConfiguration('y'),
            'yaw': LaunchConfiguration('yaw'),
            'use_mesh_collision': LaunchConfiguration('use_mesh_collision'),
            'use_mid360': LaunchConfiguration('use_mid360'),
        }.items(),
    )

    kinematics = Node(
        package='steer_wheel_control',
        executable='steer_wheel_kinematics',
        name='steer_wheel_kinematics',
        output='screen',
        parameters=[{
            'wheel_radius': 0.0935,
            'max_linear_velocity': LaunchConfiguration('max_linear_velocity'),
            'max_angular_velocity': LaunchConfiguration('max_angular_velocity'),
            'cmd_vel_timeout': LaunchConfiguration('cmd_vel_timeout'),
        }],
    )

    # 轮式里程计（仿真里代替底盘单片机发 odom）
    odometry = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory('steer_wheel_odometry'),
            'launch', 'odometry.launch.py')),
        launch_arguments={
            'use_sim_time': 'true',
            'initial_x': LaunchConfiguration('x'),
            'initial_y': LaunchConfiguration('y'),
            'initial_yaw': LaunchConfiguration('yaw'),
        }.items(),
        condition=IfCondition(LaunchConfiguration('odometry')),
    )

    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='true',
                              description='启动 gzclient 图形界面'),
        DeclareLaunchArgument('rviz', default_value='false',
                              description='额外启动 RViz2'),
        DeclareLaunchArgument(
            'world',
            default_value=os.path.join(
                get_package_share_directory('steer_wheel_chassis'),
                'worlds', 'steer_wheel_chassis.world'),
            description='Gazebo world 文件'),
        DeclareLaunchArgument('x', default_value='0.0', description='生成位置 x [m]'),
        DeclareLaunchArgument('y', default_value='0.0', description='生成位置 y [m]'),
        DeclareLaunchArgument('yaw', default_value='0.0', description='生成姿态 yaw [rad]'),
        DeclareLaunchArgument('use_mesh_collision', default_value='false',
                              description='用原始 STL 网格作为碰撞体（很慢）'),
        DeclareLaunchArgument('use_mid360', default_value='true',
                              description='车头 Livox MID-360（false 则关闭）'),
        DeclareLaunchArgument('max_linear_velocity', default_value='1.5',
                              description='cmd_vel 线速度上限 [m/s]'),
        DeclareLaunchArgument('max_angular_velocity', default_value='2.0',
                              description='cmd_vel 角速度上限 [rad/s]'),
        DeclareLaunchArgument('cmd_vel_timeout', default_value='0.5',
                              description='多久没收到 /cmd_vel 就轮速归零 [s]'),
        DeclareLaunchArgument('odometry', default_value='true',
                              description='启动轮式里程计（发布 /odom 与 odom->base_footprint）'),
        gazebo,
        kinematics,
        odometry,
    ])
