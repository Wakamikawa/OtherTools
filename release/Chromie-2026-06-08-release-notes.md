# Chromie Release Notes - 2026-06-08

## 发布产物

- 文件：`release/Chromie.exe`
- 大小：`19,476,337` bytes
- SHA256：`E029F477D28E6D8DBFAF52C1D48D8F78012AC25BB0AA8DBA206C243414A6DC78`

## 本次更新

- 在“明度结构”模块上方新增去色预览图。
- 导入、拖拽或 `Ctrl+V` 粘贴图片后，会自动生成黑白预览。
- 去色图位于明度结构深色圆角图表外部，显示在图表上方。
- 去色图使用和上方“预览图片”一致的缩放规则：
  - 跟随窗口宽度缩放；
  - 保持原图比例；
  - 图片过高时按最大高度等比缩小；
  - 不裁切图片内容。
- 原有 0-10 明度块和明度分布柱状图保持不变。
- 本次未修改色彩结构里的点缀色识别逻辑。

## 验证记录

打包前已执行：

```powershell
.build-venv\Scripts\python.exe -m py_compile colortool.py tests\conftest.py tests\test_color_structure.py tests\test_image_safety.py
.build-venv\Scripts\python.exe -c "import tests.test_color_structure as t; [getattr(t, name)() for name in dir(t) if name.startswith('test_')]; print('test functions passed')"
```

打包命令：

```powershell
.build-venv\Scripts\pyinstaller.exe --noconfirm --clean --onefile --windowed --name Chromie --icon "D:\Asset\OtherTools\assets\chromie.ico" --add-data "D:\Asset\OtherTools\assets\chromie.png;assets" --distpath release --workpath build --specpath build colortool.py
```

打包后已执行 `release\Chromie.exe` 启动 smoke，应用可正常启动。
