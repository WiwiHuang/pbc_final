import sqlite3

conn = sqlite3.connect("healthpiggy.db")
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE food_logs ADD COLUMN meal_type TEXT")
    print("✅ 成功新增 meal_type 欄位")
except Exception as e:
    print("⚠️ 已存在或發生錯誤：", e)

conn.commit()
conn.close()