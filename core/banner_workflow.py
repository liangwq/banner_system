from typing import Dict, Iterator, List, Optional, Union
from qwen_agent import Agent
from qwen_agent.agents import Assistant, Router
from qwen_agent.llm.schema import Message, ContentItem
from qwen_agent.llm import BaseChatModel
from qwen_agent.tools import BaseTool

from ..agents.top_agents import TopAgentsFactory
from ..agents.validation_agents import ValidationAgentsFactory
from ..tools.file_saver import EnhancedFileSaver
from ..tools.progress_tracker import ProgressTracker
from ..utils.helpers import FileHelper

class BannerWorkflow(Agent):
    """基于Qwen Agent Workflow的Banner生成系统"""
    
    def __init__(self, 
                 llm_config: Dict = None,
                 function_list: Optional[List[Union[str, Dict, BaseTool]]] = None,
                 debug_mode: bool = False):
        super().__init__(llm=llm_config or {'model': 'qwen-max'})
        
        # 初始化工作目录和工具
        self.work_dir = self._setup_work_directory()
        self.file_saver = EnhancedFileSaver(self.work_dir)
        self.progress_tracker = ProgressTracker(self.work_dir)
        self.file_helper = FileHelper(self.work_dir)
        
        # 初始化Agent工厂
        self.top_factory = TopAgentsFactory(llm_config, self.progress_tracker, self.file_saver)
        self.validation_factory = ValidationAgentsFactory(llm_config, self.progress_tracker, self.file_saver)
        
        # 创建专门的Agent
        self.analysis_agent = self.top_factory.create_event_analysis_agent()
        self.marketing_agent = self.top_factory.create_marketing_agent()
        self.design_agent = self.top_factory.create_layer_design_agent()
        self.routing_agent = self.top_factory.create_layer_routing_agent()
        self.render_agent = self.top_factory.create_html_render_agent()
        
        # 创建验证和优化Agent
        self.vl_validation_agent = self.validation_factory.create_vl_validation_agent()
        self.html_optimization_agent = self.validation_factory.create_html_optimization_agent()
        
        # 创建图层生成Router
        self.layer_router = self._create_layer_router()
        
        # 创建主路由器
        self.main_router = Router(
            llm=self.llm,
            agents=[
                self.analysis_agent,
                self.marketing_agent, 
                self.design_agent,
                self.routing_agent,
                self.layer_router,
                self.render_agent,
                self.vl_validation_agent
            ],
            name="Banner生成主路由器"
        )
    
    def _run(self, messages: List[Message], lang: str = 'zh', **kwargs) -> Iterator[List[Message]]:
        """定义Banner生成的workflow"""
        
        # 提取事件信息
        event_info = self._extract_event_info(messages)
        
        # 阶段1：事件分析
        yield from self._phase_event_analysis(event_info)
        
        # 阶段2：营销策划
        yield from self._phase_marketing_planning(event_info)
        
        # 阶段3：设计规划
        yield from self._phase_design_planning(event_info)
        
        # 阶段4：图层路由
        yield from self._phase_layer_routing(event_info)
        
        # 阶段5：图层生成
        yield from self._phase_layer_generation(event_info)
        
        # 阶段6：HTML渲染
        yield from self._phase_html_rendering(event_info)
        
        # 阶段7：VL验证优化
        yield from self._phase_vl_optimization(event_info)
        
        # 阶段8：最终报告
        yield from self._phase_final_report(event_info)
    
    def _phase_event_analysis(self, event_info: Dict) -> Iterator[List[Message]]:
        """事件分析阶段"""
        analysis_message = Message(
            'user', 
            f"请对事件'{event_info['event_name']}'进行深度分析。附加要求：{event_info.get('requirements', '')}"
        )
        
        for response in self.analysis_agent.run([analysis_message]):
            yield response
            # 保存分析结果
            self._save_phase_result('event_analysis', response)
    
    def _phase_marketing_planning(self, event_info: Dict) -> Iterator[List[Message]]:
        """营销策划阶段"""
        # 获取事件分析结果
        analysis_result = self._get_phase_result('event_analysis')
        
        marketing_message = Message(
            'user',
            f"基于事件分析结果，制定营销策划方案。\n\n事件分析：{analysis_result}"
        )
        
        for response in self.marketing_agent.run([marketing_message]):
            yield response
            self._save_phase_result('marketing_planning', response)
    
    def _extract_key_info(self, phase_result: str, max_length: int = 500) -> str:
        """提取阶段结果的关键信息，避免输入过长"""
        # 提取关键信息而不是完整结果
        if len(phase_result) <= max_length:
            return phase_result
        
        # 使用LLM提取关键信息
        summary_message = Message(
            'user',
            f"请提取以下内容的关键信息，控制在{max_length}字符内：\n\n{phase_result}"
        )
        
        # 调用LLM进行信息压缩
        summary = self._summarize_content(summary_message)
        return summary[:max_length]
    
    def _phase_design_planning(self, event_info: Dict) -> Iterator[List[Message]]:
        """设计规划阶段 - 优化版"""
        # 只传递关键信息而不是完整结果
        analysis_key = self._extract_key_info(self._get_phase_result('event_analysis'))
        marketing_key = self._extract_key_info(self._get_phase_result('marketing_planning'))
        
        design_message = Message(
            'user',
            f"制定6个图层的设计方案。\n\n事件分析要点：{analysis_key}\n\n营销策划要点：{marketing_key}"
        )
        
        for response in self.design_agent.run([design_message]):
            yield response
            self._save_phase_result('design_planning', response)
    
    def _phase_html_rendering(self, event_info: Dict) -> Iterator[List[Message]]:
        """HTML渲染阶段 - 优化版"""
        # 只收集关键的结构化信息，避免传递大量文本
        key_results = self._collect_key_phase_results()
        
        render_message = Message(
            'user',
            f"生成最终HTML Banner。\n\n项目：{event_info['event_name']}\n\n设计要求：{key_results}"
        )
        
        for response in self.render_agent.run([render_message]):
            # 只输出简化的进度信息，不输出完整内容
            progress_msg = Message('assistant', "HTML渲染阶段完成")
            yield [progress_msg]
            self._save_phase_result('html_rendering', response)
    
    def _phase_vl_optimization(self, event_info: Dict) -> Iterator[List[Message]]:
        """VL验证优化阶段 - 减少输出版"""
        html_result = self._get_phase_result('html_rendering')
        
        # 生成截图
        screenshot_path = self._take_html_screenshot(html_result)
        
        if screenshot_path:
            # 使用VL模型进行验证，但不传递完整HTML内容到消息中
            vl_message = Message(
                'user',
                [
                    ContentItem(text=f"请验证Banner质量。设计要求：{event_info.get('event_name', '')}"),
                    ContentItem(image=screenshot_path)
                ]
            )
            
            for response in self.vl_validation_agent.run([vl_message]):
                # 只输出验证结果摘要，不输出完整内容
                summary_msg = Message('assistant', "VL验证阶段完成")
                yield [summary_msg]
                
                # 如果需要优化，调用优化agent
                if self._should_optimize(response):
                    # 创建优化消息时，不包含完整的HTML和反馈内容
                    optimization_message = Message(
                        'user',
                        "根据VL反馈优化HTML Banner"
                    )
                    
                    for opt_response in self.html_optimization_agent.run([optimization_message]):
                        opt_summary_msg = Message('assistant', "HTML优化阶段完成")
                        yield [opt_summary_msg]
                        self._save_phase_result('vl_optimization', opt_response)
    
    def _extract_html_summary(self, html_content: str) -> str:
        """提取HTML内容摘要，用于调试"""
        if not html_content:
            return "无HTML内容"
        
        # 提取关键信息而不是完整HTML
        lines = html_content.split('\n')
        total_lines = len(lines)
        
        # 只返回基本统计信息
        return f"HTML文件包含{total_lines}行代码"
    
    def _create_debug_friendly_message(self, phase: str, content_summary: str) -> Message:
        """创建便于调试的消息"""
        return Message('assistant', f"{phase}阶段：{content_summary}")
    
    def _collect_key_phase_results(self) -> Dict:
        """收集关键阶段结果，避免信息冗余"""
        return {
            'design_specs': self._extract_design_specs(),
            'layer_config': self._extract_layer_config(),
            'style_guide': self._extract_style_guide()
        }
    
    def _extract_design_specs(self) -> Dict:
        """从设计规划中提取结构化设计规格"""
        design_result = self._get_phase_result('design_planning')
        # 解析JSON格式的设计规格
        import json
        import re
        
        # 提取JSON部分
        json_match = re.search(r'```json\s*({.*?})\s*```', design_result, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        return {}
    
    def _extract_layer_config(self) -> Dict:
        """从图层路由中提取配置信息"""
        routing_result = self._get_phase_result('layer_routing')
        # 类似地提取结构化配置
        return {}
    
    def _phase_layer_routing(self, event_info: Dict) -> Iterator[List[Message]]:
        """图层路由阶段"""
        design_result = self._get_phase_result('design_planning')
        
        routing_message = Message(
            'user',
            f"基于设计方案，分配图层执行代理。\n\n设计方案：{design_result}"
        )
        
        for response in self.routing_agent.run([routing_message]):
            yield response
            self._save_phase_result('layer_routing', response)
    
    def _phase_layer_generation(self, event_info: Dict) -> Iterator[List[Message]]:
        """图层生成阶段 - 改进版"""
        # 直接使用结构化的设计规格
        design_specs = self._extract_design_specs()
        layer_config = self._extract_layer_config()
        
        # 为每个图层生成具体的执行指令
        for layer_name, layer_spec in design_specs.get('layers', {}).items():
            layer_message = Message(
                'user',
                f"生成{layer_name}图层。\n\n规格：{json.dumps(layer_spec, ensure_ascii=False)}"
            )
            
            for response in self.layer_router.run([layer_message]):
                yield response
                self._save_layer_result(layer_name, response)
        
        # 汇总所有图层结果
        all_layers = self._collect_layer_results()
        self._save_phase_result('layer_generation', all_layers)
    
    def _save_layer_result(self, layer_name: str, result: List[Message]):
        """保存单个图层的生成结果"""
        # 保存到专门的图层结果目录
        pass
    
    def _collect_layer_results(self) -> Dict:
        """收集所有图层的生成结果"""
        # 收集所有图层文件和配置
        return {}
    
    def _phase_html_rendering(self, event_info: Dict) -> Iterator[List[Message]]:
        """HTML渲染阶段"""
        # 收集所有前期结果
        all_results = self._collect_all_phase_results()
        
        render_message = Message(
            'user',
            f"生成最终HTML Banner。\n\n项目信息：{event_info}\n\n生成结果：{all_results}"
        )
        
        for response in self.render_agent.run([render_message]):
            yield response
            self._save_phase_result('html_rendering', response)
    
    def _phase_vl_optimization(self, event_info: Dict) -> Iterator[List[Message]]:
        """VL验证优化阶段"""
        html_result = self._get_phase_result('html_rendering')
        
        # 生成截图
        screenshot_path = self._take_html_screenshot(html_result)
        
        if screenshot_path:
            # 使用VL模型进行验证
            vl_message = Message(
                'user',
                [
                    ContentItem(text=f"请验证Banner质量。设计要求：{event_info}"),
                    ContentItem(image=screenshot_path)
                ]
            )
            
            for response in self.vl_validation_agent.run([vl_message]):
                yield response
                
                # 如果需要优化，调用优化agent
                if self._should_optimize(response):
                    optimization_message = Message(
                        'user',
                        f"根据VL反馈优化HTML。\n\n当前HTML：{html_result}\n\nVL反馈：{response}"
                    )
                    
                    for opt_response in self.html_optimization_agent.run([optimization_message]):
                        yield opt_response
                        self._save_phase_result('vl_optimization', opt_response)
    
    def _phase_final_report(self, event_info: Dict) -> Iterator[List[Message]]:
        """最终报告阶段"""
        final_report = self._generate_comprehensive_report(event_info)
        
        yield [Message('assistant', f"Banner生成完成！\n\n{final_report}")]
    
    def _create_svg_layer_agents(self) -> List[Agent]:
        """创建SVG图层生成代理"""
        from ..agents.layer_agents import LayerAgentsFactory
        
        layer_factory = LayerAgentsFactory(
            llm_config={'model': 'qwen-max'},
            progress_tracker=self.progress_tracker,
            file_saver=self.file_saver
        )
        
        return [
            layer_factory.create_text_layer_agent(),
            layer_factory.create_logo_layer_agent(), 
            layer_factory.create_layout_layer_agent(),
            layer_factory.create_effects_layer_agent()
        ]
    
    def _create_image_layer_agents(self) -> List[Agent]:
        """创建图像图层生成代理"""
        from ..agents.layer_agents import LayerAgentsFactory
        
        layer_factory = LayerAgentsFactory(
            llm_config={'model': 'qwen-max'},
            progress_tracker=self.progress_tracker,
            file_saver=self.file_saver
        )
        
        return [
            layer_factory.create_background_layer_agent(),
            layer_factory.create_main_element_layer_agent()
        ]
    
    def _collect_all_phase_results(self) -> Dict:
        """收集所有阶段结果"""
        return {
            'event_analysis': self._get_phase_result('event_analysis'),
            'marketing_planning': self._get_phase_result('marketing_planning'),
            'design_planning': self._get_phase_result('design_planning'),
            'layer_routing': self._get_phase_result('layer_routing'),
            'layer_generation': self._get_phase_result('layer_generation'),
            'html_rendering': self._get_phase_result('html_rendering')
        }
    
    def _take_html_screenshot(self, html_result: str) -> str:
        """生成HTML截图"""
        # 实现HTML截图逻辑
        return None
    
    def _should_optimize(self, vl_response: List[Message]) -> bool:
        """判断是否需要优化"""
        # 实现优化判断逻辑
        return False
    
    def _generate_comprehensive_report(self, event_info: Dict) -> str:
        """生成综合报告"""
        all_results = self._collect_all_phase_results()
        return f"项目完成报告：\n事件：{event_info}\n结果：{all_results}"
    
    def _setup_work_directory(self) -> str:
        """设置工作目录"""
        import datetime
        import os
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 获取banner_system目录路径（当前文件的上级目录）
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        banner_system_dir = os.path.dirname(current_file_dir)  # 上级目录
        work_dir = os.path.join(banner_system_dir, f"banner_project_{timestamp}")
        
        os.makedirs(work_dir, exist_ok=True)
        return work_dir
    
    def _create_layer_router(self) -> Router:
        """创建图层生成路由器"""
        # 创建各种图层生成agent
        svg_agents = self._create_svg_layer_agents()
        image_agents = self._create_image_layer_agents()
        
        return Router(
            llm=self.llm,
            agents=svg_agents + image_agents,
            name="图层生成路由器"
        )
    
    def _extract_event_info(self, messages: List[Message]) -> Dict:
        """从消息中提取事件信息"""
        # 实现事件信息提取逻辑
        pass
    
    def _save_phase_result(self, phase: str, result: List[Message]):
        """保存阶段结果"""
        # 实现结果保存逻辑
        pass
    
    def _get_phase_result(self, phase: str) -> str:
        """获取阶段结果"""
        # 实现结果获取逻辑
        pass
    
    def _create_context_summary(self) -> str:
        """创建上下文摘要，避免信息累积"""
        context = {
            'event': self._extract_key_info(self._get_phase_result('event_analysis'), 200),
            'style': self._extract_style_guide(),
            'layout': self._extract_layout_info()
        }
        
        return json.dumps(context, ensure_ascii=False)
    
    def _extract_style_guide(self) -> Dict:
        """提取样式指南"""
        # 从营销策划和设计规划中提取颜色、字体等关键样式信息
        return {
            'colors': {'primary': '#FF0000', 'secondary': '#FFD700'},
            'fonts': {'title': '思源黑体 CN Bold', 'body': '思源黑体 CN Regular'},
            'theme': '春节传统与现代结合'
        }
    
    def _yield_progress_only(self, phase: str, detail: str = "") -> Iterator[List[Message]]:
        """只输出进度信息，不输出完整内容"""
        if self.debug_mode:
            yield [Message('assistant', f"{phase}: {detail}")]
        else:
            yield [Message('assistant', f"{phase}完成")]