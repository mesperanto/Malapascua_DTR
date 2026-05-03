import streamlit as st
import pandas as pd
from datetime import datetime
import os
import time
import pytz  # Added for Manila Timezone

# --- 1. APP CONFIG & HEADER ---
st.set_page_config(page_title="Malapascua DTR", layout="centered")
st.title("Malapascua - Daily Time Record")

FILE_PATH = "dtr_log.csv"
ADMIN_PIN = "1234" 
OT_THRESHOLD = 9.0  
STD_SHIFT = 8.0     
MANILA_TZ = pytz.timezone('Asia/Manila') # Fixed to Manila Time

# --- 2. DATA PERSISTENCE & TYPE SAFETY ---
def load_data():
    if os.path.exists(FILE_PATH):
        return pd.read_csv(FILE_PATH, dtype={'Time In': str, 'Time Out': str, 'Status': str})
    return pd.DataFrame(columns=["Name", "Date", "Time In", "Time Out", "Status"])

def save_data(dataframe):
    dataframe.to_csv(FILE_PATH, index=False)

df = load_data()

# --- 3. STAFF LIST ---
staff_names = [""] + [
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

# --- 4. AUTOMATIC PAYROLL CALCULATION LOGIC ---
def calculate_payroll(row):
    t_in_str = str(row.get('Time In', ''))
    t_out_str = str(row.get('Time Out', ''))
    
    if row['Status'] == 'Completed' and t_out_str and t_out_str != 'nan' and t_in_str != 'nan':
        try:
            fmt = "%H:%M:%S"
            t_in = datetime.strptime(t_in_str if len(t_in_str.split(':')) == 3 else t_in_str + ":00", fmt)
            t_out = datetime.strptime(t_out_str if len(t_out_str.split(':')) == 3 else t_out_str + ":00", fmt)
            duration = (t_out - t_in).total_seconds() / 3600
            ot = max(0.0, duration - OT_THRESHOLD)
            ut = max(0.0, STD_SHIFT - duration)
            return round(duration, 2), round(ot, 2), round(ut, 2)
        except Exception:
            return 0.0, 0.0, 0.0
    return 0.0, 0.0, 0.0

# --- 5. TABS INTERFACE ---
tab1, tab2 = st.tabs(["🕒 Attendance", "⚙️ Admin (PIN Required)"])

with tab1:
    msg_placeholder = st.empty() 
    
    # Session state key added to allow resetting to blank index 0
    if "staff_select" not in st.session_state:
        st.session_state.staff_select = ""

    selected_name = st.selectbox("Select Staff Name:", staff_names, index=staff_names.index(st.session_state.staff_select) if st.session_state.staff_select in staff_names else 0, key="staff_dropdown")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("TIME IN", type="primary", use_container_width=True):
            if selected_name != "":
                now = datetime.now(MANILA_TZ) # Manila Time
                new_entry = {"Name": selected_name, "Date": now.strftime("%Y-%m-%d"), 
                             "Time In": now.strftime("%H:%M:%S"), "Time Out": "", "Status": "Active"}
                df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
                save_data(df)
                msg_placeholder.success(f"Clocked IN: {selected_name} at {now.strftime('%H:%M')}")
                st.session_state.staff_select = "" # Reset to blank
                time.sleep(5)
                msg_placeholder.empty()
                st.rerun()

    with col2:
        if st.button("TIME OUT", use_container_width=True):
            idx = df.index[(df['Name'] == selected_name) & (df['Status'] == 'Active')]
            if not idx.empty:
                now = datetime.now(MANILA_TZ) # Manila Time
                df['Time Out'] = df['Time Out'].astype(object) 
                df.at[idx[-1], 'Time Out'] = now.strftime("%H:%M:%S")
                df.at[idx[-1], 'Status'] = 'Completed'
                save_data(df)
                msg_placeholder.error(f"Clocked OUT: {selected_name} at {now.strftime('%H:%M')}")
                st.session_state.staff_select = "" # Reset to blank
                time.sleep(5)
                msg_placeholder.empty()
                st.rerun()
            else:
                st.warning("No active record found.")

with tab2:
    pin_input = st.text_input("Enter Admin PIN", type="password")
    if pin_input == ADMIN_PIN:
        st.subheader("Admin Records (OT/UT Calculated Automatically)")
        display_df = df.copy()
        if not display_df.empty:
            metrics = display_df.apply(calculate_payroll, axis=1, result_type='expand')
            display_df['Hours Worked'] = metrics[0]
            display_df['Overtime'] = metrics[1]
            display_df['Undertime'] = metrics[2]

        edited_df = st.data_editor(
            display_df, 
            num_rows="dynamic", 
            key="payroll_editor",
            disabled=["Hours Worked", "Overtime", "Undertime"], 
            use_container_width=True
        )
        
        if st.button("Save Changes"):
            save_cols = ["Name", "Date", "Time In", "Time Out", "Status"]
            final_save = edited_df[save_cols]
            save_data(final_save)
            st.success("Changes saved. Calculations updated.")
            st.rerun()
    elif pin_input != "":
        st.error("Access Denied.")
