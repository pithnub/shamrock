import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date
import json

# --- APP SETUP & STYLING ---
st.set_page_config(page_title="Chemical Sample Lab", page_icon="🧪", layout="wide")
st.title("🧪 Chemical Sample Inventory")

# --- CONNECT TO GOOGLE SHEETS VIA RAW SECRETS ---
# We read the raw text block, parse it into a Python dictionary, and pass it directly
try:
    secret_credentials = json.loads(st.secrets["secrets"]["raw_json"])
    
    conn = st.connection(
        "gsheets",
        type=GSheetsConnection,
        spreadsheet="https://docs.google.com/spreadsheets/d/1Ou4Iwqz7qlU7faz_0K_PdxTd5YJiEUKMfJ5LWCrlHJo/edit?gid=0#gid=0",
        type="service_account",
        **secret_credentials  # This safely unpacks the entire key automatically
    )
    df = conn.read(ttl=0)
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
        new_row = pd.DataFrame([{
            "product_name": prod_name,
            "quantity": qty,
            "received_date": str(rec_date),
            "msds_link": msds,
            "notes": notes
        }])
        updated_df = pd.concat([df, new_row], ignore_index=True)
        conn.update(data=updated_df)
        st.sidebar.success(f"Successfully logged {prod_name}!")
        st.rerun()
    else:
        st.sidebar.error("Product Name and Quantity are required.")

# --- MAIN PAGE: VIEW & SEARCH ---
if not df.empty and len(df) > 0:
    st.metric(label="Total Samples Accounted For", value=len(df))
    search_query = st.text_input("🔍 Filter samples by name...", "")
    display_df = df.copy()
    
    if search_query:
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
