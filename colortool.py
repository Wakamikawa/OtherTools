import colorsys
import ctypes
import sys
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk


try:
    from pynput import mouse
    import pyperclip
except ImportError as exc:
    missing_package = exc.name or "依赖包"
    messagebox.showerror(
        "缺少依赖",
        "请先在当前目录运行：\n\n"
        "python -m pip install -r requirements.txt\n\n"
        f"缺少的依赖：{missing_package}",
    )
    sys.exit(1)


@dataclass(frozen=True)
class ColorInfo:
    r: int
    g: int
    b: int

    @property
    def rgb_text(self):
        return f"{self.r}, {self.g}, {self.b}"

    @property
    def hex_text(self):
        return f"#{self.r:02X}{self.g:02X}{self.b:02X}"

    @property
    def normalized_rgb_text(self):
        return f"{self.r / 255:.4f}, {self.g / 255:.4f}, {self.b / 255:.4f}"

    @property
    def hsl(self):
        h, l, s = colorsys.rgb_to_hls(self.r / 255, self.g / 255, self.b / 255)
        return h * 360, s * 100, l * 100

    @property
    def hsv(self):
        h, s, v = colorsys.rgb_to_hsv(self.r / 255, self.g / 255, self.b / 255)
        return h * 360, s * 100, v * 100


COPY_FORMATS = {
    "Hex": lambda color: color.hex_text,
    "RGB": lambda color: f"rgb({color.r}, {color.g}, {color.b})",
    "RGB 0-1": lambda color: color.normalized_rgb_text,
}


def parse_rgb(value):
    raw = value.replace(",", " ").replace(";", " ")
    parts = raw.split()
    if len(parts) != 3:
        raise ValueError("请输入 3 个 RGB 数值。")

    try:
        values = [int(part) for part in parts]
    except ValueError as exc:
        raise ValueError("RGB 只能包含整数。") from exc

    if any(value < 0 or value > 255 for value in values):
        raise ValueError("RGB 数值范围必须是 0-255。")

    return ColorInfo(*values)


def get_pixel_color(x, y):
    hdc = ctypes.windll.user32.GetDC(0)
    try:
        color = ctypes.windll.gdi32.GetPixel(hdc, x, y)
    finally:
        ctypes.windll.user32.ReleaseDC(0, hdc)
    return ColorInfo(color & 0xFF, (color >> 8) & 0xFF, (color >> 16) & 0xFF)


