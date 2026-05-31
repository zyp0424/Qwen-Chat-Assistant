# 板载麦克风状态检查记录

检查时间：2026-05-23  
检查目录：`/home/cat/ai/qwen3vl2b`

## 结论

板载麦克风已经打开并可用。

系统已识别到板载 ES8388 音频设备，录音通道未静音，并且已经通过实际录音测试确认可以采集到有效音频电平。

## 设备枚举

通过 `arecord -l` 查看录音硬件设备，发现板载录音设备：

```text
card 4: rockchipes8388 [rockchip-es8388], device 0: dailink-multicodecs ES8323 HiFi-0 [dailink-multicodecs ES8323 HiFi-0]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
```

对应的 ALSA 设备为：

```text
hw:4,0
```

## Mixer 状态

通过 `amixer -c 4 scontents` 查看板载声卡 mixer 状态，关键项目如下：

```text
Main Mic: Playback [on]
Capture Mute: Playback [off]
Capture Digital: 192 [100%] [0.00dB]
Left Channel: Capture 3 [38%] [9.00dB]
Right Channel: Capture 3 [38%] [9.00dB]
```

说明：

- `Main Mic = on`：主麦克风通道已打开。
- `Capture Mute = off`：录音静音功能关闭，也就是麦克风没有被静音。
- `Capture Digital = 100%`：录音数字音量为满量程。

## 录音测试

使用以下命令进行了 2 秒录音测试：

```bash
arecord -D hw:4,0 -f S16_LE -r 48000 -c 2 -d 2 /tmp/onboard_mic_test.wav
```

命令执行成功，生成了录音文件：

```text
/tmp/onboard_mic_test.wav
```

文件大小：

```text
376K
```

## 音频电平

使用 `ffmpeg volumedetect` 检查录音文件电平：

```text
mean_volume: -42.3 dB
max_volume: -27.9 dB
```

说明：

- `mean_volume: -42.3 dB` 表示录音中存在实际输入信号，整体音量偏小。
- `max_volume: -27.9 dB` 表示录音中存在明显的音频峰值。
- 结果不是全静音，因此可以判断麦克风采集到了有效音频电平。

## 录音声道说明

板载麦克风能够采集声音，但使用双声道参数录音时：

```bash
arecord -D hw:4,0 -f S16_LE -r 48000 -c 2 -d 5 /tmp/voice_test.wav
```

生成的 WAV 文件会包含两个声道：

```text
Channel 1 / Left
Channel 2 / Right
```

当前测试中，麦克风声音主要落在左声道。对 `/tmp/voice_test.wav` 做声道电平分析时，结果为：

```text
Left peak:  -29.4 dB
Right peak: -52.1 dB
```

这不代表麦克风没有识别到声音，而是 ES8388 将麦克风采样主要放在左声道轨道中。

如果后续只需要录人声，建议直接录单声道：

```bash
arecord -D hw:4,0 -f S16_LE -r 48000 -c 1 -d 5 /tmp/voice_test_mono.wav
```

## 当前状态汇总

| 项目 | 状态 |
| --- | --- |
| 板载声卡 | 已识别 |
| 录音设备 | `card 4, device 0` |
| ALSA 设备 | `hw:4,0` |
| 主麦克风 | 已打开 |
| 录音静音 | 已关闭 |
| 录音测试 | 成功 |
| 有效音频电平 | 已检测到 |
| 双声道录音特点 | 声音主要在左声道 |
