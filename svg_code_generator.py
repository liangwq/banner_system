import json
import os
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from qwen_agent.agents import Assistant
from .svg_layer_filter_agent import SVGLayerFilterAgent
import dashscope

class SVGCodeGeneratorConfig:
    """SVG代码生成器配置类"""
    def __init__(self, 
                 api_key: str = None,
                 model: str = 'qwen-max',
                 model_server: str = 'dashscope',
                 max_input_tokens: int = 80000,
                 output_dir: str = 'generated_svgs'):
        self.api_key = api_key or os.getenv('DASHSCOPE_API_KEY', '')
        self.model = model
        self.model_server = model_server
        self.max_input_tokens = max_input_tokens
        self.output_dir = output_dir
        
        # 设置API密钥
        dashscope.api_key = self.api_key

class RobustJSONExtractor:
    """鲁棒的JSON提取器"""
    def __init__(self, config: SVGCodeGeneratorConfig):
        self.agent = Assistant(
            llm={'model': config.model},
            name='JSON提取器',
            description='专门用于从混乱文本中提取和修复JSON格式',
            system_message="""
你是一个专业的JSON提取和修复专家。你的任务是：
1. 从给定的文本中识别和提取JSON内容
2. 修复格式错误的JSON
3. 确保输出是有效的JSON格式
4. 如果无法提取有效JSON，返回错误信息

请只返回修复后的JSON，不要添加任何解释。
"""
        )
    
    def extract_json_with_agent(self, text: str) -> Optional[dict]:
        """使用Agent提取和修复JSON"""
        try:
            messages = [
                {'role': 'user', 'content': f'请从以下文本中提取并修复JSON格式：\n\n{text}'}
            ]
            
            response_generator = self.agent.run(messages)
            responses = []
            for response in response_generator:
                responses.extend(response)
            
            for msg in reversed(responses):
                if msg.get('role') == 'assistant':
                    json_content = msg.get('content', '').strip()
                    try:
                        return json.loads(json_content)
                    except json.JSONDecodeError:
                        continue
            
            return None
            
        except Exception as e:
            print(f"Agent JSON提取失败: {e}")
            return None

