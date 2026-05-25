# OtherTools

一些独立的小工具集合。目前包含 Windows 桌面取色工具 `colortool.py`。

## 功能

- 输入 RGB 数值并查看饱和度、明度和 Hex 色值。
- 点击按钮后从屏幕任意位置吸取颜色。
- 点击 Hex 输入框可复制色值到剪贴板。
- 保留最近 5 个颜色记录，点击色块可快速切换。

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

首次运行时，脚本也会尝试自动安装缺失依赖。

## 用 GitHub Desktop 管理

1. 打开 GitHub Desktop。
2. 选择 `File` -> `Add local repository...`。
3. 选择本目录：`D:\Asset\OtherTools`。
4. 如果提示尚未创建 Git 仓库，选择创建仓库。
5. 检查变更后提交，再发布到 GitHub。
