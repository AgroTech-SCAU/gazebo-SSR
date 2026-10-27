# steer_wheel_chassis —— 四轮独立转向 (4WIS) 机器人描述与 Gazebo 仿真

从原始 URDF（无惯性、相对路径网格、车轮关节限位 ±π，已删除）扩展出来的 ROS 2 Humble 包：

- **模型描述**：`urdf/steer_wheel_chassis.urdf.xacro`（惯性 + 碰撞 + Gazebo 物理属性）
- **仿真**：`launch/gazebo.launch.py`（Gazebo Classic 11 + ros2_control + 8 关节控制器）
- **可视化**：`launch/display.launch.py`（RViz2，不启动 Gazebo）

## 目录结构

```
src/steer_wheel_chassis/
├── urdf/
│   ├── steer_wheel_chassis.urdf.xacro            # 主文件：link/joint/惯性/碰撞
│   ├── steer_wheel_chassis.gazebo.xacro          # 摩擦、接触参数、ros2_control 插件
│   └── steer_wheel_chassis.ros2_control.xacro    # 8 个关节的 command/state 接口
├── launch/
│   ├── display.launch.py           # RViz2 查看模型
│   └── gazebo.launch.py            # Gazebo + 生成 + 控制器
├── config/steer_wheel_controllers.yaml   # controller_manager 与控制器配置
├── worlds/steer_wheel_chassis.world              # 1 ms 步长 ODE 世界
├── rviz/steer_wheel_chassis.rviz                 # RViz 配置（RobotModel + TF + Grid）
├── test/test_{copyright,flake8,pep257}.py   # ament linter
└── meshes/*.stl                    # 原始网格（未改动）
```

`colcon test --packages-select steer_wheel_chassis` 全部通过（16 tests, 0 failures）。

## 编译与运行

```bash
cd <本仓库根目录>
colcon build --symlink-install
source install/setup.bash

# 只看模型
ros2 launch steer_wheel_chassis display.launch.py

# Gazebo 仿真（无界面 / 带 RViz）
ros2 launch steer_wheel_chassis gazebo.launch.py
ros2 launch steer_wheel_chassis gazebo.launch.py gui:=false rviz:=true
```

可用参数（`ros2 launch steer_wheel_chassis gazebo.launch.py -s` 查看全部）：
`world` `gui` `verbose` `entity` `x` `y` `z` `yaw` `rviz`
`use_sim_time` `use_mesh_collision` `controllers_file`。

> **Gazebo GUI 崩溃修复**：launch 会在包含 gazebo_ros 的 launch 之前，把
> `/usr/share/gazebo-11` 追加到 `GAZEBO_RESOURCE_PATH`。原因是 gazebo_ros 的
> `GazeboRosPaths` 把该变量覆盖成各 ROS 包导出的目录，而 Gazebo 会对每个目录
> 再拼接 `/media` 查找材质/着色器；这些目录下都没有 `media/`，导致 gzclient
> 初始化 OGRE 相机时触发 `boost::shared_ptr<Camera>` 断言崩溃
> （窗口“未响应”后消失）。注意要加的是 **`/usr/share/gazebo-11`**
> （其下有 `media/`），不是 `/usr/share/gazebo-11/media`。

## 控制接口

| 控制器 | 类型 | 关节（命令数组顺序） | 话题 |
|---|---|---|---|
| `joint_state_broadcaster` | JointStateBroadcaster | 全部 8 个 | `/joint_states` |
| `steering_position_controller` | JointGroupPositionController | `left_front, right_front, left_behind, right_behind` | `/steering_position_controller/commands` |
| `wheel_velocity_controller` | JointGroupVelocityController | `Joint_5, Joint_6, Joint_7, Joint_8`（左前、右前、左后、右后） | `/wheel_velocity_controller/commands` |

消息类型均为 `std_msgs/msg/Float64MultiArray`。

