# 🦞 DoggyClawAssistant

**基于多模态 AI 融合的四足双臂助盲机器人开源框架**

面向视障人群的室内及半结构化环境助行与生活辅助场景，打通"语义输入 → 自主导航 → 视觉识别 → 抓取递送"的端到端闭环。

---

## 🌟 核心特性

| 特性 | 说明 |
|------|------|
| 🧠 **多模态 AI 融合** | 视觉语言导航 + 意图理解 + 抓取决策 |
| 🐕 **四足移动平台** | Unitree AlienGo (12 DoF, 5-10kg 动态负载) |
| 🦾 **双臂操作系统** | LeRobot SO101 ×2 (单臂 6 DoF, 0.49kg 末端载荷) |
| 👁️ **RGB-D 感知** | Intel RealSense D435 + 双臂腕部相机 |
| 🎯 **端到端闭环** | 语义输入 → 导航 → 识别 → 抓取 → 递送 |
| 🗣️ **自然语言交互** | 飞书机器人语音入口 → OpenClaw 调度 |

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     DoggyClawAssistant                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              OpenClaw Skills 中间层                      │   │
│  │   导航 | 识别 | 抓取 | 递物 | 语音交互                   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│      ┌───────────────────────┼───────────────────────┐          │
│      ▼                       ▼                       ▼          │
│  ┌─────────────┐      ┌─────────────┐         ┌─────────────┐  │
│  │ Navigation  │      │Pick&Place   │         │  Interaction│  │
│  │   Skill     │      │   Skill     │         │    Layer    │  │
│  └─────────────┘      └─────────────┘         └─────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              分层导航架构 (NaVILA-Style)                 │   │
│  │   高层 VLM (Llama3+VGGT, ~1Hz)  →  底层 RL (~100Hz)     │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────┼───────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Jetson AGX Orin   │
                    │   (275 TOPS)       │
                    └──────────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
┌─────────────┐        ┌─────────────┐        ┌─────────────┐
│  AlienGo    │        │  SO101×2    │        │  RealSense  │
│  UDP:9090   │        │  UART+STS3215│        │   D435      │
└─────────────┘        └─────────────┘        └─────────────┘
```

---

## 📁 项目结构

```
DoggyClawAssistant/
├── navigation/                 # 导航模块
│   ├── aliengo_adapter.py     # AlienGo UDP 控制适配器
│   ├── inference.py           # NaVILA 推理模块
│   ├── diagnose.py            # 系统诊断工具
│   └── test_*.py              # 测试脚本
├── software/                  # 软件代码
├── hardware/                  # 硬件设计
├── skills/                    # OpenClaw 技能封装
├── docs/                      # 文档
├── docker/                    # Docker 配置
└── README.md
```

---

## 🛠️ 硬件清单

| 组件 | 型号 | 说明 |
|------|------|------|
| 四足底盘 | Unitree AlienGo | 12 DoF, 5-10kg 动态负载 |
| 双臂 | LeRobot SO101×2 | 单臂 6 DoF, 末端 0.49kg |
| 计算单元 | NVIDIA Jetson AGX Orin | 275 TOPS, 64GB |
| 主感知 | Intel RealSense D435 | RGB-D, 0.3-3m |
| 腕部相机 | 640×480 @ 30fps×2 | 双臂末端 |

---

## 🚀 快速开始

```bash
git clone https://github.com/YuhengNa/DoggyClawAssistant.git
cd DoggyClawAssistant
pip install -r requirements.txt

# 启动系统
cd software
python start_system.py

# 或开发模式
./scripts/start.sh --dry-run
```

---

## 📖 核心模块

### 1. OpenClaw Skills 中间层
导航、识别、抓取、递物、语音交互封装为标准 Skill 单元。

### 2. Navigation Skill (NaVILA-Style)
- 高层 VLM: Llama 3 + VGGT，1Hz
- 底层 RL: IsaacLab，100Hz

### 3. Pick & Place Skill (HIL-SERL)
SO101 主从遥操作 + 在线 RL

### 4. 交互层
飞书机器人 → Webhook → OpenClaw → Jetson

---

## 📡 通信协议

| 设备 | 协议 | 端口 | 频率 |
|------|------|------|------|
| AlienGo | UDP | 9090 | 100Hz |
| SO101 | UART | /dev/ttyUSB1-2 | 50Hz |
| RealSense | USB3.0 | - | 30fps |
| 控制器 | ROS2 | - | 50Hz |

---

## 📄 许可证

MIT License © 2026 YuhengNa

---

*Powered by OpenClaw 🦞 × NaVILA 🧠 × Unitree AlienGo 🐕 × LeRobot SO101 🦾*