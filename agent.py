# -*- coding: utf-8 -*-
"""
多工具智能体（Agent）—— DeepSeek 函数调用版

和 RAG 的区别（一句话）：
    RAG   = 大模型 + 知识库     （检索文档，基于资料回答）
    Agent = 大模型 + 工具       （模型自己决定调用哪个工具，思考过程可见）

这个 demo 给模型配了 4 个「工具」：
    1. calculate          四则运算
    2. get_current_time   查当前时间
    3. roll_dice          掷骰子
    4. generate_password  生成随机密码

模型收到问题后，会自己判断「要不要调工具、调哪个、传什么参数」，
拿到工具返回结果后再组织成最终答案。整个过程会把调用轨迹打印出来。

首次运行前安装（PyCharm 底部 Terminal）：
    pip install openai -i https://pypi.tuna.tsinghua.edu.cn/simple

运行（在 agent_demo 目录下）：
    python agent.py

需要先设置环境变量 DEEPSEEK_API_KEY（Windows PowerShell）：
    $env:DEEPSEEK_API_KEY="sk-你的key"
"""

import os
import re
import ast
import json
import string
import secrets as _secrets
import datetime
from openai import OpenAI

# ================= 配置 =================
def _load_api_key():
    """优先读环境变量 DEEPSEEK_API_KEY；没设置则回退到同目录 key.txt（已加入 .gitignore）"""
    key = os.getenv("DEEPSEEK_API_KEY", "")
    if key:
        return key
    key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "key.txt")
    if os.path.exists(key_file):
        with open(key_file, "r", encoding="utf-8") as f:
            key = f.read().strip()
    return key


API_KEY = _load_api_key()
BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-chat"
MAX_ROUNDS = 6          # 最多允许模型连续调用几轮工具，防止死循环


# ================= 工具实现（真正的函数） =================

def calculate(expression: str) -> str:
    """安全计算四则运算表达式，例如 '3 * (2 + 5)'"""
    expression = (expression or "").strip()
    # 只允许数字、运算符、括号、小数点、空格、百分号
    if not re.fullmatch(r"[0-9+\-*/().% ]+", expression):
        return "错误：表达式含非法字符，只支持数字和 + - * / ( ) % 运算"

    # 用 ast 白名单校验，杜绝 eval 执行任意代码的风险
    allowed_nodes = (
        ast.Expression, ast.BinOp, ast.UnaryOp, ast.Add, ast.Sub, ast.Mult,
        ast.Div, ast.Mod, ast.Pow, ast.USub, ast.UAdd, ast.Constant,
    )

    def _validate(node):
        if not isinstance(node, allowed_nodes):
            raise ValueError(f"不支持的语法：{type(node).__name__}")
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
            raise ValueError("只支持数字常量")
        for child in ast.iter_child_nodes(node):
            _validate(child)

    try:
        tree = ast.parse(expression, mode="eval")
        _validate(tree)
        result = eval(compile(tree, "<calc>", "eval"), {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"计算出错：{e}"


def get_current_time() -> str:
    """返回当前日期、时间和星期"""
    now = datetime.datetime.now()
    weekdays = "一二三四五六日"
    return f"{now:%Y-%m-%d %H:%M:%S} 星期{weekdays[now.weekday()]}"


def roll_dice(count: int = 1, sides: int = 6) -> str:
    """掷 count 个 sides 面的骰子，返回每次点数和总和"""
    try:
        count, sides = int(count), int(sides)
    except (TypeError, ValueError):
        return "错误：骰子个数和面数必须是整数"
    if not (1 <= count <= 100):
        return "错误：骰子个数需在 1~100 之间"
    if not (2 <= sides <= 1000):
        return "错误：骰子面数需在 2~1000 之间"
    rolls = [_secrets.randbelow(sides) + 1 for _ in range(count)]
    return f"掷 {count} 个 {sides} 面骰子：{rolls}，点数之和 = {sum(rolls)}"


def generate_password(length: int = 16) -> str:
    """生成一个指定长度的随机强密码（含大小写字母、数字、符号）"""
    try:
        length = int(length)
    except (TypeError, ValueError):
        return "错误：密码长度必须是整数"
    if not (4 <= length <= 128):
        return "错误：密码长度需在 4~128 之间"
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(_secrets.choice(chars) for _ in range(length))


# ================= 工具注册表 =================
# 供主循环按名字查找并执行
TOOL_FUNCTIONS = {
    "calculate": calculate,
    "get_current_time": get_current_time,
    "roll_dice": roll_dice,
    "generate_password": generate_password,
}

# 供大模型看的「工具说明书」（OpenAI function calling 格式）
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "计算四则运算表达式，例如 3*(2+5) 或 100/4",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string",
                                   "description": "要计算的数学表达式，只含数字和 + - * / ( ) %"}
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前日期、时间和星期几",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "roll_dice",
            "description": "掷骰子，返回每次点数与总和",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "description": "骰子个数，默认 1"},
                    "sides": {"type": "integer", "description": "骰子面数，默认 6"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_password",
            "description": "生成随机强密码，含大小写字母、数字和符号",
            "parameters": {
                "type": "object",
                "properties": {
                    "length": {"type": "integer", "description": "密码长度，默认 16"},
                },
            },
        },
    },
]


