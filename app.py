import streamlit as st
import pandas as pd
from datetime import date
import json
import gspread

# --- APP SETUP & STYLING ---
st.set_page_config(page_title="Chemical Sample Lab", page_icon="🧪", layout="wide")
st.title("🧪 Chemical Sample Inventory")

SPREADSHEET_NAME = "Shamrock"

# --- DIRECT GOOGLE SHEETS CONNECTION VIA GSPREAD ---
try:
    # 1. Parse your raw JSON key string from secrets back into a dictionary
    raw_credentials = json.loads(st.secrets["secrets"]["raw_json"])
    raw_credentials["type"] = "service_account"
    
    # 2. Authenticate directly using the native Google library
    gc = gspread.service_account_from_dict(raw_credentials)
    
    # 3. Open the spreadsheet by its exact name
    sh = gc.open(SPREADSHEET_NAME)
    worksheet = sh.get_worksheet(0) # Open the first tab
    
    # 4. Read data into a Pandas DataFrame
    records = worksheet.get_all_records()
    df = pd.DataFrame(records)
    
    # If the sheet is brand new and completely empty, force standard headers
    if df.empty:
        df = pd.DataFrame(columns=['product_name', 'quantity', 'received_date', 'msds_link', 'notes'])
        
except Exception as e:
    st.error(f"Connection Error: {e}")
    df = pd.DataFrame(columns=['product_name', 'quantity', 'received_date', 'msds_link', 'notes'])

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
        # Create the exact row layout to append
        new_row = [prod_name, qty, str(rec_date), msds, notes]
        
        try:
            # Append directly to the bottom of the Google Sheet
            worksheet.append_row(new_row)
            st.sidebar.success(f"Successfully logged {prod_name}!")
            st.rerun()
        except Exception as write_error:
            st.sidebar.error(f"Failed to save entry: {write_error}")
    else:
        st.sidebar.error("Product Name and Quantity are required.")

# --- MAIN PAGE: VIEW & SEARCH ---
if not df.empty and len(df) > 0:
    st.metric(label="Total Samples Accounted For", value=len(df))
    search_query = st.text_input("🔍 Filter samples by name...", "")
    display_df = df.copy()
    
    if search_query:
        # Quick safety check to handle any numeric columns gracefully during string filtering
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
