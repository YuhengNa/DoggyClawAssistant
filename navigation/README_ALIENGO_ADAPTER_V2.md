# AliengoAdapter 重构说明

## 问题诊断

### 原始问题
测试显示"所有测试通过"，但机器狗没有任何实际移动。

### 根本原因
原来的 `aliengo_adapter.py` 使用 `subprocess` 调用 `aliengo_cmd.py` 脚本，但这种方式存在问题：
- 可能存在进程通信延迟
- 无法确保命令正确传递
- 难以调试实际的 UDP 通信

## 解决方案

### 核心改动
**完全按照 `aliengo_cmd.py` 的逻辑重写适配器，直接发送 UDP 包**

### 关键实现细节

#### 1. UDP 通信参数（与 aliengo_cmd.py 完全一致）
```python
ROBOT_IP = "172.16.10.219"
ROBOT_PORT = 9090
HEADER = 0x12345678
PACK_FORMAT = '<I B 8f I'  # header, mode, fwd, side, rot, height, pitch, roll, yaw, footRaise, reserved
SEND_RATE = 100  # Hz - 每秒发送 100 次
```

#### 2. 数据包格式
```python
def pack_cmd(self, mode, fwd=0, side=0, rot=0, height=0, pitch=0, roll=0, yaw=0, foot_raise=0):
    return struct.pack(
        self.PACK_FORMAT,
        self.HEADER, mode, fwd, side, rot, height, pitch, roll, yaw, foot_raise, 0
    )
```

#### 3. 高频发送（关键！）
```python
def send_for_duration(self, mode, fwd=0, side=0, rot=0, duration=2.0):
    """以 100Hz 频率持续发送命令"""
    count = int(duration * self.SEND_RATE)
    data = self.pack_cmd(mode, fwd, side, rot)
    
    for i in range(count):
        self.sock.sendto(data, (self.ROBOT_IP, self.ROBOT_PORT))
        time.sleep(1.0 / self.SEND_RATE)  # 10ms 间隔
```

**为什么需要高频发送？**
- 机器人需要持续接收控制命令才会移动
- 单次发送不会触发动作
- 100Hz 是机器人控制的标准频率

#### 4. 运动模式（关键！）
```python
# mode=0: idle/stop（停止）
# mode=1: stand（站立）
# mode=2: walk（行走）- 必须使用这个模式才能移动！
```

#### 5. 前进实现
```python
def _execute_forward(self, distance_m):
    duration = distance_m / (self.forward_speed * self.estimated_mps)
    duration = max(self.min_duration, min(self.max_duration, duration))
    
    # 关键：mode=2 (walk mode) + fwd=speed
    self.send_for_duration(mode=2, fwd=self.forward_speed, duration=duration)
    
    # 动作完成后停止
    self.send_stop()
```

#### 6. 转向实现
```python
def _execute_turn(self, degrees, direction='left'):
    duration = abs(degrees) / (self.rotate_speed * self.estimated_dps)
    duration = max(self.min_duration, min(self.max_duration, duration))
    
    # 左转: rot=+speed, 右转: rot=-speed
    rot_value = self.rotate_speed if direction == 'left' else -self.rotate_speed
    
    # 关键：mode=2 (walk mode) + rot=±speed
    self.send_for_duration(mode=2, rot=rot_value, duration=duration)
    
    # 动作完成后停止
    self.send_stop()
```

## 新旧对比

### 旧版本（subprocess 方式）
```python
def _execute_forward(self, distance_m):
    # 调用外部脚本
    result = self._run_cmd(["forward", str(self.forward_speed), str(duration)])
    # 无法确保命令正确执行
```

### 新版本（直接 UDP）
```python
def _execute_forward(self, distance_m):
    # 直接发送 UDP 包
    self.send_for_duration(mode=2, fwd=self.forward_speed, duration=duration)
    self.send_stop()
    # 完全控制通信过程
```

## 测试方法

### 1. 简单测试
```bash
cd /home/nvidia/.picoclaw/workspace/navigation
python3 test_simple.py move_forward 0.1
```

### 2. 对比测试（推荐）
```bash
python3 test_compare.py
# 选择 1: 测试原始逻辑（验证 UDP 通信是否正常）
# 选择 2: 测试适配器（验证适配器是否工作）
# 选择 3: 两个都测试（完整验证）
```

### 3. 完整测试
```bash
python3 test_adapter.py --command "move_forward 0.1"
```

## 预期结果

### 如果机器人移动了
✅ 说明新的适配器工作正常！

### 如果机器人还是不动

#### 检查 1: UDP 通信是否正常
```bash
# 使用原始 aliengo_cmd.py 测试
python3 ~/.picoclaw/workspace/skills/aliengo/aliengo_cmd.py forward 0.3 2

# 如果这个也不动，说明是网络或机器人问题
```

#### 检查 2: 网络连接
```bash
ping 172.16.10.219
# 应该能 ping 通
```

#### 检查 3: 下位机状态
```bash
# 在下位机上检查 udp_bridge 是否运行
ssh mini-pc
ps aux | grep udp_bridge
```

#### 检查 4: 机器人状态
- 机器人是否已开机？
- 机器人是否处于待机模式？
- 急停按钮是否按下？

## 运动参数标定

如果机器人移动了，但距离/角度不准确，需要标定：

### 标定前进速度
```bash
# 1. 测试 5 秒前进
python3 ~/.picoclaw/workspace/skills/aliengo/aliengo_cmd.py forward 0.3 5

# 2. 测量实际前进距离（例如 2.5m）

# 3. 计算实际速度
# estimated_mps = 实际距离 / (speed * duration)
# estimated_mps = 2.5 / (0.3 * 5) = 1.67

# 4. 修改 aliengo_adapter.py 第 48 行
self.estimated_mps = 1.67  # 更新为实测值
```

### 标定转向速度
```bash
# 1. 测试 5 秒转向
python3 ~/.picoclaw/workspace/skills/aliengo/aliengo_cmd.py turn_left 0.3 5

# 2. 测量实际转向角度（例如 90°）

# 3. 计算实际角速度
# estimated_dps = 实际角度 / (speed * duration)
# estimated_dps = 90 / (0.3 * 5) = 60

# 4. 修改 aliengo_adapter.py 第 51 行
self.estimated_dps = 60  # 更新为实测值
```

## 文件清单

### 核心文件
- `aliengo_adapter.py` - 重写的适配器（直接 UDP 通信）
- `001_aliengo.py` - 使用适配器的导航程序（无需修改）

### 测试文件
- `test_simple.py` - 简单测试脚本
- `test_compare.py` - 对比测试脚本（推荐）
- `test_adapter.py` - 完整测试套件

### 文档
- `README_ALIENGO_ADAPTER_V2.md` - 本文档

## 下一步

1. **运行对比测试**
   ```bash
   python3 test_compare.py
   ```

2. **观察机器人是否移动**

3. **如果移动了**
   - 标定运动参数
   - 运行完整导航程序

4. **如果还是不动**
   - 检查网络连接
   - 检查下位机状态
   - 检查机器人状态
   - 提供详细的错误信息

## 技术支持

如果遇到问题，请提供：
1. 测试脚本的完整输出
2. 机器人的状态（开机/待机/急停）
3. 网络连接状态（ping 结果）
4. 下位机 udp_bridge 的运行状态
