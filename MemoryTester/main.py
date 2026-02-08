import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import psutil # external lib
import sys

class MemoryTester:
    def __init__(self):
        self.allocated_memory = []
        self.chunk_size = 100 * 1024 * 1024
        self.is_running = False
        
    def get_memory_info(self):
        memory = psutil.virtual_memory()
        return {
            'total': memory.total / (1024**3),
            'available': memory.available / (1024**3),
            'used': memory.used / (1024**3),
            'percent': memory.percent
        }
    
    def allocate_memory(self, size_gb, progress_callback=None):
        size_bytes = int(size_gb * 1024 * 1024 * 1024)
        chunks_needed = size_bytes // self.chunk_size
        remainder = size_bytes % self.chunk_size
        
        try:
            for i in range(chunks_needed):
                if not self.is_running:
                    return False
                    
                chunk = bytearray(self.chunk_size)
                for j in range(0, len(chunk), 4096):
                    chunk[j] = (i + j) % 256
                self.allocated_memory.append(chunk)
                
                if progress_callback:
                    progress = ((i + 1) / chunks_needed) * 100
                    allocated_mb = (i + 1) * 100
                    progress_callback(progress, f"Выделено: {allocated_mb} МБ")
            
            if remainder > 0:
                if not self.is_running:
                    return False
                chunk = bytearray(remainder)
                for j in range(0, len(chunk), 4096):
                    chunk[j] = j % 256
                self.allocated_memory.append(chunk)
            
            if progress_callback:
                progress_callback(100, f"Выделено: {size_gb:.2f} ГБ")
            
            return True
            
        except MemoryError:
            return False
        except Exception as e:
            return False
    
    def free_memory(self):
        if self.allocated_memory:
            size_gb = sum(len(chunk) for chunk in self.allocated_memory) / (1024**3)
            self.allocated_memory.clear()
            return size_gb
        return 0
    
    def fill_max_memory(self, duration_seconds, safety_margin_gb, 
                       progress_callback=None, countdown_callback=None):
        mem_info = self.get_memory_info()
        available_gb = mem_info['available']
        to_allocate = max(0, available_gb - safety_margin_gb)
        
        if to_allocate <= 0:
            return False, "Недостаточно свободной памяти"
        
        if not self.allocate_memory(to_allocate, progress_callback):
            return False, "Ошибка выделения памяти"
        
        try:
            for remaining in range(duration_seconds, 0, -1):
                if not self.is_running:
                    break
                    
                if countdown_callback:
                    mem_current = self.get_memory_info()
                    countdown_callback(remaining, mem_current['percent'])
                time.sleep(1)
            
            return True, "Тест завершён"
            
        except Exception as e:
            return False, str(e)


class MemoryTesterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Утилита тестирования памяти")
        self.root.geometry("750x700")
        self.root.resizable(False, False)
        
        self.tester = MemoryTester()
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
        self.update_memory_info()
        
    def create_widgets(self):
        header = tk.Frame(self.root, bg=self.colors['accent'], height=70)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        title_label = tk.Label(
            header,
            text="ТЕСТИРОВАНИЕ ОПЕРАТИВНОЙ ПАМЯТИ",
            font=('Arial', 20, 'bold'),
            bg=self.colors['accent'],
            fg='#1e1e2e'
        )
        title_label.pack(pady=20)
        
        main_container = tk.Frame(self.root, bg=self.colors['bg'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)
        
        self.create_memory_info_section(main_container)
        
        separator1 = tk.Frame(main_container, bg=self.colors['accent'], height=2)
        separator1.pack(fill=tk.X, pady=20)
        
        self.create_control_section(main_container)
        
        separator2 = tk.Frame(main_container, bg=self.colors['accent'], height=2)
        separator2.pack(fill=tk.X, pady=20)
        
        self.create_progress_section(main_container)
        
    def create_memory_info_section(self, parent):
        info_frame = tk.Frame(parent, bg=self.colors['card'], relief=tk.RAISED, bd=2)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        title = tk.Label(
            info_frame,
            text="Состояние памяти",
            font=('Arial', 13, 'bold'),
            bg=self.colors['card'],
            fg=self.colors['accent']
        )
        title.pack(pady=(15, 10))
        
        stats_frame = tk.Frame(info_frame, bg=self.colors['card'])
        stats_frame.pack(pady=15, padx=25, fill=tk.X)
        
        self.total_label = tk.Label(
            stats_frame,
            text="Всего: -- ГБ",
            font=('Arial', 12),
            bg=self.colors['card'],
            fg=self.colors['fg'],
            anchor='w'
        )
        self.total_label.pack(fill=tk.X, pady=5)
        
        self.available_label = tk.Label(
            stats_frame,
            text="Доступно: -- ГБ",
            font=('Arial', 12),
            bg=self.colors['card'],
            fg=self.colors['success'],
            anchor='w'
        )
        self.available_label.pack(fill=tk.X, pady=5)
        
        self.used_label = tk.Label(
            stats_frame,
            text="Использовано: -- ГБ (---%)",
            font=('Arial', 12),
            bg=self.colors['card'],
            fg=self.colors['warning'],
            anchor='w'
        )
        self.used_label.pack(fill=tk.X, pady=5)
        
        self.memory_progress = ttk.Progressbar(
            stats_frame,
            mode='determinate',
            length=400
        )
        self.memory_progress.pack(fill=tk.X, pady=(15, 15))
        
    def create_control_section(self, parent):
        control_frame = tk.Frame(parent, bg=self.colors['bg'])
        control_frame.pack(fill=tk.X)
        
        allocate_frame = tk.LabelFrame(
            control_frame,
            text=" Выделить память ",
            font=('Arial', 11, 'bold'),
            bg=self.colors['card'],
            fg=self.colors['accent'],
            relief=tk.RAISED,
            bd=2
        )
        allocate_frame.pack(fill=tk.X, pady=8)
        
        alloc_inner = tk.Frame(allocate_frame, bg=self.colors['card'])
        alloc_inner.pack(padx=20, pady=15)
        
        tk.Label(
            alloc_inner,
            text="Размер (ГБ):",
            bg=self.colors['card'],
            fg=self.colors['fg'],
            font=('Arial', 11)
        ).grid(row=0, column=0, padx=8, sticky='w')
        
        self.allocate_entry = tk.Entry(
            alloc_inner,
            width=12,
            font=('Arial', 11),
            bg='#45475a',
            fg=self.colors['fg'],
            insertbackground=self.colors['fg']
        )
        self.allocate_entry.grid(row=0, column=1, padx=8)
        self.allocate_entry.insert(0, "1.0")
        
        self.allocate_btn = tk.Button(
            alloc_inner,
            text="Выделить",
            command=self.allocate_memory,
            bg=self.colors['accent'],
            fg='#1e1e2e',
            font=('Arial', 11, 'bold'),
            relief=tk.RAISED,
            bd=2,
            padx=25,
            pady=5,
            cursor='hand2'
        )
        self.allocate_btn.grid(row=0, column=2, padx=15)
        
        fill_frame = tk.LabelFrame(
            control_frame,
            text=" Заполнить до максимума ",
            font=('Arial', 11, 'bold'),
            bg=self.colors['card'],
            fg=self.colors['accent'],
            relief=tk.RAISED,
            bd=2
        )
        fill_frame.pack(fill=tk.X, pady=8)
        
        fill_inner = tk.Frame(fill_frame, bg=self.colors['card'])
        fill_inner.pack(padx=20, pady=15)
        
        tk.Label(
            fill_inner,
            text="Время (сек):",
            bg=self.colors['card'],
            fg=self.colors['fg'],
            font=('Arial', 11)
        ).grid(row=0, column=0, padx=8, sticky='w')
        
        self.duration_entry = tk.Entry(
            fill_inner,
            width=12,
            font=('Arial', 11),
            bg='#45475a',
            fg=self.colors['fg'],
            insertbackground=self.colors['fg']
        )
        self.duration_entry.grid(row=0, column=1, padx=8)
        self.duration_entry.insert(0, "60")
        
        tk.Label(
            fill_inner,
            text="Запас (ГБ):",
            bg=self.colors['card'],
            fg=self.colors['fg'],
            font=('Arial', 11)
        ).grid(row=0, column=2, padx=(20, 8), sticky='w')
        
        self.safety_entry = tk.Entry(
            fill_inner,
            width=12,
            font=('Arial', 11),
            bg='#45475a',
            fg=self.colors['fg'],
            insertbackground=self.colors['fg']
        )
        self.safety_entry.grid(row=0, column=3, padx=8)
        self.safety_entry.insert(0, "2.0")
        
        self.fill_btn = tk.Button(
            fill_inner,
            text="Заполнить",
            command=self.fill_max_memory,
            bg=self.colors['error'],
            fg='#1e1e2e',
            font=('Arial', 11, 'bold'),
            relief=tk.RAISED,
            bd=2,
            padx=25,
            pady=5,
            cursor='hand2'
        )
        self.fill_btn.grid(row=0, column=4, padx=15)
        
        buttons_frame = tk.Frame(control_frame, bg=self.colors['bg'])
        buttons_frame.pack(fill=tk.X, pady=15)
        
        self.free_btn = tk.Button(
            buttons_frame,
            text="Освободить память",
            command=self.free_memory,
            bg=self.colors['success'],
            fg='#1e1e2e',
            font=('Arial', 12, 'bold'),
            relief=tk.RAISED,
            bd=2,
            padx=30,
            pady=10,
            cursor='hand2'
        )
        self.free_btn.pack(side=tk.LEFT, padx=8)
        
        self.stop_btn = tk.Button(
            buttons_frame,
            text="Остановить",
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
            text="Прогресс операции",
            font=('Arial', 13, 'bold'),
            bg=self.colors['card'],
            fg=self.colors['accent']
        )
        title.pack(pady=(15, 10))
        
        self.status_label = tk.Label(
            progress_frame,
            text="Ожидание операции...",
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
        
    def update_memory_info(self):
        mem_info = self.tester.get_memory_info()
        
        self.total_label.config(text=f"Всего: {mem_info['total']:.2f} ГБ")
        self.available_label.config(text=f"Доступно: {mem_info['available']:.2f} ГБ")
        self.used_label.config(
            text=f"Использовано: {mem_info['used']:.2f} ГБ ({mem_info['percent']:.1f}%)"
        )
        
        self.memory_progress['value'] = mem_info['percent']
        
        self.update_timer = self.root.after(1000, self.update_memory_info)
        
    def allocate_memory(self):
        try:
            size = float(self.allocate_entry.get())
            if size <= 0:
                messagebox.showerror("Ошибка", "Размер должен быть положительным!")
                return
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректное число!")
            return
        
        self.disable_buttons()
        self.tester.is_running = True
        
        def progress_callback(progress, message):
            self.progress_bar['value'] = progress
            self.status_label.config(text=message)
            
        def task():
            result = self.tester.allocate_memory(size, progress_callback)
            self.root.after(0, lambda: self.on_allocate_complete(result, size))
        
        threading.Thread(target=task, daemon=True).start()
        
    def fill_max_memory(self):
        try:
            duration = int(self.duration_entry.get())
            safety = float(self.safety_entry.get())
            
            if duration <= 0 or safety < 0:
                messagebox.showerror("Ошибка", "Введите корректные значения!")
                return
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректные числа!")
            return
        
        self.disable_buttons()
        self.tester.is_running = True
        
        def progress_callback(progress, message):
            self.progress_bar['value'] = progress
            self.status_label.config(text=message)
            
        def countdown_callback(remaining, mem_percent):
            self.countdown_label.config(
                text=f"Осталось: {remaining} сек | Память: {mem_percent:.1f}%"
            )
            
        def task():
            result, message = self.tester.fill_max_memory(
                duration, safety, progress_callback, countdown_callback
            )
            self.root.after(0, lambda: self.on_fill_complete(result, message))
        
        threading.Thread(target=task, daemon=True).start()
        
    def free_memory(self):
        freed = self.tester.free_memory()
        if freed > 0:
            self.status_label.config(text=f"Освобождено: {freed:.2f} ГБ")
            self.progress_bar['value'] = 0
            self.countdown_label.config(text="")
            messagebox.showinfo("Успех", f"Освобождено {freed:.2f} ГБ памяти")
        else:
            messagebox.showinfo("Информация", "Память уже освобождена")
            
    def stop_operation(self):
        self.tester.is_running = False
        self.status_label.config(text="Операция остановлена пользователем")
        
    def on_allocate_complete(self, result, size):
        if result:
            self.status_label.config(text=f"Успешно выделено {size:.2f} ГБ")
            messagebox.showinfo("Успех", f"Выделено {size:.2f} ГБ памяти")
        else:
            if self.tester.is_running:
                self.status_label.config(text="Ошибка выделения памяти")
                messagebox.showerror("Ошибка", "Недостаточно памяти!")
            else:
                self.status_label.config(text="Операция остановлена")
        self.enable_buttons()
        
    def on_fill_complete(self, result, message):
        self.tester.free_memory()
        self.countdown_label.config(text="")
        
        if result:
            self.status_label.config(text=message)
            messagebox.showinfo("Успех", message)
        else:
            if self.tester.is_running:
                self.status_label.config(text=message)
                messagebox.showerror("Ошибка", message)
            else:
                self.status_label.config(text="Операция остановлена")
        
        self.enable_buttons()
        
    def disable_buttons(self):
        self.allocate_btn.config(state=tk.DISABLED)
        self.fill_btn.config(state=tk.DISABLED)
        self.free_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
    def enable_buttons(self):
        self.allocate_btn.config(state=tk.NORMAL)
        self.fill_btn.config(state=tk.NORMAL)
        self.free_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.tester.is_running = False
        
    def on_closing(self):
        if self.tester.allocated_memory:
            if messagebox.askokcancel("Выход", "Освободить память перед выходом?"):
                self.tester.free_memory()
        
        if self.update_timer:
            self.root.after_cancel(self.update_timer)
        
        self.root.destroy()


def main():
    root = tk.Tk()
    app = MemoryTesterGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()