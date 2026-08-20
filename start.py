#!/usr/bin/env python3
"""GNSS 文献调研 Agent — 启动入口（源码运行 / PyInstaller 打包通用）。

特性：
- 单实例检查：已有实例运行时，只打开浏览器，不再启动第二个
- 端口占用自动换端口；启动自检（网络连通性、数据目录可写）
- windowed（无控制台）模式兼容：信息写入日志文件，错误弹窗提示
- 用法：python start.py [--port 9000] [--no-browser] [--skip-selfcheck]
"""
import argparse
import logging
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

from app.config import APP_NAME, DEFAULT_PORT, HOST, VERSION, data_dir


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def is_windowed() -> bool:
    """PyInstaller windowed 模式（console=False）：stdout/stderr 为 None。"""
    return sys.stdout is None or sys.stderr is None

LOG_FILE = data_dir() / "app.log"


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stderr) if not is_windowed()
            else logging.NullHandler(),
        ],
    )


def gui_message(title: str, message: str):
    """windowed 模式下用系统弹窗提示（失败路径）。"""
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, message)
        root.destroy()
    except Exception:  # noqa: BLE001
        pass


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((HOST, port)) == 0


def find_free_port(preferred: int) -> int:
    if not port_in_use(preferred):
        return preferred
    for p in range(preferred + 1, preferred + 30):
        if not port_in_use(p):
            return p
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, 0))
        return s.getsockname()[1]


def is_already_running(port: int) -> bool:
    """单实例：默认端口上运行的是本应用（通过 /api/health 确认）则视为已有实例。"""
    import json as _json
    import urllib.request
    try:
        with urllib.request.urlopen(
                f"http://{HOST}:{port}/api/health", timeout=2) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
            return bool(data.get("ok"))
    except Exception:  # noqa: BLE001
        return False


def network_reachable(host: str = "api.openalex.org", port: int = 443,
                      timeout: float = 3.0) -> bool:
    """启动自检：文献源/模型 API 网络可达性（仅探测，不调用业务接口）。"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def open_browser_later(url: str, delay: float = 1.2):
    def _open():
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:  # noqa: BLE001
            logging.info("请手动打开浏览器访问: %s", url)
    threading.Thread(target=_open, daemon=True).start()


def main():
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="监听端口")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-selfcheck", action="store_true", help="跳过网络自检")
    args = parser.parse_args()

    setup_logging()
    log = logging.getLogger("start")

    # 单实例检查：已有实例 → 直接唤起浏览器
    if port_in_use(args.port) and is_already_running(args.port):
        url = f"http://{HOST}:{args.port}"
        log.info("检测到已有实例运行，仅打开浏览器: %s", url)
        webbrowser.open(url)
        return 0

    # 数据目录可写检查
    try:
        probe = data_dir() / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as e:
        msg = f"数据目录不可写：{data_dir()}\n{e}\n\n请检查磁盘权限。"
        log.error(msg)
        gui_message(APP_NAME, msg)
        return 1

    # 网络自检（仅警告，不阻塞启动——离线也可浏览已有报告）
    if not args.skip_selfcheck:
        try:
            net_ok = network_reachable()
            if not net_ok:
                log.warning("网络不可达（无法访问文献源 API）。离线时新建任务会失败，"
                            "但可查看历史任务与报告。")
        except Exception:  # noqa: BLE001
            pass

    port = find_free_port(args.port)
    url = f"http://{HOST}:{port}"
    os.environ.setdefault("GNSS_AGENT_PORT", str(port))

    if is_windowed():
        log.info("windowed 模式启动：%s", url)
    else:
        print("=" * 56)
        print(f"  {APP_NAME} v{VERSION}")
        print(f"  访问地址: {url}")
        print("  关闭本窗口即可停止服务（任务进度已保存，重启后自动恢复）")
        print(f"  日志文件: {LOG_FILE}")
        print("=" * 56)

    if not args.no_browser:
        open_browser_later(url)

    try:
        import uvicorn
        # Windowed PyInstaller builds have no stdout/stderr. Uvicorn's default
        # formatter calls stderr.isatty(), so use the file logging configured
        # above instead of installing Uvicorn's console logging configuration.
        uvicorn.run(
            "app.main:app",
            host=HOST,
            port=port,
            log_level="info",
            log_config=None,
        )
    except Exception as e:  # noqa: BLE001
        log.exception("服务启动失败")
        gui_message(APP_NAME, f"服务启动失败：{e}\n\n详见日志：{LOG_FILE}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
