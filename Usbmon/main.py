import os
import sys
import time
import subprocess
import platform

try:
    import tooly
except ImportError:
    print("Install tooly: pip install tooly-dev")
    sys.exit(1)

c = tooly.ColorSystem()

def _run(cmd: str) -> str:
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip()
    except Exception:
        return ""

def get_drives_linux() -> set:
    drives = set()
    base = "/sys/bus/usb/drivers/usb-storage"
    if not os.path.isdir(base):
        
        for name in os.listdir("/dev"):
            if name.startswith("sd"):
                drives.add(f"/dev/{name}")
        return drives
    for entry in os.listdir(base):
        link = os.path.join(base, entry)
        if not os.path.islink(link):
            continue
        
        real = os.path.realpath(link)
        for root, dirs, files in os.walk(real):
            if "block" in dirs:
                block_dir = os.path.join(root, "block")
                for dev in os.listdir(block_dir):
                    drives.add(f"/dev/{dev}")
                    
                    dev_path = os.path.join(block_dir, dev)
                    for item in os.listdir(dev_path):
                        if item.startswith(dev):
                            drives.add(f"/dev/{item}")
    return drives


def get_drives_macos() -> set:
    out = _run("diskutil list | grep /dev/disk")
    drives = set()
    for line in out.splitlines():
        for word in line.split():
            if word.startswith("/dev/disk"):
                drives.add(word)
    return drives


def get_drives_windows() -> set:
    import string
    import ctypes
    drives = set()
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for i, letter in enumerate(string.ascii_uppercase):
        if bitmask & (1 << i):
            path = f"{letter}:\\"
            if ctypes.windll.kernel32.GetDriveTypeW(path) == 2:
                drives.add(path)
    return drives


def get_drives() -> set:
    sys_name = platform.system()
    if sys_name == "Linux":
        return get_drives_linux()
    elif sys_name == "Darwin":
        return get_drives_macos()
    elif sys_name == "Windows":
        return get_drives_windows()
    return set()

def get_info_linux(dev: str) -> dict:
    info = {}

    out = _run(f"udevadm info --query=all --name={dev} 2>/dev/null")
    for line in out.splitlines():
        line = line.strip()
        if "ID_VENDOR=" in line:
            info["Производитель"] = line.split("=", 1)[1]
        elif "ID_MODEL=" in line and "ID_MODEL_ID" not in line:
            info["Модель"] = line.split("=", 1)[1].replace("_", " ")
        elif "ID_SERIAL=" in line and "ID_SERIAL_SHORT" not in line:
            info["Серийный номер"] = line.split("=", 1)[1]
        elif "ID_FS_LABEL=" in line:
            info["Метка тома"] = line.split("=", 1)[1]
        elif "ID_FS_TYPE=" in line:
            info["Файловая система"] = line.split("=", 1)[1]
        elif "ID_FS_UUID=" in line:
            info["UUID"] = line.split("=", 1)[1]
        elif "ID_USB_DRIVER=" in line:
            info["USB-драйвер"] = line.split("=", 1)[1]
        elif "ID_REVISION=" in line:
            info["Ревизия"] = line.split("=", 1)[1]

    base_dev = dev.rstrip("0123456789") if dev[-1].isdigit() else dev
    out = _run(f"lsblk -bno SIZE,ROTA,TRAN,RM {dev} 2>/dev/null")
    if out:
        parts = out.split()
        if len(parts) >= 1:
            try:
                info["Размер"] = tooly.humanize(int(parts[0]), kind="bytes")
                info["Размер (байт)"] = f"{int(parts[0]):,}".replace(",", " ")
            except ValueError:
                pass
        if len(parts) >= 2:
            info["Тип носителя"] = "HDD (вращающийся)" if parts[1] == "1" else "SSD / Flash"
        if len(parts) >= 3 and parts[2] not in ("", "null"):
            info["Интерфейс"] = parts[2].upper()
        if len(parts) >= 4:
            info["Съёмный"] = "Да" if parts[3] == "1" else "Нет"

    out = _run(f"df -h {dev} 2>/dev/null")
    mounts = []
    for line in out.splitlines()[1:]:
        cols = line.split()
        if cols:
            mounts.append(cols[-1])
    if mounts:
        info["Смонтирован в"] = ", ".join(mounts)
        
        out2 = _run(f"df -B1 {dev} 2>/dev/null")
        for line in out2.splitlines()[1:]:
            cols = line.split()
            if len(cols) >= 4:
                try:
                    used = int(cols[2])
                    avail = int(cols[3])
                    info["Использовано"] = tooly.humanize(used, kind="bytes")
                    info["Свободно"] = tooly.humanize(avail, kind="bytes")
                    if used + avail > 0:
                        pct = round(used / (used + avail) * 100, 1)
                        info["Занято %"] = f"{pct}%"
                except ValueError:
                    pass

    return info


def get_info_macos(dev: str) -> dict:
    info = {}
    out = _run(f"diskutil info {dev}")
    mapping = {
        "Device / Media Name:": "Модель",
        "Disk Size:": "Размер",
        "File System Personality:": "Файловая система",
        "Volume Name:": "Метка тома",
        "Volume UUID:": "UUID",
        "Protocol:": "Интерфейс",
        "Solid State:": "SSD",
        "Removable Media:": "Съёмный",
        "Device Location:": "Расположение",
    }
    for line in out.splitlines():
        for key, label in mapping.items():
            if key in line:
                val = line.split(":", 1)[1].strip()
                if val:
                    info[label] = val
    return info


