import streamlit as st
import pandas as pd
from datetime import date
from google.oauth2 import service_account
from googleapiclient.discovery import build

# --- APP SETUP & STYLING ---
st.set_page_config(page_title="Chemical Sample Lab", page_icon="🧪", layout="wide")
st.title("🧪 Chemical Sample Inventory")

SPREADSHEET_ID = "1Ou4Iwqz7qlU7faz_0K_PdxTd5YJiEUKMfJ5LWCrlHJo"
DEFAULT_COLS = ['product_name', 'quantity', 'received_date', 'msds_link', 'notes']

# --- CACHED RAW GOOGLE API CONNECTION ---
@st.cache_resource(ttl=3600)
def init_raw_sheets_api(sheet_id):
    try:
        # Pull the native dictionary out of Streamlit Secrets
        creds_dict = dict(st.secrets["gspread_creds"])
        
        # Clean up line breaks in the key just in case
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
            
        SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets', 
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Generate raw google-auth credentials object
        credentials = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        
        # Build the official v4 sheets service client
        service = build('sheets', 'v4', credentials=credentials)
        return service.spreadsheets()
    except Exception as auth_err:
        st.error(f"🛑 Critical Authentication Failure: {auth_err}")
        return None

# Instantiate the raw spreadsheet service engine
sheet_service = init_raw_sheets_api(SPREADSHEET_ID)

# Pull down current table rows safely using raw API client
df = pd.DataFrame(columns=DEFAULT_COLS)
if sheet_service is not None:
    try:
        # Request data using A1 Range notation (Assuming your sheet tab is named 'Sheet1')
        result = sheet_service.values().get(spreadsheetId=SPREADSHEET_ID, range='Sheet1').execute()
        values = result.get('values', [])
        
        if values:
            # First row contains headers, subsequent rows contain data
            headers = values[0]
            rows = values[1:] if len(values) > 1 else []
            df = pd.DataFrame(rows, columns=headers) if rows else pd.DataFrame(columns=DEFAULT_COLS)
        else:
            df = pd.DataFrame(columns=DEFAULT_COLS)
            
        st.success("⚡ Raw API Database Pipeline Online")
    except Exception as e:
        st.error(f"Error fetching data via API Client: {e}")
else:
    st.warning("⚠️ App is running offline. Check credential configurations.")

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
        if sheet_service is not None:
            try:
                body = {'values': [new_row]}
                # Append the row using the raw API structure
                sheet_service.values().append(
                    spreadsheetId=SPREADSHEET_ID, 
                    range='Sheet1', 
                    valueInputOption='USER_ENTERED', 
                    body=body
                ).execute()
                
                st.sidebar.success(f"Successfully logged {prod_name}!")
                st.rerun()
            except Exception as write_error:
                st.sidebar.error(f"Write Failure: {write_error}")
        else:
            st.sidebar.error("Cannot write: Database service is offline.")
    else:
        st.sidebar.error("Product Name and Quantity are required.")

# --- MAIN PAGE: VIEW & SEARCH ---
if not df.empty and len(df) > 0:
    st.metric(label="Total Samples Accounted For", value=len(df))
    search_query = st.text_input("🔍 Filter samples by name...", "")
    display_df = df.copy()
    
    if search_query:
        # Safety normalization to string type before filtering
        display_df['product_name'] = display_df['product_name'].astype(str)
        display_df = display_df[display_df['product_name'].str.contains(search_query, case=False, na=False)]
        
    st.dataframe(
        display_df[DEFAULT_COLS],
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
    st.info("Your chemical inventory sheet is currently empty or unreadable. Start logging samples in the sidebar!")
