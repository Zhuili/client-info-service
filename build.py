"""
在开发机上运行此脚本打包当前平台的可执行文件。
用法：python build.py
依赖：pip install pyinstaller
"""
import subprocess, platform, zipfile, sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
elif sys.stdout.encoding != 'utf-8':
    # Fallback for older python or restricted environments
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

OS   = platform.system()
NAME = {
    "Windows": "client-info-setup.exe",
    "Linux":   "client-info-setup-linux",
    "Darwin":  "client-info-setup-macos",
}.get(OS, "client-info-setup")

OUT_DIR = Path("dist")

def build():
    OUT_DIR.mkdir(exist_ok=True)

    separator = ";" if OS == "Windows" else ":"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--noconfirm",
        f"--name={NAME}",
        f"--add-data=certs{separator}certs",
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.protocols.websockets",
        "--hidden-import=uvicorn.protocols.websockets.auto",
        "--hidden-import=uvicorn.lifespan",
        "--hidden-import=uvicorn.lifespan.on",
        "--hidden-import=psutil",
        "--hidden-import=netifaces",
        "--hidden-import=fastapi",
        "--hidden-import=anyio",
        "--hidden-import=anyio.lowlevel",
        "bootstrap.py",
    ]

    if OS == "Windows":
        cmd += [
            "--hidden-import=win32service",
            "--hidden-import=win32serviceutil",
            "--hidden-import=win32event",
            "--hidden-import=servicemanager",
            "--hidden-import=winreg",
        ]

    print(f"[build] Packaging {NAME} ...")
    subprocess.run(cmd, check=True)

    # 打 zip
    out_exe  = OUT_DIR / NAME
    zip_path = OUT_DIR / f"{Path(NAME).stem}-release.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(out_exe, NAME)
        z.writestr("README.txt", _readme())

    print(f"\n✅ Build completed: {zip_path}")
    print(f"   Extract and run {NAME} on the target machine.")

def _readme():
    return """\
=== Client Info HTTPS Service ===

部署步骤
--------
Windows:
  右键 client-info-setup.exe → 以管理员身份运行
  首次运行自动注册 Windows Service 并启动

Linux:
  sudo ./client-info-setup-linux

macOS:
  ./client-info-setup-macos

完成后服务开机自动启动，无需任何额外操作。

验证服务
--------
curl -k https://127.0.0.1:8443/health
curl -k -H "X-API-Key: YOUR_KEY" https://127.0.0.1:8443/info

服务管理
--------
Windows: 任务管理器 → 服务 → ClientInfoService
         或 sc stop ClientInfoService / sc start ClientInfoService
Linux:   systemctl status client-info
         systemctl stop/start/restart client-info
         journalctl -u client-info -f
macOS:   launchctl list | grep clientinfo
         tail -f /tmp/client-info.log

卸载
----
Windows: sc stop ClientInfoService && sc delete ClientInfoService
Linux:   systemctl disable --now client-info
         rm /etc/systemd/system/client-info.service
macOS:   launchctl unload ~/Library/LaunchAgents/com.clientinfo.service.plist
         rm ~/Library/LaunchAgents/com.clientinfo.service.plist

配置（可选）
-----------
服务启动前可设置以下环境变量：
  CLIENT_INFO_API_KEY  API 鉴权密钥（为空则不校验）
  PORT                 监听端口，默认 8443
  TLS_CERT             证书路径（默认使用内置证书）
  TLS_KEY              私钥路径（默认使用内置私钥）
"""

if __name__ == "__main__":
    build()
