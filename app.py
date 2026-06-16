import streamlit as st
import pandas as pd
from datetime import date
import gspread

# --- APP SETUP & STYLING ---
st.set_page_config(page_title="Chemical Sample Lab", page_icon="🧪", layout="wide")
st.title("🧪 Chemical Sample Inventory")

# Hardcoded direct ID string
SPREADSHEET_ID = "1Ou4Iwqz7qlU7faz_0K_PdxTd5YJiEUKMfJ5LWCrlHJo"
DEFAULT_COLS = ['product_name', 'quantity', 'received_date', 'msds_link', 'notes']

# --- CACHED GOOGLE SHEETS CONNECTION ---
@st.cache_resource(ttl=3600)
def init_google_connection(sheet_id):
    try:
        # Convert the native Streamlit Dict secret directly into a standard Python dict
        creds_dict = dict(st.secrets["gspread_creds"])
        
        # CLEANUP: Explicitly convert literal '\n' text characters into real structural newlines
       # CLEANUP: Explicitly normalize headers, footers, and line transitions
        if "private_key" in creds_dict:
            key = creds_dict["private_key"]
            
            # 1. Clean out any literal '\n' text characters if present
            key = key.replace("\\n", "\n")
            
            # 2. Ensure the header drops cleanly to the first data block
            if "-----BEGIN PRIVATE KEY-----" in key and not key.startswith("-----BEGIN PRIVATE KEY-----\n"):
                key = key.replace("-----BEGIN PRIVATE KEY-----", "-----BEGIN PRIVATE KEY-----\n")
                
            # 3. FIX: Ensure the footer drops cleanly to its own line at the very end
            if "-----END PRIVATE KEY-----" in key and not key.endswith("\n-----END PRIVATE KEY-----"):
                # Strip spaces/quotes, then isolate the banner on a fresh trailing line
                key = key.rstrip('"\n\r ')
                if not key.endswith("\n-----END PRIVATE KEY-----"):
                    key = key.replace("-----END PRIVATE KEY-----", "\n-----END PRIVATE KEY-----")
            
            creds_dict["private_key"] = key.strip()
        # Explicit scopes for authorization
        EXPLICIT_SCOPES = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Authenticate cleanly with the sanitized dict
        gc = gspread.service_account_from_dict(creds_dict, scopes=EXPLICIT_SCOPES)
        sh = gc.open_by_key(sheet_id)
        return sh.get_worksheet(0)
    except Exception as auth_err:
        st.error(f"🛑 Critical Authentication Failure: {auth_err}")
        return None

# Establish or retrieve connection
worksheet = init_google_connection(SPREADSHEET_ID)

# Pull down data rows safely
df = pd.DataFrame(columns=DEFAULT_COLS)
if worksheet is not None:
    try:
        records = worksheet.get_all_records()
        df = pd.DataFrame(records) if records else pd.DataFrame(columns=DEFAULT_COLS)
        st.success("⚡ Database Pipeline Online")
    except Exception as e:
        st.error(f"Error fetching data: {e}")
else:
    st.warning("⚠️ App is running offline. Check secret formatting configuration.")

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
                if not worksheet.get_all_values():
                    worksheet.append_row(DEFAULT_COLS)
                worksheet.append_row(new_row)
                st.sidebar.success(f"Successfully logged {prod_name}!")
                st.rerun()
            except Exception as write_error:
                st.sidebar.error(f"Write Failure: {write_error}")
        else:
            st.sidebar.error("Cannot write: Database connection is offline.")
    else:
        st.sidebar.error("Product Name and Quantity are required.")

# --- MAIN PAGE: VIEW & SEARCH ---
if not df.empty and len(df) > 0:
    st.metric(label="Total Samples Accounted For", value=len(df))
    search_query = st.text_input("🔍 Filter samples by name...", "")
    display_df = df.copy()
    
    if search_query:
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
    st.info("Your chemical inventory sheet is currently empty. Start logging samples in the sidebar!")
