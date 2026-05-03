import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from datetime import datetime
import os

class DTRApp:
    def __init__(self, root):
        self.root = root
        # 1. NEW HEADER
        self.root.title("Malapascua - Daily Time Record")
        self.root.geometry("800x700")

        self.file_path = "dtr_log.csv"
        self.load_data()

        # Header Label
        header = tk.Label(root, text="Malapascua - Daily Time Record", font=("Arial", 20, "bold"), pady=20)
        header.pack()

        self.tabs = ttk.Notebook(root)
        self.check_in_tab = ttk.Frame(self.tabs)
        self.admin_tab = ttk.Frame(self.tabs)
        
        self.tabs.add(self.check_in_tab, text="Attendance")
        self.tabs.add(self.admin_tab, text="Admin (Edit/Delete)")
        self.tabs.pack(expand=1, fill="both")

        # 2. FULL STAFF LIST (pulled from your crew records)
        self.staff_names = [
            "ABING, GENESIS", "ANESLAGON, JEROME", "ANESLAGON, JOSE RAMIE", "ANESLAGON, RUSTOM",
            "ARRIESGADO, MANUEL", "BATOLAT, ROGELIO", "BELANGIGUE, RAMILO", "BOHOL, ALFREDO",
            "BRUCES, JURWELJIE", "CABASAN, JORENCE", "CABRAS, YVES", "CONEL, FRANCIS ERIC",
            "CONJELADO, JONATHAN", "DAYDAY, MARRISA", "DIGNOS, ROGELIO JR", "DIMA, ALLMENDRAS",
            "GASTARDO, ARNIL", "GERALDE, ELMAR", "MAJONE, ROMEL", "MALAGASE, CYRIL",
            "MALAGASE, RONALD", "MARO, ALWEN", "MICARSOS, ALEX", "MONTECLAR, KATHLEEN RICA",
            "MORANO, REX", "MORENO, DAVID", "MORENO, JANINE", "PASCOBELLO, MARK MARTIN",
            "PEPITO, ALEXANDER", "PILAPIL, NOVEAIME", "ROSALES, JAMAICA", "ROSALES, JOHN",
            "ROSALES, LYDIO JR", "RUBIO, MELVIN", "SABALBORO, JAYVEE", "SUAN, CLARK", "UY, DANNY", "YANGAN, JESSIE"
        ]

        self.setup_attendance_tab()
        self.setup_admin_tab()

    def load_data(self):
        if os.path.exists(self.file_path):
            self.df = pd.read_csv(self.file_path)
        else:
            self.df = pd.DataFrame(columns=["Name", "Date", "Time In", "Time Out", "Status"])

    def setup_attendance_tab(self):
        tk.Label(self.check_in_tab, text="Select Name:", font=("Arial", 12)).pack(pady=10)
        self.name_var = tk.StringVar()
        # The list stays exactly like this, no names disappear after submission
        self.name_menu = ttk.Combobox(self.check_in_tab, textvariable=self.name_var, values=self.staff_names, state="readonly", font=("Arial", 12), width=30)
        self.name_menu.pack(pady=5)

        btn_frame = tk.Frame(self.check_in_tab)
        btn_frame.pack(pady=20)

        tk.Button(btn_frame, text="TIME IN", bg="green", fg="white", width=15, height=2, command=self.time_in).grid(row=0, column=0, padx=10)
        tk.Button(btn_frame, text="TIME OUT", bg="red", fg="white", width=15, height=2, command=self.time_out).grid(row=0, column=1, padx=10)

        # Status Display
        self.status_label = tk.Label(self.check_in_tab, text="", font=("Arial", 10, "italic"))
        self.status_label.pack(pady=10)

    # 3. ADMIN EDIT/DELETE SECTION
    def setup_admin_tab(self):
        self.tree = ttk.Treeview(self.admin_tab, columns=("Name", "Date", "Time In", "Time Out"), show='headings')
        for col in ("Name", "Date", "Time In", "Time Out"):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)
        
        self.tree.pack(expand=1, fill="both", padx=10, pady=10)

        btn_frame = tk.Frame(self.admin_tab)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Delete Selected", command=self.delete_record, bg="orange").pack(side="left", padx=10)
        tk.Button(btn_frame, text="Refresh", command=self.refresh_admin_list).pack(side="left", padx=10)
        
        self.refresh_admin_list()

    def time_in(self):
        name = self.name_var.get()
        if not name: return
        
        now = datetime.now()
        new_row = {"Name": name, "Date": now.strftime("%Y-%m-%d"), "Time In": now.strftime("%H:%M:%S"), "Time Out": "", "Status": "Active"}
        self.df = pd.concat([self.df, pd.DataFrame([new_row])], ignore_index=True)
        self.save_data()
        self.status_label.config(text=f"Last Entry: {name} Timed In at {new_row['Time In']}", fg="green")

    def time_out(self):
        name = self.name_var.get()
        if not name: return

        # Find the last 'Active' entry for this person
        idx = self.df.index[(self.df['Name'] == name) & (self.df['Status'] == 'Active')]
        if not idx.empty:
            tout = datetime.now().strftime("%H:%M:%S")
            self.df.at[idx[-1], 'Time Out'] = tout
            self.df.at[idx[-1], 'Status'] = 'Completed'
            self.save_data()
            self.status_label.config(text=f"Last Entry: {name} Timed Out at {tout}", fg="red")
        else:
            messagebox.showwarning("Error", "No active Time In found for this person.")

    def delete_record(self):
        selected = self.tree.selection()
        if not selected: return
        for item in selected:
            vals = self.tree.item(item)['values']
            self.df = self.df[~((self.df['Name'] == vals[0]) & (self.df['Time In'] == str(vals[2])))]
        self.save_data()

    def save_data(self):
        self.df.to_csv(self.file_path, index=False)
        self.refresh_admin_list()

    def refresh_admin_list(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for _, row in self.df.iterrows():
            self.tree.insert("", "end", values=(row["Name"], row["Date"], row["Time In"], row["Time Out"]))

if __name__ == "__main__":
    root = tk.Tk()
    app = DTRApp(root)
    root.mainloop()
