# 分支模型与维护

本仓库用**长期资源分支**存放仿真资源，`main` 只做索引。这样做的目的：

- 克隆 / 浏览 `main` 时不会被几十 MB 的网格和场景文件拖慢。
- 每个资源可以独立检出、独立编译、独立发布。
- 每个资源分支只放自己的包：大棚分支只有场景包，底盘分支只有底盘包。
- 大棚场景包不依赖任何底盘，可以被其它底盘直接复用。

## 1. 分支清单

| 分支 | 类型 | 内容 |
| --- | --- | --- |
| `main` | 默认 / 索引 | README、`docs/`、`.github/`、本地 Git 脚本 |
| `sim/sweet-pepper-greenhouse` | 长期资源 | `pepper_greenhouse`（纯场景包，不依赖底盘） |
| `sim/transfer-robot-chassis` | 长期资源 | `steer_wheel_chassis` + `steer_wheel_control` + `steer_wheel_odometry` |

命名约定：资源分支统一使用 `sim/<resource>`，`<resource>` 用小写 kebab-case。
功能开发 / 文档修改仍使用 `.github/CONTRIBUTING.md` 中的 `feat/`、`fix/`、`docs/` 等短期分支。

### 大棚场景包为什么是独立的

`pepper_greenhouse` 只包含 world、模型、相机和生成脚本，不依赖任何底盘。
`pepper_greenhouse_world.launch.py` 只启动 Gazebo 和 world，不生成机器人，
因此可以直接给其它底盘复用。

单独看场景：

```bash
git switch sim/sweet-pepper-greenhouse
colcon build --symlink-install --packages-select pepper_greenhouse
source install/setup.bash
ros2 launch pepper_greenhouse pepper_greenhouse_world.launch.py gui:=false
```

与底盘组合（以 4WIS 为例，两个包需在同一个工作空间）：

```bash
ros2 launch steer_wheel_control sim.launch.py \
  world:=$(ros2 pkg prefix pepper_greenhouse)/share/pepper_greenhouse/worlds/pepper_greenhouse.world
```

其它组合方式见 README 的“5.9 与任意底盘组合”。

## 2. 使用资源分支

### 克隆后切换

```bash
git clone <仓库 URL> gazebo-SSR
cd gazebo-SSR
git switch sim/sweet-pepper-greenhouse
```

远端分支在本地不存在时，Git 通常会自动建立跟踪分支。若没有：

```bash
git switch -c sim/sweet-pepper-greenhouse origin/sim/sweet-pepper-greenhouse
```

### 只拉取一个资源分支

```bash
git clone --single-branch --branch sim/transfer-robot-chassis <仓库 URL> gazebo-SSR
```

之后如果需要其他分支：

```bash
git remote set-branches origin '*'
git fetch origin
```

### 编译

仓库根目录就是 colcon 工作空间：

```bash
cd gazebo-SSR
colcon build --symlink-install
source install/setup.bash
```

## 3. 修改资源

资源代码直接在对应的资源分支上提交：

```bash
# 大棚场景
git switch sim/sweet-pepper-greenhouse
# 修改 src/pepper_greenhouse/...
git add -A
git commit -m "feat(greenhouse): ..."

# 底盘
git switch sim/transfer-robot-chassis
# 修改 src/steer_wheel_*...
git add -A
git commit -m "feat(chassis): ..."
```

两个分支没有共享包，不需要 cherry-pick。需要同时使用时，按第 6 节把包放进同一个工作空间。

## 4. 同步文档

文档以 `main` 为准。修改 `main` 后合并到各资源分支：

```bash
git switch main
# 修改 README.md / docs/...
git add -A
git commit -m "docs: ..."

git switch sim/sweet-pepper-greenhouse
git merge main

git switch sim/transfer-robot-chassis
git merge main

git switch main
```

资源分支之间不要互相合并整个历史。

## 5. 新增资源分支

```bash
git switch main

# 从最新 main 创建长期资源分支
git switch -c sim/<resource>

mkdir -p src
cp -a /path/to/<package_a> src/
cp -a /path/to/<package_b> src/

# 清理生成物
find src -type d -name '__pycache__' -prune -exec rm -rf {} +
find src -type f -name '*.pyc' -delete

git add src
git commit -m "feat(<resource>): add ..."
```

然后在 `main` 的 README 资源列表和本文件的表格中登记该分支。

## 6. 组合多个资源

一个工作空间只能检出一个分支。需要“大棚 + 底盘”时，用另一个工作树或临时复制：

```bash
# 当前在 sim/sweet-pepper-greenhouse，把底盘分支检出到旁边
git worktree add ../gazebo-SSR-chassis sim/transfer-robot-chassis

# 复制底盘三包到当前工作空间
cp -a ../gazebo-SSR-chassis/src/steer_wheel_chassis src/
cp -a ../gazebo-SSR-chassis/src/steer_wheel_control src/
cp -a ../gazebo-SSR-chassis/src/steer_wheel_odometry src/

colcon build --symlink-install
source install/setup.bash
```

启动组合仿真：

```bash
ros2 launch steer_wheel_control sim.launch.py \
  world:=$(ros2 pkg prefix pepper_greenhouse)/share/pepper_greenhouse/worlds/pepper_greenhouse.world
```

使用完可以删除工作树和临时复制的包：

```bash
git worktree remove ../gazebo-SSR-chassis
rm -rf src/steer_wheel_chassis src/steer_wheel_control src/steer_wheel_odometry
```

如果当前在底盘分支，反过来 worktree 大棚分支、把 `pepper_greenhouse` 复制进来即可。

## 7. 删除或归档资源

```bash
# 删除本地分支
git branch -d sim/<resource>

# 删除远端分支（确认不再需要后）
git push origin --delete sim/<resource>
```

删除前先在 `main` 的 README 和本文件中移除对应条目。

## 8. 不纳入仓库的内容

- `build/`、`install/`、`log/`：colcon 生成物
- `__pycache__/`、`*.pyc`、`.pytest_cache/`：Python 生成物
- 根目录 `photos/`：原始实拍图，按需保留在本地
- 根目录 `scripts/`：开发期调试脚本，不属于某个功能包
- `src/ackermann_chassis/`：阿克曼底盘暂不在收集范围内

这些规则已经写入 `.gitignore`。
