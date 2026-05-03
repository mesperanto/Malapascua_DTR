import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import os

# --- ERROR HANDLING WRAPPER ---
try:
    # --- CONFIGURATION ---
    ADMIN_PIN = "1234" 
    SHEET_NAME = "DTR_Database"

    # Load Crew Details
    @st.cache_data
    def load_crew():
        if not os.path.exists("Crew details.xlsx"):
            st.error("❌ ERROR: 'Crew details.xlsx' not found in GitHub. Please upload it!")
            return None
        df = pd.read_excel("Crew details.xlsx")
        df.columns = ['Name', 'Job', 'Hired', 'Pay_OT', 'Pay_Night', 'Rate']
        return df

    crew_df = load_crew()
    
    if crew_df is not None:
        staff_list = crew_df['Name'].dropna().unique().tolist()

        # Google Sheets Connection
        def get_gsheet():
            try:
                scope = ["https://www.googleapis.com/auth/spreadsheets"]
                # This checks if your Secrets are set up correctly
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
        st.title("Sipadan Borneo DTR") # Use your preferred name here

        tab1, tab2 = st.tabs(["🕒 Staff Clock-In", "🔐 Admin Dashboard"])

        # --- TAB 1: STAFF CLOCK-IN ---
        with tab1:
            selected_name = st.selectbox("Select your Name", [""] + staff_list)
            if selected_name:
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("CLOCK IN", use_container_width=True):
                        log_time(selected_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "IN")
                        st.success(f"IN at {datetime.now().strftime('%H:%M')}")
                with col2:
                    if st.button("CLOCK OUT", use_container_width=True):
                        log_time(selected_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "OUT")
                        st.warning(f"OUT at {datetime.now().strftime('%H:%M')}")

        # --- TAB 2: ADMIN DASHBOARD ---
        with tab2:
            input_pin = st.text_input("Enter Admin PIN", type="password")
            if input_pin == ADMIN_PIN:
                st.success("Admin Access Granted")
                sheet = get_gsheet()
                if sheet:
                    # (Rest of the admin code for edit/delete goes here...)
                    st.write("Admin features active.")
            elif input_pin != "":
                st.error("Access Denied")

except Exception as main_error:
    st.error(f"⚠️ A Critical Error Occurred: {main_error}")
