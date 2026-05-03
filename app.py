import streamlit as st
import pandas as pd
from datetime import datetime
import os

# 1. HEADER
st.set_page_config(page_title="Malapascua DTR")
st.title("Malapascua - Daily Time Record")

FILE_PATH = "dtr_log.csv"

# Load or create data
if os.path.exists(FILE_PATH):
    df = pd.read_csv(FILE_PATH)
else:
    df = pd.DataFrame(columns=["Name", "Date", "Time In", "Time Out", "Status"])

# 2. FULL STAFF LIST (Visible at all times)
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

tab1, tab2 = st.tabs(["Attendance", "Admin (Edit/Delete)"])

with tab1:
    selected_name = st.selectbox("Select Staff Name:", staff_names)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("TIME IN", type="primary", use_container_width=True):
            now = datetime.now()
            new_row = {"Name": selected_name, "Date": now.strftime("%Y-%m-%d"), "Time In": now.strftime("%H:%M:%S"), "Time Out": "", "Status": "Active"}
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_csv(FILE_PATH, index=False)
            st.success(f"{selected_name} Timed In at {now.strftime('%H:%M:%S')}")

    with col2:
        if st.button("TIME OUT", use_container_width=True):
            idx = df.index[(df['Name'] == selected_name) & (df['Status'] == 'Active')]
            if not idx.empty:
                tout = datetime.now().strftime("%H:%M:%S")
                df.at[idx[-1], 'Time Out'] = tout
                df.at[idx[-1], 'Status'] = 'Completed'
                df.to_csv(FILE_PATH, index=False)
                st.error(f"{selected_name} Timed Out at {tout}")
            else:
                st.warning("No active 'Time In' found.")

with tab2:
    st.subheader("Edit or Delete Records")
    # 3. EDIT/DELETE TABLE
    # This allows you to click any cell to edit or select rows to delete
    edited_df = st.data_editor(df, num_rows="dynamic", key="dtr_editor")
    
    if st.button("Save Changes"):
        edited_df.to_csv(FILE_PATH, index=False)
        st.success("Records updated!")