class SVGCodeGenerator:
    """SVG代码生成器"""
    
    def __init__(self, config: SVGCodeGeneratorConfig = None, layer_type: str = "表意标识图层"):
        self.config = config or SVGCodeGeneratorConfig()
        self.layer_type = layer_type
        
        # 创建输出目录
        os.makedirs(self.config.output_dir, exist_ok=True)
        
        # 初始化各种Agent
        self._init_agents()
        
        # 初始化图层过滤器
        self.layer_filter = SVGLayerFilterAgent(layer_type=self.layer_type)
        
        # 初始化JSON提取器
        self.json_extractor = RobustJSONExtractor(self.config)
    
    def _init_agents(self):
        """初始化各种Agent"""
        llm_config = {
            'model': self.config.model,
            'model_server': self.config.model_server,
            'api_key': self.config.api_key
        }
        
        # SVG生成Agent
        self.svg_generator = Assistant(
            llm=llm_config,
            name='SVG代码生成专家',
            description=f'专门根据{self.layer_type}设计要求生成高质量的SVG代码',
            function_list=['code_interpreter']
        )
        
        # SVG提取Agent
        self.svg_extractor = Assistant(
            llm={**llm_config, 'generate_cfg': {'max_input_tokens': self.config.max_input_tokens}}
        )
        
        # 提示词提取Agent
        self.prompt_extractor = Assistant(llm=llm_config)
        
        # 文件名提取Agent
        self.filename_extractor = Assistant(llm=llm_config)
    
    def set_layer_type(self, layer_type: str):
        """动态设置图层类型"""
        self.layer_type = layer_type
        if hasattr(self, 'layer_filter'):
            self.layer_filter.set_layer_type(layer_type)
    
    def extract_layer_requirements(self, file_path: str, layer_type: str = None) -> Dict[str, Any]:
        """从文件中提取图层要求"""
        target_layer = layer_type or self.layer_type
        
        try:
            print(f"正在从文件提取{target_layer}要求...")
            
            # 使用图层过滤器提取指定图层内容
            filter_result = self.layer_filter.process_file(file_path, target_layer)
            
            if filter_result['status'] != 'success':
                return {
                    'status': 'error',
                    'error': f'图层提取失败: {filter_result.get("error", "未知错误")}',
                    'layer_type': target_layer,
                    'source_file': file_path
                }
            
            layer_content = filter_result['filtered_content']
            print(f"成功提取{target_layer}内容")
            
            return {
                'status': 'success',
                'layer_content': layer_content,
                'layer_type': target_layer,
                'source_file': file_path
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': f'提取图层要求失败: {str(e)}',
                'layer_type': target_layer,
                'source_file': file_path
            }
    
    def generate_svg_prompt(self, layer_content: str) -> str:
        """生成SVG生成提示词"""
        try:
            return self._extract_prompt_with_agent(layer_content)
        except Exception as e:
            print(f"提示词生成失败: {e}，使用默认提示词")
            return f"根据{self.layer_type}设计要求，生成高质量的SVG代码"
    
    def _extract_prompt_with_agent(self, layer_content: str) -> str:
        """使用Agent智能提取SVG生成提示词"""
        prompt_extraction_prompt = f"""
你是一个SVG代码生成提示词提取专家，需要从设计内容中提取适合生成SVG代码的详细描述。

请从以下{self.layer_type}设计内容中提取关键信息，生成一个详细的SVG生成提示词。

注意事项：
1. 提取图标的形状、颜色、风格、尺寸等关键信息
2. 描述图标的设计元素和视觉特征
3. 包含技术要求（如SVG格式、矢量图等）
4. 保持描述准确和详细
5. 只返回提示词内容，不要其他说明
6. 如果涉及文字，请明确文字内容
"""
        
        messages = [
            {'role': 'system', 'content': prompt_extraction_prompt},
            {'role': 'user', 'content': layer_content}
        ]
        
        response_generator = self.prompt_extractor.run(messages)
        responses = []
        for response in response_generator:
            responses.extend(response)
        
        for msg in reversed(responses):
            if msg.get('role') == 'assistant':
                prompt = msg.get('content', '').strip()
                if prompt:
                    print(f"Agent提取的SVG生成提示词: {prompt}")
                    return prompt
        
        raise Exception("Agent提示词提取失败")
    
    def generate_svg_code(self, layer_content: str) -> Dict[str, Any]:
        """生成SVG代码"""
        try:
            print("正在生成SVG代码...")
            
            # 生成提示词
            svg_prompt = self.generate_svg_prompt(layer_content)
            
            # 构建完整的生成提示
            full_prompt = f"""
根据以下{self.layer_type}设计要求，生成对应的SVG代码：

{layer_content}

生成提示词：{svg_prompt}

请使用code_interpreter工具生成完整的SVG代码，要求：
1. 根据设计要求准确实现图标样式
2. 使用指定的颜色方案
3. 确保SVG代码完整可用
4. 添加适当的注释说明
5. 优化代码结构
6. 使用标准的SVG viewBox和坐标系统

请生成SVG代码。
"""
            
            # 构建消息
            messages = [
                {'role': 'user', 'content': full_prompt}
            ]
            
            # 使用Assistant生成SVG
            response_generator = self.svg_generator.run(messages)
            responses = []
            for response in response_generator:
                responses.extend(response)
            
            # 提取助手回复的内容
            full_response = ""
            for msg in responses:
                if msg.get('role') == 'assistant':
                    content = msg.get('content', '')
                    if content:
                        full_response += content + "\n"
            
            print(f"SVG生成完成，响应长度: {len(full_response)}")
            
            return {
                'status': 'success',
                'full_response': full_response,
                'prompt': svg_prompt
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': f'SVG生成失败: {str(e)}'
            }
    
    def extract_svg_from_response(self, response_content: str) -> List[str]:
        """从生成结果中提取SVG代码"""
        try:
            print("正在提取SVG代码...")
            
            # 优先使用Agent提取
            svg_code = self._extract_svg_with_agent(response_content)
            if svg_code:
                svg_codes = self._split_multiple_svgs(svg_code)
                if svg_codes:
                    print(f"Agent成功提取{len(svg_codes)}个SVG代码")
                    return svg_codes
            
            print("Agent提取失败，使用传统正则表达式方法")
            
            # 备用的传统提取方法
            return self._extract_svg_with_regex(response_content)
            
        except Exception as e:
            print(f"SVG提取失败: {e}")
            return []
    
    def _extract_svg_with_agent(self, response_content: str) -> Optional[str]:
        """使用Agent智能提取SVG代码"""
        # 如果内容太长，截取关键部分
        if len(response_content) > 50000:
            svg_start = response_content.find('<svg')
            if svg_start != -1:
                start_pos = max(0, svg_start - 1000)
                end_pos = min(len(response_content), svg_start + 30000)
                response_content = response_content[start_pos:end_pos]
            else:
                response_content = response_content[-40000:]
        
        svg_extraction_prompt = """
你是一个SVG代码提取专家，需要从响应内容中准确提取完整的SVG代码。

请从以下内容中提取完整的SVG代码，要求：
1. 只提取纯净的SVG代码（从<svg>到</svg>）
2. 不要包含任何解释性文字、注释或其他内容
3. 确保代码完整可用且格式正确
4. 如果有多个相似的SVG代码，选择最完整的一个
5. 直接返回SVG代码，不要用代码块包装
6. 不要返回任何其他文字说明
"""
        
        messages = [
            {'role': 'system', 'content': svg_extraction_prompt},
            {'role': 'user', 'content': response_content}
        ]
        
        response_generator = self.svg_extractor.run(messages)
        responses = []
        for response in response_generator:
            responses.extend(response)
        
        for msg in reversed(responses):
            if msg.get('role') == 'assistant':
                svg_code = msg.get('content', '').strip()
                if svg_code and svg_code.startswith('<svg') and svg_code.endswith('</svg>'):
                    return svg_code
        
        return None
    
    def _extract_svg_with_regex(self, response_content: str) -> List[str]:
        """使用正则表达式提取SVG代码"""
        svg_codes = []
        
        # 定义多种SVG提取模式
        svg_patterns = [
            r'```svg\s*\n([\s\S]*?)\n```',  # ```svg 代码块
            r'```xml\s*\n([\s\S]*?)\n```',  # ```xml 代码块
            r'```\s*\n(<svg[\s\S]*?</svg>)\s*\n```',  # 通用代码块中的SVG
            r'(<svg[^>]*>[\s\S]*?</svg>)',  # 直接的SVG标签
        ]
        
        for pattern in svg_patterns:
            matches = re.findall(pattern, response_content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                svg_code = match if isinstance(match, str) else match[0]
                
                # 验证SVG代码的完整性
                if '<svg' in svg_code and '</svg>' in svg_code:
                    svg_codes.append(svg_code.strip())
        
        if svg_codes:
            print(f"传统方法成功提取{len(svg_codes)}个SVG代码")
        else:
            print("传统方法也未能提取到有效的SVG代码")
        
        return svg_codes
    
    def _split_multiple_svgs(self, svg_content: str) -> List[str]:
        """分割包含多个SVG的内容"""
        svg_pattern = r'(<svg[^>]*>[\s\S]*?</svg>)'
        matches = re.findall(svg_pattern, svg_content, re.IGNORECASE)
        
        if len(matches) > 1:
            print(f"发现{len(matches)}个SVG代码")
            return [match.strip() for match in matches]
        elif matches:
            return [matches[0].strip()]
        else:
            return [svg_content.strip()] if svg_content.strip() else []
    
    def generate_filename(self, layer_content: str) -> str:
        """生成文件名"""
        try:
            return self._extract_filename_with_agent(layer_content)
        except Exception as e:
            print(f"文件名生成失败: {e}，使用默认文件名")
            return self._generate_default_filename()
    
    def _extract_filename_with_agent(self, content: str) -> str:
        """使用Agent智能提取文件名"""
        filename_prompt = f"""
你是一个文件名提取专家，需要从设计内容中提取合适的SVG文件名。

请从以下{self.layer_type}设计内容中提取或生成合适的文件名：

注意事项：
1. 优先从output字段中提取现有文件名
2. 如果没有现有文件名，根据设计内容生成描述性文件名
3. 文件名应该简洁明了，反映图标的主要特征
4. 必须以.svg结尾
5. 只返回文件名，不要其他说明
6. 如果有多个文件，选择第一个或最主要的
"""
        
        messages = [
            {'role': 'system', 'content': filename_prompt},
            {'role': 'user', 'content': content}
        ]
        
        response_generator = self.filename_extractor.run(messages)
        responses = []
        for response in response_generator:
            responses.extend(response)
        
        for msg in reversed(responses):
            if msg.get('role') == 'assistant':
                filename = msg.get('content', '').strip()
                if filename and not filename.endswith('.svg'):
                    filename += '.svg'
                if filename:
                    print(f"Agent提取的文件名: {filename}")
                    return filename
        
        raise Exception("Agent文件名提取失败")
    
    def _generate_default_filename(self) -> str:
        """生成默认文件名"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        layer_name = self.layer_type.replace('图层', '')
        return f"{layer_name}_{timestamp}.svg"
    
    def save_svg_files(self, svg_codes: List[str], base_filename: str) -> Dict[str, Any]:
        """保存SVG文件"""
        try:
            print(f"正在保存{len(svg_codes)}个SVG文件...")
            
            saved_files = []
            
            if len(svg_codes) == 1:
                # 只有一个SVG，使用原文件名
                file_path = self._save_single_svg_file(svg_codes[0], base_filename)
                saved_files.append({
                    'file_path': file_path,
                    'filename': base_filename,
                    'svg_code': svg_codes[0]
                })
            else:
                # 多个SVG，添加序号
                base_name = base_filename.replace('.svg', '')
                for i, svg_code in enumerate(svg_codes, 1):
                    filename = f"{base_name}_{i}.svg"
                    file_path = self._save_single_svg_file(svg_code, filename)
                    saved_files.append({
                        'file_path': file_path,
                        'filename': filename,
                        'svg_code': svg_code
                    })
            
            print(f"成功保存{len(saved_files)}个SVG文件")
            
            return {
                'status': 'success',
                'saved_files': saved_files,
                'count': len(saved_files)
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': f'文件保存失败: {str(e)}'
            }
    
    def _save_single_svg_file(self, svg_code: str, filename: str) -> str:
        """保存单个SVG文件"""
        file_path = os.path.join(self.config.output_dir, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(svg_code)
        
        return file_path
    
    def process_file(self, file_path: str, layer_type: str = None) -> Dict[str, Any]:
        """完整的处理流程：输入文件 -> 抽取图层要求 -> 生成SVG -> 提取SVG代码 -> 保存"""
        target_layer = layer_type or self.layer_type
        
        try:
            print(f"开始处理文件: {file_path}")
            print(f"目标图层类型: {target_layer}")
            
            # 1. 抽取图层要求
            extract_result = self.extract_layer_requirements(file_path, target_layer)
            if extract_result['status'] != 'success':
                return extract_result
            
            layer_content = extract_result['layer_content']
            
            # 2. 生成SVG代码
            generate_result = self.generate_svg_code(layer_content)
            if generate_result['status'] != 'success':
                return {
                    **extract_result,
                    **generate_result
                }
            
            # 3. 从生成结果中提取SVG代码
            svg_codes = self.extract_svg_from_response(generate_result['full_response'])
            if not svg_codes:
                return {
                    **extract_result,
                    'status': 'error',
                    'error': 'SVG代码提取失败',
                    'full_response': generate_result['full_response']
                }
            
            # 4. 生成文件名
            base_filename = self.generate_filename(layer_content)
            
            # 5. 保存SVG文件
            save_result = self.save_svg_files(svg_codes, base_filename)
            if save_result['status'] != 'success':
                return {
                    **extract_result,
                    **save_result
                }
            
            # 返回完整结果
            return {
                'status': 'success',
                'source_file': file_path,
                'layer_type': target_layer,
                'layer_content': layer_content,
                'svg_codes': svg_codes,
                'saved_files': save_result['saved_files'],
                'count': save_result['count'],
                'prompt': generate_result['prompt'],
                'full_response': generate_result['full_response']
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'source_file': file_path,
                'layer_type': target_layer,
                'error': f'处理失败: {str(e)}'
            }

def create_generator(api_key: str = None, 
                    output_dir: str = None, 
                    layer_type: str = "表意标识图层") -> SVGCodeGenerator:
    """创建SVG代码生成器的工厂函数"""
    config = SVGCodeGeneratorConfig(
        api_key=api_key,
        output_dir=output_dir or 'generated_svgs'
    )
    return SVGCodeGenerator(config, layer_type)

def main():
    """主函数 - 交互式使用"""
    print("SVG代码生成器")
    print("=" * 40)
    
    # 图层类型选择
    layer_types = [
        "表意标识图层",
        "背景图层", 
        "文字图层",
        "主元素图层",
        "效果图层"
    ]
    
    print("请选择要生成SVG的图层类型:")
    for i, layer_type in enumerate(layer_types, 1):
        print(f"{i}. {layer_type}")
    print("6. 自定义图层类型")
    
    try:
        choice = input("\n请输入选择 (1-6): ").strip()
        if choice == "6":
            selected_layer = input("请输入自定义图层类型: ").strip()
            if not selected_layer:
                selected_layer = "表意标识图层"
        elif choice in ["1", "2", "3", "4", "5"]:
            selected_layer = layer_types[int(choice) - 1]
        else:
            print("无效选择，使用默认的表意标识图层")
            selected_layer = "表意标识图层"
    except (ValueError, KeyboardInterrupt):
        print("\n使用默认的表意标识图层")
        selected_layer = "表意标识图层"
    
    # 输入文件路径
    file_path = input("\n请输入图层设计文件路径: ").strip()
    if not file_path:
        print("未提供文件路径，程序退出")
        return
    
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return
    
    # 输出目录
    output_dir = input("请输入输出目录 (回车使用默认): ").strip()
    if not output_dir:
        output_dir = "generated_svgs"
    
    # 创建生成器
    generator = create_generator(
        output_dir=output_dir,
        layer_type=selected_layer
    )
    
    print(f"\n开始处理{selected_layer}并生成SVG...")
    
    # 处理文件
    result = generator.process_file(file_path)
    
    # 打印结果
    print("=" * 60)
    print(f"{selected_layer} SVG生成结果")
    print("=" * 60)
    
    if result['status'] == 'success':
        print(f"✅ 成功生成{result['count']}个SVG文件:")
        for i, file_info in enumerate(result['saved_files'], 1):
            print(f"  {i}. {file_info['filename']} -> {file_info['file_path']}")
        print(f"📄 源文件: {result['source_file']}")
        print(f"🎯 图层类型: {result['layer_type']}")
        print("\n" + "=" * 40)
        print(f"提取的{selected_layer}内容:")
        print("=" * 40)
        print(result['layer_content'])
        print("\n" + "=" * 40)
        print("生成的SVG代码:")
        print("=" * 40)
        for i, file_info in enumerate(result['saved_files'], 1):
            print(f"\n--- SVG {i} ---")
            print(file_info['svg_code'])
    else:
        print(f"❌ 生成失败: {result['error']}")
        if 'layer_content' in result:
            print(f"\n提取的{result.get('layer_type', selected_layer)}内容:")
            print(result['layer_content'])
    
    print("\n" + "=" * 60)
    print(f"输出目录: {generator.config.output_dir}")
    print("=" * 60)

if __name__ == "__main__":
    main()