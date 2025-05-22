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
import matplotlib.pyplot as plt

 # 設定 Gemini API 金鑰
API_KEY = "AIzaSyDt-ePwvoedMgCwtA4Hfde6lVrr-VTQYiQ"
genai.configure(api_key=API_KEY)

    # 定義 Gemini 建議函數
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
    
def generate_emotional_feedback(actual_calories, recommended_calories):
    if actual_calories == 0:
        return "你今天好像還沒吃東西～記得吃飯才有力氣面對挑戰喔🍱"

    diff = actual_calories - recommended_calories

    prompt = (
        "你是一位貼心的健康 AI 教練，請針對使用者今天的熱量攝取狀況，給予一段溫柔、鼓勵且富有情感的中文建議，讓他們在追求健康的過程中感到被支持。\n\n"
        "請控制內容在兩行以內，風格像是在安慰或鼓勵朋友，例如：『別擔心，偶爾放鬆一下也沒關係～記得明天再調整就好！』\n\n"
        f"以下是使用者的飲食狀況：\n"
        f"- 建議攝取熱量：{recommended_calories} kcal\n"
        f"- 實際攝取熱量：{actual_calories} kcal\n"
        f"- 差異：{diff} kcal\n\n"
        "請給一段具體但情感豐富的鼓勵話語，不要僅描述數字。"
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
    # 正確拼接圖片路徑（相）
    img_path = f"images/{school}_level{level}.png" 
    
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
    cursor.execute("SELECT name, school, gender, birthday, height, weight, exercise, goal FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        st.error("找不到使用者資料")
        return

    name, school, gender, birthday, height, weight, exercise, goal = row
    age = datetime.now().year - int(birthday[:4])
    tdee, activity_level = calculate_tdee(gender, age, height, weight, exercise)

    # 根據目標調整熱量  
    if goal == "增肌":
        tdee = int(tdee * 1.10)  # 增加 10%
    elif goal == "減脂":
        tdee = int(tdee * 0.85)  # 減少 15%
    # 維持就不變

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
    - 🥅 目標：{goal}
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
    ["首頁", "註冊", "登入", "我的健康資料", "每日身體紀錄", "每日飲食紀錄", "編輯個人基本資料"],
    index=["首頁", "註冊", "登入", "我的健康資料", "每日身體紀錄", "每日飲食紀錄", "編輯個人基本資料"].index(
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
        goal = st.radio("你的目標是？", ["增肌", "減脂", "維持"], horizontal=True)
        height = st.number_input("身高（cm）", 100.0, 250.0, step=0.1)
        weight = st.number_input("體重（kg）", 30.0, 200.0, step=0.1)
        exercise = st.slider("每週運動次數（有氧 / 重訓）", 0, 14, 3)
        password = st.text_input("設定密碼", type="password")
        submitted = st.form_submit_button("送出註冊")
        if submitted:
            result = register_user(email, name, password, school, birthday.strftime("%Y-%m-%d"), gender, height, weight, exercise,goal)
            st.info(result)
            if result.startswith("✅"):
                st.session_state.menu = "登入"
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
        conn = sqlite3.connect("healthpiggy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM body_logs WHERE email = ? AND date = ?", (st.session_state.email, today))
        existing_entry = cursor.fetchone()
        conn.close()

        # 狀況 1：今天尚未填寫 → 顯示輸入表單
        if not existing_entry:
            with st.form("log_form"):
                weight = st.number_input("今天的體重（kg）", min_value=30.0, max_value=200.0, step=0.1)
                fat = st.number_input("體脂率（%）", min_value=0.0, max_value=60.0, step=0.1)
                exercise_min = st.number_input("今日運動時間（分鐘）", 0, 300, step=5)
                #notes = st.text_area("備註（可選）")
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
                            exercise_minutes INTEGER
                        )
                    """)
                    cursor.execute("""
                        INSERT INTO body_logs (email, date, weight, fat_percentage, exercise_minutes)
                        VALUES (?, ?, ?, ?, ?)
                    """, (st.session_state.email, today, weight, fat, exercise_min))
                    conn.commit()
                    conn.close()
                    st.success("✅ 今日紀錄已儲存！")
                    st.rerun()

# 狀況 2：今天已填過 → 顯示修改表單
        else:
            st.info("✅ 今天已有紀錄，請在下方修改。")

            old_weight = existing_entry[3]
            old_fat = existing_entry[4]
            old_exercise = existing_entry[5]
            #old_notes = existing_entry[6]

            new_weight = st.number_input("✏️ 體重（kg）", value=old_weight, min_value=30.0, max_value=200.0, step=0.1, key="edit_weight")
            new_fat = st.number_input("✏️ 體脂率（%）", value=old_fat, min_value=0.0, max_value=60.0, step=0.1, key="edit_fat")
            new_exercise = st.number_input("✏️ 運動時間（分鐘）", value=old_exercise, min_value=0, max_value=300, step=5, key="edit_exercise")
            #new_notes = st.text_area("✏️ 備註", value=old_notes, key="edit_notes")

            if st.button("💾 儲存修改"):
                conn = sqlite3.connect("healthpiggy.db")
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE body_logs
                    SET weight = ?, fat_percentage = ?, exercise_minutes = ?
                    WHERE email = ? AND date = ?
                """, (new_weight, new_fat, new_exercise, st.session_state.email, today))
                conn.commit()
                conn.close()
                st.success("✅ 修改完成！")
                st.rerun()
        with st.expander("📅 補登入過去的紀錄"):
            with st.form("backfill_form"):
                backfill_date = st.date_input("選擇日期", min_value=date(2000, 1, 1), max_value=date.today())
                weight = st.number_input("體重（kg）", min_value=30.0, max_value=200.0, step=0.1, key="backfill_weight")
                fat = st.number_input("體脂率（%）", min_value=0.0, max_value=60.0, step=0.1, key="backfill_fat")
                exercise_min = st.number_input("運動時間（分鐘）", 0, 300, step=5, key="backfill_exercise")
                #notes = st.text_area("備註（可選）", key="backfill_notes")
                submitted = st.form_submit_button("儲存補登入紀錄")

                if submitted:
                    conn = sqlite3.connect("healthpiggy.db")
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT * FROM body_logs WHERE email = ? AND date = ?
                    """, (st.session_state.email, backfill_date.isoformat()))
                    existing_entry = cursor.fetchone()

                    if existing_entry:
                        st.warning("⚠️ 該日期已有紀錄，無法重複輸入！")
                    else:
                        cursor.execute("""
                            INSERT INTO body_logs (email, date, weight, fat_percentage, exercise_minutes)
                            VALUES (?, ?, ?, ?, ?)
                        """, (st.session_state.email, backfill_date.isoformat(), weight, fat, exercise_min))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ 已成功補登入 {backfill_date} 的紀錄！")
                        st.rerun()
        # 顯示歷史紀錄
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

    # 食物搜尋
    search_name = st.text_input("🔍 輸入食物關鍵字（例如：雞肉、飯）")
    matches = nutrition_df[nutrition_df["食物名稱"].str.contains(search_name, na=False, regex=False)]
    meal_type = st.radio("用餐時段", ["早餐", "午餐", "晚餐", "其他"], horizontal=True)
 
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
                        carb REAL,
                        meal_type TEXT     
                    )
                """)
                cursor.execute("INSERT INTO food_logs (email, date, food, grams, kcal, protein, fat, carb,meal_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (
                    st.session_state.email,
                    date.today().isoformat(),
                    selected,
                    grams,
                    round(selected_row["熱量(kcal)"] * factor, 1),
                    round(selected_row["蛋白質(g)"] * factor, 1),
                    round(selected_row["脂肪(g)"] * factor, 1),
                    round(selected_row["碳水化合物(g)"] * factor, 1),
                    meal_type
                ))
                conn.commit()
                conn.close()
                st.success("✅ 已儲存攝取紀錄！")
                st.rerun()
            except Exception as e:
                st.error(f"儲存紀錄失敗：{e}")
    elif search_name:
        st.info("找不到相關食物，請嘗試其他關鍵字")

    # 顯示攝取總覽
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

        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']
        st.subheader("🍽 三餐攝取熱量分布")
        if "meal_type" in df.columns:
            meal_summary = df.groupby("meal_type")[["kcal", "protein", "fat", "carb"]].sum().round(1)
            st.dataframe(meal_summary)
            if not meal_summary.empty:
                st.subheader("🥧 各餐熱量占比")
                fig, ax = plt.subplots()
                ax.pie(
                    meal_summary["kcal"],
                    labels=meal_summary.index,       # 顯示 早餐/午餐/晚餐
                    autopct="%1.1f%%",
                    startangle=90,                    # 圓餅圖從上方開始
                    wedgeprops={"edgecolor": "white"}  
                )
                ax.set_title("三餐熱量比例", fontsize=7, color="darkblue")
                ax.axis("equal")  # 讓圓餅圖保持圓形

                st.pyplot(fig)
        else:
            st.info("目前資料尚未包含用餐時段")

        st.dataframe(df[['meal_type',"food", "grams", "kcal", "protein", "fat", "carb"]])

        # 刪除紀錄按鈕
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

        # AI 建議
        if "tdee" not in st.session_state:
            st.info("尚未計算 TDEE，請至『我的健康資料』頁面填寫並儲存基本資料")
        else:
            remaining = round(st.session_state.tdee - df_sum.kcal, 1)
            if remaining >= 0:
                st.info(f"🎯 你今天還可以攝取 **{remaining} kcal**")
            else:
                st.warning(f"⚠️ 你已超過目標熱量 **{-remaining} kcal**")

            st.subheader("🤖 Gemini AI 飲食建議")
            feedback = generate_gemini_feedback(df_sum.kcal, st.session_state.tdee)
            st.markdown(f"💡 **{feedback}**")
            st.subheader("💖 Gemini AI の 情緒價值 💖")
            feedback = generate_emotional_feedback(df_sum.kcal, st.session_state.tdee)
            st.markdown(f"💡 **{feedback}**")
    else:
        st.info("尚未紀錄今日飲食")

