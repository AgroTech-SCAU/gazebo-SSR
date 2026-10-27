# 转运机器人 4WIS 舵轮底盘

| 包 | 内容 |
| --- | --- |
| `steer_wheel_chassis` | URDF/xacro、Gazebo world、ros2_control、Livox MID-360 |
| `steer_wheel_control` | `/cmd_vel` → 4 个转向角 + 4 个轮速 |
| `steer_wheel_odometry` | `/joint_states` → `/odom` + `odom → base_footprint` |

## 编译运行

```bash
cd <仓库根目录>
colcon build --symlink-install
source install/setup.bash

ros2 launch steer_wheel_control sim.launch.py
ros2 launch steer_wheel_control sim.launch.py gui:=false rviz:=true
ros2 launch steer_wheel_chassis display.launch.py
```

## 接口

| 方向 | 话题 | 类型 |
| --- | --- | --- |
| 订阅 | `/cmd_vel` | `geometry_msgs/msg/Twist` |
| 发布 | `/odom` | `nav_msgs/msg/Odometry` |
| 发布 | `odom → base_footprint` | TF |
| 发布 | `/joint_states` | `sensor_msgs/msg/JointState` |
| 发布 | `/mid360/pointcloud` | `sensor_msgs/msg/PointCloud2` |

控制器命令话题：

- `/steering_position_controller/commands`
- `/wheel_velocity_controller/commands`

消息类型均为 `std_msgs/msg/Float64MultiArray`。

## 启动参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `gui` | `true` | 启动 gzclient |
| `rviz` | `false` | 启动 RViz2 |
| `world` | `steer_wheel_chassis.world` | world 文件 |
| `x` / `y` / `yaw` | 0 | 生成位置与姿态 |
| `use_mesh_collision` | `false` | 原始 STL 碰撞体（慢） |
| `use_mid360` | `true` | 车头 MID-360 |
| `odometry` | `true` | 轮式里程计 |
| `max_linear_velocity` | 1.5 | 线速度上限 [m/s] |
| `max_angular_velocity` | 2.0 | 角速度上限 [rad/s] |
| `cmd_vel_timeout` | 0.5 | `/cmd_vel` 超时 [s] |

## 限制

- 没有 `/scan`；Nav2 使用 `/mid360/pointcloud` 或自行加 `pointcloud_to_laserscan`。
- 直线行驶轮胎打滑约 2~3%。
- 左右轮 x 偏移镜像，来自原始 CAD。
- MID-360 需要 `ros2_livox_simulation`；不需要时 `use_mid360:=false`。
- launch 前必须 `source install/setup.bash`。

详细说明见各包 README。
