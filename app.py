import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import os
import pytz
import time

# --- CONFIGURATION ---
ADMIN_PIN = "1234" 
SHEET_NAME = "DTR_Database"
TIMEZONE = pytz.timezone('Asia/Manila')

# --- DATA HELPERS ---
@st.cache_data(ttl=60)
def load_crew():
    if not os.path.exists("Crew details.xlsx"):
        return None
    # Skips the first row as per the Excel structure found in your files
    df = pd.read_excel("Crew details.xlsx", skiprows=1)
    df.columns = ['Name', 'Job', 'Hired', 'Pay_OT', 'Pay_Night', 'Rate']
    return df

def get_spreadsheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        return client.open(SHEET_NAME)
    except Exception as e:
        st.error(f"Spreadsheet Access Error: {e}")
        return None

# --- PAYROLL CALCULATOR ENGINE ---
def calculate_payroll(df_logs, df_crew, start_date=None, end_date=None):
    df_logs['Timestamp'] = pd.to_datetime(df_logs['Timestamp'])
    df_logs['Date'] = df_logs['Timestamp'].dt.date
    
    if start_date and end_date:
        df_logs = df_logs[(df_logs['Date'] >= start_date) & (df_logs['Date'] <= end_date)]
    
    rates = df_crew.set_index('Name')['Rate'].to_dict()
    ot_enabled = df_crew.set_index('Name')['Pay_OT'].to_dict()
    
    summary = []
    for (name, date), group in df_logs.groupby(['Name', 'Date']):
        group = group.sort_values('Timestamp')
        ins = group[group['Status'] == 'IN']['Timestamp'].tolist()
        outs = group[group['Status'] == 'OUT']['Timestamp'].tolist()
        
        total_hrs = 0
        for i in range(min(len(ins), len(outs))):
            total_hrs += (outs[i] - ins[i]).total_seconds() / 3600
        
        hourly_rate = rates.get(name, 0)
        work_delta = total_hrs - 8 
        
        if work_delta > 0 and ot_enabled.get(name) == "YES":
            actual_pay = (8 * hourly_rate) + (work_delta * hourly_rate * 1.25)
        else:
            actual_pay = total_hrs * hourly_rate

        standard_day_target = 8 * hourly_rate
        net_vs_standard = actual_pay - standard_day_target

        summary.append({
            "Date": str(date), 
            "Name": name, 
            "Worked Hours": round(total_hrs, 2),
            "Hourly Rate": hourly_rate,
            "Standard 8h Pay": round(standard_day_target, 2),
            "Actual Earned": round(actual_pay, 2),
            "Net Balance (Pay)": round(net_vs_standard, 2)
        })
    return pd.DataFrame(summary)

# --- UI SETUP ---
st.set_page_config(page_title="Malapascua DTR", layout="wide")

# Initialize session state for UI reset
if 'show_conf' not in st.session_state:
    st.session_state.show_conf = False
if 'conf_msg' not in st.session_state:
    st.session_state.conf_msg = ""

st.title("Malapascua DTR & Payroll System")

tab1, tab2 = st.tabs(["🕒 Staff Clock-In", "🔐 Admin Dashboard"])

with tab1:
    # If a confirmation is showing, display it and wait
    if st.session_state.show_conf:
        st.success(st.session_state.conf_msg)
        progress_bar = st.progress(0)
        for i in range(100):
            time.sleep(0.05) # Total 5 seconds
            progress_bar.progress(i + 1)
        
        # Reset and reload
        st.session_state.show_conf = False
        st.session_state.conf_msg = ""
        st.rerun()

    crew_df = load_crew()
    if crew_df is not None:
        staff_names = [""] + crew_df['Name'].tolist()
        
        # Name selector - resetting occurs via the st.rerun() logic above
        selected_name = st.selectbox("Select your Name", staff_names, key="staff_select_box")
        
        if selected_name != "":
            now_manila = datetime.now(TIMEZONE)
            # Full timestamp for database
            db_ts = now_manila.strftime("%Y-%m-%d %H:%M:%S")
            # Simplified display for staff
            display_time = now_manila.strftime("%H:%M")
            
            col1, col2 = st.columns(2)
            ss = get_spreadsheet()
            main_sheet = ss.get_worksheet(0)

            if col1.button("TIME IN", use_container_width=True, type="primary"):
                main_sheet.append_row([selected_name, db_ts, "IN", "Live"])
                st.session_state.conf_msg = f"✅ {selected_name} - Time IN at {display_time}"
                st.session_state.show_conf = True
                st.rerun()
            
            if col2.button("TIME OUT", use_container_width=True):
                main_sheet.append_row([selected_name, db_ts, "OUT", "Live"])
                st.session_state.conf_msg = f"✅ {selected_name} - Time OUT at {display_time}"
                st.session_state.show_conf = True
                st.rerun()

with tab2:
    if st.text_input("Enter Admin PIN", type="password") == ADMIN_PIN:
        st.success("Admin Access Granted")
        
        d_start = st.date_input("From", datetime.now(TIMEZONE) - timedelta(days=7))
        d_end = st.date_input("To", datetime.now(TIMEZONE))

        ss = get_spreadsheet()
        sheet_main = ss.get_worksheet(0)
        
        if sheet_main:
            raw_logs = pd.DataFrame(sheet_main.get_all_records())
            if not raw_logs.empty:
                payroll_report = calculate_payroll(raw_logs, crew_df, d_start, d_end)
                st.dataframe(payroll_report, use_container_width=True)
                
                if st.button("🔄 Sync to 'Payroll_Summary'"):
                    try:
                        try:
                            sheet_summary = ss.worksheet("Payroll_Summary")
                        except:
                            sheet_summary = ss.add_worksheet(title="Payroll_Summary", rows="100", cols="20")
                        
                        sheet_summary.clear()
                        data = [payroll_report.columns.tolist()] + payroll_report.astype(str).values.tolist()
                        sheet_summary.update(data)
                        st.success("Synced to Google Sheets!")
                    except Exception as e:
                        st.error(f"Sync failed: {e}")
