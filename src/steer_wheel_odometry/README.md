# steer_wheel_odometry

由 `/joint_states` 的 4 个转向角和 4 个轮速解算 `/odom` 与
`odom → base_footprint`。

## 解算

```text
s_i  = omega_i * r * direction_i
v_ix = s_i * cos(delta_i)
v_iy = s_i * sin(delta_i)

v_ix = vx - wz * y_i
v_iy = vy + wz * x_i
```

4 个车轮给出 8 个方程，用最小二乘解 `(vx, vy, wz)`，再按平面刚体运动积分。

## 运行

```bash
colcon build --symlink-install && source install/setup.bash

ros2 launch steer_wheel_odometry odometry.launch.py
ros2 run steer_wheel_odometry odometry
```

完整仿真由 `steer_wheel_control` 的 `sim.launch.py` 默认启动本节点。

## 话题

| 方向 | 话题 | 类型 |
| --- | --- | --- |
| 订阅 | `/joint_states` | `sensor_msgs/msg/JointState` |
| 发布 | `/odom` | `nav_msgs/msg/Odometry` |
| 发布 | `odom → base_footprint` | TF |

## 参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `wheel_radius` | 0.0935 | 车轮半径 [m] |
| `wheel_x` | `[0.37733, 0.33267, -0.33267, -0.37733]` | 轮心 x（LF, RF, LR, RR） |
| `wheel_y` | `[0.33470, -0.33470, 0.33470, -0.33470]` | 轮心 y |
| `wheel_direction` | `[-1, 1, -1, -1]` | 轮速符号 |
| `odom_frame` / `base_frame` | `odom` / `base_footprint` | 坐标系 |
| `initial_x/y/yaw` | 0 | 初始位姿 |
| `max_dt` | 0.5 | 超过此间隔不积分 [s] |
| `publish_tf` | true | 发布 `odom → base_footprint` |

## 限制

- 轮速积分会累积打滑误差。
- 没有 IMU/雷达；`map → odom` 需 AMCL 或其它定位节点。
- 改轮径、轮心位置或轮关节方向时，同步修改上述参数。
