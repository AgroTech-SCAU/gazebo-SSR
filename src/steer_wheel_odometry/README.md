# steer_wheel_odometry —— 舵轮底盘 (4WIS) 轮式里程计

真车的里程计由底盘单片机提供；本节点是**仿真里的替身**：用 `/joint_states` 里的
4 个转向角 + 4 个轮速做正运动学解算，积分出位姿，发布：

- `/odom`（`nav_msgs/msg/Odometry`）
- TF `odom → base_footprint`

## 解算

每个车轮 i 的轮心在 `base_link` 系下为 `(x_i, y_i)`，转向角 `delta_i`：

```
s_i  = omega_i · r · direction_i        轮子沿自身朝向的滚动线速度
v_ix = s_i · cos(delta_i)               轮心速度（车体坐标系）
v_iy = s_i · sin(delta_i)

v_ix = vx − wz · y_i
v_iy = vy + wz · x_i
```

4 个车轮给出 8 个方程解 3 个未知量 `(vx, vy, wz)`，用最小二乘。
矩阵 `A` 只与固定的轮心位置有关，所以伪逆在启动时算一次。
随后按平面刚体运动精确积分（常量 twist 假设，`wz≠0` 时走圆弧）：

```
Δθ = wz·dt
Δx = (vx·[sin(θ+Δθ)−sinθ] + vy·[cos(θ+Δθ)−cosθ]) / wz
Δy = (−vx·[cos(θ+Δθ)−cosθ] + vy·[sin(θ+Δθ)−sinθ]) / wz
```

`direction_i` 必须与运动学节点一致：**`Joint_5=-1, Joint_6=+1, Joint_7=-1, Joint_8=-1`**
（右后轮 `Joint_8` 的 rpy 与左轮相同，方向也是 -1，详见
[steer_wheel_control/README.md](../steer_wheel_control/README.md)）。

## 运行

```bash
colcon build --symlink-install && source install/setup.bash

# 单独运行
ros2 launch steer_wheel_odometry odometry.launch.py
ros2 run steer_wheel_odometry odometry

# 整个仿真（sim.launch.py 默认会带上里程计）
ros2 launch steer_wheel_control sim.launch.py
ros2 launch steer_wheel_control sim.launch.py odometry:=false   # 关掉
```

## 话题 / 参数

| 方向 | 名称 | 类型 |
|---|---|---|
| 订阅 | `/joint_states` | `sensor_msgs/msg/JointState` |
| 发布 | `/odom` | `nav_msgs/msg/Odometry` |
| 发布 | TF `odom → base_footprint` | `tf2_ros` |

| 参数 | 默认 | 说明 |
|---|---|---|
| `wheel_radius` | 0.0935 | 车轮半径 [m] |
| `wheel_x` | `[0.37733, 0.33267, -0.33267, -0.37733]` | 轮心 x（LF, RF, LR, RR）[m] |
| `wheel_y` | `[0.33470, -0.33470, 0.33470, -0.33470]` | 轮心 y [m] |
| `wheel_direction` | `[-1, 1, -1, -1]` | 轮速符号（见上） |
| `odom_frame` / `base_frame` | `odom` / `base_footprint` | 坐标系名 |
| `initial_x/y/yaw` | 0 | 初始位姿（`sim.launch.py` 会把生成位置传进来） |
| `max_dt` | 0.5 | `/joint_states` 间隔超过此值不积分 [s] |
| `publish_tf` | true | 是否发布 `odom→base_footprint` |

## 仿真实测（与 Gazebo 真值对比，49 kg 车重）

| 工况 | odom 位移/转角 | Gazebo 真值 | 误差 |
|---|---|---|---|
| 前进 vx=0.3, 3 s | dx=+0.897 m | dx=+0.897 m | <0.1% |
| 横移 vy=0.3, 3 s | dy=+0.897 m | dy=+0.897 m | <0.1% |
| 自转 wz=0.5, 3 s | dyaw=+1.534 rad | dyaw=+1.564 rad | -1.9% |

`/odom` 发布频率约 120 Hz（跟随 `/joint_states`）；TF `odom → base_footprint` 同步发布。

## 说明

- 每收到一条 `/joint_states`（约 100 Hz）就更新并发布一次 `/odom` 和 TF。
  不用定时器是因为 `use_sim_time` 下 rclpy 定时器频率会被 `/clock` 的发布频率
  限制在 ~20 Hz。
- 里程计由**轮速积分**得到，打滑会累积误差（仿真里直线约 0.3%，
  自转时更大）。真车里程计来自单片机，本节点不要在真车上运行。
- `twist` 按 REP-105 在 `base_footprint` 系下发布。
- 没有 IMU/雷达；Nav2 的 `odom → base_footprint` 由本节点提供，
  `map → odom` 仍需 AMCL 或你自己补。
- 改轮径、轮心位置或轮关节 rpy 时，要同步改 `wheel_x / wheel_y / wheel_direction`。
