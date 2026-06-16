import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

# --- DATABASE SETUP ---
DB_NAME = "chemical_inventory.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            quantity TEXT NOT NULL,
            received_date TEXT NOT NULL,
            msds_link TEXT,
            notes TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- APP HUDS & STYLING ---
st.set_page_config(page_title="Chemical Sample Lab", page_icon="🧪", layout="wide")
st.title("🧪 Chemical Sample Inventory")
st.markdown("Track, manage, and access your sample stash without the Excel dread.")

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
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''
            INSERT INTO inventory (product_name, quantity, received_date, msds_link, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (prod_name, qty, str(rec_date), msds, notes))
        conn.commit()
        conn.close()
        st.sidebar.success(f"Added {prod_name} successfully!")
    else:
        st.sidebar.error("Product Name and Quantity are required.")

# --- MAIN PAGE: VIEW & SEARCH ---
conn = sqlite3.connect(DB_NAME)
df = pd.read_sql_query("SELECT * FROM inventory", conn)
conn.close()

if df.empty:
    st.info("Your inventory is currently empty. Use the sidebar to add your first chemical sample!")
else:
    # Quick Metrics
    st.metric(label="Total Samples Accounted For", value=len(df))
    
    # Search functionality
    search_query = st.text_input("🔍 Search inventory by product name...", "")
    if search_query:
        df = df[df['product_name'].str.contains(search_query, case=False, na=False)]

    # Format the dataframe for pretty display
    # Dropping the ID column for user view, but keeping the rest
    display_df = df.copy()
    
    # Render interactive data table
    st.subheader("Current Stock")
    st.dataframe(
        display_df[['product_name', 'quantity', 'received_date', 'msds_link', 'notes']], 
        column_config={
            "product_name": "Product Name",
            "quantity": "Amount",
            "received_date": "Date Received",
            "msds_link": st.column_config.LinkColumn("MSDS Link", display_text="Open MSDS"),
            "notes": "Notes"
        },
        use_container_width=True,
        hide_index=True
    )
