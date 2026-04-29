#!/usr/bin/env python3
"""
诊断脚本 - 检查所有可能的问题
"""

import socket
import struct
import subprocess
import time
import sys

ROBOT_IP = "172.16.10.219"
ROBOT_PORT = 9090

def print_section(title):
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def check_network():
    """检查网络连接"""
    print_section("1. 网络连接检查")
    
    print(f"\n检查是否能 ping 通 {ROBOT_IP}...")
    result = subprocess.run(
        ['ping', '-c', '3', '-W', '2', ROBOT_IP],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print(f"✓ {ROBOT_IP} 可达")
        # 提取延迟信息
        for line in result.stdout.split('\n'):
            if 'time=' in line:
                print(f"  {line.strip()}")
        return True
    else:
        print(f"✗ {ROBOT_IP} 不可达")
        print("  可能原因:")
        print("  - 下位机未开机")
        print("  - 网络未连接")
        print("  - IP 地址错误")
        return False

def check_udp_port():
    """检查 UDP 端口"""
    print_section("2. UDP 端口检查")
    
    print(f"\n尝试发送测试包到 {ROBOT_IP}:{ROBOT_PORT}...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2.0)
        
        # 发送测试包
        test_data = b"TEST"
        sock.sendto(test_data, (ROBOT_IP, ROBOT_PORT))
        print("✓ UDP 包发送成功")
        
        sock.close()
        return True
    
    except socket.timeout:
        print("✗ 发送超时")
        return False
    
    except Exception as e:
        print(f"✗ 发送失败: {e}")
        return False

def check_aliengo_cmd():
    """检查原始 aliengo_cmd.py 是否工作"""
    print_section("3. 原始 aliengo_cmd.py 检查")
    
    cmd_path = "/home/nvidia/.picoclaw/workspace/skills/aliengo/aliengo_cmd.py"
    
    print(f"\n检查脚本是否存在: {cmd_path}")
    import os
    if not os.path.exists(cmd_path):
        print(f"✗ 脚本不存在")
        return False
    
    print("✓ 脚本存在")
    
    print("\n测试 status 命令...")
    result = subprocess.run(
        ['python3', cmd_path, 'status'],
        capture_output=True,
        text=True,
        timeout=5
    )
    
    print(result.stdout)
    if result.stderr:
        print("错误输出:", result.stderr)
    
    return result.returncode == 0

def test_udp_communication():
    """测试 UDP 通信（发送实际控制包）"""
    print_section("4. UDP 控制包测试")
    
    print("\n⚠ 警告：即将发送控制包到机器人")
    print("这会尝试让机器人进入停止模式")
    
    response = input("\n继续? (yes/no): ")
    if response.lower() != 'yes':
        print("跳过")
        return None
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # 打包停止命令 (mode=0)
        HEADER = 0x12345678
        PACK_FORMAT = '<I B 8f I'
        data = struct.pack(PACK_FORMAT, HEADER, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        
        print("\n发送 10 个停止命令包...")
        for i in range(10):
            sock.sendto(data, (ROBOT_IP, ROBOT_PORT))
            time.sleep(0.01)  # 10ms
            print(f"  发送: {i+1}/10", end='\r')
        
        print("\n✓ 控制包发送完成")
        
        sock.close()
        return True
    
    except Exception as e:
        print(f"\n✗ 发送失败: {e}")
        return False

def test_movement():
    """测试实际移动"""
    print_section("5. 实际移动测试")
    
    print("\n⚠ 警告：即将尝试让机器人前进 0.1m")
    print("请确保:")
    print("  1. 机器人周围无障碍物")
    print("  2. 有人在旁监控")
    print("  3. 随时准备按急停按钮")
    
    response = input("\n继续? (yes/no): ")
    if response.lower() != 'yes':
        print("跳过")
        return None
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        HEADER = 0x12345678
        PACK_FORMAT = '<I B 8f I'
        SEND_RATE = 100
        
        # 前进命令: mode=2, fwd=0.3
        print("\n发送前进命令 (0.67秒, 67个包)...")
        duration = 0.67
        count = int(duration * SEND_RATE)
        
        data = struct.pack(PACK_FORMAT, HEADER, 2, 0.3, 0, 0, 0, 0, 0, 0, 0, 0)
        
        for i in range(count):
            sock.sendto(data, (ROBOT_IP, ROBOT_PORT))
            time.sleep(1.0 / SEND_RATE)
            if (i + 1) % 10 == 0:
                print(f"  进度: {i+1}/{count}", end='\r')
        
        print(f"\n✓ 前进命令发送完成")
        
        # 发送停止命令
        print("\n发送停止命令...")
        stop_data = struct.pack(PACK_FORMAT, HEADER, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        for i in range(50):
            sock.sendto(stop_data, (ROBOT_IP, ROBOT_PORT))
            time.sleep(0.01)
        
        print("✓ 停止命令发送完成")
        
        sock.close()
        
        print("\n" + "-"*60)
        print("机器人是否移动了？")
        response = input("(yes/no): ")
        
        if response.lower() == 'yes':
            print("\n✓ 机器人移动正常！")
            print("  适配器应该可以正常工作")
            return True
        else:
            print("\n✗ 机器人没有移动")
            print("  可能原因:")
            print("  - 机器人未开机或未进入待机模式")
            print("  - 急停按钮被按下")
            print("  - 下位机 udp_bridge 未运行")
            print("  - 机器人电量不足")
            return False
    
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*60)
    print(" Aliengo 机器人诊断工具")
    print("="*60)
    
    results = {}
    
    # 1. 网络检查
    results['network'] = check_network()
    
    if not results['network']:
        print("\n" + "!"*60)
        print(" 网络不通，无法继续诊断")
        print("!"*60)
        print("\n请检查:")
        print("  1. 下位机是否开机")
        print("  2. 网络线是否连接")
        print("  3. IP 地址是否正确 (172.16.10.219)")
        return 1
    
    # 2. UDP 端口检查
    results['udp_port'] = check_udp_port()
    
    # 3. aliengo_cmd.py 检查
    results['aliengo_cmd'] = check_aliengo_cmd()
    
    # 4. UDP 通信测试
    results['udp_comm'] = test_udp_communication()
    
    # 5. 移动测试
    if results['udp_comm']:
        results['movement'] = test_movement()
    
    # 汇总结果
    print_section("诊断结果汇总")
    
    print("\n检查项目:")
    for key, value in results.items():
        if value is True:
            status = "✓ 通过"
        elif value is False:
            status = "✗ 失败"
        else:
            status = "- 跳过"
        
        name = {
            'network': '网络连接',
            'udp_port': 'UDP 端口',
            'aliengo_cmd': 'aliengo_cmd.py',
            'udp_comm': 'UDP 通信',
            'movement': '实际移动'
        }.get(key, key)
        
        print(f"  {name:20} {status}")
    
    print("\n" + "="*60)
    
    if results.get('movement') == True:
        print("\n✓ 所有测试通过！")
        print("  适配器应该可以正常工作")
        print("\n下一步:")
        print("  python3 test_simple.py move_forward 0.1")
        return 0
    
    elif results.get('movement') == False:
        print("\n✗ 机器人没有移动")
        print("\n可能的问题:")
        print("  1. 机器人未开机或未进入待机模式")
        print("  2. 急停按钮被按下")
        print("  3. 下位机 udp_bridge 未运行")
        print("  4. 机器人电量不足")
        print("\n建议:")
        print("  1. 检查机器人状态指示灯")
        print("  2. 检查急停按钮")
        print("  3. SSH 到下位机检查 udp_bridge:")
        print("     ssh mini-pc")
        print("     ps aux | grep udp_bridge")
        return 1
    
    else:
        print("\n⚠ 部分测试未完成")
        return 1

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
