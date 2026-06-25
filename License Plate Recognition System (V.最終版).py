import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import cv2
import easyocr
import re
import math
import random
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk


# ==============================
# 設定區
# ==============================

# "." 代表讀取目前程式所在資料夾
input_folder = "."

# 輸出結果資料夾
output_folder = "output_results"
os.makedirs(output_folder, exist_ok=True)

# 支援的圖片格式
image_extensions = [".jpg", ".jpeg", ".png", ".bmp", ".webp"]

# 台灣新式機車車牌格式：
# 第一碼只接受 N、M、P
# 第二、三碼為英文
# 最後四碼為數字
# 例如：NDM3960、MAB1234、PFW7708
plate_regex = r"[NMP][A-Z]{2}[0-9]{4}"


# ==============================
# 車牌文字修正函式
# ==============================

def fix_taiwan_plate_text(text):
    text = text.upper()

    remove_chars = [" ", "-", ".", "_", ":", ";", "/", "\\", "|", "，", "。"]
    for ch in remove_chars:
        text = text.replace(ch, "")

    # 只保留英文與數字
    text = re.sub(r"[^A-Z0-9]", "", text)

    # 後四碼應該是數字，所以把常被誤認的英文改成數字
    letter_to_digit = {
        "O": "0",
        "Q": "0",
        "D": "0",
        "I": "1",
        "L": "1",
        "T": "1",
        "Z": "2",
        "S": "5",
        "B": "8",
        "G": "6"
    }

    # 前三碼應該是英文，所以把常被誤認的數字改成英文
    digit_to_letter = {
        "0": "O",
        "1": "I",
        "2": "Z",
        "5": "S",
        "6": "G",
        "8": "B"
    }

    possible_plates = []

    # 從 OCR 字串中滑動搜尋 7 碼
    for i in range(0, len(text) - 6):
        candidate = text[i:i + 7]

        first_three = candidate[:3]
        last_four = candidate[3:]

        fixed_first = ""
        fixed_last = ""

        # 前三碼修正成英文
        for ch in first_three:
            if ch.isalpha():
                fixed_first += ch
            elif ch in digit_to_letter:
                fixed_first += digit_to_letter[ch]
            else:
                fixed_first += ch

        # 後四碼修正成數字
        for ch in last_four:
            if ch.isdigit():
                fixed_last += ch
            elif ch in letter_to_digit:
                fixed_last += letter_to_digit[ch]
            else:
                fixed_last += ch

        fixed_plate = fixed_first + fixed_last

        # 只接受新式機車車牌：N、M、P 開頭
        if re.fullmatch(plate_regex, fixed_plate):
            possible_plates.append(fixed_plate)

    if len(possible_plates) > 0:
        return possible_plates[0], text

    return None, text


# ==============================
# 使用者輸入車牌整理函式
# ==============================

def clean_user_plate(text):
    text = text.upper()
    text = text.replace(" ", "")
    text = text.replace("-", "")
    text = text.replace(".", "")
    text = text.replace("_", "")
    text = text.replace(":", "")
    text = text.replace(";", "")
    return text


# ==============================
# 停車費計算函式
# ==============================

def calculate_fee(minutes):
    """
    收費規則：
    前 30 分鐘免費
    超過 30 分鐘後，每小時 10 元
    不滿一小時以一小時計算
    """

    if minutes <= 30:
        return 0

    charge_minutes = minutes - 30
    hours = math.ceil(charge_minutes / 60)
    fee = hours * 10

    return fee


# ==============================
# 開啟大視窗顯示車輛照片
# ==============================

def open_vehicle_photo_window(image_path, plate_number):
    if image_path is None or not os.path.exists(image_path):
        messagebox.showerror("錯誤", "找不到對應的車輛照片")
        return

    photo_window = tk.Toplevel()
    photo_window.title("車輛照片 - " + plate_number)

    # 最大化照片視窗
    photo_window.state("zoomed")

    # 讓照片視窗跳到最前面
    photo_window.lift()
    photo_window.attributes("-topmost", True)
    photo_window.focus_force()
    photo_window.after(1000, lambda: photo_window.attributes("-topmost", False))

    title_label = tk.Label(
        photo_window,
        text="車牌號碼：" + plate_number,
        font=("Microsoft JhengHei", 28, "bold")
    )
    title_label.pack(pady=15)

    img = Image.open(image_path)

    screen_width = photo_window.winfo_screenwidth()
    screen_height = photo_window.winfo_screenheight()

    max_width = int(screen_width * 0.9)
    max_height = int(screen_height * 0.75)

    img_width, img_height = img.size
    scale = min(max_width / img_width, max_height / img_height)

    new_width = int(img_width * scale)
    new_height = int(img_height * scale)

    img = img.resize((new_width, new_height))

    tk_img = ImageTk.PhotoImage(img)

    image_label = tk.Label(photo_window, image=tk_img)
    image_label.image = tk_img
    image_label.pack(pady=10)

    close_button = tk.Button(
        photo_window,
        text="關閉照片",
        font=("Microsoft JhengHei", 18),
        command=photo_window.destroy
    )
    close_button.pack(pady=10)


