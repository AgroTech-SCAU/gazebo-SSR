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
Start the 4WIS wheel odometry node.

用法:
    ros2 launch steer_wheel_odometry odometry.launch.py
    ros2 launch steer_wheel_odometry odometry.launch.py use_sim_time:=false
"""
from __future__ import annotations

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time', default_value='true',
            description='使用 Gazebo 仿真时钟'),
        DeclareLaunchArgument(
            'initial_x', default_value='0.0', description='odom 初始 x [m]'),
        DeclareLaunchArgument(
            'initial_y', default_value='0.0', description='odom 初始 y [m]'),
        DeclareLaunchArgument(
            'initial_yaw', default_value='0.0', description='odom 初始 yaw [rad]'),

        Node(
            package='steer_wheel_odometry',
            executable='odometry',
            name='steer_wheel_odometry',
            output='screen',
            parameters=[{
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'initial_x': LaunchConfiguration('initial_x'),
                'initial_y': LaunchConfiguration('initial_y'),
                'initial_yaw': LaunchConfiguration('initial_yaw'),
            }],
        ),
    ])
