from typing import List, Dict, Any
import os
import sys

# 添加banner_system目录到路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from background_image_generator import BackgroundImageGenerator
from svg_code_generator import SVGCodeGenerator

class ExecutionAgentsFactory:
    """简化的执行层智能体工厂类"""
    
    def __init__(self, llm_config: Dict, progress_tracker, file_saver):
        self.llm_config = llm_config
        self.progress_tracker = progress_tracker
        self.file_saver = file_saver
        self.work_dir = './work'
    
    def create_execution_agents(self) -> List:
        """创建执行层智能体列表（为了兼容现有系统）"""
        return []
    
    def set_work_dir(self, work_dir: str):
        """设置工作目录"""
        self.work_dir = work_dir
    
    def execute_svg_layer(self, layer_name: str, design_file_path: str, output_dir: str = None) -> Dict[str, Any]:
        """执行SVG图层生成"""
        try:
            # 如果没有指定输出目录，使用工作目录下的svg子目录
            if output_dir is None:
                output_dir = os.path.join(self.work_dir, 'svg')
            
            os.makedirs(output_dir, exist_ok=True)
            
            # 创建SVG生成器
            generator = SVGCodeGenerator(
                layer_type=layer_name,
                output_dir=output_dir
            )
            
            # 处理图层文件
            result = generator.process_layer_file(design_file_path, layer_name)
            
            print(f"✅ SVG图层 {layer_name} 生成完成")
            return result
            
        except Exception as e:
            print(f"❌ SVG图层 {layer_name} 生成失败: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def execute_image_layer(self, layer_name: str, design_file_path: str, output_dir: str = None) -> Dict[str, Any]:
        """执行图像图层生成"""
        try:
            # 如果没有指定输出目录，使用工作目录下的images子目录
            if output_dir is None:
                output_dir = os.path.join(self.work_dir, 'images')
            
            os.makedirs(output_dir, exist_ok=True)
            
            # 创建图像生成器
            generator = BackgroundImageGenerator(
                layer_type=layer_name,
                output_dir=output_dir
            )
            
            # 处理图层设计文件
            result = generator.process_layer_design_file(
                file_path=design_file_path,
                layer_type=layer_name
            )
            
            print(f"✅ 图像图层 {layer_name} 生成完成")
            return result
            
        except Exception as e:
            print(f"❌ 图像图层 {layer_name} 生成失败: {e}")
            return {'status': 'error', 'error': str(e)}