import os
import json
import datetime
from typing import List, Dict, Any, Optional
from qwen_agent.multi_agent_hub import MultiAgentHub
from qwen_agent import Agent

from ..tools.file_saver import EnhancedFileSaver
from ..tools.progress_tracker import ProgressTracker
from ..agents.top_agents import TopAgentsFactory
from ..agents.validation_agents import ValidationAgentsFactory  # 新增导入
from ..utils.helpers import FileHelper
from ..prompts import prompt_manager

class EnhancedBannerSystem(MultiAgentHub):
    """增强版Banner多Agent生成系统"""
    
    def __init__(self, llm_config: Dict = None):
        self.llm_config = llm_config or {'model': 'qwen-max'}
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.work_dir = f"banner_project_{timestamp}"
        os.makedirs(self.work_dir, exist_ok=True)
        
        # 初始化工具实例
        self.file_saver = EnhancedFileSaver(self.work_dir)
        self.progress_tracker = ProgressTracker(self.work_dir)
        
        # 初始化Agent工厂
        self.top_factory = TopAgentsFactory(self.llm_config, self.progress_tracker, self.file_saver)
        
        # 新增：初始化验证Agent工厂
        self.validation_factory = ValidationAgentsFactory(
            self.llm_config, self.progress_tracker, self.file_saver
        )
        
        # 创建 VL 验证和优化 Agent
        self.vl_validation_agent = self.validation_factory.create_vl_validation_agent()
        self.html_optimization_agent = self.validation_factory.create_html_optimization_agent()
        
        # 创建截图工具
        self.screenshot_tool = self.validation_factory.create_html_screenshot_tool()
        
        # 初始化TOP层Agent
        self.top_agents = self.top_factory.create_all_top_agents()
        self._agents = self.top_agents
        
        # 初始化辅助工具
        self.file_helper = FileHelper(self.work_dir)
        
        # 设置设计文件路径
        self.design_file_path = os.path.join(self.work_dir, 'documents', 'layer_routing_plan.json')
    
    def generate_banner(self, event_name: str, additional_requirements: str = "") -> Dict[str, Any]:
        """生成Banner的主流程"""
        
        # 初始化项目信息
        project_info = {
            'event_name': event_name,
            'requirements': additional_requirements,
            'work_dir': self.work_dir,
            'created_at': datetime.datetime.now().isoformat()
        }
        
        # 保存项目信息
        with open(os.path.join(self.work_dir, 'project_info.json'), 'w', encoding='utf-8') as f:
            json.dump(project_info, f, ensure_ascii=False, indent=2)
        
        print(f"开始Banner生成项目，工作目录：{self.work_dir}")
        
        try:
            # 阶段1：TOP层智能体顺序执行
            print("\n=== 阶段1：TOP层智能体执行 ===")
            top_results = self._execute_top_agents(event_name, additional_requirements)
            
            # 阶段2：简化的图层执行
            print("\n=== 阶段2：图层执行 ===")
            layer_materials = self._execute_layers_simple(
                top_results['routing_result'],
                top_results['marketing_result']
            )
            
            # 在阶段3：HTML渲染部分修改
            print("\n=== 阶段3：HTML渲染 ===")
            
            # 创建web文件夹
            web_dir = os.path.join(self.work_dir, 'web')
            os.makedirs(web_dir, exist_ok=True)
            
            render_input = {
                'project_info': {
                    'event_name': event_name,
                    'requirements': additional_requirements
                },
                'generated_files': self._collect_generated_files_summary(),
                'layer_summary': self._create_layer_summary(layer_materials)
            }
            
            html_instruction = f"""你是一个专业的HTML Banner生成专家。请基于以下详细信息生成最终的HTML Banner卡片：
            
            ## 项目信息
            {json.dumps(render_input['project_info'], ensure_ascii=False, indent=2)}
            
            ## 生成的文件详情
            {json.dumps(render_input['generated_files'], ensure_ascii=False, indent=2)}
            
            ## 要求：
            1. 生成完整的HTML文件，包含CSS样式
            2. **使用 <img> 标签引用 assets/svg/ 目录下的SVG文件，不要直接嵌入SVG代码**
            3. **使用 <img> 标签引用 assets/images/ 目录下的图像文件**
            4. 所有资源文件路径使用相对路径（如：assets/svg/logo.svg）
            5. 创建响应式设计
            6. 确保Banner具有良好的视觉效果
            7. 包含必要的交互效果（如悬停效果）
            8. **重要：必须使用上述文件详情中列出的实际文件名和路径**
            
            ## 可用的资源文件：
            SVG文件：{[f['filename'] for f in render_input['generated_files']['generated_files'] if f['type'] == 'svg']}
            图像文件：{[f['filename'] for f in render_input['generated_files']['generated_files'] if f['type'] in ['png', 'jpg', 'jpeg']]}
            
            请直接输出HTML代码，确保正确引用所有资源文件。"""
            
            html_result = self._execute_single_agent(
                self.top_agents[4],
                html_instruction
            )
            
            # 保存HTML文件到web文件夹
            html_file_path = os.path.join(web_dir, 'banner.html')
            try:
                with open(html_file_path, 'w', encoding='utf-8') as f:
                    f.write(html_result)
                print(f"✅ HTML Banner已保存到: {html_file_path}")
            except Exception as e:
                print(f"❌ HTML文件保存失败: {e}")
            
            # 复制相关资源文件到web文件夹
            self._copy_resources_to_web(web_dir)
            
            # 阶段4：VL验证和优化（替换原有的质量验证）
            print("\n=== 阶段4：VL质量验证和优化 ===")
            
            # 构建设计要求描述
            design_requirements = f"""
            事件名称：{event_name}
            事件描述：{additional_requirements}
            营销策略：{top_results.get('marketing_plan', '')}
            设计规范：{top_results.get('layer_design', '')}
            图层路由：{top_results.get('layer_routing', '')}
            """
            
            # 执行VL验证和优化
            vl_optimization_result = self._execute_vl_validation_and_optimization(
                html_result,
                design_requirements,  # 添加 design_requirements 参数
                max_iterations=5
            )
            
            # 生成最终报告
            final_report = self._generate_final_report(
                project_info, top_results, layer_materials, 
                html_result, vl_optimization_result  # 传入 VL 验证结果
            )
            
            print(f"\n=== Banner生成完成 ===")
            print(f"工作目录：{self.work_dir}")
            print(f"最终报告：{os.path.join(self.work_dir, 'final_report.json')}")
            
            return {
                'status': 'success',
                'work_dir': self.work_dir,
                'final_report': final_report,
                'layer_materials': layer_materials,
                'message': f'Banner生成完成，所有文件保存在 {self.work_dir} 目录中'
            }
            
        except Exception as e:
            print(f"Banner生成过程中出现错误：{e}")
            return {
                'status': 'error',
                'work_dir': self.work_dir,
                'error': str(e),
                'message': f'Banner生成失败：{e}'
            }
    
    def _execute_top_agents(self, event_name: str, additional_requirements: str = ""):
        """执行TOP层智能体并在最后批量保存文件"""
        print("\n" + "="*60)
        print("开始执行TOP层Agent流程")
        print("="*60)
        
        # 创建中间结果存储
        intermediate_results = {}
        
        # 1. 事件分析 - 使用配置化的 prompt
        print("\n🔍 步骤1: 事件分析")
        print("-" * 40)
        
        # 获取事件分析的 prompt
        event_analysis_prompt = prompt_manager.get_prompt(
            'event_analysis',
            {
                'documents': '',  # 可以从知识库获取
                'samples': ''     # 可以从样例库获取
            }
        )
        
        # 构建完整的事件分析指令
        event_instruction = f"""{event_analysis_prompt}
        
    ## 当前任务
    请对事件'{event_name}'进行深度分析。
    
    **附加要求**: {additional_requirements}
    
    请按照上述角色要求和技能框架，提供完整的事件分析报告。
        """
        
        event_result = self._execute_single_agent(
            self.top_agents[0], 
            event_instruction
        )
        
        # 保存事件分析中间文件
        intermediate_results['event_analysis'] = event_result
        self._save_intermediate_file('event_analysis.md', event_result)
        print(f"✅ 事件分析完成，已保存到 event_analysis.md")
        
        # 2. 营销策划
        print("\n📊 步骤2: 营销策划")
        print("-" * 40)
        marketing_input = f"""基于事件分析结果，为'{event_name}'制定营销策划方案。
        
    事件分析结果：
    {event_result}
    
    请提供完整的营销策划方案，包括目标受众、核心策略、视觉规范等。"""
        
        marketing_result = self._execute_single_agent(self.top_agents[1], marketing_input)
        
        # 保存营销策划中间文件
        intermediate_results['marketing_plan'] = marketing_result
        self._save_intermediate_file('marketing_plan.md', marketing_result)
        print(f"✅ 营销策划完成，已保存到 marketing_plan.md")
        
        # 3. 图层设计 - 使用配置化的 prompt
        print("\n🎨 步骤3: 图层设计")
        print("-" * 40)
        
        # 获取图层设计的 prompt
        layer_design_prompt = prompt_manager.get_prompt(
            'layer_design',
            {
                'documents': f"""## 事件分析结果\n{event_result}\n\n## 营销策划方案\n{marketing_result}"""  # 同时传入事件分析和营销策划结果
            }
        )
        
        # 构建完整的图层设计指令
        design_instruction = f"""{layer_design_prompt}
        
    ## 当前任务
    基于事件分析和营销策划方案，制定6个图层的具体设计要求。
    
    **事件分析结果**：
    {event_result}
    
    **营销策划方案**：
    {marketing_result}
    
    **事件名称**: {event_name}
    **附加要求**: {additional_requirements}
    
    请按照上述角色要求和技能框架，提供详细的图层设计方案，包括每个图层的具体要求。
        """
        
        design_result = self._execute_single_agent(self.top_agents[2], design_instruction)
        
        # 保存图层设计中间文件
        intermediate_results['layer_design'] = design_result
        self._save_intermediate_file('layer_design.md', design_result)
        print(f"✅ 图层设计完成，已保存到 layer_design.md")
        
        # 4. 图层路由
        print("\n🔀 步骤4: 图层路由")
        print("-" * 40)
        routing_input = f"""基于图层设计方案，分析并分配每个图层给相应的执行代理。
        
    图层设计方案：
    {design_result}
    
    营销策划参考：
    {marketing_result}
    
    请生成完整的路由分配方案，并以JSON格式输出图层配置信息。"""
        
        routing_result = self._execute_single_agent(self.top_agents[3], routing_input)
        
        # 保存图层路由中间文件
        intermediate_results['layer_routing'] = routing_result
        self._save_intermediate_file('layer_routing.md', routing_result)
        self._save_intermediate_file('layer_routing_plan.json', routing_result)
        print(f"✅ 图层路由完成，已保存到 layer_routing.md 和 layer_routing_plan.json")
        
        # 保存完整的中间结果汇总
        self._save_intermediate_file('intermediate_results_summary.json', 
                                    json.dumps(intermediate_results, ensure_ascii=False, indent=2))
        
        return {
            'event_result': event_result,
            'marketing_result': marketing_result, 
            'design_result': design_result,
            'routing_result': routing_result,
            'intermediate_files': intermediate_results
        }
    
    def _save_intermediate_file(self, filename: str, content: str):
        """保存中间文件到documents目录"""
        docs_dir = os.path.join(self.work_dir, 'documents')
        os.makedirs(docs_dir, exist_ok=True)
        
        file_path = os.path.join(docs_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"   📄 中间文件已保存: {filename}")
    
    def _execute_layers_simple(self, routing_result: str, marketing_context: str) -> Dict[str, Any]:
        """简化的图层执行逻辑 - 直接使用生成器"""
        
        # 定义标准图层配置
        standard_layers = [
            {
                "layer_name": "布局层",
                "generator_type": "svg",
                "output_file": "layout_structure.svg"
            },
            {
                "layer_name": "背景层", 
                "generator_type": "image",
                "output_file": "background.png"
            },
            {
                "layer_name": "主要素层",
                "generator_type": "image", 
                "output_file": "main_element.png"
            },
            {
                "layer_name": "文字层",
                "generator_type": "svg",
                "output_file": "text_content.svg"
            },
            {
                "layer_name": "表意标识层",
                "generator_type": "svg",
                "output_file": "logo.svg"
            },
            {
                "layer_name": "效果层",
                "generator_type": "svg",
                "output_file": "effects.svg"
            }
        ]
        
        layer_materials = {
            'execution_log': [],
            'layer_outputs': {},
            'file_manifest': []
        }
        
        print(f"开始执行图层生成，共{len(standard_layers)}个图层")
        
        # 创建svg和images子目录，与documents同级
        svg_dir = os.path.join(self.work_dir, 'svg')
        images_dir = os.path.join(self.work_dir, 'images')
        os.makedirs(svg_dir, exist_ok=True)
        os.makedirs(images_dir, exist_ok=True)
        
        # 直接执行每个图层
        for layer_config in standard_layers:
            layer_name = layer_config["layer_name"]
            generator_type = layer_config["generator_type"]
            output_file = layer_config["output_file"]
            
            print(f"\n执行图层: {layer_name} (类型: {generator_type})")
            
            try:
                # 根据生成器类型选择对应的执行器
                if generator_type == "svg":
                    result = self._execute_svg_layer(layer_name, marketing_context, svg_dir)
                else:  # image
                    result = self._execute_image_layer(layer_name, marketing_context, images_dir)
                
                layer_materials['layer_outputs'][layer_name] = {
                    'status': 'success',
                    'generator_type': generator_type,
                    'output_file': output_file,
                    'result': result[:200] + '...' if len(str(result)) > 200 else str(result)
                }
                
                print(f"✅ {layer_name}执行完成")
                
            except Exception as e:
                print(f"❌ {layer_name}执行失败: {str(e)}")
                layer_materials['layer_outputs'][layer_name] = {
                    'status': 'failed',
                    'error': str(e)
                }
        
        return layer_materials
    
    def _execute_svg_layer(self, layer_name, layer_routing_result, output_dir=None):
        """执行SVG图层生成"""
        try:
            # 导入create_generator函数而不是直接导入类
            from ..svg_code_generator import create_generator
            
            # 如果没有指定输出目录，使用工作目录下的svg子目录
            if output_dir is None:
                output_dir = os.path.join(self.work_dir, 'svg')
                os.makedirs(output_dir, exist_ok=True)
            
            # 图层名称映射：将简化名称转换为完整图层类型
            layer_mapping = {
                '布局层': '布局图层',
                '背景层': '背景图层', 
                '主要素层': '主元素图层',
                '文字层': '文字图层',
                '表意标识层': '表意标识图层',
                '效果层': '效果图层'
            }
            
            # 转换图层名称
            target_layer = layer_mapping.get(layer_name, layer_name)
            
            # 使用create_generator函数创建生成器（参考已验证的代码）
            generator = create_generator(
                output_dir=output_dir,
                layer_type=target_layer
            )
            
            # 确定输入文件路径
            if isinstance(layer_routing_result, dict) and 'routing_file_path' in layer_routing_result:
                file_path = layer_routing_result['routing_file_path']
            else:
                # 使用默认的设计文件路径
                file_path = self.design_file_path
            
            print(f"🎨 开始生成 {layer_name} SVG，输入文件: {file_path}")
            
            # 执行SVG生成（使用process_file方法）
            result = generator.process_file(file_path, target_layer)
            
            if result.get('status') == 'success':
                print(f"✅ {layer_name} SVG生成成功")
                print(f"   生成文件数量: {result.get('count', 0)}")
                for file_info in result.get('saved_files', []):
                    print(f"   - {file_info.get('filename', 'unknown')}: {file_info.get('file_path', 'unknown')}")
            else:
                print(f"❌ {layer_name} SVG生成失败: {result.get('error', 'Unknown error')}")
            
            return result
            
        except ImportError as e:
            error_msg = f"无法导入create_generator: {str(e)}"
            print(f"❌ {error_msg}")
            return {'status': 'error', 'error': error_msg}
        except Exception as e:
            error_msg = f"SVG图层生成失败: {str(e)}"
            print(f"❌ {error_msg}")
            return {'status': 'error', 'error': error_msg}
    
    def _execute_image_layer(self, layer_name, layer_routing_result, output_dir=None):
        """执行图像图层生成"""
        try:
            from ..background_image_generator import BackgroundImageGenerator
            
            # 如果没有指定输出目录，使用工作目录下的images子目录
            if output_dir is None:
                output_dir = os.path.join(self.work_dir, 'images')
                os.makedirs(output_dir, exist_ok=True)
            
            generator = BackgroundImageGenerator(
                layer_type=layer_name,
                output_dir=output_dir
            )
            
            # 使用图层路由结果作为输入，而不是设计文件路径
            # 如果layer_routing_result包含文件路径，使用该路径
            if isinstance(layer_routing_result, dict) and 'routing_file_path' in layer_routing_result:
                file_path = layer_routing_result['routing_file_path']
            else:
                # 否则使用默认的设计文件路径
                file_path = self.design_file_path
            
            result = generator.process_layer_design_file(
                file_path=file_path,
                layer_type=layer_name
            )
            
            return result
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def _execute_single_agent(self, agent, instruction):
        """执行单个Agent并处理错误"""
        try:
            # 检查输入长度
            if len(instruction) > 25000:
                print(f"⚠️ 指令长度过长 ({len(instruction)} 字符)，进行截断")
                instruction = instruction[:25000] + "\n\n[内容已截断，请根据上述信息继续执行]"
            
            print(f"=== 执行Agent: {agent.name} ===")
            print(f"输入消息长度: {len(instruction)} 字符")
            
            messages = [{'role': 'user', 'content': instruction}]
            response_generator = agent.run(messages)
            
            # 收集所有响应
            all_responses = []
            response_count = 0
            for response in response_generator:
                response_count += 1
                
                # 处理不同类型的响应
                if isinstance(response, list):
                    all_responses.extend(response)
                elif isinstance(response, dict):
                    all_responses.append(response)
                elif isinstance(response, str):
                    all_responses.append({'role': 'assistant', 'content': response})
            
            # 从响应中提取最终内容
            result = ""
            for msg in reversed(all_responses):
                if isinstance(msg, dict) and msg.get('role') == 'assistant':
                    content = msg.get('content', '').strip()
                    if content and content not in ['', 'None', 'null']:
                        result = content
                        break
            
            print(f"  Agent执行完成，收到 {response_count} 个响应，结果长度: {len(result)}")
            print(f"=== {agent.name} 执行完成 ===")
            
            return result
            
        except Exception as e:
            error_msg = f"Agent {agent.name} 执行失败: {str(e)}"
            print(f"❌ {error_msg}")
            return f"执行失败: {str(e)}"
    
    def _copy_resources_to_web(self, web_dir: str):
        """复制SVG和图像资源到web文件夹"""
        try:
            import shutil
            
            # 创建资源子文件夹
            assets_dir = os.path.join(web_dir, 'assets')
            os.makedirs(assets_dir, exist_ok=True)
            
            # 复制SVG文件
            svg_dir = os.path.join(self.work_dir, 'svg')
            if os.path.exists(svg_dir):
                web_svg_dir = os.path.join(assets_dir, 'svg')
                if os.path.exists(web_svg_dir):
                    shutil.rmtree(web_svg_dir)
                shutil.copytree(svg_dir, web_svg_dir)
                print(f"✅ SVG文件已复制到: {web_svg_dir}")
            
            # 复制图像文件
            images_dir = os.path.join(self.work_dir, 'images')
            if os.path.exists(images_dir):
                web_images_dir = os.path.join(assets_dir, 'images')
                if os.path.exists(web_images_dir):
                    shutil.rmtree(web_images_dir)
                shutil.copytree(images_dir, web_images_dir)
                print(f"✅ 图像文件已复制到: {web_images_dir}")
                
        except Exception as e:
            print(f"❌ 资源文件复制失败: {e}")
    
    def _collect_generated_files_summary(self):
        """收集生成文件的详细信息，包括文件内容和描述"""
        summary = {
            'generated_files': [],
            'total_count': 0,
            'by_type': {},
            'svg_sources': {},  # 存储SVG源码
            'file_descriptions': {}  # 存储文件描述
        }
        
        # 扫描工作目录中的生成文件
        for root, dirs, files in os.walk(self.work_dir):
            for file in files:
                if file.endswith(('.svg', '.png', '.jpg', '.css', '.html')):
                    file_path = os.path.join(root, file)
                    file_type = file.split('.')[-1]
                    relative_path = os.path.relpath(file_path, self.work_dir)
                    
                    file_info = {
                        'filename': file,
                        'path': file_path,
                        'relative_path': relative_path,
                        'type': file_type,
                        'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
                    }
                    
                    # 如果是SVG文件，读取源码内容
                    if file_type == 'svg':
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                svg_content = f.read()
                                summary['svg_sources'][file] = svg_content
                                file_info['svg_content'] = svg_content
                                
                                # 从SVG内容中提取描述信息
                                description = self._extract_svg_description(svg_content, file)
                                summary['file_descriptions'][file] = description
                                file_info['description'] = description
                        except Exception as e:
                            print(f"读取SVG文件 {file} 失败: {e}")
                            summary['svg_sources'][file] = "读取失败"
                            file_info['svg_content'] = "读取失败"
                            file_info['description'] = f"SVG文件读取失败: {e}"
                    
                    # 如果是图像文件，生成描述
                    elif file_type in ['png', 'jpg', 'jpeg']:
                        description = self._extract_image_description(file_path, file)
                        summary['file_descriptions'][file] = description
                        file_info['description'] = description
                    
                    summary['generated_files'].append(file_info)
                    summary['by_type'][file_type] = summary['by_type'].get(file_type, 0) + 1
        
        summary['total_count'] = len(summary['generated_files'])
        return summary
    
    def _extract_svg_description(self, svg_content: str, filename: str) -> str:
        """从SVG内容中提取描述信息 - 简化版本，让Agent智能处理"""
        # 直接返回SVG内容，让Qwen Agent智能分析和处理
        return f"SVG文件: {filename}\n内容: {svg_content}"
    
    def _extract_image_description(self, file_path: str, filename: str) -> str:
        """从图像文件路径和文件名提取描述信息"""
        try:
            description_parts = []
            
            # 从文件名推断图层类型
            if 'background' in filename.lower() or '背景' in filename:
                description_parts.append("背景图像")
            elif 'main_element' in filename.lower() or '主要素' in filename or 'main' in filename:
                description_parts.append("主要素图像")
            else:
                description_parts.append("图像素材")
            
            # 获取文件大小
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                if file_size > 1024 * 1024:
                    description_parts.append(f"文件大小: {file_size // (1024 * 1024)}MB")
                else:
                    description_parts.append(f"文件大小: {file_size // 1024}KB")
            
            # 从文件名提取时间戳
            import re
            timestamp_match = re.search(r'(\d{8}_\d{6})', filename)
            if timestamp_match:
                description_parts.append(f"生成时间: {timestamp_match.group(1)}")
            
            return '; '.join(description_parts)
            
        except Exception as e:
            return f"图像描述提取失败: {e}"
    
    def _create_layer_summary(self, layer_materials):
        """创建图层摘要"""
        summary = {
            'total_layers': len(layer_materials.get('layer_outputs', {})),
            'successful_layers': 0,
            'failed_layers': 0,
            'layer_details': {}
        }
        
        for layer_name, layer_info in layer_materials.get('layer_outputs', {}).items():
            if layer_info.get('status') == 'success':
                summary['successful_layers'] += 1
            else:
                summary['failed_layers'] += 1
            
            summary['layer_details'][layer_name] = {
                'status': layer_info.get('status'),
                'type': layer_info.get('generator_type'),
                'output_file': layer_info.get('output_file')
            }
        
        return summary
    
    def _generate_final_report(self, project_info: Dict, agent_results: Dict, 
                             layer_materials: Dict, html_result: str, 
                             vl_validation_result: Dict) -> Dict[str, Any]:
        """生成最终报告"""
        final_report = {
            'project_info': project_info,
            'summary': '本次Banner生成项目的完整报告',
            'results': {
                'event_analysis': agent_results.get('event_result', ''),
                'marketing_plan': agent_results.get('marketing_result', ''),
                'layer_design': agent_results.get('design_result', ''),
                'layer_routing': agent_results.get('routing_result', ''),
                'layer_materials': layer_materials,
                'html_render': html_result,
                'quality_validation': vl_validation_result
            },
            'completed_at': datetime.datetime.now().isoformat()
        }
        
        # 保存最终报告
        with open(os.path.join(self.work_dir, 'final_report.json'), 'w', encoding='utf-8') as f:
            json.dump(final_report, f, ensure_ascii=False, indent=2)
        
        return final_report
    
    def _flush_cached_files(self):
        """清理缓存文件"""
        try:
            # 清理临时文件和缓存
            import tempfile
            import shutil
            
            # 这里可以添加具体的清理逻辑
            print("缓存文件已清理")
        except Exception as e:
            print(f"清理缓存文件时出错: {e}")
    
    def _execute_vl_validation_and_optimization(self, html_result: str, design_requirements: str, max_iterations: int = 3) -> Dict[str, Any]:
        """
        执行基于 VL 模型的 HTML 效果验证和优化，保留完整的优化历史
        """
        optimization_history = []
        current_html = html_result
        
        # 创建优化历史目录
        history_dir = os.path.join(self.work_dir, 'optimization_history')
        os.makedirs(history_dir, exist_ok=True)
        
        # 保存初始HTML
        initial_html_path = os.path.join(history_dir, 'initial_banner.html')
        with open(initial_html_path, 'w', encoding='utf-8') as f:
            f.write(html_result)
        
        for iteration in range(max_iterations):
            print(f"\n--- VL 验证迭代 {iteration + 1}/{max_iterations} ---")
            
            # 步骤1：对当前 HTML 进行截图
            try:
                screenshot_path = self._take_html_screenshot(current_html, iteration)
                if not screenshot_path:
                    break
                print(f"HTML 截图已保存: {screenshot_path}")
            except Exception as e:
                print(f"截图失败: {e}")
                break
            
            # 步骤2：使用 VL 模型进行验证
            try:
                vl_validation_result = self.validation_factory.validate_with_vl_model(
                    screenshot_path, current_html, design_requirements
                )
                print(f"VL 验证完成，评分: {vl_validation_result.get('score', 'N/A')}")
                
                # 保存验证结果
                validation_result_path = os.path.join(history_dir, f'validation_result_iter_{iteration}.json')
                with open(validation_result_path, 'w', encoding='utf-8') as f:
                    json.dump(vl_validation_result, f, ensure_ascii=False, indent=2)
                    
            except Exception as e:
                print(f"VL 验证失败: {e}")
                break
            
            # 步骤3：判断是否需要优化
            needs_optimization = self._should_optimize(vl_validation_result)
            
            # 记录当前迭代结果
            iteration_result = {
                'iteration': iteration + 1,
                'screenshot_path': screenshot_path,
                'html_file_path': os.path.join(self.work_dir, 'debug', 'vl_optimization', f'banner_iter_{iteration}.html'),
                'validation_result_path': validation_result_path,
                'vl_validation': vl_validation_result,
                'needs_optimization': needs_optimization,
                'html_content': current_html,
                'timestamp': datetime.datetime.now().isoformat()
            }
            
            if not needs_optimization:
                print("HTML 质量已达标，无需进一步优化")
                iteration_result['optimization_result'] = "质量达标，优化完成"
                optimization_history.append(iteration_result)
                break
            
            # 步骤4：执行 HTML 优化（增强中间物料利用）
            if iteration < max_iterations - 1:
                try:
                    # 收集当前可用的资源信息
                    available_resources = self._collect_generated_files_summary()
                    
                    optimization_input = {
                        'current_html': current_html,
                        'vl_feedback': vl_validation_result.get('feedback', ''),
                        'suggestions': vl_validation_result.get('suggestions', []),
                        'score': vl_validation_result.get('score', 0),
                        'available_resources': available_resources,  # 添加可用资源信息
                        'design_requirements': design_requirements
                    }
                    
                    # 构建更详细的优化指令
                    optimization_instruction = f"""
                    根据 VL 模型反馈优化 HTML 代码。
                    
                    当前评分: {optimization_input['score']}
                    反馈: {optimization_input['vl_feedback']}
                    建议: {optimization_input['suggestions']}
                    
                    可用资源文件:
                    {json.dumps(available_resources, ensure_ascii=False, indent=2)}
                    
                    设计要求:
                    {design_requirements}
                    
                    请充分利用上述资源文件，确保优化后的HTML:
                    1. 正确引用所有可用的SVG和图像资源
                    2. 根据VL反馈调整布局、颜色、字体等
                    3. 保持响应式设计
                    4. 提升视觉效果和用户体验
                    
                    当前 HTML:
                    {current_html}
                    """
                    
                    optimization_result = self._execute_single_agent(
                        self.html_optimization_agent,
                        optimization_instruction
                    )
                    
                    # 提取优化后的 HTML
                    optimized_html = self._extract_html_from_response(optimization_result)
                    if optimized_html:
                        current_html = optimized_html
                        print("HTML 优化完成")
                        
                        # 保存优化后的HTML
                        optimized_html_path = os.path.join(history_dir, f'optimized_banner_iter_{iteration}.html')
                        with open(optimized_html_path, 'w', encoding='utf-8') as f:
                            f.write(optimized_html)
                        iteration_result['optimized_html_path'] = optimized_html_path
                    else:
                        print("未能提取优化后的 HTML，使用原始版本")
                    
                    iteration_result['optimization_result'] = optimization_result
                    iteration_result['optimization_input'] = optimization_input
                    
                except Exception as e:
                    print(f"HTML 优化失败: {e}")
                    iteration_result['optimization_result'] = f"优化失败: {e}"
            
            optimization_history.append(iteration_result)
        
        # 保存完整的优化历史
        history_summary_path = os.path.join(history_dir, 'optimization_summary.json')
        with open(history_summary_path, 'w', encoding='utf-8') as f:
            json.dump({
                'total_iterations': len(optimization_history),
                'final_score': optimization_history[-1]['vl_validation'].get('score', 0) if optimization_history else 0,
                'optimization_history': optimization_history,
                'initial_html_path': initial_html_path,
                'created_at': datetime.datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n📊 优化历史已保存: {history_summary_path}")
        
        # 保存最终优化的 HTML
        if current_html != html_result:
            final_html_path = os.path.join(self.work_dir, 'web', 'banner_optimized.html')
            try:
                with open(final_html_path, 'w', encoding='utf-8') as f:
                    f.write(current_html)
                print(f"优化后的 HTML 已保存: {final_html_path}")
            except Exception as e:
                print(f"保存优化 HTML 失败: {e}")
        
        return {
            'final_html': current_html,
            'optimization_history': optimization_history,
            'history_summary_path': history_summary_path,
            'total_iterations': len(optimization_history),
            'final_score': optimization_history[-1]['vl_validation'].get('score', 0) if optimization_history else 0
        }
    
    def _take_html_screenshot(self, html_content: str, iteration: int) -> str:
        """
        对 HTML 内容进行截图，保留中间文件用于排查
        """
        # 创建专门的调试目录
        debug_dir = os.path.join(self.work_dir, 'debug', 'vl_optimization')
        os.makedirs(debug_dir, exist_ok=True)
        
        # 保存HTML文件（不删除，用于排查）
        html_file_path = os.path.join(debug_dir, f'banner_iter_{iteration}.html')
        with open(html_file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # 生成截图
        screenshot_path = os.path.join(debug_dir, f'banner_screenshot_iter_{iteration}.png')
        
        # 调用截图工具
        try:
            screenshot_result = self.screenshot_tool(
                html_file_path=html_file_path,
                output_path=screenshot_path
            )
            print(f"✅ 截图保存成功: {screenshot_path}")
            print(f"📄 HTML文件保存: {html_file_path}")
        except Exception as e:
            print(f"❌ 截图失败: {e}")
            return None
        
        return screenshot_path
    
    def _should_optimize(self, vl_validation_result: Dict[str, Any]) -> bool:
        """
        根据 VL 验证结果判断是否需要优化
        
        Args:
            vl_validation_result: VL 验证结果
            
        Returns:
            是否需要优化
        """
        score = vl_validation_result.get('score', 0)
        feedback = vl_validation_result.get('feedback', '').lower()
        
        # 评分低于 7 分需要优化
        if score < 7:
            return True
        
        # 包含负面关键词需要优化
        negative_keywords = ['不够', '缺乏', '问题', '改进', '优化', '调整']
        if any(keyword in feedback for keyword in negative_keywords):
            return True
        
        return False
    
    def _extract_html_from_response(self, response: str) -> Optional[str]:
        """
        从 Agent 响应中提取 HTML 代码
        
        Args:
            response: Agent 响应内容
            
        Returns:
            提取的 HTML 代码，如果未找到则返回 None
        """
        import re
        
        # 尝试匹配 HTML 代码块
        html_patterns = [
            r'```html\s*\n(.*?)\n```',
            r'```\s*\n(<!DOCTYPE html.*?)\n```',
            r'(<!DOCTYPE html.*?</html>)',
        ]
        
        for pattern in html_patterns:
            matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
            if matches:
                return matches[0].strip()
        
        # 如果没有找到代码块，检查是否整个响应就是 HTML
        if '<!DOCTYPE html' in response and '</html>' in response:
            start = response.find('<!DOCTYPE html')
            end = response.rfind('</html>') + 7
            return response[start:end].strip()
        
        return None