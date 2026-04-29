#!/usr/bin/env python3
"""
对比测试 - 验证适配器是否与原始 aliengo_cmd.py 行为一致
"""

import socket
import struct
import time
import sys

# 原始 aliengo_cmd.py 的参数
ROBOT_IP = "172.16.10.219"
ROBOT_PORT = 9090
HEADER = 0x12345678
PACK_FORMAT = '<I B 8f I'
SEND_RATE = 100  # Hz

def pack_cmd(mode, fwd=0, side=0, rot=0, height=0, pitch=0, roll=0, yaw=0, foot_raise=0):
    """打包命令（与 aliengo_cmd.py 完全一致）"""
    return struct.pack(PACK_FORMAT, HEADER, mode, fwd, side, rot, height, pitch, roll, yaw, foot_raise, 0)

def send_for_duration(sock, mode, fwd=0, side=0, rot=0, duration=2.0):
    """以 100Hz 发送命令（与 aliengo_cmd.py 完全一致）"""
    count = int(duration * SEND_RATE)
    data = pack_cmd(mode, fwd, side, rot)
    
    print(f"  发送 {count} 个包 (mode={mode}, fwd={fwd}, rot={rot})")
    
    for i in range(count):
        sock.sendto(data, (ROBOT_IP, ROBOT_PORT))
        time.sleep(1.0 / SEND_RATE)
        
        # 每 10 个包显示一次进度
        if (i + 1) % 10 == 0:
            print(f"  进度: {i+1}/{count}", end='\r')
    
    print(f"  完成: {count}/{count} 包已发送")

def send_stop(sock, duration=0.5):
    """发送停止命令"""
    send_for_duration(sock, mode=0, duration=duration)

def test_original_logic():
    """使用原始逻辑测试"""
    print("="*60)
    print(" 原始 aliengo_cmd.py 逻辑测试")
    print("="*60)
    
    print("\n⚠ 警告：即将控制真实机器人！")
    print("请确保:")
    print("  1. 机器人周围无障碍物")
    print("  2. 有人在旁监控")
    print("  3. 随时准备按急停按钮")
    
    response = input("\n继续? (yes/no): ")
    if response.lower() != 'yes':
        print("测试取消")
        return
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        print("\n[1/3] 测试停止命令 (mode=0)")
        print("-" * 60)
        send_stop(sock, duration=1.0)
        print("✓ 停止命令完成")
        time.sleep(2)
        
        print("\n[2/3] 测试前进 0.1m (mode=2, fwd=0.3, duration=0.67s)")
        print("-" * 60)
        # 0.1m / (0.3 * 0.5 m/s) = 0.67s
        send_for_duration(sock, mode=2, fwd=0.3, duration=0.67)
        send_stop(sock)
        print("✓ 前进命令完成")
        time.sleep(2)
        
        print("\n[3/3] 测试左转 15° (mode=2, rot=0.3, duration=1.75s)")
        print("-" * 60)
        # 15° / (0.3 * 28.6 deg/s) = 1.75s
        send_for_duration(sock, mode=2, rot=0.3, duration=1.75)
        send_stop(sock)
        print("✓ 转向命令完成")
        
        print("\n" + "="*60)
        print(" 所有测试完成")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\n⚠ 用户中断，发送停止...")
        send_stop(sock)
    
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        send_stop(sock)
    
    finally:
        sock.close()

def test_adapter():
    """使用适配器测试"""
    print("\n\n")
    print("="*60)
    print(" AliengoAdapter 测试")
    print("="*60)
    
    from aliengo_adapter import AliengoAdapter
    
    print("\n⚠ 警告：即将控制真实机器人！")
    response = input("\n继续? (yes/no): ")
    if response.lower() != 'yes':
        print("测试取消")
        return
    
    adapter = AliengoAdapter()
    adapter.connect()
    
    try:
        print("\n[1/3] 测试停止命令")
        print("-" * 60)
        resp = adapter.send_command("stop")
        print(f"响应: {resp}")
        time.sleep(2)
        
        print("\n[2/3] 测试前进 0.1m")
        print("-" * 60)
        resp = adapter.send_command("move_forward 0.1")
        print(f"响应: {resp}")
        time.sleep(2)
        
        print("\n[3/3] 测试左转 15°")
        print("-" * 60)
        resp = adapter.send_command("turn_left 15")
        print(f"响应: {resp}")
        
        print("\n" + "="*60)
        print(" 所有测试完成")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\n⚠ 用户中断")
    
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        adapter.close()

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--adapter':
        # 只测试适配器
        test_adapter()
    elif len(sys.argv) > 1 and sys.argv[1] == '--original':
        # 只测试原始逻辑
        test_original_logic()
    else:
        # 两个都测试
        print("选择测试模式:")
        print("  1. 原始 aliengo_cmd.py 逻辑")
        print("  2. AliengoAdapter")
        print("  3. 两个都测试")
        
        choice = input("\n选择 (1/2/3): ")
        
        if choice == '1':
            test_original_logic()
        elif choice == '2':
            test_adapter()
        elif choice == '3':
            test_original_logic()
            test_adapter()
        else:
            print("无效选择")

if __name__ == '__main__':
    main()
