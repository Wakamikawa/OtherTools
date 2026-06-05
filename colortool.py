import colorsys
import ctypes
import json
import math
import os
import shutil
import sys
import tkinter as tk
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, font as tkfont, messagebox, ttk


try:
    from PIL import Image, ImageDraw, ImageGrab, ImageTk
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

try:
    PIL_IMAGE_ERRORS = (OSError, ValueError, Image.DecompressionBombError)
except AttributeError:
    PIL_IMAGE_ERRORS = (OSError, ValueError)

DND_FILES = None


def show_missing_dependency(exc, fallback_name):
    missing_package = exc.name or fallback_name
    install_command = f'"{sys.executable}" -m pip install -r requirements.txt'
    messagebox.showerror(
        "缺少依赖",
        "请用启动本工具的同一个 Python 安装依赖：\n\n"
        f"{install_command}\n\n"
        f"缺少的依赖：{missing_package}\n\n"
        f"当前 Python：{sys.executable}",
    )
    sys.exit(1)


def create_tk_root():
    global DND_FILES
    try:
        from tkinterdnd2 import DND_FILES as dnd_files, TkinterDnD
    except ImportError as exc:
        show_missing_dependency(exc, "tkinterdnd2")
    DND_FILES = dnd_files
    return TkinterDnD.Tk()


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


class ImageAnalysisError(ValueError):
    pass


COPY_FORMATS = {
    "Hex": lambda color: color.hex_text,
    "RGB": lambda color: color.rgb_text,
    "HSV": lambda color: f"HSV {color.hsv[0]:.0f} deg / {color.hsv[1]:.1f}% / {color.hsv[2]:.1f}%",
    "RGB 0-1": lambda color: color.normalized_rgb_text,
}


APP_TITLE = "Chromie"
DEFAULT_DISPLAY_TITLE = "Chromie"
BASE_DIR = Path(__file__).resolve().parent
CHROMIE_ASSET_PATH = BASE_DIR / "assets" / "chromie.png"
CONFIG_DIR = Path(os.environ.get("APPDATA", BASE_DIR)) / "Chromie"
CONFIG_PATH = CONFIG_DIR / "config.json"
USER_AVATAR_PATH = CONFIG_DIR / "avatar.png"
FONT_UI = ("Microsoft YaHei UI", 10, "bold")
FONT_TITLE = ("Microsoft YaHei UI", 17, "bold")
FONT_SUBTITLE = ("Microsoft YaHei UI", 11, "bold")
FONT_MONO = ("Cascadia Mono", 9, "bold")
FONT_MONO_SMALL = ("Cascadia Mono", 8, "bold")
PREVIEW_EMPTY_HEIGHT = 330
PREVIEW_MAX_IMAGE_HEIGHT = 300
PREVIEW_NAME_HEIGHT = 30
MAX_INPUT_PIXELS = 40_000_000
MAX_PREVIEW_SOURCE_PIXELS = 2_000_000
MAX_AVATAR_PIXELS = 4_000_000
DEFAULT_THEME_NAME = "orange_umber"

THEME_SHARED = {
    "chart": "#272625",
    "chart_line": "#7D746C",
    "swatch_border": "#6F655C",
    "pet_key": "#FF00FF",
}

THEME_PRESETS = {
    "red_clay": {
        "label": "赤",
        "name": "Red Clay",
        "colors": {
            "window": "#E2D9D6",
            "panel": "#F1EAE7",
            "panel_alt": "#D7C9C5",
            "panel_shadow": "#C8BAB6",
            "line": "#9A8580",
            "soft_line": "#E4DBD8",
            "text": "#352D2B",
            "muted": "#766966",
            "accent": "#8A5C57",
            "accent_dark": "#5B3B38",
            "danger": "#B86468",
        },
    },
    "orange_umber": {
        "label": "橙",
        "name": "Orange Umber",
        "colors": {
            "window": "#E3DDD4",
            "panel": "#F1ECE4",
            "panel_alt": "#D8CEC3",
            "panel_shadow": "#C9BDB1",
            "line": "#9D8F82",
            "soft_line": "#E4DCD2",
            "text": "#342F2A",
            "muted": "#7B6F65",
            "accent": "#8A6043",
            "accent_dark": "#5A3B29",
            "danger": "#B86468",
        },
    },
    "yellow_ochre": {
        "label": "黄",
        "name": "Yellow Ochre",
        "colors": {
            "window": "#E1DED2",
            "panel": "#F0EDE2",
            "panel_alt": "#D5D0BD",
            "panel_shadow": "#C7C0AB",
            "line": "#948C72",
            "soft_line": "#E3DFD1",
            "text": "#343126",
            "muted": "#716C5C",
            "accent": "#83734E",
            "accent_dark": "#55492F",
            "danger": "#A8645F",
        },
    },
    "moss_green": {
        "label": "绿",
        "name": "Moss Green",
        "colors": {
            "window": "#DDE1D8",
            "panel": "#EEF1E9",
            "panel_alt": "#CBD3C6",
            "panel_shadow": "#BBC6B7",
            "line": "#87927F",
            "soft_line": "#E1E7DC",
            "text": "#2E352D",
            "muted": "#697466",
            "accent": "#667A58",
            "accent_dark": "#405039",
            "danger": "#A65F62",
        },
    },
    "cyan_sage": {
        "label": "青",
        "name": "Cyan Sage",
        "colors": {
            "window": "#D8E0DE",
            "panel": "#EAF1EF",
            "panel_alt": "#C5D2CF",
            "panel_shadow": "#B6C4C1",
            "line": "#7F9290",
            "soft_line": "#DEE8E5",
            "text": "#2B3736",
            "muted": "#657674",
            "accent": "#5B7A78",
            "accent_dark": "#3C5251",
            "danger": "#A65F62",
        },
    },
    "slate_blue": {
        "label": "蓝",
        "name": "Slate Blue",
        "colors": {
            "window": "#D9DEE3",
            "panel": "#EDF0F3",
            "panel_alt": "#C9D0D8",
            "panel_shadow": "#B8C0C9",
            "line": "#7F8A96",
            "soft_line": "#E0E5EA",
            "text": "#2C333A",
            "muted": "#68727D",
            "accent": "#5F7186",
            "accent_dark": "#3E4B5A",
            "danger": "#A96368",
        },
    },
    "muted_plum": {
        "label": "紫",
        "name": "Muted Plum",
        "colors": {
            "window": "#DFDADF",
            "panel": "#F0ECF0",
            "panel_alt": "#D1C8D1",
            "panel_shadow": "#C2B7C2",
            "line": "#918393",
            "soft_line": "#E5DEE6",
            "text": "#352F36",
            "muted": "#766B78",
            "accent": "#79657F",
            "accent_dark": "#514357",
            "danger": "#A86268",
        },
    },
    "gray": {
        "label": "灰",
        "name": "Gray",
        "colors": {
            "window": "#DCDCDC",
            "panel": "#EEEEEE",
            "panel_alt": "#CCCCCC",
            "panel_shadow": "#BBBBBB",
            "line": "#888888",
            "soft_line": "#E2E2E2",
            "text": "#303030",
            "muted": "#707070",
            "accent": "#686868",
            "accent_dark": "#484848",
            "danger": "#9A6666",
        },
    },
}

THEME = {**THEME_PRESETS[DEFAULT_THEME_NAME]["colors"], **THEME_SHARED}


def enable_dpi_awareness():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def load_config():
    if not CONFIG_PATH.exists():
        return {}
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_config(config):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w", encoding="utf-8") as file:
        json.dump(config, file, ensure_ascii=False, indent=2)


def fit_text_to_width(text, font, max_width):
    text = str(text)
    max_width = max(1, int(max_width))
    measure_font = tkfont.Font(font=font)
    if measure_font.measure(text) <= max_width:
        return text

    ellipsis = "..."
    if measure_font.measure(ellipsis) > max_width:
        return ""

    low = 0
    high = len(text)
    while low < high:
        mid = (low + high + 1) // 2
        candidate = text[:mid] + ellipsis
        if measure_font.measure(candidate) <= max_width:
            low = mid
        else:
            high = mid - 1
    return text[:low] + ellipsis


