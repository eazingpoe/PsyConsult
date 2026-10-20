"""鏍稿績 Agent 妗嗘灦缁勪欢銆?"""

from .mcp.mcp_manager import MCPManager
from .workflow.state import AgentOutput, AgentState

from .memory.memory_manager import MemoryManager

__all__ = ["AgentOutput", "AgentState", "MCPManager", "AgentGraphManager", "MemoryManager"]


def __getattr__(name: str):
    """按需加载工作流管理器，避免包初始化时产生循环导入。"""
    if name == "AgentGraphManager":
        from .workflow.graph_manager import AgentGraphManager
        return AgentGraphManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
