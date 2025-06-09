from qwen_agent.tools.base import BaseTool
from qwen_agent.tools import ImageGen, CodeInterpreter
import os
import requests
import re
import json
from typing import Dict, Any, Union

class EnhancedImageGen(BaseTool):
    name = 'enhanced_image_gen'
    description = '增强的图片生成工具，支持自动下载和保存'
    parameters = [
        {
            'name': 'prompt',
            'type': 'string',
            'description': '图片生成提示词',
            'required': True
        },
        {
            'name': 'size',
            'type': 'string', 
            'description': '图片尺寸，如1024x1024',
            'required': False
        },
        {
            'name': 'filename',
            'type': 'string',
            'description': '保存的文件名',
            'required': False
        }
    ]
    
    def __init__(self, work_dir='./work'):
        super().__init__()
        self.work_dir = work_dir
        self.image_gen = ImageGen()
    
    def call(self, params: Union[str, Dict[str, Any]], **kwargs) -> str:
        # 确保params是字典格式
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except json.JSONDecodeError:
                return "参数格式错误，请提供有效的JSON格式参数"
        
        prompt = params.get('prompt', '')
        size = params.get('size', '1024x1024')
        filename = params.get('filename', 'generated_image.png')
        
        # 规范化文件名，避免特殊字符
        if filename:
            # 移除特殊字符，使用下划线替代
            import re
            filename = re.sub(r'[^\w\-_.]', '_', filename)
            filename = re.sub(r'_+', '_', filename)  # 合并多个下划线
        
        # 确保文件保存在正确的子目录
        if 'background' in prompt.lower():
            save_dir = os.path.join(self.work_dir, 'images', 'backgrounds')
        elif 'main' in prompt.lower() or 'element' in prompt.lower():
            save_dir = os.path.join(self.work_dir, 'images', 'elements')
        else:
            save_dir = os.path.join(self.work_dir, 'images')
        
        os.makedirs(save_dir, exist_ok=True)
        
        try:
            # 调用原始ImageGen工具
            result = self.image_gen.call({'prompt': prompt, 'size': size})
            
            # 提取图片URL并下载保存
            image_url = self._extract_image_url(result)
            if image_url:
                saved_path = self._download_and_save_image(image_url, filename)
                return f"图片已生成并保存到: {saved_path}"
            else:
                return f"图片生成结果: {result}"
                
        except Exception as e:
            return f"图片生成过程中出现错误: {str(e)}"
    
    def _extract_image_url(self, result):
        """从结果中提取图片URL"""
        if isinstance(result, str):
            # 使用正则表达式提取URL
            url_pattern = r'https?://[^\s<>"]+(?:\.png|\.jpg|\.jpeg|\.gif|\.webp)'
            urls = re.findall(url_pattern, result)
            return urls[0] if urls else None
        return None
    
    def _download_and_save_image(self, url: str, filename: str):
        """下载并保存图片"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # 确保工作目录存在
            os.makedirs(self.work_dir, exist_ok=True)
            
            # 保存文件
            file_path = os.path.join(self.work_dir, filename)
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            return file_path
        except Exception as e:
            raise Exception(f"下载图片失败: {str(e)}")

class EnhancedCodeExtractor(BaseTool):
    name = 'enhanced_code_extractor'
    description = '增强的代码生成和保存工具'
    parameters = [
        {
            'name': 'code',
            'type': 'string',
            'description': '要执行或保存的代码',
            'required': True
        },
        {
            'name': 'language',
            'type': 'string',
            'description': '代码语言类型',
            'required': False
        },
        {
            'name': 'filename',
            'type': 'string',
            'description': '保存的文件名',
            'required': False
        }
    ]
    
    def __init__(self, work_dir='./work'):
        super().__init__()
        self.work_dir = work_dir
        self.code_interpreter = CodeInterpreter()
    
    def call(self, params: Union[str, Dict[str, Any]], **kwargs) -> str:
        # 确保params是字典格式
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except json.JSONDecodeError:
                return "参数格式错误，请提供有效的JSON格式参数"
        
        code = params.get('code', '')
        language = params.get('language', 'svg')
        filename = params.get('filename', 'generated_code.svg')
        
        try:
            # 确保工作目录存在
            os.makedirs(self.work_dir, exist_ok=True)
            
            # 保存代码文件
            file_path = os.path.join(self.work_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(code)
            
            return f"代码已保存到: {file_path}"
            
        except Exception as e:
            return f"保存代码过程中出现错误: {str(e)}"

# 在现有代码后添加

class LayerImageGenerator(BaseTool):
    """基于图层内容的智能图像生成工具"""
    name = 'layer_image_generator'
    description = '根据图层设计内容智能生成图像，支持多种图层类型'
    parameters = [
        {
            'name': 'layer_content',
            'type': 'string', 
            'description': '图层设计内容',
            'required': True
        },
        {
            'name': 'layer_type',
            'type': 'string',
            'description': '图层类型（如：背景层、主元素层等）',
            'required': True
        },
        {
            'name': 'output_filename',
            'type': 'string',
            'description': '输出文件名（可选）',
            'required': False
        }
    ]
    
    def __init__(self, work_dir: str = './work'):
        self.work_dir = work_dir
        # 导入必要的模块
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        from background_image_generator import BackgroundImageGenerator
        from background_layer_filter_agent import BackgroundLayerFilterAgent
        
        self.generator = None
        self.filter_agent = BackgroundLayerFilterAgent()
    
    def call(self, params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """执行图层图像生成"""
        try:
            layer_content = params.get('layer_content', '')
            layer_type = params.get('layer_type', '背景层')
            output_filename = params.get('output_filename')
            
            # 如果没有提供layer_content，尝试从layer_design.md文件中读取
            if not layer_content:
                layer_design_path = os.path.join(self.work_dir, 'documents', 'layer_design.md')
                if os.path.exists(layer_design_path):
                    with open(layer_design_path, 'r', encoding='utf-8') as f:
                        layer_content = f.read()
                else:
                    return {
                        'success': False,
                        'message': f'未找到layer_design.md文件: {layer_design_path}'
                    }
            
            # 初始化生成器
            if not self.generator or self.generator.layer_type != layer_type:
                from background_image_generator import BackgroundImageGenerator
                output_dir = os.path.join(self.work_dir, 'images')
                self.generator = BackgroundImageGenerator(layer_type, output_dir)
            
            # 过滤图层内容
            filtered_content = self.filter_agent.filter_layer(layer_content, layer_type)
            
            # 生成图像
            result = self.generator.generate_background_from_content(filtered_content)
            
            if result['status'] == 'success':
                return {
                    'success': True,
                    'message': f'{layer_type}图像生成成功',
                    'image_path': result['local_path'],
                    'image_url': result['image_url'],
                    'prompt': result['prompt'],
                    'size': result['size']
                }
            else:
                return {
                    'success': False,
                    'message': f'{layer_type}图像生成失败: {result.get("error", "未知错误")}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'图像生成过程出错: {str(e)}'
            }

class LayerContentFilter(BaseTool):
    """图层内容过滤工具"""
    name = 'layer_content_filter'
    description = '从设计内容中过滤提取指定图层信息'
    parameters = [
        {
            'name': 'content',
            'type': 'string',
            'description': '原始设计内容',
            'required': True
        },
        {
            'name': 'layer_type', 
            'type': 'string',
            'description': '要提取的图层类型',
            'required': True
        }
    ]
    
    def __init__(self):
        # 导入过滤Agent
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        from background_layer_filter_agent import BackgroundLayerFilterAgent
        self.filter_agent = BackgroundLayerFilterAgent()
        self.work_dir = None  # 将在调用时设置
    
    def set_work_dir(self, work_dir: str):
        """设置工作目录"""
        self.work_dir = work_dir
    
    def call(self, params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """执行图层内容过滤"""
        try:
            content = params.get('content', '')
            layer_type = params.get('layer_type', '背景层')
            
            # 如果没有提供content，尝试从layer_design.md文件中读取
            if not content and self.work_dir:
                layer_design_path = os.path.join(self.work_dir, 'documents', 'layer_design.md')
                if os.path.exists(layer_design_path):
                    with open(layer_design_path, 'r', encoding='utf-8') as f:
                        content = f.read()
            
            filtered_content = self.filter_agent.filter_layer(content, layer_type)
            
            return {
                'success': True,
                'filtered_content': filtered_content,
                'layer_type': layer_type
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'图层内容过滤失败: {str(e)}'
            }

# 在文件末尾添加

class SVGCodeGenerator(BaseTool):
    """SVG代码生成工具"""
    name = 'svg_code_generator'
    description = '根据图层设计内容生成SVG代码'
    parameters = [
        {
            'name': 'layer_content',
            'type': 'string',
            'description': '图层设计内容',
            'required': True
        },
        {
            'name': 'layer_type',
            'type': 'string',
            'description': '图层类型（如：标识层、布局层等）',
            'required': True
        },
        {
            'name': 'output_filename',
            'type': 'string',
            'description': '输出文件名（可选）',
            'required': False
        }
    ]
    
    def __init__(self, work_dir: str = './work'):
        self.work_dir = work_dir
        # 导入SVG生成器
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        
        from svg_code_generator import SVGCodeGenerator as Generator  # 现在可以正确导入
        
        self.generator = None
    
    def call(self, params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """执行SVG代码生成"""
        try:
            layer_content = params.get('layer_content', '')
            layer_type = params.get('layer_type', '标识层')
            output_filename = params.get('output_filename')
            
            # 如果没有提供layer_content，尝试从layer_design.md文件中读取
            if not layer_content and self.work_dir:
                layer_design_path = os.path.join(self.work_dir, 'documents', 'layer_design.md')
                if os.path.exists(layer_design_path):
                    with open(layer_design_path, 'r', encoding='utf-8') as f:
                        layer_content = f.read()
                else:
                    return {
                        'success': False,
                        'message': f'未找到layer_design.md文件: {layer_design_path}'
                    }
            
            # 初始化生成器
            if not self.generator or self.generator.layer_type != layer_type:
                from svg_code_generator import SVGCodeGenerator as Generator
                output_dir = os.path.join(self.work_dir, 'images')
                self.generator = Generator(output_dir, layer_type)
            
            # 生成SVG代码
            result = self.generator.generate_svg_from_content(layer_content)
            
            if result['status'] == 'success':
                return {
                    'success': True,
                    'message': f'{layer_type}SVG代码生成成功',
                    'svg_code': result['svg_code'],
                    'file_path': result['file_path'],
                    'filename': result['filename']
                }
            else:
                return {
                    'success': False,
                    'message': f'{layer_type}SVG代码生成失败: {result.get("error", "未知错误")}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'SVG代码生成过程出错: {str(e)}'
            }