# ==============================
# 建立繳費 GUI 視窗
# ==============================

def open_payment_window(parking_data):
    window = tk.Tk()
    window.title("智慧停車場繳費系統")

    # 最大化視窗
    window.state("zoomed")

    # 讓視窗跳到最前面
    window.lift()
    window.attributes("-topmost", True)
    window.focus_force()
    window.after(1000, lambda: window.attributes("-topmost", False))

    main_frame = tk.Frame(window)
    main_frame.pack(expand=True)

    title_label = tk.Label(
        main_frame,
        text="智慧停車場機車車牌辨識與自動繳費系統",
        font=("Microsoft JhengHei", 34, "bold")
    )
    title_label.pack(pady=30)

    rule_label = tk.Label(
        main_frame,
        text="辨識對象：台灣新式機車車牌，僅接受 N、M、P 開頭\n收費規則：前 30 分鐘免費，超過 30 分鐘後每小時 10 元",
        font=("Microsoft JhengHei", 20)
    )
    rule_label.pack(pady=20)

    input_label = tk.Label(
        main_frame,
        text="請輸入你的機車車牌號碼：",
        font=("Microsoft JhengHei", 24)
    )
    input_label.pack(pady=15)

    plate_entry = tk.Entry(
        main_frame,
        font=("Microsoft JhengHei", 32),
        justify="center",
        width=20
    )
    plate_entry.pack(pady=10)

    result_label = tk.Label(
        main_frame,
        text="",
        font=("Microsoft JhengHei", 28, "bold"),
        fg="blue",
        justify="center"
    )
    result_label.pack(pady=30)

    def search_fee():
        user_plate = plate_entry.get()
        user_plate = clean_user_plate(user_plate)

        if user_plate == "":
            messagebox.showwarning("提醒", "請輸入車牌號碼")
            return

        if user_plate in parking_data:
            minutes = parking_data[user_plate]["minutes"]
            fee = calculate_fee(minutes)
            image_path = parking_data[user_plate]["vehicle_image_path"]

            result_text = (
                f"車牌號碼：{user_plate}\n"
                f"停車時間：{minutes} 分鐘\n"
                f"應繳金額：{fee} 元\n"
                f"已開啟對應車輛照片"
            )

            result_label.config(text=result_text, fg="blue")

            # 另外跳出大視窗顯示該車牌對應照片
            open_vehicle_photo_window(image_path, user_plate)

        else:
            result_label.config(
                text="查無此車牌，請確認輸入是否正確",
                fg="red"
            )

    def clear_input():
        plate_entry.delete(0, tk.END)
        result_label.config(text="")

    button_frame = tk.Frame(main_frame)
    button_frame.pack(pady=15)

    search_button = tk.Button(
        button_frame,
        text="查詢費用",
        font=("Microsoft JhengHei", 22),
        width=12,
        command=search_fee
    )
    search_button.grid(row=0, column=0, padx=15)

    clear_button = tk.Button(
        button_frame,
        text="清除",
        font=("Microsoft JhengHei", 22),
        width=10,
        command=clear_input
    )
    clear_button.grid(row=0, column=1, padx=15)

    exit_button = tk.Button(
        button_frame,
        text="離開系統",
        font=("Microsoft JhengHei", 22),
        width=10,
        command=window.destroy
    )
    exit_button.grid(row=0, column=2, padx=15)

    count_label = tk.Label(
        main_frame,
        text=f"目前系統已辨識機車數量：{len(parking_data)} 台",
        font=("Microsoft JhengHei", 18),
        fg="gray"
    )
    count_label.pack(pady=20)

    hint_label = tk.Label(
        main_frame,
        text="可輸入格式：NDM3960 或 NDM-3960",
        font=("Microsoft JhengHei", 16),
        fg="gray"
    )
    hint_label.pack(pady=5)

    # 按 Enter 也可以查詢
    window.bind("<Return>", lambda event: search_fee())

    window.mainloop()


# ==============================
# 自動讀取資料夾內所有圖片
# ==============================

image_files = []

for file_name in os.listdir(input_folder):
    file_path = os.path.join(input_folder, file_name)

    if not os.path.isfile(file_path):
        continue

    ext = os.path.splitext(file_name)[1].lower()

    if ext in image_extensions:
        image_files.append(file_path)

if len(image_files) == 0:
    print("找不到任何圖片")
    print("請確認資料夾內有 jpg、jpeg、png、bmp 或 webp 檔案")
    exit()

print("找到圖片數量：", len(image_files))


# ==============================
# 建立 EasyOCR
# ==============================

print("正在載入 EasyOCR...")
reader = easyocr.Reader(['en'], gpu=True)
print("EasyOCR 載入成功")


