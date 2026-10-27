# gazebo-SSR — Gazebo 仿真资源库

收集农业机器人开发中用到的 **Gazebo Classic 11** 仿真资源，包括大棚场景、舵轮底盘、
传感器配置等。仓库采用 **`main` 介绍 + 资源分支** 的组织方式：默认分支只保留索引与
使用说明，具体的模型、场景和功能包存放在独立的长期分支中。

> 当前环境基准：Ubuntu 22.04 + ROS 2 Humble + Gazebo Classic 11。

## 1. 仓库组织方式

```text
main                          # 介绍、索引、协作规范（不含模型资源）
├── sim/greenhouse            # 100×100 m 甜椒大棚场景（含所依赖的 4WIS 底盘包）
└── sim/steer-wheel-chassis   # 4WIS 舵轮（转运）机器人底盘仿真
```

- `main` 保持轻量，只负责说明仓库有什么、怎么取、怎么跑。
- 每个资源分支以 `main` 为基础，在 `src/` 下增加对应的 ROS 2 功能包。
- 资源分支是**长期分支**，不要合并回 `main`；文档更新从 `main` 合并到资源分支即可。
- 资源分支的详细维护方法见 [`docs/branches.md`](docs/branches.md)。

## 2. 资源列表

| 分支 | 资源 | 功能包 | 主要内容 |
| --- | --- | --- | --- |
| `main` | 仓库介绍与索引 | — | 环境、获取、编译、运行说明 |
| `sim/greenhouse` | 100×100 m 甜椒大棚场景 | `pepper_greenhouse` + 4WIS 底盘三包 | 布局档/视觉档、实体轨道与沟槽、420 根立柱、两台巡检相机、与底盘联仿 |
| `sim/steer-wheel-chassis` | 4WIS 舵轮底盘 | `steer_wheel_chassis`、`steer_wheel_control`、`steer_wheel_odometry` | URDF/xacro、ros2_control、`/cmd_vel` 运动学解算、轮式里程计、Livox MID-360 |

说明：

- `sim/greenhouse` 同时包含大棚场景和它依赖的三个底盘包，检出后可直接编译运行完整联仿。
- `sim/steer-wheel-chassis` 只包含底盘相关包。
- 两个分支中的底盘文件内容相同，Git 会共享对象存储，不会重复占用仓库体积。
- 阿克曼底盘 `ackermann_chassis` 暂不在收集范围内，未纳入任何分支。

## 3. 环境要求

### 软件

- OS：Ubuntu 22.04
- ROS 2：Humble（desktop 或基础版 + 所需组件）
- Gazebo：Gazebo Classic 11（`gazebo_ros`、`gazebo_ros2_control`）
- 编译：`colcon`、`colcon-common-extensions`
- Python：3.10
- 关键依赖：`xacro`、`robot_state_publisher`、`joint_state_publisher_gui`、`rviz2`、
  `python3-numpy`、`python3-yaml`、`python3-pil`
- MID-360 仿真（可选）：`ros2_livox_simulation`（不在 rosdep 索引中，需要单独安装）

### 安装依赖

切换资源分支后，在仓库根目录执行：

```bash
rosdep install --from-paths src --ignore-src -r -y \
  --skip-keys ros2_livox_simulation
```

## 4. 快速开始

### 克隆并切换分支

```bash
git clone <本仓库 URL> gazebo-SSR
cd gazebo-SSR
git switch sim/greenhouse          # 大棚场景
# 或
git switch sim/steer-wheel-chassis # 仅底盘
```

只拉取某一个资源分支：

```bash
git clone --single-branch --branch sim/greenhouse <本仓库 URL> gazebo-SSR
```

### 编译

仓库根目录就是 colcon 工作空间根目录：

```bash
cd gazebo-SSR
colcon build --symlink-install
source install/setup.bash
```

> 必须 `source install/setup.bash`，否则 Gazebo 无法解析 `model://`，launch 也找不到包。

### 运行大棚场景（`sim/greenhouse`）

