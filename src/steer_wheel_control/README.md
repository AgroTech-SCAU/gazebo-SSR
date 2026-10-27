# steer_wheel_control —— 4WIS 底盘控制

真车底盘由单片机解析 `vx / vy / wz`，所以 ROS 侧只提供 `/cmd_vel`，
**不需要**在 ROS 里做四轮独立转向的运动学解算。

那这个包是干嘛的？**给 Gazebo 仿真当单片机的替身**：Gazebo 里的模型只有 8 个 ros2_control
关节，没有单片机，所以 `steer_wheel_kinematics` 节点把 `/cmd_vel` 解算成 4 个转向角 + 4 个轮速，
让仿真行为和真车一致 —— 上层算法（Nav2、遥控、脚本）在仿真和真车上看到的是同一个接口。

```
                                  ┌─ 真车：串口/CAN 驱动节点 → 单片机
/cmd_vel (vx, vy, wz) ────────────┤
                                  └─ 仿真：steer_wheel_kinematics → 8 个关节命令
```

## 运行

```bash
colcon build --symlink-install && source install/setup.bash

# 仿真：Gazebo + 生成机器人 + 控制器 + 运动学节点
ros2 launch steer_wheel_control sim.launch.py
ros2 launch steer_wheel_control sim.launch.py gui:=false rviz:=true
ros2 launch steer_wheel_control sim.launch.py use_mid360:=false   # 关闭车头 MID-360

# 只跑节点（例如已经用 steer_wheel_chassis 包的 launch 起好了仿真）
ros2 run steer_wheel_control steer_wheel_kinematics
```

```bash
# 前进 / 后退
ros2 topic pub -r 20 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.3}}"
# 横移（斜行）
ros2 topic pub -r 20 /cmd_vel geometry_msgs/msg/Twist "{linear: {y: 0.3}}"
# 斜向平移（前 0.3 + 左 0.3）
ros2 topic pub -r 20 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.3, y: 0.3}}"
# 原地自转
ros2 topic pub -r 20 /cmd_vel geometry_msgs/msg/Twist "{angular: {z: 0.5}}"
# 曲线行驶
ros2 topic pub -r 20 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.3}, angular: {z: 0.2}}"
# 停（不发了 0.5 s 后轮速自动归零；转向角保持不动）
```

键盘遥控可以直接用 `teleop_twist_keyboard`，但它只发 `linear.x` 和 `angular.z`；
要试横移得用上面那种 `ros2 topic pub` 或自己写个遥控节点。

## 解算公式

对每个车轮 i（轮心在 `base_link` 系下为 `(x_i, y_i)`）：

```
v_ix = vx - wz * y_i            轮心需要的速度矢量
v_iy = vy + wz * x_i
delta_i = atan2(v_iy, v_ix)     转向角
s_i     = hypot(v_ix, v_iy)     滚动线速度
若 |delta_i| > 90°：delta_i ±= 180°，s_i 取反     （车轮对称，缩到 ±90° 内少走行程）
omega_i = s_i / r * direction_i 轮关节速度，direction_i 见下表
```

一套公式就覆盖了三种工况，不用切模式：

| 输入 | 行为 |
|---|---|
| 只有 `vx` / `vy` | 四轮同角度 → 直行 / 任意方向斜行 (crab) |
| 只有 `wz` | 前轮 +48°、后轮 -42° 级 → 原地自转（`atan2(0.377, 0.335)`，转向比略微不对称） |
| `vx` + `wz` | 一般曲线运动，四轮角度、轮速各自独立 |

`direction_i` 由每个轮关节轴的朝向决定（不是简单的“左 / 右”）：

| 关节 | 轮轴方向（base_link） | direction_i |
|---|---|---|
| `Joint_5`（左前） | -y | **-1** |
| `Joint_6`（右前） | +y | **+1** |
| `Joint_7`（左后） | -y | **-1** |
| `Joint_8`（右后） | -y | **-1** |

`Joint_8` 的 URDF rpy 是 `(0, -π/2, +π/2)`，与左轮相同（不是右前轮的
`(0, +π/2, +π/2)`），所以它的正转方向是后退，必须用 -1。写错成 +1 的话：
右后轮被反向驱动、被地面拖着走，直线行驶时车**持续右偏**（实测 yaw 漂移
-0.001 rad/s，右后轮轮速低约 0.9 rad/s，车身只有指令速度的 86%），
原地自转也会边转边平移。修正后 yaw 漂移为 0.00000 rad/s。

