import streamlit as st
import pandas as pd
from datetime import datetime
import time
import os

# --- APP CONFIG & HEADER ---
st.set_page_config(page_title="Malapascua DTR", layout="centered")
st.title("Malapascua - Daily Time Record") #

FILE_PATH = "dtr_log.csv"
ADMIN_PIN = "1234" 
TARGET_WORK_HOURS = 8.0 # Standard required work time

# --- DATA LOADING ---
def load_data():
    if os.path.exists(FILE_PATH):
        # Explicitly load as strings to prevent Pandas type errors
        return pd.read_csv(FILE_PATH, dtype={'Time In': str, 'Time Out': str, 'Status': str})
    return pd.DataFrame(columns=["Name", "Date", "Time In", "Time Out", "Status"])

df = load_data()

# --- STAFF LIST ---
# Default to blank
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
] #

# --- PAYROLL LOGIC (Break & OT/UT Rules) ---
def calculate_daily_metrics(group):
    total_work_hours = 0.0
    valid_entries = group[group['Status'] == 'Completed']
    
    if valid_entries.empty:
        return pd.Series([0.0, 0.0, 0.0], index=['Hours Worked', 'Overtime', 'Undertime'])

    durations = []
    for _, row in valid_entries.iterrows():
        try:
            fmt = "%H:%M:%S"
            t_in = datetime.strptime(row['Time In'], fmt)
            t_out = datetime.strptime(row['Time Out'], fmt)
            durations.append((t_out - t_in).total_seconds() / 3600)
        except:
            continue

    # Logic: If only one In/Out pair, subtract 1 hour for the break.
    # If multiple pairs, the gaps between them ARE the break, so just sum the work duration.
    if len(durations) == 1:
        total_work_hours = max(0.0, durations[0] - 1.0)
    else:
        total_work_hours = sum(durations)

    ot = max(0.0, total_work_hours - TARGET_WORK_HOURS)
    ut = max(0.0, TARGET_WORK_HOURS - total_work_hours) if total_work_hours < TARGET_WORK_HOURS else 0.0

    return pd.Series([round(total_work_hours, 2), round(ot, 2), round(ut, 2)], 
                     index=['Hours Worked', 'Overtime', 'Undertime'])

# --- ATTENDANCE TAB ---
tab1, tab2 = st.tabs(["🕒 Attendance", "⚙️ Admin (PIN Required)"])

with tab1:
    selected_name = st.selectbox("Select Staff Name:", staff_names, index=0)
    
    # Placeholder for the 5-second confirmation message
    msg_placeholder = st.empty()
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("TIME IN", type="primary", use_container_width=True):
            if selected_name == "":
                st.warning("Please select a name.")
            else:
                now = datetime.now()
                time_str = now.strftime("%H:%M:%S")
                new_row = {"Name": selected_name, "Date": now.strftime("%Y-%m-%d"), 
                           "Time In": time_str, "Time Out": "", "Status": "Active"}
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv(FILE_PATH, index=False)
                
                # 5-second message
                msg_placeholder.success(f"Clocked In: {selected_name} at {time_str}")
                time.sleep(5)
                msg_placeholder.empty()

    with col2:
        if st.button("TIME OUT", use_container_width=True):
            if selected_name == "":
                st.warning("Please select a name.")
            else:
                idx = df.index[(df['Name'] == selected_name) & (df['Status'] == 'Active')]
                if not idx.empty:
                    now = datetime.now()
                    time_str = now.strftime("%H:%M:%S")
                    # Type Safety Fix
                    df['Time Out'] = df['Time Out'].astype(object)
                    df.at[idx[-1], 'Time Out'] = time_str
                    df.at[idx[-1], 'Status'] = 'Completed'
                    df.to_csv(FILE_PATH, index=False)
                    
                    # 5-second message
                    msg_placeholder.error(f"Clocked Out: {selected_name} at {time_str}")
                    time.sleep(5)
                    msg_placeholder.empty()
                else:
                    st.warning("No active record found.")

# --- ADMIN TAB ---
with tab2:
    pin_input = st.text_input("Enter Admin PIN", type="password")
    if pin_input == ADMIN_PIN:
        st.subheader("Payroll Summary & Data Editor")
        
        # Merge metrics back to display_df for admin review
        if not df.empty:
            # Group by Name and Date to apply the "1-hour break" logic correctly
            metrics_df = df.groupby(['Name', 'Date']).apply(calculate_daily_metrics).reset_index()
            display_df = pd.merge(df, metrics_df, on=['Name', 'Date'], how='left')
        else:
            display_df = df.copy()

        edited_df = st.data_editor(display_df, num_rows="dynamic", key="admin_editor")
        
        if st.button("Save Changes"):
            # Only save core columns
            core_cols = ["Name", "Date", "Time In", "Time Out", "Status"]
            final_df = edited_df[core_cols]
            final_df.to_csv(FILE_PATH, index=False)
            st.success("Changes saved. Refreshing calculations...")
            st.rerun()
    elif pin_input != "":
        st.error("Incorrect PIN.")