def get_info_windows(drive: str) -> dict:
    info = {}
    letter = drive.rstrip("\\")
    
    out = _run(f'wmic logicaldisk where "DeviceID=\'{letter}\'" get Size,FreeSpace,FileSystem,VolumeName,VolumeSerialNumber /format:list')
    for line in out.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            if not v:
                continue
            if k == "Size":
                try:
                    info["Размер"] = tooly.humanize(int(v), kind="bytes")
                except ValueError:
                    pass
            elif k == "FreeSpace":
                try:
                    info["Свободно"] = tooly.humanize(int(v), kind="bytes")
                except ValueError:
                    pass
            elif k == "FileSystem":
                info["Файловая система"] = v
            elif k == "VolumeName":
                info["Метка тома"] = v
            elif k == "VolumeSerialNumber":
                info["Серийный номер"] = v
    return info


def get_device_info(dev: str) -> dict:
    sys_name = platform.system()
    if sys_name == "Linux":
        return get_info_linux(dev)
    elif sys_name == "Darwin":
        return get_info_macos(dev)
    elif sys_name == "Windows":
        return get_info_windows(dev)
    return {}

def print_device_info(dev: str):
    tooly.cls()
    tooly.banner(f"USB-накопитель обнаружен", style="thin", color="cyan")
    print()

    info = get_device_info(dev)

    rows = [("Устройство", c.cyan(dev))]

    icon_map = {
        "Производитель":     "🏭",
        "Модель":            "💾",
        "Серийный номер":    "🔢",
        "Метка тома":        "🏷",
        "Файловая система":  "📂",
        "UUID":              "🔑",
        "Интерфейс":        "🔌",
        "Тип носителя":      "⚙",
        "USB-драйвер":       "🚗",
        "Ревизия":           "📌",
        "Размер":            "📏",
        "Размер (байт)":     "📐",
        "Использовано":      "📊",
        "Свободно":          "🟢",
        "Занято %":          "📈",
        "Съёмный":           "📦",
        "Смонтирован в":     "📍",
        "SSD":               "⚡",
        "Расположение":      "🗺",
    }

    order = [
        "Производитель", "Модель", "Серийный номер", "Ревизия",
        "Интерфейс", "USB-драйвер", "Тип носителя", "SSD", "Съёмный", "Расположение",
        "Метка тома", "Файловая система", "UUID",
        "Размер", "Размер (байт)", "Использовано", "Свободно", "Занято %",
        "Смонтирован в",
    ]

    shown = set()
    for key in order:
        if key in info:
            icon = icon_map.get(key, "•")
            label_str = c.dim(f"{icon} {key}")
            val = info[key]
            
            if key == "Свободно":
                val = c.success(val)
            elif key == "Использовано":
                val = c.warning(val)
            elif key == "Занято %":
                pct_val = float(val.rstrip("%"))
                val = c.error(val) if pct_val > 85 else c.warning(val) if pct_val > 60 else c.success(val)
            elif key == "Тип носителя":
                val = c.cyan(val)
            elif key == "Файловая система":
                val = c.blue(val)
            elif key == "Серийный номер":
                val = c.dim(val)
            rows.append((label_str, val))
            shown.add(key)

    
    for key, val in info.items():
        if key not in shown:
            icon = icon_map.get(key, "•")
            rows.append((c.dim(f"{icon} {key}"), val))

    
    import re
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    col_w = max(len(ansi_escape.sub("", r[0])) for r in rows) + 2

    for label_str, val in rows:
        clean_label = ansi_escape.sub("", label_str)
        padding = col_w - len(clean_label)
        print(f"  {label_str}{' ' * padding}{val}")

    print()

    
    if "Занято %" in info:
        try:
            pct = float(info["Занято %"].rstrip("%"))
            filled = round(pct / 10)
            bar_vals = [10 if i < filled else 1 for i in range(10)]
            spark = tooly.sparkline(bar_vals)
            label_color = c.error if pct > 85 else c.warning if pct > 60 else c.success
            print(f"  Заполненность: {label_color(spark)}  {label_color(info['Занято %'])}")
            print()
        except (ValueError, AttributeError):
            pass

    tooly.log.success(f"Устройство {dev} готово к использованию")

def main():
    tooly.cls()
    tooly.banner("USB Watcher", style="block", color="blue")
    print()
    tooly.typewrite(c.info("Ожидание подключения USB-накопителя..."), delay=0.03)
    print(c.dim("  Нажмите Ctrl+C для выхода"))
    print()

    known = get_drives()

    try:
        with tooly.spinner("Мониторинг USB", done_msg="Устройство найдено!"):
            while True:
                time.sleep(1)
                current = get_drives()
                new_devs = current - known
                if new_devs:
                    break

    except KeyboardInterrupt:
        print()
        tooly.log.warn("Прерван пользователем")
        sys.exit(0)

    for dev in sorted(new_devs):
        print_device_info(dev)

    print()
    tooly.typewrite(c.info("Мониторинг отключения..."), delay=0.03)
    try:
        while True:
            time.sleep(1)
            current = get_drives()
            removed = new_devs - current
            if removed:
                for dev in removed:
                    tooly.log.warn(f"Устройство {dev} отключено")
                break
    except KeyboardInterrupt:
        pass

    print()
    tooly.log.info("Готово. Запустите снова для нового устройства.")


if __name__ == "__main__":
    main()