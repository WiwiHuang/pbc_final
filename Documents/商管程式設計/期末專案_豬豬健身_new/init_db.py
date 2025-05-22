import sqlite3

conn = sqlite3.connect("healthpiggy.db")
cursor = conn.cursor()

# 新增 goal 欄位
try:
    cursor.execute("ALTER TABLE users ADD COLUMN goal TEXT")
    print("✅ 已成功新增 goal 欄位！")
except Exception as e:
    print(f"⚠️ 新增失敗：{e}")

conn.commit()
conn.close()