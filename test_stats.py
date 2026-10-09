"""
stats.py 的自动化测试。
运行方式（在项目根目录、venv 环境下）：
    python -m pytest test_stats.py -v
"""
from stats import (
    calculate_average,
    calculate_max,
    calculate_min,
    get_failed_students,
)


def test_calculate_average():
    """平均分：(80+95+75+90+85)/5 = 85.0"""
    assert calculate_average([80, 95, 75, 90, 85]) == 85.0


def test_calculate_max():
    """最高分"""
    assert calculate_max([80, 95, 75, 90, 85]) == 95


def test_calculate_min():
    """最低分"""
    assert calculate_min([80, 95, 75, 90, 85]) == 75


def test_get_failed_students():
    """只有低于 60 分才是不及格；正好 60 分算及格"""
    students = [
        {"name": "张三", "scores": 80},
        {"name": "李四", "scores": 55},   # 不及格
        {"name": "王五", "scores": 60},   # 及格，不能进名单
    ]
    names = [s["name"] for s in get_failed_students(students)]
    assert names == ["李四"]


def test_get_failed_students_empty():
    """空列表应返回空列表，而不是报错"""
    assert get_failed_students([]) == []
