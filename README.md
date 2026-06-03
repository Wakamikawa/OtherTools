# OtherTools

独立小工具集合。目前包含 Windows 图片色彩分析工具 `colortool.py`。

## 功能

- 导入或粘贴图片，自动提取图片色彩结构。
- 按绘画语义区分主色调、辅色调和点缀色。
- 主色调和辅色调会归并相近颜色，减少重复色。
- 点缀色只保留小面积且视觉跳出的颜色，允许没有点缀色。
- 显示色块、Hex 色值、占比条和明度结构。
- 支持复制当前色值和添加采样色板。

## 运行环境

- Windows
- Python 3.9 或更高版本

## 安装依赖

```powershell
python -m pip install -r requirements.txt
```

## 启动

```powershell
python colortool.py
```

如果启动时提示缺少依赖，请先运行安装命令。

## 打包建议

建议在干净虚拟环境中只安装 `requirements.txt` 和打包工具，避免把无关依赖打入 exe。

PyInstaller 示例：

```powershell
pyinstaller --onefile --windowed --name colortool colortool.py
```