```bash
# 布局档：场景轻、headless 下实时因子接近 1，适合 Nav2 / 路径验证
ros2 launch pepper_greenhouse pepper_greenhouse_sim.launch.py gui:=false

# GUI 看布局
ros2 launch pepper_greenhouse pepper_greenhouse_sim.launch.py

# 加密植株视觉档（截图用）
ros2 launch pepper_greenhouse pepper_greenhouse_sim.launch.py profile:=visual gui:=true

# 同时打开 RViz2
ros2 launch pepper_greenhouse pepper_greenhouse_sim.launch.py profile:=visual rviz:=true

# 没有安装 ros2_livox_simulation 时，关闭车头 MID-360
ros2 launch pepper_greenhouse pepper_greenhouse_sim.launch.py gui:=false use_mid360:=false
```

![大棚中央通道](docs/images/greenhouse_aisle.png)

![大棚床区](docs/images/greenhouse_bed.png)

### 运行 4WIS 底盘（`sim/steer-wheel-chassis`）

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

`/cmd_vel` 常用工况：

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
```

## 5. 资源详情

### 5.1 甜椒大棚场景（`sim/greenhouse`）

基于现场实拍图搭建的 100×100 m 室内甜椒大棚，设计取舍是**布局优先**：通道、沟槽、
行距、轨道和棚体结构按实拍比例还原；植株用连续冠层带 + 稀疏低模八面体表示，
不做逐株精细模型。

| 项目 | 数值 |
| --- | --- |
| 棚体 | 100 × 100 m，檐高 4.50 m / 脊高 5.70 m |
| 行距 / 每侧行数 | 1.60 m / 30 行 |
| 中央通道净宽 | 1.20 m |
| 轨道间距 | 0.6694 m（与 4WIS 底盘轮距一致） |
| 柱网 | 5.0 × 5.0 m，420 根 |
| 床区 | x ∈ [−46, +46]，端部掉头区 3.95 m |
| 场景规模 | 布局档约 14.6 万三角形，视觉档约 30 万；约 45 个 draw call |

关键特性：

- 两种 world：`layout`（默认，轻量）和 `visual`（加密植株，截图用）。
- 两台固定巡检相机（1 Hz / 1280×720）：
  - `/greenhouse/aisle_camera/image_raw`：中央通道
  - `/greenhouse/bed_camera/image_raw`：床区
- 物理沿用 1 ms 步长、1000 Hz、ODE quick 50 iters。
- 轨道、沟槽、立柱、屋面、风机、黄管、吊线等都有简化碰撞体，可作为雷达点云中的结构特征。
- 大棚 launch 复用 `steer_wheel_control/sim.launch.py`，因此该分支包含底盘三包。

只预览场景、不编译工作空间：

```bash
source /opt/ros/humble/setup.bash
GAZEBO_MODEL_PATH=$PWD/src/pepper_greenhouse/models \
  gazebo --verbose src/pepper_greenhouse/worlds/pepper_greenhouse.world
