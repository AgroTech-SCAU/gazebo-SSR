# steer_wheel_chassis

四轮独立转向 (4WIS) 机器人模型与 Gazebo Classic 11 仿真。

## 目录

```text
src/steer_wheel_chassis/
├── urdf/
│   ├── steer_wheel_chassis.urdf.xacro
│   ├── steer_wheel_chassis.gazebo.xacro
│   ├── steer_wheel_chassis.ros2_control.xacro
│   └── steer_wheel_chassis.mid360.xacro
├── launch/
│   ├── display.launch.py
│   └── gazebo.launch.py
├── config/steer_wheel_controllers.yaml
├── worlds/steer_wheel_chassis.world
├── rviz/steer_wheel_chassis.rviz
└── meshes/*.stl
```

## 编译运行

```bash
cd <仓库根目录>
colcon build --symlink-install
source install/setup.bash

# RViz
ros2 launch steer_wheel_chassis display.launch.py

# Gazebo
ros2 launch steer_wheel_chassis gazebo.launch.py
ros2 launch steer_wheel_chassis gazebo.launch.py gui:=false rviz:=true
ros2 launch steer_wheel_chassis gazebo.launch.py use_mid360:=false
ros2 launch steer_wheel_chassis gazebo.launch.py use_mesh_collision:=true
```

启动参数：`world`、`gui`、`verbose`、`entity`、`x`、`y`、`z`、`yaw`、`rviz`、
`use_sim_time`、`use_mesh_collision`、`use_mid360`、`controllers_file`。

## 模型

| Link | 质量 | 说明 |
| --- | ---: | --- |
| `base_link` | 25.0 kg | 车体 0.86 × 0.86 × 0.346 m |
| `Link_1~4` | 2.0 kg ×4 | 转向节 |
| `Link_5~8` | 4.0 kg ×4 | 车轮，半径 0.0935 m |
| 合计 | 49.0 kg | |

- 轮心：`y = ±0.33470 m`，`x = ±0.37733 / ±0.33267 m`（左右镜像）。
- `base_footprint` 为根 link，`base_link` 离地 0.2529 m。
- 碰撞体：车体 box、转向节 box、车轮 cylinder。
  `use_mesh_collision:=true` 使用原始 STL（很慢）。
- 摩擦：车轮 `mu=1.0`，转向节 `0.1`，车体 `0.2`。

## 控制器

| 控制器 | 类型 | 关节 | 话题 |
| --- | --- | --- | --- |
| `joint_state_broadcaster` | `JointStateBroadcaster` | 全部 8 个 | `/joint_states` |
| `steering_position_controller` | `JointGroupPositionController` | `left_front, right_front, left_behind, right_behind` | `/steering_position_controller/commands` |
| `wheel_velocity_controller` | `JointGroupVelocityController` | `Joint_5, Joint_6, Joint_7, Joint_8` | `/wheel_velocity_controller/commands` |

命令类型：`std_msgs/msg/Float64MultiArray`。

## MID-360

- 位置：`x=0.46, y=0, z=0.28`，下俯 13°。
- 话题：`/mid360`（`CustomMsg`）、`/mid360/pointcloud`（`PointCloud2`）。
- 参数：`use_mid360`、`mid360_x/y/z`、`mid360_pitch`、`mid360_samples`。
- 依赖：`ros2_livox_simulation`。

## 限制

- 左右轮 x 偏移镜像，来自原始 CAD。
- 没有 `/scan`。
- 控制器 100 Hz、物理 1000 Hz，`gazebo_ros2_control` 的周期提示属正常。
- headless 下的 `Unable to find shader lib` 属正常。
- 手动启动 Gazebo 时需补
  `GAZEBO_RESOURCE_PATH=/usr/share/gazebo-11:$GAZEBO_RESOURCE_PATH`。
