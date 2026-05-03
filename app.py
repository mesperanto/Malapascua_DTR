import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from datetime import datetime
import os

class DTRApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Malapascua - Daily Time Record")
        self.root.geometry("800x600")

        self.file_path = "dtr_log.csv"
        self.load_data()

        # Custom Header
        header = tk.Label(root, text="Malapascua - Daily Time Record", font=("Arial", 20, "bold"), pady=20)
        header.pack()

        self.tabs = ttk.Notebook(root)
        self.check_in_tab = ttk.Frame(self.tabs)
        self.admin_tab = ttk.Frame(self.tabs)
        
        self.tabs.add(self.check_in_tab, text="Attendance")
        self.tabs.add(self.admin_tab, text="Admin (Edit Records)")
        self.tabs.pack(expand=1, fill="both")

        self.setup_attendance_tab()
        self.setup_admin_tab()

    def load_data(self):
        if os.path.exists(self.file_path):
            self.df = pd.read_csv(self.file_path)
        else:
            self.df = pd.DataFrame(columns=["Name", "Date", "Time In", "Time Out", "Status"])

    def setup_attendance_tab(self):
        # Staff list (Add your actual staff names here)
        self.staff_names = ["Juan Dela Cruz", "Maria Santos", "Ricardo Dalisay"] 
        
        tk.Label(self.check_in_tab, text="Select Name:", font=("Arial", 12)).pack(pady=10)
        self.name_var = tk.StringVar()
        self.name_menu = ttk.Combobox(self.check_in_tab, textvariable=self.name_var, values=self.staff_names, state="readonly", font=("Arial", 12))
        self.name_menu.pack(pady=5)

        btn_frame = tk.Frame(self.check_in_tab)
        btn_frame.pack(pady=20)

        tk.Button(btn_frame, text="TIME IN", bg="green", fg="white", width=15, height=2, command=self.time_in).grid(row=0, column=0, padx=10)
        tk.Button(btn_frame, text="TIME OUT", bg="red", fg="white", width=15, height=2, command=self.time_out).grid(row=0, column=1, padx=10)

    def setup_admin_tab(self):
        # Admin table to view and edit records
        self.tree = ttk.Treeview(self.admin_tab, columns=("Name", "Date", "Time In", "Time Out"), show='headings')
        self.tree.heading("Name", text="Name")
        self.tree.heading("Date", text="Date")
        self.tree.heading("Time In", text="Time In")
        self.tree.heading("Time Out", text="Time Out")
        self.tree.pack(expand=1, fill="both", padx=10, pady=10)

        edit_btn_frame = tk.Frame(self.admin_tab)
        edit_btn_frame.pack(pady=10)

        tk.Button(edit_btn_frame, text="Delete Selected Record", command=self.delete_record, bg="#ff9999").pack(side="left", padx=10)
        tk.Button(edit_btn_frame, text="Refresh List", command=self.refresh_admin_list).pack(side="left", padx=10)
        
        self.refresh_admin_list()

    def time_in(self):
        name = self.name_var.get()
        if not name:
            messagebox.showwarning("Error", "Please select a name.")
            return

        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

        # Check if already timed in
        if not self.df[(self.df['Name'] == name) & (self.df['Status'] == 'Active')].empty:
            messagebox.showwarning("Error", f"{name} is already timed in.")
            return

        new_row = {"Name": name, "Date": date_str, "Time In": time_str, "Time Out": "", "Status": "Active"}
        self.df = pd.concat([self.df, pd.DataFrame([new_row])], ignore_index=True)
        self.save_and_refresh()
        messagebox.showinfo("Success", f"{name} timed in at {time_str}")

    def time_out(self):
        name = self.name_var.get()
        if not name:
            messagebox.showwarning("Error", "Please select a name.")
            return

        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")

        idx = self.df.index[(self.df['Name'] == name) & (self.df['Status'] == 'Active')]
        if not idx.empty:
            self.df.at[idx[0], 'Time Out'] = time_str
            self.df.at[idx[0], 'Status'] = 'Completed'
            self.save_and_refresh()
            messagebox.showinfo("Success", f"{name} timed out at {time_str}")
            # Note: name_menu values are NOT filtered, so the name stays in the list for tomorrow/next shift.
        else:
            messagebox.showwarning("Error", f"No active 'Time In' record found for {name}.")

    def delete_record(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Error", "Select a record to delete.")
            return
        
        item_vals = self.tree.item(selected_item)['values']
        # Remove from dataframe based on matching values
        self.df = self.df[~((self.df['Name'] == item_vals[0]) & (self.df['Time In'] == item_vals[2]))]
        self.save_and_refresh()

    def save_and_refresh(self):
        self.df.to_csv(self.file_path, index=False)
        self.refresh_admin_list()

    def refresh_admin_list(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for _, row in self.df.iterrows():
            self.tree.insert("", "end", values=(row["Name"], row["Date"], row["Time In"], row["Time Out"]))

if __name__ == "__main__":
    root = tk.Tk()
    app = DTRApp(root)
    root.mainloop()
