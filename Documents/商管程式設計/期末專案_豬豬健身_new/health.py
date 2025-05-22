def get_activity_factor(exercise_freq):
    """
    根據每週運動次數回傳活動係數與描述
    """
    if exercise_freq <= 0:
        return 1.2, "坐式生活"
    elif 1 <= exercise_freq <= 3:
        return 1.375, "輕度活動量"
    elif 4 <= exercise_freq <= 5:
        return 1.55, "中度活動量"
    elif 6 <= exercise_freq <= 7:
        return 1.725, "高度活動量"
    else:
        return 1.9, "劇烈活動量"


def calculate_tdee(gender, age, height, weight, exercise_freq):
    """
    根據性別、年齡、身高、體重與運動頻率計算 TDEE
    使用 Harris-Benedict 公式
    """
    factor, activity_level = get_activity_factor(exercise_freq)

    if gender == "男":
        bmr = 66.5 + (13.7 * weight) + (5 * height) - (6.8 * age)
    else:
        bmr = 655.1 + (9.56 * weight) + (1.85 * height) - (4.7 * age)

    tdee = round(bmr * factor)
    return tdee, activity_level


def suggest_macros(tdee, weight):
    """
    根據 TDEE 推算蛋白質、脂肪、碳水攝取量（克數）
    蛋白質 1.8 g/kg 體重、脂肪 0.8 g/kg 體重、碳水 剩餘熱量
    """
    protein_g = round(weight * 1.8)  # 每公斤1.8克蛋白質
    fat_g = round(weight * 0.8)      # 每公斤0.8克脂肪

    # 蛋白質與脂肪的熱量
    protein_kcal = protein_g * 4
    fat_kcal = fat_g * 9

    # 碳水化合物為剩餘熱量
    carb_kcal = tdee - (protein_kcal + fat_kcal)
    carb_g = round(carb_kcal / 4)

    return {
        "protein_g": protein_g,
        "fat_g": fat_g,
        "carb_g": carb_g
    }

# 測試
tdee, level = calculate_tdee("男", 25, 170, 60, 5)
macros = suggest_macros(tdee, 60)
print(f"TDEE: {tdee} kcal, 活動量：{level}")
print(f"蛋白質: {macros['protein_g']}g, 脂肪: {macros['fat_g']}g, 碳水: {macros['carb_g']}g")
