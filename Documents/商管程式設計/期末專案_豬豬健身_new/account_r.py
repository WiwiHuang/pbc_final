# account.py
import sqlite3

# ✅ 使用者註冊函式
def register_user(email, name, password, school, birthday, gender, height, weight, exercise):
    """
    將新使用者資料寫入 SQLite 資料庫。
    若 email 已存在，則不允許重複註冊。
    """
    # 連接 SQLite 資料庫
    conn = sqlite3.connect('healthpiggy.db')
    cursor = conn.cursor()

    # 檢查此 email 是否已註冊
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    if cursor.fetchone():
        conn.close()
        return "❌ 此 Email 已被註冊，請使用其他信箱"

    # 插入新使用者資料
    cursor.execute('''
        INSERT INTO users (name, birthday, gender, email, school, height, weight, exercise, password)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, birthday, gender, email, school, height, weight, exercise, password))

    conn.commit()  # 提交變更
    conn.close()   # 關閉資料庫連線

    return "✅ 註冊成功！請返回登入頁面"

# ✅ 使用者登入函式
def login(email, password):
    """
    檢查使用者登入資訊是否正確。
    """
    conn = sqlite3.connect('healthpiggy.db')
    cursor = conn.cursor()

    # 查詢該 email 與密碼是否匹配
    cursor.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password))
    user = cursor.fetchone()

    conn.close()

    if user:
        return "✅ 登入成功，歡迎回來！"
    else:
        return "❌ 帳號或密碼錯誤"
