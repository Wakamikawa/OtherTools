# OtherTools

独立小工具集合。目前包含 Windows 图片色彩分析工具 `colortool.py`，已打包产物位于 `release/Chromie.exe`。

## Chromie 功能

- 支持点击、拖拽或 `Ctrl+V` 粘贴图片进行分析。
- 自动提取图片色彩结构，区分主色调、辅色调和点缀色。
- 显示当前采样色、色彩结构、图片预览和明度结构。
- 点击采样色板可按当前格式复制颜色值。
- 支持 Hex、RGB、HSV、RGB 0-1 等复制格式。
- 支持收纳为桌面边缘悬浮球。
- 支持设置自定义标题。
- 支持上传正方形透明 PNG 替换标题头像和悬浮球头像。
- 支持 8 套低饱和配色主题：赤、橙、黄、绿、青、蓝、紫、灰。

## 配置位置

用户设置保存在 Windows 用户配置目录：

```text
%APPDATA%\Chromie
```

当前包含：

- `config.json`：标题、配色等设置。
- `avatar.png`：用户上传的自定义头像。

## 运行源码

要求：

- Windows
- Python 3.9 或更高版本

安装依赖：

```powershell
python -m pip install -r requirements.txt
```

启动：

```powershell
python colortool.py
```

## 打包

建议使用干净虚拟环境，避免把旧依赖打进 exe。

```powershell
python -m venv .build-venv
.build-venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.build-venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller
.build-venv\Scripts\pyinstaller.exe --noconfirm --clean --onefile --windowed --name Chromie --icon "assets\chromie.ico" --add-data "assets\chromie.png;assets" --distpath release --workpath build --specpath build colortool.py
```

当前已生成：

```text
release\Chromie.exe
```
