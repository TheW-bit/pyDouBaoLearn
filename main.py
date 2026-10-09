import json
from stats import calculate_average, calculate_max, calculate_min, get_failed_students

def main() -> None:
    students = [
        {"name": "张三", "scores": 80},
        {"name": "李四", "scores": 95},
        {"name": "王五", "scores": 75},
        {"name": "赵六", "scores": 90},
        {"name": "孙七", "scores": 85}
    ]
    scores = [student["scores"] for student in students]

    result = {
        "average": round(calculate_average(scores), 2),
        "highest": calculate_max(scores),
        "lowest": calculate_min(scores),
        "failed_students": get_failed_students(students)
    }

    with open("score_stats.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)

    print("结果已保存为score_stats.json文件",
          json.dumps(result, ensure_ascii=False, indent=4)
          )

if __name__ == "__main__":
    main()