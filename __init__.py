from .core.system import EnhancedBannerSystem
from .tools.file_saver import EnhancedFileSaver
from .tools.progress_tracker import ProgressTracker

__version__ = "1.0.0"
__all__ = ["EnhancedBannerSystem", "EnhancedFileSaver", "ProgressTracker"]

def create_enhanced_banner_system(llm_config=None):
    """创建增强版Banner生成系统"""
    if llm_config is None:
        llm_config = {'model': 'qwen-max'}
    
    return EnhancedBannerSystem(llm_config=llm_config)