def average_color(colors):
    count = len(colors)
    return ColorInfo(
        round(sum(color.r for color in colors) / count),
        round(sum(color.g for color in colors) / count),
        round(sum(color.b for color in colors) / count),
    )


def image_size(image):
    try:
        width, height = image.size
    except (AttributeError, TypeError) as exc:
        raise ImageAnalysisError("无法读取图片尺寸。") from exc
    try:
        width = int(width)
        height = int(height)
    except (TypeError, ValueError) as exc:
        raise ImageAnalysisError("图片尺寸无效。") from exc
    if width <= 0 or height <= 0:
        raise ImageAnalysisError("图片尺寸无效。")
    return width, height


def ensure_image_size_allowed(image, max_pixels=MAX_INPUT_PIXELS):
    width, height = image_size(image)
    if width * height > max_pixels:
        megapixels = max_pixels / 1_000_000
        raise ImageAnalysisError(f"图片尺寸过大：{width} x {height}，请使用不超过 {megapixels:.0f}MP 的图片。")
    return width, height


def convert_image_safely(image, mode):
    try:
        return image.convert(mode)
    except PIL_IMAGE_ERRORS as exc:
        raise ImageAnalysisError(f"图片解码失败：{exc}") from exc


def image_to_colors(image, max_pixels=60000):
    ensure_image_size_allowed(image)
    rgb_image = convert_image_safely(image, "RGB")
    width, height = rgb_image.size
    if width * height > max_pixels:
        scale = (max_pixels / (width * height)) ** 0.5
        new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        rgb_image = rgb_image.resize(new_size, Image.Resampling.BILINEAR)

    return [ColorInfo(r, g, b) for r, g, b in rgb_image.getdata()]


def make_preview_source_image(image):
    ensure_image_size_allowed(image)
    preview = convert_image_safely(image, "RGB")
    width, height = preview.size
    if width * height > MAX_PREVIEW_SOURCE_PIXELS:
        scale = (MAX_PREVIEW_SOURCE_PIXELS / (width * height)) ** 0.5
        new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        preview = preview.resize(new_size, Image.Resampling.LANCZOS)
    return preview


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


def extract_color_structure(colors, bucket_size=16, main_count=6, auxiliary_count=6, accent_count=3):
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


def make_rounded_image(width, height, radius, fill, bg, outline=None, shadow=None, scale=3):
    width = max(2, int(width))
    height = max(2, int(height))
    canvas = Image.new("RGB", (width * scale, height * scale), bg)
    draw = ImageDraw.Draw(canvas)
    rect = (scale, scale, (width - 1) * scale, (height - 1) * scale)
    if shadow:
        shadow_rect = (scale * 2, scale * 4, width * scale, height * scale)
        draw.rounded_rectangle(shadow_rect, radius=radius * scale, fill=shadow)
    draw.rounded_rectangle(rect, radius=radius * scale, fill=fill, outline=outline, width=scale if outline else 1)
    return canvas.resize((width, height), Image.Resampling.LANCZOS)