class RGBApp:
    def __init__(self, root):
        self.root = root
        self.root.title("OtherTools - 色彩助手")
        self.root.geometry("300x500")
        self.root.minsize(280, 460)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.95)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.history = []
        self.listener = None
        self.current_color = ColorInfo(0, 166, 218)

        self.frame = ttk.Frame(root, padding="15")
        self.frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(self.frame, text="输入 RGB（例如 0,166,218）：").pack(anchor="w", pady=2)
        self.input_var = tk.StringVar(value=self.current_color.rgb_text)
        self.entry = ttk.Entry(self.frame, textvariable=self.input_var, font=("Consolas", 11))
        self.entry.pack(fill=tk.X, pady=5)
        self.entry.bind("<Return>", self.update_from_input)

        self.status_var = tk.StringVar(value="就绪")
        self.status_label = ttk.Label(self.frame, textvariable=self.status_var, foreground="gray")
        self.status_label.pack(anchor="w", pady=(0, 8))

        self.pick_btn = ttk.Button(
            self.frame,
            text="点击吸取屏幕颜色",
            command=self.start_picking,
        )
        self.pick_btn.pack(fill=tk.X, pady=6)

        self.label_hsl = ttk.Label(self.frame, font=("Microsoft YaHei", 10))
        self.label_hsl.pack(anchor="w", pady=(8, 0))
        self.label_hsv = ttk.Label(self.frame, font=("Microsoft YaHei", 10))
        self.label_hsv.pack(anchor="w")

        ttk.Label(self.frame, text="复制格式：").pack(anchor="w", pady=(12, 2))
        copy_row = ttk.Frame(self.frame)
        copy_row.pack(fill=tk.X)
        self.copy_format = tk.StringVar(value="Hex")
        self.copy_format_combo = ttk.Combobox(
            copy_row,
            textvariable=self.copy_format,
            values=list(COPY_FORMATS.keys()),
            state="readonly",
            width=9,
        )
        self.copy_format_combo.pack(side=tk.LEFT)
        self.copy_value_var = tk.StringVar()
        self.copy_entry = ttk.Entry(
            copy_row,
            textvariable=self.copy_value_var,
            justify="center",
            font=("Consolas", 10),
        )
        self.copy_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))
        self.copy_entry.bind("<Button-1>", lambda event: self.copy_current_value())
        self.copy_format_combo.bind("<<ComboboxSelected>>", lambda event: self.update_copy_value())

        self.canvas = tk.Canvas(self.frame, height=48, bg=self.current_color.hex_text, highlightthickness=1)
        self.canvas.pack(fill=tk.X, pady=12)

        ttk.Label(
            self.frame,
            text="最近记录（点击切换）：",
            foreground="gray",
            font=("Microsoft YaHei", 9),
        ).pack(anchor="w", pady=(8, 5))
        self.history_frame = ttk.Frame(self.frame)
        self.history_frame.pack(fill=tk.X)
        self.history_blocks = []
        for i in range(5):
            btn = tk.Canvas(
                self.history_frame,
                width=36,
                height=36,
                bg="#f0f0f0",
                highlightthickness=1,
                cursor="hand2",
            )
            btn.pack(side=tk.LEFT, padx=(0, 6))
            btn.bind("<Button-1>", lambda event, idx=i: self.load_history(idx))
            self.history_blocks.append(btn)

        self.update_ui(self.current_color)

    def set_status(self, message, is_error=False):
        self.status_var.set(message)
        self.status_label.config(foreground="firebrick" if is_error else "gray")

    def update_ui(self, color, add_history=True):
        self.current_color = color
        h_hsl, s_hsl, l_hsl = color.hsl
        h_hsv, s_hsv, v_hsv = color.hsv

        self.input_var.set(color.rgb_text)
        self.label_hsl.config(text=f"HSL：H {h_hsl:.0f}° / S {s_hsl:.1f}% / L {l_hsl:.1f}%")
        self.label_hsv.config(text=f"HSV：H {h_hsv:.0f}° / S {s_hsv:.1f}% / V {v_hsv:.1f}%")
        self.canvas.config(bg=color.hex_text)
        self.update_copy_value()
        self.set_status("就绪")

        if add_history:
            self.add_to_history(color)

    def update_copy_value(self):
        formatter = COPY_FORMATS[self.copy_format.get()]
        self.copy_value_var.set(formatter(self.current_color))

    def add_to_history(self, color):
        if self.history and self.history[0] == color:
            return

        self.history.insert(0, color)
        self.history = self.history[:5]
        for i, block in enumerate(self.history_blocks):
            if i < len(self.history):
                block.config(bg=self.history[i].hex_text)
            else:
                block.config(bg="#f0f0f0")

    def load_history(self, idx):
        if idx < len(self.history):
            self.update_ui(self.history[idx], add_history=False)

    def update_from_input(self, event=None):
        try:
            color = parse_rgb(self.input_var.get())
        except ValueError as exc:
            self.set_status(str(exc), is_error=True)
            return

        self.update_ui(color)

    def copy_current_value(self):
        value = self.copy_value_var.get()
        pyperclip.copy(value)
        self.set_status(f"已复制：{value}")

    def start_picking(self):
        if self.listener:
            return

        self.pick_btn.config(text="请在目标处点击鼠标左键", state="disabled")
        self.set_status("正在等待屏幕取色...")
        self.listener = mouse.Listener(on_click=self.on_screen_click)
        self.listener.start()

    def stop_picking(self):
        if self.listener:
            self.listener.stop()
            self.listener = None
        self.pick_btn.config(text="点击吸取屏幕颜色", state="normal")

    def on_screen_click(self, x, y, button, pressed):
        if pressed and button == mouse.Button.left:
            try:
                color = get_pixel_color(int(x), int(y))
            except OSError as exc:
                self.root.after(0, lambda: self.set_status(f"取色失败：{exc}", is_error=True))
            else:
                self.root.after(0, lambda: self.update_ui(color))
            finally:
                self.root.after(0, self.stop_picking)
            return False
        return None

    def close(self):
        self.stop_picking()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = RGBApp(root)
    root.mainloop()
