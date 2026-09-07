import logging
import os
from datetime import datetime
from pathlib import Path

_BaseHome = Path.cwd()
_MAX_LOG_FILES = 20

# 日志配置
_log_level_str = "DEBUG"
_log_level = getattr(logging, _log_level_str.upper())
_log_dir = _BaseHome / "reports" / "LOG"
_log_format = "%(asctime)s - %(name)s - %(filename)s[line:%(lineno)d] - %(levelname)s - %(message)s"


def _cleanup_old_logs(log_dir: Path, max_files: int = _MAX_LOG_FILES) -> None:
    """保留最近的 max_files 个日志文件，删除更早的。"""
    log_files = sorted(log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime)
    while len(log_files) > max_files:
        oldest = log_files.pop(0)
        try:
            oldest.unlink()
        except OSError:
            pass


def log_init():
    """初始化日志：每次调用创建带时间戳的新文件，保留最近 20 个。"""
    _log_dir.mkdir(parents=True, exist_ok=True)

    # 每次执行生成带时间戳的唯一文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    log_file = _log_dir / f"log_{timestamp}.log"

    logger = logging.getLogger("main")
    logger.setLevel(level=_log_level)
    formatter = logging.Formatter(_log_format)

    try:
        handler = logging.FileHandler(filename=log_file, encoding="utf-8")
        handler.setLevel(_log_level)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    except PermissionError:
        pass  # 日志目录不可写时降级为仅控制台

    console = logging.StreamHandler()
    console.setLevel(_log_level)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # 清理超出数量限制的旧文件
    _cleanup_old_logs(_log_dir)

    return logger


logger = log_init()
