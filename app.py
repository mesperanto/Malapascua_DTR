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
        st.error(f"Spreadsheet Access Error: {e}")
        return None

# --- AUTOMATIC SYNC ENGINE ---
def run_auto_sync(ss, crew_df):
    """Calculates payroll and updates the Summary sheet automatically."""
    try:
        main_sheet = ss.get_worksheet(0)
        raw_logs = pd.DataFrame(main_sheet.get_all_records())
        if raw_logs.empty:
            return

        # Calculate payroll for the current month to keep the summary fresh
        report = calculate_payroll(raw_logs, crew_df)
        
        try:
            sheet_summary = ss.worksheet("Payroll_Summary")
        except:
            sheet_summary = ss.add_worksheet(title="Payroll_Summary", rows="100", cols="20")
        
        sheet_summary.clear()
        data_to_push = [report.columns.tolist()] + report.astype(str).values.tolist()
        sheet_summary.update(data_to_push)
    except Exception as e:
        print(f"Auto-sync background error: {e}")

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
        
        total_hrs = sum((o - i).total_seconds() / 3600 for i, o in zip(ins, outs))
        h_rate = rates.get(name, 0)
        actual_pay = total_hrs * h_rate
        
        if total_hrs > 8 and ot_enabled.get(name) == "YES":
            actual_pay += (total_hrs - 8) * h_rate * 0.25
            
        summary.append({
            "Date": str(date), "Name": name, "Worked Hours": round(total_hrs, 2),
            "Hourly Rate": h_rate, "Final Pay": round(actual_pay, 2),
            "Net vs 8h": round(actual_pay - (8 * h_rate), 2)
        })
    return pd.DataFrame(summary)

# --- UI SETUP ---
st.set_page_config(page_title="Malapascua DTR", layout="centered")

# Initialize states
if 'submitted' not in st.session_state:
    st.session_state.submitted = False
if 'msg' not in st.session_state:
    st.session_state.msg = ""
if 'widget_key' not in st.session_state:
    st.session_state.widget_key = 0

tab1, tab2 = st.tabs(["🕒 Staff Clock-In", "🔐 Admin Dashboard"])

with tab1:
    placeholder = st.empty()
    
    if st.session_state.submitted:
        with placeholder.container():
            st.markdown(f"<h1 style='text-align: center; color: #2E7D32;'>{st.session_state.msg}</h1>", unsafe_allow_html=True)
            time.sleep(5)
            st.session_state.submitted = False
            # Incrementing the key forces the selectbox to reset to blank
            st.session_state.widget_key += 1 
            st.rerun()
    else:
        with placeholder.container():
            crew_df = load_crew()
            if crew_df is not None:
                staff_names = [""] + sorted(crew_df['Name'].tolist())
                # Key changes every time a submission happens, clearing the selection
                selected_name = st.selectbox(
                    "Select your Name", 
                    staff_names, 
                    key=f"name_select_{st.session_state.widget_key}"
                )
                
                if selected_name:
                    now = datetime.now(TIMEZONE)
                    display_time = now.strftime("%H:%M")
                    db_ts = now.strftime("%Y-%m-%d %H:%M:%S")
                    
                    col1, col2 = st.columns(2)
                    ss = get_spreadsheet()

                    if col1.button("TIME IN", use_container_width=True, type="primary"):
                        ss.get_worksheet(0).append_row([selected_name, db_ts, "IN", "Live"])
                        # RUN AUTO SYNC IMMEDIATELY
                        run_auto_sync(ss, crew_df)
                        st.session_state.msg = f"Time IN: {display_time}"
                        st.session_state.submitted = True
                        st.rerun()

                    if col2.button("TIME OUT", use_container_width=True):
                        ss.get_worksheet(0).append_row([selected_name, db_ts, "OUT", "Live"])
                        # RUN AUTO SYNC IMMEDIATELY
                        run_auto_sync(ss, crew_df)
                        st.session_state.msg = f"Time OUT: {display_time}"
                        st.session_state.submitted = True
                        st.rerun()

with tab2:
    if st.text_input("Admin PIN", type="password") == ADMIN_PIN:
        st.success("Access Granted")
        d_start = st.date_input("From", datetime.now(TIMEZONE) - timedelta(days=14))
        d_end = st.date_input("To", datetime.now(TIMEZONE))
        
        ss = get_spreadsheet()
        raw_logs = pd.DataFrame(ss.get_worksheet(0).get_all_records())
        if not raw_logs.empty:
            report = calculate_payroll(raw_logs, load_crew())
            # Filter report by selected dates for viewing
            report['Date_dt'] = pd.to_datetime(report['Date']).dt.date
            filtered_report = report[(report['Date_dt'] >= d_start) & (report['Date_dt'] <= d_end)]
            st.dataframe(filtered_report.drop(columns=['Date_dt']), use_container_width=True)