# ==============================
# 停車場資料庫
# key = 車牌號碼
# value = 停車時間 + 車輛照片路徑
# ==============================

parking_data = {}


# ==============================
# 開始辨識每張圖片
# ==============================

for image_path in image_files:
    print("----------------------------------------")
    print("正在處理圖片：", image_path)

    img = cv2.imread(image_path)

    if img is None:
        print("圖片讀取失敗，跳過：", image_path)
        continue

    result_img = img.copy()
    img_h, img_w = img.shape[:2]

    # ==============================
    # 影像前處理
    # ==============================

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)

    contours, hierarchy = cv2.findContours(
        edges,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    print("找到輪廓數量：", len(contours))

    # ==============================
    # 找車牌候選區域
    # ==============================

    plate_img = None
    plate_rect = None
    candidates = []

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)

        if h == 0:
            continue

        area = w * h
        ratio = w / h

        # 機車車牌多為橫向矩形
        # 避免抓到螺絲孔、貼紙、儀表板、行車紀錄器等細節
        if 2.0 < ratio < 6.5:
            if w > img_w * 0.35 and h > img_h * 0.12 and area > img_w * img_h * 0.05:
                candidates.append((x, y, w, h, area, ratio))

    if len(candidates) > 0:
        candidates = sorted(candidates, key=lambda item: item[4], reverse=True)

        x, y, w, h, area, ratio = candidates[0]

        plate_img = img[y:y + h, x:x + w]
        plate_rect = (x, y, w, h)

        print("找到可能車牌區域")
        print("車牌位置 x, y, w, h =", x, y, w, h)
        print("車牌 ratio =", ratio)

    else:
        print("沒有找到符合大小條件的車牌區域")

    base_name = os.path.splitext(os.path.basename(image_path))[0]

    result_output_path = os.path.join(output_folder, "result_" + base_name + ".jpg")
    edge_output_path = os.path.join(output_folder, "edge_" + base_name + ".jpg")
    plate_output_path = os.path.join(output_folder, "plate_" + base_name + ".jpg")

    # ==============================
    # 如果找到車牌
    # ==============================

    if plate_img is not None:
        x, y, w, h = plate_rect

        # 框出車牌
        cv2.rectangle(result_img, (x, y), (x + w, y + h), (0, 255, 0), 3)

        ocr_target = plate_img

        # 車牌裁切圖輸出
        cv2.imwrite(plate_output_path, plate_img)
        print("已輸出車牌裁切圖：", plate_output_path)

    # ==============================
    # 如果找不到車牌，就直接 OCR 整張圖
    # ==============================

    else:
        print("沒有找到車牌區域，改成直接辨識整張圖片")
        ocr_target = img
        plate_output_path = None

    # 輸出框選結果圖與邊緣圖
    cv2.imwrite(result_output_path, result_img)
    cv2.imwrite(edge_output_path, edges)

    print("已輸出框選結果圖：", result_output_path)
    print("已輸出邊緣偵測圖：", edge_output_path)

    # ==============================
    # EasyOCR 辨識
    # ==============================

    results = reader.readtext(
        ocr_target,
        allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"
    )

    print("EasyOCR 原始辨識結果：")

    raw_text = ""

    if len(results) == 0:
        print("沒有辨識到任何文字")
    else:
        for bbox, text, confidence in results:
            print("文字：", text, "信心值：", confidence)
            raw_text += text

    fixed_plate, cleaned_text = fix_taiwan_plate_text(raw_text)

    print("整理後文字：", cleaned_text)

    if fixed_plate is not None:
        print("修正後機車車牌號碼：", fixed_plate)

        random_minutes = random.randint(1, 1440)

        # 查詢時會顯示原本拍的照片加上綠框
        parking_data[fixed_plate] = {
            "minutes": random_minutes,
            "vehicle_image_path": result_output_path
        }

        print("系統隨機產生停車時間：", random_minutes, "分鐘")
        print("已建立停車資料：", fixed_plate, "停車", random_minutes, "分鐘")
        print("車輛照片路徑：", result_output_path)

    else:
        print("沒有符合台灣新式機車車牌格式的結果")
        print("此結果不建立停車資料")


# ==============================
# 顯示目前停車場資料
# ==============================

print("----------------------------------------")
print("車牌辨識完成")
print("目前停車場資料如下：")

if len(parking_data) == 0:
    print("目前沒有成功辨識到任何機車車牌")
else:
    for plate, data in parking_data.items():
        minutes = data["minutes"]
        fee = calculate_fee(minutes)
        image_path = data["vehicle_image_path"]

        print("車牌：", plate)
        print("停車時間：", minutes, "分鐘")
        print("目前應繳：", fee, "元")
        print("車輛照片：", image_path)
        print("----------------------------------------")


# ==============================
# 開啟繳費視窗
# ==============================

print("即將開啟繳費視窗")

open_payment_window(parking_data)