# pepper_greenhouse

100×100 m 甜椒大棚 Gazebo Classic 11 场景包。提供 world、模型、巡检相机和生成脚本；
不生成机器人。

## 目录

```text
src/pepper_greenhouse/
├── config/greenhouse.yaml
├── launch/pepper_greenhouse_world.launch.py
├── models/
│   ├── pepper_greenhouse_shell/
│   ├── pepper_beds_mid/
│   ├── pepper_beds_end/
│   └── pepper_plants_dense/
├── worlds/
│   ├── pepper_greenhouse.world
│   └── pepper_greenhouse_visual.world
├── scripts/
│   ├── layout.py
│   ├── generate_world.py
│   ├── check_layout.py
│   └── save_camera_frame.py
└── test/test_generated_assets.py
```

## 编译运行

```bash
cd <仓库根目录>
colcon build --symlink-install --packages-select pepper_greenhouse
source install/setup.bash

ros2 launch pepper_greenhouse pepper_greenhouse_world.launch.py gui:=false
ros2 launch pepper_greenhouse pepper_greenhouse_world.launch.py profile:=visual gui:=true
```

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `profile` | `layout` | `layout` 或 `visual` |
| `gui` | `true` | 启动 gzclient |
| `verbose` | `false` | gzserver 详细输出 |
| `pause` | `false` | 启动后暂停 |

## 尺寸

| 项目 | 数值 |
| --- | ---: |
| 场地 | 100 × 100 m |
| 檐高 / 脊高 | 4.50 / 5.70 m |
| 轨道中心 | y = ±0.33470 m（轨距 0.6694 m） |
| 轨道截面 | 0.050 × 0.006 m |
| 中央通道净宽 | 1.20 m |
| 沟槽 | 0.35 m 宽，底 0.15 / 顶 0.35 m |
| 行距 / 每侧行数 | 1.60 m / 30 |
| 侧通道 | 2.60 m |
| 床区 | x ∈ [−46, +46]，92 m |
| 横向通道 | 2.0 m，中心 x = ±22.5 m |
| 柱网 | 5.0 × 5.0 m，420 根 |
| 冠层 | z = 0.35~0.50 m |
| 吊蔓钢丝 / 黄管 | z = 3.80 / 2.50 m |

`config/greenhouse.yaml` 是尺寸来源，`scripts/layout.py` 会校验轨距、轮轨间隙、
行数和通道无柱等约束。

## 模型

| 模型 | 内容 |
| --- | --- |
| `pepper_greenhouse_shell` | 白框、玻璃、风扇、黄管、钢丝、地面 |
| `pepper_beds_mid` | 43 m 床段 |
| `pepper_beds_end` | 22.5 m 床段 |
| `pepper_plants_dense` | visual 档加密植株 |

- `layout`：稀疏植株，约 14.6 万三角形。
- `visual`：加密植株，约 30 万三角形。

## 巡检相机

两台 1 Hz / 1280×720 相机：

| 相机 | 位置 / 朝向 | 话题 |
| --- | --- | --- |
| `aisle_camera` | (30, 0, 4.5)，沿 −x | `/greenhouse/aisle_camera/image_raw` |
| `bed_camera` | (0, −18, 5.5)，沿 +y | `/greenhouse/bed_camera/image_raw` |

```bash
ros2 run pepper_greenhouse save_camera_frame.py \
  /greenhouse/aisle_camera/image_raw /tmp/aisle.png
```

## 性能

- 约 45 个 draw call，与植株数量无关。
- 静态碰撞体约 1070 个：地面 1、轨道 2、沟槽 180、墙 4、屋面 40、立柱 420、
  冠层 180、风机 25、屋脊通风口 20、黄管 118、吊线 78。
- 果实、吊绳、卡片、地缝和 visual 档的密集植株为 visual-only。
- Gazebo 的 ray sensor 只和 collision 求交，碰撞体为简化 box/cylinder 代理。

## 重新生成

```bash
python3 src/pepper_greenhouse/scripts/generate_world.py
python3 src/pepper_greenhouse/scripts/check_layout.py
colcon build --symlink-install --packages-select pepper_greenhouse
source install/setup.bash
```

`generate_world.py --check` 可只比对、不写盘。

## 限制

- 不生成机器人、控制器或里程计。
- 只有两台固定巡检相机。
- 柱网 5 m 与行距 1.6 m 不整除，部分立柱落在行间走道；中央通道、横向通道、
  端部掉头区无柱。
- 轨道高 6 mm；更高轨道需加倒角碰撞，或只能从轨面开始。
- launch 前必须 `source install/setup.bash`；手动 `gzserver` 需补
  `GAZEBO_MODEL_PATH`。
