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
from ultralytics import YOLO


# ==============================
# 設定區
# ==============================

input_folder = "."
output_folder = "output_results"
os.makedirs(output_folder, exist_ok=True)

image_extensions = [".jpg", ".jpeg", ".png", ".bmp", ".webp"]

# best.pt 跟這支程式放在同一層
yolo_model_path = "./best.pt"

# 台灣新式車牌：前三碼英文 + 後四碼數字，例如 NDM3960
plate_regex = r"[A-Z]{3}[0-9]{4}"


# ==============================
# 車牌文字修正函式
# ==============================

def fix_taiwan_plate_text(text):
    text = text.upper()

    remove_chars = [" ", "-", ".", "_", ":", ";", "/", "\\", "|", "，", "。"]
    for ch in remove_chars:
        text = text.replace(ch, "")

    text = re.sub(r"[^A-Z0-9]", "", text)

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

    digit_to_letter = {
        "0": "O",
        "1": "I",
        "2": "Z",
        "5": "S",
        "6": "G",
        "8": "B"
    }

    possible_plates = []

    for i in range(0, len(text) - 6):
        candidate = text[i:i + 7]

        first_three = candidate[:3]
        last_four = candidate[3:]

        fixed_first = ""
        fixed_last = ""

        for ch in first_three:
            if ch.isalpha():
                fixed_first += ch
            elif ch in digit_to_letter:
                fixed_first += digit_to_letter[ch]
            else:
                fixed_first += ch

        for ch in last_four:
            if ch.isdigit():
                fixed_last += ch
            elif ch in letter_to_digit:
                fixed_last += letter_to_digit[ch]
            else:
                fixed_last += ch

        fixed_plate = fixed_first + fixed_last

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
    if minutes <= 30:
        return 0

    charge_minutes = minutes - 30
    hours = math.ceil(charge_minutes / 60)
    fee = hours * 10

    return fee


# ==============================
# YOLO 車牌偵測函式
# ==============================

def detect_plate_by_yolo(img, yolo_model):
    results = yolo_model.predict(
        source=img,
        conf=0.25,
        save=False,
        verbose=False
    )

    best_box = None
    best_conf = -1

    for result in results:
        boxes = result.boxes

        if boxes is None or len(boxes) == 0:
            continue

        for box in boxes:
            conf = float(box.conf[0].cpu().numpy())

            if conf > best_conf:
                best_conf = conf
                best_box = box

    if best_box is None:
        return None, None, None

    x1, y1, x2, y2 = best_box.xyxy[0].cpu().numpy().astype(int)

    img_h, img_w = img.shape[:2]

    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(img_w, x2)
    y2 = min(img_h, y2)

    if x2 <= x1 or y2 <= y1:
        return None, None, None

    plate_img = img[y1:y2, x1:x2]
    plate_rect = (x1, y1, x2 - x1, y2 - y1)

    return plate_img, plate_rect, best_conf


# ==============================
# 裁切真正車牌文字區域
# ==============================

def crop_real_plate_text_area(plate_img):
    h, w = plate_img.shape[:2]

    # 只取車牌下半部，避免讀到上方貼紙
    y_start = int(h * 0.32)
    y_end = int(h * 0.95)

    x_start = int(w * 0.03)
    x_end = int(w * 0.97)

    text_area = plate_img[y_start:y_end, x_start:x_end]

    return text_area


# ==============================
# OCR 前處理函式
# ==============================

def preprocess_for_ocr(ocr_target):
    ocr_target = cv2.resize(
        ocr_target,
        None,
        fx=2,
        fy=2,
        interpolation=cv2.INTER_CUBIC
    )

    gray_ocr = cv2.cvtColor(ocr_target, cv2.COLOR_BGR2GRAY)

    gray_ocr = cv2.GaussianBlur(gray_ocr, (3, 3), 0)

    binary_ocr = cv2.adaptiveThreshold(
        gray_ocr,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        5
    )

    return binary_ocr


# ==============================
# 多方法 EasyOCR 辨識函式
# ==============================

