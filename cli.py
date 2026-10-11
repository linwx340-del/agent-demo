# -*- coding: utf-8 -*-
"""命令行入口。

运行（在 agent_demo 目录下）：
    python cli.py

首次运行前装依赖：
    pip install openai -i https://pypi.tuna.tsinghua.edu.cn/simple
"""
from openai import OpenAI

from agent import API_KEY, BASE_URL, setup_logging, run_agent


def main():
    setup_logging()

    if not API_KEY:
        print("=" * 50)
        print("未检测到 DEEPSEEK_API_KEY。")
        print()
        print("两种方式二选一（不要写进代码）：")
        print("1) 在 agent_demo 目录建 key.txt，第一行放 key（已被 .gitignore 忽略）")
        print("2) 设置环境变量 DEEPSEEK_API_KEY")
        print("=" * 50)
        return

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    print("=" * 50)
    print("多工具智能体已就绪，可用工具：")
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
        answer, trace, usage = run_agent(client, question)
        for step in trace:
            print(f"  第 {step['round']} 轮 -> 调用工具 [{step['tool']}] 参数={step['args']}")
            print(f"     -> 返回：{step['result']}")
        print(f"助手：{answer}")
        print(f"  [用量] 输入 {usage['prompt_tokens']} / 输出 {usage['completion_tokens']} / 共 {usage['total_tokens']} tokens，{usage['tool_calls']} 次工具调用，{usage['elapsed_ms']}ms")


if __name__ == "__main__":
    main()
