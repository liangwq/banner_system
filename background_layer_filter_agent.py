import json
import os
from typing import Dict, Any, Optional
from qwen_agent.agents import Assistant
import dashscope

# 设置API密钥
dashscope.api_key = ""

class BackgroundLayerFilterAgent:
    """专门用于从设计图层内容中过滤提取指定图层信息的Agent"""
    
    def __init__(self, layer_type: str = "背景层"):
        self.layer_type = layer_type
        # 使用Assistant而不是继承Agent
        self.llm_cfg = {'model': 'qwen-max'}
        self.agent = Assistant(
            llm=self.llm_cfg,
            name='设计文本处理专家',
            description='可以根据用户指令严格把用户需要部分内容提取出来。把用户输入的设计图层内容中最接近用户需求的那一层拿出来，严格遵循用户要求只是拿那一层输出。'
        )
        
        # 设计文本处理专家的系统提示
        self.system_prompt = """
你是一个设计文本处理专家，可以根据用户指令严格把用户需要部分内容提取出来。
把用户输入的设计图层内容中最接近用户需求的那一层拿出来，严格遵循用户要求只是拿那一层输出。

注意事项：
1. 只输出用户要求的那一层内容
2. 保持原始格式和结构
3. 不要添加任何解释或额外内容
4. 如果找不到对应层，返回"未找到对应图层"
        """.strip()
    
    def set_layer_type(self, layer_type: str):
        """设置要过滤的图层类型"""
        self.layer_type = layer_type
    
    def filter_layer(self, layer_content: str, layer_type: str = None) -> str:
        """从图层内容中过滤出指定图层信息"""
        
        # 如果没有指定图层类型，使用默认的
        if layer_type is None:
            layer_type = self.layer_type
        
        # 构建消息
        messages = [
            {'role': 'system', 'content': self.system_prompt},
            {'role': 'user', 'content': f"{layer_type}\n\n{layer_content}"}
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
    
    def filter_background_layer(self, layer_content: str) -> str:
        """从图层内容中过滤出背景层信息（向后兼容方法）"""
        return self.filter_layer(layer_content, "背景层")
    
    def process_file(self, file_path: str, layer_type: str = None) -> Dict[str, Any]:
        """处理指定文件，提取指定图层内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 如果没有指定图层类型，使用默认的
            if layer_type is None:
                layer_type = self.layer_type
            
            # 使用Agent过滤图层内容
            filtered_content = self.filter_layer(content, layer_type)
            
            return {
                'source_file': file_path,
                'layer_type': layer_type,
                'filtered_background_content': filtered_content,  # 保持原字段名兼容
                'filtered_content': filtered_content,  # 新字段名
                'status': 'success'
            }
            
        except Exception as e:
            return {
                'source_file': file_path,
                'layer_type': layer_type or self.layer_type,
                'error': f'文件处理失败: {str(e)}',
                'status': 'error'
            }


def main():
    """主函数：演示图层过滤功能"""
    # 获取用户输入的图层类型
    print("请选择要提取的图层类型：")
    print("1. 背景层")
    print("2. 文字层")
    print("3. 主元素层")
    print("4. 效果层")
    print("5. 自定义图层")
    
    choice = input("请输入选择 (1-5): ").strip()
    
    layer_type_map = {
        "1": "背景层",
        "2": "文字层", 
        "3": "主元素层",
        "4": "效果层"
    }
    
    if choice in layer_type_map:
        layer_type = layer_type_map[choice]
    elif choice == "5":
        layer_type = input("请输入自定义图层类型: ").strip()
    else:
        print("无效选择，使用默认背景层")
        layer_type = "背景层"
    
    # 初始化Agent
    agent = BackgroundLayerFilterAgent(layer_type)
    
    # 指定文件路径
    file_path = "/Users/qian.lwq/Downloads/autogen_test/Qwen-Agent/banner_project_20250530_212535/documents/layer_design.md"
    
    # 处理文件
    result = agent.process_file(file_path)
    
    # 打印结果
    print("=" * 60)
    print(f"{layer_type}过滤结果")
    print("=" * 60)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 如果成功，单独显示过滤出的图层内容
    if result['status'] == 'success':
        print("\n" + "=" * 60)
        print(f"提取的{layer_type}内容")
        print("=" * 60)
        print(result['filtered_content'])


if __name__ == "__main__":
    main()