def recognize_plate_with_easyocr(reader, img, plate_img, output_folder, base_name):
    ocr_images = []

    if plate_img is not None:
        # 方法 1：車牌下半部，避免上方貼紙
        real_text_area = crop_real_plate_text_area(plate_img)
        lower_processed = preprocess_for_ocr(real_text_area)
        ocr_images.append(("lower_text_area", lower_processed))

        # 方法 2：完整車牌二值化
        full_processed = preprocess_for_ocr(plate_img)
        ocr_images.append(("full_plate_binary", full_processed))

        # 方法 3：完整車牌原圖放大
        plate_resized = cv2.resize(
            plate_img,
            None,
            fx=2,
            fy=2,
            interpolation=cv2.INTER_CUBIC
        )
        ocr_images.append(("full_plate_original", plate_resized))

    else:
        # YOLO 沒抓到時，才用整張圖備用
        full_img_processed = preprocess_for_ocr(img)
        ocr_images.append(("full_image_backup", full_img_processed))

    fixed_plate = None
    cleaned_text = ""
    raw_text = ""

    for method_name, ocr_image in ocr_images:
        print("正在使用 OCR 方法：", method_name)

        debug_path = os.path.join(
            output_folder,
            "ocr_area_" + method_name + "_" + base_name + ".jpg"
        )
        cv2.imwrite(debug_path, ocr_image)
        print("已輸出 OCR 辨識區域：", debug_path)

        results = reader.readtext(
            ocr_image,
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
            print("此方法成功辨識車牌：", fixed_plate)
            return fixed_plate, cleaned_text, raw_text

        print("此方法沒有得到符合格式的車牌")

    return None, cleaned_text, raw_text


# ==============================
# 開啟大視窗顯示車輛照片
# ==============================

def open_vehicle_photo_window(image_path, plate_number):
    if image_path is None or not os.path.exists(image_path):
        messagebox.showerror("錯誤", "找不到對應的車輛照片")
        return

    photo_window = tk.Toplevel()
    photo_window.title("車輛照片 - " + plate_number)

    photo_window.state("zoomed")

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

    window.state("zoomed")

    window.lift()
    window.attributes("-topmost", True)
    window.focus_force()
    window.after(1000, lambda: window.attributes("-topmost", False))

    main_frame = tk.Frame(window)
    main_frame.pack(expand=True)

    title_label = tk.Label(
        main_frame,
        text="智慧停車場車牌辨識與自動繳費系統",
        font=("Microsoft JhengHei", 34, "bold")
    )
    title_label.pack(pady=30)

    rule_label = tk.Label(
        main_frame,
        text="YOLO 車牌偵測 + EasyOCR 車牌辨識\n收費規則：前 30 分鐘免費，超過後每小時 10 元",
        font=("Microsoft JhengHei", 20)
    )
    rule_label.pack(pady=20)

    input_label = tk.Label(
        main_frame,
        text="請輸入你的車牌號碼：",
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
        text=f"目前系統已辨識車輛數量：{len(parking_data)} 台",
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

    window.bind("<Return>", lambda event: search_fee())

    window.mainloop()


# ==============================
# 主程式開始
# ==============================

print("目前執行位置：", os.getcwd())
print("YOLO 模型位置：", os.path.abspath(yolo_model_path))
print("best.pt 是否存在：", os.path.exists(yolo_model_path))

if not os.path.exists(yolo_model_path):
    print("錯誤：找不到 YOLO 模型 best.pt")
    print("請確認 best.pt 是否跟這支 Python 程式放在同一層")
    exit()

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
    print("請確認目前資料夾內有 jpg、jpeg、png、bmp 或 webp 檔案")
    exit()

print("找到圖片數量：", len(image_files))


# ==============================
# 載入 YOLO 與 EasyOCR
# ==============================

print("正在載入 YOLO 模型...")
yolo_model = YOLO(yolo_model_path)
print("YOLO 模型載入成功")

print("正在載入 EasyOCR...")
reader = easyocr.Reader(['en'], gpu=False)
print("EasyOCR 載入成功")


# ==============================
# 停車場資料庫
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

    base_name = os.path.splitext(os.path.basename(image_path))[0]

    result_output_path = os.path.join(output_folder, "result_" + base_name + ".jpg")
    plate_output_path = os.path.join(output_folder, "plate_" + base_name + ".jpg")

    plate_img, plate_rect, yolo_confidence = detect_plate_by_yolo(img, yolo_model)

    if plate_img is not None:
        x, y, w, h = plate_rect

        print("YOLO 找到車牌")
        print("車牌位置 x, y, w, h =", x, y, w, h)
        print("YOLO 信心值 =", yolo_confidence)

        cv2.rectangle(result_img, (x, y), (x + w, y + h), (0, 255, 0), 3)

        cv2.imwrite(plate_output_path, plate_img)
        print("已輸出完整車牌裁切圖：", plate_output_path)

    else:
        print("YOLO 沒有偵測到車牌")

    cv2.imwrite(result_output_path, result_img)
    print("已輸出框選結果圖：", result_output_path)

    fixed_plate, cleaned_text, raw_text = recognize_plate_with_easyocr(
        reader=reader,
        img=img,
        plate_img=plate_img,
        output_folder=output_folder,
        base_name=base_name
    )

    if fixed_plate is not None:
        print("修正後車牌號碼：", fixed_plate)

        random_minutes = random.randint(1, 1440)

        parking_data[fixed_plate] = {
            "minutes": random_minutes,
            "vehicle_image_path": result_output_path
        }

        print("系統隨機產生停車時間：", random_minutes, "分鐘")
        print("已建立停車資料：", fixed_plate, "停車", random_minutes, "分鐘")
        print("車輛照片路徑：", result_output_path)

    else:
        print("沒有符合台灣新式車牌格式的結果")


# ==============================
# 顯示目前停車場資料
# ==============================

print("----------------------------------------")
print("車牌辨識完成")
print("目前停車場資料如下：")

if len(parking_data) == 0:
    print("目前沒有成功辨識到任何車牌")
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