# ================= Agent 主循环（函数调用循环） =================

def run_agent_stream(client: OpenAI, question: str):
    """
    ReAct 式循环（生成器版）：边执行边 yield 事件，供界面实时显示思考过程。

    事件有两种：
      {"type": "tool",   "round": 第几轮, "tool": 工具名, "args": 参数, "result": 工具返回}
      {"type": "answer", "content": 最终答案}
    """
    messages = [{"role": "user", "content": question}]

    for round_no in range(1, MAX_ROUNDS + 1):
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            temperature=0.0,          # 工具调用求稳，不需要发散
        )
        msg = resp.choices[0].message

        if msg.tool_calls:
            # 模型这轮决定调工具：先把这条 assistant 消息放回上下文
            messages.append(msg)
            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}

                fn = TOOL_FUNCTIONS.get(name)
                if fn is None:
                    result = f"未知工具：{name}"
                else:
                    try:
                        result = fn(**args)
                    except Exception as e:
                        result = f"工具执行出错：{e}"

                # 先把这一步「思考痕迹」交给界面，再继续
                yield {"type": "tool", "round": round_no, "tool": name,
                       "args": args, "result": str(result)}

                # 把工具结果作为 role="tool" 消息追加，tool_call_id 必须对上
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result),
                })
        else:
            # 没有 tool_calls，说明模型决定直接给出最终答案
            yield {"type": "answer", "content": msg.content or ""}
            return

    yield {"type": "answer", "content": "（达到最大调用轮数，仍未给出最终答案）"}


def run_agent(client: OpenAI, question: str):
    """
    命令行版用的普通函数：内部调用 run_agent_stream，
    返回 (最终答案, 工具调用轨迹列表)。轨迹每项为
    {"round", "tool", "args", "result"}。
    """
    answer, trace = "", []
    for ev in run_agent_stream(client, question):
        if ev["type"] == "tool":
            trace.append({"round": ev["round"], "tool": ev["tool"],
                          "args": ev["args"], "result": ev["result"]})
        else:
            answer = ev["content"]
    return answer, trace


# ================= 交互入口 =================

def main():
    if not API_KEY:
        print("=" * 50)
        print("未检测到 DEEPSEEK_API_KEY 环境变量。")
        print()
        print("Windows PowerShell 设置（临时，关闭窗口失效）：")
        print('    $env:DEEPSEEK_API_KEY="sk-你的key"')
        print()
        print("永久设置（系统环境变量）：")
        print("    此电脑 → 属性 → 高级系统设置 → 环境变量 → 新建")
        print('    变量名 DEEPSEEK_API_KEY，值填你的 key')
        print("=" * 50)
        return

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    print("=" * 50)
    print("🤖 多工具智能体已就绪，可用工具：")
    print("   · calculate 四则运算   · get_current_time 查时间")
    print("   · roll_dice 掷骰子     · generate_password 生成密码")
    print("输入 exit / 退出 可结束对话")
    print("=" * 50)

    while True:
        question = input("\n你：").strip()
        if question.lower() in ("exit", "quit", "退出"):
            print("再见！")
            break
        if not question:
            continue
        answer, trace = run_agent(client, question)
        for step in trace:
            print(f"  🔧 第 {step['round']} 轮 → 调用工具 [{step['tool']}] 参数={step['args']}")
            print(f"      ↳ 返回：{step['result']}")
        print(f"助手：{answer}")


if __name__ == "__main__":
    main()
