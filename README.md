# gazebo-SSR

Gazebo Classic 11 仿真资源库。资源按分支存放，`main` 只保留索引。

## 分支

| 分支 | 内容 |
| --- | --- |
| `sim/sweet-pepper-greenhouse` | 100×100 m 甜椒大棚场景包 |
| `sim/transfer-robot-chassis` | 转运机器人 4WIS 舵轮底盘 |

## 使用

```bash
git clone <仓库 URL> gazebo-SSR
cd gazebo-SSR
git switch sim/sweet-pepper-greenhouse   # 或 sim/transfer-robot-chassis
colcon build --symlink-install
source install/setup.bash
```

运行方式见切换后分支的 README。

## 环境

- Ubuntu 22.04
- ROS 2 Humble
- Gazebo Classic 11
- colcon

## 维护

协作流程见 [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md)。

- 项目负责人：`@funfun-run`
