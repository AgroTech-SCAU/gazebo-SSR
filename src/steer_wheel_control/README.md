# steer_wheel_control

把 `/cmd_vel` 的 `vx / vy / wz` 解算成 4 个转向角和 4 个轮速，并提供完整仿真入口。

## 运行

```bash
colcon build --symlink-install && source install/setup.bash

ros2 launch steer_wheel_control sim.launch.py
ros2 launch steer_wheel_control sim.launch.py gui:=false rviz:=true
ros2 launch steer_wheel_control sim.launch.py use_mid360:=false

# 只跑节点（仿真已启动时）
ros2 run steer_wheel_control steer_wheel_kinematics
```

```bash
ros2 topic pub -r 20 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.3}}"
ros2 topic pub -r 20 /cmd_vel geometry_msgs/msg/Twist "{linear: {y: 0.3}}"
ros2 topic pub -r 20 /cmd_vel geometry_msgs/msg/Twist "{angular: {z: 0.5}}"
```

## 解算

```text
v_ix = vx - wz * y_i
v_iy = vy + wz * x_i
delta_i = atan2(v_iy, v_ix)
s_i = hypot(v_ix, v_iy)
若 |delta_i| > 90°：delta_i ±= 180°，s_i 取反
omega_i = s_i / r * direction_i
```

## 轮速方向

| 关节 | 车轮 | `direction_i` |
| --- | --- | ---: |
| `Joint_5` | 左前 | −1 |
| `Joint_6` | 右前 | +1 |
| `Joint_7` | 左后 | −1 |
| `Joint_8` | 右后 | −1 |

## 参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `wheel_radius` | 0.0935 | 车轮半径 [m] |
| `max_linear_velocity` | 1.5 | 线速度上限 [m/s] |
| `max_angular_velocity` | 2.0 | 角速度上限 [rad/s] |
| `max_wheel_velocity` | 20.0 | 轮速上限 [rad/s] |
| `max_steer_angle` | 3.14159 | 转向角上限 [rad] |
| `cmd_vel_timeout` | 0.5 | 超时后轮速归零 [s] |
| `publish_rate` | 50.0 | 命令发布频率 [Hz] |

## 话题

| 方向 | 话题 | 类型 |
| --- | --- | --- |
| 订阅 | `/cmd_vel` | `geometry_msgs/msg/Twist` |
| 发布 | `/steering_position_controller/commands` | `std_msgs/msg/Float64MultiArray` |
| 发布 | `/wheel_velocity_controller/commands` | `std_msgs/msg/Float64MultiArray` |

## 限制

- 直线行驶轮胎打滑约 2~3%。
- 原地自转时轮速比指令低约 10%，车身角速度正常。
- `/odom` 由 `steer_wheel_odometry` 发布。
