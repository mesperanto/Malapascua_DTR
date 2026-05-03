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
        st.error(f"Spreadsheet Error: {e}")
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
        
        sessions = len(ins)
        threshold = 8 if sessions >= 2 else 9
        hourly_rate = rates.get(name, 0)
        
        # LOGIC: If they work less than 8h, result should be negative.
        # We calculate the "Delta" from a standard 8-hour shift.
        work_delta = total_hrs - 8 
        
        # OT Calculation (Only if Delta is positive AND person is OT eligible)
        # They get paid their hourly rate for the 8 hours, 
        # plus the extra hours at 1.25x.
        
        if work_delta > 0:
            # Overtime logic
            if ot_enabled.get(name) == "YES":
                # First 8 hours at normal rate + extra hours at 1.25 rate
                actual_pay = (8 * hourly_rate) + (work_delta * hourly_rate * 1.25)
            else:
                # No OT pay, just flat rate for all hours worked
                actual_pay = total_hrs * hourly_rate
        else:
            # Undertime logic: They just get paid for the hours they actually worked
            # which will be less than the "Standard 8h pay"
            actual_pay = total_hrs * hourly_rate

        # To show the "Negative" balance you requested:
        # This shows how much they are 'down' or 'up' compared to a standard day's pay
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

# Initialize Session State for the Name Dropdown
if 'name_index' not in st.session_state:
    st.session_state.name_index = 0

def reset_name():
    st.session_state.name_index = 0

st.title("Malapascua DTR & Payroll")

tab1, tab2 = st.tabs(["🕒 Staff Clock-In", "🔐 Admin Dashboard"])

with tab1:
    crew_df = load_crew()
    if crew_df is not None:
        staff_names = [""] + crew_df['Name'].tolist()
        
        # Use session state index to force the dropdown back to index 0
        selected_name = st.selectbox(
            "Select your Name", 
            staff_names, 
            index=st.session_state.name_index,
            key="name_selector"
        )
        
        if selected_name != "":
            now_manila = datetime.now(TIMEZONE)
            ts_str = now_manila.strftime("%Y-%m-%d %H:%M:%S")
            
            col1, col2 = st.columns(2)
            ss = get_spreadsheet()
            main_sheet = ss.get_worksheet(0)

            if col1.button("TIME IN", use_container_width=True, type="primary"):
                main_sheet.append_row([selected_name, ts_str, "IN", "Live"])
                st.success(f"✅ Time IN: {ts_str}")
                time.sleep(2)
                st.session_state.name_index = 0 # Reset the index
                st.rerun()
            
            if col2.button("TIME OUT", use_container_width=True):
                main_sheet.append_row([selected_name, ts_str, "OUT", "Live"])
                st.warning(f"✅ Time OUT: {ts_str}")
                time.sleep(4)
                st.session_state.name_index = 0 # Reset the index
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
                        st.success("Synced!")
                    except Exception as e:
                        st.error(f"Error: {e}")
