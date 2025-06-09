import json
import os
import requests
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import re
from background_layer_filter_agent import BackgroundLayerFilterAgent
from qwen_agent.agents import Assistant
import dashscope

# 设置API密钥
dashscope.api_key = ""

class BackgroundImageGenerator:
    """专门用于根据背景层内容生成背景图像的Agent"""
    
    def __init__(self, layer_type: str = "背景层", output_dir: str = None):
        # 设置图层类型
        self.layer_type = layer_type
        
        # 如果没有指定输出目录，根据图层类型生成
        if output_dir is None:
            output_dir = f"generated_{layer_type.replace('层', '')}_images"
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.filter_agent = BackgroundLayerFilterAgent()
        
        # 设置过滤器的图层类型
        self.filter_agent.set_layer_type(layer_type)
        
        # 初始化用于提取尺寸的Agent
        self.size_extractor = Assistant(
            llm={'model': 'qwen-max'},
            name='尺寸提取专家',
            description='专门从设计内容中提取图像尺寸信息'
        )
        
        # 初始化用于提取提示词的Agent
        self.prompt_extractor = Assistant(
            llm={'model': 'qwen-max'},
            name='提示词提取专家',
            description='专门从设计内容中提取图像生成提示词'
        )
        
        # 初始化用于提取文件名的Agent
        self.filename_extractor = Assistant(
            llm={'model': 'qwen-max'},
            name='文件名提取专家',
            description='专门从设计内容中提取输出文件名信息'
        )
        
    def extract_filename_with_agent(self, background_content: str) -> str:
        """使用Qwen Agent智能提取文件名"""
        filename_prompt = """
你是一个文件名提取专家，需要从设计内容中提取输出文件名信息。

请从以下内容中提取 "output" 字段中的文件名，通常格式如下：
"output": ["background.png"]
或
"output": ["filename.png", "another.jpg"]

注意事项：
1. 优先查找 JSON 格式中的 "output" 字段
2. 提取第一个文件名（通常是主要输出文件）
3. 如果找不到明确的文件名，根据内容类型生成合适的文件名
4. 背景类设计建议使用 "background.png"
5. 只返回文件名，不要包含路径
6. 不要包含任何其他文字说明
7. 确保文件名包含适当的扩展名（.png, .jpg等）
        """.strip()
        
        messages = [
            {'role': 'system', 'content': filename_prompt},
            {'role': 'user', 'content': background_content}
        ]
        
        try:
            response_generator = self.filename_extractor.run(messages)
            responses = []
            for response in response_generator:
                responses.extend(response)
            
            for msg in reversed(responses):
                if msg.get('role') == 'assistant':
                    filename = msg.get('content', '').strip()
                    # 清理文件名，移除引号和多余字符
                    filename = re.sub(r'["\[\]\s]', '', filename)
                    # 确保有扩展名
                    if filename and not filename.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        filename += '.png'
                    if filename:
                        print(f"Agent提取的文件名: {filename}")
                        return filename
            
            # 如果提取失败，返回默认文件名
            print("Agent文件名提取失败，使用默认文件名")
            return "background.png"
            
        except Exception as e:
            print(f"文件名提取失败: {e}，使用默认文件名")
            return "background.png"
    
    def extract_filename_from_background_content(self, background_content: str) -> str:
        """从背景层内容中提取文件名（包含Agent方法和备用方法）"""
        try:
            # 优先使用Agent提取
            return self.extract_filename_with_agent(background_content)
            
        except Exception as e:
            print(f"Agent提取失败，使用传统方法: {e}")
            
            # 备用的传统提取方法
            try:
                # 尝试解析JSON格式的内容
                if '{' in background_content and '}' in background_content:
                    # 查找output字段
                    output_match = re.search(r'"output"\s*:\s*\[([^\]]+)\]', background_content)
                    if output_match:
                        output_content = output_match.group(1)
                        # 提取第一个文件名
                        filename_match = re.search(r'"([^"]+\.(png|jpg|jpeg|gif|svg))"', output_content)
                        if filename_match:
                            return filename_match.group(1)
                
                # 如果没有找到JSON格式，使用默认文件名
                return "background.png"
                
            except Exception as e:
                print(f"传统提取方法也失败: {e}")
                return "background.png"
    
    def extract_image_size_with_agent(self, background_content: str) -> Tuple[int, int]:
        """使用Qwen Agent智能提取图像尺寸"""
        size_prompt = """
你是一个尺寸提取专家，需要从设计内容中提取图像的宽度和高度信息。

请从以下内容中提取图像尺寸信息，返回格式为：宽度,高度

注意事项：
1. 优先查找明确的尺寸数字（如1200x600、1024*768等）
2. 如果没有明确尺寸，根据设计类型推断合适尺寸
3. 横幅类设计建议1200x600
4. 背景类设计建议1024x768
5. 只返回数字格式：宽度,高度
6. 不要包含任何其他文字说明
        """.strip()
        
        messages = [
            {'role': 'system', 'content': size_prompt},
            {'role': 'user', 'content': background_content}
        ]
        
        try:
            response_generator = self.size_extractor.run(messages)
            responses = []
            for response in response_generator:
                responses.extend(response)
            
            for msg in reversed(responses):
                if msg.get('role') == 'assistant':
                    size_text = msg.get('content', '').strip()
                    # 解析尺寸
                    size_match = re.search(r'(\d+)[,x*×](\d+)', size_text)
                    if size_match:
                        width = int(size_match.group(1))
                        height = int(size_match.group(2))
                        print(f"Agent提取的尺寸: {width}x{height}")
                        return width, height
            
            # 如果提取失败，返回默认尺寸
            print("Agent尺寸提取失败，使用默认尺寸")
            return 1024, 768
            
        except Exception as e:
            print(f"尺寸提取失败: {e}，使用默认尺寸")
            return 1024, 768
    
    def extract_prompt_with_agent(self, background_content: str) -> str:
        """使用Qwen Agent智能提取图像生成提示词"""
        prompt_extraction_prompt = """
你是一个提示词提取专家，需要从设计内容中提取适合AI图像生成的英文提示词。

请从以下设计内容中提取关键的视觉元素，生成一个简洁的英文图像生成提示词。

注意事项：
1. 提取颜色、风格、图案、材质等视觉元素
2. 转换为英文描述
3. 保持简洁，不超过50个单词
4. 适合AI图像生成模型理解
5. 只返回英文提示词，不要其他说明
6. 如果是背景设计，加上background, design等关键词
        """.strip()
        
        messages = [
            {'role': 'system', 'content': prompt_extraction_prompt},
            {'role': 'user', 'content': background_content}
        ]
        
        try:
            response_generator = self.prompt_extractor.run(messages)
            responses = []
            for response in response_generator:
                responses.extend(response)
            
            for msg in reversed(responses):
                if msg.get('role') == 'assistant':
                    prompt = msg.get('content', '').strip()
                    if prompt:
                        print(f"Agent提取的提示词: {prompt}")
                        return prompt
            
            # 如果提取失败，返回默认提示词
            print("Agent提示词提取失败，使用默认提示词")
            return "elegant background design, gradient colors, modern style"
            
        except Exception as e:
            print(f"提示词提取失败: {e}，使用默认提示词")
            return "elegant background design, gradient colors, modern style"
    
    def extract_prompt_from_background_content(self, background_content: str) -> str:
        """从背景层内容中提取图像生成提示词（保留原方法作为备用）"""
        try:
            # 优先使用Agent提取
            return self.extract_prompt_with_agent(background_content)
            
        except Exception as e:
            print(f"Agent提取失败，使用传统方法: {e}")
            
            # 备用的传统提取方法
            try:
                # 尝试解析JSON格式的内容
                if '{' in background_content and '}' in background_content:
                    # 提取JSON部分
                    json_match = re.search(r'\{[^}]*"prompt"[^}]*\}', background_content)
                    if json_match:
                        json_data = json.loads(json_match.group())
                        if 'prompt' in json_data:
                            return json_data['prompt']
                
                # 如果没有找到JSON格式，尝试提取描述性文本
                lines = background_content.split('\n')
                prompt_parts = []
                
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#') and not line.startswith('*'):
                        # 过滤掉明显的标题和格式化内容
                        if '背景' in line or '颜色' in line or '渐变' in line or '图案' in line:
                            prompt_parts.append(line)
                
                if prompt_parts:
                    return ', '.join(prompt_parts[:3])  # 取前3个相关描述
                
                # 默认提示词
                return "elegant background design, gradient colors, modern style"
                
            except Exception as e:
                print(f"传统提取方法也失败: {e}")
                return "elegant background design, gradient colors, modern style"
    
    def generate_image_with_pollinations(self, prompt: str, width: int = 1024, height: int = 768) -> Optional[str]:
        """使用Pollinations.ai API生成图像"""
        try:
            # Pollinations.ai的图像生成API
            api_url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}"
            
            # 添加一些参数来提高图像质量
            params = {
                'width': width,
                'height': height,
                'seed': -1,  # 随机种子
                'model': 'flux'  # 使用flux模型
            }
            
            # 构建完整URL
            param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            full_url = f"{api_url}?{param_string}"
            
            print(f"正在生成图像，提示词: {prompt}")
            print(f"图像尺寸: {width}x{height}")
            print(f"API URL: {full_url}")
            
            # 发送请求
            response = requests.get(full_url, timeout=30)
            
            if response.status_code == 200:
                return full_url
            else:
                print(f"API请求失败，状态码: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"图像生成失败: {e}")
            return None
    
    def download_and_save_image(self, image_url: str, prompt: str, background_content: str = "", use_timestamp: bool = True) -> Optional[str]:
        """下载并保存图像到本地，使用Agent提取的文件名"""
        try:
            # 使用Agent提取文件名
            base_filename = self.extract_filename_from_background_content(background_content) if background_content else "background.png"
            
            if use_timestamp:
                # 生成带时间戳的文件名
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                name_part, ext = os.path.splitext(base_filename)
                filename = f"{name_part}_{timestamp}{ext}"
            else:
                # 直接使用提取的文件名
                filename = base_filename
                
            filepath = self.output_dir / filename
            
            print(f"正在下载图像到: {filepath}")
            print(f"基础文件名: {base_filename}")
            
            # 下载图像
            response = requests.get(image_url, timeout=30)
            
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                print(f"图像保存成功: {filepath}")
                return str(filepath)
            else:
                print(f"图像下载失败，状态码: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"图像保存失败: {e}")
            return None
    
    def generate_background_from_content(self, background_content: str) -> Dict[str, Any]:
        """根据背景层内容生成背景图像"""
        try:
            # 使用Agent提取提示词
            prompt = self.extract_prompt_from_background_content(background_content)
            print(f"提取的提示词: {prompt}")
            
            # 使用Agent提取尺寸
            width, height = self.extract_image_size_with_agent(background_content)
            print(f"提取的尺寸: {width}x{height}")
            
            # 使用Agent提取文件名
            filename = self.extract_filename_from_background_content(background_content)
            print(f"提取的文件名: {filename}")
            
            # 生成图像URL
            image_url = self.generate_image_with_pollinations(prompt, width, height)
            if not image_url:
                return {
                    'status': 'error',
                    'error': '图像生成失败',
                    'prompt': prompt,
                    'size': f"{width}x{height}",
                    'filename': filename
                }
            
            # 下载并保存图像（传入background_content用于文件名提取）
            local_path = self.download_and_save_image(image_url, prompt, background_content)
            if not local_path:
                return {
                    'status': 'error',
                    'error': '图像下载失败',
                    'prompt': prompt,
                    'image_url': image_url,
                    'size': f"{width}x{height}",
                    'filename': filename
                }
            
            return {
                'status': 'success',
                'prompt': prompt,
                'image_url': image_url,
                'local_path': local_path,
                'size': f"{width}x{height}",
                'width': width,
                'height': height,
                'filename': filename,
                'output_dir': str(self.output_dir)
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': f'生成过程失败: {str(e)}',
                'prompt': prompt if 'prompt' in locals() else 'unknown',
                'filename': filename if 'filename' in locals() else 'background.png'
            }
    
    def set_layer_type(self, layer_type: str):
        """设置图层类型"""
        self.layer_type = layer_type
        self.filter_agent.set_layer_type(layer_type)
        # 注释掉重新设置输出目录的代码，保持构造函数中设置的目录
        # output_dir = f"generated_{layer_type.replace('层', '')}_images"
        # self.output_dir = Path(output_dir)
        # self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_filename_with_agent(self, layer_content: str) -> str:
        """使用Qwen Agent智能提取文件名"""
        filename_prompt = f"""
你是一个文件名提取专家，需要从设计内容中提取输出文件名信息。

请从以下内容中提取 "output" 字段中的文件名，通常格式如下：
"output": ["filename.png"]
或
"output": ["filename.png", "another.jpg"]

注意事项：
1. 优先查找 JSON 格式中的 "output" 字段
2. 提取第一个文件名（通常是主要输出文件）
3. 如果找不到明确的文件名，根据内容类型生成合适的文件名
4. {self.layer_type}设计建议使用 "{self.layer_type.replace('层', '')}.png"
5. 只返回文件名，不要包含路径
6. 不要包含任何其他文字说明
7. 确保文件名包含适当的扩展名（.png, .jpg等）
        """.strip()
        
        messages = [
            {'role': 'system', 'content': filename_prompt},
            {'role': 'user', 'content': layer_content}
        ]
        
        try:
            response_generator = self.filename_extractor.run(messages)
            responses = []
            for response in response_generator:
                responses.extend(response)
            
            for msg in reversed(responses):
                if msg.get('role') == 'assistant':
                    filename = msg.get('content', '').strip()
                    # 清理文件名，移除引号和多余字符
                    filename = re.sub(r'["\[\]\s]', '', filename)
                    # 确保有扩展名
                    if filename and not filename.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        filename += '.png'
                    if filename:
                        print(f"Agent提取的文件名: {filename}")
                        return filename
            
            # 如果提取失败，返回默认文件名
            default_filename = f"{self.layer_type.replace('层', '')}.png"
            print(f"Agent文件名提取失败，使用默认文件名: {default_filename}")
            return default_filename
            
        except Exception as e:
            default_filename = f"{self.layer_type.replace('层', '')}.png"
            print(f"文件名提取失败: {e}，使用默认文件名: {default_filename}")
            return default_filename

    def process_layer_design_file(self, file_path: str, layer_type: str = None) -> Dict[str, Any]:
        """处理图层设计文件并生成图像"""
        try:
            # 如果指定了图层类型，更新当前设置
            if layer_type:
                self.set_layer_type(layer_type)
            
            # 使用过滤Agent提取指定图层内容
            filter_result = self.filter_agent.process_file(file_path, self.layer_type)
            
            if filter_result['status'] != 'success':
                return filter_result
            
            layer_content = filter_result['filtered_content']
            
            # 生成图像 - 修改这里的方法名
            generation_result = self.generate_background_from_content(layer_content)
            
            # 合并结果
            result = {
                'source_file': file_path,
                'layer_type': self.layer_type,
                'layer_content': layer_content,
                **generation_result
            }
            
            return result
            
        except Exception as e:
            return {
                'status': 'error',
                'error': f'文件处理失败: {str(e)}',
                'source_file': file_path,
                'layer_type': self.layer_type
            }


def main():
    print("请选择要生成的图层类型:")
    print("1. 背景层")
    print("2. 文字层")
    print("3. 主元素层")
    print("4. 效果层")
    print("5. 自定义")
    
    choice = input("请输入选择 (1-5): ").strip()
    
    layer_type_map = {
        "1": "背景层",
        "2": "文字层", 
        "3": "主元素层",
        "4": "效果层"
    }
    
    if choice in layer_type_map:
        layer_type = layer_type_map[choice]
    elif choice == "5":
        layer_type = input("请输入自定义图层类型: ").strip()
    else:
        print("无效选择，使用默认背景层")
        layer_type = "背景层"
    
    # 初始化生成器 - 传递 layer_type 作为第一个参数
    generator = BackgroundImageGenerator(layer_type)
    
    # 指定文件路径
    file_path = "/Users/qian.lwq/Downloads/autogen_test/Qwen-Agent/banner_project_20250605_140543/documents/layer_routing_plan.json"
    
    # 处理文件并生成图像
    result = generator.process_layer_design_file(file_path)
    
    # 打印结果
    print("=" * 60)
    print(f"{layer_type}图像生成结果")
    print("=" * 60)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 如果成功，显示详细信息
    if result['status'] == 'success':
        print("\n" + "=" * 60)
        print("生成成功！")
        print("=" * 60)
        print(f"图层类型: {result['layer_type']}")
        print(f"提示词: {result['prompt']}")
        print(f"图像尺寸: {result['size']}")
        print(f"图像URL: {result['image_url']}")
        print(f"本地路径: {result['local_path']}")
        print(f"输出目录: {result['output_dir']}")


if __name__ == "__main__":
    main()