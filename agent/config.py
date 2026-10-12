# -*- coding: utf-8 -*-
"""集中配置：所有可调参数都从这里读。

读取优先级（高 → 低）：
    1. 环境变量（DEEPSEEK_API_KEY 等）
    2. 项目根目录 .env 文件（由 python-dotenv 自动加载进环境变量）
    3. key.txt 兜底（老方式，已 gitignore）

环境变量：
    DEEPSEEK_API_KEY    必填，DeepSeek 的 API Key
    DEEPSEEK_BASE_URL   可选，默认 https://api.deepseek.com
    DEEPSEEK_MODEL      可选，默认 deepseek-chat
    AGENT_MAX_ROUNDS    可选，工具调用最大轮数，默认 6
    DEEPSEEK_TIMEOUT    可选，请求超时秒数，默认 60
    CHAT_HISTORY_DB     可选，会话历史 SQLite 文件路径，默认项目根目录 chat_history.db

新手最快上手：复制 .env.example 为 .env，填上 DEEPSEEK_API_KEY，直接跑即可
（Windows 双击 start.bat，Linux/macOS 运行 ./start.sh）。
"""
import os
import logging

# 项目根目录（agent_demo/），key.txt / .env / chat_history.db 都放这里
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 自动加载项目根目录的 .env（用 python-dotenv），让"填一次 key 就能跑"更省事。
# 没装 dotenv 也不会崩：跳过加载，仍可用环境变量 / key.txt。
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except ImportError:
    pass


def _load_api_key() -> str:
    """按优先级读 key：环境变量 > .env（load_dotenv 已注入）> key.txt 兜底。"""
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

# 会话历史数据库（阶段 4：LangChain 会话记忆用 SQLite 持久化）
CHAT_HISTORY_DB = os.getenv("CHAT_HISTORY_DB", os.path.join(BASE_DIR, "chat_history.db"))


def setup_logging(level: int = logging.INFO) -> None:
    """统一日志格式，便于线上排查问题。"""
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
