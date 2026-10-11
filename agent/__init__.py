# -*- coding: utf-8 -*-
"""多工具智能体核心包：配置 / 工具 / 主循环。

对外统一导出，供命令行（cli.py）、网页（app.py）、后续的 API 服务共用：
    from agent import run_agent_stream, API_KEY, BASE_URL, MODEL, TOOLS
"""
from .config import API_KEY, BASE_URL, MODEL, MAX_ROUNDS, TIMEOUT, setup_logging
from .tools import TOOLS, TOOL_FUNCTIONS
from .core import run_agent_stream, run_agent

__all__ = [
    "API_KEY", "BASE_URL", "MODEL", "MAX_ROUNDS", "TIMEOUT", "setup_logging",
    "TOOLS", "TOOL_FUNCTIONS", "run_agent_stream", "run_agent",
]
