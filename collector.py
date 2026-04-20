import socket
import platform
import uuid
import psutil
import subprocess
import re
from datetime import datetime, timezone

try:
    import netifaces
    HAS_NETIFACES = True
except ImportError:
    HAS_NETIFACES = False


def get_all_interfaces() -> list[dict]:
    result = []
    if HAS_NETIFACES:
        import netifaces as ni
        for iface in ni.interfaces():
            addrs = ni.ifaddresses(iface)
            result.append({
                "interface": iface,
                "ipv4": addrs.get(ni.AF_INET,  [{}])[0].get("addr", ""),
                "ipv6": addrs.get(ni.AF_INET6, [{}])[0].get("addr", ""),
                "mac":  addrs.get(ni.AF_LINK,  [{}])[0].get("addr", ""),
            })
    else:
        for iface, addrs in psutil.net_if_addrs().items():
            ipv4 = ipv6 = mac = ""
            for a in addrs:
                fname = a.family.name if hasattr(a.family, 'name') else str(a.family)
                if fname in ("AF_INET", "2"):     ipv4 = a.address
                if fname in ("AF_INET6", "23"):   ipv6 = a.address
                if fname in ("AF_LINK", "AF_PACKET", "17", "-1"): mac = a.address
            result.append({"interface": iface, "ipv4": ipv4, "ipv6": ipv6, "mac": mac})
    return result


def get_primary_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_real_mac_macos(iface_name: str) -> str:
    try:
        output = subprocess.check_output(["networksetup", "-listallhardwareports"], text=True)
        match = re.search(rf"Device:\s*{iface_name}\nEthernet Address:\s*([0-9a-fA-F:]+)", output)
        if match:
            return match.group(1).lower()
    except Exception:
        pass
    return ""

def get_real_mac_windows(iface_name: str) -> str:
    try:
        output = subprocess.check_output(["getmac", "/V", "/FO", "CSV"], text=True)
        for line in output.splitlines():
            if iface_name in line:
                parts = line.split('","')
                if len(parts) >= 3:
                    mac = parts[2].replace('"', '').replace('-', ':').lower()
                    if mac and mac != "n/a":
                        return mac
    except Exception:
        pass
    return ""

def get_real_mac_linux(iface_name: str) -> str:
    try:
        with open(f"/sys/class/net/{iface_name}/address", "r") as f:
            return f.read().strip().lower()
    except Exception:
        pass
    return ""

def get_primary_mac() -> str:
    primary_ip = get_primary_ip()
    active_iface = None
    active_mac = None

    for iface in get_all_interfaces():
        if iface["ipv4"] == primary_ip and iface["mac"]:
            active_iface = iface["interface"]
            active_mac = iface["mac"]
            break

    if active_iface:
        sys_name = platform.system()
        real_mac = ""
        if sys_name == "Darwin":
            real_mac = get_real_mac_macos(active_iface)
        elif sys_name == "Windows":
            real_mac = get_real_mac_windows(active_iface)
        elif sys_name == "Linux":
            real_mac = get_real_mac_linux(active_iface)
            
        if real_mac:
            return real_mac
        return active_mac

    n = uuid.getnode()
    return ":".join(f"{(n >> i) & 0xFF:02x}" for i in range(40, -8, -8))


def collect() -> dict:
    cpu_freq = psutil.cpu_freq()
    mem  = psutil.virtual_memory()
    disk_path = "C:\\" if platform.system() == "Windows" else "/"
    disk = psutil.disk_usage(disk_path)

    return {
        "timestamp":   datetime.now(timezone.utc).isoformat(),
        "hostname":    socket.gethostname(),
        "fqdn":        socket.getfqdn(),
        "primary_ip":  get_primary_ip(),
        "primary_mac": get_primary_mac(),
        "interfaces":  get_all_interfaces(),
        "os": {
            "system":    platform.system(),
            "release":   platform.release(),
            "version":   platform.version(),
            "machine":   platform.machine(),
            "processor": platform.processor(),
        },
        "cpu": {
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores":  psutil.cpu_count(logical=True),
            "usage_percent":  psutil.cpu_percent(interval=0.5),
            "freq_mhz": round(cpu_freq.current, 1) if cpu_freq else None,
        },
        "memory": {
            "total_gb":     round(mem.total     / 1024**3, 2),
            "available_gb": round(mem.available / 1024**3, 2),
            "used_percent": mem.percent,
        },
        "disk": {
            "path":         disk_path,
            "total_gb":     round(disk.total / 1024**3, 2),
            "free_gb":      round(disk.free  / 1024**3, 2),
            "used_percent": disk.percent,
        },
    }
