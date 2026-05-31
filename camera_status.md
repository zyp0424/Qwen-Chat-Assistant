# 摄像头模块状态检查记录

检查时间：2026-05-23 18:59:43 CST +0800  
检查目录：`/home/cat/ai/qwen3vl2b`  
设备型号：`Embedfire LubanCat-5IO`  
用户确认板型：LubanCat 5BTB（16+128G）  
摄像头模块：IMX415，接在 CAM4

## 结论

当前正在使用的 MIPI 摄像头链路已经打开并可用。

系统已经识别到 IMX415 传感器，CAM4 对应的 `csi2-dphy4`、`mipi4-csi2`、`rkcif-mipi-lvds4`、`rkisp1-vir1` 和 `rkisp@fdcc0000` 关键节点均为 `okay`。

当前实际拍照使用的 V4L2 节点是：

```text
/dev/video11
```

该节点对应：

```text
rkisp_mainpath (platform:rkisp1-vir1)
```

当前默认拍照格式为：

```text
1920x1080 NV12
```

1080p NV12 原始帧大小为：

```text
3110400 bytes
```

这和实际 `v4l2-ctl` 读取到的 `Size Image` 一致。

## 当前启动 DTB

当前 `/boot/firmware/ubuntuEnv.txt` 中使用的设备树文件为：

```text
fdtfile=rk3588-lubancat-5io-cam4-imx415.dtb
```

该 DTB 是此前为了 CAM4 IMX415 摄像头链路启用而使用的自定义 DTB。

## 设备树状态

当前关键节点状态如下：

| 节点 | 状态 |
| --- | --- |
| `/sys/firmware/devicetree/base/i2c@fec90000/dphy4-imx415@1a` | `okay` |
| `/sys/firmware/devicetree/base/csi2-dphy4` | `okay` |
| `/sys/firmware/devicetree/base/mipi4-csi2` | `okay` |
| `/sys/firmware/devicetree/base/rkcif-mipi-lvds4` | `okay` |
| `/sys/firmware/devicetree/base/rkcif-mipi-lvds4-sditf` | `okay` |
| `/sys/firmware/devicetree/base/rkisp1-vir1` | `okay` |
| `/sys/firmware/devicetree/base/rkisp@fdcc0000` | `okay` |
| `/sys/firmware/devicetree/base/i2c@fec90000/dphy4-dw9714@c` | `disabled` |

说明：

- IMX415 传感器节点已经启用。
- CAM4 的 CSI/DPHY/CIF/ISP 主链路已经启用。
- `dphy4-dw9714@c` 是对焦马达/VCM 相关节点，目前是 `disabled`，所以当前没有可用的自动对焦控制。

## V4L2 设备枚举

通过 `v4l2-ctl --list-devices` 当前看到的摄像头相关设备如下：

```text
rkcif (platform:rkcif-mipi-lvds4):
        /dev/video0
        /dev/video1
        /dev/video2
        /dev/video3
        /dev/video4
        /dev/video5
        /dev/video6
        /dev/video7
        /dev/video8
        /dev/video9
        /dev/video10
        /dev/media0

rkisp_mainpath (platform:rkisp1-vir1):
        /dev/video11
        /dev/video12
        /dev/video13
        /dev/video14
        /dev/video15
        /dev/video16
        /dev/video17
        /dev/media1

rkisp-statistics (platform: rkisp):
        /dev/video18
        /dev/video19
```

当前拍照使用 `/dev/video11`，也就是 `rkisp_mainpath`。

## 当前 `/dev/video11` 格式

通过 `v4l2-ctl -d /dev/video11 --get-fmt-video --all` 读取到：

```text
Driver name      : rkisp_v6
Card type        : rkisp_mainpath
Bus info         : platform:rkisp1-vir1
Driver version   : 3.0.0

Format Video Capture Multiplanar:
        Width/Height      : 1920/1080
        Pixel Format      : 'NV12' (Y/UV 4:2:0)
        Field             : None
        Number of planes  : 1
        Plane 0:
           Bytes per Line : 1920
           Size Image     : 3110400

Selection Video Capture: crop, Left 0, Top 0, Width 3840, Height 2160
```

说明：

- ISP 主路径当前输出是 `1920x1080 NV12`。
- 上游裁剪范围是 `3840x2160`，说明传感器/ISP 链路仍以 4K 视场进入，最终由 ISP 输出 1080p。

## Media 拓扑

当前主链路可以概括为：

```text
m04_b_imx415 7-001a
  -> rockchip-csi2-dphy4
  -> rockchip-mipi-csi2
  -> rkcif-mipi-lvds4
  -> rkisp-isp-subdev
  -> rkisp_mainpath
  -> /dev/video11
```

`/dev/media0` 传感器/CIF 侧关键拓扑：

