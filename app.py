import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- APP CONFIG & HEADER ---
st.set_page_config(page_title="Malapascua DTR", layout="centered")
st.title("Malapascua - Daily Time Record")

FILE_PATH = "dtr_log.csv"

# --- DATA HANDLING ---
def load_data():
    if os.path.exists(FILE_PATH):
        return pd.read_csv(FILE_PATH)
    return pd.DataFrame(columns=["Name", "Date", "Time In", "Time Out", "Status"])

def save_data(df):
    df.to_csv(FILE_PATH, index=False)

df = load_data()

# --- STAFF LIST ---
# You can expand this list as needed for your team
staff_names = ["Juan Dela Cruz", "Maria Santos", "Ricardo Dalisay", "Marcin Szymanski"]

# --- TABS ---
tab1, tab2 = st.tabs(["🕒 Attendance", "⚙️ Admin Panel"])

with tab1:
    st.subheader("Staff Clock In/Out")
    selected_name = st.selectbox("Select Staff Name", staff_names)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("TIME IN", use_container_width=True, type="primary"):
            # Check if already active
            if not df[(df['Name'] == selected_name) & (df['Status'] == 'Active')].empty:
                st.error(f"{selected_name} is already timed in!")
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
            idx = df.index[(df['Name'] == selected_name) & (df['Status'] == 'Active')]
            if not idx.empty:
                df.at[idx[0], 'Time Out'] = datetime.now().strftime("%H:%M:%S")
                df.at[idx[0], 'Status'] = 'Completed'
                save_data(df)
                st.success(f"Clocked Out: {selected_name}")
            else:
                st.warning(f"No active 'Time In' record for {selected_name}")

with tab2:
    st.subheader("Manage Records")
    
    # Editable Data Table
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        column_config={
            "Status": st.column_config.SelectboxColumn(options=["Active", "Completed"])
        },
        key="dtr_editor"
    )
    
    if st.button("Save Changes to CSV"):
        save_data(edited_df)
        st.toast("Records updated successfully!")
