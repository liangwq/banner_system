import os
import json
import datetime
from typing import Dict
from qwen_agent.tools.base import BaseTool, register_tool

@register_tool('enhanced_file_saver')
class EnhancedFileSaver(BaseTool):
    description = '保存生成的物料文件并记录到项目清单中'
    parameters = [{
        'name': 'content',
        'type': 'string', 
        'description': '要保存的内容',
        'required': True
    }, {
        'name': 'filename',
        'type': 'string',
        'description': '文件名',
        'required': True
    }, {
        'name': 'file_type',
        'type': 'string',
        'description': '文件类型：html, css, js, png, jpg, txt等',
        'required': True
    }, {
        'name': 'description',
        'type': 'string',
        'description': '文件描述',
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
        
        # 根据文件类型创建子目录
        file_type = params['file_type']
        if file_type in ['html', 'css', 'js']:
            sub_dir = 'web'
        elif file_type in ['png', 'jpg', 'jpeg', 'gif', 'svg']:
            sub_dir = 'images'
        else:
            sub_dir = 'documents'
            
        target_dir = os.path.join(self.work_dir, sub_dir)
        os.makedirs(target_dir, exist_ok=True)
        
        file_path = os.path.join(target_dir, params['filename'])
        
        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(params['content'])
            
        # 更新文件清单
        self._update_file_manifest({
            'filename': params['filename'],
            'file_path': file_path,
            'file_type': file_type,
            'description': params.get('description', ''),
            'created_at': datetime.datetime.now().isoformat(),
            'size': len(params['content'])
        })
        
        return json.dumps({
            'status': 'success',
            'file_path': file_path,
            'message': f'文件已保存到 {file_path}'
        }, ensure_ascii=False)
    
    def _update_file_manifest(self, file_info: Dict):
        manifest_path = os.path.join(self.work_dir, 'file_manifest.json')
        
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
        else:
            manifest = {'files': []}
            
        manifest['files'].append(file_info)
        
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)