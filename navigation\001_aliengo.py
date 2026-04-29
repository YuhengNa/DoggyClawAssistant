import torch
import numpy as np
import re
import time
import logging
import pyrealsense2 as rs
import cv2
from PIL import Image as PILImage
from llava.constants import IMAGE_TOKEN_INDEX
from llava.conversation import conv_templates, SeparatorStyle
from llava.mm_utils import process_images, tokenizer_image_token, KeywordsStoppingCriteria
from llava.model.builder import load_pretrained_model
from aliengo_adapter import AliengoAdapter as UpperClient

# 初始化日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


class MockRL:
    # 修正1：通过构造函数接收client并保存为实例变豆包量
    def __init__(self, client):
        self.client = client  # 保存client引用
        logging.info("[MockRL初始化] 已获取UpperClient实例")

    def execute(self, command):
        """模拟执行动作，接收标准化指令字符串"""
        logging.info(f"[动作执行] 开始执行指令: {command}")
        start_time = time.time()

        # 修正2：使用实例变量self.client而非全局变量
        resp = self.client.send_command(command)  # 补充resp的赋值
        
        elapsed = time.time() - start_time
        
        # 修正3：修复resp判断逻辑和stop()调用方式
        if "in stance" not in resp and "stance finished" not in resp and "standing" not in resp:
            self.stop()  # 调用实例方法需加self
        else:
            logging.info(f"[动作执行] 指令执行完成，耗时: {elapsed:.2f}秒")

        return True

    def stop(self):
        """模拟停止机器人，打印停止信息"""
        # 修正4：使用实例变量self.client
        self.client.send_command("stance")
        logging.info("[机器人控制] 模拟停止机器人")


