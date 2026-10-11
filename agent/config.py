# -*- coding: utf-8 -*-
"""集中配置：所有可调参数都从这里读，优先级 = 环境变量 > key.txt 兜底。

环境变量：
    DEEPSEEK_API_KEY    必填，DeepSeek 的 API Key
    DEEPSEEK_BASE_URL   可选，默认 https://api.deepseek.com
    DEEPSEEK_MODEL      可选，默认 deepseek-chat
    AGENT_MAX_ROUNDS    可选，工具调用最大轮数，默认 6
    DEEPSEEK_TIMEOUT    可选，请求超时秒数，默认 60
"""
import os
import logging

# 项目根目录（agent_demo/），key.txt 就放在这里
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_api_key() -> str:
    """优先读环境变量 DEEPSEEK_API_KEY；没有则回退到项目根目录 key.txt（已 gitignore）。"""
    key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if key:
        return key
    key_file = os.path.join(BASE_DIR, "key.txt")
    if os.path.exists(key_file):
        with open(key_file, "r", encoding="utf-8") as f:
            key = f.read().strip()
    return key


API_KEY = _load_api_key()
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
MAX_ROUNDS = int(os.getenv("AGENT_MAX_ROUNDS", "6"))
TIMEOUT = float(os.getenv("DEEPSEEK_TIMEOUT", "60"))


def setup_logging(level: int = logging.INFO) -> None:
    """统一日志格式，便于线上排查问题（阶段 3 会接到监控里）。"""
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
