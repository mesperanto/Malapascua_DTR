import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import os
import pytz

# --- CONFIGURATION ---
ADMIN_PIN = "1234" 
SHEET_NAME = "DTR_Database"
TIMEZONE = pytz.timezone('Asia/Manila')

# --- DATA HELPERS ---
@st.cache_data(ttl=60)
def load_crew():
    if not os.path.exists("Crew details.xlsx"):
        return None
    df = pd.read_excel("Crew details.xlsx")
    df.columns = ['Name', 'Job', 'Hired', 'Pay_OT', 'Pay_Night', 'Rate']
    return df

def get_gsheet(sheet_index=0):
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open(SHEET_NAME)
        return spreadsheet.get_worksheet(sheet_index)
    except:
        return None

# --- PAYROLL CALCULATOR ENGINE ---
def calculate_payroll(df_logs, df_crew, start_date=None, end_date=None):
    df_logs['Timestamp'] = pd.to_datetime(df_logs['Timestamp'])
    df_logs['Date'] = df_logs['Timestamp'].dt.date
    
    # Apply Date Filters
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
        
        # Calculations
        ot_hrs = max(0, total_hrs - threshold) if ot_enabled.get(name) == "YES" else 0
        under_hrs = max(0, 8 - total_hrs)
        rate = rates.get(name, 0)
        hourly_rate = rate / 8 # Assuming the rate in Excel is a Daily Rate
        
        ot_pay = ot_hrs * (hourly_rate * 1.25) # 25% premium for OT
        under_deduction = under_hrs * hourly_rate
        total_pay = rate + ot_pay - under_deduction

        summary.append({
            "Date": str(date), 
            "Name": name, 
            "Worked Hours": round(total_hrs, 2),
            "OT Hours": round(ot_hrs, 2), 
            "Undertime Hours": round(under_hrs, 2), 
            "Daily Rate": rate,
            "OT Pay": round(ot_pay, 2),
            "Deductions": round(under_deduction, 2),
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
        selected_name = st.selectbox("Select your Name", staff_names)
        
        if selected_name:
            now_manila = datetime.now(TIMEZONE)
            ts_str = now_manila.strftime("%Y-%m-%d %H:%M:%S")
            time_display = now_manila.strftime("%H:%M:%S")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("TIME IN", use_container_width=True, type="primary"):
                    sheet = get_gsheet(0)
                    sheet.append_row([selected_name, ts_str, "IN", "Live"])
                    st.success(f"✅ Time IN recorded at {time_display}")
            
            with col2:
                if st.button("TIME OUT", use_container_width=True):
                    sheet = get_gsheet(0)
                    sheet.append_row([selected_name, ts_str, "OUT", "Live"])
                    
                    # Logic to show duration immediately
                    raw_data = pd.DataFrame(sheet.get_all_records())
                    user_today = raw_data[(raw_data['Name'] == selected_name)]
                    user_today['Timestamp'] = pd.to_datetime(user_today['Timestamp'])
                    user_today = user_today[user_today['Timestamp'].dt.date == now_manila.date()]
                    
                    # Calculate duration for display
                    ins = user_today[user_today['Status'] == 'IN']['Timestamp'].tolist()
                    outs = user_today[user_today['Status'] == 'OUT']['Timestamp'].tolist()
                    total_today = 0
                    for i in range(min(len(ins), len(outs))):
                        total_today += (outs[i] - ins[i]).total_seconds() / 3600
                    
                    st.warning(f"✅ Time OUT recorded at {time_display}")
                    st.info(f"📊 Total worked today: {round(total_today, 2)} hours")

with tab2:
    if st.text_input("Enter Admin PIN", type="password") == ADMIN_PIN:
        st.success("Admin Access Granted")
        
        # 1. Date Range Filter
        st.subheader("📅 Report Filters")
        col_start, col_end = st.columns(2)
        with col_start:
            d_start = st.date_input("From Date", datetime.now(TIMEZONE) - timedelta(days=7))
        with col_end:
            d_end = st.date_input("To Date", datetime.now(TIMEZONE))

        sheet_main = get_gsheet(0)
        if sheet_main:
            raw_logs = pd.DataFrame(sheet_main.get_all_records())
            
            if not raw_logs.empty:
                payroll_report = calculate_payroll(raw_logs, crew_df, d_start, d_end)
                
                st.subheader(f"💵 Payroll Report ({d_start} to {d_end})")
                st.dataframe(payroll_report, use_container_width=True)
                
                # 2. Sync to Spreadsheet Button
                if st.button("🔄 Sync Calculations to Google Sheets"):
                    sheet_summary = get_gsheet(1) # Connects to the second tab
                    if sheet_summary:
                        sheet_summary.clear() # Clear old summary
                        sheet_summary.update([payroll_report.columns.values.tolist()] + payroll_report.values.tolist())
                        st.success("Data synced to 'Payroll_Summary' tab!")
                
                # 3. Download Button
                csv = payroll_report.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download CSV Report",
                    data=csv,
                    file_name=f"Payroll_{d_start}_to_{d_end}.csv",
                    mime="text/csv"
                )
