#!/usr/bin/env python3

import hashlib
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set
import threading
import json


class DuplicateFinder:
    def __init__(self):
        self.duplicates: Dict[str, List[Path]] = defaultdict(list)
        self.total_files = 0
        self.scanned_files = 0
        self.total_size = 0
        self.duplicate_size = 0
        self.stop_flag = False
        
    def calculate_hash(self, filepath: Path, chunk_size: int = 8192) -> str:
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, 'rb') as f:
                while chunk := f.read(chunk_size):
                    if self.stop_flag:
                        return ""
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except (OSError, PermissionError):
            return ""
    
    def get_file_size(self, filepath: Path) -> int:
        try:
            return filepath.stat().st_size
        except OSError:
            return 0
    
    def scan_directory(self, directory: Path, recursive: bool = True,
                      min_size: int = 0, extensions: Set[str] = None,
                      progress_callback=None) -> None:
        self.duplicates.clear()
        self.total_files = 0
        self.scanned_files = 0
        self.total_size = 0
        self.duplicate_size = 0
        self.stop_flag = False
        
        files_to_scan = []
        try:
            if recursive:
                for root, _, files in os.walk(directory):
                    if self.stop_flag:
                        return
                    for filename in files:
                        filepath = Path(root) / filename
                        if extensions and filepath.suffix.lower() not in extensions:
                            continue
                        if self.get_file_size(filepath) >= min_size:
                            files_to_scan.append(filepath)
            else:
                for filepath in directory.iterdir():
                    if filepath.is_file():
                        if extensions and filepath.suffix.lower() not in extensions:
                            continue
                        if self.get_file_size(filepath) >= min_size:
                            files_to_scan.append(filepath)
        except PermissionError:
            pass
        
        self.total_files = len(files_to_scan)
        
        size_groups: Dict[int, List[Path]] = defaultdict(list)
        for filepath in files_to_scan:
            if self.stop_flag:
                return
            size = self.get_file_size(filepath)
            if size > 0:
                size_groups[size].append(filepath)
        
        hash_to_files: Dict[str, List[Path]] = defaultdict(list)
        
        for size, files in size_groups.items():
            if self.stop_flag:
                return
            
            if len(files) > 1:
                for filepath in files:
                    if self.stop_flag:
                        return
                    
                    file_hash = self.calculate_hash(filepath)
                    if file_hash:
                        hash_to_files[file_hash].append(filepath)
                        self.total_size += size
                    
                    self.scanned_files += 1
                    if progress_callback:
                        progress_callback(self.scanned_files, self.total_files)
            else:
                self.scanned_files += 1
                if progress_callback:
                    progress_callback(self.scanned_files, self.total_files)
        
        for file_hash, files in hash_to_files.items():
            if len(files) > 1:
                self.duplicates[file_hash] = files
                file_size = self.get_file_size(files[0])
                self.duplicate_size += file_size * (len(files) - 1)
    
    def stop_scan(self):
        self.stop_flag = True


class DuplicateFinderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Duplicate File Finder")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        self.finder = DuplicateFinder()
        self.scan_thread = None
        self.selected_items = set()
        
        style = ttk.Style()
        style.theme_use('clam')
        
        self.create_widgets()
        
    def create_widgets(self):
        top_frame = ttk.LabelFrame(self.root, text="Scan Settings", padding=10)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        dir_frame = ttk.Frame(top_frame)
        dir_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(dir_frame, text="Directory:").pack(side=tk.LEFT, padx=5)
        
        self.dir_entry = ttk.Entry(dir_frame, width=50)
        self.dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        browse_btn = ttk.Button(dir_frame, text="Browse", command=self.browse_directory)
        browse_btn.pack(side=tk.LEFT, padx=5)
        
        options_frame = ttk.Frame(top_frame)
        options_frame.pack(fill=tk.X, pady=5)
        
        self.recursive_var = tk.BooleanVar(value=True)
        recursive_cb = ttk.Checkbutton(options_frame, text="Recursive scan",
                                       variable=self.recursive_var)
        recursive_cb.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(options_frame, text="Min size (KB):").pack(side=tk.LEFT, padx=(20, 5))
        self.min_size_entry = ttk.Entry(options_frame, width=10)
        self.min_size_entry.insert(0, "0")
        self.min_size_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(options_frame, text="Extensions (e.g., .jpg,.png):").pack(side=tk.LEFT, padx=(20, 5))
        self.ext_entry = ttk.Entry(options_frame, width=20)
        self.ext_entry.pack(side=tk.LEFT, padx=5)
        
        control_frame = ttk.Frame(top_frame)
        control_frame.pack(fill=tk.X, pady=10)
        
        self.scan_btn = ttk.Button(control_frame, text="Start Scan",
                                   command=self.start_scan)
        self.scan_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(control_frame, text="Stop",
                                   command=self.stop_scan, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.delete_btn = ttk.Button(control_frame, text="Delete Selected",
                                     command=self.delete_selected, state=tk.DISABLED)
        self.delete_btn.pack(side=tk.LEFT, padx=5)
        
        self.export_btn = ttk.Button(control_frame, text="Export Results",
                                     command=self.export_results, state=tk.DISABLED)
        self.export_btn.pack(side=tk.LEFT, padx=5)
        
        progress_frame = ttk.Frame(self.root)
        progress_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.progress_label = ttk.Label(progress_frame, text="Ready to scan")
        self.progress_label.pack(side=tk.LEFT, padx=5)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        results_frame = ttk.LabelFrame(self.root, text="Duplicate Files", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.stats_label = ttk.Label(results_frame, text="", font=('Arial', 9, 'bold'))
        self.stats_label.pack(fill=tk.X, pady=5)
        
        tree_frame = ttk.Frame(results_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.tree = ttk.Treeview(tree_frame, columns=("Path", "Size", "Modified"),
                                yscrollcommand=vsb.set, xscrollcommand=hsb.set,
                                selectmode='extended')
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        
        self.tree.heading("#0", text="Group / File")
        self.tree.heading("Path", text="Full Path")
        self.tree.heading("Size", text="Size")
        self.tree.heading("Modified", text="Modified")
        
        self.tree.column("#0", width=200)
        self.tree.column("Path", width=400)
        self.tree.column("Size", width=100)
        self.tree.column("Modified", width=150)
        
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Open file location", command=self.open_file_location)
        self.context_menu.add_command(label="Delete file", command=self.delete_file)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Select all in group", command=self.select_all_in_group)
        self.context_menu.add_command(label="Keep oldest", command=self.keep_oldest)
        self.context_menu.add_command(label="Keep newest", command=self.keep_newest)
        
        self.tree.bind("<Button-3>", self.show_context_menu)
        
    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, directory)
    
    def start_scan(self):
        directory = self.dir_entry.get().strip()
        if not directory or not os.path.isdir(directory):
            messagebox.showerror("Error", "Please select a valid directory")
            return
        
        try:
            min_size = int(self.min_size_entry.get()) * 1024
        except ValueError:
            min_size = 0
        
        extensions_str = self.ext_entry.get().strip()
        extensions = None
        if extensions_str:
            extensions = set(ext.strip().lower() if ext.startswith('.') else f'.{ext.strip().lower()}'
                           for ext in extensions_str.split(','))
        
        recursive = self.recursive_var.get()
        
        self.tree.delete(*self.tree.get_children())
        self.stats_label.config(text="")
        
        self.scan_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.delete_btn.config(state=tk.DISABLED)
        self.export_btn.config(state=tk.DISABLED)
        
        self.scan_thread = threading.Thread(
            target=self.run_scan,
            args=(Path(directory), recursive, min_size, extensions)
        )
        self.scan_thread.daemon = True
        self.scan_thread.start()
    
    def run_scan(self, directory, recursive, min_size, extensions):
        def progress_callback(current, total):
            progress = (current / total * 100) if total > 0 else 0
            self.root.after(0, lambda: self.update_progress(current, total, progress))
        
        self.finder.scan_directory(directory, recursive, min_size, extensions, progress_callback)
        self.root.after(0, self.scan_complete)
    
    def update_progress(self, current, total, progress):
        self.progress_bar['value'] = progress
        self.progress_label.config(text=f"Scanning: {current}/{total} files")
    
    def scan_complete(self):
        self.scan_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
        if not self.finder.duplicates:
            self.progress_label.config(text="No duplicates found")
            messagebox.showinfo("Scan Complete", "No duplicate files found!")
            return
        
        self.delete_btn.config(state=tk.NORMAL)
        self.export_btn.config(state=tk.NORMAL)
        
        group_num = 1
        for file_hash, files in self.finder.duplicates.items():
            file_size = self.finder.get_file_size(files[0])
            group_text = f"Group {group_num} ({len(files)} files, {self.format_size(file_size)} each)"
            
            group_id = self.tree.insert("", tk.END, text=group_text, values=("", "", ""),
                                       tags=('group',))
            
            for filepath in sorted(files):
                try:
                    modified = os.path.getmtime(filepath)
                    modified_str = self.format_time(modified)
                except OSError:
                    modified_str = "N/A"
                
                self.tree.insert(group_id, tk.END, text=filepath.name,
                               values=(str(filepath), self.format_size(file_size), modified_str),
                               tags=('file',))
            
            group_num += 1
        
        total_groups = len(self.finder.duplicates)
        total_duplicates = sum(len(files) - 1 for files in self.finder.duplicates.values())
        stats_text = (f"Found {total_groups} groups with {total_duplicates} duplicate files | "
                     f"Wasted space: {self.format_size(self.finder.duplicate_size)}")
        self.stats_label.config(text=stats_text)
        self.progress_label.config(text=f"Scan complete: {self.finder.scanned_files} files scanned")
    
    def stop_scan(self):
        self.finder.stop_scan()
        self.progress_label.config(text="Stopping scan...")
    
    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "No files selected")
            return
        
        files_to_delete = []
        for item in selected:
            if 'file' in self.tree.item(item, 'tags'):
                filepath = self.tree.item(item, 'values')[0]
                files_to_delete.append((item, filepath))
        
        if not files_to_delete:
            messagebox.showwarning("Warning", "No files selected")
            return
        
        count = len(files_to_delete)
        if not messagebox.askyesno("Confirm Delete",
                                   f"Are you sure you want to delete {count} file(s)?"):
            return
        
        deleted_count = 0
        errors = []
        
        for item, filepath in files_to_delete:
            try:
                os.remove(filepath)
                self.tree.delete(item)
                deleted_count += 1
            except OSError as e:
                errors.append(f"{filepath}: {str(e)}")
        
        for item in self.tree.get_children():
            if not self.tree.get_children(item):
                self.tree.delete(item)
        
        if errors:
            error_msg = f"Deleted {deleted_count} file(s)\n\nErrors:\n" + "\n".join(errors[:10])
            if len(errors) > 10:
                error_msg += f"\n... and {len(errors) - 10} more errors"
            messagebox.showwarning("Delete Complete", error_msg)
        else:
            messagebox.showinfo("Delete Complete", f"Successfully deleted {deleted_count} file(s)")
    
    def export_results(self):
        if not self.finder.duplicates:
            messagebox.showwarning("Warning", "No results to export")
            return
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        try:
            if filepath.endswith('.json'):
                self.export_json(filepath)
            else:
                self.export_text(filepath)
            messagebox.showinfo("Export Complete", f"Results exported to {filepath}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {str(e)}")
    
    def export_json(self, filepath):
        data = {
            'duplicates': {
                hash_val: [str(f) for f in files]
                for hash_val, files in self.finder.duplicates.items()
            },
            'statistics': {
                'total_groups': len(self.finder.duplicates),
                'total_duplicates': sum(len(files) - 1 for files in self.finder.duplicates.values()),
                'wasted_space_bytes': self.finder.duplicate_size
            }
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def export_text(self, filepath):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("Duplicate File Finder Results\n")
            f.write("=" * 60 + "\n\n")
            
            group_num = 1
            for file_hash, files in self.finder.duplicates.items():
                file_size = self.finder.get_file_size(files[0])
                f.write(f"Group {group_num} (Hash: {file_hash[:8]}...)\n")
                f.write(f"File size: {self.format_size(file_size)}\n")
                f.write(f"Copies: {len(files)}\n\n")
                
                for filepath in sorted(files):
                    f.write(f"  - {filepath}\n")
                
                f.write("\n" + "-" * 60 + "\n\n")
                group_num += 1
            
            f.write(f"\nTotal groups: {len(self.finder.duplicates)}\n")
            f.write(f"Total duplicates: {sum(len(files) - 1 for files in self.finder.duplicates.values())}\n")
            f.write(f"Wasted space: {self.format_size(self.finder.duplicate_size)}\n")
    
    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
    
    def open_file_location(self):
        selected = self.tree.selection()
        if not selected:
            return
        
        item = selected[0]
        if 'file' in self.tree.item(item, 'tags'):
            filepath = self.tree.item(item, 'values')[0]
            directory = os.path.dirname(filepath)
            
            if sys.platform == 'win32':
                os.startfile(directory)
            elif sys.platform == 'darwin':
                os.system(f'open "{directory}"')
            else:
                os.system(f'xdg-open "{directory}"')
    
    def delete_file(self):
        selected = self.tree.selection()
        if selected:
            self.delete_selected()
    
    def select_all_in_group(self):
        selected = self.tree.selection()
        if not selected:
            return
        
        item = selected[0]
        parent = self.tree.parent(item)
        
        if parent:
            group = parent
        else:
            group = item
        
        children = self.tree.get_children(group)
        self.tree.selection_set(children)
    
    def keep_oldest(self):
        self.keep_by_criterion('oldest')
    
    def keep_newest(self):
        self.keep_by_criterion('newest')
    
    def keep_by_criterion(self, criterion):
        selected = self.tree.selection()
        if not selected:
            return
        
        item = selected[0]
        parent = self.tree.parent(item)
        
        if parent:
            group = parent
        else:
            group = item
        
        children = self.tree.get_children(group)
        if len(children) <= 1:
            return
        
        files_info = []
        for child in children:
            filepath = self.tree.item(child, 'values')[0]
            try:
                mtime = os.path.getmtime(filepath)
                files_info.append((child, filepath, mtime))
            except OSError:
                pass
        
        if not files_info:
            return
        
        files_info.sort(key=lambda x: x[2])
        
        if criterion == 'oldest':
            keep_item = files_info[0][0]
            delete_items = [item for item, _, _ in files_info[1:]]
        else:
            keep_item = files_info[-1][0]
            delete_items = [item for item, _, _ in files_info[:-1]]
        
        self.tree.selection_set(delete_items)
    
    @staticmethod
    def format_size(size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"
    
    @staticmethod
    def format_time(timestamp):
        import datetime
        return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')


def main():
    root = tk.Tk()
    app = DuplicateFinderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()