> 话题名是 **`/commands` 复数**（Humble 的 `JointGroup*Controller` 用复数，
> 很多网上教程写单数 `/command` 是错的，发出去没有任何反应也不会报错）。
> 命令订阅的 QoS 是 `BEST_EFFORT`，`ros2 topic pub`（reliable）兼容。

```bash
# 转向：四个轮子同向 0.3 rad（斜行 / crab）
ros2 topic pub --once /steering_position_controller/commands \
  std_msgs/msg/Float64MultiArray "{data: [0.3, 0.3, 0.3, 0.3]}"

# 直行：左轮 -5 rad/s、右轮 +5 rad/s（轮半径 0.0935 → 约 0.47 m/s）
ros2 topic pub -r 20 /wheel_velocity_controller/commands \
  std_msgs/msg/Float64MultiArray "{data: [-5.0, 5.0, -5.0, 5.0]}"

# 原地自转：前轮 +45°，后轮 -45°
ros2 topic pub --once /steering_position_controller/commands \
  std_msgs/msg/Float64MultiArray "{data: [0.785, 0.785, -0.785, -0.785]}"
```

> `ros2 topic pub --once` 偶尔会报 `failed to get subscription count: publisher's
> context is invalid`，这是 Humble CLI 的已知小毛病，消息能发出去；不放心可以加 `-w 1`
> 等订阅者匹配，或者用 `-r 20` 连发几秒。

**车轮速度符号**（已用仿真实测验证）：符号取决于每个轮关节轴在车体坐标系里的朝向，
不是简单的“左 / 右”：

| 关节 | 轮轴方向（base_link） | 前进 (+x) 时的关节速度 |
|---|---|---|
| `Joint_5`（左前） | -y | **负** |
| `Joint_6`（右前） | +y | **正** |
| `Joint_7`（左后） | -y | **负** |
| `Joint_8`（右后） | -y | **负** |

`Joint_8` 的 rpy 是 `(0, -π/2, +π/2)`，与左轮相同（不是右前轮那种
`(0, +π/2, +π/2)`），所以右后轮的符号与左轮一致。**如果按“右轮为正”处理，
右后轮会被反向驱动**：直线行驶时车持续右偏（实测 yaw 漂移 -0.001 rad/s，
右后轮轮速比其它轮低约 0.9 rad/s，车身只能达到指令速度的 86%），
原地自转也会变成边转边平移。修正后 yaw 漂移为 0.00000 rad/s。

**转向角符号**：四个转向关节同时给 +δ 时，机器人沿 `+x` 逆时针偏转 δ 的方向平移
（实测 δ=0.3 rad、驱动 5 s，位移 2.57 m，方向 17.2°，误差 <0.1°）。

## 物理属性

质量与惯性张量不是拍脑袋填的：把每个 STL 当闭合三角网格做四面体积分，得到网格体积、
质心和**单位质量惯性张量**，再乘以选定质量。xacro 里写的就是单位质量张量，
所以改 `base_mass / leg_mass / wheel_mass` 时惯性会自动等比缩放。

| Link | 质量 [kg] | 网格体积 [m³] | 说明 |
|---|---|---|---|
| `base_link` | 25.0 | 9.149e-3 | 车体 0.86×0.86×0.346 m，质心 z=0.149 |
| `Link_1~4` | 2.0 ×4 | 7.3e-4 | 转向节（含减速器），质心在 z≈-0.07 |
| `Link_5~8` | 4.0 ×4 | 2.11e-3 | 车轮（含轮毂电机），轮半径 0.0935 m |
| **合计** | **49.0** | | |

质量是按工业 AGV 的量级假设的（有效密度约 2700 kg/m³），**如果知道真实称重请直接改质量**，
惯性会自动跟着变。

碰撞体默认用**简化几何**代替原始网格，因为 `base_link.stl` 有 15 MB / 31.8 万个三角形，
直接拿来做碰撞体会让 Gazebo 物理计算慢到不可用：

