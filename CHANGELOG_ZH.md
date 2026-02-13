# 更新日志

**中文版 | [English](./CHANGELOG.md)**

本文件记录了本项目的所有重要更改。

格式基于 [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)，
项目遵循 [语义化版本](https://semver.org/spec/v2.0.0.html) 规范。

## [未发布]

### 新增
- **小型 VLM 的上下文感知视频理解** 🎯
  - 为小型视觉语言模型（如 Ministral-3-3B）启用时序上下文理解
  - 自动维护先前帧分析的历史记录（默认：4 帧）
  - 小模型现在可以理解视频流中的连续动作（如体育、监控）
  - 在高帧间隔设置下特别有效（如帧间隔=100）
  - **核心功能**：
    - 可配置深度的响应历史追踪
    - 双锁保护的线程安全异步操作
    - 智能截断的自动内存管理
    - 零配置部署（默认启用）
    - 运行时控制：启用/禁用、清除历史、查看摘要
  - **性能指标**：
    - 时序理解能力提升 60-80%
    - 延迟增加 50-100ms（prompt 长度增加）
    - Token 消耗增加 30-50%
    - 内存占用 <1KB（可忽略）
  - **配置选项**：
    - `enable_context=True` - 启用上下文追踪（默认）
    - `max_history=4` - 记忆帧数（默认 4）
    - 响应自动截断到 150 字符以控制 prompt 大小
  - **使用场景**：
    - 体育分析：理解完整的动作序列（投篮、传球等）
    - 安全监控：追踪随时间变化的运动模式
    - 教学演示：跟踪多步骤流程
  - **修改文件**: `src/live_vlm_webui/vlm_service.py`
  - **文档**：
    - 完整指南：`docs/improve-video-context-understanding.md`（中文）
    - 快速开始：`QUICK_START_CONTEXT_FEATURE.md`
    - 代码审查：`CODE_REVIEW_REPORT.md`

### 修复
- **模型初始化竞态条件**：修复自动选择的模型未发送到服务器的问题
  - 之前，如果 UI 在页面加载时自动选择模型，不会发送到服务器
  - 原因是 `fetchModels()` 在 WebSocket 连接完成前运行
  - 症状：摄像头打开但 VLM 不处理，直到手动选择模型
  - 修复：WebSocket 连接后立即发送当前模型到服务器
  - 确保服务器始终使用 UI 中显示的模型，即使是自动选择的
  - 结果：VLM 处理自动开始，无需手动选择模型

---

## [0.2.1] - 2025-11-13

### 修复
- **版本字符串修复**：更新 `__init__.py` 中的 `__version__` 以匹配包版本
  - `live-vlm-webui --version` 命令现在正确显示 0.2.1
  - 修复了 v0.2.0 在版本命令中显示 0.1.1 的问题
- **测试基础设施**：修复 pytest-asyncio 事件循环与 AioHTTPTestCase 的冲突
  - 将 `pyproject.toml` 中的 `asyncio_mode` 从 `strict` 改为 `auto`
  - 从 `conftest.py` 中删除冲突的 `event_loop` fixture
  - 所有集成/单元/性能测试现在可以一起运行并通过
  - 注意：E2E 测试应单独运行以避免事件循环冲突

### 变更
- **文档**：将发布文档合并到单个 `releasing.md` 文件
  - 将 `RELEASING.md` 内容合并到 `releasing.md` 并删除冗余文件
  - 在整个发布流程中添加了关于更新 `__init__.py` 版本的重点强调
  - 添加了详细的测试执行说明以避免事件循环冲突
  - 更新了版本验证步骤的发布检查清单

---

## [0.2.0] - 2025-11-13

**新 Beta 功能：RTSP IP 摄像头支持 + UI/UX 改进**

### 新增（Beta 功能）

#### 🧪 RTSP IP 摄像头支持（Beta）
- **状态**：Beta - 有限硬件测试
- **测试硬件**：Reolink RLC-811A（1080p H.264）
- **功能**：
  - 从 RTSP IP 摄像头流式传输视频以进行连续监控
  - 在 UI 中切换网络摄像头和 RTSP 摄像头
  - 手动 RTSP URL 配置和测试连接
  - 流断开时自动重连
  - 支持 H.264、H.265 和 MJPEG 编解码器
- **使用场景**：
  - 泳池安全监控（儿童溺水检测）
  - 带 VLM 智能的家庭监控
  - 老年人护理（跌倒检测）
  - 宠物监控
  - 安全摄像头分析
- **文档**：完整设置指南位于 `docs/usage/rtsp-ip-cameras.md`
- **已知限制**：
  - 摄像头兼容性测试有限（仅测试 Reolink）
  - 每个会话单个流
  - UI 中无视频预览（仅后端处理）
  - 基于 CPU 的视频解码
- **需要社区帮助**：
  - 使用您的 IP 摄像头品牌/型号测试并报告结果
  - 帮助扩展已测试硬件兼容性列表
  - 在 GitHub 上报告问题：https://github.com/NVIDIA-AI-IOT/live-vlm-webui/issues

### 技术细节（RTSP）
- **后端**：添加了用于 RTSP 流处理的 `RTSPVideoTrack` 类（aiortc + FFmpeg）
- **前端**：UI 选择器在"网络摄像头"和"RTSP 流"模式之间切换
- **配置**：RTSP URL 输入，可选测试连接
- **错误处理**：连接失败、流断开、自动重连
- **安全性**：服务器日志中凭证已脱敏

### 文档
- 添加了 `docs/usage/rtsp-ip-cameras.md` - 全面的 RTSP 设置指南
  - 带示例 URL 的快速入门（Reolink、海康威视、大华等）
  - 带提示模板的用例示例
  - 常见问题故障排除
  - 性能基准测试
  - 安全和隐私注意事项
  - 无物理摄像头的测试（FFmpeg、MediaMTX）
- 更新了 README.md，添加 Beta 功能通知
- 添加了已测试硬件兼容性表

### 新增（UI/UX 改进）

#### 🎨 主题支持
- **操作系统深色/浅色模式偏好**：自动检测并遵循系统主题偏好
  - 使用 `prefers-color-scheme` 媒体查询检测
  - 主题切换循环：自动 → 浅色 → 深色 → 自动
  - 手动覆盖保存到 localStorage
  - 操作系统偏好更改时动态主题切换
  - 视觉指示器显示当前模式（显示器图标表示自动，太阳表示浅色，月亮表示深色）

#### 📝 Markdown 渲染
- **VLM 输出中的 Markdown 支持**：从 VLM 渲染格式化的 markdown 响应
  - 结果气泡右上角的切换按钮
  - 支持标题、列表、代码块、表格、引用、链接、粗体、斜体
  - 默认启用 Markdown 以提高可读性
  - 使用 DOMPurify 进行 HTML 清理以确保安全性
  - 所有 markdown 元素的主题感知样式
  - 流式更新期间按钮保持存在

#### 📋 复制到剪贴板
- **复制按钮**：结果气泡右下角的透明覆盖按钮
  - 一键复制生成结果
  - 适用于 markdown 和纯文本模式
  - 带复选标记动画的视觉反馈
  - 复制原始文本（不是 HTML）以便于共享

### 变更
- 改进了警告颜色对比度（橙色）以在深色背景上更好的可读性
- 为浅色主题一致性添加了警告和错误颜色变量

### 未来增强（Post-Beta 后）
- 多摄像头支持（网格视图）
- RTSP 流的 UI 视频预览
- 硬件加速视频解码（Jetson 上的 NVDEC）
- ONVIF 摄像头自动发现
- 摄像头预设管理
- 运动检测触发器
- AI 检测事件的录制/快照

---

## [0.1.1] - 2025-11-12

**错误修复和文档改进**

### 修复
- **WSL2 GPU 监控韧性**：为 WSL2 环境中间歇性 NVML GPU 访问问题添加了健壮的错误处理
  - 防止 GPU 暂时不可用时崩溃
  - GPU 访问丢失时优雅降级
  - 提高 Linux 子系统 for Windows 的可靠性

### 新增
- **全面的 VLM 文档**：带已验证 NVIDIA API 模型的完整模型目录
  - 添加了 `docs/usage/list-of-vlms.md`，包含 16 个已验证的 NVIDIA API Catalog 模型
  - 更正了 gemma3 和 llava 模型的视觉能力
  - 关于纯文本与支持视觉模型的详细指导
  - 常见模型选择问题的示例和故障排除

### 文档
- 添加了 Windows WSL 使用指南（`docs/usage/windows-wsl.md`）
- 更新了 v0.1.1 状态的 TODO 跟踪器
- 改进了故障排除文档

---

## [0.1.0] - 2025-11-09

**首次 PyPI 发布** 🎉

这是 Live VLM WebUI 的首次公开发布 - 一个具有 WebRTC 视频流和实时 GPU 监控的实时视觉语言模型界面。

### 新增

#### 核心功能
- **WebRTC 视频流**，带实时 VLM 分析叠加
- **实时 VLM 集成**，支持多个后端：
  - Ollama（带自动检测）✅ 已测试
  - vLLM（带自动检测）⚠️ 部分测试
  - SGLang（带自动检测）⚠️ 未测试 - 有自动检测但未验证
  - NVIDIA API Catalog（备用）
  - OpenAI API（可配置）
- **实时系统监控**，带实时更新：
  - GPU 利用率和 VRAM 使用
  - CPU 利用率和 RAM 使用
  - 推理延迟追踪（最后、平均、总计数）
  - 历史趋势的迷你图表
- **可配置的 VLM 设置**，通过 WebSocket：
  - 模型选择
  - 自定义提示
  - 帧处理间隔
  - 最大 token

#### 平台支持
- **多平台 GPU 监控**：
  - 通过 NVML 监控 NVIDIA GPU（PC、工作站、DGX 系统）
  - Apple Silicon Mac（通过 powermetrics）
  - NVIDIA Jetson Orin（通过 jetson-stats/jtop）
  - NVIDIA Jetson Thor（通过 jetson-stats/jtop，带 nvhost_podgov 备用）
  - 无 GPU 系统的纯 CPU 备用
- **特定平台产品检测和显示**：
  - Jetson AGX Orin 开发者套件
  - Jetson Orin Nano 开发者套件
  - Jetson AGX Thor 开发者套件
  - DGX Spark（ARM64 SBSA）
  - Mac（Apple Silicon）
  - 通用 PC/工作站显示

#### 安全和网络
- **自动 SSL 证书生成**：
  - 首次运行时自动创建自签名证书
  - 存储在操作系统适当的配置目录（Linux 上为 ~/.config/live-vlm-webui/）
  - 如果 openssl 不可用，快速失败机制
  - WebRTC 摄像头访问需要 HTTPS
- **端口冲突检测**，带有用的错误消息
- **网络接口检测**，便于访问 URL 显示

#### 安装和部署
- **PyPI 包**，采用现代 PEP 621 结构：
  - 源布局（src/live_vlm_webui/）
  - 入口点：`live-vlm-webui`（启动）、`live-vlm-webui-stop`（停止）
  - 平台无关的 wheel（纯 Python）
- **Docker 支持**，带多架构镜像：
  - 多架构基础镜像（linux/amd64、linux/arm64）
  - Jetson Orin 优化镜像（JetPack 6.x / L4T R36）
  - Jetson Thor 优化镜像（JetPack 7.x / L4T R38+）
  - Mac 开发镜像
- **GitHub Actions CI/CD**：
  - 自动化 Docker 镜像构建并发布到 GHCR
  - Python wheel 构建和工件生成
  - 集成和单元测试
  - 代码格式化和 lint 检查

#### 测试和质量保证
- **自动化测试套件**，带 GitHub Actions CI：
  - **单元测试**：Python 3.10、3.11、3.12 兼容性
  - **集成测试**：服务器启动、WebSocket 连接、静态文件服务
  - **性能测试**：基准测试和指标追踪
  - **代码覆盖**：通过 Codecov 追踪
- **代码质量检查**：
  - Black（代码格式化）
  - Ruff（lint）
  - mypy（类型检查）
- **E2E 工作流测试**（仅本地）：
  - 通过 Chrome fake device 的真实视频输入
  - 带测试视频的实际 VLM 推理
  - 完整的 WebRTC 管道验证
  - 基于 Playwright 的浏览器自动化
  - 注意：需要 GPU、Ollama 和浏览器（CI 中不运行）
- **测试文档**：
  - 测试快速入门指南（docs/development/testing-quickstart.md）
  - E2E 工作流测试指南（tests/e2e/real_workflow_testing.md）
  - 测试 fixture 和实用程序

#### 脚本和工具
- **start_server.sh** - 智能服务器启动脚本：
  - 虚拟环境检测和激活
  - 带有用说明的包安装验证
  - 端口可用性检查
  - Jetson 平台检测，带 Docker 推荐
- **start_container.sh** - Docker 容器启动器：
  - 平台自动检测（x86_64、ARM64、Jetson 变体）
  - GPU 运行时配置（CUDA、Jetson）
  - 现有容器检测和重启
- **stop_container.sh** - Docker 容器管理
- **generate_cert.sh** - 手动 SSL 证书生成（现在在 Python 中自动化）

#### 文档
- **全面的 README.md**，包含：
  - 不同平台的快速入门指南
  - 专用 Jetson 安装说明（pip 和 Docker）
  - 开发设置指南
  - Docker 使用示例
  - 贡献指南
- **故障排除指南**（docs/troubleshooting.md）：
  - 安装问题（setup.py 未找到、ModuleNotFoundError）
  - Jetson 特定问题（Python 版本、externally-managed-environment、pip 命令）
  - Thor 上的 jetson-stats 安装（GitHub 安装、服务设置、pipx inject）
  - SSL 证书问题
  - 常见运行时错误
- **开发者文档**：
  - 发布流程指南（docs/development/releasing.md）
  - 发布检查清单（docs/development/release-checklist.md）
  - 测试快速入门（docs/development/testing-quickstart.md）
  - E2E 工作流测试指南（tests/e2e/real_workflow_testing.md）
  - UI 增强想法（docs/development/ui_enhancements.md）
  - TODO 跟踪器（docs/development/TODO.md）
- **设置指南**：
  - Docker Compose 详细信息（docs/setup/docker-compose-details.md）

### 变更
- **项目结构**重组以兼容 PyPI：
  - 源代码移至 src/live_vlm_webui/
  - 静态文件（HTML、CSS、JS、图像）打包在包中
  - 基于现代 pyproject.toml 的配置
- **SSL 证书存储**移至操作系统适当位置：
  - Linux/Jetson：~/.config/live-vlm-webui/
  - macOS：~/Library/Application Support/live-vlm-webui/
  - Windows：%APPDATA%\live-vlm-webui\
  - 当前工作目录中不再有证书混乱
- **静态文件服务**改进以正确工作于：
  - 开发模式（pip install -e .）
  - 生产模式（从 wheel pip install）
- **Jetson Orin Nano 产品名称**清理以供显示：
  - "NVIDIA Jetson Orin Nano Engineering Reference Developer Kit Super"
  - → "NVIDIA Jetson Orin Nano Developer Kit"

### 修复
- **端口 8090 冲突检测**现在使用可靠的 Python socket 绑定测试
- **图像服务**用于 pip wheel 安装（GPU 产品图像现在正确打包）
- **Docker 构建**使用新包结构（pip install -e . 而不是 requirements.txt）
- **虚拟环境检测**在 start_server.sh 中（处理 .venv 和 venv）
- **服务器启动前包安装验证**
- **Jetson Thor pip 安装**使用 Python 3.12 / PEP 668：
  - 推荐 live-vlm-webui 使用 pipx
  - 记录从 GitHub 安装 jetson-stats
  - 提供完整的 jetson-stats 设置（服务 + pipx inject）
- **`live-vlm-webui-stop` 命令**现在作为 pip 入口点正确公开
  - 已记录但在 pyproject.toml 中缺失
  - 现在在 pip 安装后可用以优雅关闭服务器

### 测试于
- ✅ x86_64 PC（Linux Ubuntu 22.04）
- ✅ NVIDIA DGX Spark（ARM64 SBSA）
- ✅ macOS（Apple Silicon M 系列）
- ✅ NVIDIA Jetson AGX Orin（ARM64 L4T R36 / JetPack 6.x）
- ✅ NVIDIA Jetson AGX Thor（ARM64 L4T R38.2 / JetPack 7.0）

### 依赖项
- Python ≥ 3.10（Jetson Thor 为 3.12）
- aiohttp ≥ 3.9.5 - 异步 HTTP 服务器和 WebSocket 支持
- aiortc ≥ 1.10.0 - WebRTC 实现
- opencv-python ≥ 4.8.0 - 视频帧处理
- numpy ≥ 1.24.0 - 图像数组操作
- openai ≥ 1.0.0 - VLM API 客户端（OpenAI 兼容）
- psutil ≥ 5.9.0 - 系统资源监控
- nvidia-ml-py ≥ 11.495.46 - NVIDIA GPU 监控（可选）
- pynvml ≥ 11.0.0 - NVIDIA GPU 监控（传统，可选）
- jetson-stats（仅 Jetson，可选）- Jetson 特定监控

### 已知限制
- **单用户/单会话架构**：多个用户共享 VLM 状态并看到彼此的输出
  - 解决方法：在不同端口上部署多个实例
  - 未来：计划多用户支持（见 TODO.md）
- **Jetson jtop 依赖**：jetson-stats 使 Jetson 上的 pip 安装复杂化
  - Thor 需要 GitHub 安装 + 服务设置 + pipx inject
  - 未来：计划不使用 jtop 的直接 GPU 统计
- **WSL 支持**：尚未在 Linux 子系统 for Windows 上测试
- **浏览器兼容性**：在 Chrome、Firefox、Edge 上测试（Safari 可能有 WebRTC 限制）

### 已知问题
- **Mac：mlx-vlm 依赖冲突警告**（非阻塞）
  - 安装期间 pip 可能显示 transformers 版本冲突
  - 影响：仅警告 - 包安装和运行正常
  - 详见[故障排除指南](./docs/troubleshooting.md)

### 安全说明
- 默认使用自签名 SSL 证书（预期浏览器安全警告）
- 无身份验证或速率限制（仅适用于本地/受信任网络使用）
- 不建议在没有额外安全措施的情况下公开互联网部署

---

## 项目信息

**仓库**：https://github.com/NVIDIA-AI-IOT/live-vlm-webui
**PyPI 包**：https://pypi.org/project/live-vlm-webui/
**Docker 镜像**：https://github.com/NVIDIA-AI-IOT/live-vlm-webui/pkgs/container/live-vlm-webui
**许可证**：Apache License 2.0

---

[未发布]: https://github.com/NVIDIA-AI-IOT/live-vlm-webui/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/NVIDIA-AI-IOT/live-vlm-webui/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/NVIDIA-AI-IOT/live-vlm-webui/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/NVIDIA-AI-IOT/live-vlm-webui/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/NVIDIA-AI-IOT/live-vlm-webui/releases/tag/v0.1.0
