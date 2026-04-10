#!/usr/bin/env python3
"""
简单测试脚本 - 直接测试 UDP 通信
"""

import sys
import time
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

from aliengo_adapter import AliengoAdapter

def main():
    print("="*60)
    print(" AliengoAdapter 简单测试")
    print("="*60)
    
    # 获取命令行参数
    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
    else:
        command = "move_forward 0.1"
    
    print(f"\n测试指令: {command}")
    print("\n⚠ 警告：即将控制真实机器人！")
    print("请确保:")
    print("  1. 机器人周围无障碍物")
    print("  2. 有人在旁监控")
    print("  3. 随时准备按急停按钮")
    
    response = input("\n继续? (yes/no): ")
    if response.lower() != 'yes':
        print("测试取消")
        return
    
    # 创建适配器
    print("\n初始化适配器...")
    adapter = AliengoAdapter()
    
    # 连接测试
    print("测试连接...")
    adapter.connect()
    time.sleep(1)
    
    # 执行指令
    print(f"\n执行指令: {command}")
    print("-" * 60)
    
    try:
        resp = adapter.send_command(command)
        print(f"响应: {resp}")
        print("\n✓ 指令执行完成")
    
    except KeyboardInterrupt:
        print("\n\n⚠ 用户中断")
    
    except Exception as e:
        print(f"\n✗ 执行失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n关闭连接...")
        adapter.close()
        print("完成")

if __name__ == '__main__':
    main()
