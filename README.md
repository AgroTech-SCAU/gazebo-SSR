# 甜椒大棚场景

`pepper_greenhouse`：100×100 m Gazebo Classic 11 甜椒大棚场景包。
只启动 Gazebo 和 world，不生成机器人。

## 编译运行

```bash
cd <仓库根目录>
colcon build --symlink-install --packages-select pepper_greenhouse
source install/setup.bash

# 布局档
ros2 launch pepper_greenhouse pepper_greenhouse_world.launch.py gui:=false

# 视觉档
ros2 launch pepper_greenhouse pepper_greenhouse_world.launch.py profile:=visual gui:=true
```

启动参数：

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `profile` | `layout` | `layout` 或 `visual` |
| `gui` | `true` | 启动 gzclient |
| `verbose` | `false` | gzserver 详细输出 |
| `pause` | `false` | 启动后暂停 |

## 场景内容

- 100×100 m，30 行/侧，行距 1.6 m，轨距 0.6694 m，420 根立柱。
- `layout` 约 14.6 万三角形；`visual` 约 30 万三角形。
- 物理：1 ms 步长、1000 Hz、ODE quick 50 iters。
- 巡检相机：`/greenhouse/aisle_camera/image_raw`、`/greenhouse/bed_camera/image_raw`。
- 世界文件：`src/pepper_greenhouse/worlds/pepper_greenhouse.world`。
- 详细说明：`src/pepper_greenhouse/README.md`。

![中央通道](src/pepper_greenhouse/docs/aisle_camera.png)

## 限制

- 不生成机器人、控制器或里程计；机器人由你的 launch 生成。
- 只有两台固定巡检相机。
- `model://` 需要先 `source install/setup.bash`。