def make_transparent_pill(width, height, radius, fill, shadow=None, scale=3):
    width = max(2, int(width))
    height = max(2, int(height))
    canvas = Image.new("RGBA", (width * scale, height * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    if shadow:
        shadow_rect = (scale * 2, scale * 4, width * scale, height * scale)
        draw.rounded_rectangle(shadow_rect, radius=radius * scale, fill=shadow)
    rect = (scale, scale, (width - 1) * scale, (height - 1) * scale)
    draw.rounded_rectangle(rect, radius=radius * scale, fill=fill)
    return canvas.resize((width, height), Image.Resampling.LANCZOS)


def make_dashed_rounded_outline(width, height, radius, outline, bg, dash=5, gap=4, line_width=2, scale=3):
    width = max(2, int(width))
    height = max(2, int(height))
    scale = max(1, int(scale))
    canvas = Image.new("RGBA", (width * scale, height * scale), bg)
    draw = ImageDraw.Draw(canvas)
    stroke = max(1, line_width * scale)
    dash_len = max(1, dash * scale)
    gap_len = max(1, gap * scale)
    radius = max(1, min(radius * scale, (width * scale - stroke) // 2, (height * scale - stroke) // 2))
    x1 = stroke / 2
    y1 = stroke / 2
    x2 = width * scale - stroke / 2 - 1
    y2 = height * scale - stroke / 2 - 1
    step = max(2, scale)
    points = []

    def add_line(start, end, count):
        sx, sy = start
        ex, ey = end
        for index in range(count):
            progress = index / max(1, count)
            points.append((sx + (ex - sx) * progress, sy + (ey - sy) * progress))

    def add_arc(cx, cy, start_deg, end_deg):
        arc_len = abs(end_deg - start_deg) / 180 * math.pi * radius
        count = max(4, round(arc_len / step))
        for index in range(count):
            angle = math.radians(start_deg + (end_deg - start_deg) * index / max(1, count))
            points.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))

    add_line((x1 + radius, y1), (x2 - radius, y1), max(1, round((x2 - x1 - radius * 2) / step)))
    add_arc(x2 - radius, y1 + radius, -90, 0)
    add_line((x2, y1 + radius), (x2, y2 - radius), max(1, round((y2 - y1 - radius * 2) / step)))
    add_arc(x2 - radius, y2 - radius, 0, 90)
    add_line((x2 - radius, y2), (x1 + radius, y2), max(1, round((x2 - x1 - radius * 2) / step)))
    add_arc(x1 + radius, y2 - radius, 90, 180)
    add_line((x1, y2 - radius), (x1, y1 + radius), max(1, round((y2 - y1 - radius * 2) / step)))
    add_arc(x1 + radius, y1 + radius, 180, 270)

    if len(points) > 1:
        phase = 0
        for start, end in zip(points, points[1:] + points[:1]):
            segment_len = math.dist(start, end)
            if phase < dash_len:
                draw.line((start, end), fill=outline, width=stroke)
            phase = (phase + segment_len) % (dash_len + gap_len)

    return canvas.resize((width, height), Image.Resampling.LANCZOS)


def round_image_corners(image, radius, scale=3):
    rounded = image.convert("RGBA")
    width, height = rounded.size
    scale = max(1, int(scale))
    mask = Image.new("L", (width * scale, height * scale), 0)
    draw = ImageDraw.Draw(mask)
    rect = (0, 0, width * scale - 1, height * scale - 1)
    draw.rounded_rectangle(rect, radius=radius * scale, fill=255)
    if scale > 1:
        mask = mask.resize((width, height), Image.Resampling.LANCZOS)
    rounded.putalpha(mask)
    return rounded


def harden_alpha(image, threshold=96):
    image = image.convert("RGBA")
    alpha = image.getchannel("A").point(lambda value: 255 if value >= threshold else 0)
    image.putalpha(alpha)
    return image


def load_chromie_image(size, hard_alpha=False, source_path=None):
    path = Path(source_path) if source_path else CHROMIE_ASSET_PATH
    try:
        image = Image.open(path)
        if source_path:
            ensure_image_size_allowed(image, max_pixels=MAX_AVATAR_PIXELS)
        image = convert_image_safely(image, "RGBA")
    except (OSError, ImageAnalysisError):
        image = Image.open(CHROMIE_ASSET_PATH).convert("RGBA")
    bbox = image.getbbox()
    if bbox:
        image = image.crop(bbox)
    image.thumbnail((size, size), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    x = (size - image.width) // 2
    y = (size - image.height) // 2
    canvas.alpha_composite(image, (x, y))
    if hard_alpha:
        canvas = harden_alpha(canvas)
    return canvas


def load_pet_avatar_image(size, source_path=None):
    avatar = load_chromie_image(size, hard_alpha=True, source_path=source_path).convert("RGBA")
    keyed = Image.new("RGBA", (size, size), THEME["pet_key"])
    keyed.alpha_composite(avatar)
    return keyed.convert("RGB")


class RoundedPanel(tk.Canvas):
    def __init__(self, parent, title, min_height=92, fixed_height=False):
        super().__init__(parent, bg=THEME["window"], highlightthickness=0, height=min_height)
        self.title = title
        self.min_height = min_height
        self.fixed_height = fixed_height
        self.pad_x = 16
        self.title_h = 34 if title else 14
        self.bottom_pad = 16
        self.bg_image = None
        self.body = ttk.Frame(self, style="Panel.TFrame")
        self.body_window = self.create_window(self.pad_x, self.title_h, window=self.body, anchor="nw")
        self.bind("<Configure>", self.redraw)
        self.body.bind("<Configure>", self.sync_height)

    def sync_height(self, _event=None):
        if self.fixed_height:
            return
        desired = max(self.min_height, self.title_h + self.body.winfo_reqheight() + self.bottom_pad)
        if abs(self.winfo_height() - desired) > 2:
            self.configure(height=desired)

    def redraw(self, _event=None):
        self.delete("surface")
        width = max(1, self.winfo_width())
        height = max(self.min_height, self.winfo_height())
        image = make_rounded_image(
            width,
            height,
            26,
            THEME["panel"],
            THEME["window"],
            outline=THEME["soft_line"],
            shadow=THEME["panel_shadow"],
        )
        self.bg_image = ImageTk.PhotoImage(image)
        self.create_image(0, 0, image=self.bg_image, anchor="nw", tags=("surface",))
        if self.title:
            self.create_text(
                self.pad_x,
                20,
                anchor="w",
                text=self.title,
                fill=THEME["accent_dark"],
                font=FONT_SUBTITLE,
                tags=("surface",),
            )
        self.tag_lower("surface", self.body_window)
        self.itemconfigure(self.body_window, width=max(1, width - self.pad_x * 2))


class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command, variant="primary", min_width=92):
        bg = THEME["window"] if variant == "pet" else THEME["panel"]
        super().__init__(
            parent,
            width=min_width,
            height=36,
            bg=bg,
            highlightthickness=0,
            cursor="hand2",
        )
        self.text = text
        self.command = command
        self.variant = variant
        self.hovered = False
        self.bg_image = None
        self.bind("<Configure>", lambda _event: self.redraw())
        self.bind("<Enter>", self.enter)
        self.bind("<Leave>", self.leave)
        self.bind("<Button-1>", lambda _event: self.command())
        self.redraw()

    def colors(self):
        if self.variant == "primary":
            return (THEME["accent_dark"] if self.hovered else THEME["accent"], "#FFFFFF")
        if self.variant == "pet":
            return (THEME["accent"] if self.hovered else THEME["panel_alt"], THEME["accent_dark"])
        return (THEME["accent"] if self.hovered else THEME["panel_alt"], "#FFFFFF" if self.hovered else THEME["accent_dark"])

    def enter(self, _event):
        self.hovered = True
        self.redraw()

    def leave(self, _event):
        self.hovered = False
        self.redraw()

    def redraw(self):
        self.delete("all")
        width = max(1, self.winfo_width())
        fill, text_color = self.colors()
        bg = THEME["window"] if self.variant == "pet" else THEME["panel"]
        image = make_rounded_image(width, 36, 17, fill, bg, shadow=THEME["panel_shadow"])
        self.bg_image = ImageTk.PhotoImage(image)
        self.create_image(0, 0, image=self.bg_image, anchor="nw")
        self.create_text(width / 2, 18, text=self.text, fill=text_color, font=FONT_UI)


class ChromiePet:
    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.size = 104
        self.visible_edge = 34
        self.drag_start = None
        self.did_drag = False
        self.is_dragging = False
        self.docked_side = "right"
        self.hide_after_id = None
        self.animation_after_id = None
        self.avatar_image = None

        self.window = tk.Toplevel(self.root)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.attributes("-alpha", 1.0)
        try:
            self.window.attributes("-transparentcolor", THEME["pet_key"])
        except tk.TclError:
            pass

        self.canvas = tk.Canvas(
            self.window,
            width=self.size,
            height=self.size,
            bg=THEME["pet_key"],
            highlightthickness=0,
            cursor="hand2",
        )
        self.canvas.place(x=0, y=0, width=self.size, height=self.size)
        self.draw()

        for widget in (self.window, self.canvas):
            widget.bind("<ButtonPress-1>", self.start_drag)
            widget.bind("<B1-Motion>", self.drag)
            widget.bind("<ButtonRelease-1>", self.release_drag)
            widget.bind("<Enter>", self.reveal)
            widget.bind("<Leave>", self.hide_edge_later)

    def draw(self):
        c = self.canvas
        c.delete("all")
        self.avatar_image = ImageTk.PhotoImage(self.app.load_pet_avatar_image(self.size))
        c.create_image(self.size / 2, self.size / 2, image=self.avatar_image)

    def show(self):
        self.cancel_hide_timer()
        self.cancel_animation()
        self.window.deiconify()
        self.snap_to_nearest_edge(animate=False)

    def hide(self):
        self.cancel_hide_timer()
        self.cancel_animation()
        self.window.withdraw()

    def start_drag(self, event):
        self.cancel_hide_timer()
        self.cancel_animation()
        self.is_dragging = True
        self.drag_start = (event.x_root, event.y_root, self.window.winfo_x(), self.window.winfo_y())
        self.did_drag = False

    def drag(self, event):
        if not self.drag_start:
            return
        start_x, start_y, win_x, win_y = self.drag_start
        dx = event.x_root - start_x
        dy = event.y_root - start_y
        if abs(dx) + abs(dy) > 4:
            self.did_drag = True
        self.window.geometry(f"{self.size}x{self.size}+{win_x + dx}+{win_y + dy}")

    def release_drag(self, _event):
        if self.did_drag:
            self.snap_to_nearest_edge(animate=True)
            self.window.after(240, self.finish_drag)
        else:
            self.app.show_main_panel()
            self.is_dragging = False
        self.drag_start = None

    def finish_drag(self):
        self.is_dragging = False

    def snap_to_nearest_edge(self, animate=True):
        screen_w, screen_h = self.screen_bounds()
        x = self.window.winfo_x()
        y = max(0, min(self.window.winfo_y(), screen_h - self.size))
        distances = {
            "left": abs(x),
            "right": abs(screen_w - (x + self.size)),
        }
        self.docked_side = min(distances, key=distances.get)
        self.dock(y, animate=animate)

    def screen_bounds(self):
        return self.window.winfo_screenwidth(), self.window.winfo_screenheight()

    def dock(self, y=None, animate=True):
        screen_w, screen_h = self.screen_bounds()
        if y is None:
            y = self.window.winfo_y()
        y = max(0, min(y, screen_h - self.size))
        if self.docked_side == "left":
            x = -(self.size - self.visible_edge)
        else:
            x = screen_w - self.visible_edge
        if animate:
            self.animate_to(self.size, self.size, x, y, 0)
        else:
            self.apply_pet_geometry(self.size, self.size, x, y, 0)

    def reveal(self, _event=None):
        if self.is_dragging:
            return
        self.cancel_hide_timer()
        screen_w, screen_h = self.screen_bounds()
        y = max(0, min(self.window.winfo_y(), screen_h - self.size))
        if self.docked_side == "left":
            x = 0
        else:
            x = screen_w - self.size
        self.animate_to(self.size, self.size, x, y, 0)

    def hide_edge_later(self, _event=None):
        if self.is_dragging:
            return
        self.cancel_hide_timer()
        self.hide_after_id = self.window.after(450, self.hide_if_pointer_outside)

    def cancel_hide_timer(self):
        if self.hide_after_id is None:
            return
        try:
            self.window.after_cancel(self.hide_after_id)
        except tk.TclError:
            pass
        self.hide_after_id = None

    def hide_if_pointer_outside(self):
        if self.is_dragging:
            return
        self.hide_after_id = None
        pointer_x = self.window.winfo_pointerx()
        pointer_y = self.window.winfo_pointery()
        win_x = self.window.winfo_x()
        win_y = self.window.winfo_y()
        inside_x = win_x <= pointer_x < win_x + self.window.winfo_width()
        inside_y = win_y <= pointer_y < win_y + self.window.winfo_height()
        if not (inside_x and inside_y):
            self.dock()

    def cancel_animation(self):
        if self.animation_after_id is None:
            return
        try:
            self.window.after_cancel(self.animation_after_id)
        except tk.TclError:
            pass
        self.animation_after_id = None

    def apply_pet_geometry(self, width, height, x, y, canvas_x):
        width = max(1, round(width))
        height = max(1, round(height))
        x = round(x)
        y = round(y)
        canvas_x = round(canvas_x)
        self.canvas.place_configure(x=canvas_x, y=0, width=self.size, height=self.size)
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def smooth_progress(self, progress):
        return progress * progress * (3 - 2 * progress)

    def animate_to(self, target_width, target_height, target_x, target_y, target_canvas_x, duration=220):
        self.cancel_animation()
        start_width = self.window.winfo_width()
        start_height = self.window.winfo_height()
        start_x = self.window.winfo_x()
        start_y = self.window.winfo_y()
        start_canvas_x = self.canvas.winfo_x()
        frames = max(1, round(duration / 16))

        def step(index=0):
            progress = min(1, index / frames)
            eased = self.smooth_progress(progress)
            width = start_width + (target_width - start_width) * eased
            height = start_height + (target_height - start_height) * eased
            x = start_x + (target_x - start_x) * eased
            y = start_y + (target_y - start_y) * eased
            canvas_x = start_canvas_x + (target_canvas_x - start_canvas_x) * eased
            self.apply_pet_geometry(width, height, x, y, canvas_x)
            if index < frames:
                self.animation_after_id = self.window.after(16, lambda: step(index + 1))
            else:
                self.animation_after_id = None
                self.apply_pet_geometry(target_width, target_height, target_x, target_y, target_canvas_x)

        step()


class RGBApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("560x720")
        self.root.minsize(500, 520)
        self.root.configure(bg=THEME["window"])
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 1.0)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.window_icon = None
        self.header_avatar_image = None
        self.header_bg_image = None
        self.header_bg_width = None
        self.header_button_image = None
        self.header_button_images = {}
        self.header_hovered_button = None
        self.settings_visible = False
        self.config = load_config()
        self.avatar_path = self.config.get("avatar_path") if USER_AVATAR_PATH.exists() else None
        self.display_title = str(self.config.get("display_title") or DEFAULT_DISPLAY_TITLE)
        configured_theme = "gray" if self.config.get("theme") == "warm_grey" else self.config.get("theme")
        self.theme_name = configured_theme if configured_theme in THEME_PRESETS else DEFAULT_THEME_NAME
        self.theme_option_images = {}
        self.theme_option_canvases = {}
        self.apply_theme_values(self.theme_name)
        self.root.title(self.display_title)
        self.configure_style()
        self.set_window_icon()

        self.current_color = ColorInfo(0, 166, 218)
        self.analysis_source = []
        self.dominant_palette = []
        self.auxiliary_palette = []
        self.accent_palette = []
        self.preview_image = None
        self.preview_drop_hovered = False
        self.analysis_bg_image = None
        self.preview_source_image = None
        self.preview_source_name = ""
        self.status_is_error = False
        self.pet = ChromiePet(self)
        self.copy_format = tk.StringVar(value="Hex")
        self.display_title_var = tk.StringVar(value=self.display_title)
        self.outer = ttk.Frame(root)
        self.outer.pack(fill=tk.BOTH, expand=True)
        self.scroll_canvas = tk.Canvas(self.outer, highlightthickness=0, bg=THEME["window"])
        self.scrollbar = ttk.Scrollbar(self.outer, orient=tk.VERTICAL, command=self.scroll_canvas.yview, style="Chromie.Vertical.TScrollbar")
        self.scroll_canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.frame = ttk.Frame(self.scroll_canvas, padding="10")
        self.frame_window = self.scroll_canvas.create_window((0, 0), window=self.frame, anchor="nw")
        self.frame.bind("<Configure>", self.update_scroll_region)
        self.scroll_canvas.bind("<Configure>", self.resize_scroll_frame)
        self.root.bind_all("<MouseWheel>", self.on_mouse_wheel)
        self.root.bind_all("<Control-v>", self.handle_paste_shortcut)
        self.root.bind_all("<Control-V>", self.handle_paste_shortcut)

        self.build_status_section()
        self.build_settings_section(self.frame)
        self.build_palette_section(self.frame)
        self.build_preview_section(self.frame)
        self.build_color_structure_section(self.frame)
        self.build_analysis_section(self.frame)

        self.refresh_color_structure()
        self.update_current_display(self.current_color)

    def configure_style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(".", font=FONT_UI, background=THEME["window"], foreground=THEME["text"])
        style.configure("TFrame", background=THEME["window"])
        style.configure("Panel.TFrame", background=THEME["panel"])
        style.configure("TLabel", background=THEME["window"], foreground=THEME["text"], font=FONT_UI)
        style.configure("Panel.TLabel", background=THEME["panel"], foreground=THEME["text"], font=FONT_UI)
        style.configure(
            "Chromie.TCombobox",
            fieldbackground=THEME["panel"],
            background=THEME["panel_alt"],
            foreground=THEME["text"],
            arrowcolor=THEME["accent_dark"],
            bordercolor=THEME["line"],
            lightcolor=THEME["panel_alt"],
            darkcolor=THEME["line"],
            selectbackground=THEME["accent"],
            selectforeground="#FFFFFF",
            insertcolor=THEME["text"],
            font=FONT_UI,
        )
        style.map(
            "Chromie.TCombobox",
            fieldbackground=[("readonly", THEME["panel"]), ("focus", THEME["panel"])],
            background=[("active", THEME["panel_alt"]), ("pressed", THEME["panel_alt"])],
            foreground=[("readonly", THEME["text"])],
            arrowcolor=[("active", THEME["accent_dark"]), ("pressed", THEME["accent_dark"])],
        )
        style.configure(
            "Chromie.Vertical.TScrollbar",
            background=THEME["panel_alt"],
            troughcolor=THEME["window"],
            bordercolor=THEME["line"],
            arrowcolor=THEME["accent_dark"],
            lightcolor=THEME["panel_alt"],
            darkcolor=THEME["line"],
            relief=tk.FLAT,
            width=14,
        )
        style.map(
            "Chromie.Vertical.TScrollbar",
            background=[("active", THEME["accent"]), ("pressed", THEME["accent"])],
            arrowcolor=[("active", "#FFFFFF"), ("pressed", "#FFFFFF")],
        )

    def apply_theme_values(self, theme_name):
        preset = THEME_PRESETS.get(theme_name, THEME_PRESETS[DEFAULT_THEME_NAME])
        THEME.clear()
        THEME.update(preset["colors"])
        THEME.update(THEME_SHARED)

    def apply_theme(self, theme_name):
        if theme_name not in THEME_PRESETS:
            return
        self.theme_name = theme_name
        self.config["theme"] = theme_name
        try:
            save_config(self.config)
        except OSError as exc:
            self.set_status(f"配色保存失败：{exc}", is_error=True)
            return

        self.apply_theme_values(theme_name)
        self.configure_style()
        self.refresh_theme()
        self.set_status(f"已切换配色：{THEME_PRESETS[theme_name]['name']}")

    def configure_combobox_popdown(self, combo):
        try:
            popdown = combo.tk.call("ttk::combobox::PopdownWindow", combo)
            listbox = f"{popdown}.f.l"
            combo.tk.call(listbox, "configure", "-background", THEME["panel"], "-foreground", THEME["text"])
            combo.tk.call(listbox, "configure", "-selectbackground", THEME["accent"], "-selectforeground", "#FFFFFF")
        except tk.TclError:
            pass

    def refresh_theme(self):
        self.root.configure(bg=THEME["window"])
        self.scroll_canvas.configure(bg=THEME["window"])
        if hasattr(self, "scrollbar"):
            self.scrollbar.configure(style="Chromie.Vertical.TScrollbar")
        if hasattr(self, "copy_format_combo"):
            self.copy_format_combo.configure(style="Chromie.TCombobox")
            self.configure_combobox_popdown(self.copy_format_combo)
        self.refresh_widget_theme(self.root)
        self.header_bg_image = None
        self.header_bg_width = None
        self.header_button_images.clear()
        self.redraw_header()
        self.refresh_theme_options()
        self.refresh_palette()
        self.refresh_color_structure()
        self.refresh_preview()
        self.refresh_analysis()

    def refresh_widget_theme(self, widget):
        if isinstance(widget, RoundedPanel):
            widget.configure(bg=THEME["window"])
            widget.body.configure(style="Panel.TFrame")
            widget.bg_image = None
            widget.redraw()
        elif isinstance(widget, RoundedButton):
            widget.configure(bg=THEME["window"] if widget.variant == "pet" else THEME["panel"])
            widget.redraw()
        elif isinstance(widget, tk.Canvas):
            try:
                widget.configure(bg=THEME["panel"] if widget is getattr(self, "preview_canvas", None) or widget is getattr(self, "value_canvas", None) else THEME["window"])
            except tk.TclError:
                pass
        for child in widget.winfo_children():
            self.refresh_widget_theme(child)

    def set_window_icon(self):
        self.window_icon = ImageTk.PhotoImage(load_chromie_image(64))
        self.root.iconphoto(True, self.window_icon)

    def load_avatar_image(self, size, hard_alpha=False):
        return load_chromie_image(size, hard_alpha=hard_alpha, source_path=self.avatar_path)

    def load_pet_avatar_image(self, size):
        return load_pet_avatar_image(size, source_path=self.avatar_path)

    def update_scroll_region(self, event=None):
        self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))

    def resize_scroll_frame(self, event):
        self.scroll_canvas.itemconfigure(self.frame_window, width=event.width)

    def on_mouse_wheel(self, event):
        self.scroll_canvas.yview_scroll(int(-event.delta / 120), "units")

    def build_status_section(self):
        self.status_var = tk.StringVar(value="就绪")
        header = tk.Canvas(self.frame, height=132, bg=THEME["window"], highlightthickness=0)
        header.pack(fill=tk.X, pady=(0, 8))
        header.bind("<Configure>", self.redraw_header)
        self.header_canvas = header
        self.header_avatar_image = ImageTk.PhotoImage(self.load_avatar_image(106))
        for tag, command in (("settings_button", self.toggle_settings), ("hide_button", self.hide_to_pet)):
            header.tag_bind(tag, "<Enter>", lambda _event, name=tag: self.enter_header_button(name))
            header.tag_bind(tag, "<Leave>", lambda _event: self.leave_header_button())
            header.tag_bind(tag, "<Button-1>", lambda _event, action=command: action())
        self.redraw_header()

    def redraw_header(self, _event=None):
        if not hasattr(self, "header_canvas"):
            return
        canvas = self.header_canvas
        canvas.delete("header_art")
        width = max(canvas.winfo_width(), 1)
        panel_y = 26
        panel_h = 92
        if self.header_bg_image is None or self.header_bg_width != width:
            header_bg = make_rounded_image(
                width,
                panel_h,
                23,
                THEME["panel"],
                THEME["window"],
                outline=THEME["soft_line"],
                shadow=THEME["panel_shadow"],
            )
            self.header_bg_image = ImageTk.PhotoImage(header_bg)
            self.header_bg_width = width
        canvas.create_image(0, panel_y, image=self.header_bg_image, anchor="nw", tags=("header_art",))
        canvas.create_image(72, 72, image=self.header_avatar_image, tags=("header_art",))
        button_x = max(42, width - 50)
        text_max_width = max(40, button_x - 134 - 48)
        title_text = fit_text_to_width(self.display_title, FONT_TITLE, text_max_width)
        canvas.create_text(134, 54, text=title_text, anchor="w", fill=THEME["text"], font=FONT_TITLE, tags=("header_art",))
        status_color = THEME["danger"] if getattr(self, "status_is_error", False) else THEME["muted"]
        status_text = fit_text_to_width(self.status_var.get(), FONT_SUBTITLE, text_max_width)
        canvas.create_text(134, 82, text=status_text, anchor="w", fill=status_color, font=FONT_SUBTITLE, tags=("header_art",))
        for tag, icon, center_y in (("settings_button", "settings", 54), ("hide_button", "collapse", 94)):
            button_fill = self.header_button_fill(tag)
            self.header_button_images[tag] = ImageTk.PhotoImage(
                make_transparent_pill(34, 34, 9, button_fill, shadow=self.theme_shadow_rgba())
            )
            canvas.create_image(button_x, center_y, image=self.header_button_images[tag], tags=("header_art", tag))
            self.draw_header_icon(canvas, button_x, center_y, icon, tag)

    def header_button_fill(self, tag):
        return THEME["accent"] if self.header_hovered_button == tag else THEME["panel_alt"]

    def theme_shadow_rgba(self, alpha=80):
        color = THEME["panel_shadow"].lstrip("#")
        return (int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16), alpha)

    def draw_header_icon(self, canvas, cx, cy, icon, tag):
        color = "#FFFFFF" if self.header_hovered_button == tag else THEME["accent_dark"]
        if icon == "settings":
            points = []
            radius = 8
            for index in range(6):
                angle = math.radians(30 + index * 60)
                points.extend((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
            canvas.create_polygon(points, outline=color, fill="", width=2, tags=("header_art", tag))
            canvas.create_oval(cx - 2, cy - 2, cx + 2, cy + 2, outline=color, width=2, tags=("header_art", tag))
            return

        canvas.create_line(cx - 7, cy - 5, cx + 7, cy - 5, cx + 7, cy + 5, fill=color, width=2, tags=("header_art", tag))
        canvas.create_line(cx - 7, cy - 5, cx - 7, cy - 1, fill=color, width=2, tags=("header_art", tag))
        canvas.create_line(cx - 3, cy - 1, cx + 3, cy - 1, cx + 3, cy + 7, cx - 7, cy + 7, cx - 7, cy + 3, fill=color, width=2, tags=("header_art", tag))

    def enter_header_button(self, button_name):
        if self.header_hovered_button == button_name:
            return
        self.header_hovered_button = button_name
        self.header_canvas.configure(cursor="hand2")
        self.redraw_header()

    def leave_header_button(self, _event=None):
        if not self.header_hovered_button:
            return
        self.header_hovered_button = None
        self.header_canvas.configure(cursor="")
        self.redraw_header()

    def build_settings_section(self, parent):
        self.settings_panel = RoundedPanel(parent, "设置", min_height=120)

        title_row = ttk.Frame(self.settings_panel.body, style="Panel.TFrame", padding=(0, 3, 0, 7))
        title_row.pack(fill=tk.X)
        ttk.Label(title_row, text="标题", style="Panel.TLabel", foreground=THEME["muted"], font=FONT_SUBTITLE).pack(side=tk.LEFT)
        self.display_title_entry = ttk.Entry(title_row, textvariable=self.display_title_var, font=FONT_UI)
        self.display_title_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(12, 8))
        self.display_title_entry.bind("<Return>", lambda _event: self.save_display_title())
        RoundedButton(title_row, text="保存", variant="primary", command=self.save_display_title, min_width=72).pack(side=tk.LEFT, padx=(0, 8))
        RoundedButton(title_row, text="默认", variant="ghost", command=self.reset_display_title, min_width=72).pack(side=tk.LEFT)

        theme_row = ttk.Frame(self.settings_panel.body, style="Panel.TFrame", padding=(0, 3, 0, 8))
        theme_row.pack(fill=tk.X)
        ttk.Label(theme_row, text="配色", style="Panel.TLabel", foreground=THEME["muted"], font=FONT_SUBTITLE).pack(side=tk.LEFT, anchor="n", pady=(8, 0))
        self.theme_options_frame = ttk.Frame(theme_row, style="Panel.TFrame")
        self.theme_options_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(12, 0))
        self.build_theme_options()

        avatar_row = ttk.Frame(self.settings_panel.body, style="Panel.TFrame", padding=(0, 3, 0, 4))
        avatar_row.pack(fill=tk.X)
        ttk.Label(avatar_row, text="头像", style="Panel.TLabel", foreground=THEME["muted"], font=FONT_SUBTITLE).pack(side=tk.LEFT)
        RoundedButton(avatar_row, text="上传 PNG", variant="primary", command=self.upload_avatar, min_width=96).pack(side=tk.LEFT, padx=(12, 8))
        RoundedButton(avatar_row, text="恢复默认", variant="ghost", command=self.reset_avatar, min_width=96).pack(side=tk.LEFT)

        self.avatar_status_var = tk.StringVar()
        ttk.Label(
            self.settings_panel.body,
            textvariable=self.avatar_status_var,
            style="Panel.TLabel",
            foreground=THEME["muted"],
            font=FONT_MONO_SMALL,
        ).pack(anchor="w", pady=(4, 0))
        ttk.Label(
            self.settings_panel.body,
            text=f"保存位置：{CONFIG_DIR}",
            style="Panel.TLabel",
            foreground=THEME["muted"],
            font=FONT_MONO_SMALL,
        ).pack(anchor="w", pady=(3, 0))
        self.refresh_avatar_status()

    def build_theme_options(self):
        for child in self.theme_options_frame.winfo_children():
            child.destroy()
        self.theme_option_canvases.clear()
        for index, theme_name in enumerate(THEME_PRESETS):
            canvas = tk.Canvas(
                self.theme_options_frame,
                width=92,
                height=42,
                bg=THEME["panel"],
                highlightthickness=0,
                cursor="hand2",
            )
            canvas.grid(row=index // 4, column=index % 4, padx=(0, 8), pady=(0, 8), sticky="w")
            canvas.bind("<Button-1>", lambda _event, name=theme_name: self.apply_theme(name))
            self.theme_option_canvases[theme_name] = canvas
        self.refresh_theme_options()

    def make_theme_option_image(self, theme_name, width=92, height=42):
        preset = THEME_PRESETS[theme_name]
        colors = preset["colors"]
        selected = theme_name == self.theme_name
        outline = THEME["accent"] if selected else THEME["line"]
        image = make_rounded_image(width, height, 16, THEME["panel_alt"], THEME["panel"], outline=outline)
        image = image.convert("RGBA")
        draw = ImageDraw.Draw(image)
        swatch_colors = [colors["window"], colors["panel"], colors["accent"]]
        for index, color in enumerate(swatch_colors):
            x1 = 10 + index * 16
            draw.rounded_rectangle((x1, 8, x1 + 12, 20), radius=3, fill=color, outline=THEME["line"])
        return image

    def refresh_theme_options(self):
        if not hasattr(self, "theme_option_canvases"):
            return
        self.theme_option_images.clear()
        for theme_name, canvas in self.theme_option_canvases.items():
            canvas.configure(bg=THEME["panel"])
            canvas.delete("all")
            image = self.make_theme_option_image(theme_name)
            self.theme_option_images[theme_name] = ImageTk.PhotoImage(image)
            canvas.create_image(0, 0, image=self.theme_option_images[theme_name], anchor="nw")
            preset = THEME_PRESETS[theme_name]
            canvas.create_text(12, 29, text=preset["label"], fill=THEME["accent_dark"], font=FONT_UI, anchor="w")
            canvas.create_text(34, 29, text=preset["name"].split()[0], fill=THEME["text"], font=FONT_MONO_SMALL, anchor="w")

    def save_display_title(self):
        title = self.display_title_var.get().strip() or DEFAULT_DISPLAY_TITLE
        self.display_title = title
        self.display_title_var.set(title)
        self.config["display_title"] = title
        try:
            save_config(self.config)
        except OSError as exc:
            self.set_status(f"标题保存失败：{exc}", is_error=True)
            return
        self.root.title(title)
        self.redraw_header()
        self.set_status("已更新标题。")

    def reset_display_title(self):
        self.display_title = DEFAULT_DISPLAY_TITLE
        self.display_title_var.set(DEFAULT_DISPLAY_TITLE)
        self.config.pop("display_title", None)
        try:
            save_config(self.config)
        except OSError as exc:
            self.set_status(f"标题恢复失败：{exc}", is_error=True)
            return
        self.root.title(APP_TITLE)
        self.redraw_header()
        self.set_status("已恢复默认标题。")

    def toggle_settings(self):
        self.settings_visible = not self.settings_visible
        if self.settings_visible:
            pack_options = {"fill": tk.X, "pady": (0, 8)}
            if hasattr(self, "palette_box"):
                pack_options["before"] = self.palette_box
            self.settings_panel.pack(**pack_options)
        else:
            self.settings_panel.pack_forget()
        self.update_scroll_region()

    def refresh_avatar_status(self):
        if not hasattr(self, "avatar_status_var"):
            return
        if self.avatar_path and Path(self.avatar_path).exists():
            self.avatar_status_var.set("当前头像：自定义 PNG")
        else:
            self.avatar_status_var.set("当前头像：默认 Chromie")

    def upload_avatar(self):
        file_path = filedialog.askopenfilename(
            title="选择正方形 PNG 头像",
            filetypes=[("PNG 图片", "*.png"), ("所有文件", "*.*")],
        )
        if not file_path:
            return

        path = Path(file_path)
        if path.suffix.lower() != ".png":
            self.set_status("头像必须是 PNG 文件。", is_error=True)
            return

        try:
            with Image.open(path) as image:
                if image.width != image.height:
                    self.set_status("头像必须是正方形 PNG。", is_error=True)
                    return
                if image.width * image.height > MAX_AVATAR_PIXELS:
                    self.set_status("头像尺寸过大，请使用不超过 4MP 的 PNG。", is_error=True)
                    return
                image.verify()
        except PIL_IMAGE_ERRORS as exc:
            self.set_status(f"头像读取失败：{exc}", is_error=True)
            return

        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copyfile(path, USER_AVATAR_PATH)
            self.config["avatar_path"] = str(USER_AVATAR_PATH)
            save_config(self.config)
        except OSError as exc:
            self.set_status(f"头像保存失败：{exc}", is_error=True)
            return

        self.avatar_path = str(USER_AVATAR_PATH)
        self.refresh_avatar_images()
        self.refresh_avatar_status()
        self.set_status("已更新自定义头像。")

    def reset_avatar(self):
        try:
            if USER_AVATAR_PATH.exists():
                USER_AVATAR_PATH.unlink()
            self.config.pop("avatar_path", None)
            save_config(self.config)
        except OSError as exc:
            self.set_status(f"恢复默认头像失败：{exc}", is_error=True)
            return

        self.avatar_path = None
        self.refresh_avatar_images()
        self.refresh_avatar_status()
        self.set_status("已恢复默认头像。")

    def refresh_avatar_images(self):
        self.header_avatar_image = ImageTk.PhotoImage(self.load_avatar_image(106))
        self.redraw_header()
        if hasattr(self, "pet"):
            self.pet.draw()

    def build_palette_section(self, parent):
        palette_box = RoundedPanel(parent, "采样色板", min_height=100, fixed_height=True)
        self.palette_box = palette_box
        palette_box.pack(fill=tk.X, pady=(0, 8))

        toolbar = ttk.Frame(palette_box.body, style="Panel.TFrame", padding=(0, 1, 0, 2))
        toolbar.pack(fill=tk.X)

        self.palette_frame = ttk.Frame(toolbar, style="Panel.TFrame")
        self.palette_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        format_frame = ttk.Frame(toolbar, style="Panel.TFrame")
        format_frame.pack(side=tk.RIGHT)
        ttk.Label(format_frame, text="格式", style="Panel.TLabel").pack(side=tk.LEFT)
        self.copy_format_combo = ttk.Combobox(
            format_frame,
            textvariable=self.copy_format,
            values=list(COPY_FORMATS.keys()),
            state="readonly",
            width=10,
            font=FONT_UI,
            style="Chromie.TCombobox",
        )
        self.copy_format_combo.pack(side=tk.LEFT, padx=(8, 0))
        self.copy_format_combo.bind("<<ComboboxSelected>>", lambda event: self.refresh_palette())
        self.configure_combobox_popdown(self.copy_format_combo)

    def build_color_structure_section(self, parent):
        structure = RoundedPanel(parent, "色彩结构", min_height=170)
        structure.pack(fill=tk.X, pady=(0, 8))

        self.dominant_frame = ttk.Frame(structure.body, style="Panel.TFrame", padding=(0, 4, 0, 4))
        self.dominant_frame.pack(fill=tk.X)
        self.auxiliary_frame = ttk.Frame(structure.body, style="Panel.TFrame", padding=(0, 4, 0, 4))
        self.auxiliary_frame.pack(fill=tk.X)
        self.accent_frame = ttk.Frame(structure.body, style="Panel.TFrame", padding=(0, 4, 0, 2))
        self.accent_frame.pack(fill=tk.X)

    def build_preview_section(self, parent):
        preview_box = RoundedPanel(parent, "预览图片", min_height=120)
        preview_box.pack(fill=tk.X, pady=(0, 8))

        self.preview_canvas = tk.Canvas(
            preview_box.body,
            height=PREVIEW_EMPTY_HEIGHT,
            bg=THEME["panel"],
            highlightthickness=0,
            cursor="hand2",
        )
        self.preview_canvas.pack(fill=tk.X, pady=(6, 6))
        self.preview_canvas.bind("<Configure>", lambda event: self.refresh_preview())
        self.preview_canvas.bind("<Button-1>", lambda _event: self.open_image())
        self.preview_canvas.bind("<Enter>", lambda _event: self.set_preview_hover(True))
        self.preview_canvas.bind("<Leave>", lambda _event: self.set_preview_hover(False))
        self.preview_canvas.drop_target_register(DND_FILES)
        self.preview_canvas.dnd_bind("<<DropEnter>>", self.enter_preview_drop)
        self.preview_canvas.dnd_bind("<<DropLeave>>", self.leave_preview_drop)
        self.preview_canvas.dnd_bind("<<Drop>>", self.drop_preview_image)

    def build_analysis_section(self, parent):
        analysis = RoundedPanel(parent, "明度结构", min_height=280)
        analysis.pack(fill=tk.X)

        self.value_canvas = tk.Canvas(analysis.body, height=230, bg=THEME["panel"], highlightthickness=0)
        self.value_canvas.pack(fill=tk.X, pady=(2, 6))
        self.value_canvas.pack_propagate(False)
        self.value_canvas.bind("<Configure>", lambda event: (self.refresh_preview(), self.refresh_analysis()))

    def set_status(self, message, is_error=False):
        self.status_var.set(message)
        self.status_is_error = is_error
        self.redraw_header()

    def hide_to_pet(self):
        self.root.withdraw()
        self.pet.show()

    def show_main_panel(self):
        self.pet.hide()
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)

    def update_ui(self, color):
        self.update_current_display(color)
        self.refresh_analysis()

    def update_current_display(self, color):
        self.current_color = color
        if hasattr(self, "palette_frame"):
            self.refresh_palette()

    def select_color(self, color):
        self.update_current_display(color)
        self.set_status(f"当前颜色：{COPY_FORMATS[self.copy_format.get()](color)}")

    def refresh_palette(self):
        for child in self.palette_frame.winfo_children():
            child.destroy()

        self.render_palette_item(self.palette_frame, self.current_color, row_index=0, column=0, is_current=True)

        self.palette_frame.columnconfigure(0, weight=1)

    def render_palette_item(self, parent, color, row_index, column, is_current=False):
        frame = ttk.Frame(parent, style="Panel.TFrame")
        frame.grid(row=row_index, column=column, sticky="w", padx=(0, 8), pady=0)
        value_column = 1
        frame.columnconfigure(value_column, weight=1)

        swatch = tk.Canvas(
            frame,
            width=42,
            height=34,
            bg=color.hex_text,
            highlightthickness=3,
            highlightbackground=THEME["swatch_border"],
            highlightcolor=THEME["swatch_border"],
            cursor="hand2",
        )
        swatch.grid(row=0, column=0, rowspan=2, padx=(0, 10))
        command = self.copy_color if is_current else self.update_current_display
        swatch.bind("<Button-1>", lambda event, item=color, action=command: action(item))

        text = COPY_FORMATS[self.copy_format.get()](color)
        hint_label = ttk.Label(frame, text="点击复制", style="Panel.TLabel", foreground=THEME["muted"], font=FONT_MONO_SMALL, cursor="hand2")
        hint_label.grid(row=0, column=value_column, sticky="w")
        value_label = ttk.Label(frame, text=text, style="Panel.TLabel", font=FONT_MONO, cursor="hand2")
        value_label.grid(row=1, column=value_column, sticky="w")
        for label in (hint_label, value_label):
            label.bind("<Button-1>", lambda event, item=color, action=command: action(item))
        self.bind_color_hover(swatch, hint_label, value_label)

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

        ttk.Label(parent, text=title_text, style="Panel.TLabel", foreground=THEME["muted"], font=FONT_SUBTITLE).grid(row=0, column=0, columnspan=4, sticky="w", pady=(1, 5))
        if not stats:
            ttk.Label(parent, text="暂无数据", style="Panel.TLabel", foreground=THEME["muted"], font=FONT_SUBTITLE).grid(row=1, column=0, sticky="w")
            return

        for idx, stat in enumerate(stats):
            row_idx = idx + 1
            swatch = tk.Canvas(
                parent,
                width=34,
                height=24,
                bg=stat.color.hex_text,
                highlightthickness=3,
                highlightbackground=THEME["swatch_border"],
                highlightcolor=THEME["swatch_border"],
                cursor="hand2",
            )
            swatch.grid(row=row_idx, column=0, padx=(0, 8), pady=3, sticky="w")
            swatch.bind("<Button-1>", lambda event, item=stat.color: self.select_color(item))

            label = ttk.Label(parent, text=stat.color.hex_text, style="Panel.TLabel", font=FONT_MONO, cursor="hand2")
            label.grid(row=row_idx, column=1, sticky="w", padx=(0, 8))
            label.bind("<Button-1>", lambda event, item=stat.color: self.select_color(item))
            self.bind_color_hover(swatch, label)

            bar = tk.Canvas(parent, height=16, bg=THEME["panel"], highlightthickness=0)
            bar.grid(row=row_idx, column=2, sticky="ew", padx=(0, 8))
            bar.bind("<Configure>", lambda event, item=stat, max_value=max_percent: self.draw_percent_bar(event.widget, item, max_value))

            percent_label = ttk.Label(parent, text=self.format_percent(stat.percent), style="Panel.TLabel", font=FONT_MONO)
            percent_label.grid(row=row_idx, column=3, sticky="e")

        parent.columnconfigure(2, weight=1)

    def bind_color_hover(self, swatch, *labels):
        def set_hover(_event):
            swatch.config(highlightbackground=THEME["accent"], highlightcolor=THEME["accent"])

        def clear_hover(_event):
            swatch.config(highlightbackground=THEME["swatch_border"], highlightcolor=THEME["swatch_border"])

        for widget in (swatch, *labels):
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
        canvas.create_rectangle(1, 5, bar_width + 1, height - 3, fill="#8A7D70", outline="")
        canvas.create_rectangle(0, 4, bar_width, height - 4, fill=stat.color.hex_text, outline="")

    def copy_to_clipboard(self, value):
        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        self.set_status(f"已复制：{value}")

    def copy_color(self, color):
        self.copy_to_clipboard(COPY_FORMATS[self.copy_format.get()](color))

    def handle_paste_shortcut(self, _event=None):
        if self.root.state() == "withdrawn":
            return "break"
        self.paste_from_clipboard()
        return "break"

    def set_preview_hover(self, hovered):
        if self.preview_drop_hovered == hovered:
            return
        self.preview_drop_hovered = hovered
        self.refresh_preview()

    def enter_preview_drop(self, _event=None):
        self.set_preview_hover(True)
        return "copy"

    def leave_preview_drop(self, _event=None):
        self.set_preview_hover(False)
        return "copy"

    def drop_preview_image(self, event):
        self.set_preview_hover(False)
        paths = self.root.tk.splitlist(event.data)
        if not paths:
            self.set_status("没有识别到拖入的文件。", is_error=True)
            return "break"
        self.open_image_file(paths[0])
        return "break"

    def paste_from_clipboard(self):
        try:
            image = ImageGrab.grabclipboard()
        except Exception as exc:
            self.set_status(f"读取剪贴板失败：{exc}", is_error=True)
            return

        if image is None:
            self.set_status("剪贴板中没有图片，请先复制图片后再粘贴。", is_error=True)
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

        self.open_image_file(file_path)

    def open_image_file(self, file_path):
        path = Path(file_path)
        if not path.is_file():
            self.set_status(f"不是可读取的图片文件：{path}", is_error=True)
            return

        try:
            image = Image.open(path)
        except PIL_IMAGE_ERRORS as exc:
            self.set_status(f"图片打开失败：{exc}", is_error=True)
            return

        self.apply_image_analysis(image, path.name)

    def apply_image_analysis(self, image, source_name):
        try:
            colors = image_to_colors(image)
            dominant_palette, auxiliary_palette, accent_palette = extract_color_structure(colors)
            preview_image = make_preview_source_image(image)
        except ImageAnalysisError as exc:
            self.set_status(f"图片分析失败：{exc}", is_error=True)
            return

        if not dominant_palette:
            self.set_status("没有可分析的像素。", is_error=True)
            return

        self.dominant_palette = dominant_palette
        self.auxiliary_palette = auxiliary_palette
        self.accent_palette = accent_palette
        self.analysis_source = colors
        self.update_ui(self.dominant_palette[0].color)
        self.refresh_color_structure()
        self.refresh_analysis()
        self.update_preview(preview_image, source_name)
        self.set_status(f"已分析：{source_name}")

    def update_preview(self, image, source_name):
        self.preview_source_image = image
        self.preview_source_name = source_name
        self.refresh_preview()

    def refresh_preview(self):
        if not hasattr(self, "preview_canvas"):
            return

        canvas = self.preview_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 1)
        height = max(canvas.winfo_height(), 1)
        if width <= 1 or height <= 1:
            return

        if not self.preview_source_image:
            if canvas.winfo_height() != PREVIEW_EMPTY_HEIGHT:
                canvas.configure(height=PREVIEW_EMPTY_HEIGHT)
                return
            self.draw_preview_empty_state(canvas, width, height)
            return

        name_area_height = PREVIEW_NAME_HEIGHT
        available_width = max(1, width - 24)
        source_width, source_height = self.preview_source_image.size
        width_scale = available_width / source_width
        target_height = max(1, round(source_height * width_scale))
        if target_height > PREVIEW_MAX_IMAGE_HEIGHT:
            target_height = PREVIEW_MAX_IMAGE_HEIGHT
            scale = target_height / source_height
        else:
            scale = width_scale
        target_width = max(1, round(source_width * scale))
        desired_height = target_height + name_area_height + 12
        if abs(height - desired_height) > 1:
            canvas.configure(height=desired_height)
            return
        preview = self.preview_source_image.resize((target_width, target_height), Image.Resampling.LANCZOS)
        preview = round_image_corners(preview, 30)
        self.preview_image = ImageTk.PhotoImage(preview)
        image_y = 4
        canvas.create_image(width / 2, image_y, image=self.preview_image, anchor="n")
        canvas.create_text(
            width / 2,
            height - 14,
            text=fit_text_to_width(self.preview_source_name, FONT_UI, width - 24),
            fill=THEME["text"],
            font=FONT_UI,
        )

    def draw_preview_empty_state(self, canvas, width, height):
        outline = THEME["accent"] if self.preview_drop_hovered else THEME["line"]
        fill = THEME["panel_alt"] if self.preview_drop_hovered else THEME["panel"]
        bg = make_rounded_image(width, height, 24, fill, THEME["panel"], outline=outline)
        self.preview_image = ImageTk.PhotoImage(bg)
        canvas.create_image(0, 0, image=self.preview_image, anchor="nw")

        inset = 12
        outline_image = make_dashed_rounded_outline(
            width - inset * 2,
            height - inset * 2,
            18,
            outline,
            (0, 0, 0, 0),
        )
        self.preview_outline_image = ImageTk.PhotoImage(outline_image)
        canvas.create_image(inset, inset, image=self.preview_outline_image, anchor="nw")
        center_x = width / 2
        icon_y = height / 2 - 52
        canvas.create_rectangle(center_x - 13, icon_y - 14, center_x + 7, icon_y + 13, fill=THEME["muted"], outline="")
        canvas.create_polygon(
            center_x + 7,
            icon_y + 2,
            center_x + 17,
            icon_y + 2,
            center_x + 7,
            icon_y + 12,
            fill=THEME["panel"],
            outline=THEME["muted"],
        )
        canvas.create_text(
            center_x,
            height / 2,
            text="拖拽图片到这里",
            fill=THEME["text"],
            font=FONT_SUBTITLE,
        )
        canvas.create_text(
            center_x,
            height / 2 + 32,
            text="点击选择文件，或 Ctrl+V 粘贴截图",
            fill=THEME["accent_dark"],
            font=FONT_UI,
        )
        canvas.create_text(
            center_x,
            height / 2 + 62,
            text="PNG / JPG / JPEG / BMP / WEBP",
            fill=THEME["muted"],
            font=FONT_MONO_SMALL,
        )

    def refresh_analysis(self):
        source = self.analysis_source or [self.current_color]
        if not hasattr(self, "value_canvas"):
            return

        canvas = self.value_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 1)
        height = max(canvas.winfo_height(), 230)
        chart_bg = make_rounded_image(width, height, 20, THEME["chart"], THEME["panel"], outline=THEME["chart_line"])
        self.analysis_bg_image = ImageTk.PhotoImage(chart_bg)
        canvas.create_image(0, 0, image=self.analysis_bg_image, anchor="nw")
        margin_x = 28
        top = 16
        step_h = 32
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
            canvas.create_text((x1 + x2) / 2, top + step_h / 2, text=str(value), fill=label_color, font=FONT_MONO)

        bins = value_distribution(source)
        total = sum(bins)
        chart_top = top + step_h + 30
        chart_bottom = height - 46
        chart_h = max(60, chart_bottom - chart_top)
        max_count = max(bins) if bins else 0

        canvas.create_line(margin_x, chart_bottom, width - margin_x, chart_bottom, fill=THEME["chart_line"])
        if not total:
            canvas.create_text(width / 2, chart_top + chart_h / 2, text="暂无明度数据", fill="#CCCCCC", font=FONT_UI)
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
                canvas.create_text((x1 + x2) / 2, y1 - 9, text=f"{percent:.0f}%", fill="#DDDDDD", font=FONT_MONO_SMALL)
            canvas.create_text((x1 + x2) / 2, chart_bottom + 16, text=str(value), fill="#BBBBBB", font=FONT_MONO_SMALL)

    def close(self):
        if hasattr(self, "pet"):
            self.pet.window.destroy()
        self.root.destroy()


if __name__ == "__main__":
    enable_dpi_awareness()
    root = create_tk_root()
    app = RGBApp(root)
    root.mainloop()
