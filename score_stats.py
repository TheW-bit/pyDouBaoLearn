import json

def calculate_average(scores):
    """Calculate the average score from a list of scores."""
    return sum(scores) / len(scores)
def calculate_max(scores):
    """Calculate the maximum score from a list of scores."""
    return max(scores)
def calculate_min(scores):
    """Calculate the minimum score from a list of scores."""
    return min(scores)

def main():
    try:
        # 定义5个学生的名字以及成绩
        students = [
            {"name": "张三", "scores": 80},
            {"name": "李四", "scores": 95},
            {"name": "王五", "scores": 75},
            {"name": "赵六", "scores": 90},
            {"name": "孙七", "scores": 85}
        ]

        # 提取所有学生的分数
        scores = [student["scores"] for student in students]

        # 2,过滤不及格的学生 <60 分的学生
        filed_students = [student for student in students if student["scores"] <= 60]

        # 3,计算平均分,最高分，最低分
        average_score = calculate_average(scores)
        max_score = calculate_max(scores)
        min_score = calculate_min(scores)


        # 整理结果
        result = {
            "average":round(average_score,2),
            "highest":max_score,
            "lowest":min_score,
            "failed_students":filed_students
        }

        # 将结果保存为JSON文件
        with open("score_stats.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=4)

        print("结果已保存为score_stats.json文件")
        print(json.dumps(result, ensure_ascii=False, indent=4)) # 打印结果


    except ZeroDivisionError:
        print("没有学生,无法计算成绩")

    except KeyError as  e:
        print(f"错误：学生缺少必要字段：{e}")

    except (TypeError, ValueError) as e:
        print(f"错误：成绩数据格式不正确：{e}")

    except OSError as e:
        print(f"文件操作失败：{e}")

    except Exception as e:
        print(f"发生未知错误：{e}")





if __name__ == "__main__":
    try:
        main()

    except Exception as e:
        print(f"发生未知错误,程序启动失败：{e}")