# 中文语音拍照 Qwen-VL 助手测试说明

## 已安装内容

- Python 虚拟环境：`.venv`
- 本地中文 ASR/KWS/TTS 框架：`sherpa-onnx`
- 中文 ASR 模型：`models/sherpa-onnx-conformer-zh-stateless2-2023-05-23`
- 中文/英文 KWS 模型：`models/sherpa-onnx-kws-zipformer-zh-en-3M-2025-12-20`
- 中文 TTS 模型：`models/matcha-icefall-zh-baker` + `models/vocos-22khz-univ.onnx`
- 主入口：`voice_assistant.py`
- 配置：`config/default.yaml`

## 分段测试

1. 测中文 STT：

```bash
./scripts/test_stt_record.sh 5
```

开始录音后说一句中文，例如“请拍照看看眼前有什么”。

2. 测中文 TTS 和外接喇叭播放：

```bash
./scripts/test_tts_play.sh "你好，我是本地中文语音助手。"
```

播放链路会把 TTS 单声道 samples 在内存中转成 44100Hz 双声道 PCM，再写入 `aplay` 播放，避免单声道到外接喇叭模块时由 ALSA 隐式混音，也规避该设备不接受 22050Hz 直放的问题。

当前默认 TTS 为中文 Matcha Baker 模型，配置为 `speed=1.0`、`length_scale=1.0`。此前测试过的 VITS 中文模型发音不可懂，已不作为默认方案。

流式播报是唯一回答播放路径：Qwen 输出时会按句切分，每句 TTS 生成后直接转成 44100Hz 双声道 PCM 写入 `aplay`，不为回答播报生成临时 WAV。单独测试流式 PCM 播放：

```bash
.venv/bin/python voice_assistant.py tts-stream "这是流式内存播放测试。"
```

3. 测摄像头拍照：

```bash
./scripts/test_camera.sh
```

成功后会在 `/home/cat/图片` 下生成 `voice_*.jpg`，本轮 `.nv12` 会被删除。

4. 测 Qwen 交互式 wrapper：

```bash
./scripts/test_qwen_text.sh "这张图片里有什么？" demo.jpg
```

包含“图片”二字的问题会保留 `<图片>` 规则，并自动补当前 `demo` 需要的 `<image>` 视觉触发标记。

5. 测一次完整语音流程：

```bash
./scripts/test_once_voice.sh 6
```

开始录音后说完整指令，例如“请拍照看看眼前有什么”。流程会自动 STT、判断拍照、调用 Qwen、TTS、播放。
默认播放方式是流式 TTS：Qwen 每生成一句，喇叭就开始播放该句。

6. 测唤醒词流程：

```bash
./scripts/run_listen.sh kws 6
```

先说“鲁班猫”或“拍照助手”，唤醒后再说 6 秒内的完整指令。

当前唤醒链路会采集双声道音频并只取左声道，启动时自动把 ES8388 采集增益调到 `8/8`。远距离唤醒相关参数在 [config/default.yaml](config/default.yaml)：`capture_channel_gain`、`wake_input_gain`、`keywords_score`、`keywords_threshold`。

如果 KWS 唤醒词效果不好，可用 STT 回退模式：

```bash
./scripts/run_listen.sh stt 6
```

单独诊断唤醒词：

```bash
./scripts/test_wake_record.sh 3
```

这会录 3 秒，只说“鲁班猫”或“拍照助手”。脚本会同时打印 KWS 检测结果和 STT 转写结果。

7. 常驻唤醒模式：

```bash
./scripts/run_listen_forever.sh kws 6
```

每轮结束后会自动回到等待唤醒词状态。按 `Ctrl+C` 退出。

## 临时文件策略

- 中间音频和临时拍照工作目录都在 `/tmp/qwen_voice_assistant/`。
- 无效录音不保留。
- 指令音频 STT 后删除。
- 回答 TTS 音频不落盘，直接以内存 PCM 流播放。
- `.nv12` 原始帧删除。
- JPG 照片保存在 `/home/cat/图片`。

手动清理临时目录：

```bash
.venv/bin/python voice_assistant.py cleanup
```

## 直接命令

转写已有 WAV：

```bash
.venv/bin/python voice_assistant.py stt /path/to/audio.wav
```

流式合成并播放 TTS：

```bash
.venv/bin/python voice_assistant.py tts-stream "你好"
```

文本直接问 Qwen：

```bash
.venv/bin/python voice_assistant.py ask "这张图片里有什么？" --image demo.jpg --no-speak --no-play
```
