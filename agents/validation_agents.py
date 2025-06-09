from typing import List, Dict, Optional
from qwen_agent.agents import Assistant
from qwen_agent import Agent
from qwen_agent.llm import get_chat_model
from qwen_agent.llm.schema import ContentItem, Message
import os
import base64
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image
import time
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service  # 添加这行导入

class ValidationAgentsFactory:
    """验证和优化Agent工厂类"""
    
    def __init__(self, llm_config: Dict, progress_tracker, file_saver):
        self.llm_config = llm_config
        self.llm_config_vl = {'model': 'qwen-vl-max', 'model_server': 'dashscope'}
        self.progress_tracker = progress_tracker
        self.file_saver = file_saver
        self.vl_model = get_chat_model(self.llm_config_vl)
    
    def create_html_screenshot_tool(self):
        """创建HTML截图工具"""
        def take_screenshot(html_file_path: str, output_path: str, width: int = 800, height: int = 600) -> str:
            """对HTML文件进行截图"""
            try:
                # 配置Chrome选项
                chrome_options = Options()
                chrome_options.add_argument('--headless')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument(f'--window-size={width},{height}')
                
                # 使用webdriver-manager自动管理ChromeDriver
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
                
                # 打开HTML文件
                file_url = f"file://{os.path.abspath(html_file_path)}"
                driver.get(file_url)
                
                # 等待页面加载
                time.sleep(2)
                
                # 截图
                driver.save_screenshot(output_path)
                driver.quit()
                
                return output_path
            except Exception as e:
                print(f"截图失败: {e}")
                return None
        
        return take_screenshot
    
    def create_vl_validation_agent(self) -> Agent:
        """创建基于VL模型的验证Agent"""
        return Assistant(
            name="VL视觉验证专家",
            description="基于Qwen VL模型的Banner视觉效果验证专家",
            system_message="""# 角色
你是一位专业的Banner视觉效果验证专家，具备以下能力：

## 核心技能
### 技能1：视觉质量评估
- 分析Banner的整体视觉效果和设计质量
- 评估色彩搭配、字体选择、布局合理性
- 检查视觉层次和信息传达效果
- 评估品牌调性和目标受众匹配度

### 技能2：技术质量检测
- 检查HTML代码的规范性和兼容性
- 验证响应式设计效果
- 检测可能的显示问题和bug
- 评估加载性能和用户体验

### 技能3：营销效果预测
- 基于视觉心理学评估吸引力
- 预测点击率和转化效果
- 分析竞争力和差异化程度
- 提供投放建议和优化方向

## 评估标准
1. **视觉吸引力** (1-10分)：色彩、构图、创意度
2. **信息传达** (1-10分)：文字清晰度、层次结构、核心信息突出
3. **品牌一致性** (1-10分)：与品牌调性匹配度
4. **技术质量** (1-10分)：代码规范、兼容性、性能
5. **营销效果** (1-10分)：预期点击率、转化潜力

## 输出要求
- 提供详细的评分和分析报告
- 指出具体的问题和改进建议
- 给出是否需要优化的明确建议
- 如需优化，提供具体的优化方向""",
            function_list=[self.progress_tracker, self.file_saver],
            llm=self.llm_config_vl
        )
    
    def create_html_optimization_agent(self) -> Agent:
        """创建HTML优化Agent"""
        return Assistant(
            name="HTML优化专家",
            description="专业的HTML Banner优化专家，负责根据VL评测结果优化HTML代码",
            system_message="""# 角色
你是一位专业的HTML Banner优化专家，专门根据视觉评测反馈优化HTML代码。

## 核心技能
### 技能1：代码优化
- 根据VL模型评测结果调整HTML结构
- 优化CSS样式，改善视觉效果
- 调整布局、颜色、字体、间距等设计元素
- 确保代码的规范性和兼容性

### 技能2：视觉效果改进
- 基于评测反馈调整色彩搭配
- 优化文字排版和视觉层次
- 改善整体构图和平衡感
- 增强视觉吸引力和品牌表现力

### 技能3：性能优化
- 优化代码结构，提升加载速度
- 确保响应式设计效果
- 改善用户体验和交互效果

## 优化原则
1. **保持核心信息不变**：确保营销信息和品牌元素完整
2. **渐进式改进**：每次优化聚焦1-2个主要问题
3. **数据驱动**：严格按照VL评测反馈进行针对性优化
4. **兼容性优先**：确保在各种设备和浏览器上正常显示

## 输出要求
- 提供完整的优化后HTML代码
- 说明具体的优化内容和理由
- 预期的改进效果说明""",
            function_list=[self.progress_tracker, self.file_saver],
            llm=self.llm_config
        )
    
    def validate_with_vl_model(self, screenshot_path: str, html_content: str, design_requirements: str) -> Dict:
        """使用VL模型验证Banner效果"""
        try:
            # 构建VL模型输入
            messages = [{
                'role': 'user',
                'content': [
                    {
                        'text': f"""请对这个Banner设计进行专业评估：
                        
设计要求：{design_requirements}

HTML代码：
{html_content}

请从以下维度进行评分（1-10分）：
1. 视觉吸引力：色彩、构图、创意度
2. 信息传达：文字清晰度、层次结构、核心信息突出
3. 品牌一致性：与品牌调性匹配度
4. 技术质量：代码规范、兼容性、性能
5. 营销效果：预期点击率、转化潜力

请提供详细分析和具体改进建议。如果总分低于35分，建议进行优化。"""
                    },
                    {
                        'image': screenshot_path
                    }
                ]
            }]
            
            # 调用VL模型
            response = self.vl_model.chat(messages)
            
            # 解析响应
            validation_result = {
                'status': 'success',
                'analysis': response[-1]['content'] if response else '评估失败',
                'screenshot_path': screenshot_path,
                'timestamp': time.time()
            }
            
            return validation_result
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'screenshot_path': screenshot_path,
                'timestamp': time.time()
            }