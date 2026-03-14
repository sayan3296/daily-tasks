import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import uuid
from datetime import datetime

# --- PATH SETUP (Compatible with RPM system-wide install) ---
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.expanduser("~/Daily-Tasks")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
DATA_FILE = os.path.join(DATA_DIR, "tasks.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json") # New config file for Dark Mode

def load_tasks():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_tasks(tasks):
    with open(DATA_FILE, 'w') as f:
        json.dump(tasks, f)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"dark_mode": False} # Default

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

class TaskApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Daily-Tasks")
        self.root.geometry("850x700") 
        self.root.minsize(700, 550)
        
        self.style = ttk.Style()
        if 'clam' in self.style.theme_names():
            self.style.theme_use('clam')
            
        self.style.configure("Treeview", font=("Sans", 10), rowheight=30)
        self.style.configure("Treeview.Heading", font=("Sans", 10, "bold"))
        
        icon_path = os.path.join(APP_DIR, "icon.png")
        if os.path.exists(icon_path):
            self.root.iconphoto(False, tk.PhotoImage(file=icon_path))
            
        self.tasks = load_tasks()
        self.config = load_config()
        self.task_ids = [] 
        
        self.main_frame = ttk.Frame(root, padding="15")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # --- INPUT SECTION ---
        self.input_frame = ttk.LabelFrame(self.main_frame, text=" Add New Task ", padding="10")
        self.input_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.input_frame.columnconfigure(1, weight=1) 
        
        ttk.Label(self.input_frame, text="Task:").grid(row=0, column=0, sticky="w", pady=5, padx=(0, 10))
        self.task_entry = ttk.Entry(self.input_frame, font=("Sans", 10))
        self.task_entry.grid(row=0, column=1, sticky="ew", pady=5) 
        
        ttk.Label(self.input_frame, text="Due Date:").grid(row=1, column=0, sticky="w", pady=5, padx=(0, 10))
        
        date_frame = ttk.Frame(self.input_frame)
        date_frame.grid(row=1, column=1, sticky="w")
        
        current_date = datetime.now()
        
        self.year_var = tk.StringVar(value=current_date.strftime("%Y"))
        self.month_var = tk.StringVar(value=current_date.strftime("%m"))
        self.day_var = tk.StringVar(value=current_date.strftime("%d"))
        
        years = [str(y) for y in range(current_date.year, current_date.year + 10)]
        months = [f"{m:02d}" for m in range(1, 13)] 
        days = [f"{d:02d}" for d in range(1, 32)]   
        
        self.year_cb = ttk.Combobox(date_frame, textvariable=self.year_var, values=years, width=5, state="readonly", font=("Sans", 10))
        self.year_cb.pack(side=tk.LEFT)
        ttk.Label(date_frame, text="-").pack(side=tk.LEFT, padx=2)
        
        self.month_cb = ttk.Combobox(date_frame, textvariable=self.month_var, values=months, width=3, state="readonly", font=("Sans", 10))
        self.month_cb.pack(side=tk.LEFT)
        ttk.Label(date_frame, text="-").pack(side=tk.LEFT, padx=2)
        
        self.day_cb = ttk.Combobox(date_frame, textvariable=self.day_var, values=days, width=3, state="readonly", font=("Sans", 10))
        self.day_cb.pack(side=tk.LEFT)
        
        self.weekday_label = tk.Label(date_frame, text="", font=("Sans", 10, "italic"))
        self.weekday_label.pack(side=tk.LEFT, padx=(10, 0))

        self.year_cb.bind("<<ComboboxSelected>>", self.update_weekday)
        self.month_cb.bind("<<ComboboxSelected>>", self.update_weekday)
        self.day_cb.bind("<<ComboboxSelected>>", self.update_weekday)
        
        ttk.Button(self.input_frame, text="Add Task", command=self.add_task).grid(row=2, column=0, columnspan=2, pady=(10, 0))
        
        # --- NEW: LIVE SEARCH BAR ---
        search_frame = ttk.Frame(self.main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(search_frame, text="🔍 Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, font=("Sans", 10))
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        # Trigger refresh_list every time a key is released in the search box
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_list())

        # --- TASK LIST SECTION ---
        list_frame = ttk.Frame(self.main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True) 
        
        self.tree = ttk.Treeview(list_frame, columns=("Created", "Due", "Day", "Task"), show="headings", selectmode="browse")
        self.tree.heading("Created", text="Created On")
        self.tree.heading("Due", text="Due Date")
        self.tree.heading("Day", text="Day")
        self.tree.heading("Task", text="Task Description")
        
        self.tree.column("Created", width=100, minwidth=100, stretch=False, anchor="center")
        self.tree.column("Due", width=100, minwidth=100, stretch=False, anchor="center")
        self.tree.column("Day", width=90, minwidth=90, stretch=False, anchor="center")
        self.tree.column("Task", width=250, minwidth=200, stretch=True)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.config(yscrollcommand=scrollbar.set)
        
        # --- BOTTOM CONTROLS SECTION ---
        ctrl_frame = ttk.Frame(self.main_frame)
        ctrl_frame.pack(fill=tk.X, pady=(15, 0))
        
        for i in range(4):
            ctrl_frame.columnconfigure(i, weight=1)

        ttk.Button(ctrl_frame, text="✓ Complete", command=self.mark_complete).grid(row=0, column=0, padx=3, sticky="ew")
        ttk.Button(ctrl_frame, text="✗ Delete", command=self.delete_task).grid(row=0, column=1, padx=3, sticky="ew")
        ttk.Button(ctrl_frame, text="↑ Move Up", command=self.move_up).grid(row=0, column=2, padx=3, sticky="ew")
        ttk.Button(ctrl_frame, text="↓ Move Down", command=self.move_down).grid(row=0, column=3, padx=3, sticky="ew")

        ttk.Button(ctrl_frame, text="Clear All Completed Tasks", command=self.clear_done).grid(row=1, column=0, columnspan=3, pady=(10, 0), padx=3, sticky="ew")
        
        # --- NEW: DARK MODE TOGGLE ---
        self.theme_btn = ttk.Button(ctrl_frame, text="🌙 Dark Mode", command=self.toggle_theme)
        self.theme_btn.grid(row=1, column=3, pady=(10, 0), padx=3, sticky="ew")

        # --- NEW: STATUS BAR (For Copy Notifications) ---
        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(self.main_frame, textvariable=self.status_var, font=("Sans", 9, "italic"), foreground="gray")
        self.status_label.pack(side=tk.BOTTOM, anchor="w", pady=(5, 0))

        # --- BINDINGS ---
        self.task_entry.bind("<Return>", self.add_task)
        self.tree.bind("<Double-1>", self.edit_due_date)
        # NEW: Right-click (<Button-3>) to copy task
        self.tree.bind("<Button-3>", self.copy_task)

        # Initialize
        self.apply_theme() # Applies light/dark mode based on saved config
        self.refresh_list()
        self.update_weekday()

    # --- NEW: THEME ENGINE ---
    def toggle_theme(self):
        self.config["dark_mode"] = not self.config["dark_mode"]
        save_config(self.config)
        self.apply_theme()
        self.refresh_list() # Refresh to update row colors

    def apply_theme(self):
        is_dark = self.config.get("dark_mode", False)
        
        if is_dark:
            bg_color = "#2d2d2d"
            fg_color = "#ffffff"
            tree_bg = "#1e1e1e"
            select_bg = "#005f87"
            self.theme_btn.config(text="☀️ Light Mode")
            self.weekday_label.config(bg=bg_color, fg="#aaaaaa")
        else:
            bg_color = "#d9d9d9"
            fg_color = "#000000"
            tree_bg = "#ffffff"
            select_bg = "#5294e2"
            self.theme_btn.config(text="🌙 Dark Mode")
            self.weekday_label.config(bg=bg_color, fg="#555555")

        self.root.configure(bg=bg_color)
        self.style.configure("TFrame", background=bg_color)
        self.style.configure("TLabelframe", background=bg_color, foreground=fg_color)
        self.style.configure("TLabelframe.Label", background=bg_color, foreground=fg_color)
        self.style.configure("TLabel", background=bg_color, foreground=fg_color)
        self.style.configure("Treeview", background=tree_bg, fieldbackground=tree_bg, foreground=fg_color)
        self.style.configure("Treeview.Heading", background="#3c3c3c" if is_dark else "#f0f0f0", foreground=fg_color)
        self.style.map("Treeview", background=[("selected", select_bg)])

    # --- NEW: COPY ACTION ---
    def copy_task(self, event):
        item_id = self.tree.identify_row(event.y)
        if item_id:
            # Highlight the row you clicked
            self.tree.selection_set(item_id)
            task_text = self.tasks[item_id]['text']
            
            # Copy to Fedora clipboard
            self.root.clipboard_clear()
            self.root.clipboard_append(task_text)
            
            # Show status message that fades away after 3 seconds
            self.status_var.set(f"✓ Copied to clipboard: '{task_text[:40]}...'")
            self.root.after(3000, lambda: self.status_var.set(""))

    def update_weekday(self, event=None):
        try:
            y = int(self.year_var.get())
            m = int(self.month_var.get())
            d = int(self.day_var.get())
            selected_date = datetime(y, m, d)
            day_name = selected_date.strftime("%A")
            # The color of this label is managed by apply_theme now!
            self.weekday_label.config(text=f"({day_name})")
        except ValueError:
            self.weekday_label.config(text="(Invalid Date)", fg="#ef5350" if self.config.get("dark_mode") else "#d32f2f")

    def add_task(self, event=None):
        text = self.task_entry.get().strip()
        
        try:
            y = int(self.year_var.get())
            m = int(self.month_var.get())
            d = int(self.day_var.get())
            datetime(y, m, d) 
        except ValueError:
            messagebox.showwarning("Invalid Date", "The date you selected does not exist on the calendar.")
            return

        due_date = f"{self.year_var.get()}-{self.month_var.get()}-{self.day_var.get()}"
        created_date = datetime.now().strftime("%Y-%m-%d")
        
        if not text:
            messagebox.showwarning("Error", "Please enter a task description")
            return
            
        task_id = str(uuid.uuid4())
        self.tasks[task_id] = {
            "text": text,
            "date": due_date,         
            "created_date": created_date, 
            "completed": False,
            "reminders_sent": 0,
            "last_reminded": None,
            "snoozed_until": None
        }
        save_tasks(self.tasks)
        
        self.task_entry.delete(0, tk.END)
        self.year_var.set(datetime.now().strftime("%Y"))
        self.month_var.set(datetime.now().strftime("%m"))
        self.day_var.set(datetime.now().strftime("%d"))
        
        # Clear search box when adding a new task so you can see it appear
        self.search_var.set("") 
        self.refresh_list()
        self.update_weekday() 
        self.task_entry.focus_set()

    def edit_due_date(self, event=None):
        selected = self.tree.selection()
        if not selected: return
        task_id = selected[0]
        task = self.tasks[task_id]

        edit_win = tk.Toplevel(self.root)
        edit_win.title("Change Due Date")
        edit_win.geometry("360x180")
        edit_win.resizable(False, False)
        
        # Make the pop-up match the current theme
        if self.config.get("dark_mode"):
            edit_win.configure(bg="#2d2d2d")
        
        edit_win.transient(self.root) 

        ttk.Label(edit_win, text="Task:", font=("Sans", 9)).pack(pady=(10, 0))
        ttk.Label(edit_win, text=task['text'], font=("Sans", 10, "bold"), wraplength=320).pack(pady=(0, 15))

        date_frame = ttk.Frame(edit_win)
        date_frame.pack()

        curr_y, curr_m, curr_d = task['date'].split('-')
        
        current_date = datetime.now()
        years = [str(y) for y in range(current_date.year - 5, current_date.year + 10)]
        months = [f"{m:02d}" for m in range(1, 13)] 
        days = [f"{d:02d}" for d in range(1, 32)]   
        
        pop_y_var = tk.StringVar(value=curr_y)
        pop_m_var = tk.StringVar(value=curr_m)
        pop_d_var = tk.StringVar(value=curr_d)

        ttk.Combobox(date_frame, textvariable=pop_y_var, values=years, width=5, state="readonly", font=("Sans", 10)).pack(side=tk.LEFT)
        ttk.Label(date_frame, text="-").pack(side=tk.LEFT, padx=2)
        ttk.Combobox(date_frame, textvariable=pop_m_var, values=months, width=3, state="readonly", font=("Sans", 10)).pack(side=tk.LEFT)
        ttk.Label(date_frame, text="-").pack(side=tk.LEFT, padx=2)
        ttk.Combobox(date_frame, textvariable=pop_d_var, values=days, width=3, state="readonly", font=("Sans", 10)).pack(side=tk.LEFT)

        def save_new_date():
            try:
                datetime(int(pop_y_var.get()), int(pop_m_var.get()), int(pop_d_var.get()))
            except ValueError:
                messagebox.showwarning("Invalid Date", "Please select a valid date.", parent=edit_win)
                return
                
            new_date = f"{pop_y_var.get()}-{pop_m_var.get()}-{pop_d_var.get()}"
            self.tasks[task_id]['date'] = new_date
            save_tasks(self.tasks)
            self.refresh_list()
            edit_win.destroy() 

        ttk.Button(edit_win, text="Save New Date", command=save_new_date).pack(pady=20)
        
        edit_win.update_idletasks()
        edit_win.grab_set() 
        edit_win.focus_set()

    def refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        today_str = datetime.now().strftime("%Y-%m-%d")
        search_query = self.search_var.get().lower() # Get text from search bar
        
        # Configure colors based on Light/Dark mode
        is_dark = self.config.get("dark_mode", False)
        if is_dark:
            self.tree.tag_configure("overdue", foreground="#ef5350", font=("Sans", 10, "bold")) # Lighter red
            self.tree.tag_configure("today", foreground="#4fc3f7", font=("Sans", 10, "bold"))   # Lighter blue
            self.tree.tag_configure("upcoming", foreground="#dddddd")                            # Off-white
        else:
            self.tree.tag_configure("overdue", foreground="#d32f2f", font=("Sans", 10, "bold"))
            self.tree.tag_configure("today", foreground="#1976d2", font=("Sans", 10, "bold"))
            self.tree.tag_configure("upcoming", foreground="#333333")

        overdue_tasks = []
        normal_tasks = []
        
        for t_id, t_info in self.tasks.items():
            if not t_info.get('completed', False):
                # Apply the search filter here!
                if search_query in t_info['text'].lower() or search_query in t_info['date']:
                    if t_info['date'] < today_str:
                        overdue_tasks.append((t_id, t_info))
                    else:
                        normal_tasks.append((t_id, t_info))
        
        self.task_ids = []
        
        for t_id, t_info in overdue_tasks:
            created = t_info.get('created_date', 'Legacy') 
            tag = "overdue"
            day_name = datetime.strptime(t_info['date'], "%Y-%m-%d").strftime("%A")
            self.tree.insert("", tk.END, iid=t_id, values=(created, t_info['date'], day_name, t_info['text']), tags=(tag,))
            self.task_ids.append(t_id)
            
        for t_id, t_info in normal_tasks:
            created = t_info.get('created_date', 'Legacy')
            tag = "today" if t_info['date'] == today_str else "upcoming"
            day_name = datetime.strptime(t_info['date'], "%Y-%m-%d").strftime("%A")
            self.tree.insert("", tk.END, iid=t_id, values=(created, t_info['date'], day_name, t_info['text']), tags=(tag,))
            self.task_ids.append(t_id)

    def mark_complete(self):
        selected = self.tree.selection()
        if not selected: return
        task_id = selected[0]
        self.tasks[task_id]['completed'] = True
        save_tasks(self.tasks)
        self.refresh_list()

    def delete_task(self):
        selected = self.tree.selection()
        if not selected: return
        task_id = selected[0]
        del self.tasks[task_id]
        save_tasks(self.tasks)
        self.refresh_list()

    def clear_done(self):
        if messagebox.askyesno("Confirm", "Permanently delete all completed tasks?"):
            self.tasks = {t_id: info for t_id, info in self.tasks.items() if not info.get('completed', False)}
            save_tasks(self.tasks)
            self.refresh_list()

    def reorder_tasks(self, index1, index2):
        # Disable reordering if search is active to prevent weird data scrambling
        if self.search_var.get().strip():
            messagebox.showinfo("Notice", "Cannot reorder tasks while searching.")
            return

        self.task_ids[index1], self.task_ids[index2] = self.task_ids[index2], self.task_ids[index1]
        
        new_tasks = {}
        for tid in self.task_ids:
            new_tasks[tid] = self.tasks[tid]
            
        for tid, info in self.tasks.items():
            if tid not in new_tasks:
                new_tasks[tid] = info

        self.tasks = new_tasks
        save_tasks(self.tasks)
        self.refresh_list()
        
        self.tree.selection_set(self.task_ids[index2])
        self.tree.focus(self.task_ids[index2])

    def move_up(self):
        selected = self.tree.selection()
        if not selected: return
        task_id = selected[0]
        index = self.task_ids.index(task_id)
        if index > 0:
            self.reorder_tasks(index, index - 1)

    def move_down(self):
        selected = self.tree.selection()
        if not selected: return
        task_id = selected[0]
        index = self.task_ids.index(task_id)
        if index < len(self.task_ids) - 1:
            self.reorder_tasks(index, index + 1)

if __name__ == "__main__":
    root = tk.Tk()
    app = TaskApp(root)
    root.mainloop()
