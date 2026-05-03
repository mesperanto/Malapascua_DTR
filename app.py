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
@st.cache_data
def load_crew():
    if not os.path.exists("Crew details.xlsx"):
        return None
    df = pd.read_excel("Crew details.xlsx")
    df.columns = ['Name', 'Job', 'Hired', 'Pay_OT', 'Pay_Night', 'Rate']
    return df

def get_gsheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        return client.open(SHEET_NAME).sheet1
    except:
        return None

# --- PAYROLL CALCULATOR ENGINE ---
def calculate_payroll(df_logs, df_crew):
    df_logs['Timestamp'] = pd.to_datetime(df_logs['Timestamp'])
    df_logs['Date'] = df_logs['Timestamp'].dt.date
    
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
        
        # Rules logic
        sessions = len(ins)
        threshold = 8 if sessions >= 2 else 9
        
        ot_hrs = max(0, total_hrs - threshold) if ot_enabled.get(name) == "YES" else 0
        under_hrs = max(0, 8 - total_hrs)
        
        rate = rates.get(name, 0)
        daily_pay = (total_hrs * rate) # Or use your specific day-rate logic
        
        summary.append({
            "Date": date, "Name": name, "Worked": round(total_hrs, 2),
            "OT": round(ot_hrs, 2), "Under": round(under_hrs, 2), "Rate": rate
        })
    return pd.DataFrame(summary)

# --- UI ---
st.set_page_config(page_title="Malapascua DTR", layout="wide")
st.title("Malapascua DTR & Payroll")

tab1, tab2 = st.tabs(["🕒 Staff Clock-In", "🔐 Admin & Payroll"])

with tab1:
    crew_df = load_crew()
    if crew_df is not None:
        names = [""] + crew_df['Name'].tolist()
        name = st.selectbox("Select Name", names)
        if name:
            ts = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
            c1, c2 = st.columns(2)
            if c1.button("IN"):
                get_gsheet().append_row([name, ts, "IN", "Live"])
                st.success("Logged IN")
            if c2.button("OUT"):
                get_gsheet().append_row([name, ts, "OUT", "Live"])
                st.warning("Logged OUT")

with tab2:
    if st.text_input("PIN", type="password") == ADMIN_PIN:
        sheet = get_gsheet()
        if sheet:
            raw_data = pd.DataFrame(sheet.get_all_records())
            if not raw_data.empty:
                st.subheader("💰 Payroll Calculation")
                payroll_df = calculate_payroll(raw_data, crew_df)
                st.dataframe(payroll_df, use_container_width=True)
                
                # Export to CSV
                csv = payroll_df.to_csv(index=False).encode('utf-8')
                st.download_button("Download Payroll Report", csv, "payroll.csv", "text/csv")
