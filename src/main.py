import json
import os
import base64
import requests
import pyperclip
import tkinter as tk
import threading
import keyboard
import re
import pyautogui
import io
from PIL import Image, ImageTk
from tkinter import messagebox
import ctypes
import time
from ctypes import wintypes
from mss import mss  # 新增mss库

# 全局状态管理
class AppState:
    def __init__(self):
        self.root = None
        self.selection_start = None
        self.rect = None
        self.selection_window = None
        self.image_full = None
        self.is_capturing = False
        self.hotkey = "ctrl+shift+s"
        self.config = {}
        self.physical_width = 0
        self.physical_height = 0
        self.hotkey_id = None  # 热键ID存储
        self.hotkey_registered = False  # 热键状态标识
        self.thread_alive = True        # 线程状态标识
        
    def load_config(self):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                self.config = json.load(f)
            self.hotkey = self.config.get("hotkey", self.hotkey)
        except Exception as e:
            messagebox.showerror("配置错误", f"无法加载配置文件: {str(e)}")
            os._exit(1)

app_state = AppState()

def keyboard_wait_loop():
    while app_state.thread_alive:
        try:
            keyboard.wait()
        except Exception as e:
            print(f"键盘监听异常: {str(e)}")
            time.sleep(1)

# 在程序退出时清理资源
def on_exit():
    if app_state.hotkey_id:
        keyboard.remove_hotkey(app_state.hotkey_id)
    app_state.thread_alive = False
    keyboard.unhook_all()
    app_state.root.quit()

# 热键管理函数
def manage_hotkey():
    while app_state.thread_alive:
        try:
            # 仅在热键未注册时重新注册
            if not app_state.hotkey_id: 
                # 先移除可能存在的旧热键
                if app_state.hotkey_id is not None:  # 首次运行为None跳过
                    keyboard.remove_hotkey(app_state.hotkey_id)
                
                # 注册新热键并保存ID
                new_id = keyboard.add_hotkey(
                    app_state.hotkey, 
                    capture_trigger,
                    suppress=True
                )
                app_state.hotkey_id = new_id
                print(f"请按下快捷键进行截图：{app_state.hotkey}")

            time.sleep(5)
        except Exception as e:
            print(f"热键维护异常: {str(e)}")
            app_state.hotkey_id = None  # 重置ID触发重新注册
            time.sleep(1)

# 改进后的热键触发函数
def capture_trigger():
    try:
        print(1)
        if not app_state.is_capturing:
            app_state.is_capturing = True
            app_state.root.after(0, capture_screen)
        print(2)
    except Exception as e:
        print(f"热键回调异常: {str(e)}")
        app_state.is_capturing = False

def capture_screen():
    try:
        with mss() as sct:  # 使用mss获取多显示器信息
            # 获取所有显示器信息
            monitors = sct.monitors
            # 获取当前鼠标位置
            mouse_x, mouse_y = pyautogui.position()
            
            # 查找鼠标所在的显示器
            target_monitor = None
            for monitor in monitors[1:]:  # 跳过第一个总区域
                left = monitor['left']
                top = monitor['top']
                right = left + monitor['width']
                bottom = top + monitor['height']
                if left <= mouse_x < right and top <= mouse_y < bottom:
                    target_monitor = monitor
                    break
            
            if not target_monitor:  # 默认主显示器
                target_monitor = monitors[1] if len(monitors) > 1 else monitors[0]
            
            # 截取目标显示器
            img = sct.grab(target_monitor)
            img_pil = Image.frombytes('RGB', img.size, img.rgb)
            
            # 保存截图和显示器参数
            app_state.image_full = img_pil
            app_state.physical_width = target_monitor['width']
            app_state.physical_height = target_monitor['height']
            
            show_selection_window(img_pil, target_monitor)
            
    except Exception as e:
        messagebox.showerror("截图错误", f"截图失败: {str(e)}")
    finally:
        app_state.is_capturing = False

