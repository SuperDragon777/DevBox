# hello @superdragon0000

import tkinter as tk
from tkinter import messagebox
import subprocess
import os

class TaskKiller:
    def __init__(self, root):
        self.root = root
        self.root.title("Task Killer")
        self.root.geometry("400x250")
        self.root.resizable(False, False)
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(script_dir, 'knife.ico')
        
        try:
            root.iconbitmap(icon_path)
        except:
            pass
        
        input_frame = tk.Frame(root)
        input_frame.pack(pady=15, padx=20, fill=tk.X)
        
        tk.Label(input_frame, text="Enter name or PID:", font=("Arial", 10)).pack(anchor=tk.W)
        
        self.input_field = tk.Entry(input_frame, font=("Arial", 11))
        self.input_field.pack(fill=tk.X, pady=5)
        self.input_field.focus()
        self.input_field.bind('<Return>', lambda e: self.kill())
        
        kill_btn = tk.Button(root, text="KILL", command=self.kill,
                            font=("Arial", 11, "bold"), padx=25, pady=8)
        kill_btn.pack(pady=15)
        
        self.status = tk.Label(root, text="", font=("Arial", 9))
        self.status.pack(pady=5)
        
        info_text = f"Task Killer | PID: {os.getpid()} | NAME: {os.path.basename(__file__)}\n@superdragon0000"
        info = tk.Label(root, text=info_text, font=("Arial", 7), fg="gray")
        info.pack(pady=2)
    
    def kill(self):
        value = self.input_field.get().strip()
        if not value:
            messagebox.showwarning("Error", "Enter name or PID")
            return
        
        try:
            subprocess.run(['taskkill', '/IM', value, '/F'], 
                        capture_output=True, check=False)
            subprocess.run(['taskkill', '/PID', value, '/F'], 
                        capture_output=True, check=False)
            self.status.config(text="Process terminated")
            
            self.input_field.delete(0, tk.END)
            self.root.after(2000, lambda: self.status.config(text=""))
        except Exception as e:
            messagebox.showerror("Error", str(e))

if __name__ == '__main__':
    root = tk.Tk()
    app = TaskKiller(root)
    root.mainloop()