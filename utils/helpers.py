import os
import json
import datetime
from typing import List, Dict, Any
import re
from qwen_agent import Agent

class FileHelper:
    """文件操作辅助类"""
    
    def __init__(self, work_dir: str):
        self.work_dir = work_dir
    
    def collect_generated_files(self) -> List[Dict[str, Any]]:
        """收集工作目录中生成的文件"""
        file_manifest = []
        
        try:
            for root, dirs, files in os.walk(self.work_dir):
                for file in files:
                    if file.endswith(('.png', '.jpg', '.jpeg', '.svg', '.css', '.html', '.js')):
                        file_path = os.path.join(root, file)
                        file_info = {
                            'filename': file,
                            'path': file_path,
                            'relative_path': os.path.relpath(file_path, self.work_dir),
                            'size': os.path.getsize(file_path),
                            'created_at': datetime.datetime.fromtimestamp(os.path.getctime(file_path)).isoformat(),
                            'type': self._get_file_type(file)
                        }
                        file_manifest.append(file_info)
        except Exception as e:
            print(f"收集文件时出错：{e}")
        
        return file_manifest
    
    def _get_file_type(self, filename: str) -> str:
        """根据文件扩展名确定文件类型"""
        ext = filename.lower().split('.')[-1]
        type_mapping = {
            'png': 'image',
            'jpg': 'image',
            'jpeg': 'image',
            'svg': 'vector',
            'css': 'stylesheet',
            'html': 'markup',
            'js': 'script'
        }
        return type_mapping.get(ext, 'unknown')