def show_selection_window(full_img, monitor):
    """在目标显示器上显示选区窗口"""
    # 获取显示器参数
    width = monitor['width']
    height = monitor['height']
    left = monitor['left']
    top = monitor['top']

    # 创建窗口（先不设置全屏）
    top_window = tk.Toplevel()
    top_window.geometry(f"{width}x{height}+{left}+{top}")
    top_window.overrideredirect(True)  # 隐藏窗口装饰
    top_window.attributes("-topmost", True)
    top_window.configure(cursor="cross")
    
    # Windows系统下强制窗口位置
    if os.name == 'nt':
        hwnd = top_window.winfo_id()
        
        # 移除窗口边框（更彻底的样式修改）
        GWL_STYLE = -16
        WS_POPUP = 0x80000000
        WS_VISIBLE = 0x10000000
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, WS_POPUP | WS_VISIBLE)
        
        # 强制设置窗口位置和大小
        ctypes.windll.user32.SetWindowPos(
            hwnd, -1,  # HWND_TOPMOST
            left, top, width, height,
            0x0040  # SWP_FRAMECHANGED
        )

    # 显示截图
    imgtk = ImageTk.PhotoImage(full_img)
    canvas = tk.Canvas(top_window, bg='black', highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    canvas.create_image(0, 0, anchor="nw", image=imgtk)
    canvas.imgtk = imgtk

    # 半透明遮罩
    canvas.create_rectangle(0, 0, width, height, fill="black", stipple="gray50")
    
    # 提示文字
    canvas.create_text(
        width/2, height/2, 
        text="拖拽选择区域 (ESC取消)", 
        fill="white", 
        font=("Helvetica", 20)
    )

    # 事件绑定
    canvas.bind("<ButtonPress-1>", lambda e: on_mouse_down(e, canvas))
    canvas.bind("<B1-Motion>", lambda e: on_mouse_move(e, canvas))
    canvas.bind("<ButtonRelease-1>", lambda e: on_mouse_up(e, canvas, top_window))

    def on_esc(event):
        top_window.destroy()
        print("截图已取消")
    
    top_window.bind("<Escape>", on_esc)
    top_window.focus_force()

def on_mouse_down(event, canvas):
    app_state.selection_start = (event.x, event.y)
    canvas.delete("selection")
    canvas.delete("instruction")
    app_state.rect = canvas.create_rectangle(
        *app_state.selection_start, *app_state.selection_start,
        outline='red', width=2, tags="selection"
    )

def on_mouse_move(event, canvas):
    if app_state.selection_start:
        x1, y1 = app_state.selection_start
        x2, y2 = event.x, event.y
        canvas.coords(app_state.rect, x1, y1, x2, y2)

def on_mouse_up(event, canvas, window):
    if app_state.selection_start:
        # 获取规范化的坐标
        x1, y1 = app_state.selection_start
        x2, y2 = event.x, event.y
        x_start, x_end = sorted([x1, x2])
        y_start, y_end = sorted([y1, y2])
        
        # 启动OCR处理线程
        threading.Thread(
            target=process_ocr, 
            args=(x_start, y_start, x_end, y_end)
        ).start()
    
    window.destroy()
    app_state.selection_start = None

def process_ocr(x1, y1, x2, y2):
    try:
        # 裁剪图像（使用相对坐标）
        crop_img = app_state.image_full.crop((x1, y1, x2, y2))
        image_bytes = io.BytesIO()
        crop_img.save(image_bytes, format='PNG')
        
        # 调用OCR API
        encoded_image = base64.b64encode(image_bytes.getvalue()).decode('ascii')
        response = call_ocr_api(encoded_image)
        
        # 处理结果
        if response:
            content = response["choices"][0]["message"]["content"]
            print(content)
            if latex_code := extract_latex(content):
                pyperclip.copy(latex_code)
                show_tooltip("LaTeX已复制到剪贴板")
            else:
                show_tooltip("未识别到公式")
    except Exception as e:
        show_tooltip(f"处理失败: {str(e)}")

def call_ocr_api(image_base64):
    """调用OCR API"""
    config = app_state.config
    api_config = config.get("api_config", {}).copy()
    
    # 动态插入图片数据
    if "messages" in api_config:
        for msg in api_config["messages"]:
            if "content" in msg and isinstance(msg["content"], list):
                for content_item in msg["content"]:
                    if isinstance(content_item, dict) and "image_url" in content_item:
                        content_item["image_url"]["url"] = f"data:image/png;base64,{image_base64}"
    
    try:
        response = requests.post(
            url = config["endpoint"].rstrip("/") + "/" + config.get("api_path", "").lstrip("/"),
            headers = {
                "Content-Type": "application/json",
                "api-key": config["api_key"]
            },
            json = api_config,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        show_tooltip(f"API请求失败: {str(e)}")
        return None

def extract_latex(content):
    """从响应内容提取LaTeX代码"""
    match = re.search(r"```latex\n(.*?)\n```", content, re.DOTALL)
    return match.group(1).strip() if match else None

def show_tooltip(text):
    """显示浮动提示"""
    tip = tk.Toplevel()
    tip.overrideredirect(True)
    tip.attributes("-topmost", True)
    
    # 获取鼠标位置
    x = tip.winfo_pointerx() + 15
    y = tip.winfo_pointery() + 10
    
    # 设置位置和内容
    tip.geometry(f"+{x}+{y}")
    label = tk.Label(tip, text=text, bg="yellow", fg="black", 
                    padx=5, pady=2, font=("微软雅黑", 10))
    label.pack()
    
    # 自动关闭
    tip.after(1500, tip.destroy)

def main():
    app_state.load_config()
    app_state.root = tk.Tk()
    app_state.root.withdraw()
    
    # 启动独立的热键维护线程
    hotkey_thread = threading.Thread(target=manage_hotkey, daemon=True)
    hotkey_thread.start()

    # 启动键盘监听线程
    keyboard_thread = threading.Thread(target=keyboard_wait_loop, daemon=True)
    keyboard_thread.start()
    
    app_state.root.mainloop()

if __name__ == "__main__":
    main()