- 车体：`box 0.86×0.86×0.346`（包围盒包络）
- 转向节：`box 0.24×0.125×0.189`（逐 link 实测包围盒）
- 车轮：`cylinder r=0.0935, l=0.0449`（实测滚动半径与胎面宽，轴向 = local z 轮轴）

需要精确碰撞时：`ros2 launch steer_wheel_chassis gazebo.launch.py use_mesh_collision:=true`（会很慢）。

### 关键几何数据（决定生成高度）

四轮中心的实测位置均为 `z = -0.1594 m`、`y = ±0.335 m`（在 `base_link` 系下），
轮半径 0.0935 m，所以**轮胎着地时 `base_link` 离地 0.2529 m**。模型根 link 是
`base_footprint`（`base_link` 在地面的投影，fixed joint 抬高 0.2529 m），
所以 launch 里 `-z` 默认 0.02 —— base_footprint 落在地面时 z≈0，机器人自由落体 2 cm
后停住（实测稳定在 0.2518，与 0.2529 差 1 mm 即接触面穿透，吻合）。

### 摩擦与接触参数

| 部位 | mu1/mu2 | kp | kd | 理由 |
|---|---|---|---|---|
| 车轮 | 1.0 | 1e6 | 10 | 橡胶对地板的真实量级；4WIS 原地转向需要车轮能侧向擦地滑移 |
| 转向节 | 0.1 | 1e6 | 100 | 不该抓地 |
| 车体 | 0.2 | 1e6 | 100 | 避免底盘被地面蹭住 |

TurtleBot3 风格的 `mu=10000`（近似无限摩擦）在 4WIS 上会让转向关节原地拧死并抖动，
不要直接照搬。需要各向异性摩擦（纵向抓 / 侧向滑）时，`steer_wheel_chassis.gazebo.xacro` 里已注明
四个车轮的滚动方向在各自 link 系下都是 `local -y`，可打开 `<fdir1>0 -1 0</fdir1>`。

### 相对原始 URDF 的改动

1. 补齐 9 个 link 的 `<inertial>`（原始 URDF 没有惯性，Gazebo 会拒绝加载 / 物体乱飞）
2. 车轮关节 `revolute (±3.14159)` → `continuous`（车轮必须能连续转）
3. 网格路径 `meshes/x.stl` → `package://steer_wheel_chassis/meshes/x.stl`
   （配套在 `package.xml` 里 export 了 `<gazebo_ros gazebo_model_path="${prefix}/.."/>`，
   否则 Gazebo 解析不了 `model://robot/meshes/...`）
4. 关节上限从 `effort=10 / velocity=1` 改为可调参数，默认转向 `20 N·m / 3 rad/s`、
   车轮 `20 N·m / 20 rad/s`：原值下轮速 1 rad/s 只有 9.4 cm/s，仿真里几乎不动
5. 增加关节 `<dynamics damping>`：转向 0.2、车轮 0.05，控制器未加载时不会自己乱滑
6. 增加 `base_footprint`（地面投影）+ `base_joint`（fixed），既是 Nav2 惯例基准，
   也消除了 robot_state_publisher 的 “root link has an inertia” KDL 警告

**关节 origin/rpy/axis 与原始 URDF 完全一致，没有改动运动学。**

## Livox MID-360（车头）

使用系统已安装的 `ros2_livox_simulation`（Gazebo ray 传感器 + `libros2_livox.so` +
`scan_mode/mid360.csv`），传感器定义在 `urdf/steer_wheel_chassis.mid360.xacro`。

**安装位姿**（`base_link` 系）：`x=0.46, y=0, z=0.28`，**向下俯 13°**（`pitch=+0.226893`，
ROS 中绕 +y 正转会把传感器 +x 轴压向 -z）。传感器 +x 为出光前向，+y 左，+z 上；
MID-360 的垂直视场 -7.22°~+55.22° 是相对 +x 的，13° 下俯后相对车体水平面约为
-20.2°~+42.2°。