class RoutingHelper:
    """路由处理辅助类"""
    
    def __init__(self, llm_config: Dict):
        self.llm_config = llm_config
        self.routing_agent = self._create_routing_agent()
    
    def _create_routing_agent(self) -> Agent:
        """创建智能路由分析Agent"""
        from qwen_agent.agents import Assistant
        
        return Assistant(
            name="智能路由分析器",
            description="专业的路由分析Agent，负责解析和优化图层路由计划",
            system_message="""# 角色
你是一位专业的路由分析专家，负责解析图层路由结果并生成标准化的路由计划。

## 技能
### 技能1: 智能解析
- 从复杂的文本中提取路由信息
- 识别图层配置和Agent分配
- 处理不完整或格式不规范的输入

### 技能2: 路由优化
- 根据图层依赖关系优化执行顺序
- 确保Agent分配的合理性
- 提供备选方案和容错处理

### 技能3: 标准化输出
- 生成符合系统要求的JSON格式路由计划
- 确保所有必需字段完整
- 提供详细的执行指导

## 输出要求
必须输出标准JSON格式的路由计划，包含以下字段：
- layer_name: 图层名称
- agent: 执行Agent名称
- target: 图层目标
- key_elements: 关键要素列表
- input_params: 输入参数对象
- output_requirements: 输出要求

## 容错机制
如果输入信息不完整，使用合理的默认值补充，确保系统正常运行。""",
            llm=self.llm_config
        )
    
    def parse_routing_result(self, routing_result: str, work_dir: str) -> List[Dict[str, Any]]:
        """简化的路由解析 - 直接返回标准配置"""
        try:
            # 直接使用标准路由配置，不进行复杂的JSON解析
            routing_plan = self._get_default_routing_plan()
            
            # 保存路由计划到文件
            routing_file = os.path.join(work_dir, 'documents', 'layer_routing_plan.json')
            os.makedirs(os.path.dirname(routing_file), exist_ok=True)
            
            with open(routing_file, 'w', encoding='utf-8') as f:
                json.dump(routing_plan, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 路由计划已保存到: {routing_file}")
            return routing_plan
            
        except Exception as e:
            print(f"路由解析失败：{e}，使用默认配置")
            return self._get_default_routing_plan()
    
           
    def _validate_and_enhance_routing_plan(self, routing_plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """验证和增强路由计划"""
        enhanced_plan = []
        required_fields = ['layer_name', 'agent', 'target', 'key_elements', 'input_params', 'output_requirements']
        
        for layer in routing_plan:
            enhanced_layer = {}
            
            # 确保所有必需字段存在
            for field in required_fields:
                if field in layer:
                    enhanced_layer[field] = layer[field]
                else:
                    enhanced_layer[field] = self._get_default_field_value(field, layer)
            
            # 验证Agent名称
            valid_agents = ['布局执行师', '背景执行师', '主元素执行师', '标识执行师', '文字执行师', '效果执行师']
            if enhanced_layer['agent'] not in valid_agents:
                enhanced_layer['agent'] = self._map_to_valid_agent(enhanced_layer['agent'])
            
            enhanced_plan.append(enhanced_layer)
        
        return enhanced_plan
    
    def _get_default_field_value(self, field: str, layer_data: Dict) -> Any:
        """获取字段的默认值"""
        defaults = {
            'layer_name': layer_data.get('name', '未知图层'),
            'agent': '布局执行师',
            'target': '生成图层内容',
            'key_elements': [],
            'input_params': {},
            'output_requirements': '标准输出文件'
        }
        return defaults.get(field, '')
    
    def _map_to_valid_agent(self, agent_name: str) -> str:
        """将Agent名称映射到有效的执行师"""
        mapping = {
            'layout': '布局执行师',
            'background': '背景执行师', 
            'main': '主元素执行师',
            'logo': '标识执行师',
            'text': '文字执行师',
            'effect': '效果执行师'
        }
        
        agent_lower = agent_name.lower()
        for key, value in mapping.items():
            if key in agent_lower:
                return value
        
        return '布局执行师'  # 默认返回布局执行师
    
    def _get_enhanced_default_routing_plan(self, context: str = "") -> List[Dict[str, Any]]:
        """获取增强的默认路由计划"""
        return self._get_default_routing_plan()
    
    def _get_default_routing_plan(self) -> List[Dict[str, Any]]:
        """获取默认的路由计划"""
        return [
            {
                "layer_name": "布局层",
                "agent": "布局执行师",
                "target": "生成Banner整体布局结构",
                "key_elements": ["整体框架", "分区布局", "响应式设计"],
                "input_params": {
                    "size": "1200x600",
                    "format": "svg",
                    "layout_type": "grid"
                },
                "output_requirements": "layout_structure.svg"
            },
            {
                "layer_name": "背景层",
                "agent": "背景执行师",
                "target": "生成Banner背景图像",
                "key_elements": ["背景色彩", "纹理效果", "氛围营造"],
                "input_params": {
                    "size": "1200x600",
                    "format": "png",
                    "style": "modern"
                },
                "output_requirements": "background.png"
            },
            {
                "layer_name": "主要素层",
                "agent": "主元素执行师",
                "target": "生成主要视觉元素",
                "key_elements": ["产品图像", "主体元素", "视觉焦点"],
                "input_params": {
                    "size": "600x400",
                    "format": "png",
                    "transparent": True
                },
                "output_requirements": "main_element.png"
            },
            {
                "layer_name": "表意标识层",
                "agent": "标识执行师",
                "target": "生成Logo和标识元素",
                "key_elements": ["品牌Logo", "图标元素", "标识符号"],
                "input_params": {
                    "size": "200x200",
                    "format": "svg",
                    "vector": True
                },
                "output_requirements": "logo.svg"
            },
            {
                "layer_name": "文字层",
                "agent": "文字执行师",
                "target": "生成文字内容和样式",
                "key_elements": ["标题文字", "正文内容", "字体效果"],
                "input_params": {
                    "format": "svg",
                    "font_family": "sans-serif",
                    "responsive": True
                },
                "output_requirements": "text_content.svg"
            },
            {
                "layer_name": "效果层",
                "agent": "效果执行师",
                "target": "生成特效和装饰元素",
                "key_elements": ["视觉特效", "装饰元素", "动画效果"],
                "input_params": {
                    "format": "svg",
                    "animation": False,
                    "effects": ["shadow", "glow"]
                },
                "output_requirements": "effects.svg"
            }
        ]
    
    def build_layer_instruction(self, layer_config: Dict[str, Any], marketing_context: str) -> str:
        """构建图层执行指令"""
        instruction = f"""请根据以下配置执行{layer_config.get('layer_name', '图层')}的生成任务：

**营销背景：**
{marketing_context}

**图层配置：**
- 图层名称：{layer_config.get('layer_name', '未指定')}
- 目标：{layer_config.get('target', '未指定')}
- 关键要素：{', '.join(layer_config.get('key_elements', []))}
- 输入参数：{json.dumps(layer_config.get('input_params', {}), ensure_ascii=False)}
- 输出要求：{layer_config.get('output_requirements', '未指定')}

**执行要求：**
1. 严格按照输入参数执行
2. 确保输出文件符合命名规范
3. 记录生成过程和参数
4. 保存所有中间文件
5. 确保文件质量和规格要求

请开始执行并生成相应的图层物料。"""
        
        return instruction