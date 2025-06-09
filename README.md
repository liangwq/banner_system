# Banner 生成系统
这是一个基于 Qwen Agent Workflow 的 Banner 图片自动化生成系统。

## 项目结构
```
├── __init__.py
├── 
agents/                           
# Agent 定义
│   ├── execution_agents.py
│   ├── layer_agents.py
│   ├── top_agents.py
│   └── validation_agents.py
├── background_image_generator.
py     # 背景图片生成器
├── background_layer_filter_agent.
py  # 背景图层筛选 Agent
├── 
core/                             
# 核心逻辑
│   ├── banner_workflow.
py            # Banner 生成工作流
│   ├── enhanced_system.
py            # 增强的 Banner 系统
│   └── system.
py                     # 基础 
Banner 系统
├── 
examples/                         
# 示例代码
│   └── workflow_demo.
py              # 工作流演示
├── 
prompts/                          
# Prompt 定义
│   ├── __init__.py
│   ├── event_analysis_prompt.py
│   └── layer_design_prompt.py
├── svg_code_generator.
py             # SVG 代码生成器
├── svg_layer_filter_agent.
py         # SVG 图层筛选 Agent
├── 
tools/                            
# 工具类
│   ├── enhanced_tools.py
│   ├── file_saver.
py                 # 文件保存工具
│   └── progress_tracker.
py           # 进度追踪工具
└── 
utils/                            
# 辅助函数
    └── helpers.py
```
## 核心功能
项目核心在于 core/banner_workflow.py 文件中定义的 BannerWorkflow 类。该工作流通过一系列 Agent 的协作，实现从事件分析、营销策划、设计规划、图层生成到最终 HTML Banner 渲染和优化的完整流程。

主要阶段包括：

1. 事件分析 (Event Analysis) ：对输入的事件信息进行深度分析。
2. 营销策划 (Marketing Planning) ：基于事件分析结果，制定营销策略。
3. 设计规划 (Design Planning) ：根据营销策略，规划 Banner 的图层设计。
4. 图层路由 (Layer Routing) ：根据设计规划，将图层生成任务分配给合适的 Agent。
5. 图层生成 (Layer Generation) ：各个 Agent 生成具体的图层内容（例如背景、SVG 元素等）。
6. HTML 渲染 (HTML Rendering) ：将所有图层合成为最终的 HTML Banner。
7. VL 验证优化 (VL Validation & Optimization) ：使用视觉语言模型 (VL) 对生成的 Banner 进行质量验证，并根据反馈进行优化。
## 如何运行
可以参考 examples/workflow_demo.py 中的示例代码来运行 Banner 生成系统。

## 主要技术栈
- Qwen Agent: 构建智能体和工作流的核心框架。
- LLM (Large Language Model): 用于文本理解、生成和决策，例如 qwen-max 。
- Python
## 如何贡献
(这部分可以根据项目的实际情况填写，例如：)

欢迎提交 Pull Request 或 Issue 来改进本项目。

## 许可证
(请根据项目实际情况添加许可证信息，例如 MIT, Apache 2.0 等)