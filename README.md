# 🦾 DoggyClawAssistant

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux%20ARM64-orange)](https://developer.nvidia.com/embedded/jetson-agx-xavier)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Robot](https://img.shields.io/badge/Robot-Unitree%20Aliengo-blue)](https://www.unitree.com/)
[![AI](https://img.shields.io/badge/AI-NaVILA%20%7C%20OpenClaw-purple)](https://github.com/YuhengNa/DoggyClawAssistant)

**OpenClaw-Enhanced Multimodal Embodied Intelligence for Quadruped Mobile Manipulation**

DoggyClawAssistant 是一个面向四足机器人的多模态具身智能系统，将 **NaVILA 视觉语言导航模型** 与 **Unitree Aliengo** 四足机器人深度集成，通过 **OpenClaw LLM 意图解析引擎** 实现自然语言驱动的自主导航与操控。

---

## 🌟 核心特性

| 特性 | 说明 |
|------|------|
| 🧠 **NaVILA 视觉导航** | 基于 LLaMA3-8B 的多帧视觉语言导航推理 |
| 🐕 **Aliengo 直接控制** | 100Hz UDP 高频控制，精准执行运动指令 |
| 🦞 **OpenClaw 意图解析** | 自然语言 → 结构化运动命令的智能转换 |
| 📷 **RealSense 视觉** | Intel RealSense RGB-D 深度视觉感知 |
| 🔄 **实时反馈闭环** | 视觉感知 → 推理 → 执行 → 感知的完整闭环 |
| 🖥️ **AGX 上位机** | NVIDIA AGX Xavier 高性能推理平台 |

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    AGX Xavier (上位机)                    │
│                                                         │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────┐  │
│  │  RealSense  │───▶│  NaVILA      │───▶│  OpenClaw  │  │
│  │  RGB-D 相机  │    │  LLaMA3-8B   │    │  意图解析  │  │
│  └─────────────┘    └──────────────┘    └─────┬──────┘  │
│                                               │         │
│                                    ┌──────────▼──────┐  │
│                                    │ AliengoAdapter  │  │
│                                    │  UDP 100Hz 控制  │  │
│                                    └──────────┬──────┘  │
└───────────────────────────────────────────────┼─────────┘
                                                │ UDP
                                    ┌───────────▼──────────┐
                                    │   Mini PC (下位机)    │
                                    │   UDP Bridge         │
                                    └───────────┬──────────┘
                                                │
                                    ┌───────────▼──────────┐
                                    │  Unitree Aliengo     │
                                    │  四足机器人           │
                                    └──────────────────────┘
```

---

## 📁 项目结构

```
DoggyClawAssistant/
├── navigation/                    # 导航核心模块
│   ├── 001_aliengo.py             # 主导航程序（NaVILA + Aliengo）
│   ├── aliengo_adapter.py         # Aliengo UDP 控制适配器
│   ├── inference.py               # NaVILA 推理模块
│   ├── navilarobot_deploy.py      # 机器人部署脚本
│   ├── diagnose.py                # 系统诊断工具
│   ├── test_simple.py             # 快速测试脚本
│   └── test_compare.py            # 对比测试脚本
├── skills/                        # OpenClaw 技能模块
│   └── aliengo/                   # Aliengo 控制技能
├── docs/                          # 文档
│   ├── QUICK_START.md             # 快速开始
│   └── ARCHITECTURE.md            # 架构说明
├── requirements.txt               # Python 依赖
└── README.md                      # 项目说明
```

---

## 🚀 快速开始

### 环境要求

- **硬件**: NVIDIA AGX Xavier + Intel RealSense + Unitree Aliengo
- **系统**: Ubuntu 20.04 / JetPack 5.x
- **Python**: 3.8+
- **网络**: AGX 与 Aliengo 下位机在同一局域网（172.16.10.x）

### 安装依赖

```bash
git clone https://github.com/YuhengNa/DoggyClawAssistant.git
cd DoggyClawAssistant
pip install -r requirements.txt
```

### 系统诊断

首次运行前，先执行诊断工具检查所有组件状态：

```bash
python3 navigation/diagnose.py
```

诊断项目包括：
- ✅ Python 依赖检查
- ✅ RealSense 相机连接
- ✅ 网络连通性（ping Aliengo）
- ✅ UDP 端口可达性
- ✅ NaVILA 模型加载

### 快速测试 Aliengo 连接

```bash
# 测试前进 0.1m
python3 navigation/test_simple.py move_forward 0.1

# 测试左转 30°
python3 navigation/test_simple.py turn_left 30
```

### 运行完整导航

```bash
python3 navigation/001_aliengo.py
```

---

## 🧠 NaVILA 导航模型

NaVILA（Navigation with Vision-Language Action）是基于 LLaMA3-8B 的多帧视觉语言导航模型：

- **模型**: `navila-llama3-8b-8f`
- **输入**: 8帧历史视觉观测 + 自然语言导航指令
- **输出**: 结构化动作命令（前进/后退/左转/右转/停止）
- **推理平台**: NVIDIA AGX Xavier（TensorRT 加速）

```python
# 推理示例
from navigation.inference import NaVILAInference

model = NaVILAInference("navila-llama3-8b-8f")
action = model.predict(
    frames=last_8_frames,
    instruction="走到红色椅子旁边"
)
# action: {"type": "move_forward", "distance": 0.5}
```

---

## 🐕 Aliengo 控制协议

### UDP 通信参数

| 参数 | 值 |
|------|-----|
| 目标 IP | `172.16.10.219` |
| 目标端口 | `9090` |
| 数据包格式 | `<I B 8f I` |
| 发送频率 | **100 Hz** |

### 运动模式

```python
# mode=0: 停止/空闲
# mode=1: 站立
# mode=2: 行走（必须使用此模式才能移动）

# 前进示例
adapter.send_for_duration(mode=2, fwd=0.3, duration=2.0)

# 左转示例
adapter.send_for_duration(mode=2, rot=0.3, duration=1.5)

# 停止
adapter.send_stop()
```

### 为什么需要 100Hz 高频发送？

机器人底层控制器需要**持续接收**控制命令才会保持运动。单次发送只会触发一个控制周期（10ms），之后机器人会自动停止。100Hz 是 Aliengo 的标准控制频率。

---

## 🔧 配置说明

### 网络配置

编辑 `navigation/aliengo_adapter.py`：

```python
ROBOT_IP = "172.16.10.219"   # Aliengo 下位机 IP
ROBOT_PORT = 9090             # UDP 端口
```

### 运动参数标定

```python
self.forward_speed = 0.3      # 前进速度 (m/s 控制值)
self.rotate_speed = 0.3       # 旋转速度 (rad/s 控制值)
self.estimated_mps = 1.0      # 实测前进速度（需标定）
self.estimated_dps = 45.0     # 实测转向速度 °/s（需标定）
```

**标定方法：**

```bash
# 1. 测试 5 秒前进，测量实际距离
python3 -c "from navigation.aliengo_adapter import AliengoAdapter; a=AliengoAdapter(); a.send_for_duration(2, fwd=0.3, duration=5)"

# 2. 假设实际前进 1.5m
# estimated_mps = 1.5 / (0.3 * 5) = 1.0
```

---

## 🛠️ 故障排查

### 机器人不移动

```bash
# 1. 检查网络连通性
ping 172.16.10.219

# 2. 检查下位机 UDP Bridge 状态
ssh mini-pc "ps aux | grep udp_bridge"

# 3. 运行诊断工具
python3 navigation/diagnose.py

# 4. 对比测试（原始 vs 适配器）
python3 navigation/test_compare.py
```

### 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| UDP 超时 | 网络不通 | 检查 IP 配置和防火墙 |
| 机器人抖动但不移动 | mode 设置错误 | 确保使用 mode=2 |
| 距离不准确 | 速度参数未标定 | 按标定方法重新标定 |
| 相机无法打开 | RealSense 未连接 | 检查 USB 连接 |

---

## 📊 系统性能

| 指标 | 值 |
|------|-----|
| 推理延迟 | ~200ms (AGX TensorRT) |
| 控制频率 | 100 Hz |
| 导航精度 | ±10cm（标定后） |
| 转向精度 | ±5° （标定后） |

---

## 🗺️ 路线图

- [x] NaVILA + Aliengo 基础集成
- [x] 100Hz UDP 直接控制
- [x] 系统诊断工具
- [ ] ROS2 接口支持
- [ ] LiDAR SLAM 集成
- [ ] 多目标跟踪
- [ ] 语音指令控制
- [ ] 自动运动参数标定

---

## 📖 相关文档

- [快速开始指南](docs/QUICK_START.md)
- [系统架构说明](docs/ARCHITECTURE.md)
- [Aliengo 适配器 V2 说明](navigation/README_ALIENGO_ADAPTER_V2.md)
- [NaVILA 原始论文](https://arxiv.org/abs/2412.04453)

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 许可证

MIT License © 2026 YuhengNa

---

*Powered by OpenClaw 🦞 × NaVILA 🧠 × Unitree Aliengo 🐕*