```

> 场景内的相机插件来自 `gazebo_ros`；如果只关心画面、不关心相机话题，可以忽略插件报错。
> 完整的编译、运行、重新生成流程见分支内的 `src/pepper_greenhouse/README.md`。

### 5.2 4WIS 舵轮底盘（`sim/steer-wheel-chassis`）

四轮独立转向（4WIS）转运机器人底盘的完整仿真，包含模型描述、Gazebo 物理配置、
`ros2_control` 控制器、`/cmd_vel` 运动学替身节点和轮式里程计。

| 项目 | 数值 |
| --- | --- |
| 车体 | 0.86 × 0.86 × 0.346 m，49 kg |
| 车轮 | 半径 0.0935 m，4 个独立转向 + 4 个独立驱动 |
| 关节 | 共 8 个：4 转向 + 4 轮速，全部走 `ros2_control` |
| 传感器 | Livox MID-360，车头 `x=0.46, z=0.28`，下俯 13° |
| 里程计 | `/joint_states` → 最小二乘正运动学 → `/odom` + `odom → base_footprint` |

话题与控制器：

| 方向 | 话题 / 控制器 | 类型 |
| --- | --- | --- |
| 订阅 | `/cmd_vel` | `geometry_msgs/msg/Twist` |
| 发布 | `/odom` | `nav_msgs/msg/Odometry` |
| 发布 | `odom → base_footprint` | TF |
| 发布 | `/joint_states` | `sensor_msgs/msg/JointState` |
| 发布 | `/mid360/pointcloud` | `sensor_msgs/msg/PointCloud2`（约 10 Hz） |
| 控制器 | `joint_state_broadcaster` | 全部 8 个关节 |
| 控制器 | `steering_position_controller` | 4 个转向角，`/commands` 复数话题 |
| 控制器 | `wheel_velocity_controller` | 4 个轮速，`/commands` 复数话题 |

特点：

- 质量与惯性张量由 STL 四面体积分得到，改质量时惯性等比缩放。
- 默认用简化几何做碰撞体；`use_mesh_collision:=true` 可启用原始网格（很慢）。
- 运动学节点用一套公式覆盖直行、横移、斜行、原地自转和曲线行驶。
- 轮速方向符号已按各轮关节轴实际朝向处理，直线行驶偏航率实测为 0。
- `sim.launch.py` 默认同时启动运动学节点和轮式里程计；可用 `odometry:=false` 关闭里程计。

> 控制器的命令话题是 **`/commands` 复数**（Humble 的 `JointGroup*Controller` 约定）。
> 更多模型参数、实测数据和调试命令见分支内的
> `src/steer_wheel_chassis/README.md`、`src/steer_wheel_control/README.md`、
> `src/steer_wheel_odometry/README.md`。

## 6. 目录结构

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
    ├── pepper_greenhouse/       # 仅 sim/greenhouse
    ├── steer_wheel_chassis/     # 两个资源分支都有
    ├── steer_wheel_control/     # 两个资源分支都有
    └── steer_wheel_odometry/    # 两个资源分支都有
```

`build/`、`install/`、`log/`、`__pycache__/` 等生成物已在 `.gitignore` 中排除，不入库。

## 7. 开发与维护

协作流程沿用模板约定：

```text
Issue → Branch → Commit → Push → Pull Request → 项目负责人 Merge
```

- 不要直接在 `main` 开发或 Push。
- 新增资源时，从 `main` 创建 `sim/<resource>` 长期分支，在 `src/` 下加入功能包。
- 修改 `main` 文档后，把 `main` 合并进各资源分支，保持说明同步。
- 完整流程见 [`.github/CONTRIBUTING.md`](.github/CONTRIBUTING.md) 和
  [`docs/branches.md`](docs/branches.md)。

可选：启用本地 Git 防误操作提醒（不会自动启用）：

```bash
bash setup-scripts/setup-git.sh
```

如果仓库为 public，建议导入
[`.github/rulesets/main-protection.json`](.github/rulesets/main-protection.json)
保护 `main` 分支。

## 8. 常见问题

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
不需要雷达时，启动时加 `use_mid360:=false`：

```bash
ros2 launch steer_wheel_control sim.launch.py use_mid360:=false
ros2 launch pepper_greenhouse pepper_greenhouse_sim.launch.py use_mid360:=false
```

### 没有 `/scan`，Nav2 怎么用

底盘只提供 MID-360 点云 `/mid360/pointcloud`。Nav2 可以使用点云输入
（`voxel_layer` / `obstacle_layer`），或者自行加 `pointcloud_to_laserscan`。

### 大棚 + MID-360 仿真很慢

MID-360 插件按样本数逐条发射射线。默认 `mid360_samples=10000` 时大棚 RTF 约 0.38；
可以降到 5000，或把 `<update_rate>` 从 10 Hz 降到 5 Hz。

### `model://` 模型找不到

确认已 `source install/setup.bash`。手动 `gzserver world` 时还需要补
`GAZEBO_MODEL_PATH`，或直接使用 launch 文件。

## 9. 版本与发布

- 当前状态：**资源收集中**，尚无稳定版本。
- 计划在干净环境完成一次从 clone 到 launch 的完整验证后，使用
  **Git Tag + GitHub Release** 发布第一个稳定版本。
- 版本规划见 [`docs/plan.md`](docs/plan.md)。

## 10. 维护者

- 项目负责人：`@funfun-run`