| 话题 | 类型 | 说明 |
|---|---|---|
| `/mid360` | `livox_ros_driver2/msg/CustomMsg` | Livox 原始格式 |
| `/mid360/pointcloud` | `sensor_msgs/msg/PointCloud2` | 常规点云，frame_id=`mid360`，约 10 Hz |

可调参数（xacro args，可通过 launch 覆盖 `use_mid360`）：

| 参数 | 默认 | 说明 |
|---|---|---|
| `use_mid360` | `true` | 是否安装传感器；launch 参数 `use_mid360:=false` 可关闭 |
| `mid360_x` / `mid360_y` / `mid360_z` | 0.46 / 0 / 0.28 | 安装位置 [m] |
| `mid360_pitch` | 0.226893 | 俯仰角 [rad]，正值下俯 |

实测（与地面拟合）：下俯 **12.72°**（期望 13°，误差 0.28°），平面残差 RMS 2.3 mm。
**性能**：插件按 `<samples>` 逐条 `AddRay`，每帧射线数 = samples（`<ray><scan>`
里的 100×360 网格基本不参与）。`mid360_samples` 默认 **10000**：
空世界 RTF ≈ 0.9~1.0；甜椒大棚（含全部结构碰撞体）RTF ≈ **0.38**，
每帧约 20000 点（`accumulate_scans=2`），墙钟约 4 Hz。
40000 时大棚 RTF 只有 0.065，所以默认降到了 10000。需要更流畅可以把
`mid360_samples` 降到 5000，或把 `<update_rate>` 从 10 降到 5 Hz。

注意事项：

- 传感器必须带 `<always_on>true</always_on>`，否则 Gazebo 不更新传感器、插件回调不触发
  （表现为话题存在但收不到数据）。因此这里没有直接 include 上游的 `mid360.xacro`。
- 模型里没有 `sensor_msgs/LaserScan` 的 `/scan`；Nav2 要么用点云层（如
  `voxel_layer`/`obstacle_layer` 的 pointcloud 输入），要么另加 `pointcloud_to_laserscan`。

## 调试命令

```bash
ros2 control list_controllers                    # 控制器状态
ros2 control list_hardware_interfaces            # 硬件接口
ros2 topic echo /joint_states --once             # 关节反馈
ros2 topic hz /joint_states                      # 发布频率
ros2 run tf2_tools view_frames                   # 导出 TF 树 PDF
gz model -m robot -p                             # Gazebo 里模型当前位姿
ros2 launch steer_wheel_chassis gazebo.launch.py verbose:=true # 打开 gzserver 详细输出
```

## 已知事项 / 后续

- **左右轮 x 偏移是镜像的**：左前轮中心 x=+0.3773、右前轮 x=+0.3327（后轮同理反号），
  即左右转向节的轮子在转向轴前/后的偏移方向相反。这来自原始 CAD 导出的 link 系定义，
  本次未改动；如果设计上是四个轮子都往同一侧偏，需要修正 `Joint_5~8` 的 origin。
- **这个包只到 8 个关节命令为止**。要用 `/cmd_vel`（vx/vy/wz）控制，见
  [steer_wheel_control](../steer_wheel_control/README.md)：仿真里由 `steer_wheel_kinematics`
  节点当单片机替身做 4WIS 解算（真车由底盘单片机自己解算）。
- 模型本身没有 `odom` 帧；仿真里由
  [steer_wheel_odometry](../steer_wheel_odometry/README.md) 根据轮速/转向角积分，
  发布 `/odom` 和 `odom → base_footprint`。真车里程计由底盘单片机提供。
- `gazebo_ros2_control` 会打印 `Desired controller update period (0.01 s) is slower
  than the gazebo simulation period (0.001 s)`：控制器 100 Hz、物理 1000 Hz，
  属正常提示，不是错误。
- 无界面跑 gzserver 时会报 `Unable to find shader lib`：headless 下没有 GL 上下文，
  不影响物理与控制。
