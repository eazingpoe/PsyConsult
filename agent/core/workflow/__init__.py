"""多智能体系统的工作流编排。"""

from .state import AgentOutput, AgentState


__all__ = ["AgentOutput", "AgentState", "AgentGraphManager"]


def __getattr__(name: str):
    """按需加载工作流管理器，避免包初始化时产生循环导入。"""
    if name == "AgentGraphManager":
        from .graph_manager import AgentGraphManager
        return AgentGraphManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