```text
m04_b_imx415 7-001a (/dev/v4l-subdev2)
  pad0 Source: SGBRG10_1X10/3864x2192@10000/150000
  -> rockchip-csi2-dphy4:0 [ENABLED]

rockchip-csi2-dphy4 (/dev/v4l-subdev1)
  -> rockchip-mipi-csi2:0 [ENABLED]
```

`/dev/media1` ISP 侧关键拓扑：

```text
rkcif-mipi-lvds4 (/dev/v4l-subdev4)
  -> rkisp-isp-subdev:0 [ENABLED]

rkisp-isp-subdev
  -> rkisp_mainpath:0 [ENABLED]

rkisp_mainpath
  device node name /dev/video11
```

## IMX415 子设备状态

当前 IMX415 子设备为：

```text
/dev/v4l-subdev2
```

当前 pad 格式：

```text
Width/Height      : 3864/2192
Mediabus Code     : MEDIA_BUS_FMT_SGBRG10_1X10
Field             : None
Quantization      : Full Range
```

当前可见控制项：

```text
exposure          min=4 max=2242 default=2242 value=1013
horizontal_flip   default=0 value=0
vertical_flip     default=0 value=0
vertical_blanking min=58 max=30575 default=58 value=58
horizontal_blanking value=4936 read-only
analogue_gain     min=0 max=240 default=0 value=17
link_frequency    value=1 (446000000)
pixel_rate        value=178400000 read-only
```

没有看到 focus/auto-focus 相关 V4L2 控制项。结合 `dphy4-dw9714@c = disabled`，当前应按手动调焦镜头处理。

## 内核识别记录

当前内核日志中可以看到 IMX415 已被识别：

```text
imx415 7-001a: Detected imx415 id 0000e0
rockchip-csi2-dphy csi2-dphy4: dphy4 matches m04_b_imx415 7-001a
rkcif-mipi-lvds4: Async subdev notifier completed
rkisp1-vir1: Async subdev notifier completed
```

实际采集时也能看到链路启动：

```text
rkcif-mipi-lvds4: stream[0] start streaming
rockchip-mipi-csi2 mipi4-csi2: stream ON
rockchip-csi2-dphy4: dphy4, data_rate_mbps 892
imx415 7-001a: s_stream: 1. 3864x2192, hdr: 0, bpp: 10
```

## 默认拍照方式

已经封装了 Codex skill：

```text
/home/cat/.codex/skills/lubancat-camera-capture
```

默认拍照脚本：

```text
/home/cat/.codex/skills/lubancat-camera-capture/scripts/capture-photo.sh
```

默认参数：

| 参数 | 值 |
| --- | --- |
| V4L2 节点 | `/dev/video11` |
| 分辨率 | `1920x1080` |
| 像素格式 | `NV12` |
| 跳过帧数 | `30` |
| 输出目录 | `/home/cat/图片` |

等价手动命令：

```bash
ts=$(date +%Y%m%d_%H%M%S)
v4l2-ctl -d /dev/video11 \
  --set-fmt-video=width=1920,height=1080,pixelformat=NV12 \
  --stream-mmap=4 --stream-skip=30 --stream-count=1 \
  --stream-to="/home/cat/图片/camera_${ts}.nv12"
ffmpeg -y -f rawvideo -pix_fmt nv12 -s 1920x1080 \
  -i "/home/cat/图片/camera_${ts}.nv12" -frames:v 1 \
  "/home/cat/图片/camera_${ts}.jpg"
```

## 当前已有拍照文件

当前 `/home/cat/图片` 中存在这些摄像头拍照文件：

```text
/home/cat/图片/camera_20260521_214825.jpg
/home/cat/图片/camera_20260521_214825.nv12
/home/cat/图片/camera_20260523_105159.jpg
/home/cat/图片/camera_20260523_105159.nv12
/home/cat/图片/camera_20260523_110826.jpg
/home/cat/图片/camera_20260523_110826.nv12
```

其中 `.jpg` 是可直接查看的照片，`.nv12` 是对应的原始帧。

## 当前状态汇总

| 项目 | 状态 |
| --- | --- |
| 摄像头型号 | IMX415 |
| 接口位置 | CAM4 |
| 传感器 I2C | `7-001a` |
| 传感器节点 | `m04_b_imx415 7-001a` |
| 传感器设备 | `/dev/v4l-subdev2` |
| CSI DPHY | `csi2-dphy4`，`okay` |
| MIPI CSI2 | `mipi4-csi2`，`okay` |
| CIF | `rkcif-mipi-lvds4`，`okay` |
| ISP | `rkisp1-vir1`，`okay` |
| 拍照节点 | `/dev/video11` |
| 拍照节点类型 | `rkisp_mainpath` |
| 默认输出格式 | `1920x1080 NV12` |
| 原始帧大小 | `3110400 bytes` |
| 默认输出目录 | `/home/cat/图片` |
| 自动对焦/VCM | 未启用，`dphy4-dw9714@c = disabled` |
| 当前判断 | 摄像头链路已开启，可正常采集 |

