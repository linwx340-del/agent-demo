# -*- coding: utf-8 -*-
"""工具函数单元测试：不依赖网络、不依赖 openai。"""
from agent.tools import calculate, roll_dice, generate_password, get_current_time


def test_calculate_simple():
    assert calculate("3 * (2 + 5)") == "21"


def test_calculate_division():
    assert calculate("100 / 4") == "25.0"


def test_calculate_rejects_illegal_chars():
    assert calculate("3 + abc").startswith("错误")


def test_calculate_rejects_code_injection():
    # 曾经的风险：eval 直接执行任意代码；现在白名单只放行算术
    result = calculate("__import__('os').system('whoami')")
    assert result.startswith("错误")


def test_roll_dice_range():
    result = roll_dice(2, 6)
    assert "点数之和" in result


def test_roll_dice_invalid_count():
    assert "错误" in roll_dice(0, 6)


def test_roll_dice_invalid_sides():
    assert "错误" in roll_dice(1, 1)


def test_generate_password_length():
    pwd = generate_password(12)
    assert len(pwd) == 12


def test_generate_password_too_short():
    assert "错误" in generate_password(2)


def test_get_current_time_format():
    assert "星期" in get_current_time()
