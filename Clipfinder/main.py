#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import pyperclip
import sqlite3
import threading
import time
import hashlib
import ctypes


class ClipboardDatabase:
    def __init__(self, db_path="clipfinder.db"):
        self.db_path = db_path
        self.conn = None
        self.init_database()
    
    def init_database(self):
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clipboard_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                content_hash TEXT UNIQUE NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp ON clipboard_history(timestamp DESC)
        ''')
        self.conn.commit()
    
    def add_entry(self, content):
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO clipboard_history (content, content_hash)
                VALUES (?, ?)
            ''', (content, content_hash))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def search_entries(self, query="", limit=100):
        cursor = self.conn.cursor()
        if query:
            cursor.execute('''
                SELECT id, content, timestamp
                FROM clipboard_history
                WHERE content LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (f'%{query}%', limit))
        else:
            cursor.execute('''
                SELECT id, content, timestamp
                FROM clipboard_history
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
        return cursor.fetchall()
    
    def delete_entry(self, entry_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM clipboard_history WHERE id = ?', (entry_id,))
        self.conn.commit()
    
    def clear_all(self):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM clipboard_history')
        self.conn.commit()
    
    def close(self):
        if self.conn:
            self.conn.close()


class Clipfinder:
    def __init__(self, root):
        self.root = root
        self.root.title("Clipfinder")
        self.root.geometry("1000x600")
        
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass
        
        self.db = ClipboardDatabase()
        self.last_clipboard = ""
        self.monitoring = True
        self.selected_entry_id = None
        
        self.setup_ui()
        self.start_monitoring()
        self.refresh_list()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_ui(self):
        style = ttk.Style()
        style.configure('TLabel', font=('Segoe UI', 11))
        style.configure('TButton', font=('Segoe UI', 10))
        style.configure('TEntry', font=('Segoe UI', 11))
        
        main_container = ttk.Frame(self.root, padding=15)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        title_label = ttk.Label(header_frame, text="Clipfinder", font=('Segoe UI', 18, 'bold'))
        title_label.pack(side=tk.LEFT)
        
        btn_frame = ttk.Frame(header_frame)
        btn_frame.pack(side=tk.RIGHT)
        
        refresh_btn = ttk.Button(btn_frame, text="Refresh", command=self.refresh_list)
        refresh_btn.pack(side=tk.RIGHT, padx=5)
        
        clear_btn = ttk.Button(btn_frame, text="Clear All", command=self.clear_all)
        clear_btn.pack(side=tk.RIGHT, padx=5)
        
        search_frame = ttk.Frame(main_container)
        search_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(search_frame, text="Search:", font=('Segoe UI', 12)).pack(side=tk.LEFT, padx=(0, 10))
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.refresh_list())
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, font=('Segoe UI', 12))
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        content_frame = ttk.Frame(main_container)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        list_frame = ttk.Frame(content_frame)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        list_scroll = ttk.Scrollbar(list_frame)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.history_list = tk.Listbox(
            list_frame,
            yscrollcommand=list_scroll.set,
            font=('Segoe UI', 11),
            selectmode=tk.SINGLE,
            activestyle='none'
        )
        self.history_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_scroll.config(command=self.history_list.yview)
        
        self.history_list.bind('<<ListboxSelect>>', self.on_select)
        self.history_list.bind('<Double-Button-1>', lambda e: self.copy_to_clipboard())
        
        preview_frame = ttk.Frame(content_frame)
        preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        preview_header = ttk.Frame(preview_frame)
        preview_header.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(preview_header, text="Preview", font=('Segoe UI', 13, 'bold')).pack(side=tk.LEFT)
        
        self.preview_text = scrolledtext.ScrolledText(
            preview_frame,
            wrap=tk.WORD,
            font=('Segoe UI', 11),
            state=tk.DISABLED
        )
        self.preview_text.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        action_frame = ttk.Frame(preview_frame)
        action_frame.pack(fill=tk.X)
        
        copy_btn = ttk.Button(action_frame, text="Copy", command=self.copy_to_clipboard)
        copy_btn.pack(side=tk.LEFT, padx=(0, 10), ipadx=20, ipady=5)
        
        delete_btn = ttk.Button(action_frame, text="Delete", command=self.delete_entry)
        delete_btn.pack(side=tk.LEFT, ipadx=20, ipady=5)
        
        status_frame = ttk.Frame(main_container)
        status_frame.pack(fill=tk.X, pady=(15, 0))
        
        self.status_label = ttk.Label(status_frame, text="Ready", font=('Segoe UI', 10))
        self.status_label.pack(side=tk.LEFT)
        
        self.entries_label = ttk.Label(status_frame, text="", font=('Segoe UI', 10))
        self.entries_label.pack(side=tk.RIGHT)
    
    def monitor_clipboard(self):
        while self.monitoring:
            try:
                current = pyperclip.paste()
                if current and current != self.last_clipboard:
                    self.last_clipboard = current
                    if self.db.add_entry(current):
                        self.root.after(0, self.refresh_list)
                time.sleep(0.5)
            except Exception:
                time.sleep(1)
    
    def start_monitoring(self):
        thread = threading.Thread(target=self.monitor_clipboard, daemon=True)
        thread.start()
    
    def refresh_list(self):
        query = self.search_var.get()
        entries = self.db.search_entries(query)
        
        self.history_list.delete(0, tk.END)
        self.entry_map = {}
        
        for entry in entries:
            entry_id, content, timestamp = entry
            
            preview = content.replace('\n', ' ').replace('\r', '').strip()[:100]
            if len(content) > 100:
                preview += "..."
            
            time_str = timestamp.split('.')[0] if '.' in timestamp else timestamp
            display = f"{time_str}  |  {preview}"
            
            self.history_list.insert(tk.END, display)
            self.entry_map[self.history_list.size() - 1] = entry
        
        self.entries_label.config(text=f"{len(entries)} entries")
    
    def on_select(self, event):
        selection = self.history_list.curselection()
        if not selection:
            return
        
        index = selection[0]
        entry = self.entry_map.get(index)
        
        if entry:
            entry_id, content, timestamp = entry
            self.selected_entry_id = entry_id
            
            self.preview_text.config(state=tk.NORMAL)
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(1.0, content)
            self.preview_text.config(state=tk.DISABLED)
    
    def copy_to_clipboard(self):
        if self.selected_entry_id is None:
            return
        
        content = self.preview_text.get(1.0, tk.END).strip()
        self.monitoring = False
        pyperclip.copy(content)
        self.last_clipboard = content
        
        self.root.after(500, lambda: setattr(self, 'monitoring', True))
        self.set_status("Copied!")
    
    def delete_entry(self):
        if self.selected_entry_id is None:
            return
        
        self.db.delete_entry(self.selected_entry_id)
        self.selected_entry_id = None
        
        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.config(state=tk.DISABLED)
        
        self.refresh_list()
        self.set_status("Deleted")
    
    def clear_all(self):
        if messagebox.askyesno("Clear All", "Delete all clipboard history?"):
            self.db.clear_all()
            self.selected_entry_id = None
            
            self.preview_text.config(state=tk.NORMAL)
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.config(state=tk.DISABLED)
            
            self.refresh_list()
            self.set_status("History cleared")
    
    def set_status(self, message):
        self.status_label.config(text=message)
        self.root.after(2000, lambda: self.status_label.config(text="Ready"))
    
    def on_closing(self):
        self.monitoring = False
        self.db.close()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = Clipfinder(root)
    root.mainloop()


if __name__ == '__main__':
    main()