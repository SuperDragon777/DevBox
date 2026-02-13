import tkinter as tk
from tkinter import ttk
import psutil
import platform
import subprocess
import re
import threading
import time
import ctypes


class TemperatureMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("Temperature Monitor")
        self.root.geometry("600x500")
        self.root.resizable(False, False)
        
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass
        
        self.monitoring = True
        self.update_interval = 2000
        
        self.setup_ui()
        self.start_monitoring()
    
    def setup_ui(self):
        style = ttk.Style()
        style.configure('TLabel', font=('Segoe UI', 11))
        style.configure('Title.TLabel', font=('Segoe UI', 16, 'bold'))
        style.configure('Temp.TLabel', font=('Segoe UI', 14))
        
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = ttk.Label(header_frame, text="Temperature Monitor", style='Title.TLabel')
        title_label.pack(side=tk.LEFT)
        
        self.refresh_btn = ttk.Button(header_frame, text="Refresh", command=self.refresh_data)
        self.refresh_btn.pack(side=tk.RIGHT, padx=5)
        
        self.auto_refresh_var = tk.BooleanVar(value=True)
        auto_check = ttk.Checkbutton(
            header_frame,
            text="Auto-refresh",
            variable=self.auto_refresh_var
        )
        auto_check.pack(side=tk.RIGHT, padx=5)
        
        self.info_frame = ttk.LabelFrame(main_frame, text="System Information", padding=15)
        self.info_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        self.cpu_frame = ttk.Frame(self.info_frame)
        self.cpu_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.cpu_frame, text="CPU:", font=('Segoe UI', 12, 'bold')).pack(anchor=tk.W)
        
        self.cpu_temp_label = ttk.Label(self.cpu_frame, text="Temperature: --°C", style='Temp.TLabel')
        self.cpu_temp_label.pack(anchor=tk.W, padx=20, pady=5)
        
        self.cpu_usage_label = ttk.Label(self.cpu_frame, text="Usage: --%")
        self.cpu_usage_label.pack(anchor=tk.W, padx=20)
        
        ttk.Separator(self.info_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        self.gpu_frame = ttk.Frame(self.info_frame)
        self.gpu_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.gpu_frame, text="GPU:", font=('Segoe UI', 12, 'bold')).pack(anchor=tk.W)
        
        self.gpu_temp_label = ttk.Label(self.gpu_frame, text="Temperature: --°C", style='Temp.TLabel')
        self.gpu_temp_label.pack(anchor=tk.W, padx=20, pady=5)
        
        self.gpu_usage_label = ttk.Label(self.gpu_frame, text="Usage: --%")
        self.gpu_usage_label.pack(anchor=tk.W, padx=20)
        
        ttk.Separator(self.info_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        self.disk_frame = ttk.Frame(self.info_frame)
        self.disk_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.disk_frame, text="Storage:", font=('Segoe UI', 12, 'bold')).pack(anchor=tk.W)
        
        self.disk_temp_label = ttk.Label(self.disk_frame, text="Temperature: --°C", style='Temp.TLabel')
        self.disk_temp_label.pack(anchor=tk.W, padx=20, pady=5)
        
        ttk.Separator(self.info_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        self.system_frame = ttk.Frame(self.info_frame)
        self.system_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.system_frame, text="System:", font=('Segoe UI', 12, 'bold')).pack(anchor=tk.W)
        
        self.battery_temp_label = ttk.Label(self.system_frame, text="Battery: --°C", style='Temp.TLabel')
        self.battery_temp_label.pack(anchor=tk.W, padx=20, pady=5)
        
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X)
        
        self.status_label = ttk.Label(status_frame, text="Initializing...", font=('Segoe UI', 9))
        self.status_label.pack(side=tk.LEFT)
        
        self.last_update_label = ttk.Label(status_frame, text="", font=('Segoe UI', 9))
        self.last_update_label.pack(side=tk.RIGHT)
    
    def get_cpu_temperature(self):
        system = platform.system()
        
        try:
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                
                if temps:
                    if 'coretemp' in temps:
                        core_temps = [entry.current for entry in temps['coretemp'] if 'Core' in entry.label]
                        if core_temps:
                            return round(sum(core_temps) / len(core_temps), 1)
                    
                    elif 'k10temp' in temps:
                        for entry in temps['k10temp']:
                            if 'Tdie' in entry.label or 'Tctl' in entry.label:
                                return round(entry.current, 1)
                    
                    elif 'cpu_thermal' in temps:
                        return round(temps['cpu_thermal'][0].current, 1)
                    
                    for sensor_name, entries in temps.items():
                        if entries:
                            return round(entries[0].current, 1)
            
            if system == "Windows":
                try:
                    result = subprocess.run(
                        ['wmic', 'path', 'Win32_PerfFormattedData_Counters_ThermalZoneInformation', 
                         'get', 'Temperature'],
                        capture_output=True,
                        text=True,
                        encoding='cp866',
                        errors='ignore',
                        timeout=5
                    )
                    
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        if len(lines) > 1:
                            temp_str = lines[1].strip()
                            if temp_str.isdigit():
                                temp_kelvin = int(temp_str)
                                temp_celsius = (temp_kelvin - 2732) / 10.0
                                return round(temp_celsius, 1)
                except:
                    pass
        except:
            pass
        
        return None
    
    def get_gpu_temperature(self):
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=temperature.gpu', '--format=csv,noheader'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                temp = result.stdout.strip()
                if temp.isdigit():
                    return int(temp)
        except:
            pass
        
        return None
    
    def get_gpu_usage(self):
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                usage = result.stdout.strip().replace('%', '').strip()
                if usage.isdigit():
                    return int(usage)
        except:
            pass
        
        return None
    
    def get_disk_temperature(self):
        system = platform.system()
        
        if system == "Linux":
            try:
                result = subprocess.run(
                    ['hddtemp', '-n', '/dev/sda'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    temp = result.stdout.strip()
                    if temp.replace('.', '').isdigit():
                        return float(temp)
            except:
                pass
        
        elif system == "Windows":
            try:
                result = subprocess.run(
                    ['wmic', 'diskdrive', 'get', 'Temperature'],
                    capture_output=True,
                    text=True,
                    encoding='cp866',
                    errors='ignore',
                    timeout=5
                )
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        temp_str = lines[1].strip()
                        if temp_str.isdigit():
                            return int(temp_str)
            except:
                pass
        
        return None
    
    def get_battery_temperature(self):
        try:
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                
                if temps:
                    if 'BAT0' in temps:
                        return round(temps['BAT0'][0].current, 1)
                    
                    for sensor_name, entries in temps.items():
                        if 'bat' in sensor_name.lower():
                            return round(entries[0].current, 1)
        except:
            pass
        
        return None
    
    def format_temp(self, temp, label="Temperature"):
        if temp is not None:
            color = self.get_temp_color(temp)
            return f"{label}: {temp}°C", color
        return f"{label}: N/A", "#808080"
    
    def get_temp_color(self, temp):
        if temp >= 80:
            return "#DC143C"
        elif temp >= 60:
            return "#FF8C00"
        elif temp >= 40:
            return "#DAA520"
        else:
            return "#228B22"
    
    def update_display(self):
        cpu_temp = self.get_cpu_temperature()
        cpu_usage = psutil.cpu_percent(interval=0.1)
        
        gpu_temp = self.get_gpu_temperature()
        gpu_usage = self.get_gpu_usage()
        
        disk_temp = self.get_disk_temperature()
        battery_temp = self.get_battery_temperature()
        
        cpu_text, cpu_color = self.format_temp(cpu_temp)
        self.cpu_temp_label.config(text=cpu_text, foreground=cpu_color)
        self.cpu_usage_label.config(text=f"Usage: {cpu_usage:.1f}%")
        
        gpu_text, gpu_color = self.format_temp(gpu_temp)
        self.gpu_temp_label.config(text=gpu_text, foreground=gpu_color)
        
        if gpu_usage is not None:
            self.gpu_usage_label.config(text=f"Usage: {gpu_usage}%")
        else:
            self.gpu_usage_label.config(text="Usage: N/A")
        
        disk_text, disk_color = self.format_temp(disk_temp)
        self.disk_temp_label.config(text=disk_text, foreground=disk_color)
        
        battery_text, battery_color = self.format_temp(battery_temp, "Battery")
        self.battery_temp_label.config(text=battery_text, foreground=battery_color)
        
        current_time = time.strftime("%H:%M:%S")
        self.last_update_label.config(text=f"Updated: {current_time}")
        self.status_label.config(text="Monitoring...")
    
    def refresh_data(self):
        self.status_label.config(text="Refreshing...")
        threading.Thread(target=self.update_display, daemon=True).start()
    
    def start_monitoring(self):
        def monitor():
            self.update_display()
            
            if self.monitoring and self.auto_refresh_var.get():
                self.root.after(self.update_interval, monitor)
        
        monitor()
    
    def on_closing(self):
        self.monitoring = False
        self.root.destroy()


def main():
    root = tk.Tk()
    app = TemperatureMonitor(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == '__main__':
    main()