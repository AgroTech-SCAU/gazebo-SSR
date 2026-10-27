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
Bring up the Gazebo Classic 11 + ros2_control simulation.

启动内容:
    gzserver / gzclient (gazebo_ros 官方 launch)
    robot_state_publisher  —— 发布 /robot_description 与 TF
    spawn_entity.py        —— 把模型生成到 Gazebo
    controller_manager spawner —— 依次激活 joint_state_broadcaster、
                                  steering_position_controller、wheel_velocity_controller
    (可选) rviz2

用法:
    ros2 launch steer_wheel_chassis gazebo.launch.py
    ros2 launch steer_wheel_chassis gazebo.launch.py rviz:=true
    ros2 launch steer_wheel_chassis gazebo.launch.py gui:=false            # 无界面（服务器/远程）
    ros2 launch steer_wheel_chassis gazebo.launch.py world:=/path/to.world
    ros2 launch steer_wheel_chassis gazebo.launch.py x:=1.0 y:=-0.5 yaw:=1.57

生成高度说明:
    模型根 link 是 base_footprint（base_link 在地面的投影，两者相距 0.2529 m），
    所以 z 默认 0.02：base_footprint 生成在离地 2 cm 处，让机器人自由落到地面。
"""
from __future__ import annotations

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


# Gazebo 11 在 Ubuntu 上的默认资源根目录（其下必须有 media/ 子目录）
_GAZEBO_RESOURCE_ROOT = '/usr/share/gazebo-11'


def _fix_gazebo_resource_path() -> None:
    """
    把 Gazebo 默认资源目录补进 GAZEBO_RESOURCE_PATH.

    gazebo_ros 的 GazeboRosPaths 会把 GAZEBO_RESOURCE_PATH 设成各 ROS 包导出的
    目录（这些目录下没有 media/）。Gazebo 对 GAZEBO_RESOURCE_PATH 里的每个目录
    都会再拼接 /media 查找材质/着色器，于是自带的 media 全部找不到，gzclient
    初始化 OGRE 相机时触发 boost shared_ptr<Camera> 断言并崩溃
    （表现成 GUI 窗口“未响应”后消失）。

    gazebo_ros 的 launch 会把本进程已有的 GAZEBO_RESOURCE_PATH 追加到它算出的
    列表后面，所以直接改 os.environ 就能同时修复 gzserver 和 gzclient。
    """
    if not os.path.isdir(os.path.join(_GAZEBO_RESOURCE_ROOT, 'media')):
        return
    current = os.environ.get('GAZEBO_RESOURCE_PATH', '')
    if _GAZEBO_RESOURCE_ROOT in current.split(os.pathsep):
        return
    os.environ['GAZEBO_RESOURCE_PATH'] = os.pathsep.join(
        p for p in (current, _GAZEBO_RESOURCE_ROOT) if p)


def generate_launch_description() -> LaunchDescription:
    _fix_gazebo_resource_path()

    pkg_share = get_package_share_directory('steer_wheel_chassis')
    gazebo_share = get_package_share_directory('gazebo_ros')

    xacro_file = os.path.join(pkg_share, 'urdf', 'steer_wheel_chassis.urdf.xacro')
    default_world = os.path.join(pkg_share, 'worlds', 'steer_wheel_chassis.world')
    default_rviz = os.path.join(pkg_share, 'rviz', 'steer_wheel_chassis.rviz')
    default_controllers = os.path.join(pkg_share, 'config', 'steer_wheel_controllers.yaml')

    # ---------------- launch 参数 ----------------
    world = LaunchConfiguration('world')
    gui = LaunchConfiguration('gui')
    verbose = LaunchConfiguration('verbose')
    entity = LaunchConfiguration('entity')
    use_sim_time = LaunchConfiguration('use_sim_time')
    use_mesh_collision = LaunchConfiguration('use_mesh_collision')
    use_mid360 = LaunchConfiguration('use_mid360')
    controllers_file = LaunchConfiguration('controllers_file')

    declared_arguments = [
        DeclareLaunchArgument(
            'world', default_value=default_world,
            description='Gazebo world 文件，默认为包内 worlds/steer_wheel_chassis.world'),
        DeclareLaunchArgument(
            'gui', default_value='true',
            description='是否启动 gzclient 图形界面'),
        DeclareLaunchArgument(
            'verbose', default_value='false',
            description='gzserver 输出详细信息（调试物理/插件问题时打开）'),
        DeclareLaunchArgument(
            'entity', default_value='robot',
            description='Gazebo 中的模型名'),
        DeclareLaunchArgument(
            'x', default_value='0.0', description='生成位置 x [m]'),
        DeclareLaunchArgument(
            'y', default_value='0.0', description='生成位置 y [m]'),
        DeclareLaunchArgument(
            'z', default_value='0.02',
            description='生成位置 z [m]（模型根 link 是 base_footprint，落在地面即 z=0）'),
        DeclareLaunchArgument(
            'yaw', default_value='0.0', description='生成姿态 yaw [rad]'),
        DeclareLaunchArgument(
            'rviz', default_value='false', description='额外启动 RViz2'),
        DeclareLaunchArgument(
            'use_sim_time', default_value='true', description='使用 Gazebo 仿真时钟'),
        DeclareLaunchArgument(
            'use_mesh_collision', default_value='false',
            description='用原始 STL 网格作为碰撞体（精确但很慢）'),
        DeclareLaunchArgument(
            'use_mid360', default_value='true',
            description='在车头安装 Livox MID-360（false 则不生成传感器）'),
        DeclareLaunchArgument(
            'controllers_file', default_value=default_controllers,
            description='ros2_control 控制器配置文件'),
    ]

    # ---------------- 模型描述 ----------------
    robot_description = ParameterValue(
        Command([
            'xacro ', xacro_file,
            ' use_mesh_collision:=', use_mesh_collision,
            ' use_mid360:=', use_mid360,
            ' controllers_file:=', controllers_file,
        ]),
        value_type=str,
    )

    # ---------------- Gazebo ----------------
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_share, 'launch', 'gazebo.launch.py')),
        launch_arguments={
            'world': world,
            'gui': gui,
            'verbose': verbose,
            # server_required:=true 时关掉 gzserver 会连带结束整个 launch
            'server_required': 'false',
        }.items(),
    )

    # ---------------- 状态发布 ----------------
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': use_sim_time,
        }],
    )

    # ---------------- 生成模型 ----------------
    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        name='spawn_entity',
        output='screen',
        arguments=[
            '-topic', 'robot_description',
            '-entity', entity,
            '-x', LaunchConfiguration('x'),
            '-y', LaunchConfiguration('y'),
            '-z', LaunchConfiguration('z'),
            '-Y', LaunchConfiguration('yaw'),
        ],
    )

    # ---------------- 控制器 ----------------
    # 一个 spawner 顺序加载 3 个控制器：先 joint_state_broadcaster，再两个控制器
    load_controllers = Node(
        package='controller_manager',
        executable='spawner',
        name='spawner',
        output='screen',
        arguments=[
            'joint_state_broadcaster',
            'steering_position_controller',
            'wheel_velocity_controller',
            '--controller-manager', '/controller_manager',
            '--controller-manager-timeout', '60',
        ],
    )

    # 模型生成完成后才能加载控制器（此时硬件接口才存在）
    load_controllers_after_spawn = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=spawn_entity,
            on_exit=[load_controllers],
        )
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', default_rviz],
        parameters=[{'use_sim_time': use_sim_time}],
        condition=IfCondition(LaunchConfiguration('rviz')),
    )

    return LaunchDescription(
        declared_arguments + [
            gazebo,
            robot_state_publisher,
            spawn_entity,
            load_controllers_after_spawn,
            rviz,
        ]
    )
