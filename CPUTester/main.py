import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import psutil
import multiprocessing
import math

class CPUTester:
    def __init__(self):
        self.is_running = False
        self.workers = []
        self.cpu_count = psutil.cpu_count()
        
    def get_cpu_info(self):
        cpu_percent = psutil.cpu_percent(interval=0.1, percpu=True)
        cpu_freq = psutil.cpu_freq()
        
        return {
            'count': self.cpu_count,
            'percent': psutil.cpu_percent(interval=0.1),
            'per_cpu': cpu_percent,
            'freq_current': cpu_freq.current if cpu_freq else 0,
            'freq_max': cpu_freq.max if cpu_freq else 0,
        }
    
    def cpu_stress_worker(self, duration, target_load):
        end_time = time.time() + duration
        work_time = target_load / 100.0
        sleep_time = 1.0 - work_time
        
        while time.time() < end_time and self.is_running:
            cycle_start = time.time()
            
            while time.time() - cycle_start < work_time and self.is_running:
                for _ in range(1000):
                    if not self.is_running:
                        return
                    math.sqrt(math.factorial(20))
                    math.sin(math.pi * 12345.6789)
                    math.cos(math.e * 98765.4321)
            
            if sleep_time > 0 and self.is_running:
                time.sleep(sleep_time)
    
    def stress_test(self, num_threads, duration_seconds, target_load, progress_callback=None):
        self.workers = []
        threads = []
        
        for i in range(num_threads):
            thread = threading.Thread(
                target=self.cpu_stress_worker,
                args=(duration_seconds, target_load),
                daemon=True
            )
            threads.append(thread)
            thread.start()
        
        try:
            for remaining in range(duration_seconds, 0, -1):
                if not self.is_running:
                    break
                
                if progress_callback:
                    cpu_info = self.get_cpu_info()
                    elapsed = duration_seconds - remaining
                    progress = (elapsed / duration_seconds) * 100
                    progress_callback(progress, remaining, cpu_info['percent'])
                
                time.sleep(1)
            
            for thread in threads:
                thread.join(timeout=1)
            
            return True, "Test completed"
            
        except Exception as e:
            return False, str(e)
    
    def benchmark_single_thread(self, iterations, progress_callback=None):
        start_time = time.time()
        
        try:
            for i in range(iterations):
                if not self.is_running:
                    return False, 0
                
                for _ in range(1000):
                    if not self.is_running:
                        return False, 0
                    math.sqrt(math.factorial(15))
                    math.sin(math.pi * 123.456)
                
                if progress_callback and i % 10 == 0:
                    progress = ((i + 1) / iterations) * 100
                    progress_callback(progress, f"Iteration: {i + 1}/{iterations}")
            
            elapsed = time.time() - start_time
            score = int((iterations * 1000) / elapsed)
            
            return True, score
            
        except Exception as e:
            return False, 0
    
    def stop(self):
        self.is_running = False


class CPUTesterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CPU Testing Utility")
        self.root.geometry("750x750")
        self.root.resizable(False, False)
        
        self.tester = CPUTester()
        self.update_timer = None
        
        style = ttk.Style()
        style.theme_use('clam')
        
        self.colors = {
            'bg': '#1e1e2e',
            'fg': '#cdd6f4',
            'accent': '#89b4fa',
            'success': '#a6e3a1',
            'warning': '#f9e2af',
            'error': '#f38ba8',
            'card': '#313244'
        }
        
        self.root.configure(bg=self.colors['bg'])
        
        self.create_widgets()
        self.update_cpu_info()
        
    def create_widgets(self):
        header = tk.Frame(self.root, bg=self.colors['accent'], height=70)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        title_label = tk.Label(
            header,
            text="CPU TESTING UTILITY",
            font=('Arial', 20, 'bold'),
            bg=self.colors['accent'],
            fg='#1e1e2e'
        )
        title_label.pack(pady=20)
        
        main_container = tk.Frame(self.root, bg=self.colors['bg'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)
        
        self.create_cpu_info_section(main_container)
        
        separator1 = tk.Frame(main_container, bg=self.colors['accent'], height=2)
        separator1.pack(fill=tk.X, pady=20)
        
        self.create_control_section(main_container)
        
        separator2 = tk.Frame(main_container, bg=self.colors['accent'], height=2)
        separator2.pack(fill=tk.X, pady=20)
        
        self.create_progress_section(main_container)
        
    def create_cpu_info_section(self, parent):
        info_frame = tk.Frame(parent, bg=self.colors['card'], relief=tk.RAISED, bd=2)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        title = tk.Label(
            info_frame,
            text="CPU Status",
            font=('Arial', 13, 'bold'),
            bg=self.colors['card'],
            fg=self.colors['accent']
        )
        title.pack(pady=(15, 10))
        
        stats_frame = tk.Frame(info_frame, bg=self.colors['card'])
        stats_frame.pack(pady=15, padx=25, fill=tk.X)
        
        self.cpu_count_label = tk.Label(
            stats_frame,
            text="CPU Cores: --",
            font=('Arial', 12),
            bg=self.colors['card'],
            fg=self.colors['fg'],
            anchor='w'
        )
        self.cpu_count_label.pack(fill=tk.X, pady=5)
        
        self.cpu_freq_label = tk.Label(
            stats_frame,
            text="Frequency: -- MHz",
            font=('Arial', 12),
            bg=self.colors['card'],
            fg=self.colors['success'],
            anchor='w'
        )
        self.cpu_freq_label.pack(fill=tk.X, pady=5)
        
        self.cpu_usage_label = tk.Label(
            stats_frame,
            text="CPU Usage: ---%",
            font=('Arial', 12),
            bg=self.colors['card'],
            fg=self.colors['warning'],
            anchor='w'
        )
        self.cpu_usage_label.pack(fill=tk.X, pady=5)
        
        self.cpu_progress = ttk.Progressbar(
            stats_frame,
            mode='determinate',
            length=400
        )
        self.cpu_progress.pack(fill=tk.X, pady=(15, 15))
        
    def create_control_section(self, parent):
        control_frame = tk.Frame(parent, bg=self.colors['bg'])
        control_frame.pack(fill=tk.X)
        
        stress_frame = tk.LabelFrame(
            control_frame,
            text=" Stress Test ",
            font=('Arial', 11, 'bold'),
            bg=self.colors['card'],
            fg=self.colors['accent'],
            relief=tk.RAISED,
            bd=2
        )
        stress_frame.pack(fill=tk.X, pady=8)
        
        stress_inner = tk.Frame(stress_frame, bg=self.colors['card'])
        stress_inner.pack(padx=20, pady=15)
        
        tk.Label(
            stress_inner,
            text="Threads:",
            bg=self.colors['card'],
            fg=self.colors['fg'],
            font=('Arial', 11)
        ).grid(row=0, column=0, padx=8, sticky='w')
        
        self.threads_entry = tk.Entry(
            stress_inner,
            width=10,
            font=('Arial', 11),
            bg='#45475a',
            fg=self.colors['fg'],
            insertbackground=self.colors['fg']
        )
        self.threads_entry.grid(row=0, column=1, padx=8)
        self.threads_entry.insert(0, str(self.tester.cpu_count))
        
        tk.Label(
            stress_inner,
            text="Duration (sec):",
            bg=self.colors['card'],
            fg=self.colors['fg'],
            font=('Arial', 11)
        ).grid(row=0, column=2, padx=(20, 8), sticky='w')
        
        self.stress_duration_entry = tk.Entry(
            stress_inner,
            width=10,
            font=('Arial', 11),
            bg='#45475a',
            fg=self.colors['fg'],
            insertbackground=self.colors['fg']
        )
        self.stress_duration_entry.grid(row=0, column=3, padx=8)
        self.stress_duration_entry.insert(0, "60")
        
        tk.Label(
            stress_inner,
            text="Load (%):",
            bg=self.colors['card'],
            fg=self.colors['fg'],
            font=('Arial', 11)
        ).grid(row=0, column=4, padx=(20, 8), sticky='w')
        
        self.load_entry = tk.Entry(
            stress_inner,
            width=10,
            font=('Arial', 11),
            bg='#45475a',
            fg=self.colors['fg'],
            insertbackground=self.colors['fg']
        )
        self.load_entry.grid(row=0, column=5, padx=8)
        self.load_entry.insert(0, "100")
        
        self.stress_btn = tk.Button(
            stress_inner,
            text="Start Stress Test",
            command=self.start_stress_test,
            bg=self.colors['error'],
            fg='#1e1e2e',
            font=('Arial', 11, 'bold'),
            relief=tk.RAISED,
            bd=2,
            padx=25,
            pady=5,
            cursor='hand2'
        )
        self.stress_btn.grid(row=0, column=6, padx=15)
        
        benchmark_frame = tk.LabelFrame(
            control_frame,
            text=" Single-Thread Benchmark ",
            font=('Arial', 11, 'bold'),
            bg=self.colors['card'],
            fg=self.colors['accent'],
            relief=tk.RAISED,
            bd=2
        )
        benchmark_frame.pack(fill=tk.X, pady=8)
        
        bench_inner = tk.Frame(benchmark_frame, bg=self.colors['card'])
        bench_inner.pack(padx=20, pady=15)
        
        tk.Label(
            bench_inner,
            text="Iterations:",
            bg=self.colors['card'],
            fg=self.colors['fg'],
            font=('Arial', 11)
        ).grid(row=0, column=0, padx=8, sticky='w')
        
        self.iterations_entry = tk.Entry(
            bench_inner,
            width=12,
            font=('Arial', 11),
            bg='#45475a',
            fg=self.colors['fg'],
            insertbackground=self.colors['fg']
        )
        self.iterations_entry.grid(row=0, column=1, padx=8)
        self.iterations_entry.insert(0, "100")
        
        self.benchmark_btn = tk.Button(
            bench_inner,
            text="Run Benchmark",
            command=self.run_benchmark,
            bg=self.colors['accent'],
            fg='#1e1e2e',
            font=('Arial', 11, 'bold'),
            relief=tk.RAISED,
            bd=2,
            padx=25,
            pady=5,
            cursor='hand2'
        )
        self.benchmark_btn.grid(row=0, column=2, padx=15)
        
        buttons_frame = tk.Frame(control_frame, bg=self.colors['bg'])
        buttons_frame.pack(fill=tk.X, pady=15)
        
        self.stop_btn = tk.Button(
            buttons_frame,
            text="Stop Test",
            command=self.stop_operation,
            bg=self.colors['warning'],
            fg='#1e1e2e',
            font=('Arial', 12, 'bold'),
            relief=tk.RAISED,
            bd=2,
            padx=30,
            pady=10,
            cursor='hand2',
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=8)
        
    def create_progress_section(self, parent):
        progress_frame = tk.Frame(parent, bg=self.colors['card'], relief=tk.RAISED, bd=2)
        progress_frame.pack(fill=tk.BOTH, expand=True)
        
        title = tk.Label(
            progress_frame,
            text="Operation Progress",
            font=('Arial', 13, 'bold'),
            bg=self.colors['card'],
            fg=self.colors['accent']
        )
        title.pack(pady=(15, 10))
        
        self.status_label = tk.Label(
            progress_frame,
            text="Waiting for operation...",
            font=('Arial', 11),
            bg=self.colors['card'],
            fg=self.colors['fg']
        )
        self.status_label.pack(pady=10)
        
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            length=600
        )
        self.progress_bar.pack(pady=15, padx=25)
        
        self.countdown_label = tk.Label(
            progress_frame,
            text="",
            font=('Arial', 16, 'bold'),
            bg=self.colors['card'],
            fg=self.colors['warning']
        )
        self.countdown_label.pack(pady=15)
        
        self.result_label = tk.Label(
            progress_frame,
            text="",
            font=('Arial', 14, 'bold'),
            bg=self.colors['card'],
            fg=self.colors['success']
        )
        self.result_label.pack(pady=10)
        
    def update_cpu_info(self):
        cpu_info = self.tester.get_cpu_info()
        
        self.cpu_count_label.config(text=f"CPU Cores: {cpu_info['count']}")
        self.cpu_freq_label.config(text=f"Frequency: {cpu_info['freq_current']:.0f} MHz")
        self.cpu_usage_label.config(text=f"CPU Usage: {cpu_info['percent']:.1f}%")
        
        self.cpu_progress['value'] = cpu_info['percent']
        
        self.update_timer = self.root.after(1000, self.update_cpu_info)
        
    def start_stress_test(self):
        try:
            threads = int(self.threads_entry.get())
            duration = int(self.stress_duration_entry.get())
            load = int(self.load_entry.get())
            
            if threads <= 0 or duration <= 0:
                messagebox.showerror("Error", "Enter valid positive values!")
                return
            
            if load <= 0 or load > 100:
                messagebox.showerror("Error", "Load must be between 1 and 100%!")
                return
                
            if threads > self.tester.cpu_count * 4:
                if not messagebox.askyesno("Warning", 
                    f"Thread count ({threads}) is much higher than CPU cores ({self.tester.cpu_count}). Continue?"):
                    return
                    
        except ValueError:
            messagebox.showerror("Error", "Enter valid numbers!")
            return
        
        self.disable_buttons()
        self.tester.is_running = True
        self.result_label.config(text="")
        
        def progress_callback(progress, remaining, cpu_percent):
            self.progress_bar['value'] = progress
            self.status_label.config(text=f"Running stress test at {load}% target load...")
            self.countdown_label.config(
                text=f"Remaining: {remaining} sec | CPU: {cpu_percent:.1f}%"
            )
            
        def task():
            result, message = self.tester.stress_test(threads, duration, load, progress_callback)
            self.root.after(0, lambda: self.on_stress_complete(result, message))
        
        threading.Thread(target=task, daemon=True).start()
        
    def run_benchmark(self):
        try:
            iterations = int(self.iterations_entry.get())
            
            if iterations <= 0:
                messagebox.showerror("Error", "Enter a positive number!")
                return
                
        except ValueError:
            messagebox.showerror("Error", "Enter a valid number!")
            return
        
        self.disable_buttons()
        self.tester.is_running = True
        self.result_label.config(text="")
        
        def progress_callback(progress, message):
            self.progress_bar['value'] = progress
            self.status_label.config(text=message)
            
        def task():
            result, score = self.tester.benchmark_single_thread(iterations, progress_callback)
            self.root.after(0, lambda: self.on_benchmark_complete(result, score))
        
        threading.Thread(target=task, daemon=True).start()
        
    def stop_operation(self):
        self.tester.stop()
        self.status_label.config(text="Operation stopped by user")
        self.countdown_label.config(text="")
        
    def on_stress_complete(self, result, message):
        self.countdown_label.config(text="")
        
        if result:
            self.status_label.config(text=message)
            messagebox.showinfo("Success", "Stress test completed successfully!")
        else:
            if self.tester.is_running:
                self.status_label.config(text=f"Error: {message}")
                messagebox.showerror("Error", message)
            else:
                self.status_label.config(text="Operation stopped")
        
        self.enable_buttons()
        
    def on_benchmark_complete(self, result, score):
        if result:
            self.status_label.config(text="Benchmark completed")
            self.result_label.config(text=f"Score: {score:,} ops/sec")
            messagebox.showinfo("Success", f"Benchmark Score: {score:,} operations per second")
        else:
            if self.tester.is_running:
                self.status_label.config(text="Benchmark error")
                messagebox.showerror("Error", "Benchmark failed!")
            else:
                self.status_label.config(text="Operation stopped")
        
        self.enable_buttons()
        
    def disable_buttons(self):
        self.stress_btn.config(state=tk.DISABLED)
        self.benchmark_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
    def enable_buttons(self):
        self.stress_btn.config(state=tk.NORMAL)
        self.benchmark_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.tester.is_running = False
        
    def on_closing(self):
        self.tester.stop()
        
        if self.update_timer:
            self.root.after_cancel(self.update_timer)
        
        self.root.destroy()


def main():
    root = tk.Tk()
    app = CPUTesterGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()