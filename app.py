import streamlit as st
import pandas as pd
from datetime import date
import json
import gspread

# --- APP SETUP & STYLING ---
st.set_page_config(page_title="Chemical Sample Lab", page_icon="🧪", layout="wide")
st.title("🧪 Chemical Sample Inventory")

# Hardcoded direct ID string
SPREADSHEET_ID = "1Ou4Iwqz7qlU7faz_0K_PdxTd5YJiEUKMfJ5LWCrlHJo"

# Pre-define empty baseline columns
DEFAULT_COLS = ['product_name', 'quantity', 'received_date', 'msds_link', 'notes']
df = pd.DataFrame(columns=DEFAULT_COLS)
worksheet = None

# --- DIRECT GOOGLE SHEETS CONNECTION ---
try:
    raw_credentials = json.loads(st.secrets["secrets"]["raw_json"])
    raw_credentials["type"] = "service_account"
    
    service_account_email = raw_credentials.get("client_email", "Unknown Email")
    st.info(f"🔑 Authenticating as Service Account: `{service_account_email}`")
    
    gc = gspread.service_account_from_dict(raw_credentials)
    worksheet = gc.open_by_key(SPREADSHEET_ID).get_worksheet(0)
    
    # Try reading records safely
    try:
        records = worksheet.get_all_records()
        if records:
            df = pd.DataFrame(records)
    except Exception:
        # If it fails to read because the sheet is totally blank, we ignore it and use our default columns
        pass

    st.success("⚡ Database Connection Established Successfully!")

except Exception as e:
    error_msg = str(e).strip()
    if not error_msg:
        error_msg = "Empty response error (usually means the sheet is totally blank or lacks column headers)."
    st.error(f"🛑 RAW GOOGLE ERROR: {error_msg}")

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
                # If the sheet has no values at all, write headers first
                if not worksheet.get_all_values():
                    worksheet.append_row(DEFAULT_COLS)
                
                worksheet.append_row(new_row)
                st.sidebar.success(f"Successfully logged {prod_name}!")
                st.rerun()
            except Exception as write_error:
                st.sidebar.error(f"Failed to save entry: {write_error}")
        else:
            st.sidebar.error("Database connection is offline.")
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
