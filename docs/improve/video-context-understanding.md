# 优化小模型的视频上下文理解

本文档介绍如何优化小型 VLM 模型（如 Ministral-3-3B）在处理视频流时的上下文理解能力，特别是针对连续动作分析场景（如体育比赛）。

## 目录

- [问题背景](#问题背景)
- [当前架构分析](#当前架构分析)
- [优化策略](#优化策略)
  - [策略 1: 提示词工程 - 累积上下文](#策略-1-提示词工程---累积上下文)
  - [策略 2: 多帧合成](#策略-2-多帧合成)
  - [策略 3: 关键帧检测 + 增量分析](#策略-3-关键帧检测--增量分析)
  - [策略 4: 轻量级运动追踪辅助](#策略-4-轻量级运动追踪辅助)
  - [策略 5: 双模型架构](#策略-5-双模型架构)
- [推荐实施方案](#推荐实施方案)
- [参数调优建议](#参数调优建议)

---

## 问题背景

### 当前挑战

使用小型 VLM 模型（如 `mistralai/Ministral-3-3B-Instruct-2512`）处理视频流时存在以下问题：

- ✅ **单帧分析效果好**：对静态图像的理解准确
- ❌ **缺乏上下文联系**：无法理解连续帧之间的关系
- ❌ **动作不连贯**：分析体育比赛等连续动作时无法衔接

**典型场景示例**：
```
帧 1: "一个人站在球场上"
帧 2: "一个人举起手臂"
帧 3: "一个人跳起来"
```

理想情况下应该理解为："球员正在进行投篮动作"，但小模型只能看到每一帧的孤立画面。

---

## 当前架构分析

### RTSP 流到 VLM 的数据流

```
RTSP 摄像头流
    ↓
[RTSPVideoTrack] - PyAV 解码 RTSP 流
    ↓ recv()
[VideoProcessorTrack] - 帧处理器
    ↓
┌─────────────────────────────────────┐
│ 1. 接收原始帧                        │
│ 2. 计算帧延迟 (PTS 时间戳)           │
│ 3. 延迟控制：丢弃过期帧（可选）       │
│ 4. 帧采样检查                        │
│    if (frame_count % process_every_n_frames == 0) │
│    {                                 │
│       - 转换为 numpy/PIL Image       │
│       - asyncio.create_task(         │
│           vlm_service.process_frame()) │
│    }                                 │
│ 5. 获取最新 VLM 响应                 │
│ 6. WebSocket 广播结果                │
│ 7. 返回原始帧（零拷贝）              │
└─────────────────────────────────────┘
    ↓
[VLMService.process_frame()] - 异步处理
    ↓
┌─────────────────────────────────────┐
│ - 检查 processing_lock               │
│ - 如果忙碌 → 跳过该帧                │
│ - 否则：                             │
│   1. 图像转 base64                   │
│   2. 发送到 VLM API                  │
│   3. 等待响应                        │
│   4. 更新 current_response           │
└─────────────────────────────────────┘
```

### 关键参数

| 参数名 | 代码位置 | 默认值 | 作用 |
|--------|---------|--------|------|
| `process_every_n_frames` | `video_processor.py:47` | 30 | 每 N 帧发送一次到 VLM |
| `max_frame_latency` | `video_processor.py:49` | 0.0 (禁用) | 丢弃超过阈值的旧帧 |
| `max_tokens` | `vlm_service.py:43` | 512 | VLM 响应最大长度 |

### 架构特点

✅ **异步非阻塞**：VLM 处理不会阻塞视频流
✅ **帧采样**：避免过载小模型
✅ **忙碌跳过**：如果 VLM 还在处理上一帧，新帧会被跳过
❌ **无状态单帧**：每次只发送一张图片，**没有历史上下文**

---

## 优化策略

### 策略 1: 提示词工程 - 累积上下文

**难度**：⭐
**效果**：⭐⭐⭐⭐⭐
**推荐度**：⭐⭐⭐⭐⭐

#### 核心思路

在 VLM prompt 中包含历史分析结果，形成"记忆"，让模型理解"之前发生了什么"。

#### 实现方案

**修改文件**：`src/live_vlm_webui/vlm_service.py`

```python
class VLMService:
    def __init__(self, ...):
        # ... 现有代码 ...

        # 添加历史记录
        self.response_history = []  # 保存最近 N 条响应
        self.max_history = 3  # 保留最近 3 次分析

    def _build_contextual_prompt(self, base_prompt: str) -> str:
        """构建包含历史上下文的 prompt"""
        if not self.response_history:
            return base_prompt

        # 构建历史上下文文本
        history_lines = []
        for i, resp in enumerate(reversed(self.response_history[-self.max_history:]), 1):
            history_lines.append(f"  {i} 帧前: {resp}")

        history_text = "\n".join(history_lines)

        # 增强的 prompt
        contextual_prompt = f"""{base_prompt}

[历史观察]
{history_text}

[当前帧分析]
请结合上述历史信息，分析当前帧的内容和动作趋势。
"""
        return contextual_prompt

    async def analyze_image(self, image: Image.Image, prompt: Optional[str] = None) -> str:
        if prompt is None:
            prompt = self.prompt

        # 构建上下文感知的 prompt
        contextual_prompt = self._build_contextual_prompt(prompt)

        try:
            # ... 现有的 API 调用代码 ...

            result = response.choices[0].message.content.strip()

            # 保存到历史
            self.response_history.append(result)
            if len(self.response_history) > 10:  # 最多保留 10 条
                self.response_history.pop(0)

            logger.info(f"VLM response: {result} (latency: {inference_time*1000:.0f}ms)")
            return result

        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return f"Error: {str(e)}"
```

#### 优点

- ✅ **实现简单**：仅需修改 10-20 行代码
- ✅ **不改变模型**：任何模型都可使用
- ✅ **效果显著**：小模型也能理解时序关系
- ✅ **参数可调**：`max_history` 可根据场景调整

#### 缺点

- ⚠️ **Token 消耗增加**：prompt 变长，每次调用成本提高
- ⚠️ **依赖模型能力**：需要模型有一定的上下文理解能力

#### 使用示例

调整后的分析效果：

```
[历史观察]
  3 帧前: 篮球运动员正在运球靠近篮筐
  2 帧前: 运动员开始起跳动作，双脚离地
  1 帧前: 运动员在空中举起篮球，准备投篮

[当前帧分析]
→ 模型输出: "运动员正在完成上篮动作，篮球即将投向篮筐"
```

---

### 策略 2: 多帧合成

**难度**：⭐⭐⭐
**效果**：⭐⭐⭐⭐⭐
**推荐度**：⭐⭐⭐⭐

#### 核心思路

将连续的 3-5 帧合成一张图发送，或直接发送多张图片，让模型直接看到动作序列。

#### 方案 A: 图像拼接

**修改文件**：`src/live_vlm_webui/video_processor.py`

```python
class VideoProcessorTrack(VideoStreamTrack):
    def __init__(self, ...):
        # ... 现有代码 ...

        # 添加帧缓冲区
        self.frame_buffer = []
        self.buffer_size = 4  # 保存 4 帧

    async def recv(self):
        # ... 获取帧的代码 ...

        if need_conversion:
            img = frame.to_ndarray(format="bgr24")
            self.last_frame = img.copy()

            # 添加到缓冲区
            self.frame_buffer.append(img.copy())
            if len(self.frame_buffer) > self.buffer_size:
                self.frame_buffer.pop(0)

            # 发送帧到 VLM
            if self.frame_count % interval == 0 and len(self.frame_buffer) >= self.buffer_size:
                # 创建多帧拼接图像
                multi_frame_img = self._create_multi_frame_image(self.frame_buffer)
                pil_img = Image.fromarray(cv2.cvtColor(multi_frame_img, cv2.COLOR_BGR2RGB))

                asyncio.create_task(self.vlm_service.process_frame(pil_img))
                logger.info(f"Frame {self.frame_count}: Sending {self.buffer_size} frames to VLM")

        # ... 返回帧的代码 ...

    def _create_multi_frame_image(self, frames: list) -> np.ndarray:
        """将多帧拼接成一张图"""
        # 方案 1: 横向拼接 (1x4 布局)
        return np.hstack(frames)

        # 方案 2: 2x2 网格布局（如果是 4 帧）
        # top_row = np.hstack([frames[0], frames[1]])
        # bottom_row = np.hstack([frames[2], frames[3]])
        # return np.vstack([top_row, bottom_row])
```

#### 方案 B: 多图片发送（推荐，如果 API 支持）

**修改文件**：`src/live_vlm_webui/vlm_service.py`

```python
async def analyze_images(self, images: list[Image.Image], prompt: Optional[str] = None) -> str:
    """分析多张图片（时序帧）"""
    if prompt is None:
        prompt = self.prompt

    try:
        start_time = time.perf_counter()

        # 转换所有图片为 base64
        image_contents = []
        for idx, image in enumerate(images):
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format="JPEG")
            img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode("utf-8")
            image_contents.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}
            })

        # 构建消息（包含多张图片）
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"{prompt}\n\n这是连续的 {len(images)} 帧视频画面，请分析其中的动作序列。"},
                    *image_contents
                ]
            }
        ]

        # 调用 API
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=0.7
        )

        # ... 处理响应和指标 ...

    except Exception as e:
        logger.error(f"Error analyzing images: {e}")
        return f"Error: {str(e)}"
```

#### 优点

- ✅ **直观有效**：模型能直接看到动作变化
- ✅ **理解能力强**：更容易捕捉运动趋势
- ✅ **适合动作分析**：特别适合体育、监控等场景

#### 缺点

- ⚠️ **API 成本高**：token 消耗大幅增加（4 倍图片）
- ⚠️ **推理时间长**：处理时间显著增加
- ⚠️ **API 兼容性**：需要确认 API 是否支持多图片

---

### 策略 3: 关键帧检测 + 增量分析

**难度**：⭐⭐⭐⭐
**效果**：⭐⭐⭐⭐
**推荐度**：⭐⭐⭐

#### 核心思路

只在场景变化明显时才发送完整分析，其他时候只做增量更新，节省 API 调用。

#### 实现方案

**修改文件**：`src/live_vlm_webui/video_processor.py`

```python
class VideoProcessorTrack(VideoStreamTrack):
    def __init__(self, ...):
        # ... 现有代码 ...

        self.prev_frame = None
        self.scene_change_threshold = 25.0  # 场景变化阈值

    def _calculate_frame_difference(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """计算两帧之间的差异程度"""
        # 转换为灰度图
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        # 计算平均像素差异
        diff = np.abs(gray1.astype(float) - gray2.astype(float)).mean()
        return diff

    async def recv(self):
        # ... 获取和转换帧 ...

        if need_conversion:
            img = frame.to_ndarray(format="bgr24")

            # 判断是否为关键帧
            is_key_frame = True
            if self.prev_frame is not None:
                frame_diff = self._calculate_frame_difference(img, self.prev_frame)
                is_key_frame = frame_diff > self.scene_change_threshold

            self.prev_frame = img.copy()

            # 根据是否为关键帧选择不同的 prompt
            if self.frame_count % interval == 0:
                pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

                if is_key_frame or self.frame_count % 300 == 0:  # 关键帧或每 10 秒强制更新
                    prompt = "详细描述这个场景中发生的事情"
                    logger.info(f"Key frame detected, sending full analysis")
                else:
                    prompt = "简要描述相比上一帧的变化，如果没有明显变化则说'场景保持不变'"
                    logger.info(f"Incremental frame, sending change detection")

                asyncio.create_task(self.vlm_service.process_frame(pil_img, prompt))

        # ... 返回帧 ...
```

#### 优点

- ✅ **节省资源**：减少不必要的 API 调用
- ✅ **聚焦变化**：关注动态内容
- ✅ **自适应**：根据场景活跃度调整

#### 缺点

- ⚠️ **实现复杂**：需要调优阈值参数
- ⚠️ **可能漏帧**：缓慢的动作可能被忽略

---

### 策略 4: 轻量级运动追踪辅助

**难度**：⭐⭐⭐⭐
**效果**：⭐⭐⭐
**推荐度**：⭐⭐⭐

#### 核心思路

使用传统 CV 方法（光流、目标跟踪）提取运动信息，注入到 prompt 中辅助理解。

#### 实现方案

```python
class VideoProcessorTrack(VideoStreamTrack):
    def __init__(self, ...):
        self.prev_gray = None
        self.motion_detector = None

    def _analyze_motion(self, curr_frame: np.ndarray, prev_gray: np.ndarray) -> dict:
        """使用光流分析运动"""
        curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)

        # 计算光流
        flow = cv2.calcOpticalFlowFarneback(
            prev_gray, curr_gray, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0
        )

        # 计算运动强度
        mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        motion_magnitude = np.mean(mag)

        # 主要运动方向
        avg_angle = np.mean(ang)
        direction = self._angle_to_direction(avg_angle)

        return {
            "magnitude": motion_magnitude,
            "direction": direction,
            "level": "high" if motion_magnitude > 2.0 else "medium" if motion_magnitude > 0.5 else "low"
        }

    def _angle_to_direction(self, angle: float) -> str:
        """将角度转换为方向描述"""
        angle_deg = np.degrees(angle)
        if angle_deg < 22.5 or angle_deg >= 337.5:
            return "向右"
        elif angle_deg < 67.5:
            return "向右下"
        elif angle_deg < 112.5:
            return "向下"
        elif angle_deg < 157.5:
            return "向左下"
        elif angle_deg < 202.5:
            return "向左"
        elif angle_deg < 247.5:
            return "向左上"
        elif angle_deg < 292.5:
            return "向上"
        else:
            return "向右上"

    async def recv(self):
        # ... 获取帧 ...

        if need_conversion:
            img = frame.to_ndarray(format="bgr24")
            curr_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # 分析运动
            motion_info = None
            if self.prev_gray is not None:
                motion_info = self._analyze_motion(img, self.prev_gray)

            self.prev_gray = curr_gray

            # 发送到 VLM 时增强 prompt
            if self.frame_count % interval == 0:
                pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

                # 构建增强 prompt
                base_prompt = self.vlm_service.prompt
                if motion_info:
                    enhanced_prompt = f"""{base_prompt}

[运动信息]
- 运动强度: {motion_info['level']}
- 主要方向: {motion_info['direction']}

请结合运动信息分析画面。
"""
                    asyncio.create_task(self.vlm_service.process_frame(pil_img, enhanced_prompt))
                else:
                    asyncio.create_task(self.vlm_service.process_frame(pil_img))

        # ... 返回帧 ...
```

#### 优点

- ✅ **无需额外模型**：使用 OpenCV 即可
- ✅ **提供运动线索**：帮助 VLM 理解动态
- ✅ **计算开销小**：光流计算快速

#### 缺点

- ⚠️ **复杂度增加**：需要维护额外的 CV 逻辑
- ⚠️ **效果间接**：仍依赖 VLM 理解 prompt

---

### 策略 5: 双模型架构

**难度**：⭐⭐⭐⭐⭐
**效果**：⭐⭐⭐⭐⭐
**推荐度**：⭐⭐⭐

#### 核心思路

- **快速通道**：小模型实时分析每帧
- **慢速通道**：大模型定期总结上下文

#### 实现方案

**修改文件**：`src/live_vlm_webui/video_processor.py`

```python
class VideoProcessorTrack(VideoStreamTrack):
    def __init__(self, track, vlm_service, text_callback=None):
        super().__init__()
        self.track = track

        # 双模型配置
        self.fast_vlm = vlm_service  # 原有的小模型

        # 可选：初始化大模型（通过配置启用）
        self.slow_vlm = None
        self.use_dual_model = False  # 通过配置启用

        if self.use_dual_model:
            from .vlm_service import VLMService
            self.slow_vlm = VLMService(
                model="larger-model-name",  # 配置更大的模型
                api_base=vlm_service.api_base,
                api_key=vlm_service.api_key,
                prompt="总结过去 10 秒的视频内容，描述主要的动作和事件"
            )

        self.context_summary = ""  # 慢速模型的上下文总结
        self.frame_buffer_for_summary = []

    async def recv(self):
        # ... 获取帧 ...

        if need_conversion:
            img = frame.to_ndarray(format="bgr24")
            self.last_frame = img.copy()

            # 快速通道：每帧都分析（按 interval）
            if self.frame_count % interval == 0:
                pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

                # 构建包含上下文的 prompt
                fast_prompt = self.fast_vlm.prompt
                if self.context_summary:
                    fast_prompt = f"{fast_prompt}\n\n[最近10秒总结]\n{self.context_summary}"

                asyncio.create_task(self.fast_vlm.process_frame(pil_img, fast_prompt))
                logger.info(f"Fast VLM: Analyzing frame {self.frame_count}")

            # 慢速通道：每 10 秒总结一次
            if self.use_dual_model and self.slow_vlm:
                self.frame_buffer_for_summary.append(img.copy())

                if self.frame_count % 300 == 0 and len(self.frame_buffer_for_summary) > 0:
                    # 从缓冲区选择关键帧（每隔几帧选一个）
                    key_frames = self.frame_buffer_for_summary[::30]  # 每秒 1 帧

                    # 创建拼接图像或多图片
                    asyncio.create_task(self._update_context_summary(key_frames))

                    # 清空缓冲区
                    self.frame_buffer_for_summary = []

        # ... 返回帧 ...

    async def _update_context_summary(self, frames: list):
        """使用大模型更新上下文总结"""
        try:
            # 拼接关键帧
            if len(frames) > 4:
                frames = frames[:4]  # 最多 4 帧

            multi_frame = np.hstack(frames)
            pil_img = Image.fromarray(cv2.cvtColor(multi_frame, cv2.COLOR_BGR2RGB))

            # 调用大模型
            summary = await self.slow_vlm.analyze_image(pil_img)
            self.context_summary = summary

            logger.info(f"Slow VLM: Context updated - {summary[:100]}...")

        except Exception as e:
            logger.error(f"Error updating context summary: {e}")
```

#### 优点

- ✅ **最佳效果**：结合实时性和准确性
- ✅ **自适应**：小模型快速响应，大模型深度理解
- ✅ **灵活配置**：可根据资源调整

#### 缺点

- ⚠️ **实现复杂**：需要管理两个模型
- ⚠️ **成本较高**：同时运行两个模型
- ⚠️ **需要协调**：两个模型的结果需要合理整合

---

## 推荐实施方案

根据不同的需求和资源情况，推荐以下方案：

### 方案 A: 零代码优化（立即可用）

**适用场景**：快速测试，无法修改代码

**步骤**：

1. **优化 Prompt**（在 Web UI 中输入）：
   ```
   你正在分析体育比赛的视频流。这是连续视频的一帧，请：

   1. 描述当前画面的核心内容（人物、动作、位置）
   2. 推断正在进行的动作（基于姿态和运动趋势）
   3. 预测接下来可能发生什么

   请用 2-3 句话简洁描述，重点关注动态变化。
   ```

2. **调整参数**：
   - **Frame Processing Interval**: 降低到 15-20
   - **Max Tokens**: 提高到 150-200

**预期效果**：轻微改善，模型会尝试推断动作趋势

---

### 方案 B: 基础代码优化（推荐）⭐⭐⭐⭐⭐

**适用场景**：愿意修改代码，追求性价比

**实施策略 1**（添加响应历史）

**预期效果**：显著改善，模型能理解前后关系

**实施难度**：⭐（约 30 分钟）

**预期改善**：60-80%

---

### 方案 C: 进阶优化（最佳效果）

**适用场景**：有充足 API 预算，追求最佳效果

**实施策略 1 + 策略 2（多帧合成）**

**预期效果**：极大改善，接近人类理解水平

**实施难度**：⭐⭐⭐（约 2-3 小时）

**预期改善**：80-95%

---

### 方案 D: 长期优化（生产级）

**适用场景**：构建生产系统，需要平衡成本和效果

**实施策略 3（关键帧检测）+ 策略 4（运动辅助）+ 策略 5（双模型）**

**预期效果**：最优的成本效益比

**实施难度**：⭐⭐⭐⭐⭐（约 1-2 周）

**预期改善**：90-98%

---

## 参数调优建议

### 针对不同场景的推荐配置

#### 场景 1: 体育比赛（高速动作）

```yaml
Frame Processing Interval: 10-15  # 更频繁采样
Max Tokens: 100-150
Response History: 5  # 保留 5 帧历史
Scene Change Threshold: 30.0  # 较高阈值，避免频繁关键帧
```

**Prompt 模板**：
```
分析这个体育比赛画面，描述运动员的动作和位置变化。
重点关注：正在执行的技术动作、运动方向、比赛态势。
```

---

#### 场景 2: 安防监控（慢速变化）

```yaml
Frame Processing Interval: 60-90  # 较少采样
Max Tokens: 50-100
Response History: 3
Scene Change Threshold: 15.0  # 低阈值，捕捉细微变化
```

**Prompt 模板**：
```
监控画面分析：描述画面中的人员活动和异常情况。
重点关注：新出现的人员、异常行为、物体移动。
```

---

#### 场景 3: 教学演示（中速，重细节）

```yaml
Frame Processing Interval: 20-30
Max Tokens: 200-300
Response History: 4
```

**Prompt 模板**：
```
分析教学演示画面，详细描述正在进行的操作步骤。
重点关注：手部动作、工具使用、操作顺序、关键细节。
```

---

## 效果评估方法

### 定性评估

准备测试视频片段（如 30 秒的篮球投篮），记录：

1. **连贯性**：输出是否能理解动作的前后关系？
2. **准确性**：描述是否符合实际情况？
3. **及时性**：响应延迟是否可接受？

### 定量指标

```python
# 示例：记录关键指标
metrics = {
    "frame_interval": 20,
    "avg_latency_ms": 450,
    "context_accuracy": "8/10",  # 人工评分
    "action_continuity": "7/10",  # 人工评分
    "api_cost_per_minute": 0.05  # USD
}
```

---

## 故障排查

### 问题 1: 响应历史没有效果

**可能原因**：
- Prompt 太长，超出模型上下文长度
- 小模型理解能力不足

**解决方案**：
- 减少 `max_history` 到 2-3
- 精简历史描述，只保留关键词
- 尝试更大的模型

---

### 问题 2: 多帧合成导致推理过慢

**可能原因**：
- 图片尺寸太大
- 帧数过多

**解决方案**：
- 在拼接前先缩小图片：`cv2.resize(img, (320, 240))`
- 减少帧数到 2-3 帧
- 增加 `process_every_n_frames` 间隔

---

### 问题 3: API 成本过高

**可能原因**：
- 采样过于频繁
- 使用了多帧合成

**解决方案**：
- 增加 `process_every_n_frames` 到 60-90
- 启用策略 3（关键帧检测）
- 使用本地模型（Ollama）而非云 API

---

## 进阶话题

### 结合外部工具

可以考虑集成以下工具增强效果：

1. **YOLO/目标检测**：预先识别关键对象
2. **姿态估计**：提取人体骨架信息
3. **场景分类**：识别环境类型（室内/室外/体育场等）

示例：
```python
# 伪代码
detected_objects = yolo_detector.detect(frame)
pose_data = pose_estimator.estimate(frame)

enhanced_prompt = f"""
{base_prompt}

[场景信息]
- 检测到的对象: {', '.join(detected_objects)}
- 人体姿态: {pose_data['action_label']}
"""
```

---

## 总结

| 策略 | 难度 | 效果 | 成本 | 推荐度 |
|------|------|------|------|--------|
| 1. 提示词工程 | ⭐ | ⭐⭐⭐⭐⭐ | 低 | ⭐⭐⭐⭐⭐ |
| 2. 多帧合成 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 高 | ⭐⭐⭐⭐ |
| 3. 关键帧检测 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 中 | ⭐⭐⭐ |
| 4. 运动追踪 | ⭐⭐⭐⭐ | ⭐⭐⭐ | 低 | ⭐⭐⭐ |
| 5. 双模型 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 高 | ⭐⭐⭐ |

**最佳实践路径**：
1. 从**策略 1**开始（最简单，效果好）
2. 如果效果不满意，添加**策略 2**（多帧合成）
3. 如果成本过高，引入**策略 3**（关键帧检测）优化
4. 生产环境考虑**策略 5**（双模型）平衡实时性和准确性

---

## 相关资源

- [VLM 模型列表](./list-of-vlms.md)
- [RTSP 摄像头配置](./rtsp-ip-cameras.md)
- [高级配置选项](./advanced-configuration.md)
- [故障排查指南](../troubleshooting.md)

---

**文档版本**: v1.0
**最后更新**: 2026-02-12
**维护者**: Community Contributors
