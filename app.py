import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# --- APP SETUP & STYLING ---
st.set_page_config(page_title="Chemical Sample Lab", page_icon="🧪", layout="wide")
st.title("🧪 Chemical Sample Inventory")
st.markdown("A sleek, Streamlit front-end powered by a permanent Google Sheets backend.")

# --- CONNECT TO GOOGLE SHEETS ---
# This establishes the connection using credentials we'll provide to the Streamlit Cloud dashboard
conn = st.connection("gsheets", type=GSheetsConnection)

# Fetch existing data from the sheet
try:
    # We clear the cache on every rerun to make sure we immediately see new samples logged
    df = conn.read(ttl=0)
    # Ensure dataframe isn't completely empty and has columns
    if df.empty:
        df = pd.DataFrame(columns=['product_name', 'quantity', 'received_date', 'msds_link', 'notes'])
except Exception as e:
    df = pd.DataFrame(columns=['product_name', 'quantity', 'received_date', 'msds_link', 'notes'])

# --- SIDEBAR: ADD NEW SAMPLE ---
st.sidebar.header("📥 Log New Sample")
with st.sidebar.form("sample_form", clear_on_submit=True):
    prod_name = st.text_input("Product Name *")
    qty = st.text_input("Quantity (e.g., 500ml, 10g) *")
    rec_date = st.date_input("Received Date", date.today())
    msds = st.text_input("MSDS URL / Link")
    notes = st.text_area("Notes / Hazards")
    
    submit = st.form_submit_with_button("Add to Inventory")

if submit:
    if prod_name and qty:
        # Create a new row of data
        new_row = pd.DataFrame([{
            "product_name": prod_name,
            "quantity": qty,
            "received_date": str(rec_date),
            "msds_link": msds,
            "notes": notes
        }])
        
        # Combine existing data with the new entry
        updated_df = pd.concat([df, new_row], ignore_index=True)
        
        # Push back to Google Sheets
        conn.update(data=updated_df)
        st.sidebar.success(f"Successfully logged {prod_name} to the cloud!")
        
        # Rerun the app to refresh the main data view instantly
        st.rerun()
    else:
        st.sidebar.error("Product Name and Quantity are required.")

# --- MAIN PAGE: VIEW & SEARCH ---
if df.empty or len(df) == 0:
    st.info("Your chemical inventory sheet is currently empty. Start logging samples in the sidebar!")
else:
    # High-level tracking metric
    st.metric(label="Total Samples Accounted For", value=len(df))
    
    # Live Search bar
    search_query = st.text_input("🔍 Filter samples by name...", "")
    display_df = df.copy()
    
    if search_query:
        display_df = display_df[display_df['product_name'].str.contains(search_query, case=False, na=False)]

    # Clean, interactive UI Data Table
    st.subheader("Current Stock Table")
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
