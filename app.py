import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- APP CONFIG & HEADER ---
st.set_page_config(page_title="Malapascua DTR")
st.title("Malapascua - Daily Time Record") # Requested Header

FILE_PATH = "dtr_log.csv"
ADMIN_PIN = "1234"  # Replace with your actual PIN

# --- DATA LOADING ---
if os.path.exists(FILE_PATH):
    df = pd.read_csv(FILE_PATH)
else:
    df = pd.DataFrame(columns=["Name", "Date", "Time In", "Time Out", "Status"])

# --- FULL STAFF LIST (Names stay visible after Clock Out) ---
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
] # Staff list from your records

# --- TABS ---
tab1, tab2 = st.tabs(["🕒 Attendance", "⚙️ Admin (PIN Required)"])

with tab1:
    selected_name = st.selectbox("Select Staff Name:", staff_names)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("TIME IN", type="primary", use_container_width=True):
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
            st.success(f"Confirmed: {selected_name} Timed In at {now.strftime('%H:%M:%S')}")

    with col2:
        if st.button("TIME OUT", use_container_width=True):
            # Target the last 'Active' entry for this person
            idx = df.index[(df['Name'] == selected_name) & (df['Status'] == 'Active')]
            if not idx.empty:
                tout = datetime.now().strftime("%H:%M:%S")
                df.at[idx[-1], 'Time Out'] = tout
                df.at[idx[-1], 'Status'] = 'Completed'
                df.to_csv(FILE_PATH, index=False)
                st.error(f"Confirmed: {selected_name} Timed Out at {tout}")
            else:
                st.warning(f"No active 'Time In' found for {selected_name}")

with tab2:
    # --- PIN PROTECTION ---
    pin_input = st.text_input("Enter Admin PIN to Edit Records", type="password")
    
    if pin_input == ADMIN_PIN:
        st.subheader("Edit or Delete Records")
        # Admin Edit/Delete table
        edited_df = st.data_editor(df, num_rows="dynamic", key="dtr_editor")
        
        if st.button("Save Changes"):
            edited_df.to_csv(FILE_PATH, index=False)
            st.success("Admin records updated and saved.")
    elif pin_input != "":
        st.error("Incorrect PIN. Access Denied.")
