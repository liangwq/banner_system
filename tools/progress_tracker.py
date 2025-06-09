import os
import json
import datetime
from qwen_agent.tools.base import BaseTool, register_tool

@register_tool('progress_tracker')
class ProgressTracker(BaseTool):
    description = '记录项目进度和状态'
    parameters = [{
        'name': 'step_name',
        'type': 'string',
        'description': '步骤名称',
        'required': True
    }, {
        'name': 'status',
        'type': 'string', 
        'description': '状态：started, in_progress, completed, failed',
        'required': True
    }, {
        'name': 'details',
        'type': 'string',
        'description': '详细信息',
        'required': False
    }]
    
    def __init__(self, work_dir: str = None):
        super().__init__()
        self.work_dir = work_dir
        
    def call(self, params: str, **kwargs) -> str:
        import json5
        params = json5.loads(params)
        
        if self.work_dir is None:
            self.work_dir = os.getcwd()
        
        progress_info = {
            'step_name': params['step_name'],
            'status': params['status'],
            'details': params.get('details', ''),
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        progress_path = os.path.join(self.work_dir, 'progress.json')
        
        if os.path.exists(progress_path):
            with open(progress_path, 'r', encoding='utf-8') as f:
                progress_log = json.load(f)
        else:
            progress_log = []
            
        progress_log.append(progress_info)
        
        with open(progress_path, 'w', encoding='utf-8') as f:
            json.dump(progress_log, f, ensure_ascii=False, indent=2)
            
        return json.dumps({
            'status': 'success',
            'message': f'进度已记录：{params["step_name"]} - {params["status"]}'
        }, ensure_ascii=False)