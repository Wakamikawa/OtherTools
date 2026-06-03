import colorsys
import ctypes
import math
import sys
import tkinter as tk
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


try:
    from PIL import Image, ImageGrab, ImageTk
except ImportError as exc:
    missing_package = exc.name or "依赖包"
    install_command = f'"{sys.executable}" -m pip install -r requirements.txt'
    messagebox.showerror(
        "缺少依赖",
        "请用启动本工具的同一个 Python 安装依赖：\n\n"
        f"{install_command}\n\n"
        f"缺少的依赖：{missing_package}\n\n"
        f"当前 Python：{sys.executable}",
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

    @property
    def luminance(self):
        return (0.2126 * self.r + 0.7152 * self.g + 0.0722 * self.b) / 255 * 100


@dataclass(frozen=True)
class ColorStat:
    color: ColorInfo
    percent: float


@dataclass(frozen=True)
class ToneFamily:
    color: ColorInfo
    percent: float
    lab: tuple
    chroma: float
    hue: float


COPY_FORMATS = {
    "Hex": lambda color: color.hex_text,
    "RGB": lambda color: color.rgb_text,
    "HSV": lambda color: f"HSV {color.hsv[0]:.0f} deg / {color.hsv[1]:.1f}% / {color.hsv[2]:.1f}%",
    "RGB 0-1": lambda color: color.normalized_rgb_text,
}

def enable_dpi_awareness():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def average_color(colors):
    count = len(colors)
    return ColorInfo(
        round(sum(color.r for color in colors) / count),
        round(sum(color.g for color in colors) / count),
        round(sum(color.b for color in colors) / count),
    )


def image_to_colors(image, max_pixels=60000):
    rgb_image = image.convert("RGB")
    width, height = rgb_image.size
    if width * height > max_pixels:
        scale = (max_pixels / (width * height)) ** 0.5
        new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        rgb_image = rgb_image.resize(new_size, Image.Resampling.BILINEAR)

    return [ColorInfo(r, g, b) for r, g, b in rgb_image.getdata()]


def srgb_channel_to_linear(value):
    value = value / 255
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def xyz_to_lab_channel(value):
    if value > 0.008856:
        return value ** (1 / 3)
    return 7.787 * value + 16 / 116


def color_to_lab(color):
    r = srgb_channel_to_linear(color.r)
    g = srgb_channel_to_linear(color.g)
    b = srgb_channel_to_linear(color.b)

    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041

    fx = xyz_to_lab_channel(x / 0.95047)
    fy = xyz_to_lab_channel(y)
    fz = xyz_to_lab_channel(z / 1.08883)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def lab_distance(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


def lab_chroma(lab):
    return (lab[1] ** 2 + lab[2] ** 2) ** 0.5


def hue_distance(a, b):
    delta = abs(a - b) % 360
    return min(delta, 360 - delta)


def bucket_colors(colors, bucket_size=32):
    buckets = defaultdict(list)
    for color in colors:
        key = (color.r // bucket_size, color.g // bucket_size, color.b // bucket_size)
        buckets[key].append(color)
    return buckets


def build_weighted_color_samples(colors, bucket_size=16):
    buckets = bucket_colors(colors, bucket_size)
    samples = []
    for bucket in buckets.values():
        color = average_color(bucket)
        samples.append(
            {
                "color": color,
                "lab": color_to_lab(color),
                "weight": len(bucket),
            }
        )
    return samples


def weighted_average_lab(samples):
    total = sum(sample["weight"] for sample in samples)
    return (
        sum(sample["lab"][0] * sample["weight"] for sample in samples) / total,
        sum(sample["lab"][1] * sample["weight"] for sample in samples) / total,
        sum(sample["lab"][2] * sample["weight"] for sample in samples) / total,
    )


def weighted_average_color(samples):
    total = sum(sample["weight"] for sample in samples)
    return ColorInfo(
        round(sum(sample["color"].r * sample["weight"] for sample in samples) / total),
        round(sum(sample["color"].g * sample["weight"] for sample in samples) / total),
        round(sum(sample["color"].b * sample["weight"] for sample in samples) / total),
    )


def initialize_lab_centers(samples, count):
    centers = [max(samples, key=lambda sample: sample["weight"])["lab"]]
    while len(centers) < count and len(centers) < len(samples):
        next_sample = max(
            samples,
            key=lambda sample: min(lab_distance(sample["lab"], center) for center in centers) * sample["weight"] ** 0.5,
        )
        if any(lab_distance(next_sample["lab"], center) < 0.01 for center in centers):
            break
        centers.append(next_sample["lab"])
    return centers


def cluster_colors_perceptually(colors, count=8, bucket_size=16, iterations=10):
    if not colors:
        return []

    samples = build_weighted_color_samples(colors, bucket_size)
    if not samples:
        return []

    count = min(count, len(samples))
    centers = initialize_lab_centers(samples, count)
    clusters = []

    for _ in range(iterations):
        clusters = [[] for _ in centers]
        for sample in samples:
            nearest_idx = min(range(len(centers)), key=lambda idx: lab_distance(sample["lab"], centers[idx]))
            clusters[nearest_idx].append(sample)

        next_centers = []
        next_clusters = []
        for center, cluster in zip(centers, clusters):
            if not cluster:
                next_centers.append(center)
                next_clusters.append(cluster)
                continue
            next_centers.append(weighted_average_lab(cluster))
            next_clusters.append(cluster)

        shift = max((lab_distance(old, new) for old, new in zip(centers, next_centers)), default=0)
        centers = next_centers
        clusters = next_clusters
        if shift < 0.05:
            break

    total = len(colors)
    stats = []
    for cluster in clusters:
        if not cluster:
            continue
        weight = sum(sample["weight"] for sample in cluster)
        stats.append(ColorStat(weighted_average_color(cluster), weight / total * 100))

    stats.sort(key=lambda stat: stat.percent, reverse=True)
    return stats


def weighted_average_stat(stats):
    total = sum(stat.percent for stat in stats)
    return ColorStat(
        ColorInfo(
            round(sum(stat.color.r * stat.percent for stat in stats) / total),
            round(sum(stat.color.g * stat.percent for stat in stats) / total),
            round(sum(stat.color.b * stat.percent for stat in stats) / total),
        ),
        total,
    )


def tone_family_from_stats(stats):
    stat = weighted_average_stat(stats)
    lab = color_to_lab(stat.color)
    return ToneFamily(stat.color, stat.percent, lab, lab_chroma(lab), stat.color.hsv[0])


def should_merge_into_family(stat, family):
    lab = color_to_lab(stat.color)
    lab_dist = lab_distance(lab, family.lab)
    hue_gap = hue_distance(stat.color.hsv[0], family.hue)
    lightness_gap = abs(lab[0] - family.lab[0])
    chroma_gap = abs(lab_chroma(lab) - family.chroma)

    if lab_dist <= 14:
        return True
    return hue_gap <= 12 and lightness_gap <= 16 and chroma_gap <= 18


def build_tone_families(colors, count=36, bucket_size=16):
    raw_stats = cluster_colors_perceptually(colors, count=count, bucket_size=bucket_size)
    families = []
    family_members = []

    for stat in raw_stats:
        if stat.percent < 0.04:
            continue
        match_index = None
        for idx, family in enumerate(families):
            if should_merge_into_family(stat, family):
                match_index = idx
                break
        if match_index is None:
            family_members.append([stat])
            families.append(tone_family_from_stats([stat]))
        else:
            family_members[match_index].append(stat)
            families[match_index] = tone_family_from_stats(family_members[match_index])

    families.sort(key=lambda family: family.percent, reverse=True)
    return families


def family_to_stat(family):
    return ColorStat(family.color, family.percent)


def nearest_family_distance(family, selected):
    if not selected:
        return 999.0
    return min(lab_distance(family.lab, item.lab) for item in selected)


def nearest_family_layer_gaps(family, selected):
    if not selected:
        return 999.0, 999.0, 180.0
    nearest = min(selected, key=lambda item: lab_distance(family.lab, item.lab))
    return (
        abs(family.lab[0] - nearest.lab[0]),
        abs(family.chroma - nearest.chroma),
        hue_distance(family.hue, nearest.hue),
    )


def is_auxiliary_family(family, main_families):
    if family.percent < 0.45:
        return False

    nearest_dist = nearest_family_distance(family, main_families)
    lightness_gap, chroma_gap, hue_gap = nearest_family_layer_gaps(family, main_families)
    if family.percent <= 3.5 and nearest_dist >= 30 and max(chroma_gap, hue_gap) >= 35:
        return False

    if nearest_dist >= 26:
        return True
    if lightness_gap >= 20 and nearest_dist >= 16:
        return True
    if chroma_gap >= 22 and nearest_dist >= 16:
        return True
    if hue_gap >= 24 and nearest_dist >= 18:
        return True
    return family.percent >= 2.0 and nearest_dist >= 18


def auxiliary_score(family, main_families):
    lightness_gap, chroma_gap, hue_gap = nearest_family_layer_gaps(family, main_families)
    area = min(family.percent / 8.0, 1.0)
    lightness = min(lightness_gap / 40.0, 1.0)
    chroma = min(chroma_gap / 45.0, 1.0)
    hue = min(hue_gap / 75.0, 1.0)
    return area * 0.45 + max(lightness, chroma, hue) * 0.35 + min(family.chroma / 70.0, 1.0) * 0.20


def accent_area_score(percent):
    if percent < 0.02 or percent > 3.5:
        return 0.0
    if percent <= 0.8:
        return 0.6 + percent / 0.8 * 0.4
    return max(0.0, 1.0 - (percent - 0.8) / 2.7 * 0.45)


def accent_family_score(family, context_families):
    if family.percent < 0.02 or family.percent > 3.5:
        return 0.0

    _hue, _saturation, value = family.color.hsv
    if value < 12 or family.chroma < 10:
        return 0.0

    nearest_dist = nearest_family_distance(family, context_families)
    if nearest_dist < 30:
        return 0.0

    lightness_gap, chroma_gap, hue_gap = nearest_family_layer_gaps(family, context_families)
    jump = max(
        min(lightness_gap / 42.0, 1.0),
        min(chroma_gap / 45.0, 1.0),
        min(hue_gap / 70.0, 1.0),
    )
    if jump < 0.55:
        return 0.0

    return (
        accent_area_score(family.percent) * 0.30
        + min(nearest_dist / 70.0, 1.0) * 0.25
        + min(family.chroma / 80.0, 1.0) * 0.25
        + jump * 0.20
    )


def unexplained_gamut_score(family, explained):
    if family.percent < 1.4:
        return 0.0

    nearest_dist = nearest_family_distance(family, explained)
    if nearest_dist < 24:
        return 0.0

    lightness_gap, chroma_gap, hue_gap = nearest_family_layer_gaps(family, explained)
    if family.percent <= 3.5 and nearest_dist >= 30 and max(chroma_gap, hue_gap) >= 35:
        return 0.0

    hue_signal = min(hue_gap / 70.0, 1.0)
    layer_signal = max(min(lightness_gap / 36.0, 1.0), min(chroma_gap / 42.0, 1.0))
    area_signal = min(family.percent / 6.0, 1.0)
    chroma_signal = min(family.chroma / 65.0, 1.0)
    return area_signal * 0.45 + max(hue_signal, layer_signal) * 0.35 + chroma_signal * 0.20


def backfill_auxiliary_families(families, main_families, auxiliary_families, count=6):
    selected = list(auxiliary_families)
    explained = main_families + selected
    candidates = []
    for family in families:
        if family in main_families or family in selected:
            continue
        score = unexplained_gamut_score(family, explained)
        if score >= 0.58:
            candidates.append((score, family))

    candidates.sort(key=lambda item: item[0], reverse=True)
    for _score, family in candidates:
        if len(selected) >= count:
            break
        if nearest_family_distance(family, main_families + selected) >= 18:
            selected.append(family)
    return selected


def salient_small_accent_score(family, context_families):
    if family.percent < 0.02 or family.percent > 2.2:
        return 0.0

    _hue, saturation, value = family.color.hsv
    if value < 14 or family.chroma < 9:
        return 0.0

    nearest_dist = nearest_family_distance(family, context_families)
    if nearest_dist < 24:
        return 0.0

    lightness_gap, chroma_gap, hue_gap = nearest_family_layer_gaps(family, context_families)
    jump = max(
        min(lightness_gap / 38.0, 1.0),
        min(chroma_gap / 34.0, 1.0),
        min(hue_gap / 55.0, 1.0),
        min(saturation / 75.0, 1.0),
    )
    if jump < 0.62:
        return 0.0

    area = min(family.percent / 0.65, 1.0)
    return area * 0.25 + min(nearest_dist / 62.0, 1.0) * 0.25 + min(family.chroma / 70.0, 1.0) * 0.25 + jump * 0.25


def add_accent_family(accent_families, family, count):
    if len(accent_families) >= count:
        return False
    if nearest_family_distance(family, accent_families) < 14:
        return False
    accent_families.append(family)
    return True


def family_group_compatible(family, group, role="main"):
    if not group:
        return True

    nearest = min(group, key=lambda item: lab_distance(family.lab, item.lab))
    lab_dist = lab_distance(family.lab, nearest.lab)
    lightness_gap = abs(family.lab[0] - nearest.lab[0])
    chroma_gap = abs(family.chroma - nearest.chroma)
    hue_gap = hue_distance(family.hue, nearest.hue)

    if lab_dist <= 22:
        return True

    if family.chroma < 12 or nearest.chroma < 12:
        return lab_dist <= 34 and lightness_gap <= 30

    if role == "auxiliary":
        return hue_gap <= 42 and lightness_gap <= 42 and chroma_gap <= 38 and lab_dist <= 52

    return hue_gap <= 34 and lightness_gap <= 38 and chroma_gap <= 34 and lab_dist <= 46


def select_coherent_layer_families(candidates, count, role="main", min_percent=0.0):
    selected = []
    for family in candidates:
        if len(selected) >= count:
            break
        if selected and family.percent < min_percent:
            continue
        if family_group_compatible(family, selected, role=role):
            selected.append(family)
    return selected


def select_main_families(families, count=6):
    if not families:
        return []

    top_percent = families[0].percent
    min_main_percent = max(1.2, top_percent * 0.12)
    return select_coherent_layer_families(
        families,
        count=count,
        role="main",
        min_percent=min_main_percent,
    )


def select_auxiliary_families(families, main_families, count=6):
    candidates = [family for family in families if is_auxiliary_family(family, main_families)]
    candidates.sort(key=lambda family: auxiliary_score(family, main_families), reverse=True)
    return select_coherent_layer_families(
        candidates,
        count=count,
        role="auxiliary",
        min_percent=0.35,
    )


def extract_color_structure(colors, image=None, bucket_size=16, main_count=6, auxiliary_count=6, accent_count=3):
    if not colors:
        return [], [], []

    families = build_tone_families(colors, count=36, bucket_size=bucket_size)
    if not families:
        return [], [], []

    main_families = select_main_families(families, count=main_count)
    remaining = [family for family in families if family not in main_families]

    auxiliary_families = select_auxiliary_families(remaining, main_families, count=auxiliary_count)
    auxiliary_families = backfill_auxiliary_families(
        families,
        main_families,
        auxiliary_families,
        count=auxiliary_count,
    )

    explained = main_families + auxiliary_families
    accent_candidates = []
    for family in remaining:
        if family in auxiliary_families:
            continue
        score = accent_family_score(family, explained)
        if score >= 0.62:
            accent_candidates.append((score, family))

    accent_candidates.sort(key=lambda item: item[0], reverse=True)
    accent_families = []
    for _score, family in accent_candidates:
        add_accent_family(accent_families, family, accent_count)

    if len(accent_families) < accent_count:
        backfill_candidates = []
        for family in remaining:
            if family in auxiliary_families or family in accent_families:
                continue
            score = salient_small_accent_score(family, explained)
            if score >= 0.60:
                backfill_candidates.append((score, family))
        backfill_candidates.sort(key=lambda item: item[0], reverse=True)
        for _score, family in backfill_candidates:
            add_accent_family(accent_families, family, accent_count)

    return (
        [family_to_stat(family) for family in main_families],
        [family_to_stat(family) for family in auxiliary_families],
        [family_to_stat(family) for family in accent_families],
    )


def value_distribution(colors):
    bins = [0] * 11
    if not colors:
        return bins

    for color in colors:
        value = max(0, min(10, round(color.luminance / 10)))
        bins[value] += 1
    return bins


class RGBApp:
    def __init__(self, root):
        self.root = root
        self.root.title("色彩分析助手")
        self.root.geometry("560x760")
        self.root.minsize(500, 520)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.97)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.current_color = ColorInfo(0, 166, 218)
        self.palette = []
        self.analysis_source = []
        self.dominant_palette = []
        self.auxiliary_palette = []
        self.accent_palette = []
        self.preview_image = None
        self.preview_source_image = None
        self.preview_source_name = ""
        self.copy_format = tk.StringVar(value="Hex")
        self.outer = ttk.Frame(root)
        self.outer.pack(fill=tk.BOTH, expand=True)
        self.scroll_canvas = tk.Canvas(self.outer, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.outer, orient=tk.VERTICAL, command=self.scroll_canvas.yview)
        self.scroll_canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.frame = ttk.Frame(self.scroll_canvas, padding="14")
        self.frame_window = self.scroll_canvas.create_window((0, 0), window=self.frame, anchor="nw")
        self.frame.bind("<Configure>", self.update_scroll_region)
        self.scroll_canvas.bind("<Configure>", self.resize_scroll_frame)
        self.root.bind_all("<MouseWheel>", self.on_mouse_wheel)
        self.root.bind_all("<Control-v>", lambda event: self.paste_from_clipboard())
        self.root.bind_all("<Control-V>", lambda event: self.paste_from_clipboard())

        self.build_status_section()
        self.build_source_section()
        self.build_palette_section()
        self.build_preview_section()
        self.build_color_structure_section()
        self.build_analysis_section()

        self.refresh_color_structure()
        self.update_current_display(self.current_color)

    def update_scroll_region(self, event=None):
        self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))

    def resize_scroll_frame(self, event):
        self.scroll_canvas.itemconfigure(self.frame_window, width=event.width)

    def on_mouse_wheel(self, event):
        self.scroll_canvas.yview_scroll(int(-event.delta / 120), "units")

    def build_status_section(self):
        self.status_var = tk.StringVar(value="就绪")
        self.status_label = ttk.Label(self.frame, textvariable=self.status_var, foreground="gray")
        self.status_label.pack(anchor="w", pady=(0, 8))

    def build_source_section(self):
        source = ttk.LabelFrame(self.frame, text="图片")
        source.pack(fill=tk.X, pady=(0, 10))

        row = ttk.Frame(source, padding=8)
        row.pack(fill=tk.X)
        ttk.Button(row, text="导入图片", command=self.open_image).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row, text="粘贴图片", command=self.paste_from_clipboard).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))

    def build_palette_section(self):
        palette_box = ttk.LabelFrame(self.frame, text="采样色板")
        palette_box.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        toolbar = ttk.Frame(palette_box, padding=(8, 8, 8, 4))
        toolbar.pack(fill=tk.X)
        ttk.Label(toolbar, text="格式").pack(side=tk.LEFT)
        self.copy_format_combo = ttk.Combobox(
            toolbar,
            textvariable=self.copy_format,
            values=list(COPY_FORMATS.keys()),
            state="readonly",
            width=9,
        )
        self.copy_format_combo.pack(side=tk.LEFT, padx=(8, 12))
        self.copy_format_combo.bind("<<ComboboxSelected>>", lambda event: self.refresh_palette())
        ttk.Button(toolbar, text="复制色板", command=self.copy_palette).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="清空", command=self.clear_palette).pack(side=tk.LEFT, padx=(8, 0))

        self.palette_frame = ttk.Frame(palette_box, padding=(8, 4, 8, 8))
        self.palette_frame.pack(fill=tk.BOTH, expand=True)

    def build_color_structure_section(self):
        structure = ttk.LabelFrame(self.frame, text="色彩结构")
        structure.pack(fill=tk.X, pady=(0, 10))

        self.dominant_frame = ttk.Frame(structure, padding=(8, 8, 8, 4))
        self.dominant_frame.pack(fill=tk.X)
        self.auxiliary_frame = ttk.Frame(structure, padding=(8, 4, 8, 4))
        self.auxiliary_frame.pack(fill=tk.X)
        self.accent_frame = ttk.Frame(structure, padding=(8, 4, 8, 8))
        self.accent_frame.pack(fill=tk.X)

    def build_preview_section(self):
        preview_box = ttk.LabelFrame(self.frame, text="预览图片")
        preview_box.pack(fill=tk.X, pady=(0, 10))

        self.preview_label = ttk.Label(preview_box)
        self.preview_label.pack(fill=tk.X, padx=8, pady=8)

    def build_analysis_section(self):
        analysis = ttk.LabelFrame(self.frame, text="明度结构")
        analysis.pack(fill=tk.X)

        self.value_canvas = tk.Canvas(analysis, height=220, bg="#202020", highlightthickness=0)
        self.value_canvas.pack(fill=tk.X, padx=8, pady=8)
        self.value_canvas.bind("<Configure>", lambda event: (self.refresh_preview(), self.refresh_analysis()))

    def set_status(self, message, is_error=False):
        self.status_var.set(message)
        self.status_label.config(foreground="firebrick" if is_error else "gray")

    def update_ui(self, color, add_palette=True):
        self.update_current_display(color)

        if add_palette:
            self.add_to_palette(color)
        else:
            self.refresh_analysis()

    def update_current_display(self, color):
        self.current_color = color
        if hasattr(self, "palette_frame"):
            self.refresh_palette()

    def add_to_palette(self, color):
        self.palette = [item for item in self.palette if item != color]
        self.palette.insert(0, color)
        self.palette = self.palette[:8]
        self.update_current_display(color)
        self.set_status(f"已加入色板：{COPY_FORMATS[self.copy_format.get()](color)}")

    def refresh_palette(self):
        for child in self.palette_frame.winfo_children():
            child.destroy()

        self.render_palette_item(self.palette_frame, self.current_color, row_index=0, column=0, is_current=True)

        self.palette_frame.columnconfigure(0, weight=1)

    def render_palette_item(self, parent, color, row_index, column, is_current=False):
        frame = ttk.Frame(parent)
        frame.grid(row=row_index, column=column, sticky="ew", padx=(0, 8), pady=(3, 8 if is_current else 3))
        value_column = 2 if is_current else 1
        frame.columnconfigure(value_column, weight=1)

        if is_current:
            ttk.Label(frame, text="当前颜色").grid(row=0, column=0, padx=(0, 8), sticky="w")

        swatch = tk.Canvas(
            frame,
            width=34,
            height=24,
            bg=color.hex_text,
            highlightthickness=2,
            highlightbackground="#D8D8D8",
            highlightcolor="#D8D8D8",
            cursor="hand2",
        )
        swatch.grid(row=0, column=1 if is_current else 0, padx=(0, 6))
        command = self.copy_color if is_current else self.update_current_display
        swatch.bind("<Button-1>", lambda event, item=color, action=command: action(item))

        text = COPY_FORMATS[self.copy_format.get()](color)
        label = ttk.Label(frame, text=text, font=("Consolas", 9), cursor="hand2")
        label.grid(row=0, column=value_column, sticky="w")
        label.bind("<Button-1>", lambda event, item=color, action=command: action(item))
        self.bind_color_hover(swatch, label)

    def refresh_color_structure(self):
        self.render_stat_group(self.dominant_frame, "主色调", self.dominant_palette)
        self.render_stat_group(self.auxiliary_frame, "辅色调", self.auxiliary_palette)
        self.render_stat_group(self.accent_frame, "点缀色", self.accent_palette)

    def format_percent(self, value):
        if value >= 10:
            return f"{value:.1f}%"
        if value >= 1:
            return f"{value:.2f}%"
        return f"{value:.3f}%"

    def render_stat_group(self, parent, title, stats):
        for child in parent.winfo_children():
            child.destroy()

        max_percent = max((stat.percent for stat in stats), default=0)
        title_text = title
        if stats:
            title_text = f"{title}  占比 0-{self.format_percent(max_percent)}"

        ttk.Label(parent, text=title_text, foreground="gray").grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 4))
        if not stats:
            ttk.Label(parent, text="暂无数据", foreground="gray").grid(row=1, column=0, sticky="w")
            return

        for idx, stat in enumerate(stats):
            row_idx = idx + 1
            swatch = tk.Canvas(
                parent,
                width=34,
                height=22,
                bg=stat.color.hex_text,
                highlightthickness=2,
                highlightbackground="#D8D8D8",
                highlightcolor="#D8D8D8",
                cursor="hand2",
            )
            swatch.grid(row=row_idx, column=0, padx=(0, 6), pady=3, sticky="w")
            swatch.bind("<Button-1>", lambda event, item=stat.color: self.add_to_palette(item))

            label = ttk.Label(parent, text=stat.color.hex_text, font=("Consolas", 9), cursor="hand2")
            label.grid(row=row_idx, column=1, sticky="w", padx=(0, 8))
            label.bind("<Button-1>", lambda event, item=stat.color: self.add_to_palette(item))
            self.bind_color_hover(swatch, label)

            bar = tk.Canvas(parent, height=16, bg=self.root.cget("bg"), highlightthickness=0)
            bar.grid(row=row_idx, column=2, sticky="ew", padx=(0, 8))
            bar.bind("<Configure>", lambda event, item=stat, max_value=max_percent: self.draw_percent_bar(event.widget, item, max_value))

            percent_label = ttk.Label(parent, text=self.format_percent(stat.percent), font=("Consolas", 9))
            percent_label.grid(row=row_idx, column=3, sticky="e")

        parent.columnconfigure(2, weight=1)

    def bind_color_hover(self, swatch, label):
        def set_hover(_event):
            swatch.config(highlightbackground="#2D8CFF", highlightcolor="#2D8CFF")

        def clear_hover(_event):
            swatch.config(highlightbackground="#D8D8D8", highlightcolor="#D8D8D8")

        for widget in (swatch, label):
            widget.bind("<Enter>", set_hover)
            widget.bind("<Leave>", clear_hover)

    def draw_percent_bar(self, canvas, stat, max_percent):
        canvas.delete("all")
        width = max(canvas.winfo_width(), 1)
        height = max(canvas.winfo_height(), 16)
        if max_percent <= 0:
            return

        ratio = stat.percent / max_percent
        bar_width = max(1, width * ratio)
        canvas.create_rectangle(0, 2, width, height - 2, fill="", outline="#D8D8D8")
        canvas.create_rectangle(0, 2, bar_width, height - 2, fill=stat.color.hex_text, outline="")

    def clear_palette(self):
        self.palette = []
        self.refresh_palette()
        self.set_status("色板已清空")

    def copy_to_clipboard(self, value):
        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        self.set_status(f"已复制：{value}")

    def copy_color(self, color):
        self.copy_to_clipboard(COPY_FORMATS[self.copy_format.get()](color))

    def copy_palette(self):
        formatter = COPY_FORMATS[self.copy_format.get()]
        self.copy_to_clipboard(formatter(self.current_color))

    def paste_from_clipboard(self):
        try:
            image = ImageGrab.grabclipboard()
        except Exception as exc:
            self.set_status(f"读取剪贴板失败：{exc}", is_error=True)
            return

        if image is None:
            self.set_status("剪贴板中没有图片，请先截图再粘贴。", is_error=True)
            return

        if not isinstance(image, Image.Image):
            self.set_status("剪贴板内容不是图片（可能是文件路径或文字）。", is_error=True)
            return

        self.apply_image_analysis(image, "剪贴板图片")

    def open_image(self):
        file_path = filedialog.askopenfilename(
            title="选择参考图",
            filetypes=[
                ("图片文件", "*.png *.jpg *.jpeg *.bmp *.webp"),
                ("所有文件", "*.*"),
            ],
        )
        if not file_path:
            return

        try:
            image = Image.open(file_path)
        except OSError as exc:
            self.set_status(f"图片打开失败：{exc}", is_error=True)
            return

        self.apply_image_analysis(image, Path(file_path).name)

    def apply_image_analysis(self, image, source_name):
        colors = image_to_colors(image)
        dominant_palette, auxiliary_palette, accent_palette = extract_color_structure(colors, image=image)
        if not dominant_palette:
            self.set_status("没有可分析的像素。", is_error=True)
            return

        self.dominant_palette = dominant_palette
        self.auxiliary_palette = auxiliary_palette
        self.accent_palette = accent_palette
        self.analysis_source = colors
        self.update_ui(self.dominant_palette[0].color, add_palette=False)
        self.refresh_color_structure()
        self.refresh_analysis()
        self.update_preview(image, source_name)
        self.set_status(f"已分析：{source_name}")

    def update_preview(self, image, source_name):
        self.preview_source_image = image.convert("RGB")
        self.preview_source_name = source_name
        self.refresh_preview()

    def refresh_preview(self):
        if not self.preview_source_image or not hasattr(self, "value_canvas"):
            return

        canvas_width = max(self.value_canvas.winfo_width(), 440)
        target_width = max(1, canvas_width - 56)
        source_width, source_height = self.preview_source_image.size
        target_height = max(1, round(source_height * target_width / source_width))
        preview = self.preview_source_image.resize((target_width, target_height), Image.Resampling.LANCZOS)
        self.preview_image = ImageTk.PhotoImage(preview)
        self.preview_label.config(image=self.preview_image, text=self.preview_source_name, compound=tk.TOP)

    def refresh_analysis(self):
        source = self.analysis_source or self.palette
        if not hasattr(self, "value_canvas"):
            return

        canvas = self.value_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 440)
        height = max(canvas.winfo_height(), 220)
        margin_x = 28
        top = 18
        step_h = 34
        gap = 4
        usable_w = width - margin_x * 2
        step_w = usable_w / 11

        for value in range(11):
            gray = round(value / 10 * 255)
            color = f"#{gray:02X}{gray:02X}{gray:02X}"
            x1 = margin_x + value * step_w
            x2 = margin_x + (value + 1) * step_w - gap
            canvas.create_rectangle(x1, top, x2, top + step_h, fill=color, outline="")
            label_color = "white" if value < 5 else "black"
            canvas.create_text((x1 + x2) / 2, top + step_h / 2, text=str(value), fill=label_color, font=("Consolas", 10, "bold"))

        bins = value_distribution(source)
        total = sum(bins)
        chart_top = top + step_h + 34
        chart_bottom = height - 30
        chart_h = max(60, chart_bottom - chart_top)
        max_count = max(bins) if bins else 0

        canvas.create_line(margin_x, chart_bottom, width - margin_x, chart_bottom, fill="#777777")
        if not total:
            canvas.create_text(width / 2, chart_top + chart_h / 2, text="暂无明度数据", fill="#CCCCCC", font=("Microsoft YaHei", 11))
            return

        for value, count in enumerate(bins):
            ratio = count / max_count if max_count else 0
            x1 = margin_x + value * step_w
            x2 = margin_x + (value + 1) * step_w - gap
            bar_h = ratio * chart_h
            y1 = chart_bottom - bar_h
            gray = round(value / 10 * 255)
            fill = f"#{gray:02X}{gray:02X}{gray:02X}"
            outline = "#B0B0B0" if value < 5 else "#555555"
            canvas.create_rectangle(x1, y1, x2, chart_bottom, fill=fill, outline=outline)
            percent = count / total * 100
            if percent >= 1:
                canvas.create_text((x1 + x2) / 2, y1 - 9, text=f"{percent:.0f}%", fill="#DDDDDD", font=("Consolas", 8))
            canvas.create_text((x1 + x2) / 2, chart_bottom + 14, text=str(value), fill="#BBBBBB", font=("Consolas", 9))

    def close(self):
        self.root.destroy()


if __name__ == "__main__":
    enable_dpi_awareness()
    root = tk.Tk()
    app = RGBApp(root)
    root.mainloop()



