# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置（Windows / macOS 通用）。

正式交付为 windowed（无控制台）应用：
- Windows：dist/GNSS文献调研Agent/GNSSAgent.exe（双击启动，无黑窗口）
- macOS：dist/GNSS文献调研Agent.app（双击启动，无终端，Dock 图标）
调试可设 GNSS_BUILD_CONSOLE=1 保留控制台。

用法（Windows 一键打包见 packaging/build_windows.bat）：
    pip install -r requirements.txt pyinstaller
    pyinstaller packaging/gnss_agent.spec --noconfirm
"""
import os
import sys
from pathlib import Path

# SPECPATH = 本 spec 所在目录（packaging/），项目根在其上一层
root = Path(SPECPATH).parent  # noqa: F821
static_dir = root / "app" / "web" / "static"
assets_dir = root / "packaging" / "assets"
ico = str(assets_dir / "app.ico") if (assets_dir / "app.ico").exists() else None
icns = str(assets_dir / "app.icns") if (assets_dir / "app.icns").exists() else None

# 正式版隐藏控制台（windowed）；调试时 GNSS_BUILD_CONSOLE=1 保留
console = os.environ.get("GNSS_BUILD_CONSOLE") == "1"
# 版本资源（Windows 文件属性）
version_file = str(root / "packaging" / "version_info.txt")

a = Analysis(
    [str(root / "start.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[
        (str(static_dir), "app/web/static"),
    ],
    hiddenimports=[
        # start.py 通过字符串 uvicorn.run("app.main:app") 启动，需显式收集
        "app.main",
        # uvicorn 运行时动态加载的组件
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "pytest", "setuptools", "pip", "numpy", "pandas", "matplotlib",
        "scipy", "torch", "tensorflow", "jupyter", "notebook",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GNSSAgent",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=console,          # 正式版 False（无黑窗口/无终端）
    icon=ico,                 # Windows 图标（packaging/assets/app.ico）
    version=version_file if os.path.exists(version_file) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="GNSS文献调研Agent",
)

# macOS：再包一层 .app（双击启动、无终端、Dock 图标）
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="GNSS文献调研Agent.app",
        icon=icns,  # macOS 图标（packaging/assets/app.icns）
        bundle_identifier="com.gnssagent.local",
        info_plist={
            "CFBundleName": "GNSS 文献调研 Agent",
            "CFBundleDisplayName": "GNSS 文献调研 Agent",
            "CFBundleShortVersionString": "0.2.0",
            "CFBundleVersion": "0.2.0",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "10.15",
        },
    )
