import streamlit as st
import pandas as pd
from datetime import date
import json
import gspread

# --- APP SETUP & STYLING ---
st.set_page_config(page_title="Chemical Sample Lab", page_icon="🧪", layout="wide")
st.title("🧪 Chemical Sample Inventory")

# Hardcoded direct ID string to guarantee Google finds the file instantly
SPREADSHEET_ID = "1Ou4Iwqz7qlU7faz_0K_PdxTd5YJiEUKMfJ5LWCrlHJo"

# --- DIRECT GOOGLE SHEETS CONNECTION VIA GSPREAD ---
@st.cache_resource(ttl=3600)
def get_google_worksheet(sheet_id):
    try:
        # Parse the raw JSON key block from secrets
        raw_credentials = json.loads(st.secrets["secrets"]["raw_json"])
        raw_credentials["type"] = "service_account"
        
        # Authenticate using standard Google Auth
        gc = gspread.service_account_from_dict(raw_credentials)
        
        # Open directly by ID (100% foolproof vs text names)
        sh = gc.open_by_key(sheet_id)
        return sh.get_worksheet(0)
    except Exception as e:
        # If it returns a string success message disguised as an error, look for it
        if "Response [200]" in str(e):
            try:
                gc = gspread.service_account_from_dict(raw_credentials)
                sh = gc.open_by_key(sheet_id)
                return sh.get_worksheet(0)
            except:
                pass
        st.error(f"Google Connection Error: {e}")
        return None

# Establish connection
worksheet = get_google_worksheet(SPREADSHEET_ID)

# Read the data safely
df = pd.DataFrame(columns=['product_name', 'quantity', 'received_date', 'msds_link', 'notes'])
if worksheet is not None:
    try:
        records = worksheet.get_all_records()
        if records:
            df = pd.DataFrame(records)
    except Exception as read_err:
        # Fallback if the sheet is completely empty of entries/headers
        pass

# --- SIDEBAR: ADD NEW SAMPLE ---
st.sidebar.header("📥 Log New Sample")
with st.sidebar.form("sample_form", clear_on_submit=True):
    prod_name = st.text_input("Product Name *")
    qty = st.text_input("Quantity *")
    rec_date = st.date_input("Received Date", date.today())
    msds = st.text_input("MSDS URL / Link")
    notes = st.text_area("Notes / Hazards")
    
    submit = st.form_submit_button("Add to Inventory")

if submit:
    if prod_name and qty:
        new_row = [prod_name, qty, str(rec_date), msds, notes]
        
        if worksheet is not None:
            try:
                # If the sheet is brand new and completely blank, insert headers first
                if not worksheet.get_all_values():
                    worksheet.append_row(['product_name', 'quantity', 'received_date', 'msds_link', 'notes'])
                
                # Append data directly to the bottom of the Google Sheet
                worksheet.append_row(new_row)
                st.sidebar.success(f"Successfully logged {prod_name}!")
                st.rerun()
            except Exception as write_error:
                st.sidebar.error(f"Failed to save entry: {write_error}")
        else:
            st.sidebar.error("Database connection is offline. Verify your Google Sheet is shared with the service account email.")
    else:
        st.sidebar.error("Product Name and Quantity are required.")

# --- MAIN PAGE: VIEW & SEARCH ---
if worksheet is None:
    st.warning("⚠️ App is running in offline sandbox mode. Please check the connection error message above.")

if not df.empty and len(df) > 0:
    st.metric(label="Total Samples Accounted For", value=len(df))
    search_query = st.text_input("🔍 Filter samples by name...", "")
    display_df = df.copy()
    
    if search_query:
        display_df['product_name'] = display_df['product_name'].astype(str)
        display_df = display_df[display_df['product_name'].str.contains(search_query, case=False, na=False)]

    st.dataframe(
        display_df[['product_name', 'quantity', 'received_date', 'msds_link', 'notes']], 
        column_config={
            "product_name": "Product Name",
            "quantity": "Amount",
            "received_date": "Date Received",
            "msds_link": st.column_config.LinkColumn("MSDS Link", display_text="Open MSDS"),
            "notes": "Notes / Hazards"
        },
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Your chemical inventory sheet is currently empty. Start logging samples in the sidebar!")
