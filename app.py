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
    # Skip original header row to get to the actual column names/data
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
        
        sessions = len(ins)
        threshold = 8 if sessions >= 2 else 9
        
        # Calculations (Rates are Hourly)
        ot_hrs = max(0, total_hrs - threshold) if ot_enabled.get(name) == "YES" else 0
        under_hrs = max(0, 8 - total_hrs)
        
        hourly_rate = rates.get(name, 0)
        
        base_pay = total_hrs * hourly_rate
        ot_pay = ot_hrs * (hourly_rate * 0.25) # Extra 25% premium for the OT hours
        total_pay = base_pay + ot_pay

        summary.append({
            "Date": str(date), 
            "Name": name, 
            "Worked Hours": round(total_hrs, 2),
            "OT Hours": round(ot_hrs, 2), 
            "Undertime Hours": round(under_hrs, 2), 
            "Hourly Rate": hourly_rate,
            "Base Pay": round(base_pay, 2),
            "OT Premium": round(ot_pay, 2),
            "Final Pay": round(total_pay, 2)
        })
    return pd.DataFrame(summary)

# --- UI SETUP ---
st.set_page_config(page_title="Malapascua DTR", layout="wide")
st.title("Malapascua DTR & Payroll System")

tab1, tab2 = st.tabs(["🕒 Staff Clock-In", "🔐 Admin Dashboard"])

with tab1:
    crew_df = load_crew()
    if crew_df is not None:
        staff_names = [""] + crew_df['Name'].tolist()
        # The key helps Streamlit track state for the reset
        selected_name = st.selectbox("Select your Name", staff_names, key="staff_select")
        
        if selected_name != "":
            now_manila = datetime.now(TIMEZONE)
            ts_str = now_manila.strftime("%Y-%m-%d %H:%M:%S")
            time_display = now_manila.strftime("%H:%M:%S")
            
            col1, col2 = st.columns(2)
            ss = get_spreadsheet()
            main_sheet = ss.get_worksheet(0)

            with col1:
                if st.button("TIME IN", use_container_width=True, type="primary"):
                    main_sheet.append_row([selected_name, ts_str, "IN", "Live"])
                    st.success(f"✅ Time IN recorded at {time_display}")
                    time.sleep(3) # Give them 3 seconds to read
                    st.rerun()
            
            with col2:
                if st.button("TIME OUT", use_container_width=True):
                    main_sheet.append_row([selected_name, ts_str, "OUT", "Live"])
                    
                    raw_data = pd.DataFrame(main_sheet.get_all_records())
                    user_today = raw_data[(raw_data['Name'] == selected_name)]
                    user_today['Timestamp'] = pd.to_datetime(user_today['Timestamp'])
                    user_today = user_today[user_today['Timestamp'].dt.date == now_manila.date()]
                    
                    ins = user_today[user_today['Status'] == 'IN']['Timestamp'].tolist()
                    outs = user_today[user_today['Status'] == 'OUT']['Timestamp'].tolist()
                    total_today = 0
                    for i in range(min(len(ins), len(outs))):
                        total_today += (outs[i] - ins[i]).total_seconds() / 3600
                    
                    st.warning(f"✅ Time OUT recorded at {time_display}")
                    st.info(f"📊 Total worked today: {round(total_today, 2)} hours")
                    time.sleep(5) # Give more time to see the hour summary
                    st.rerun()

with tab2:
    if st.text_input("Enter Admin PIN", type="password") == ADMIN_PIN:
        st.success("Admin Access Granted")
        
        st.subheader("📅 Report Filters")
        col_start, col_end = st.columns(2)
        with col_start:
            d_start = st.date_input("From Date", datetime.now(TIMEZONE) - timedelta(days=7))
        with col_end:
            d_end = st.date_input("To Date", datetime.now(TIMEZONE))

        ss = get_spreadsheet()
        sheet_main = ss.get_worksheet(0)
        
        if sheet_main:
            raw_logs = pd.DataFrame(sheet_main.get_all_records())
            
            if not raw_logs.empty:
                payroll_report = calculate_payroll(raw_logs, crew_df, d_start, d_end)
                st.subheader(f"💵 Payroll Report ({d_start} to {d_end})")
                st.dataframe(payroll_report, use_container_width=True)
                
                if st.button("🔄 Sync Calculations to 'Payroll_Summary' Tab"):
                    try:
                        try:
                            sheet_summary = ss.worksheet("Payroll_Summary")
                        except gspread.exceptions.WorksheetNotFound:
                            sheet_summary = ss.add_worksheet(title="Payroll_Summary", rows="100", cols="20")
                        
                        sheet_summary.clear()
                        # Convert all to string to prevent sync errors
                        data_to_push = [payroll_report.columns.values.tolist()] + payroll_report.astype(str).values.tolist()
                        sheet_summary.update(data_to_push)
                        st.success("Successfully synced to Google Sheets!")
                    except Exception as sync_err:
                        st.error(f"Sync failed: {sync_err}")
                
                csv = payroll_report.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download CSV Report", csv, f"Payroll_{d_start}_{d_end}.csv", "text/csv")
