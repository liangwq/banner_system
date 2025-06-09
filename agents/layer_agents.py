from qwen_agent import Agent
from typing import Dict, Iterator, List
from qwen_agent.llm.schema import Message

class LayerGenerationAgent(Agent):
    """图层生成基础Agent"""
    
    def __init__(self, layer_type: str, generator_type: str, llm_config: Dict, name: str = None):
        # 设置Agent名称
        agent_name = name or f"{layer_type}执行师"
        super().__init__(llm=llm_config, name=agent_name)
        self.layer_type = layer_type
        self.generator_type = generator_type
        
        # 根据生成器类型选择工具
        if generator_type == 'svg':
            from ..svg_code_generator import create_generator
            self.generator = create_generator
        else:
            from ..background_image_generator import BackgroundImageGenerator
            self.generator = BackgroundImageGenerator
    
    def _run(self, messages: List[Message], **kwargs) -> Iterator[List[Message]]:
        """执行图层生成"""
        # 解析输入消息，提取设计要求
        design_requirements = self._parse_design_requirements(messages)
        
        # 调用相应的生成器
        result = self._generate_layer(design_requirements)
        
        # 返回生成结果
        yield [Message('assistant', f"{self.layer_type}生成完成：{result}")]
    
    def _parse_design_requirements(self, messages: List[Message]) -> Dict:
        """解析设计要求"""
        # 实现设计要求解析逻辑
        return {}
    
    def _generate_layer(self, requirements: Dict) -> Dict:
        """生成图层"""
        # 实现具体的图层生成逻辑
        return {}

class SVGLayerAgent(LayerGenerationAgent):
    """SVG图层生成Agent"""
    
    def __init__(self, layer_type: str, llm_config: Dict, name: str = None):
        super().__init__(layer_type, 'svg', llm_config, name)

class ImageLayerAgent(LayerGenerationAgent):
    """图像图层生成Agent"""
    
    def __init__(self, layer_type: str, llm_config: Dict, name: str = None):
        super().__init__(layer_type, 'image', llm_config, name)

class LayerAgentsFactory:
    """图层代理工厂类"""
    
    def __init__(self, llm_config: Dict, progress_tracker=None, file_saver=None):
        self.llm_config = llm_config
        self.progress_tracker = progress_tracker
        self.file_saver = file_saver
    
    def create_text_layer_agent(self) -> SVGLayerAgent:
        """创建文字图层代理"""
        return SVGLayerAgent('文字', self.llm_config, name='文字执行师')
    
    def create_logo_layer_agent(self) -> SVGLayerAgent:
        """创建标识图层代理"""
        return SVGLayerAgent('标识', self.llm_config, name='标识执行师')
    
    def create_layout_layer_agent(self) -> SVGLayerAgent:
        """创建布局图层代理"""
        return SVGLayerAgent('布局', self.llm_config, name='布局执行师')
    
    def create_effects_layer_agent(self) -> SVGLayerAgent:
        """创建效果图层代理"""
        return SVGLayerAgent('效果', self.llm_config, name='效果执行师')
    
    def create_background_layer_agent(self) -> ImageLayerAgent:
        """创建背景图层代理"""
        return ImageLayerAgent('背景', self.llm_config, name='背景执行师')
    
    def create_main_element_layer_agent(self) -> ImageLayerAgent:
        """创建主元素图层代理"""
        return ImageLayerAgent('主元素', self.llm_config, name='主元素执行师')