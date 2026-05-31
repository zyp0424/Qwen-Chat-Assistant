# 中文语音拍照 Qwen-VL 助手 TODO

目标：通过已配置好的板载麦克风接收中文语音指令，识别唤醒词和问题文本；按需调用已配置好的摄像头拍照；把文字问题和可选图片送入当前目录的 Qwen3-VL RKNN/RKLLM `demo`；再把模型回答用中文 TTS 合成为语音，并通过已配置好的外接喇叭模块播放。

## 0. 已确认条件

- [x] Qwen3-VL 离线推理包已在当前目录：
  - `demo`
  - `imgenc`
  - `qwen3-vl-2b_vision_rk3588.rknn`
  - `qwen3-vl-2b-instruct_w8a8_rk3588.rkllm`
  - `librknnrt.so`
  - `librkllmrt.so`
- [x] `run_qwen3vl.sh` 不只是启动 `demo`，它已经会：
  - 设置 `LD_LIBRARY_PATH=.`
  - 在 `/home/cat/图片` 下查找最新 JPG/JPEG
  - 把最新图片路径传给 `demo`
  - 传入 vision RKNN、LLM RKLLM 和视觉 token
- [x] 目前缺的是：
  - 向 `demo` 的交互式 stdin 写入问题
  - 捕获 `robot:` 后的回答文本
  - 将回答文本交给 TTS
- [x] 摄像头链路已配置，拍照默认参数：
  - 节点：`/dev/video11`
  - 分辨率：`1920x1080`
  - 格式：`NV12`
  - JPG 输出目录：`/home/cat/图片`
  - 已复制到本项目并默认调用：`/home/cat/ai/qwen3vl2b/scripts/capture-photo.sh`
- [x] 板载麦克风已配置：
  - ALSA 录音设备：`hw:4,0`
  - 文档见 `onboard_mic_status.md`
- [x] 外接喇叭模块已配置：
  - 文档见 `speaker_status.md`
  - 当前接线记录为只接 `SPK_R`
  - 播放链路需要按该文档复核，不再称为“板载喇叭”

## 1. 当前最终约束

- [x] STT 必须中文。
- [x] TTS 必须中文；已从不可懂的 VITS 方案切换到中文 `matcha-icefall-zh-baker` + `vocos-22khz-univ.onnx`。
- [x] STT/TTS 优先本地离线，不走联网服务。
- [x] 必须做唤醒词或关键词检测；如果选用的 STT 框架自带关键词检测，可先复用它。
- [x] 先不做 `systemd service`。
- [x] 不保存回答文本日志。
- [x] 不保存无效录音。
- [x] 整个流程的中间文件都放进 `/tmp`。
- [x] `.nv12` 原始帧默认不保留，拍照后只保留 `/home/cat/图片` 下的 JPG。
- [x] `demo` 强依赖 `image_path` 不构成问题；没有真实拍照时可以传占位图片。
- [x] 如果语音问题文本里包含 `图片` 二字，则传给 Qwen 前在文本前加 `<图片>`。
- [x] 当前 `demo` 二进制实际需要 `<image>` 才会使用图片输入；实现里会保留 `<图片>` 规则，同时在发送给 `demo` 时补内部视觉触发标记 `<image>`。

## 2. 推荐架构

第一版做一个手动运行的 Python 编排程序，不做后台服务：

```text
麦克风流
  -> 本地唤醒词/关键词检测
  -> 录制一次有效中文指令到 /tmp
  -> 本地中文 STT
  -> 意图解析
      -> 是否需要拍照
      -> 是否需要在问题前加 <图片>
  -> 可选调用摄像头拍照
      -> JPG 留在 /home/cat/图片
      -> 临时 NV12 删除
  -> Qwen demo wrapper
      -> 启动交互式 demo
      -> 写入问题文本
      -> 流式捕获回答
  -> 按句调用本地中文 TTS
  -> 直接转 raw PCM 写入外接喇叭播放
  -> 删除 /tmp 中本轮临时文件
```

说明：麦克风可以常驻监听，但不需要持续写硬盘。监听阶段只在内存里跑唤醒词/VAD；只有命中唤醒词后，才把本轮有效语音短片段写到 `/tmp` 或直接送给 STT。

## 3. 模块选择

### 3.1 唤醒词 / 关键词检测

- [ ] 首选：`sherpa-onnx` KWS/VAD
  - 原因：同一项目覆盖 ASR、TTS、VAD、KWS，适合减少模块数量。
  - 如果能用中文关键词模型，就直接用它做唤醒词。
- [ ] 备选：`openWakeWord`
  - 适合唤醒词检测，但中文自定义唤醒词可能需要额外训练/样本。
- [ ] 保底：先用 STT 流式识别关键词
  - 一直监听短音频片段，不落盘。
  - 识别到例如“鲁班猫”“拍照助手”后，进入正式指令录制。
  - 代价是比专用 KWS 更费算力。

### 3.2 中文 STT

- [ ] 首选：`sherpa-onnx` 中文流式/非流式 ASR
  - 本地离线。
  - 支持 Python/C++/Node 等接口。
  - 后续可和 KWS/VAD/TTS 共用生态。
