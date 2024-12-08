import json
import os
import sys
import io
import time
import base64
import requests
import pyperclip
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import pyscreenshot as ImageGrab
import keyboard
import re
import ctypes

# 全局变量
selection_start = None
rect = None
selection_window = None
image_full = None
image_path = "temp_screenshot.png"
instruction_text_id = None

def load_config():
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    return config

def on_mouse_down(event):
    global selection_start, rect, instruction_text_id
    selection_start = (event.x, event.y)
    # 移除提示文本
    if instruction_text_id is not None:
        selection_window.delete(instruction_text_id)
    if rect is not None:
        selection_window.delete(rect)
    rect = selection_window.create_rectangle(event.x, event.y, event.x, event.y, outline='red', width=2)

def on_mouse_move(event):
    global rect, selection_start
    if selection_start:
        x1, y1 = selection_start
        x2, y2 = event.x, event.y
        if rect is not None:
            selection_window.delete(rect)
        rect = selection_window.create_rectangle(x1, y1, x2, y2, outline='red', width=2)

def on_mouse_up(event):
    global selection_start, rect, selection_window, image_full
    if selection_start:
        x1, y1 = selection_start
        x2, y2 = event.x, event.y
        if x2 < x1: x1, x2 = x2, x1
        if y2 < y1: y1, y2 = y2, y1

        # 裁剪图像
        crop_img = image_full.crop((x1, y1, x2, y2))
        crop_img.save(image_path)

        root = selection_window._root()
        root.destroy()

        # 调用OCR->LaTeX API
        process_image_and_ocr()

def show_selection_window(full_img):
    global selection_window, instruction_text_id
    # 使用Tk()作为主窗口，而不是Toplevel()
    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.attributes('-topmost', True)
    root.configure(cursor="cross")

    imgtk = ImageTk.PhotoImage(full_img)
    W, H = full_img.size

    selection_window = tk.Canvas(root, bg='black', highlightthickness=0)
    selection_window.pack(fill="both", expand=True)

    selection_window.create_image(0, 0, anchor="nw", image=imgtk)
    selection_window.imgtk = imgtk

    # 添加半透明遮罩
    overlay = selection_window.create_rectangle(0, 0, W, H, fill="black", stipple="gray50")

    # 显示提示文字
    instruction_text_id = selection_window.create_text(
        W/2, H/2, text="请用鼠标拖拽选择区域，松开结束", fill="white", font=("Helvetica", 20)
    )

    selection_window.bind("<ButtonPress-1>", on_mouse_down)
    selection_window.bind("<B1-Motion>", on_mouse_move)
    selection_window.bind("<ButtonRelease-1>", on_mouse_up)

    def on_esc(event):
        """按下 Esc 关闭窗口"""
        print("截图已取消")
        root.destroy()

    # 绑定 Esc 键
    root.bind("<Escape>", on_esc)

    root.focus_force()
    root.mainloop()


def capture_screen():
    global image_full
    user32 = ctypes.windll.user32
    user32.SetProcessDPIAware()  # 设置为DPI感知，确保获取实际分辨率
    screen_width = user32.GetSystemMetrics(0)
    screen_height = user32.GetSystemMetrics(1)
    img = ImageGrab.grab(bbox=(0, 0, screen_width, screen_height))
    image_full = img
    show_selection_window(img)

def process_image_and_ocr():
    config = load_config()
    endpoint = config["endpoint"]
    api_key = config["api_key"]
    api_path = config.get("api_path", "")

    api_config = config.get("api_config", {})

    encoded_image = base64.b64encode(open(image_path, 'rb').read()).decode('ascii')
    config["api_config"]["messages"][1]["content"][1]["image_url"]["url"] = f"data:image/jpeg;base64,{encoded_image}"

    headers = {
        "Content-Type": "application/json",
        "api-key": api_key,
    }

    url = endpoint.rstrip("/") + "/" + api_path.lstrip("/")

    try:
        response = requests.post(url, headers=headers, json=api_config)
        response.raise_for_status()
    except requests.RequestException as e:
        show_tooltip(f"请求失败: {e}")
        return

    if response.status_code == 200:
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        print(f"回复内容：{content}")
        match = re.search(r"latex\n(.*?)\n", content)
        latex_code = match[1] if match else ""
        if latex_code:
            pyperclip.copy(latex_code)
            show_tooltip("LaTeX代码已复制！")
        else:
            show_tooltip("未识别到公式")
    else:
        show_tooltip(f"请求失败: {response.status_code}")

def show_tooltip(text):
    tip = tk.Tk()
    tip.overrideredirect(True)
    tip.attributes("-topmost", True)
    x, y = tip.winfo_pointerx(), tip.winfo_pointery()
    tip.geometry(f"+{x+10}+{y+10}")
    label = tk.Label(tip, text=text, bg="yellow", fg="black", bd=1, relief="solid")
    label.pack()
    tip.after(1000, tip.destroy)  # 0.5秒后关闭
    tip.mainloop()

def on_hotkey():
    capture_screen()

def main():
    hotkey = load_config().get("hotkey", "ctrl+shift+s")
    keyboard.add_hotkey(hotkey, on_hotkey)
    print(f"Press {hotkey} to capture and OCR.")
    keyboard.wait()

if __name__ == "__main__":
    main()
