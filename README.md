# gazebo-SSR — Gazebo 仿真资源库

收集农业机器人开发中用到的 **Gazebo Classic 11** 仿真资源，包括甜椒大棚场景、
转运机器人底盘、传感器配置等。仓库采用 **`main` 介绍 + 资源分支** 的组织方式：
默认分支只保留索引与使用说明，具体的模型、场景和功能包存放在独立的长期分支中。

> 当前环境基准：Ubuntu 22.04 + ROS 2 Humble + Gazebo Classic 11。

## 目录

- [1. 仓库组织方式](#1-仓库组织方式)
- [2. 资源列表](#2-资源列表)
- [3. 环境要求](#3-环境要求)
- [4. 快速开始](#4-快速开始)
- [5. 资源详解：甜椒大棚](#5-资源详解甜椒大棚)
- [6. 资源详解：转运机器人底盘](#6-资源详解转运机器人底盘)
- [7. 目录结构](#7-目录结构)
- [8. 开发与维护](#8-开发与维护)
- [9. 常见问题](#9-常见问题)
- [10. 版本与发布](#10-版本与发布)
- [11. 维护者](#11-维护者)

## 1. 仓库组织方式

```text
main                              # 介绍、索引、协作规范（不含模型资源）
├── sim/sweet-pepper-greenhouse   # 100×100 m 甜椒大棚场景（独立场景包）
└── sim/transfer-robot-chassis    # 转运机器人 4WIS 舵轮底盘仿真
```

### 为什么要用分支存资源

- `main` 保持轻量：README、`docs/`、协作模板和少量预览图，克隆和浏览都很快。
- 每个资源可以独立检出、独立编译、独立发布，互不干扰。
- 资源分支只放该资源自己的包：大棚分支只有场景包，底盘分支只有底盘包。
- 场景包**不依赖具体底盘**，可以通过 `world:=` 参数直接给其它底盘复用。
- 资源分支是**长期分支**，不要合并回 `main`；文档更新从 `main` 合并到资源分支即可。

### 分支命名

| 分支 | 含义 | 主要内容 |
| --- | --- | --- |
| `main` | 仓库索引 | 介绍、环境、编译、运行、协作规范 |
| `sim/sweet-pepper-greenhouse` | 甜椒大棚场景 | `pepper_greenhouse`（独立场景包） |
| `sim/transfer-robot-chassis` | 转运机器人底盘 | `steer_wheel_chassis`、`steer_wheel_control`、`steer_wheel_odometry` |

## 2. 资源列表

| 分支 | 资源 | 功能包 | 主要内容 |
| --- | --- | --- | --- |
| `main` | 仓库介绍与索引 | — | 环境、获取、编译、运行说明 |
| `sim/sweet-pepper-greenhouse` | 100×100 m 甜椒大棚场景 | `pepper_greenhouse` | 布局档/视觉档、实体轨道与沟槽、420 根立柱、两台巡检相机、可配合任意底盘 |
| `sim/transfer-robot-chassis` | 转运机器人 4WIS 舵轮底盘 | `steer_wheel_chassis`、`steer_wheel_control`、`steer_wheel_odometry` | URDF/xacro、ros2_control、`/cmd_vel` 运动学解算、轮式里程计、Livox MID-360 |

说明：

- `sim/sweet-pepper-greenhouse` 是**纯场景包**，不依赖任何底盘；单独启动只开 Gazebo 和 world。
- `sim/transfer-robot-chassis` 只包含底盘相关包，不含大棚场景。
- 两个资源分支互相独立；需要“大棚 + 底盘”联仿时，把两个包放进同一个工作空间，
  通过底盘 launch 的 `world:=` 参数加载大棚 world（见 [5.9](#59-与任意底盘组合)）。
- 阿克曼底盘 `ackermann_chassis` 暂不在收集范围内，未纳入任何分支。

## 3. 环境要求

### 3.1 软件

| 项目 | 要求 |
| --- | --- |
| OS | Ubuntu 22.04 |
| ROS 2 | Humble（desktop 或基础版 + 所需组件） |
| Gazebo | Gazebo Classic 11（`gazebo_ros`、`gazebo_ros2_control`） |
| 编译 | `colcon`、`colcon-common-extensions` |
| Python | 3.10 |
| 可视化 | `rviz2`、`joint_state_publisher_gui` |
| 关键依赖 | `xacro`、`robot_state_publisher`、`python3-numpy`、`python3-yaml`、`python3-pil` |
| 雷达仿真（可选） | `ros2_livox_simulation`（不在 rosdep 索引中，需要单独安装） |

### 3.2 安装依赖

切换资源分支后，在仓库根目录执行：

```bash
rosdep install --from-paths src --ignore-src -r -y \
  --skip-keys ros2_livox_simulation
```

`ros2_livox_simulation` 提供 MID-360 插件和 `scan_mode/mid360.csv`。本机如果已有
`/opt/ros/humble/share/ros2_livox_simulation` 就可以直接使用；没有安装时，启动加
`use_mid360:=false` 关闭雷达即可。

## 4. 快速开始

### 4.1 克隆并切换分支

```bash
git clone <本仓库 URL> gazebo-SSR
cd gazebo-SSR

# 甜椒大棚场景
git switch sim/sweet-pepper-greenhouse

# 或者：转运机器人底盘
git switch sim/transfer-robot-chassis
```

只拉取某一个资源分支：

```bash
git clone --single-branch --branch sim/sweet-pepper-greenhouse \
  <本仓库 URL> gazebo-SSR
```

### 4.2 编译

仓库根目录就是 colcon 工作空间根目录：

```bash
cd gazebo-SSR
colcon build --symlink-install
source install/setup.bash
```

> 必须 `source install/setup.bash`，否则 Gazebo 无法解析 `model://`，launch 也找不到包。

### 4.3 运行甜椒大棚（`sim/sweet-pepper-greenhouse`）

```bash
# 布局档：场景轻、headless 下实时因子接近 1，适合 Nav2 / 路径验证
ros2 launch pepper_greenhouse pepper_greenhouse_world.launch.py gui:=false

# GUI 看布局
ros2 launch pepper_greenhouse pepper_greenhouse_world.launch.py

# 加密植株视觉档（截图用）
ros2 launch pepper_greenhouse pepper_greenhouse_world.launch.py profile:=visual gui:=true

# 暂停启动，方便先摆相机/机器人
ros2 launch pepper_greenhouse pepper_greenhouse_world.launch.py pause:=true
```

这个 launch **只启动 Gazebo 和 world**，不生成机器人、不加载控制器。
要与 4WIS 底盘或其它底盘联仿，见 [5.9 与任意底盘组合](#59-与任意底盘组合)。

![大棚中央通道](docs/images/greenhouse_aisle.png)

![大棚床区](docs/images/greenhouse_bed.png)

### 4.4 运行转运机器人底盘（`sim/transfer-robot-chassis`）

```bash
# 完整仿真：Gazebo + 机器人 + 控制器 + /cmd_vel 运动学 + 轮式里程计
ros2 launch steer_wheel_control sim.launch.py
ros2 launch steer_wheel_control sim.launch.py gui:=false rviz:=true
ros2 launch steer_wheel_control sim.launch.py use_mid360:=false   # 关闭车头 MID-360

# 只看模型（RViz2 + 关节滑块）
ros2 launch steer_wheel_chassis display.launch.py

# 只起 Gazebo 与控制器，再单独跑运动学节点
ros2 launch steer_wheel_chassis gazebo.launch.py
ros2 run steer_wheel_control steer_wheel_kinematics
```

### 4.5 常用 `/cmd_vel`

```bash
# 前进 / 后退
ros2 topic pub -r 20 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.3}}"
# 横移（斜行）
ros2 topic pub -r 20 /cmd_vel geometry_msgs/msg/Twist "{linear: {y: 0.3}}"
# 斜向平移
ros2 topic pub -r 20 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.3, y: 0.3}}"
# 原地自转
ros2 topic pub -r 20 /cmd_vel geometry_msgs/msg/Twist "{angular: {z: 0.5}}"
# 曲线行驶
ros2 topic pub -r 20 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.3}, angular: {z: 0.2}}"
# 停：不发 0.5 s 后轮速自动归零，转向角保持不动
```

键盘遥控可以直接用 `teleop_twist_keyboard`，但它只发 `linear.x` 和 `angular.z`；
要试横移得用上面的 `ros2 topic pub` 或自己写遥控节点。

## 5. 资源详解：甜椒大棚

分支：`sim/sweet-pepper-greenhouse`
功能包：`pepper_greenhouse`

### 5.1 定位与设计取舍

基于 8 张现场实拍图搭建的 100×100 m 室内甜椒大棚。**独立场景包**，
不依赖任何底盘；任何机器人/底盘都可以通过 `world:=` 参数或 `spawn_entity`
放进这个场景。设计取舍是**布局优先**：

- 通道、沟槽、行距、轨道和棚体结构按实拍比例还原。
- 植株用连续冠层带 + 稀疏低模八面体表示，不做逐株精细模型。
- headless 下实时因子接近 1，可直接用于 Nav2 / 路径验证。
- 场景内固定放置两台巡检相机，方便录制和检查布局。
- 只包含 world、模型、相机和生成脚本；不生成机器人、不加载控制器。

### 5.2 尺寸基准

照片里中央通道的两条钢轨是与底盘轨道接口配合的。当前尺寸以仓库里的
4WIS 底盘作为**参考底盘**：轮心 `y=±0.33470 m`，因此：

```text
轨距 = 2 × 0.33470 = 0.6694 m
```

其余尺寸都由此推算：

| 项目 | 数值 | 说明 |
| --- | ---: | --- |
| 场地 | 100 × 100 m | 20 个 5 m 屋面 bay |
| 檐高 / 脊高 | 4.50 / 5.70 m | — |
| 轨道中心 | y = ±0.33470 m | 轨距 0.6694 m |
| 轨道截面 | 0.050 × 0.006 m | 5 cm 宽，6 mm 高，便于爬轨 |
| 车轮外缘 / 轨道外缘 | 0.35715 / 0.35970 m | 车轮不悬空 |
| 中央通道净宽 | 1.20 m | 沟槽内壁 ±0.60 m |
| 轮-沟槽间隙 | 0.243 m | 单侧 |
| 沟槽 | 0.35 m 宽，底 0.15 / 顶 0.35 m | 基质面 0.34 m |
| 行距 | 1.60 m | 行间走道 1.25 m |
| 每侧行数 | 30 | 最外缘 ±47.35 m |
| 侧通道 | 2.60 m | 墙内壁 ±49.95 m |
| 床区 | x ∈ [−46, +46]，92 m | 端部掉头区 3.95 m |
| 横向通道 | 2.0 m，中心 x = ±22.5 m | 柱网 x=20 / 25 之间 |
| 轨道长度 | 94 m，x ∈ [−47, +47] | 穿过横向通道 |
| 柱网 | 5.0 × 5.0 m，420 根 | y=0 柱线省略，中央通道无柱 |
| 冠层 | z = 0.35~0.50 m | 植株高 0.15 m，略低于雷达 |
| 吊蔓钢丝 / 黄管 | z = 3.80 / 2.50 m | 黄管 118 根 |

床段划分：`22.5 + 2 + 43 + 2 + 22.5 = 92 m`。

`scripts/layout.py` 是唯一尺寸来源，`Layout.validate()` 会断言轨距、轮轨间隙、
行数、通道无柱等约束。换成其它底盘时，先改 `config/greenhouse.yaml` 里的
`chassis.wheel_y` / `wheel_width` / `wheel_radius`，再重新生成 world。

### 5.3 功能包与模型组成

```text
src/pepper_greenhouse/
├── config/greenhouse.yaml          # 所有可调尺寸与密度
├── launch/pepper_greenhouse_world.launch.py  # 独立场景 launch
├── models/
│   ├── pepper_greenhouse_shell/    # 白框、玻璃、风扇、黄管、钢丝、地面
│   ├── pepper_beds_mid/            # 43 m 床段
│   ├── pepper_beds_end/            # 22.5 m 床段，东西复用
│   └── pepper_plants_dense/        # visual 档的加密植株覆盖层
├── worlds/
│   ├── pepper_greenhouse.world     # 默认布局档
│   └── pepper_greenhouse_visual.world
├── scripts/
│   ├── layout.py                   # dataclass + 派生尺寸 + validate
│   ├── generate_world.py           # 生成 world/model/二进制 STL
│   ├── check_layout.py             # 尺寸与资产检查
│   └── save_camera_frame.py        # 保存一帧巡检相机图像
└── test/test_generated_assets.py
```

### 5.4 两种 world 档位

| profile | world 文件 | 特点 | 用途 |
| --- | --- | --- | --- |
| `layout`（默认） | `pepper_greenhouse.world` | 稀疏植株，约 14.6 万三角形 | 路径规划、Nav2、日常仿真 |
| `visual` | `pepper_greenhouse_visual.world` | 加密植株，约 30 万三角形 | 截图、展示 |

### 5.5 启动参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `profile` | `layout` | `layout` 或 `visual` |
| `gui` | `true` | 是否启动 gzclient |
| `verbose` | `false` | gzserver 详细输出 |
| `pause` | `false` | 启动后暂停仿真 |

> 这个 launch 不生成机器人，所以没有 `x/y/yaw`、`use_mid360` 这类底盘参数。
> 机器人生成与传感器由你使用的底盘 launch 负责。

### 5.6 巡检相机

world 里固定放置了两台 1 Hz / 1280×720 的相机，不依赖 TF：

| 相机 | 位置 / 朝向 | 话题 |
| --- | --- | --- |
| `aisle_camera` | (30, 0, 4.5)，沿 −x 看中央通道 | `/greenhouse/aisle_camera/image_raw` |
| `bed_camera` | (0, −18, 5.5)，沿 +y 看床区 | `/greenhouse/bed_camera/image_raw` |

保存一帧：

```bash
ros2 run pepper_greenhouse save_camera_frame.py \
  /greenhouse/aisle_camera/image_raw /tmp/aisle.png
ros2 run pepper_greenhouse save_camera_frame.py \
  /greenhouse/bed_camera/image_raw /tmp/bed.png
```

也可以使用 `rqt_image_view` 或 RViz2 的 Image 显示。

### 5.7 性能与碰撞体

- 每个模型把同材质几何合并成一个二进制 STL，整场景约 **45 个 draw call**，
  与植株数量无关。
- 布局档约 **14.6 万三角形**；visual 档约 **30 万三角形**。
- 玻璃只用一个 merged mesh，`transparency=0.80`、`cast_shadows=false`；
  框架、风扇、植株可以投影。
- 物理沿用现有 world：1 ms 步长、1000 Hz、ODE quick 50 iters。
- 静态碰撞体约 **1070 个**：地面 1、轨道 2、沟槽 180、墙 4、屋面 40、立柱 420、
  冠层 180、风机 25、屋脊通风口 20、黄管 118、吊线 78。
- 这些碰撞体是雷达点云里可用于重定位的结构特征；冠层是每行一整条
  0.3×0.9 m 的简化带，不是逐株八面体。
- 果实、吊绳、卡片、地缝以及 visual 档的密集植株覆盖层仍为 visual-only
  （对点云贡献很小，全部做成碰撞体会严重拖慢仿真）。

> Gazebo 的 ray sensor（MID-360 插件）只和 **collision** 求交。碰撞体都是简化的
> box/cylinder 代理，与视觉 mesh 不完全一致；屋面按檐口 4.5 m / 屋脊 5.7 m 的
> 40 块斜板生成。

### 5.8 重新生成场景

修改 `config/greenhouse.yaml` 后：

```bash
python3 src/pepper_greenhouse/scripts/generate_world.py
python3 src/pepper_greenhouse/scripts/check_layout.py

colcon build --symlink-install --packages-select pepper_greenhouse
source install/setup.bash
```

生成物（world / model.sdf / model.config / STL）提交到源码树。
`generate_world.py --check` 可以不写盘地比对生成物是否与配置一致。

### 5.9 与任意底盘组合

场景 launch 只负责 Gazebo 和 world，机器人由底盘包生成。常用三种方式。

#### 方式 1：给底盘 launch 传 `world:=`（推荐）

大多数底盘 launch 都允许指定 world。以本仓库的 4WIS 底盘为例：

```bash
# 需要 pepper_greenhouse 和底盘包在同一个工作空间里
ros2 launch steer_wheel_control sim.launch.py \
  world:=$(ros2 pkg prefix pepper_greenhouse)/share/pepper_greenhouse/worlds/pepper_greenhouse.world
```

`steer_wheel_control/sim.launch.py` 会把 `world` 透传给
`steer_wheel_chassis/gazebo.launch.py`，机器人生成、控制器、运动学和里程计
都照常启动。换成其它底盘时，把包名和 launch 名替换成你的底盘入口即可；
如果它不支持 `world:=`，用方式 2。

#### 方式 2：先起场景，再单独生成机器人

```bash
# 终端 1：只启动场景
ros2 launch pepper_greenhouse pepper_greenhouse_world.launch.py gui:=false

# 终端 2：用你的底盘 launch 只做 spawn，或直接调用 spawn_entity
ros2 run gazebo_ros spawn_entity.py \
  -file /path/to/robot.urdf -entity robot -x 0 -y 0 -z 0.02
```

相机、TF、控制器、传感器都由你的底盘节点负责。

#### 方式 3：把两个资源分支放进同一个工作空间

两个资源分支互相独立。需要组合时，用 `git worktree` 或直接复制：

```bash
# 在仓库旁边再检出一个底盘分支
git worktree add ../gazebo-SSR-chassis sim/transfer-robot-chassis

# 把底盘包复制到当前大棚工作空间
cp -a ../gazebo-SSR-chassis/src/steer_wheel_chassis src/
cp -a ../gazebo-SSR-chassis/src/steer_wheel_control src/
cp -a ../gazebo-SSR-chassis/src/steer_wheel_odometry src/

colcon build --symlink-install
source install/setup.bash
```

然后按方式 1 启动。

### 5.10 手动预览场景

不编译工作空间、只看画面：

```bash
source /opt/ros/humble/setup.bash

GAZEBO_MODEL_PATH=$PWD/src/pepper_greenhouse/models \
  gazebo --verbose src/pepper_greenhouse/worlds/pepper_greenhouse.world
```

> 场景内的相机插件来自 `gazebo_ros`；如果只关心画面、不关心相机话题，
> 可以忽略插件报错。完整的编译、运行、重新生成流程见分支内的
> `src/pepper_greenhouse/README.md`。

### 5.11 已知限制

- **场景本身不含机器人**：这是刻意设计。单独启动时没有里程计、控制器或雷达；
  组合后由你使用的底盘包提供。4WIS 组合时由 `steer_wheel_odometry` 发布
  `/odom` 和 `odom → base_footprint`。
- **只有两台固定巡检相机**：照片里的其它相机/机械臂不在本场景范围内；
  车头 MID-360 由底盘包提供。
- **柱网与行距不整除**：柱网 5 m、行距 1.6 m，部分立柱会落在 1.25 m 行间走道；
  中央通道、横向通道、端部掉头区已断言无柱。立柱有简化碰撞代理，但视觉网格与
  碰撞代理不完全一致。
- **轨道高度可调**：当前轨道 6 mm 高、5 cm 宽。最初用 1 cm 高时，49 kg 的
  参考底盘可以压上去，但从地面横移回来时爬不上 1 cm 台阶；降到 6 mm 后重测。
  如果现场轨道更高，把 `config/greenhouse.yaml` 的 `rails.height` 调回去，
  并给轨道加 45° 倒角碰撞，或接受“只能从轨面开始”。
- **换成其它底盘要改尺寸锚点**：`chassis.wheel_y` / `wheel_width` / `wheel_radius`
  是按 4WIS 参考底盘写的；轨距、轮轨间隙和轨道宽度都由此派生。换底盘后改这三个值，
  重新生成 world，再跑 `check_layout.py`。
- **`model://` 依赖**：`package.xml` 通过 `gazebo_model_path="${prefix}/models"`
  导出模型路径，launch 前必须 `source install/setup.bash`。手动 `gzserver world`
  时要补 `GAZEBO_MODEL_PATH`。
- **雷达性能**：场景本身不含雷达；如果底盘带 MID-360，默认 `mid360_samples=10000`
  时大棚 RTF 约 0.38，40000 时只有 0.065。需要更流畅可以把 samples 降到 5000，
  或把 `<update_rate>` 从 10 Hz 降到 5 Hz。

## 6. 资源详解：转运机器人底盘

分支：`sim/transfer-robot-chassis`
功能包：`steer_wheel_chassis`、`steer_wheel_control`、`steer_wheel_odometry`

### 6.1 设计背景

真车底盘的**单片机自己解析 `vx / vy / wz`**，ROS 侧只发 `/cmd_vel`。所以
`steer_wheel_control` 里的运动学节点不是真车控制逻辑，而是**仿真里单片机的替身**：
让 Gazebo 模型和真车对上层暴露同一个 `/cmd_vel` 接口。

```text
                                  ┌─ 真车：串口/CAN 驱动节点 → 单片机
/cmd_vel (vx, vy, wz) ────────────┤
                                  └─ 仿真：steer_wheel_kinematics → 8 个关节命令
```

底盘分支本身不含大棚场景。要在大棚里跑，把大棚 world 传给 `sim.launch.py` 的
`world:=` 参数即可，组合方法见 [5.9](#59-与任意底盘组合)。

### 6.2 功能包职责

| 包 | 构建类型 | 职责 |
| --- | --- | --- |
| `steer_wheel_chassis` | `ament_cmake` | 4WIS 模型（xacro）、惯性/碰撞/摩擦参数、Gazebo world、ros2_control 配置、车头 Livox MID-360、`display.launch.py` / `gazebo.launch.py` |
| `steer_wheel_control` | `ament_python` | `steer_wheel_kinematics` 节点：`/cmd_vel` → 4 个转向角 + 4 个轮速；`sim.launch.py` 组合启动整个仿真 |
| `steer_wheel_odometry` | `ament_python` | 轮式里程计：由 `/joint_states` 的转向角 + 轮速最小二乘解算车体速度，发布 `/odom` 与 `odom → base_footprint` TF |

### 6.3 模型与物理参数

| Link | 质量 | 网格体积 | 说明 |
| --- | ---: | ---: | --- |
| `base_link` | 25.0 kg | 9.149e-3 m³ | 车体 0.86×0.86×0.346 m，质心 z=0.149 m |
| `Link_1~4` | 2.0 kg ×4 | 7.3e-4 m³ | 转向节（含减速器），质心 z≈−0.07 m |
| `Link_5~8` | 4.0 kg ×4 | 2.11e-3 m³ | 车轮（含轮毂电机），半径 0.0935 m |
| **合计** | **49.0 kg** | | |

质量与惯性张量不是拍脑袋填的：把每个 STL 当闭合三角网格做四面体积分，得到网格体积、
质心和**单位质量惯性张量**，再乘以选定质量。xacro 里写的就是单位质量张量，
所以改 `base_mass / leg_mass / wheel_mass` 时惯性会自动等比缩放。

关键几何：

- 四轮中心实测位置均为 `z = −0.1594 m`、`y = ±0.335 m`（`base_link` 系）。
- 轮半径 0.0935 m，轮胎着地时 `base_link` 离地 0.2529 m。
- 根 link 是 `base_footprint`（`base_link` 的地面投影，fixed joint 抬高 0.2529 m）。
- launch 默认 `-z 0.02`，机器人自由落体 2 cm 后停住。

碰撞体默认用**简化几何**代替原始网格：

| 部位 | 碰撞体 |
| --- | --- |
| 车体 | `box 0.86×0.86×0.346`（包围盒包络） |
| 转向节 | `box 0.24×0.125×0.189`（逐 link 实测包围盒） |
| 车轮 | `cylinder r=0.0935, l=0.0449`（滚动半径与胎面宽，轴向 = local z） |

需要精确碰撞时：

```bash
ros2 launch steer_wheel_chassis gazebo.launch.py use_mesh_collision:=true
```

> `base_link.stl` 有 15 MB / 31.8 万个三角形，直接拿来做碰撞体会让 Gazebo 物理
> 计算慢到不可用。

摩擦与接触参数：

| 部位 | mu1/mu2 | kp | kd | 说明 |
| --- | ---: | ---: | ---: | --- |
| 车轮 | 1.0 | 1e6 | 10 | 橡胶对地板的真实量级；4WIS 原地转向需要车轮能侧向擦地滑移 |
| 转向节 | 0.1 | 1e6 | 100 | 不该抓地 |
| 车体 | 0.2 | 1e6 | 100 | 避免底盘被地面蹭住 |

> TurtleBot3 风格的 `mu=10000`（近似无限摩擦）在 4WIS 上会让转向关节原地拧死并抖动，
> 不要直接照搬。需要各向异性摩擦时，车轮滚动方向在各自 link 系下都是 `local -y`，
> 可打开 `<fdir1>0 -1 0</fdir1>`。

### 6.4 关节、控制器与话题

8 个关节全部走 `ros2_control`：

| 控制器 | 类型 | 关节（命令数组顺序） | 话题 |
| --- | --- | --- | --- |
| `joint_state_broadcaster` | `JointStateBroadcaster` | 全部 8 个 | `/joint_states` |
| `steering_position_controller` | `JointGroupPositionController` | `left_front, right_front, left_behind, right_behind` | `/steering_position_controller/commands` |
| `wheel_velocity_controller` | `JointGroupVelocityController` | `Joint_5, Joint_6, Joint_7, Joint_8`（左前、右前、左后、右后） | `/wheel_velocity_controller/commands` |

消息类型均为 `std_msgs/msg/Float64MultiArray`。

> 话题名是 **`/commands` 复数**（Humble 的 `JointGroup*Controller` 用复数，
> 很多网上教程写单数 `/command` 是错的，发出去没有任何反应也不会报错）。
> 命令订阅的 QoS 是 `BEST_EFFORT`，`ros2 topic pub`（reliable）兼容。

低层关节命令示例：

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

主要话题：

| 方向 | 话题 | 类型 | 说明 |
| --- | --- | --- | --- |
| 订阅 | `/cmd_vel` | `geometry_msgs/msg/Twist` | `vx, vy, wz` |
| 发布 | `/odom` | `nav_msgs/msg/Odometry` | 约 120 Hz |
| 发布 | `odom → base_footprint` | TF | REP-105 |
| 发布 | `/joint_states` | `sensor_msgs/msg/JointState` | 全部 8 个关节 |
| 发布 | `/mid360` | `livox_ros_driver2/msg/CustomMsg` | Livox 原始格式 |
| 发布 | `/mid360/pointcloud` | `sensor_msgs/msg/PointCloud2` | 约 10 Hz，frame_id=`mid360` |

### 6.5 运动学解算

对每个车轮 i（轮心在 `base_link` 系下为 `(x_i, y_i)`）：

```text
v_ix = vx - wz * y_i            轮心需要的速度矢量
v_iy = vy + wz * x_i
delta_i = atan2(v_iy, v_ix)     转向角
s_i     = hypot(v_ix, v_iy)     滚动线速度
若 |delta_i| > 90°：delta_i ±= 180°，s_i 取反   车轮对称，缩到 ±90° 内少走行程
omega_i = s_i / r * direction_i 轮关节速度
```

一套公式覆盖三种工况，不用切模式：

| 输入 | 行为 |
| --- | --- |
| 只有 `vx` / `vy` | 四轮同角度 → 直行 / 任意方向斜行 (crab) |
| 只有 `wz` | 前轮 +48°、后轮 −42° 级 → 原地自转 |
| `vx` + `wz` | 一般曲线运动，四轮角度、轮速各自独立 |

### 6.6 轮速方向符号（关键坑）

车轮速度符号取决于每个轮关节轴在车体坐标系里的朝向，不是简单的“左 / 右”：

| 关节 | 轮轴方向（base_link） | `direction_i` |
| --- | --- | --- |
| `Joint_5`（左前） | −y | **−1** |
| `Joint_6`（右前） | +y | **+1** |
| `Joint_7`（左后） | −y | **−1** |
| `Joint_8`（右后） | −y | **−1** |

`Joint_8` 的 rpy 是 `(0, −π/2, +π/2)`，与左轮相同（不是右前轮那种
`(0, +π/2, +π/2)`），所以右后轮的符号与左轮一致。

> 写错成 +1 的话：右后轮被反向驱动、被地面拖着走，直线行驶时车**持续右偏**
> （实测 yaw 漂移 −0.001 rad/s，右后轮轮速低约 0.9 rad/s，车身只能达到指令速度的 86%），
> 原地自转也会边转边平移。修正后 yaw 漂移为 0.00000 rad/s。

转向角符号：四个转向关节同时给 `+δ` 时，机器人沿 `+x` 逆时针偏转 δ 的方向平移
（实测 δ=0.3 rad、驱动 5 s，位移 2.57 m，方向 17.2°，误差 <0.1°）。

### 6.7 轮式里程计

`steer_wheel_odometry` 用 `/joint_states` 里的 4 个转向角 + 4 个轮速做正运动学解算：

```text
s_i  = omega_i · r · direction_i        轮子沿自身朝向的滚动线速度
v_ix = s_i · cos(delta_i)               轮心速度（车体坐标系）
v_iy = s_i · sin(delta_i)

v_ix = vx − wz · y_i
v_iy = vy + wz · x_i
```

4 个车轮给出 8 个方程解 3 个未知量 `(vx, vy, wz)`，用最小二乘。矩阵 `A` 只与固定的
轮心位置有关，所以伪逆在启动时算一次。随后按平面刚体运动精确积分（常量 twist 假设，
`wz≠0` 时走圆弧）：

```text
Δθ = wz·dt
Δx = (vx·[sin(θ+Δθ)−sinθ] + vy·[cos(θ+Δθ)−cosθ]) / wz
Δy = (−vx·[cos(θ+Δθ)−cosθ] + vy·[sin(θ+Δθ)−sinθ]) / wz
```

主要参数：

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `wheel_radius` | 0.0935 | 车轮半径 [m] |
| `wheel_x` | `[0.37733, 0.33267, -0.33267, -0.37733]` | 轮心 x（LF, RF, LR, RR）[m] |
| `wheel_y` | `[0.33470, -0.33470, 0.33470, -0.33470]` | 轮心 y [m] |
| `wheel_direction` | `[-1, 1, -1, -1]` | 轮速符号 |
| `odom_frame` / `base_frame` | `odom` / `base_footprint` | 坐标系名 |
| `initial_x/y/yaw` | 0 | 初始位姿（`sim.launch.py` 会传生成位置） |
| `max_dt` | 0.5 | `/joint_states` 间隔超过此值不积分 [s] |
| `publish_tf` | true | 是否发布 `odom → base_footprint` |

### 6.8 Livox MID-360

使用系统已安装的 `ros2_livox_simulation`（Gazebo ray 传感器 + `libros2_livox.so` +
`scan_mode/mid360.csv`），传感器定义在 `urdf/steer_wheel_chassis.mid360.xacro`。

安装位姿（`base_link` 系）：`x=0.46, y=0, z=0.28`，**向下俯 13°**
（`pitch=+0.226893`，ROS 中绕 +y 正转会把传感器 +x 轴压向 −z）。传感器 +x 为出光前向，
+y 左，+z 上；MID-360 的垂直视场 −7.22°~+55.22° 是相对 +x 的，13° 下俯后相对车体
水平面约为 −20.2°~+42.2°。

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `use_mid360` | `true` | 是否安装传感器；`use_mid360:=false` 可关闭 |
| `mid360_x` / `mid360_y` / `mid360_z` | 0.46 / 0 / 0.28 | 安装位置 [m] |
| `mid360_pitch` | 0.226893 | 俯仰角 [rad]，正值下俯 |
| `mid360_samples` | 10000 | 每帧射线数 |

实测（与地面拟合）：下俯 **12.72°**（期望 13°，误差 0.28°），平面残差 RMS 2.3 mm。

性能：插件按 `<samples>` 逐条 `AddRay`，每帧射线数 = samples。默认 10000 时，
空世界 RTF ≈ 0.9~1.0；甜椒大棚 RTF ≈ **0.38**，每帧约 20000 点
（`accumulate_scans=2`），墙钟约 4 Hz。40000 时大棚 RTF 只有 0.065。

注意事项：

- 传感器必须带 `<always_on>true</always_on>`，否则 Gazebo 不更新传感器、插件回调不触发。
- 模型里没有 `sensor_msgs/LaserScan` 的 `/scan`；Nav2 要么用点云层
  （`voxel_layer` / `obstacle_layer` 的 pointcloud 输入），要么另加
  `pointcloud_to_laserscan`。

### 6.9 启动参数

`ros2 launch steer_wheel_control sim.launch.py -s` 可查看全部参数：

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `gui` | `true` | 启动 gzclient 图形界面 |
| `rviz` | `false` | 额外启动 RViz2 |
| `world` | `steer_wheel_chassis.world` | Gazebo world 文件；可指向大棚 world（见 5.9） |
| `x` / `y` / `yaw` | 0 | 生成位置与姿态 |
| `use_mesh_collision` | `false` | 用原始 STL 网格作为碰撞体（很慢） |
| `use_mid360` | `true` | 车头 Livox MID-360 |
| `odometry` | `true` | 启动轮式里程计 |
| `max_linear_velocity` | 1.5 | `/cmd_vel` 线速度上限 [m/s] |
| `max_angular_velocity` | 2.0 | `/cmd_vel` 角速度上限 [rad/s] |
| `cmd_vel_timeout` | 0.5 | 多久没收到 `/cmd_vel` 就轮速归零 [s] |

### 6.10 仿真实测

| 工况 | 指令 | 实测 | 偏差 |
| --- | --- | --- | --- |
| 直线 4 s | vx=0.3 m/s | 车身 0.292 m/s，yaw 漂移 −0.00000 rad/s | −2.5%（轮胎打滑） |
| 直线各速度段 | vx=±0.05~0.5 m/s | 四轮轮速与理论值差 <0.02 rad/s | — |
| 横移 4 s | vy=0.3 m/s | 方向 +89.99°，Δyaw +0.0003 rad | — |
| 原地自转 | wz=0.5 rad/s | 约 0.50~0.52 rad/s，位置基本不动 | — |
| 自转四轮转向角 | ±48.4° / ±44.8° | −0.845 / +0.782 rad | 一位不差 |
| odom 前进 3 s | vx=0.3 m/s | dx=+0.897 m，Gazebo 真值 +0.897 m | <0.1% |
| odom 横移 3 s | vy=0.3 m/s | dy=+0.897 m，Gazebo 真值 +0.897 m | <0.1% |
| odom 自转 3 s | wz=0.5 rad/s | dyaw=+1.534 rad，真值 +1.564 rad | −1.9% |

仿真特性：

- **轮胎打滑**：直线行驶时车身约比指令慢 2~3%。打滑量取决于
  `steer_wheel_chassis.gazebo.xacro` 里的 `mu1/mu2`。
- **自转时轮速会略低**：原地自转各轮切向滚动，实测轮速比指令低约 10%，
  但车身角速度仍与指令吻合。
- **里程计由轮速积分**得到，打滑会累积误差；真车里程计由底盘单片机提供。

### 6.11 已知限制

- **左右轮 x 偏移是镜像的**：左前轮中心 x=+0.3773、右前轮 x=+0.3327（后轮同理反号），
  即左右转向节的轮子在转向轴前/后的偏移方向相反。这来自原始 CAD 导出的 link 系定义，
  本次未改动；如果设计上是四个轮子都往同一侧偏，需要修正 `Joint_5~8` 的 origin。
- **这个包只到 8 个关节命令为止**。要用 `/cmd_vel`（vx/vy/wz）控制，走
  `steer_wheel_control` 的运动学节点。
- **模型本身没有 `odom` 帧**；仿真里由 `steer_wheel_odometry` 发布。
- **`gazebo_ros2_control` 警告**：`Desired controller update period (0.01 s) is slower
  than the gazebo simulation period (0.001 s)`。控制器 100 Hz、物理 1000 Hz，
  属正常提示，不是错误。
- **headless 下的 shader 警告**：无界面跑 gzserver 时会报
  `Unable to find shader lib`，没有 GL 上下文，不影响物理与控制。
- **Gazebo GUI 崩溃**：launch 会在包含 `gazebo_ros` 的 launch 之前，把
  `/usr/share/gazebo-11` 追加到 `GAZEBO_RESOURCE_PATH`。原因是 `gazebo_ros` 的
  `GazeboRosPaths` 把该变量覆盖成各 ROS 包导出的目录，而 Gazebo 会对每个目录
  再拼接 `/media` 查找材质/着色器；这些目录下都没有 `media/`，导致 gzclient
  初始化 OGRE 相机时触发断言崩溃。注意要加的是 **`/usr/share/gazebo-11`**
  （其下有 `media/`），不是 `/usr/share/gazebo-11/media`。

### 6.12 上真车要改什么

1. 不要跑 `steer_wheel_kinematics`（单片机自己解算）。
2. 在 `steer_wheel_control` 里加一个串口/CAN 驱动节点，订阅 `/cmd_vel` 后把
   `vx, vy, wz` 按单片机协议打包发出去；同时把单片机上来的里程计/状态转成 ROS 消息。
3. 仿真里的 `odom → base_footprint` 由 `steer_wheel_odometry` 提供；真车上改成由
   单片机的里程计驱动同样的 `odom → base_footprint`（`base_footprint` 在地面，
   比 `base_link` 低 0.2529 m）。
4. `steer_wheel_odometry` 不要在真车上运行。

## 7. 目录结构

`main` 分支：

```text
gazebo-SSR/
├── README.md
├── docs/
│   ├── plan.md              # 资源收集计划
│   ├── branches.md          # 分支模型与维护方法
│   └── images/              # 仓库预览图
├── .github/                 # Issue / PR 模板、协作指南、main 保护规则
├── .githooks/               # 可选的本地防误操作提醒
└── setup-scripts/           # 一键启用本地 Git 设置
```

资源分支在 `main` 的基础上增加：

```text
gazebo-SSR/
└── src/
    ├── pepper_greenhouse/       # 仅 sim/sweet-pepper-greenhouse
    ├── steer_wheel_chassis/     # 仅 sim/transfer-robot-chassis
    ├── steer_wheel_control/     # 仅 sim/transfer-robot-chassis
    └── steer_wheel_odometry/    # 仅 sim/transfer-robot-chassis
```

`build/`、`install/`、`log/`、`__pycache__/` 等生成物已在 `.gitignore` 中排除，不入库。

## 8. 开发与维护

协作流程沿用模板约定：

```text
Issue → Branch → Commit → Push → Pull Request → 项目负责人 Merge
```

- 不要直接在 `main` 开发或 Push。
- 新增资源时，从 `main` 创建 `sim/<resource>` 长期分支，在 `src/` 下加入功能包。
- 修改 `main` 文档后，把 `main` 合并进各资源分支，保持说明同步。
- 资源分支彼此独立，不要在资源分支之间合并整个历史；需要组合时按
  [5.9](#59-与任意底盘组合) 的方式放进同一个工作空间。
- 完整流程见 [`.github/CONTRIBUTING.md`](.github/CONTRIBUTING.md) 和
  [`docs/branches.md`](docs/branches.md)。

可选：启用本地 Git 防误操作提醒（不会自动启用）：

```bash
bash setup-scripts/setup-git.sh
```

如果仓库为 public，建议导入
[`.github/rulesets/main-protection.json`](.github/rulesets/main-protection.json)
保护 `main` 分支。

## 9. 常见问题

### `gzclient` 启动后崩溃或无响应

`steer_wheel_chassis` 的 launch 已经在启动 Gazebo 前把 `/usr/share/gazebo-11`
追加到 `GAZEBO_RESOURCE_PATH`，用于规避 `gazebo_ros` 覆盖该变量导致的 OGRE 断言崩溃。
手动启动 `gazebo` 时也需要补上：

```bash
export GAZEBO_RESOURCE_PATH=/usr/share/gazebo-11:$GAZEBO_RESOURCE_PATH
```

### 发命令没反应

- 控制器命令话题是 `/commands` 复数，不是 `/command`。
- 检查控制器是否已加载：`ros2 control list_controllers`。
- 检查 joint_states 是否在发布：`ros2 topic hz /joint_states`。

### 没有安装 `ros2_livox_simulation`

MID-360 插件和 `scan_mode/mid360.csv` 由该系统包提供，它不在 rosdep 索引里。
大棚场景本身不需要雷达包；底盘不需要雷达时，启动时加 `use_mid360:=false`：

```bash
ros2 launch steer_wheel_control sim.launch.py use_mid360:=false
```

### 没有 `/scan`，Nav2 怎么用

底盘只提供 MID-360 点云 `/mid360/pointcloud`。Nav2 可以使用点云输入
（`voxel_layer` / `obstacle_layer`），或者自行加 `pointcloud_to_laserscan`。

### 在大棚里用 MID-360 时仿真很慢

MID-360 插件按样本数逐条发射射线。默认 `mid360_samples=10000` 时大棚 RTF 约 0.38；
可以降到 5000，或把 `<update_rate>` 从 10 Hz 降到 5 Hz。只跑场景、不挂雷达时
不受影响。

### `model://` 模型找不到

确认已 `source install/setup.bash`。手动 `gzserver world` 时还需要补
`GAZEBO_MODEL_PATH`，或直接使用 launch 文件。

### 停止仿真时出现 `KeyboardInterrupt` traceback

`steer_wheel_kinematics` 和 `steer_wheel_odometry` 在 SIGINT 退出阶段可能在
`destroy_node()` 里打印 traceback。这是 rclpy 在退出瞬间收到中断的已知现象，
不影响仿真结果和进程清理。

## 10. 版本与发布

- 当前状态：**资源收集中**，尚无稳定版本。
- 计划在干净环境完成一次从 clone 到 launch 的完整验证后，使用
  **Git Tag + GitHub Release** 发布第一个稳定版本。
- 版本规划见 [`docs/plan.md`](docs/plan.md)。

## 11. 维护者

- 项目负责人：`@funfun-run`