- [ ] 备选：`whisper.cpp`
  - 本地离线，中文能力通常不错。
  - 更适合“录完一段再转写”，流式唤醒需要额外适配。
- [ ] 备选：`Vosk` 中文模型
  - 本地离线，轻量，流式方便。
  - 中文准确率需要在当前麦克风上实测。

### 3.3 中文 TTS

- [x] 首选：`sherpa-onnx` 中文 TTS
  - 和 STT/KWS 尽量统一。
  - 当前默认使用 Matcha Baker 中文模型，Vocos 作为声码器。
- [ ] 备选：`piper-tts` / `piper1-gpl` 中文声音模型
  - 本地离线，若后续采用则也应转为 raw PCM 写入外接喇叭播放。
- [ ] 不推荐作为最终方案：`espeak-ng`
  - 可用于临时验证播放链路，但中文自然度和可懂度通常不够。

## 4. 意图解析与摄像头调用

用一个 Python `IntentRouter` 模块识别 STT 后的中文文本。它不直接识别语音，只消费 STT 输出的文本。

第一版规则：

```text
需要拍照关键词：
  拍照、拍一张、照一张、看一下、看看、摄像头、画面、眼前、现在看到

需要加 <图片> 前缀：
  文本中包含 图片

需要加 demo 内部视觉标记：
  本轮拍照，或文本已经带 <图片>
```

处理逻辑：

```text
STT 文本
  -> IntentRouter.analyze(text)
  -> need_photo: bool
  -> qwen_text: str
  -> if "图片" in text: qwen_text = "<图片>" + text
  -> if need_photo or qwen_text startswith "<图片>": demo_text = "<image>" + qwen_text
```

`IntentRouter` 由本项目内的 Python 代码实现，不需要额外 AI 模型。建议接口：

```python
@dataclass
class Intent:
    need_photo: bool
    qwen_text: str

class IntentRouter:
    PHOTO_KEYWORDS = ("拍照", "拍一张", "照一张", "看一下", "看看", "摄像头", "画面", "眼前", "现在看到")

    def analyze(self, text: str) -> Intent:
        need_photo = any(k in text for k in self.PHOTO_KEYWORDS)
        qwen_text = "<图片>" + text if "图片" in text else text
        return Intent(need_photo=need_photo, qwen_text=qwen_text)
```

当 `need_photo = true` 时，由 `CameraAdapter` 调用：

```bash
/home/cat/ai/qwen3vl2b/scripts/capture-photo.sh
```

`CameraAdapter` 也由本项目内的 Python 代码实现，不直接操作 V4L2，而是封装已有拍照脚本。建议接口：

```python
class CameraAdapter:
    def capture(self) -> str:
        """Capture one photo and return final JPG path under /home/cat/图片."""
```

然后：

- 使用 `subprocess` 调用现有脚本。
- 为了遵守临时文件策略，第一步先让脚本输出到 `/tmp/qwen_voice_assistant/capture_work/`。
- 解析脚本输出里的键值：
  - `jpg=...`
  - `raw=...`
  - `raw_size=...`
  - `device=...`
  - `format=...`
- 把临时 JPG 移动到 `/home/cat/图片/`。
- 删除本轮 `.nv12` 原始帧。
- 把最终 JPG 路径作为本轮 Qwen 图片输入。

调用关系：

```text
STT -> 中文文本
  -> IntentRouter.analyze(text)
  -> if need_photo:
       image_path = CameraAdapter.capture()
     else:
       image_path = 占位图片
  -> QwenRunner.ask(image_path, qwen_text)
```

当 `need_photo = false` 时：

- 不调用摄像头。
- 使用占位图片作为 `demo` 的 `image_path`。
- 只把语音转成的问题文本传给 Qwen。

## 5. Qwen demo 交互适配

当前 `demo` 是交互式界面，可以用于第一版，但要区分两种模式：

- 如果本轮使用固定图片或占位图片，交互式进程适合复用，因为模型加载很重，复用已加载的 RKNN/RKLLM 会更快。
- 如果本轮刚拍了新照片，第一版最可靠的做法是每轮按新 `image_path` 启动一次 `demo`。从 usage 看，图片路径是进程启动参数，除非实测证明交互过程中能切换图片，否则不应假设同一个 `demo` 进程能更换图片。

wrapper 仍然适合当前场景，因为它可以：

- 通过 stdin 写入问题。
- 通过 stdout 捕获 `robot:` 后的回答。
- 在“同一张图片连续追问”场景中复用进程。
- 在“新拍一张照片”场景中重启进程以保证图片正确。

风险与对策：

- [x] 需要实测 `demo` 输出边界：
  - 什么时候打印 `user:`
  - 什么时候打印 `robot:`
  - 回答结束是否重新出现 `user:`
- [x] 如果 stdout 缓冲影响捕获，尝试：
  - `stdbuf -oL -eL`
  - Python `pty`
  - `pexpect`
- [ ] 如果交互协议不稳定，后续再考虑拿源码改成非交互 CLI。

第一版 `QwenRunner` 行为：