class NaVILARobotDeploy:
    # 修正5：接收client参数并传递给控制器
    def __init__(self, client):
        logging.info("===== 开始初始化导航系统 =====")

        # 保存client引用
        self.client = client
        logging.info("[系统初始化] 已接收UpperClient实例")

        # 初始化参数
        self.model_path = "/media/nvidia/ESD-USB/model"
        self.model_name = "navila-llama3-8b-8f"
        self.instruction_sequence = [
            "Navigate to the white table and stop in front of it",
        ]
        logging.info(f"[参数初始化] 导航任务列表: {self.instruction_sequence}")

        # 图像获取失败计数参数
        self.max_consecutive_failures = 10
        self.consecutive_fail_count = 0
        logging.info(f"[参数初始化] 图像最大连续失败次数: {self.max_consecutive_failures}")

        # 内部变量初始化
        self.current_image = None
        self.current_instruction_idx = 0
        self.queue_actions = []  # 队列存储标准化指令字符串
        logging.info("[变量初始化] 指令队列和内部状态已重置")

        # 初始化模拟RL控制器（修正6：传递client参数）
        logging.info("[控制器初始化] 开始初始化Mock RL控制器...")
        self.rl_controller = MockRL(client)  # 将client传入控制器
        logging.info("[控制器初始化] Mock RL控制器初始化完成")

        # 加载模型
        logging.info(f"[模型加载] 开始加载模型: {self.model_path}...")
        start_time = time.time()
        self.tokenizer, self.model, self.image_processor, _ = load_pretrained_model(
            self.model_path, self.model_name
        )
        self.model = self.model.cuda() if torch.cuda.is_available() else self.model
        elapsed = time.time() - start_time
        logging.info(
            f"[模型加载] 模型加载完成，耗时: {elapsed:.2f}秒 (设备: {'GPU' if torch.cuda.is_available() else 'CPU'})")

        # 初始化RealSense相机
        logging.info("[相机初始化] 开始初始化RealSense相机...")
        self.ctx = rs.context()
        if len(self.ctx.devices) == 0:
            raise Exception("No RealSense device detected!")
        self.pipeline = rs.pipeline()
        self.config = rs.config()
        self.config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        self.pipeline.start(self.config)
        logging.info("[相机初始化] RealSense相机初始化成功 (分辨率: 640×480)")

        logging.info("===== 导航系统初始化完成 =====")

    def get_realsense_image(self):
        """从RealSense相机获取图像并转换为PIL格式"""
        start_time = time.time()
        try:
            frames = self.pipeline.wait_for_frames()
            color_frame = frames.get_color_frame()
            if not color_frame:
                logging.warning("[图像采集] 未获取到有效彩色图像帧")
                return None

            color_image = np.asanyarray(color_frame.get_data())
            rgb_image = cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB)
            pil_image = PILImage.fromarray(rgb_image).convert("RGB")
            elapsed = time.time() - start_time
            logging.info(
                f"[图像采集] 成功获取图像 (尺寸: {pil_image.size[0]}×{pil_image.size[1]}px, 耗时: {elapsed:.2f}秒)")
            return pil_image
        except Exception as e:
            elapsed = time.time() - start_time
            logging.error(f"[图像采集] 获取图像失败 (耗时: {elapsed:.2f}秒)，错误: {str(e)}")
            return None

    def sample_and_pad_images(self, images, num_frames=8, width=512, height=512):
        """处理图像序列：历史帧不足时复制最新帧填充"""
        logging.info(f"[图像处理] 开始处理图像序列 (原始帧数: {len(images)}, 目标帧数: {num_frames})")
        start_time = time.time()

        frames = images.copy()
        if len(frames) < num_frames:
            latest_frame = frames[-1] if frames else PILImage.new("RGB", (width, height), color=(0, 0, 0))
            while len(frames) < num_frames:
                frames.append(latest_frame.copy())
            logging.info(f"[图像处理] 图像帧不足，填充至{num_frames}帧")

        latest_frame = frames[-1]
        sampled_indices = np.linspace(0, len(frames) - 1, num=num_frames - 1, endpoint=False, dtype=int)
        result = [frames[i] for i in sampled_indices] + [latest_frame]

        elapsed = time.time() - start_time
        logging.info(f"[图像处理] 图像序列处理完成 (耗时: {elapsed:.2f}秒)")
        return result

    def generate_model_prompt(self, instruction, past_frames):
        """构建模型输入提示词"""
        logging.info(f"[提示词生成] 开始构建模型输入提示词 (历史帧数: {len(past_frames)})")
        interleaved_images = "<image>\n" * (len(past_frames) - 1)
        question = (
            f"Imagine you are a robot programmed for navigation tasks. You have been given a video "
            f'of historical observations {interleaved_images}, and current observation <image>\n. Your assigned task is: "{instruction}" '
            f"Analyze this series of images to decide your next action, which could be turning left or right by a specific "
            f"degree, moving forward a certain distance, or stop if the task is completed."
        )
        conv = conv_templates["llama_3"].copy()
        conv.append_message(conv.roles[0], question)
        conv.append_message(conv.roles[1], None)
        prompt, stop_str = conv.get_prompt(), conv.sep if conv.sep_style != SeparatorStyle.TWO else conv.sep2
        logging.info("[提示词生成] 模型输入提示词构建完成")
        return prompt, stop_str

    def parse_model_output(self, output_str):
        """解析模型输出并生成标准化指令字符串（小写+下划线+米单位）"""
        logging.info(f"[指令解析] 开始解析模型输出: {output_str}")
        patterns = {
            0: re.compile(r"\bstop\b", re.IGNORECASE),  # 停止
            1: re.compile(r"\bmove forward\b", re.IGNORECASE),  # 前进
            2: re.compile(r"\bturn left\b", re.IGNORECASE),  # 左转
            3: re.compile(r"\bturn right\b", re.IGNORECASE),  # 右转
        }

        for action_id, pattern in patterns.items():
            if pattern.search(output_str):
                if action_id == 1:  # 前进
                    match = re.search(r"(\d+) cm", output_str)
                    total_distance_cm = int(match.group(1)) if match else 25
                    step_cm = 25
                    num_steps = (total_distance_cm + step_cm - 1) // step_cm

                    for i in range(num_steps):
                        distance_cm = step_cm if i < num_steps - 1 else total_distance_cm - i * step_cm
                        distance_m = distance_cm / 100.0
                        self.queue_actions.append(f"move_forward {distance_m:.2f}")

                    logging.info(f"[指令解析] 解析为前进动作 (总距离: {total_distance_cm}cm, 拆解为{num_steps}条指令)")
                    return action_id, {"distance_cm": total_distance_cm}

                elif action_id == 2:  # 左转
                    match = re.search(r"(\d+) degree", output_str)
                    total_degree = int(match.group(1)) if match else 15
                    step_degree = 15
                    num_steps = (total_degree + step_degree - 1) // step_degree

                    for i in range(num_steps):
                        degree = step_degree if i < num_steps - 1 else total_degree - i * step_degree
                        self.queue_actions.append(f"turn_left {degree}")

                    logging.info(f"[指令解析] 解析为左转动作 (总角度: {total_degree}度, 拆解为{num_steps}条指令)")
                    return action_id, {"degree": total_degree}

                elif action_id == 3:  # 右转
                    match = re.search(r"(\d+) degree", output_str)
                    total_degree = int(match.group(1)) if match else 15
                    step_degree = 15
                    num_steps = (total_degree + step_degree - 1) // step_degree

                    for i in range(num_steps):
                        degree = step_degree if i < num_steps - 1 else total_degree - i * step_degree
                        self.queue_actions.append(f"turn_right {degree}")

                    logging.info(f"[指令解析] 解析为右转动作 (总角度: {total_degree}度, 拆解为{num_steps}条指令)")
                    return action_id, {"degree": total_degree}

                else:  # 停止
                    self.queue_actions.append("stop")
                    logging.info(f"[指令解析] 解析为停止动作")
                    return action_id, {}

        # 解析失败默认处理
        logging.warning(f"[指令解析] 无法解析动作，使用默认前进25cm")
        self.queue_actions.append("move_forward 0.25")
        return 1, {"distance_cm": 25}

    def execute_action(self, command):
        """将标准化指令字符串传递给模拟RL类执行"""
        logging.info(f"[指令发送] 向控制器发送指令: {command}")
        try:
            start_time = time.time()
            success = self.rl_controller.execute(command)
            elapsed = time.time() - start_time

            if success:
                logging.info(f"[指令发送] 指令执行成功 (总耗时: {elapsed:.2f}秒)")
                return True
            else:
                logging.error(f"[指令发送] 控制器返回执行失败 (总耗时: {elapsed:.2f}秒)")
                return False

        except Exception as e:
            logging.error(f"[指令发送] 调用控制器时发生错误: {str(e)}")
            return False

    def run(self):
        """主循环：处理队列中的指令"""
        past_frames = []
        logging.info("===== 开始执行导航主循环 =====")
        try:
            loop_count = 0  # 循环计数器
            while self.current_instruction_idx < len(self.instruction_sequence):
                loop_count += 1
                logging.info(f"\n===== 主循环迭代 {loop_count} =====")
                logging.info(
                    f"[循环状态] 当前任务索引: {self.current_instruction_idx}/{len(self.instruction_sequence) - 1}, 指令队列长度: {len(self.queue_actions)}")

                # 从RealSense获取图像
                logging.info("[循环步骤] 开始采集图像...")
                self.current_image = self.get_realsense_image()

                # 处理图像获取失败的情况
                if self.current_image is None:
                    self.consecutive_fail_count += 1
                    logging.warning(
                        f"[循环状态] 图像采集失败，连续失败次数: {self.consecutive_fail_count}/{self.max_consecutive_failures}")

                    if self.consecutive_fail_count >= self.max_consecutive_failures:
                        logging.critical(f"[循环终止] 已连续{self.max_consecutive_failures}次获取图像失败，程序将退出")
                        break

                    logging.info("[循环步骤] 跳过本次迭代，等待下一次图像采集")
                    continue
                else:
                    self.consecutive_fail_count = 0
                    logging.info("[循环状态] 图像采集成功，继续处理")

                current_instruction = self.instruction_sequence[self.current_instruction_idx]
                logging.info(f"[循环状态] 当前执行任务: {current_instruction}")

                # 处理指令队列
                if self.queue_actions:
                    logging.info(f"[循环步骤] 指令队列非空，准备执行指令 (剩余{len(self.queue_actions)}条)")
                    command = self.queue_actions.pop(0)
                    self.execute_action(command)

                    # 执行完更新历史帧
                    past_frames.append(self.current_image)
                    logging.info(f"[循环状态] 历史帧已更新，当前累计: {len(past_frames)}帧")

                    # 若队列空且当前是停止指令，标记指令完成
                    if command == "stop" and not self.queue_actions:
                        logging.info(f"[循环状态] 停止指令执行完成，当前任务已完成")
                        self.current_instruction_idx += 1
                        past_frames = []
                        logging.info(
                            f"[循环状态] 重置历史帧，准备执行下一个任务 (新任务索引: {self.current_instruction_idx})")

                    logging.info(f"[循环步骤] 本次迭代完成，准备进入下一次循环")
                    continue

                # 队列空时生成新指令
                logging.info(f"[循环步骤] 指令队列为空，开始生成新指令...")
                past_frames.append(self.current_image)
                logging.info(f"[循环状态] 历史帧已更新，当前累计: {len(past_frames)}帧")

                num_video_frames = self.model.config.num_video_frames
                processed_frames = self.sample_and_pad_images(past_frames, num_frames=num_video_frames)

                prompt, stop_str = self.generate_model_prompt(current_instruction, processed_frames)

                logging.info("[模型推理] 开始准备模型输入数据...")
                start_time = time.time()
                images_tensor = process_images(processed_frames, self.image_processor, self.model.config).to(
                    self.model.device, dtype=torch.float16
                )
                input_ids = tokenizer_image_token(
                    prompt, self.tokenizer, IMAGE_TOKEN_INDEX, return_tensors="pt"
                ).unsqueeze(0).to(self.model.device)
                stopping_criteria = KeywordsStoppingCriteria([stop_str], self.tokenizer, input_ids)
                elapsed = time.time() - start_time
                logging.info(f"[模型推理] 输入数据准备完成 (耗时: {elapsed:.2f}秒)")

                logging.info("[模型推理] 开始模型推理...")
                start_time = time.time()
                with torch.no_grad():
                    output_ids = self.model.generate(
                        input_ids,
                        images=images_tensor,
                        do_sample=False,
                        temperature=0.0,
                        max_new_tokens=32,
                        stopping_criteria=[stopping_criteria],
                        pad_token_id=self.tokenizer.eos_token_id
                    )
                elapsed = time.time() - start_time
                output_str = self.tokenizer.decode(output_ids[0], skip_special_tokens=True).strip()
                logging.info(f"[模型推理] 推理完成 (耗时: {elapsed:.2f}秒)")
                logging.info("===== 模型原始输出开始 =====")
                logging.info(output_str)
                logging.info("===== 模型原始输出结束 =====")

                self.parse_model_output(output_str)
                logging.info(f"[循环步骤] 新指令生成完成，当前队列长度: {len(self.queue_actions)}")

        except KeyboardInterrupt:
            logging.info("[程序中断] 用户触发中断 (Ctrl+C)")
        finally:
            logging.info("\n===== 开始释放资源 =====")
            # 停止RealSense相机
            self.pipeline.stop()
            logging.info("[资源释放] RealSense相机已停止")
            self.rl_controller.stop()
            logging.info("[资源释放] 机器人控制器已停止")
            logging.info("===== 导航程序已结束 =====")


if __name__ == "__main__":
    try:
        logging.info("===== 启动导航程序 =====")
        # 修正7：先初始化client并连接（使用 AliengoAdapter）
        logging.info("[主程序] 初始化AliengoAdapter...")
        client = UpperClient()  # AliengoAdapter 不需要 IP 参数
        client.connect()
        logging.info("[主程序] AliengoAdapter连接成功")

        # 修正8：将client传入导航系统
        deployer = NaVILARobotDeploy(client)
        deployer.run()

    except Exception as e:
        logging.critical(f"[初始化失败] 程序初始化过程中发生错误: {str(e)}", exc_info=True)
    finally:
        # 修正9：确保client资源正确释放
        if 'client' in locals():
            try:
                client.close()
                logging.info("[主程序] AliengoAdapter已关闭")
            except Exception as e:
                logging.warning(f"[主程序] 关闭AliengoAdapter时发生错误: {str(e)}")