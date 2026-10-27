# 分支模型与维护

本仓库用**长期资源分支**存放仿真资源，`main` 只做索引。这样做的目的：

- 克隆 / 浏览 `main` 时不会被几十 MB 的网格和场景文件拖慢。
- 每个资源可以独立检出、独立编译、独立发布。
- 资源之间共享的包（例如 4WIS 底盘）由 Git 对象去重，不会因为出现在多个分支里而重复占用仓库体积。

## 1. 分支清单

| 分支 | 类型 | 内容 |
| --- | --- | --- |
| `main` | 默认 / 索引 | README、`docs/`、`.github/`、本地 Git 脚本 |
| `sim/sweet-pepper-greenhouse` | 长期资源 | `pepper_greenhouse` + `steer_wheel_chassis` + `steer_wheel_control` + `steer_wheel_odometry` |
| `sim/transfer-robot-chassis` | 长期资源 | `steer_wheel_chassis` + `steer_wheel_control` + `steer_wheel_odometry` |

命名约定：资源分支统一使用 `sim/<resource>`，`<resource>` 用小写 kebab-case。
功能开发 / 文档修改仍使用 `.github/CONTRIBUTING.md` 中的 `feat/`、`fix/`、`docs/` 等短期分支。

### 为什么 `sim/sweet-pepper-greenhouse` 也包含底盘包

`pepper_greenhouse_sim.launch.py` 会 include `steer_wheel_control/sim.launch.py`，
把大棚 world 交给底盘仿真启动。只放大棚包时该 launch 无法运行，所以资源分支把
它依赖的三个底盘包一起带上，保证检出即可编译、启动。

如果只需要大棚场景本身，可以：

```bash
git switch sim/sweet-pepper-greenhouse
source /opt/ros/humble/setup.bash
GAZEBO_MODEL_PATH=$PWD/src/pepper_greenhouse/models \
  gazebo --verbose src/pepper_greenhouse/worlds/pepper_greenhouse.world
```

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
git switch sim/sweet-pepper-greenhouse

# 修改 src/pepper_greenhouse/... 或底盘包
git add -A
git commit -m "feat(greenhouse): ..."
```

如果修改的是底盘包，记得同步到另一个资源分支：

```bash
git switch sim/transfer-robot-chassis
git cherry-pick <上面的 commit SHA>
```

`sim/transfer-robot-chassis` 是 `sim/sweet-pepper-greenhouse` 的子集，也可以把底盘分支合并进大棚分支，
但 cherry-pick 更不容易把无关历史带进来。

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

一个工作空间只能检出一个分支。需要同时使用多个资源时，用另一个工作树或临时复制：

```bash
# 在仓库旁边再检出一个资源分支
git worktree add ../gazebo-SSR-chassis sim/transfer-robot-chassis

# 复制需要的包到当前工作空间
cp -a ../gazebo-SSR-chassis/src/steer_wheel_chassis src/
```

使用完可以删除工作树：

```bash
git worktree remove ../gazebo-SSR-chassis
```

> `sim/sweet-pepper-greenhouse` 已经包含底盘三包，通常不需要再组合。

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
