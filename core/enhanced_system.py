from .banner_workflow import BannerWorkflow
from .system import EnhancedBannerSystem
from typing import Dict, Any

class WorkflowEnhancedBannerSystem(EnhancedBannerSystem):
    """增强的Banner系统，集成Workflow支持"""
    
    def __init__(self, llm_config: Dict = None, use_workflow: bool = True):
        if use_workflow:
            # 使用新的Workflow实现
            self.workflow = BannerWorkflow(llm_config)
            self.llm_config = llm_config or {'model': 'qwen-max'}
            self.work_dir = self.workflow.work_dir
        else:
            # 使用原有实现
            super().__init__(llm_config)
    
    def generate_banner(self, event_name: str, additional_requirements: str = "") -> Dict[str, Any]:
        """生成Banner的主流程"""
        if hasattr(self, 'workflow'):
            return self._generate_with_workflow(event_name, additional_requirements)
        else:
            return super().generate_banner(event_name, additional_requirements)
    
    def _generate_with_workflow(self, event_name: str, additional_requirements: str) -> Dict[str, Any]:
        """使用Workflow生成Banner"""
        from qwen_agent.llm.schema import Message
        
        # 构建输入消息
        input_message = Message(
            'user',
            f"生成Banner项目。事件名称：{event_name}。附加要求：{additional_requirements}"
        )
        
        try:
            # 执行workflow
            all_responses = []
            for responses in self.workflow.run([input_message]):
                all_responses.extend(responses)
                # 实时输出进度
                for response in responses:
                    if response.role == 'assistant':
                        print(f"Workflow进度: {response.content[:100]}...")
            
            return {
                'status': 'success',
                'work_dir': self.work_dir,
                'responses': all_responses,
                'message': f'Banner生成完成，使用Workflow模式，工作目录：{self.work_dir}'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'work_dir': self.work_dir,
                'error': str(e),
                'message': f'Workflow Banner生成失败：{e}'
            }