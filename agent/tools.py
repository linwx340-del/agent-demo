# -*- coding: utf-8 -*-
"""工具实现：4 个工具函数 + 注册表 + 给大模型看的工具说明书（OpenAI function calling 格式）。

这里只依赖标准库，方便单元测试；不要在这里 import openai。
"""
import re
import ast
import string
import secrets as _secrets
import datetime

# ================= 工具函数（真正的实现） =================

def calculate(expression: str) -> str:
    """安全计算四则运算表达式，例如 '3 * (2 + 5)'"""
    expression = (expression or "").strip()
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


# ================= 注册表 =================

TOOL_FUNCTIONS = {
    "calculate": calculate,
    "get_current_time": get_current_time,
    "roll_dice": roll_dice,
    "generate_password": generate_password,
}

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
