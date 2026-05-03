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
def load_data():
    if os.path.exists(FILE_PATH):
        # Force string types to avoid the "TypeError: Invalid value" crash
        return pd.read_csv(FILE_PATH, dtype={'Time In': str, 'Time Out': str, 'Status': str})
    return pd.DataFrame(columns=["Name", "Date", "Time In", "Time Out", "Status"])

df = load_data()

# --- STAFF LIST ---
# Added "" at the start so the default selection is blank
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

# --- CALCULATION LOGIC ---
def calculate_metrics(row):
    # Ensure values are strings and not NaN
    t_in_str = str(row.get('Time In', ''))
    t_out_str = str(row.get('Time Out', ''))
    
    if row['Status'] == 'Completed' and t_out_str and t_out_str != 'nan':
        try:
            fmt = "%H:%M:%S"
            t_in = datetime.strptime(t_in_str, fmt)
            t_out = datetime.strptime(t_out_str, fmt)
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
    selected_name = st.selectbox("Select Staff Name:", staff_names, index=0)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("TIME IN", type="primary", use_container_width=True):
            if selected_name == "":
                st.warning("Please select a name first.")
            else:
                now = datetime.now()
                new_row = {
                    "Name": selected_name, 
                    "Date": now.strftime("%Y-%m-%d"), 
                    "Time In": now.strftime("%H:%M:%S"), 
                    "Time Out": "", 
                    "Status": "Active"
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv(FILE_PATH, index=False)
                st.success(f"{selected_name} Timed In.")

    with col2:
        if st.button("TIME OUT", use_container_width=True):
            if selected_name == "":
                st.warning("Please select a name first.")
            else:
                # Find active record for this specific user
                idx = df.index[(df['Name'] == selected_name) & (df['Status'] == 'Active')]
                if not idx.empty:
                    # Convert column to object type explicitly before inserting string to prevent TypeErrors
                    df['Time Out'] = df['Time Out'].astype(object)
                    df.at[idx[-1], 'Time Out'] = datetime.now().strftime("%H:%M:%S")
                    df.at[idx[-1], 'Status'] = 'Completed'
                    df.to_csv(FILE_PATH, index=False)
                    st.error(f"{selected_name} Timed Out.")
                else:
                    st.warning("No active 'Time In' found for this person.")

with tab2:
    pin_input = st.text_input("Enter Admin PIN", type="password")
    if pin_input == ADMIN_PIN:
        st.subheader("Payroll Review & Record Management")
        
        display_df = df.copy()
        if not display_df.empty:
            metrics = display_df.apply(calculate_metrics, axis=1, result_type='expand')
            display_df['Hours Worked'] = metrics[0]
            display_df['Overtime'] = metrics[1]
            display_df['Undertime'] = metrics[2]

        edited_df = st.data_editor(display_df, num_rows="dynamic", key="payroll_editor")
        
        if st.button("Save Changes"):
            save_cols = ["Name", "Date", "Time In", "Time Out", "Status"]
            final_df = edited_df[save_cols]
            # Ensure no numeric conversion happens on save
            final_df.to_csv(FILE_PATH, index=False)
            st.success("Changes saved successfully.")
    elif pin_input != "":
        st.error("Incorrect PIN.")
