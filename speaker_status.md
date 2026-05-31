# 喇叭模块状态检查记录

检查时间：2026-05-23  
检查目录：`/home/cat/ai/qwen3vl2b`  
设备型号：Embedfire LubanCat-5IO

## 结论

当前喇叭模块使用 `rockchip-es8388` 音频设备，系统侧喇叭输出已经打开。

当前硬件接线情况：

- 已接：`SPK_R`
- 未接：`SPK_L`

因此播放右声道内容时，应该从当前接入的右声道喇叭出声；播放左声道内容时，因为 `SPK_L` 未接，不会从外接喇叭听到声音。

## 设备树状态

当前设备树中 ES8388 音频节点已启用：

```text
/sys/firmware/devicetree/base/es8388-sound/status = okay
```

该节点中存在喇叭控制 GPIO：

```text
/sys/firmware/devicetree/base/es8388-sound/spk-con-gpio
```

音频路由中喇叭输出对应：

```text
Speaker -> LOUT2
Speaker -> ROUT2
```

对应关系：

- `LOUT2`：左声道喇叭输出，通常对应 `SPK_L`
- `ROUT2`：右声道喇叭输出，通常对应 `SPK_R`

## ALSA 播放设备

通过 `aplay -l` 可以看到 ES8388 播放设备：

```text
card 4: rockchipes8388 [rockchip-es8388], device 0: dailink-multicodecs ES8323 HiFi-0 [dailink-multicodecs ES8323 HiFi-0]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
```

对应 ALSA 设备名：

```text
hw:4,0
```

也可以使用声卡名称访问：

```text
rockchipes8388
```

## Mixer 状态

当前关键 mixer 状态如下：

```text
spk switch: Playback [on]
Speaker: Playback [on]
Output 2 Front Left: Playback 27 [82%] [-4.50dB]
Output 2 Front Right: Playback 27 [82%] [-4.50dB]
```

说明：

- `spk switch = on`：喇叭功放/喇叭使能开关已打开。
- `Speaker = on`：喇叭播放路径已打开。
- `Output 2 Front Right = 82%`：右声道喇叭输出音量已打开，当前接入的 `SPK_R` 使用该通道。
- `Output 2 Front Left = 82%`：左声道也处于打开状态，但当前 `SPK_L` 未接线。

## 右声道测试

已使用以下命令进行右声道测试：

```bash
speaker-test -D hw:4,0 -c 2 -t sine -f 1000 -s 2 -l 1
```

测试输出显示：

```text
Front Right
```

说明系统已经向右声道播放测试音。由于当前只接了 `SPK_R`，该测试用于验证右声道喇叭输出。

## 播放麦克风录音

当前硬件只接了 `SPK_R`，未接 `SPK_L`。而板载麦克风双声道录音时，声音主要落在左声道。

因此直接播放双声道录音时：

```bash
aplay -D hw:4,0 /tmp/voice_test.wav
```

可能会很小声或听不见。原因是：

```text
麦克风声音主要在 Left
当前外接喇叭只接 SPK_R / Right
```

已验证 `/tmp/voice_test.wav` 的声道电平：

```text
Left peak:  -29.4 dB
Right peak: -52.1 dB
```

如果只接 `SPK_R`，播放麦克风录音前应将录音混到右声道并适当放大：

```bash
ffmpeg -y -i /tmp/voice_test.wav \
  -af "pan=stereo|c0=0*c0|c1=c0+c1,volume=8,alimiter=limit=0.9" \
  -ar 48000 -ac 2 -sample_fmt s16 /tmp/voice_test_right_boost.wav

aplay -D hw:4,0 /tmp/voice_test_right_boost.wav
```

更简单的录音方式是先录单声道，再复制到右声道播放：

```bash
arecord -D hw:4,0 -f S16_LE -r 48000 -c 1 -d 5 /tmp/voice_test_mono.wav

ffmpeg -y -i /tmp/voice_test_mono.wav \
  -af "pan=stereo|c0=0*c0|c1=c0,volume=4,alimiter=limit=0.9" \
  -ar 48000 -ac 2 -sample_fmt s16 /tmp/voice_test_right.wav

aplay -D hw:4,0 /tmp/voice_test_right.wav
```

根本解决办法是同时接上 `SPK_L` 和 `SPK_R`，这样普通双声道录音和音乐播放都不会丢左声道内容。

## 自动保持打开

已经添加 systemd 常驻服务，用于启动后持续监控 ES8388 喇叭输出。

如果播放结束后驱动把 `spk switch` 自动拉回 `off`，该服务会在约 1 秒内重新设置为 `on`。

服务文件：

```text
/etc/systemd/system/enable-es8388-speaker.service
```

执行脚本：

```text
/usr/local/sbin/enable-es8388-speaker.sh
```

服务状态：

```text
Loaded: loaded (/etc/systemd/system/enable-es8388-speaker.service; enabled)
Active: active (running)
ExecStart: /usr/local/sbin/enable-es8388-speaker.sh
```

服务启动时执行的初始化设置：

```bash
amixer -c rockchipes8388 set 'Speaker' on
amixer -c rockchipes8388 set 'Output 2' 82%
```

服务运行期间持续检查并自动恢复：

```bash
amixer -c rockchipes8388 set 'spk switch' on
```

已验证：手动将 `spk switch` 设置为 `off` 后，服务会自动恢复为 `on`。

## 当前状态汇总

| 项目 | 状态 |
| --- | --- |
| 喇叭音频设备 | `rockchip-es8388` |
| ALSA 设备 | `hw:4,0` |
| 设备树 ES8388 节点 | `okay` |
| 喇叭路由 | `Speaker -> LOUT2/ROUT2` |
| 当前接线 | 只接 `SPK_R` |
| `SPK_R` 系统侧状态 | 已打开 |
| `SPK_L` 系统侧状态 | 已打开但未接线 |
| `spk switch` | `on` |
| `Speaker` | `on` |
| `Output 2 Front Right` | `82%` |
| 右声道测试 | 已完成 |
| 麦克风录音播放注意 | 双声道录音需混到右声道 |
| 自动保持打开服务 | 已启用并运行中 |
