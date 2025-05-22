from PIL import Image
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
from health import calculate_tdee, suggest_macros
from account import register_user, login
import tkinter as tk
import threading
import time
import google.generativeai as genai
import os

 # ✅ 設定 Gemini API 金鑰
API_KEY = "AIzaSyDt-ePwvoedMgCwtA4Hfde6lVrr-VTQYiQ"
genai.configure(api_key=API_KEY)

    # ✅ 定義 Gemini 建議函數
def generate_gemini_feedback(actual_calories, recommended_calories):
    if actual_calories == 0:
        return "你今天好像什麼都沒吃耶！趕快去吃飯吧～"

    diff = actual_calories - recommended_calories
    prompt = (
        f"你是一位健康建議助理，請針對以下使用者的熱量攝取狀況，提供一段語氣溫和、鼓勵且具體的飲食建議：\n"
        f"- 建議攝取熱量：{recommended_calories} kcal\n"
        f"- 實際攝取熱量：{actual_calories} kcal\n"
        f"- 熱量差異：{diff} kcal\n"
        f"請根據這些資訊，回覆一句具體而溫和的建議，控制在 2 行以內。"
    )

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return "⚠️ Gemini API 請求失敗：請稍後再試\n" + str(e)


st.set_page_config(page_title="健康豬豬系統", layout="centered")

if 'email' not in st.session_state:
    st.session_state.email = None
def get_pig_level(intake, goal):
    ratio = intake / goal
    if ratio < 0.8:
        return 1
    elif ratio < 1.0:
        return 2
    elif ratio < 1.2:
        return 3
    else:
        return 4

def show_pig_image(school, level):
    """
    顯示對應豬豬等級圖片
    """
    # 正確拼接圖片路徑
    img_path = f"images/{school}_level{level}.png"
    #st.write(f"嘗試加載圖片路徑：{img_path}")  # 日誌輸出圖片路徑，方便排查
    try:
        img = Image.open(img_path)
        # 使用 use_container_width 替代 use_column_width，並控制寬度
        st.image(img, caption=f"🐷 你的豬豬等級：Level {level}", width=250, use_container_width=False)
    except FileNotFoundError:
        st.warning(f"找不到對應等級的豬豬圖片：{img_path}")

