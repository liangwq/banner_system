# -*- coding: utf-8 -*-
import os
from typing import Dict, Any

class PromptManager:
    """Prompt 配置管理器"""
    
    def __init__(self):
        self.prompts = {}
        self._load_prompts()
    
    def _load_prompts(self):
        """加载所有 prompt 配置"""
        try:
            from .event_analysis_prompt import EVENT_ANALYSIS_PROMPT, EVENT_ANALYSIS_VARIABLES
            self.prompts['event_analysis'] = {
                'template': EVENT_ANALYSIS_PROMPT,
                'variables': EVENT_ANALYSIS_VARIABLES
            }
        except ImportError:
            print("Warning: 事件分析 prompt 配置文件未找到")
        
        try:
            from .layer_design_prompt import LAYER_DESIGN_PROMPT, LAYER_DESIGN_VARIABLES
            self.prompts['layer_design'] = {
                'template': LAYER_DESIGN_PROMPT,
                'variables': LAYER_DESIGN_VARIABLES
            }
        except ImportError:
            print("Warning: 图层设计 prompt 配置文件未找到")
    
    def get_prompt(self, prompt_type: str, variables: Dict[str, Any] = None) -> str:
        """获取指定类型的 prompt"""
        if prompt_type not in self.prompts:
            raise ValueError(f"未找到 prompt 类型: {prompt_type}")
        
        prompt_config = self.prompts[prompt_type]
        template = prompt_config['template']
        
        # 如果提供了变量，进行替换
        if variables:
            for key, value in variables.items():
                placeholder = prompt_config['variables'].get(key, f'${{{key}}}')
                template = template.replace(placeholder, str(value))
        
        return template
    
    def list_available_prompts(self) -> list:
        """列出所有可用的 prompt 类型"""
        return list(self.prompts.keys())

# 创建全局实例
prompt_manager = PromptManager()