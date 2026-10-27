# gazebo-SSR

Gazebo Classic 11 仿真资源库。资源按分支存放，`main` 只保留索引。

## 分支

| 分支 | 内容 |
| --- | --- |
| `sim/sweet-pepper-greenhouse` | 100×100 m 甜椒大棚场景包 |
| `sim/transfer-robot-chassis` | 转运机器人 4WIS 舵轮底盘 |

## 新增资源

1. 从最新 `main` 创建长期分支 `sim/<resource>`，`<resource>` 使用小写 kebab-case；
   资源分支不合并回 `main`。
2. 一个分支只放一个资源；功能包放在 `src/` 下，只包含该资源自身的包。
3. 资源分支必须自包含：检出后不依赖其它资源分支的文件。
4. 每个包必须包含 `package.xml`、构建文件（`CMakeLists.txt` 或 `setup.py`）
   和 `README.md`；按需包含 launch、config、模型等运行资源。
5. 分支根 `README.md` 只写本分支内容：包组成、编译运行、接口 / 参数、限制，
   不引用其它资源分支。
6. 不提交 `build/`、`install/`、`log/`、`__pycache__/`、`*.pyc`、`.vscode/`、
   本地调试脚本和原始照片。
7. 单个文件不超过 GitHub 的 100 MiB；超过时使用 Git LFS。
8. 提交前完成 `colcon build --symlink-install` 和一次 launch 或等价运行验证。
9. 新分支创建后，在 `main` 的“分支”表中登记分支名和一句话内容。
10. 按 [`.github/CONTRIBUTING.md`](.github/CONTRIBUTING.md) 的
    Issue → Branch → PR 流程提交。

## 环境

- Ubuntu 22.04
- ROS 2 Humble
- Gazebo Classic 11
- colcon

## 维护

- 项目负责人：`@funfun-run`