elif menu == "編輯個人基本資料":
    if st.session_state.email:
        st.subheader("✏️ 編輯個人基本資料")
        conn = sqlite3.connect("healthpiggy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT height, weight, exercise, goal FROM users WHERE email = ?", (st.session_state.email,))
        row = cursor.fetchone()
        conn.close()

        if row:
            current_height, current_weight, current_exercise, current_goal = row
            new_height = st.number_input("身高（cm）", 100.0, 250.0, value=current_height, step=0.1)
            new_weight = st.number_input("體重（kg）", 30.0, 200.0, value=current_weight, step=0.1)
            new_exercise = st.slider("每週運動次數（有氧 / 重訓）", 0, 14, value=current_exercise)
            new_goal = st.radio("你的目標是？", ["增肌", "減脂", "維持"], index=["增肌", "減脂", "維持"].index(current_goal), horizontal=True)

            if st.button("✅ 儲存變更"):
                try:
                    conn = sqlite3.connect("healthpiggy.db")
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE users
                        SET height = ?, weight = ?, exercise = ?, goal = ?
                        WHERE email = ?
                    """, (new_height, new_weight, new_exercise, new_goal, st.session_state.email))
                    conn.commit()
                    conn.close()

                    # 更新 session_state 的 TDEE
                    conn = sqlite3.connect("healthpiggy.db")
                    cursor = conn.cursor()
                    cursor.execute("SELECT gender, birthday FROM users WHERE email = ?", (st.session_state.email,))
                    user_data = cursor.fetchone()
                    conn.close()  # 再次關閉連線

                    if user_data:
                        gender, birthday = user_data
                        age = datetime.now().year - int(birthday[:4])
                        tdee, _ = calculate_tdee(gender, age, new_height, new_weight, new_exercise)

                        # 根據目標調整 TDEE
                        if new_goal == "增肌":
                            tdee = int(tdee * 1.10)  # 增加 10%
                        elif new_goal == "減脂":
                            tdee = int(tdee * 0.85)  # 減少 15%
                        # 維持就不變

                        st.session_state.tdee = tdee

                    st.success("✅ 基本資料已更新！")
                except Exception as e:
                    st.error(f"更新失敗：{e}")
        else:
            st.error("找不到使用者資料，請重新登入")
    else:
        st.warning("請先登入才能編輯個人基本資料")
    

st.sidebar.markdown("---")
if st.sidebar.button("🔓 登出"):
    if st.session_state.email:
        st.success(f"已成功登出 {st.session_state.email}！")
        st.session_state.email = None
        #st.experimental_rerun()  # 重新載入頁面
    else:
        st.info("你尚未登入帳號")
    st.session_state.menu = "首頁"