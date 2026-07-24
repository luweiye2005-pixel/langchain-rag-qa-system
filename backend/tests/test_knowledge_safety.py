"""知识库文档存储安全辅助函数测试。"""
from pathlib import Path

import pytest

from app.api.v1.knowledge import _ensure_managed_path
from app.config import settings


def test_managed_path_accepts_file_below_upload_root(tmp_path):
    """上传根目录内的 UUID 文件可被访问。"""
    original = settings.UPLOAD_DIR
    settings.UPLOAD_DIR = str(tmp_path)
    try:
        path = tmp_path / "a8f9b3a6-916e-4b3f-a0f1-1e5342d37db9" / "file.txt"
        assert _ensure_managed_path(str(path)) == path.resolve()
    finally:
        settings.UPLOAD_DIR = original


def test_managed_path_rejects_path_outside_upload_root(tmp_path):
    """数据库路径被篡改为根目录外时不得访问。"""
    original = settings.UPLOAD_DIR
    settings.UPLOAD_DIR = str(tmp_path / "uploads")
    try:
        with pytest.raises(ValueError, match="outside"):
            _ensure_managed_path(str(tmp_path / "outside.txt"))
    finally:
        settings.UPLOAD_DIR = original
