"""
    成绩统计核心逻辑，只做计算，不碰文件，不打印
"""

def calculate_average(scores:list[float]) -> float:
    """Calculate the average score from a list of scores."""
    return sum(scores) / len(scores)
def calculate_max(scores:list[ float]) -> float:
    """Calculate the maximum score from a list of scores."""
    return max(scores)
def calculate_min(scores:list[float]) -> float:
    """Calculate the minimum score from a list of scores."""
    return min(scores)

def get_failed_students(students: list[dict]) -> list[dict]:
    """Get the students who failed the course."""
    return [s for s in students if s["scores"] < 60]
