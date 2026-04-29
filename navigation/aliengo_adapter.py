#!/usr/bin/env python3
"""
aliengo_adapter.py — NaVILA 指令到 Aliengo UDP 控制的适配器

完全按照 aliengo_cmd.py 的逻辑实现，直接发送 UDP 包到机器人
"""

import socket
import struct
import logging
import time


class AliengoAdapter:
    """
    适配器类，模拟 UpperClient 接口，直接发送 UDP 控制包
    完全复制 aliengo_cmd.py 的通信逻辑
    """
    
    # UDP 通信参数（与 aliengo_cmd.py 完全一致）
    ROBOT_IP = "172.16.10.219"
    ROBOT_PORT = 9090
    HEADER = 0x12345678
    PACK_FORMAT = '<I B 8f I'  # header, mode, fwd, side, rot, height, pitch, roll, yaw, footRaise, reserved
    SEND_RATE = 100  # Hz - 每秒发送 100 次
    
    def __init__(self, server_ip=None, server_port=None):
        """
        初始化适配器
        
        Args:
            server_ip: 兼容参数（忽略，使用硬编码的 172.16.10.219）
            server_port: 兼容参数（忽略，使用硬编码的 9090）
        """
        # 创建 UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # 运动参数（用于计算持续时间）
        self.forward_speed = 0.3        # 前进速度（归一化 0-1）
        self.estimated_mps = 0.5        # 实测: speed=0.3 时约 0.5 m/s
        
        self.rotate_speed = 0.3         # 转向速度（归一化 0-1）
        self.estimated_dps = 28.6       # 实测: speed=0.3 时约 28.6 deg/s
        
        # 安全参数
        self.min_duration = 0.5         # 最小持续时间（秒）
        self.max_duration = 10.0        # 最大持续时间（秒）
        
        logging.info(f"[AliengoAdapter] 初始化完成")
        logging.info(f"[AliengoAdapter] 目标: {self.ROBOT_IP}:{self.ROBOT_PORT}")
        logging.info(f"[AliengoAdapter] 运动参数: fwd_speed={self.forward_speed}, "
                     f"est_mps={self.estimated_mps}, rot_speed={self.rotate_speed}, "
                     f"est_dps={self.estimated_dps}")
    
    def pack_cmd(self, mode, fwd=0, side=0, rot=0, height=0, pitch=0, roll=0, yaw=0, foot_raise=0):
        """
        打包控制命令（与 aliengo_cmd.py 完全一致）
        
        Args:
            mode: 0=idle, 1=stand, 2=walk
            fwd: 前进速度 [-1, 1]
            side: 侧移速度 [-1, 1]
            rot: 转向速度 [-1, 1]
            其他参数: 姿态控制
        
        Returns:
            bytes: 打包后的二进制数据
        """
        return struct.pack(
            self.PACK_FORMAT,
            self.HEADER, mode, fwd, side, rot, height, pitch, roll, yaw, foot_raise, 0
        )
    
    def send_for_duration(self, mode, fwd=0, side=0, rot=0, height=0, pitch=0, roll=0, yaw=0, duration=2.0):
        """
        以 100Hz 频率持续发送命令（与 aliengo_cmd.py 完全一致）
        
        这是关键！机器人需要持续接收命令才会移动
        """
        count = int(duration * self.SEND_RATE)
        data = self.pack_cmd(mode, fwd, side, rot, height, pitch, roll, yaw)
        
        logging.debug(f"[AliengoAdapter] 发送 {count} 个包 (mode={mode}, fwd={fwd}, side={side}, rot={rot})")
        
        for i in range(count):
            self.sock.sendto(data, (self.ROBOT_IP, self.ROBOT_PORT))
            time.sleep(1.0 / self.SEND_RATE)  # 10ms 间隔
    
    def send_stop(self, duration=0.5):
        """
        发送停止命令（mode=0）
        """
        self.send_for_duration(mode=0, duration=duration)
    
    def connect(self):
        """
        模拟连接（兼容接口）
        测试 UDP 连通性
        """
        logging.info("[AliengoAdapter] 测试连接...")
        try:
            # 发送一个测试包
            data = self.pack_cmd(0)
            self.sock.sendto(data, (self.ROBOT_IP, self.ROBOT_PORT))
            logging.info("[AliengoAdapter] 连接测试成功")
        except Exception as e:
            logging.error(f"[AliengoAdapter] 连接测试失败: {e}")
    
    def close(self):
        """
        关闭连接，发送停止命令确保安全
        """
        logging.info("[AliengoAdapter] 关闭连接，发送停止命令...")
        try:
            self.send_stop(duration=1.0)
            logging.info("[AliengoAdapter] 已发送停止命令")
        except Exception as e:
            logging.warning(f"[AliengoAdapter] 发送停止命令失败: {e}")
        finally:
            self.sock.close()
    
    def send_command(self, command):
        """
        发送指令（主接口）
        
        Args:
            command: NaVILA 格式的指令字符串
                    如 "move_forward 0.25", "turn_left 15", "stop"
        
        Returns:
            str: 状态字符串
                "in stance" - 停止/站立
                "stance finished" - 动作完成
                "error: ..." - 错误信息
        """
        command = command.strip().lower()
        logging.info(f"[AliengoAdapter] 收到指令: {command}")
        
        try:
            if command == "stance" or command == "stop":
                return self._execute_stop()
            
            elif command.startswith("move_forward"):
                parts = command.split()
                distance_m = float(parts[1]) if len(parts) > 1 else 0.25
                return self._execute_forward(distance_m)
            
            elif command.startswith("turn_left"):
                parts = command.split()
                degrees = float(parts[1]) if len(parts) > 1 else 15
                return self._execute_turn(degrees, direction='left')
            
            elif command.startswith("turn_right"):
                parts = command.split()
                degrees = float(parts[1]) if len(parts) > 1 else 15
                return self._execute_turn(degrees, direction='right')
            
            else:
                logging.warning(f"[AliengoAdapter] 未知指令: {command}，执行停止")
                return self._execute_stop()
        
        except Exception as e:
            logging.error(f"[AliengoAdapter] 指令执行异常: {e}")
            # 异常时紧急停止
            try:
                self.send_stop()
            except:
                pass
            return f"error: {e}"
    
    # ===== 内部执行方法 =====
    
    def _execute_stop(self):
        """执行停止"""
        logging.info("[AliengoAdapter] 执行: stop")
        self.send_stop(duration=1.0)
        logging.info("[AliengoAdapter] 停止完成")
        return "in stance"
    
    def _execute_forward(self, distance_m):
        """
        执行前进（完全按照 aliengo_cmd.py 的 forward 逻辑）
        
        Args:
            distance_m: 前进距离（米）
        """
        # 计算持续时间
        duration = distance_m / (self.forward_speed * self.estimated_mps)
        duration = max(self.min_duration, min(self.max_duration, duration))
        
        logging.info(f"[AliengoAdapter] 执行: 前进 {distance_m:.2f}m "
                     f"(speed={self.forward_speed}, duration={duration:.2f}s)")
        
        # 关键：mode=2 (walk mode) + fwd=speed
        self.send_for_duration(mode=2, fwd=self.forward_speed, duration=duration)
        
        # 动作完成后停止
        self.send_stop()
        
        logging.info(f"[AliengoAdapter] 前进完成")
        return "stance finished"
    
    def _execute_turn(self, degrees, direction='left'):
        """
        执行转向（完全按照 aliengo_cmd.py 的 turn_left/turn_right 逻辑）
        
        Args:
            degrees: 转向角度（度）
            direction: 'left' 或 'right'
        """
        # 计算持续时间
        duration = abs(degrees) / (self.rotate_speed * self.estimated_dps)
        duration = max(self.min_duration, min(self.max_duration, duration))
        
        # 左转: rot=+speed, 右转: rot=-speed
        rot_value = self.rotate_speed if direction == 'left' else -self.rotate_speed
        
        logging.info(f"[AliengoAdapter] 执行: {direction}转 {degrees:.0f}° "
                     f"(speed={self.rotate_speed}, duration={duration:.2f}s)")
        
        # 关键：mode=2 (walk mode) + rot=±speed
        self.send_for_duration(mode=2, rot=rot_value, duration=duration)
        
        # 动作完成后停止
        self.send_stop()
        
        logging.info(f"[AliengoAdapter] 转向完成")
        return "stance finished"


# ===== 向后兼容别名 =====
UpperClient = AliengoAdapter


# ===== 测试代码 =====
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 60)
    print(" AliengoAdapter UDP 直接控制测试")
    print("=" * 60)
    
    client = UpperClient()
    client.connect()
    
    try:
        print("\n--- 测试 stance ---")
        resp = client.send_command("stance")
        print(f"响应: {resp}")
        time.sleep(1)
        
        print("\n--- 测试 move_forward 0.1 ---")
        resp = client.send_command("move_forward 0.1")
        print(f"响应: {resp}")
        time.sleep(1)
        
        print("\n--- 测试 turn_left 15 ---")
        resp = client.send_command("turn_left 15")
        print(f"响应: {resp}")
        time.sleep(1)
        
        print("\n--- 测试 stop ---")
        resp = client.send_command("stop")
        print(f"响应: {resp}")
        
    except KeyboardInterrupt:
        print("\n中断")
    finally:
        client.close()
        print("\n测试完成")
