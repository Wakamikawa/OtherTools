import ctypes
import subprocess
import sys
import tkinter as tk
from tkinter import ttk


def install_dependencies():
    """Install runtime dependencies when they are missing."""
    required_libs = ["pynput", "pyperclip"]
    for lib in required_libs:
        try:
            __import__(lib)
        except ImportError:
            print(f"正在初始化运行环境，安装 {lib}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", lib])


install_dependencies()

from pynput import mouse  # noqa: E402
import pyperclip  # noqa: E402


def get_pixel_color(x, y):
    hdc = ctypes.windll.user32.GetDC(0)
    color = ctypes.windll.gdi32.GetPixel(hdc, x, y)
    ctypes.windll.user32.ReleaseDC(0, hdc)
    return color & 0xFF, (color >> 8) & 0xFF, (color >> 16) & 0xFF


def rgb_to_sl(r, g, b):
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    mx, mn = max(r, g, b), min(r, g, b)
    df = mx - mn
    l = (mx + mn) / 2
    s = 0 if df == 0 else df / (1 - abs(2 * l - 1))
    return s * 100, l * 100


class RGBApp:
    def __init__(self, root):
        self.root = root
        self.root.title("色彩助手 Pro")
        self.root.geometry("260x420")
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.95)
        self.history = []

        self.frame = ttk.Frame(root, padding="15")
        self.frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(self.frame, text="输入 RGB（例如 0,166,218）：").pack(pady=2)
        self.input_var = tk.StringVar(value="0, 166, 218")
        self.entry = ttk.Entry(self.frame, textvariable=self.input_var, font=("Consolas", 11))
        self.entry.pack(fill=tk.X, pady=5)
        self.entry.bind("<Return>", self.update_from_input)

        self.pick_btn = ttk.Button(
            self.frame,
            text="点击吸取屏幕颜色",
            command=self.start_picking,
        )
        self.pick_btn.pack(fill=tk.X, pady=10)

        self.label_s = ttk.Label(self.frame, text="饱和度（S）：100.0%", font=("Microsoft YaHei", 10))
        self.label_s.pack(anchor="w")
        self.label_l = ttk.Label(self.frame, text="明度（L）：42.7%", font=("Microsoft YaHei", 10))
        self.label_l.pack(anchor="w")

        self.hex_var = tk.StringVar(value="#00A6DA")
        self.hex_entry = ttk.Entry(
            self.frame,
            textvariable=self.hex_var,
            justify="center",
            font=("Consolas", 10),
        )
        self.hex_entry.pack(fill=tk.X, pady=10)
        self.hex_entry.bind("<Button-1>", lambda e: self.copy_hex())

        self.canvas = tk.Canvas(self.frame, height=40, bg="#00A6DA", highlightthickness=1)
        self.canvas.pack(fill=tk.X, pady=5)

        ttk.Label(
            self.frame,
            text="最近记录（点击切换）：",
            foreground="gray",
            font=("Microsoft YaHei", 9),
        ).pack(pady=(10, 5))
        self.history_frame = ttk.Frame(self.frame)
        self.history_frame.pack(fill=tk.X)
        self.history_blocks = []
        for i in range(5):
            btn = tk.Canvas(
                self.history_frame,
                width=32,
                height=32,
                bg="#f0f0f0",
                highlightthickness=1,
                cursor="hand2",
            )
            btn.pack(side=tk.LEFT, padx=3)
            btn.bind("<Button-1>", lambda e, idx=i: self.load_history(idx))
            self.history_blocks.append(btn)

    def update_ui(self, r, g, b, add_h=True):
        s, l = rgb_to_sl(r, g, b)
        hex_c = f"#{r:02x}{g:02x}{b:02x}".upper()
        self.input_var.set(f"{r}, {g}, {b}")
        self.label_s.config(text=f"饱和度（S）：{s:.1f}%")
        self.label_l.config(text=f"明度（L）：{l:.1f}%")
        self.hex_var.set(hex_c)
        self.canvas.config(bg=hex_c)
        if add_h:
            self.add_to_history(r, g, b)

    def add_to_history(self, r, g, b):
        color = (r, g, b)
        if not self.history or self.history[0] != color:
            self.history.insert(0, color)
            self.history = self.history[:5]
            for i, col in enumerate(self.history):
                hc = f"#{col[0]:02x}{col[1]:02x}{col[2]:02x}"
                self.history_blocks[i].config(bg=hc)

    def load_history(self, idx):
        if idx < len(self.history):
            self.update_ui(*self.history[idx], add_h=False)

    def update_from_input(self, e=None):
        try:
            raw = self.input_var.get().replace(",", " ").replace(";", " ")
            vals = [max(0, min(255, int(x))) for x in raw.split()]
            if len(vals) == 3:
                self.update_ui(*vals)
        except ValueError:
            pass

    def copy_hex(self):
        pyperclip.copy(self.hex_var.get())
        old = self.hex_var.get()
        self.hex_var.set("已复制到剪贴板")
        self.root.after(800, lambda: self.hex_var.set(old))

    def start_picking(self):
        self.pick_btn.config(text="请在目标处点击鼠标左键", state="disabled")
        self.listener = mouse.Listener(on_click=self.on_screen_click)
        self.listener.start()

    def on_screen_click(self, x, y, button, pressed):
        if pressed and button == mouse.Button.left:
            r, g, b = get_pixel_color(int(x), int(y))
            self.root.after(0, lambda: self.update_ui(r, g, b))
            self.root.after(
                0,
                lambda: self.pick_btn.config(text="点击吸取屏幕颜色", state="normal"),
            )
            return False
        return None


if __name__ == "__main__":
    root = tk.Tk()
    app = RGBApp(root)
    root.mainloop()
