"""跨平台构建脚本：PyInstaller 打包 +（Windows 上）Inno Setup 安装器。

用法：
    python packaging/build.py            # Windows / macOS / Linux 通用
构建产物：
    dist/GNSS文献调研Agent/             # PyInstaller 单目录应用（跨平台）
    dist_installer/*.exe                # Windows 安装器（仅 Windows + Inno Setup）
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list):
    print("$", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def pip_install(packages: list):
    """pip 安装，失败自动切换清华镜像重试（国内网络友好）。"""
    try:
        run([sys.executable, "-m", "pip", "install", *packages])
    except subprocess.CalledProcessError:
        print("  ⚠️ pip 安装失败，自动改用清华镜像重试…")
        run([sys.executable, "-m", "pip", "install",
             "-i", "https://pypi.tuna.tsinghua.edu.cn/simple", *packages])


def main():
    print("=" * 56)
    print("  GNSS 文献调研 Agent — 构建")
    print("=" * 56)

    # 1. 依赖
    if not shutil.which("pyinstaller"):
        print("[1/4] 安装构建依赖（pyinstaller / pillow）…")
        pip_install(["-r", str(ROOT / "requirements.txt"), "pyinstaller", "pillow"])
    else:
        print("[1/4] 构建依赖已就绪")

    # 2. 应用图标（ico/icns）
    print("[2/4] 生成应用图标…")
    try:
        import PIL  # noqa: F401
    except ImportError:
        pip_install(["pillow"])
    run([sys.executable, str(ROOT / "packaging" / "make_icon.py")])

    # 3. PyInstaller
    print("[3/4] PyInstaller 打包…")
    run([sys.executable, "-m", "PyInstaller",
         str(ROOT / "packaging" / "gnss_agent.spec"),
         "--noconfirm",
         "--distpath", str(ROOT / "dist"),
         "--workpath", str(ROOT / "build")])
    dist = ROOT / "dist" / "GNSS文献调研Agent"
    if not dist.exists():
        print("❌ 打包失败：未找到产物", dist)
        sys.exit(1)
    print(f"   ✅ 产物：{dist}")

    # 4. Inno Setup 安装器（仅 Windows）
    if os.name == "nt":
        iscc = shutil.which("iscc")
        if not iscc:
            print("[4/4] ⚠️ 未找到 Inno Setup 编译器（iscc）。")
            print("      安装 Inno Setup 6：https://jrsoftware.org/isinfo.php")
            print("      安装后重新运行本脚本，或手动执行：iscc packaging\\installer.iss")
            print("      产物已生成，可手动把 dist\\GNSS文献调研Agent\\ 分发给用户。")
        else:
            print("[4/4] 生成安装器…")
            run([iscc, str(ROOT / "packaging" / "installer.iss")])
            print(f"   ✅ 安装器输出：{ROOT / 'dist_installer'}")
    else:
        print("[4/4] ℹ️ 非 Windows 环境，跳过 Inno Setup 安装器。")
        print("      macOS 产物为 dist/GNSS文献调研Agent.app（双击即用）；")
        print("      请在 Windows 上运行 packaging\\build_windows.bat 生成安装包。")

    print("=" * 56)
    print("  构建完成")


if __name__ == "__main__":
    main()
