# 资源收集计划

> 本文件记录仓库的资源收集路线图。`main` 只维护介绍与索引，具体资源在资源分支中。

## 当前状态

- **当前稳定版本：** 暂无
- **当前开发版本：** `v0.1`
- **当前目标：** 完成首批 Gazebo 仿真资源的分支化存储、文档整理与干净环境验证

## 已完成

- [x] 建立 `main` 分支：仓库介绍、资源索引、环境与运行说明
- [x] 建立 `sim/greenhouse` 分支：100×100 m 甜椒大棚场景 + 所依赖的 4WIS 底盘三包
- [x] 建立 `sim/steer-wheel-chassis` 分支：4WIS 舵轮底盘模型、控制与里程计
- [x] 纳入模板的 `.github` 协作文件、Issue / PR 模板与 `main` 保护规则
- [x] 排除过程性文件：`build/`、`install/`、`log/`、`__pycache__`、原始实拍图、调试脚本

## 下一步

- [ ] 在 GitHub 创建远程仓库，推送 `main`、`sim/greenhouse`、`sim/steer-wheel-chassis`
- [ ] 导入 `.github/rulesets/main-protection.json` 保护 `main`
- [ ] 在干净环境（Ubuntu 22.04 + ROS 2 Humble + Gazebo 11）完整验证：
  clone → switch → rosdep → colcon build → launch
- [ ] 为两个资源分支补充预览图或演示 GIF
- [ ] 修正文档中与最新代码不一致的历史描述
- [ ] 首次稳定版本打 Tag + GitHub Release

## 后续版本

### v0.2

目标：提高资源可用性与可验证性

- [ ] 为 `pepper_greenhouse` 增加不依赖底盘的独立场景 launch
- [ ] 为 4WIS 底盘提供 Nav2 参数模板与点云转 LaserScan 示例
- [ ] 在 CI 或本地脚本中增加 `colcon build` / `colcon test` 检查
- [ ] 补充大棚场景与底盘的组合使用示例

### v1.0

目标：发布第一个稳定资源版本

- [ ] 资源分支内容冻结并完成验证
- [ ] README 中的安装、构建、运行流程全部实测通过
- [ ] 生成 Release Notes 与版本对应表

## Backlog / 长期方向

- [ ] 视需要增加阿克曼底盘分支 `sim/ackermann-chassis`
- [ ] 收集更多农业场景：温室、果园、大田
- [ ] 收集传感器仿真配置：2D/3D 雷达、深度相机、IMU、GNSS
- [ ] 提供资源清单生成脚本，自动更新 README 中的分支索引
- [ ] 提供 Docker 镜像，降低 Gazebo Classic 11 环境搭建成本

## 已完成版本

历史正式版本以 GitHub Releases 为准。当前尚未发布任何版本。
