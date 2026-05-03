import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import os
import pytz

# --- ERROR HANDLING WRAPPER ---
try:
    # --- CONFIGURATION ---
    ADMIN_PIN = "1234" 
    SHEET_NAME = "DTR_Database"
    TIMEZONE = pytz.timezone('Asia/Manila')

    # Load Crew Details
    @st.cache_data
    def load_crew():
        if not os.path.exists("Crew details.xlsx"):
            st.error("❌ ERROR: 'Crew details.xlsx' not found in GitHub. Please upload it!")
            return None
        df = pd.read_excel("Crew details.xlsx")
        # Ensure column alignment with your file structure
        df.columns = ['Name', 'Job', 'Hired', 'Pay_OT', 'Pay_Night', 'Rate']
        return df

    crew_df = load_crew()
    
    if crew_df is not None:
        staff_list = crew_df['Name'].dropna().unique().tolist()

        # Google Sheets Connection with Expanded Scopes
        def get_gsheet():
            try:
                # Adding Drive scope fixes the 403 insufficient authentication error
                scope = [
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive"
                ]
                creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
                client = gspread.authorize(creds)
                return client.open(SHEET_NAME).sheet1
            except Exception as e:
                st.error(f"❌ Google Connection Error: {e}")
                return None

        def log_time(name, timestamp, status, source="Live"):
            sheet = get_gsheet()
            if sheet:
                sheet.append_row([name, str(timestamp), status, source])

        # --- UI SETUP ---
        st.set_page_config(page_title="Malapascua DTR", layout="wide")
        st.title("Malapascua DTR") 

        tab1, tab2 = st.tabs(["🕒 Staff Clock-In", "🔐 Admin Dashboard"])

        # --- TAB 1: STAFF CLOCK-IN ---
        with tab1:
            selected_name = st.selectbox("Select your Name", [""] + staff_list)
            
            if selected_name:
                # Get current time in Manila
                now_manila = datetime.now(TIMEZONE)
                ts_str = now_manila.strftime("%Y-%m-%d %H:%M:%S")
                display_time = now_manila.strftime("%H:%M")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("CLOCK IN", use_container_width=True):
                        log_time(selected_name, ts_str, "IN")
                        st.success(f"IN at {display_time}")
                with col2:
                    if st.button("CLOCK OUT", use_container_width=True):
                        log_time(selected_name, ts_str, "OUT")
                        st.warning(f"OUT at {display_time}")

        # --- TAB 2: ADMIN DASHBOARD ---
        with tab2:
            input_pin = st.text_input("Enter Admin PIN", type="password")
            if input_pin == ADMIN_PIN:
                st.success("Admin Access Granted")
                sheet = get_gsheet()
                
                if sheet:
                    # 1. ADD NEW RECORD MANUALLY
                    with st.expander("➕ Add Manual Entry"):
                        m_name = st.selectbox("Staff Name", staff_list)
                        m_date = st.date_input("Date")
                        m_time = st.time_input("Time")
                        m_status = st.radio("Status", ["IN", "OUT"], horizontal=True)
                        if st.button("Save Entry"):
                            dt = datetime.combine(m_date, m_time)
                            log_time(m_name, dt, m_status, source="Manual")
                            st.rerun()

                    # 2. EDIT / DELETE RECORDS
                    st.divider()
                    st.subheader("Manage Existing Records")
                    raw_data = sheet.get_all_records()
                    
                    if raw_data:
                        df_logs = pd.DataFrame(raw_data)
                        # Create a visual ID based on row number (gspread is 1-indexed, +1 for header)
                        df_logs['ID'] = range(2, len(df_logs) + 2)
                        
                        selected_id = st.selectbox("Select Log ID to Edit/Delete", df_logs['ID'].tolist()[::-1])
                        row_to_edit = df_logs[df_logs['ID'] == selected_id].iloc[0]
                        
                        st.info(f"Selected: **{row_to_edit['Name']}** | Current Log: **{row_to_edit['Timestamp']}** ({row_to_edit['Status']})")
                        
                        col_del, col_upd = st.columns(2)
                        with col_del:
                            if st.button("🗑️ DELETE RECORD", type="primary", use_container_width=True):
                                sheet.delete_rows(int(selected_id))
                                st.toast("Record Deleted")
                                st.rerun()
                        
                        with col_upd:
                            new_ts = st.text_input("Edit Timestamp", value=row_to_edit['Timestamp'])
                            if st.button("💾 UPDATE RECORD", use_container_width=True):
                                sheet.update_cell(int(selected_id), 2, new_ts)
                                st.toast("Record Updated")
                                st.rerun()

                        st.dataframe(df_logs[['ID', 'Name', 'Timestamp', 'Status', 'Source']].tail(20), use_container_width=True)
            elif input_pin != "":
                st.error("Access Denied")

except Exception as main_error:
    st.error(f"⚠️ A Critical Error Occurred: {main_error}")