```text
输入：
  image_path
  qwen_text

步骤：
  1. 按 image_path 启动 ./demo，参数与 run_qwen3vl.sh 一致
  2. 等待进入 user prompt
  3. 写入 qwen_text + "\n"
  4. 捕获 robot 回答，同时按句流式回调
  5. 不保存回答日志
  6. 每句交给 TTS，直接转 raw PCM 写入 `aplay` stdin 播放
  7. 回答后退出 demo
```

注意：`run_qwen3vl.sh` 目前自动取最新图片。为了可控，wrapper 建议直接调用 `./demo` 并显式传入本轮图片路径；如果暂时不改脚本，也可以让拍照脚本保存新 JPG 后继续使用 `run_qwen3vl.sh` 的“最新图片”行为。

## 6. 临时文件策略

所有中间文件放 `/tmp/qwen_voice_assistant/`：

```text
/tmp/qwen_voice_assistant/
  wake_chunk_*.wav        # 可选，默认不保留
  command_*.wav           # 本轮有效指令，STT 后删除
  session_state.json      # 可选，调试时才用
```

默认策略：

- [x] 无效录音不落盘。
- [x] 有效指令音频只临时放 `/tmp`，STT 后删除。
- [x] 回答 TTS 不落盘，只用内存 raw PCM 流写入外接喇叭播放。
- [x] 不保存回答文本日志。
- [x] `.nv12` 拍照原始帧删除。
- [x] JPG 照片按需求保存在 `/home/cat/图片`。

## 7. 外接喇叭播放

播放模块名为 `PcmSpeakerStream`，注释和文档中明确写“外接喇叭模块”，不要写“板载喇叭”。

已验证可用播放命令：

```bash
aplay -q -D plughw:4,0 -t raw -f S16_LE -r 44100 -c 2
```

说明：`hw:4,0` 会拒绝当前 TTS 播放参数，`plughw:4,0` 加上播放前在内存中转为 44100Hz 双声道 PCM 可以稳定输出，所以配置中默认使用 `plughw:4,0`。

## 8. 实施阶段

- [x] Phase 1：安装并验证本地中文 STT/TTS/KWS
  - 已安装/部署 `sherpa-onnx`。
  - 已下载中文 ASR 模型。
  - 已下载中文 TTS 模型，当前默认 `matcha-icefall-zh-baker` + `vocos-22khz-univ.onnx`。
  - 已下载并初始化中文/英文 KWS 模型。
  - 已验证 ASR 样例转写。
  - 已验证 TTS 生成和外接喇叭播放。

- [x] Phase 2：验证 Qwen 交互式 wrapper
  - 已用占位图启动 `demo`。
  - 已自动写入中文问题。
  - 已捕获回答文本。
  - 已验证 `<图片>` 前缀规则和 `<image>` 内部触发标记。

- [x] Phase 3：验证拍照意图相关组件
  - 已实现 `IntentRouter`。
  - 已实现 `CameraAdapter`。
  - 已调用摄像头生成 JPG 到 `/home/cat/图片`。
  - 已删除本轮 `.nv12`。
  - 已验证本轮 JPG 可作为 Qwen 输入路径。

- [x] Phase 4：整合单次完整流程
  - 唤醒词命中。
  - 录制本轮指令。
  - 中文 STT。
  - IntentRouter 判定。
  - 可选拍照。
  - Qwen 流式回答。
  - 中文 TTS 按句合成。
  - raw PCM 直接写入外接喇叭播放。
  - 清理 `/tmp`。

## 9. 当前不做

- [ ] 不做联网 STT/TTS。
- [ ] 不做 systemd service。
- [ ] 不保留回答文本日志。
- [ ] 不保留无效录音。
- [ ] 不保留 `.nv12` 原始帧。
- [ ] 不强行改 `demo` 二进制。

## 10. 需要下载安装到本机的东西

- [x] 本地中文 STT/KWS/VAD/TTS 运行框架：
  - 已安装 `sherpa-onnx`
- [x] 中文 ASR 模型。
- [x] 中文 TTS 模型/声音。
- [x] 中文/英文 KWS 模型。
- [x] Python 侧进程交互库：
  - 已安装 `pexpect`
- [ ] 如果实际测试中 `sherpa-onnx` KWS 对“鲁班猫/拍照助手”效果不够，再额外安装或训练唤醒词模块。

## 11. 建议第一版固定决策

- STT/TTS/KWS：优先本地 `sherpa-onnx` 中文方案。
- 唤醒词：必须做，优先复用 `sherpa-onnx` KWS；不行再换独立唤醒词。
- Qwen：先用交互式 `demo`，写 wrapper 驱动 stdin/stdout。
- 无图片问题：用占位图片，不阻塞流程。
- 包含 `图片`：传给 Qwen 前加 `<图片>`，发送给当前 `demo` 时再自动补 `<image>`。
- 拍照触发：由 `IntentRouter` 识别中文文本关键词，然后调用 `CameraAdapter`。
- 中间文件：全部 `/tmp/qwen_voice_assistant/`，用完删除。
- 服务化：暂时不做。
