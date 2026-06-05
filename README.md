# OtherTools

独立小工具集合。目前包含 Windows 图片色彩分析工具 `colortool.py`，已打包产物位于 `release/Chromie.exe`。

## 功能

- 导入或粘贴图片，自动提取图片色彩结构。
- 按绘画语义区分主色调、辅色调和点缀色。
- 主色调和辅色调会归并相近颜色，减少重复色。
- 点缀色只保留小面积且视觉跳出的颜色，允许没有点缀色。
- 显示色块、Hex 色值、占比条、图片预览和明度结构。
- 支持复制当前颜色值。
- 支持收纳为桌面边缘小窗。

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
.build-venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel Pillow pyinstaller
.build-venv\Scripts\pyinstaller.exe --noconfirm --clean --onefile --windowed --name Chromie --icon "assets\chromie.ico" --add-data "assets\chromie.png;assets" --distpath release --workpath build --specpath build colortool.py
```

当前已生成：

```text
release\Chromie.exe
```