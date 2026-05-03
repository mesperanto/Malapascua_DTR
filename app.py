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
    # Skips the first row based on your Excel structure
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

# --- PAYROLL ENGINE (Hourly Rate Logic) ---
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
        
        h_rate = rates.get(name, 0)
        # Final pay calculation: Hours worked * Rate
        # Includes a net balance vs an 8-hour shift
        actual_pay = total_hrs * h_rate
        if total_hrs > 8 and ot_enabled.get(name) == "YES":
            actual_pay += (total_hrs - 8) * h_rate * 0.25 # 25% OT Premium
            
        summary.append({
            "Date": str(date), "Name": name, "Worked Hours": round(total_hrs, 2),
            "Hourly Rate": h_rate, "Final Pay": round(actual_pay, 2),
            "Net vs 8h": round(actual_pay - (8 * h_rate), 2)
        })
    return pd.DataFrame(summary)

# --- UI SETUP ---
st.set_page_config(page_title="Malapascua DTR", layout="centered")

# Initialize a 'submitted' state to handle the 5-second screen
if 'submitted' not in st.session_state:
    st.session_state.submitted = False
if 'msg' not in st.session_state:
    st.session_state.msg = ""

tab1, tab2 = st.tabs(["🕒 Staff Clock-In", "🔐 Admin Dashboard"])

with tab1:
    placeholder = st.empty() # This container allows us to wipe the screen
    
    if st.session_state.submitted:
        # 1. Display ONLY hh:mm for 5 seconds
        with placeholder.container():
            st.markdown(f"<h1 style='text-align: center; color: green;'>{st.session_state.msg}</h1>", unsafe_allow_html=True)
            time.sleep(5)
            # 2. Clear state and reset
            st.session_state.submitted = False
            st.session_state.msg = ""
            st.rerun()
    else:
        # Normal Clock-in UI
        with placeholder.container():
            crew_df = load_crew()
            if crew_df is not None:
                staff_names = [""] + sorted(crew_df['Name'].tolist())
                # Using a key that we can clear
                selected_name = st.selectbox("Select your Name", staff_names, key="name_selector")
                
                if selected_name:
                    now = datetime.now(TIMEZONE)
                    display_time = now.strftime("%H:%M") # hh:mm format
                    db_ts = now.strftime("%Y-%m-%d %H:%M:%S")
                    
                    col1, col2 = st.columns(2)
                    ss = get_spreadsheet()
                    main_sheet = ss.get_worksheet(0)

                    if col1.button("TIME IN", use_container_width=True, type="primary"):
                        main_sheet.append_row([selected_name, db_ts, "IN", "Live"])
                        st.session_state.msg = f"Time IN: {display_time}"
                        st.session_state.submitted = True
                        st.rerun()

                    if col2.button("TIME OUT", use_container_width=True):
                        main_sheet.append_row([selected_name, db_ts, "OUT", "Live"])
                        st.session_state.msg = f"Time OUT: {display_time}"
                        st.session_state.submitted = True
                        st.rerun()

with tab2:
    if st.text_input("Admin PIN", type="password") == ADMIN_PIN:
        st.success("Access Granted")
        d_start = st.date_input("From", datetime.now(TIMEZONE) - timedelta(days=7))
        d_end = st.date_input("To", datetime.now(TIMEZONE))
        
        ss = get_spreadsheet()
        raw_logs = pd.DataFrame(ss.get_worksheet(0).get_all_records())
        if not raw_logs.empty:
            report = calculate_payroll(raw_logs, load_crew(), d_start, d_end)
            st.dataframe(report, use_container_width=True)
            
            if st.button("🔄 Sync to 'Payroll_Summary'"):
                try:
                    try: sheet_summary = ss.worksheet("Payroll_Summary")
                    except: sheet_summary = ss.add_worksheet(title="Payroll_Summary", rows="100", cols="20")
                    sheet_summary.clear()
                    sheet_summary.update([report.columns.tolist()] + report.astype(str).values.tolist())
                    st.success("Synced!")
                except Exception as e: st.error(f"Error: {e}")