`direction_i` 和轮心坐标都写死在 [steer_wheel_kinematics.py](steer_wheel_control/steer_wheel_kinematics.py)
的 `WHEEL_LAYOUT` 里，数值来自 `steer_wheel_chassis` 包的实测几何（详见 `../steer_wheel_chassis/README.md`）：
轮心 ±0.37733 / ±0.33267（x，左右不对称来自原始 CAD）、±0.33470（y）、轮半径 0.0935。
如果真车单片机用的是一组理想化参数（比如四轮完全对称 x=±0.355），
仿真里也应该改成同一组，否则两边行为会有差别。

## 参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `wheel_radius` | 0.0935 | 车轮滚动半径 [m] |
| `max_linear_velocity` | 1.5 | `/cmd_vel` 线速度截断 [m/s] |
| `max_angular_velocity` | 2.0 | `/cmd_vel` 角速度截断 [rad/s] |
| `max_wheel_velocity` | 20.0 | 轮速截断 [rad/s]，与 URDF limit 一致 |
| `max_steer_angle` | 3.14159 | 转向角截断 [rad] |
| `cmd_vel_timeout` | 0.5 | 超时后轮速归零（转向保持）[s] |
| `publish_rate` | 50.0 | 命令发布频率 [Hz] |
| `stop_linear_threshold` | 0.005 | 小于此线速度视为不动 [m/s] |
| `stop_angular_threshold` | 0.010 | 小于此角速度视为不转 [rad/s] |

## 话题

| 方向 | 话题 | 类型 |
|---|---|---|
| 订阅 | `/cmd_vel` | `geometry_msgs/msg/Twist` |
| 发布 | `/steering_position_controller/commands` | `std_msgs/msg/Float64MultiArray`（4 个转向角，顺序 LF, RF, LR, RR） |
| 发布 | `/wheel_velocity_controller/commands` | `std_msgs/msg/Float64MultiArray`（4 个轮速，顺序 LF, RF, LR, RR） |

## 上真车要改什么

1. 不要跑 `steer_wheel_kinematics`（单片机自己解算）。
2. 在这个包里加一个串口/CAN 驱动节点，订阅 `/cmd_vel` 后把 `vx, vy, wz` 按你们
   单片机的协议打包发出去；同时把单片机上来的里程计/状态转成 ROS 消息。
3. 仿真里的 `odom → base_footprint` 由
   [steer_wheel_odometry](../steer_wheel_odometry/README.md) 提供；真车上改成由单片机的
   里程计驱动同样的 `odom → base_footprint`（`base_footprint` 在地面，
   比 `base_link` 低 0.2529 m）。
4. 本节点没有发布里程计 —— 仿真里如果要跑 Nav2，需要补一个把轮速积分成里程计的节点，
   或者在单片机驱动那边一起做。

## 仿真实测（Gazebo Classic 11，49 kg 车重）

| 工况 | 指令 | 实测 | 偏差 |
|---|---|---|---|
| 直线 4 s | vx=0.3 m/s | 车身 0.292 m/s，**yaw 漂移 -0.00000 rad/s** | -2.5%（轮胎打滑） |
| 直线各速度段 | vx=±0.05~0.5 m/s | 四轮轮速与理论值差 <0.02 rad/s，yaw 漂移 0.00000 | — |
| 横移 4 s | vy=0.3 m/s | 方向 **+89.99°**，Δyaw +0.0003 rad | — |
| 原地自转 | wz=0.5 rad/s | 约 0.50~0.52 rad/s，位置基本不动 | — |
| 自转四轮转向角 | ±48.4° / ±44.8° | -0.845 / +0.782 rad | 一位不差 |
| 停止 1.5 s 后 | 轮速 0 | ~3e-4 rad/s | 超时归零生效 |

仿真特性：

1. **轮胎打滑**：直线行驶时车身约比指令慢 2~3%（轮速指令 3.21 rad/s，
   实测四轮均 3.20 rad/s，轮缘速度略高于车身速度）。打滑量取决于
   `robot.gazebo.xacro` 里的 `mu1/mu2`，真车轮胎特性不同的话可以调。
2. **自转时轮速会略低**：原地自转各轮切向滚动，实测轮速比指令低约 10%，
   但车身角速度仍与指令吻合（0.50~0.52 vs 0.5 rad/s）。

> 早期版本直线行驶会持续右偏（yaw 漂移约 -0.06°/s），原因是 `Joint_8` 的
> `direction_i` 写成了 +1（详见上面的符号表）。修正后偏航率降到 0.00000。

`colcon test --packages-select steer_wheel_control` 应全部通过。
