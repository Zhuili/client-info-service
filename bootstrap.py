"""
双击此文件即完成部署：
  - 自动注册开机自启（systemd / Windows Service / launchd）
  - 自动启动服务
  - 二次运行会跳过已安装步骤
"""
import sys, os, platform, subprocess, textwrap, shutil
from pathlib import Path

if getattr(sys, "frozen", False):
    EXE_DIR = Path(sys.executable).parent
    BUNDLE  = Path(sys._MEIPASS)
else:
    EXE_DIR = Path(__file__).parent
    BUNDLE  = EXE_DIR

INSTALL_DIR = EXE_DIR
CERT_DIR    = INSTALL_DIR / "certs"
API_KEY     = os.environ.get("CLIENT_INFO_API_KEY", "")
PORT        = os.environ.get("PORT", "8443")
OS          = platform.system()


def release_certs():
    CERT_DIR.mkdir(exist_ok=True)
    for f in ["cert.pem", "key.pem"]:
        src = BUNDLE / "certs" / f
        dst = CERT_DIR / f
        if src.exists() and not dst.exists():
            shutil.copy(src, dst)
            print(f"  [certs] 释放 {f}")


def install():
    release_certs()
    if OS == "Linux":
        _install_linux()
    elif OS == "Windows":
        _install_windows()
    elif OS == "Darwin":
        _install_macos()
    else:
        print(f"不支持的平台: {OS}")
        sys.exit(1)


def _install_linux():
    NAME      = "client-info"
    UNIT_PATH = Path(f"/etc/systemd/system/{NAME}.service")
    if UNIT_PATH.exists():
        print(f"[linux] 服务已存在，跳过安装: {UNIT_PATH}")
        return
    exe = str(Path(sys.executable))
    env_extra = f"Environment=CLIENT_INFO_API_KEY={API_KEY}\n" if API_KEY else ""
    unit = textwrap.dedent(f"""\
        [Unit]
        Description=Client Info HTTPS Service
        After=network.target

        [Service]
        Type=simple
        WorkingDirectory={INSTALL_DIR}
        ExecStart={exe}
        Restart=always
        RestartSec=5
        StandardOutput=journal
        StandardError=journal
        Environment=PORT={PORT}
        Environment=TLS_CERT={CERT_DIR}/cert.pem
        Environment=TLS_KEY={CERT_DIR}/key.pem
        {env_extra}
        [Install]
        WantedBy=multi-user.target
    """)
    UNIT_PATH.write_text(unit)
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", "--now", NAME], check=True)
    print(f"[linux] ✅ 已安装并启动")
    print(f"         journalctl -u {NAME} -f")


def _install_windows():
    import ctypes
    SVC_NAME = "ClientInfoService"
    SVC_DISP = "Client Info HTTPS Service"
    EXE_PATH = str(Path(sys.executable))

    # 检查是否已安装
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             rf"SYSTEM\CurrentControlSet\Services\{SVC_NAME}")
        winreg.CloseKey(key)
        print("[windows] 服务已存在，跳过安装")
        return
    except Exception:
        pass

    if not ctypes.windll.shell32.IsUserAnAdmin():
        print("[windows] 需要管理员权限，正在提权重启...")
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit(0)

    import win32service
    hscm = win32service.OpenSCManager(
        None, None, win32service.SC_MANAGER_CREATE_SERVICE)
    hs = win32service.CreateService(
        hscm, SVC_NAME, SVC_DISP,
        win32service.SERVICE_ALL_ACCESS,
        win32service.SERVICE_WIN32_OWN_PROCESS,
        win32service.SERVICE_AUTO_START,
        win32service.SERVICE_ERROR_NORMAL,
        EXE_PATH, None, 0, None, None, None
    )
    # 设置服务环境变量（写注册表）
    try:
        import winreg
        reg_path = rf"SYSTEM\CurrentControlSet\Services\{SVC_NAME}"
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path,
                           0, winreg.KEY_SET_VALUE)
        env_vars = [
            f"PORT={PORT}",
            f"TLS_CERT={CERT_DIR}\\cert.pem",
            f"TLS_KEY={CERT_DIR}\\key.pem",
        ]
        if API_KEY:
            env_vars.append(f"CLIENT_INFO_API_KEY={API_KEY}")
        winreg.SetValueEx(k, "Environment", 0, winreg.REG_MULTI_SZ, env_vars)
        winreg.CloseKey(k)
    except Exception as e:
        print(f"  [warn] 环境变量写入失败: {e}")

    win32service.StartService(hs, [])
    win32service.CloseServiceHandle(hs)
    win32service.CloseServiceHandle(hscm)
    print(f"[windows] ✅ 已安装并启动，服务名: {SVC_NAME}")
    input("按 Enter 关闭窗口...")


def _install_macos():
    LABEL = "com.clientinfo.service"
    PLIST = Path.home() / f"Library/LaunchAgents/{LABEL}.plist"
    if PLIST.exists():
        print(f"[macos] 已存在，跳过安装: {PLIST}")
        return
    exe = str(Path(sys.executable))
    env_extra = f"<key>CLIENT_INFO_API_KEY</key><string>{API_KEY}</string>" if API_KEY else ""
    xml = textwrap.dedent(f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
          "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
        <plist version="1.0"><dict>
            <key>Label</key>             <string>{LABEL}</string>
            <key>ProgramArguments</key>  <array><string>{exe}</string></array>
            <key>WorkingDirectory</key>  <string>{INSTALL_DIR}</string>
            <key>RunAtLoad</key>         <true/>
            <key>KeepAlive</key>         <true/>
            <key>EnvironmentVariables</key>
            <dict>
                <key>PORT</key>     <string>{PORT}</string>
                <key>TLS_CERT</key> <string>{CERT_DIR}/cert.pem</string>
                <key>TLS_KEY</key>  <string>{CERT_DIR}/key.pem</string>
                {env_extra}
            </dict>
            <key>StandardOutPath</key>  <string>/tmp/client-info.log</string>
            <key>StandardErrorPath</key><string>/tmp/client-info.err</string>
        </dict></plist>
    """)
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    PLIST.write_text(xml)
    subprocess.run(["launchctl", "load", "-w", str(PLIST)], check=True)
    print(f"[macos] ✅ 已安装并启动")
    print(f"         tail -f /tmp/client-info.log")


if __name__ == "__main__":
    print(f"=== Client Info Service 部署工具 ({OS}) ===\n")
    install()

    print(f"\n[service] 启动中，监听 0.0.0.0:{PORT} ...")
    import uvicorn
    from main import app
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(PORT),
        ssl_certfile=str(CERT_DIR / "cert.pem"),
        ssl_keyfile=str(CERT_DIR / "key.pem"),
        log_level="info",
    )
