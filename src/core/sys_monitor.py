# src/core/sys_monitor.py
import psutil
import platform
import os
import shutil

def get_system_stats():
    """Récupère les stats style 'Cockpit'"""
    
    # 1. CPU & RAM
    cpu_usage = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()
    
    # 2. Espace Disque (Partition principale /)
    total, used, free = shutil.disk_usage("/")
    disk_percent = (used / total) * 100
    
    # 3. Température (Gestion Mac vs Pi)
    temp = 0
    system = platform.system()
    
    if system == "Linux":
        try:
            # Lecture standard sonde Raspberry Pi
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = int(f.read()) / 1000.0
        except:
            temp = 0
    else:
        # Sur Mac, on simule pour le test (car accès restreint par Apple)
        temp = 45.0 

    return {
        "cpu": round(cpu_usage, 1),
        "ram": round(ram.percent, 1),
        "ram_used_mb": round(ram.used / 1024 / 1024),
        "disk": round(disk_percent, 1),
        "disk_free_gb": round(free / (1024**3), 1),
        "temp": round(temp, 1),
        "os": f"{system} {platform.release()}"
    }

# Test rapide si lancé directement
if __name__ == "__main__":
    print(get_system_stats())