def show_profile(email):
    st.subheader("💻 健康豬豬個人建議")
    conn = sqlite3.connect("healthpiggy.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, school, gender, birthday, height, weight, exercise FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        st.error("找不到使用者資料")
        return

    name, school, gender, birthday, height, weight, exercise = row
    age = datetime.now().year - int(birthday[:4])
    tdee, activity_level = calculate_tdee(gender, age, height, weight, exercise)
    macros = suggest_macros(tdee, weight)
    st.session_state.tdee = tdee 

    st.success(f"歡迎回來，{name}！")
    
    conn = sqlite3.connect("healthpiggy.db")
    # 查詢當天攝取熱量
    kcal_query = """
        SELECT SUM(kcal) AS total_kcal
        FROM food_logs
        WHERE email = ?
        AND date = ?;
    """
    kcal_df = pd.read_sql_query(kcal_query, conn, params=[email, date.today().isoformat()])
    conn.close()

    # 如果查詢有結果，計算豬豬等級
    if not kcal_df.empty and kcal_df['total_kcal'][0] is not None:
        today_intake = float(kcal_df['total_kcal'][0])
        st.info(f"📊 今日攝取總熱量：{today_intake:.0f} kcal")
    else:
        today_intake = 0
        st.info("📊 今日尚未記錄任何攝取熱量")


    # 計算豬豬等級
    pig_level = get_pig_level(today_intake, tdee)

    # 顯示豬豬等級圖片
    
    
    st.markdown(f"""
    - 🎂 年齡：{age} 歲
    - 🏫 學院：{school}
    - 📏 身高：{height} cm
    - ⚖️ 體重：{weight} kg
    - 🏃 活動量：{activity_level}
    - 🔥 TDEE：{tdee} kcal
    """)
    show_pig_image(school, pig_level)
    st.subheader("🍱 每日營養素建議攝取量：")
    st.markdown(f"""
    - 🥩 蛋白質：{macros['protein_g']} g  
    - 🧈 脂肪：{macros['fat_g']} g  
    - 🍚 碳水化合物：{macros['carb_g']} g  
    """)

st.title("🐷 健康豬豬互動系統")

menu = st.sidebar.radio(
    "功能選單", 
    ["首頁", "註冊", "登入", "我的健康資料", "每日身體紀錄", "每日飲食紀錄"],
    index=["首頁", "註冊", "登入", "我的健康資料", "每日身體紀錄", "每日飲食紀錄"].index(
        st.session_state.get("menu", "首頁")
    )
)

if menu == "首頁":
    st.markdown("歡迎來到 **健康豬豬系統** 🐽！請從左側選單開始使用。")

elif menu == "註冊":
    st.subheader("✍️ 註冊帳號")
    with st.form("register_form"):
        name = st.text_input("姓名")
        birthday = st.date_input(
            "出生年月日",
            value=date(2000, 1, 1),       # 預設選擇日期
            min_value=date(1900, 1, 1),   # 最早可選日期
            max_value=date.today()        # 最晚可選日期
        )

        gender = st.radio("性別", ["男", "女"], horizontal=True)
        email = st.text_input("Email")
        school_list = [
            "文學院", "社會科學院", "電機資訊學院", "工學院", "管理學院",
            "生命科學院", "生物資源暨農學院", "理學院", "公共衛生學院",
            "法律學院", "醫學院"
        ]
        school = st.selectbox("就讀學院", school_list)
        height = st.number_input("身高（cm）", 100.0, 250.0, step=0.1)
        weight = st.number_input("體重（kg）", 30.0, 200.0, step=0.1)
        exercise = st.slider("每週運動次數（有氧 / 重訓）", 0, 14, 3)
        password = st.text_input("設定密碼", type="password")
        submitted = st.form_submit_button("送出註冊")
        if submitted:
            result = register_user(email, name, password, school, birthday.strftime("%Y-%m-%d"), gender, height, weight, exercise)
            st.info(result)
            if result.startswith("✅"):
                st.session_state.menu = '登入'
                st.rerun()

elif menu == "登入":
    st.subheader("🔐 登入系統")
    email = st.text_input("Email")
    password = st.text_input("密碼", type="password")
    if st.button("登入"):
        result = login(email, password)
        if result.startswith("✅"):
            st.session_state.email = email
            st.session_state.menu = "我的健康資料"  # ← 這行新增：切換頁面狀態
            st.success("登入成功！")
            st.rerun()  # ← 重新載入頁面以顯示「我的健康資料」
        else:
            st.error(result)


elif menu == "我的健康資料":
    if st.session_state.email:
        show_profile(st.session_state.email)
    else:
        st.warning("請先登入才能查看個人資料")

elif menu == "每日身體紀錄":
    if not st.session_state.email:
        st.warning("請先登入才能記錄身體數據")
    else:
        st.subheader("✍️ 每日身體紀錄")
        today = date.today().isoformat()

        with st.form("log_form"):
            weight = st.number_input("今天的體重（kg）", min_value=30.0, max_value=200.0, step=0.1)
            fat = st.number_input("體脂率（%）", min_value=0.0, max_value=60.0, step=0.1)
            exercise_min = st.number_input("今日運動時間（分鐘）", 0, 300, step=5)
            notes = st.text_area("備註（可選）")
            submitted = st.form_submit_button("儲存紀錄")
            if submitted:
                conn = sqlite3.connect("healthpiggy.db")
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS body_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT,
                        date TEXT,
                        weight REAL,
                        fat_percentage REAL,
                        exercise_minutes INTEGER,
                        notes TEXT
                    )
                """)
                cursor.execute("INSERT INTO body_logs (email, date, weight, fat_percentage, exercise_minutes, notes) VALUES (?, ?, ?, ?, ?, ?)",
                               (st.session_state.email, today, weight, fat, exercise_min, notes))
                conn.commit()
                conn.close()
                st.success("✅ 今日紀錄已儲存！")

        st.subheader("📈 歷史紀錄趨勢")
        conn = sqlite3.connect("healthpiggy.db")
        df = pd.read_sql_query("SELECT date, weight, fat_percentage, exercise_minutes FROM body_logs WHERE email = ? ORDER BY date", conn, params=[st.session_state.email])
        conn.close()

        if not df.empty:
            st.line_chart(df.set_index("date")[["weight"]], height=250, use_container_width=True)
            st.dataframe(df.set_index("date"), use_container_width=True)
        else:
            st.info("尚無任何紀錄，快來輸入第一筆吧！")

elif menu == "每日飲食紀錄":
    import os

    if not st.session_state.email:
        st.warning("請先登入才能使用飲食紀錄功能")
        st.stop()

    st.subheader("🍱 每日飲食紀錄")

    # 讀取營養資料
    csv_path = "data_nutrition.csv"
    if not os.path.exists(csv_path):
        st.error(f"❌ 找不到資料檔案：{csv_path}")
        st.stop()

    try:
        nutrition_df = pd.read_csv(csv_path, skiprows=1)
        nutrition_df = nutrition_df.rename(columns={
            nutrition_df.columns[2]: "食物名稱",
            nutrition_df.columns[6]: "熱量(kcal)",
            nutrition_df.columns[7]: "蛋白質(g)",
            nutrition_df.columns[8]: "脂肪(g)",
            nutrition_df.columns[10]: "碳水化合物(g)"
        })
        nutrition_df = nutrition_df[["食物名稱", "熱量(kcal)", "蛋白質(g)", "脂肪(g)", "碳水化合物(g)"]].dropna()
    except Exception as e:
        st.error(f"讀取營養資料失敗：{e}")
        st.stop()

    # 🔍 食物搜尋
    search_name = st.text_input("🔍 輸入食物關鍵字（例如：雞肉、飯）")
    matches = nutrition_df[nutrition_df["食物名稱"].str.contains(search_name, na=False, regex=False)]

    if not matches.empty:
        selected = st.selectbox("請選擇正確的食物名稱：", matches["食物名稱"].unique())
        selected_row = nutrition_df[nutrition_df["食物名稱"] == selected].iloc[0]

        st.write("每 100g 含有：")
        st.markdown(f"- 🔥 熱量：{selected_row['熱量(kcal)']} kcal")
        st.markdown(f"- 🥩 蛋白質：{selected_row['蛋白質(g)']} g")
        st.markdown(f"- 🧈 脂肪：{selected_row['脂肪(g)']} g")
        st.markdown(f"- 🍚 碳水化合物：{selected_row['碳水化合物(g)']} g")

        grams = st.number_input("實際攝取份量（g）", min_value=1, step=1)
        if st.button("✅ 儲存今日紀錄"):
            factor = grams / 100
            try:
                conn = sqlite3.connect("healthpiggy.db")
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS food_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT,
                        date TEXT,
                        food TEXT,
                        grams REAL,
                        kcal REAL,
                        protein REAL,
                        fat REAL,
                        carb REAL
                    )
                """)
                cursor.execute("INSERT INTO food_logs (email, date, food, grams, kcal, protein, fat, carb) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
                    st.session_state.email,
                    date.today().isoformat(),
                    selected,
                    grams,
                    round(selected_row["熱量(kcal)"] * factor, 1),
                    round(selected_row["蛋白質(g)"] * factor, 1),
                    round(selected_row["脂肪(g)"] * factor, 1),
                    round(selected_row["碳水化合物(g)"] * factor, 1)
                ))
                conn.commit()
                conn.close()
                st.success("✅ 已儲存攝取紀錄！")
                st.rerun()
            except Exception as e:
                st.error(f"儲存紀錄失敗：{e}")
    elif search_name:
        st.info("找不到相關食物，請嘗試其他關鍵字")

    # 📋 顯示攝取總覽
    st.subheader("📋 今日攝取總覽")
    try:
        conn = sqlite3.connect("healthpiggy.db")
        df = pd.read_sql_query("SELECT * FROM food_logs WHERE email = ? AND date = ?", conn, params=[st.session_state.email, date.today().isoformat()])
        conn.close()
    except Exception as e:
        st.error(f"查詢資料失敗：{e}")
        st.stop()

    if not df.empty:
        df_sum = df[["kcal", "protein", "fat", "carb"]].sum().round(1)
        st.markdown(f"🔥 今日總熱量：**{df_sum.kcal} kcal**")
        st.markdown(f"🥩 蛋白質：**{df_sum.protein} g**")
        st.markdown(f"🧈 脂肪：**{df_sum.fat} g**")
        st.markdown(f"🍚 碳水化合物：**{df_sum.carb} g**")
        st.dataframe(df[["food", "grams", "kcal", "protein", "fat", "carb"]])

        # 🗑️ 刪除紀錄按鈕
        st.subheader("📋 今日攝取紀錄")
        for i, row in df.iterrows():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(
                    f"- 🍴 **{row['food']}** | {row['grams']} g | 🔥 {row['kcal']} kcal | 🥩 {row['protein']} g | 🧈 {row['fat']} g | 🍚 {row['carb']} g"
                )
            with col2:
                if st.button("❌ 刪除", key=f"delete_{row['id']}"):
                    conn = sqlite3.connect("healthpiggy.db")
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM food_logs WHERE id = ?", (row["id"],))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ 已刪除 {row['food']} 的紀錄")
                    st.rerun()

        # 🤖 AI 建議
        if "tdee" not in st.session_state:
            st.info("尚未計算 TDEE，請至『我的健康資料』頁面填寫並儲存基本資料")
        else:
            remaining = round(st.session_state.tdee - df_sum.kcal, 1)
            if remaining >= 0:
                st.info(f"🎯 你今天還可以攝取 **{remaining} kcal**")
            else:
                st.warning(f"⚠️ 你已超過目標熱量 **{-remaining} kcal**")

            st.subheader("🤖 Gemini AI 建議")
            feedback = generate_gemini_feedback(df_sum.kcal, st.session_state.tdee)
            st.markdown(f"💡 **{feedback}**")
    else:
        st.info("尚未紀錄今日飲食")

st.sidebar.markdown("---")
if st.sidebar.button("🔓 登出"):
    if st.session_state.email:
        st.success(f"已成功登出 {st.session_state.email}！")
        st.session_state.email = None
        time.sleep(1)
        st.session_state.menu = "首頁"
    else:
        st.info("你尚未登入帳號")
    #st.session_state.menu = "首頁"
