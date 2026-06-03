# Handoff: 色彩结构分析工具更新

**时间:** 2026-06-04 01:00  
**主文件:** `colortool.py`  
**测试:** `tests/test_color_structure.py`

## 本次更新

- 用新版图片色彩结构分析工具完整替换旧版 `colortool.py`。
- 色彩结构从旧的“主色调 / 强调色”改为“主色调 / 辅色调 / 点缀色”。
- 主色调和辅色调使用色调族归并，减少相近颜色重复显示。
- 点缀色只从主色和辅色都解释不了的小面积跳出色中选择，最多 3 个，可为空。
- 增加色域补漏逻辑，避免蓝天、绿色植被、橙色小点缀等视觉重要颜色被漏掉。
- 复制色值改用 Tk 自带剪贴板，移除 `pyperclip` 依赖。
- 依赖精简到仅 `Pillow>=10`。

## 算法概览

1. 将图片像素采样后做 LAB 感知聚类，生成候选颜色。
2. 将相近候选合并成色调族。
3. 从最大色调族开始扩展相近颜色，形成主色调。
4. 从剩余色调族中选择辅色核心并扩展相近颜色，形成辅色调。
5. 对未解释的大色域做辅色补漏。
6. 从剩余色调族中选择小面积、高显著性的点缀色。

## 验证

已执行：

```powershell
python -m py_compile colortool.py tests/conftest.py tests/test_color_structure.py
```

并直接执行 `tests/test_color_structure.py` 中的行为测试函数，覆盖：

- 小面积暖色进入点缀色，不进入主色/辅色。
- 接近主色的小色块不进入点缀色。
- 大面积红色从主色转入辅色。
- 蓝天/绿色植被可补入辅色。
- 小面积橙色细节可补入点缀色。

## 打包建议

在干净虚拟环境中只安装：

```powershell
python -m pip install -r requirements.txt pyinstaller
```

推荐打包命令：

```powershell
pyinstaller --onefile --windowed --name colortool colortool.py
```
