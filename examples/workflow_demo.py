from banner_system.core.enhanced_system import WorkflowEnhancedBannerSystem

def demo_workflow_banner_generation():
    """演示使用Workflow的Banner生成"""
    
    # 创建增强系统（使用Workflow）
    system = WorkflowEnhancedBannerSystem(
        llm_config={'model': 'qwen-max'},
        use_workflow=True
    )
    
    # 生成Banner
    result = system.generate_banner(
        event_name="春节促销活动",
        additional_requirements="要求体现传统文化元素，色彩温暖，适合电商平台使用"
    )
    
    print(f"生成结果：{result}")

def demo_traditional_banner_generation():
    """演示使用传统方式的Banner生成（向后兼容）"""
    
    # 创建增强系统（使用传统方式）
    system = WorkflowEnhancedBannerSystem(
        llm_config={'model': 'qwen-max'},
        use_workflow=False
    )
    
    # 生成Banner
    result = system.generate_banner(
        event_name="春节促销活动",
        additional_requirements="要求体现传统文化元素，色彩温暖，适合电商平台使用"
    )
    
    print(f"生成结果：{result}")

if __name__ == '__main__':
    print("=== Workflow模式演示 ===")
    demo_workflow_banner_generation()    
    print("\n=== 传统模式演示（向后兼容）===")
    demo_traditional_banner_generation()
