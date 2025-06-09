import json
import os
from typing import Dict, Any, Optional
from qwen_agent.agents import Assistant
import dashscope

# 设置API密钥
dashscope.api_key = ""

class SVGLayerFilterAgent:
    """SVG图层内容过滤提取Agent，专门用于SVG相关图层"""
    
    def __init__(self, layer_type: str = "标识图层"):
        # 使用Assistant而不是继承Agent
        self.llm_cfg = {'model': 'qwen-max'}
        self.layer_type = layer_type  # 可配置的图层类型
        
        self.agent = Assistant(
            llm=self.llm_cfg,
            name='SVG设计文本处理专家',
            description=f'专门从设计内容中提取{self.layer_type}信息，用于SVG代码生成。'
        )
        
        # SVG设计文本处理专家的系统提示
        self.system_prompt = f"""
你是一个SVG设计文本处理专家，专门从设计内容中提取{self.layer_type}信息。

你的任务：
1. 从设计图层内容中提取与{self.layer_type}相关的所有信息
2. 重点关注形状、颜色、尺寸、位置、文字内容等SVG生成所需的关键信息
3. 保持原始格式和结构
4. 提取适合SVG代码生成的详细描述

注意事项：
1. 只输出与{self.layer_type}相关的内容
2. 包含所有SVG生成需要的技术细节
3. 不要添加任何解释或额外内容
4. 如果找不到对应层，返回"未找到对应图层"
        """.strip()
    
    def filter_layer(self, layer_content: str, target_layer: str = None) -> str:
        """从图层内容中过滤出指定图层信息
        
        Args:
            layer_content: 图层设计内容
            target_layer: 目标图层类型，如果不指定则使用初始化时的layer_type
        """
        # 使用传入的target_layer或默认的layer_type
        layer_to_extract = target_layer or self.layer_type
        
        # 构建消息
        messages = [
            {'role': 'system', 'content': self.system_prompt},
            {'role': 'user', 'content': f"请提取{layer_to_extract}相关信息：\n\n{layer_content}"}
        ]
        
        try:
            # 使用Assistant的run方法
            response_generator = self.agent.run(messages)
            
            # 获取响应
            responses = []
            for response in response_generator:
                responses.extend(response)
            
            # 提取最后一个助手回复的内容
            for msg in reversed(responses):
                if msg.get('role') == 'assistant':
                    return msg.get('content', '').strip()
            
            return "未获取到有效响应"
            
        except Exception as e:
            return f"过滤失败: {str(e)}"
    
    def process_file(self, file_path: str, target_layer: str = None) -> Dict[str, Any]:
        """处理指定文件，提取指定图层内容
        
        Args:
            file_path: 文件路径
            target_layer: 目标图层类型，如果不指定则使用初始化时的layer_type
        """
        layer_to_extract = target_layer or self.layer_type
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 使用Agent过滤指定图层内容
            filtered_content = self.filter_layer(content, layer_to_extract)
            
            return {
                'source_file': file_path,
                'layer_type': layer_to_extract,
                'filtered_content': filtered_content,
                'status': 'success'
            }
            
        except Exception as e:
            return {
                'source_file': file_path,
                'layer_type': layer_to_extract,
                'error': f'文件处理失败: {str(e)}',
                'status': 'error'
            }
    
    def set_layer_type(self, layer_type: str):
        """动态设置图层类型"""
        self.layer_type = layer_type
        # 更新系统提示
        self.system_prompt = f"""
你是一个SVG设计文本处理专家，专门从设计内容中提取{self.layer_type}信息。

你的任务：
1. 从设计图层内容中提取与{self.layer_type}相关的所有信息
2. 重点关注形状、颜色、尺寸、位置、文字内容等SVG生成所需的关键信息
3. 保持原始格式和结构
4. 提取适合SVG代码生成的详细描述

注意事项：
1. 只输出与{self.layer_type}相关的内容
2. 包含所有SVG生成需要的技术细节
3. 不要添加任何解释或额外内容
4. 如果找不到对应层，返回"未找到对应图层"
        """.strip()