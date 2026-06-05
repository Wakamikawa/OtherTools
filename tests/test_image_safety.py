import os
import subprocess
import sys
import textwrap

import pytest

import colortool


class HugeImage:
    size = (100_000, 100_000)

    def convert(self, _mode):
        raise AssertionError("oversized images should be rejected before conversion")


class BrokenImage:
    size = (10, 10)

    def convert(self, _mode):
        raise OSError("decode failed")


class DummyApp:
    def __init__(self):
        self.status = None
        self.is_error = None

    def set_status(self, message, is_error=False):
        self.status = message
        self.is_error = is_error


def test_algorithm_import_does_not_require_tkinterdnd2():
    script = textwrap.dedent(
        """
        import importlib.abc
        import sys

        class BlockTkinterDnD(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname == "tkinterdnd2" or fullname.startswith("tkinterdnd2."):
                    raise ModuleNotFoundError("No module named 'tkinterdnd2'", name="tkinterdnd2")
                return None

        sys.meta_path.insert(0, BlockTkinterDnD())
        import colortool
        print(colortool.ColorInfo(1, 2, 3).hex_text)
        """
    )

    env = {**os.environ, "PYTHONPATH": os.getcwd()}
    result = subprocess.run(
        [sys.executable, "-c", script],
        text=True,
        capture_output=True,
        env=env,
        timeout=5,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "#010203"


def test_image_to_colors_rejects_oversized_images_before_decoding():
    with pytest.raises(Exception) as exc_info:
        colortool.image_to_colors(HugeImage())

    assert exc_info.type.__name__ == "ImageAnalysisError"
    assert "过大" in str(exc_info.value)


def test_apply_image_analysis_reports_decode_errors_without_crashing():
    app = DummyApp()

    colortool.RGBApp.apply_image_analysis(app, BrokenImage(), "broken.png")

    assert app.is_error is True
    assert "图片分析失败" in app.status
