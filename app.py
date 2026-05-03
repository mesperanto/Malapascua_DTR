import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- APP CONFIG & HEADER ---
st.set_page_config(page_title="Malapascua DTR")
st.title("Malapascua - Daily Time Record")

FILE_PATH = "dtr_log.csv"
ADMIN_PIN = "1234" 
STANDARD_HOURS = 8.0 

# --- DATA LOADING ---
if os.path.exists(FILE_PATH):
    df = pd.read_csv(FILE_PATH)
else:
    df = pd.DataFrame(columns=["Name", "Date", "Time In", "Time Out", "Status"])

# --- STAFF LIST ---
staff_names = [
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

# --- CALCULATION LOGIC ---
def calculate_metrics(row):
    if row['Status'] == 'Completed' and pd.notnull(row['Time Out']) and row['Time Out'] != "":
        try:
            fmt = "%H:%M:%S"
            t_in = datetime.strptime(row['Time In'], fmt)
            t_out = datetime.strptime(row['Time Out'], fmt)
            duration = (t_out - t_in).total_seconds() / 3600
            
            ot = max(0.0, duration - STANDARD_HOURS)
            ut = max(0.0, STANDARD_HOURS - duration)
            return round(duration, 2), round(ot, 2), round(ut, 2)
        except:
            return 0.0, 0.0, 0.0
    return 0.0, 0.0, 0.0

# --- TABS ---
tab1, tab2 = st.tabs(["🕒 Attendance", "⚙️ Admin (Payroll & Edits)"])

with tab1:
    selected_name = st.selectbox("Select Staff Name:", staff_names)
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("TIME IN", type="primary", use_container_width=True):
            now = datetime.now()
            new_row = {"Name": selected_name, "Date": now.strftime("%Y-%m-%d"), "Time In": now.strftime("%H:%M:%S"), "Time Out": "", "Status": "Active"}
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_csv(FILE_PATH, index=False)
            st.success(f"{selected_name} Timed In.")

    with col2:
        if st.button("TIME OUT", use_container_width=True):
            idx = df.index[(df['Name'] == selected_name) & (df['Status'] == 'Active')]
            if not idx.empty:
                df.at[idx[-1], 'Time Out'] = datetime.now().strftime("%H:%M:%S")
                df.at[idx[-1], 'Status'] = 'Completed'
                df.to_csv(FILE_PATH, index=False)
                st.error(f"{selected_name} Timed Out.")
            else:
                st.warning("No active 'Time In' record found.")

with tab2:
    pin_input = st.text_input("Enter Admin PIN", type="password")
    if pin_input == ADMIN_PIN:
        st.subheader("Payroll Review & Record Management")
        
        # Display logic with calculations
        display_df = df.copy()
        if not display_df.empty:
            metrics = display_df.apply(calculate_metrics, axis=1, result_type='expand')
            display_df['Hours Worked'] = metrics[0]
            display_df['Overtime'] = metrics[1]
            display_df['Undertime'] = metrics[2]

        # Use data_editor for easy editing/deleting
        edited_df = st.data_editor(display_df, num_rows="dynamic", key="payroll_editor")
        
        if st.button("Save Changes"):
            save_cols = ["Name", "Date", "Time In", "Time Out", "Status"]
            # Filter back to original columns for storage
            final_df = edited_df[save_cols]
            final_df.to_csv(FILE_PATH, index=False)
            st.success("Changes saved successfully.")
    elif pin_input != "":
        st.error("Incorrect PIN.")
