import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- 1. APP CONFIG & HEADER ---
st.set_page_config(page_title="Malapascua DTR", layout="centered")
st.title("Malapascua - Daily Time Record") #[cite: 11]

FILE_PATH = "dtr_log.csv"
ADMIN_PIN = "1234" 
STANDARD_HOURS = 8.0 #[cite: 11]

# --- 2. DATA PERSISTENCE & TYPE SAFETY ---
def load_data():
    if os.path.exists(FILE_PATH):
        # Explicitly load columns as strings to prevent Pandas type-guessing crashes[cite: 11]
        return pd.read_csv(FILE_PATH, dtype={'Time In': str, 'Time Out': str, 'Status': str})
    return pd.DataFrame(columns=["Name", "Date", "Time In", "Time Out", "Status"])

def save_data(dataframe):
    # Ensure no index is saved to the CSV
    dataframe.to_csv(FILE_PATH, index=False)

df = load_data()

# --- 3. STAFF LIST (Names stay visible & default to blank) ---
#[cite: 1, 10]
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

# --- 4. PAYROLL LOGIC (Re-processed on load) ---
def calculate_payroll_metrics(row):
    # Ensure we handle empty or non-string values gracefully[cite: 11]
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
        except Exception:
            return 0.0, 0.0, 0.0
    return 0.0, 0.0, 0.0

# --- 5. TABS INTERFACE ---
tab1, tab2 = st.tabs(["🕒 Attendance", "⚙️ Admin (PIN Required)"])

with tab1:
    # Default to blank[cite: 11]
    selected_name = st.selectbox("Select Staff Name:", staff_names, index=0)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("TIME IN", type="primary", use_container_width=True):
            if selected_name == "":
                st.warning("Please select a name.")
            else:
                now = datetime.now()
                new_entry = {
                    "Name": selected_name, 
                    "Date": now.strftime("%Y-%m-%d"), 
                    "Time In": now.strftime("%H:%M:%S"), 
                    "Time Out": "", 
                    "Status": "Active"
                }
                df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
                save_data(df)
                st.success(f"Clocked In: {selected_name}")

    with col2:
        if st.button("TIME OUT", use_container_width=True):
            if selected_name == "":
                st.warning("Please select a name.")
            else:
                # Find the most recent 'Active' record for this user
                idx = df.index[(df['Name'] == selected_name) & (df['Status'] == 'Active')]
                if not idx.empty:
                    # CRITICAL: Set type to object to prevent TypeError on string insertion[cite: 11]
                    df['Time Out'] = df['Time Out'].astype(object)
                    df.at[idx[-1], 'Time Out'] = datetime.now().strftime("%H:%M:%S")
                    df.at[idx[-1], 'Status'] = 'Completed'
                    save_data(df)
                    st.error(f"Clocked Out: {selected_name}")
                else:
                    st.warning(f"No active record found for {selected_name}.")

with tab2:
    # PIN Protection[cite: 11]
    pin_input = st.text_input("Enter Admin PIN", type="password")
    
    if pin_input == ADMIN_PIN:
        st.subheader("Data Management & Payroll Summary")
        
        # Apply calculations to current dataframe for display
        display_df = df.copy()
        if not display_df.empty:
            metrics = display_df.apply(calculate_payroll_metrics, axis=1, result_type='expand')
            display_df['Hours Worked'] = metrics[0]
            display_df['Overtime'] = metrics[1]
            display_df['Undertime'] = metrics[2]

        # Editable Table[cite: 11]
        edited_df = st.data_editor(
            display_df, 
            num_rows="dynamic", 
            key="payroll_editor",
            use_container_width=True
        )
        
        if st.button("Save Changes"):
            # Strip the calculated columns before saving to keep CSV clean
            core_cols = ["Name", "Date", "Time In", "Time Out", "Status"]
            final_to_save = edited_df[core_cols]
            save_data(final_to_save)
            st.success("Database updated successfully.")
            st.rerun() # Refresh to update calculations
            
    elif pin_input != "":
        st.error("Invalid PIN. Access restricted.")
