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
@st.cache_resource(ttl=300)  # Dropped to 5 mins to prevent "Broken Pipes" on idle machines
def init_raw_sheets_api(sheet_id):
    try:
        creds_dict = dict(st.secrets["gspread_creds"])
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
            
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        credentials = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        return build('sheets', 'v4', credentials=credentials).spreadsheets()
    except Exception as auth_err:
        st.error(f"🛑 Critical Authentication Failure: {auth_err}")
        return None

sheet_service = init_raw_sheets_api(SPREADSHEET_ID)

# Pull down current table rows
df = pd.DataFrame(columns=DEFAULT_COLS)
if sheet_service is not None:
    try:
        result = sheet_service.values().get(spreadsheetId=SPREADSHEET_ID, range='Sheet1').execute()
        values = result.get('values', [])
        
        if values:
            headers = values[0]
            rows = values[1:] if len(values) > 1 else []
            
            # Create the dataframe from raw rows
            df = pd.DataFrame(rows, columns=headers) if rows else pd.DataFrame(columns=DEFAULT_COLS)
            
            # TRACK GOOGLE ROW NUMBER: 
            # Row 1 is headers. First data row is Row 2.
            df['sheet_row_idx'] = range(2, len(df) + 2)
        else:
            df = pd.DataFrame(columns=DEFAULT_COLS)
            
        st.success("⚡ Raw API Database Pipeline Online")
    except Exception as e:
        st.error(f"Error fetching data via API Client: {e}")
else:
    st.warning("⚠️ App is running offline. Check credential configurations.")

# --- SIDEBAR: OPERATIONS ---
st.sidebar.header("📥 Log New Sample")
with st.sidebar.form("sample_form", clear_on_submit=True):
    prod_name = st.text_input("Product Name *")
    qty = st.text_input("Quantity *")
    rec_date = st.date_input("Received Date", date.today())
    msds = st.text_input("MSDS URL / Link")
    notes = st.text_area("Notes / Hazards")
    submit = st.form_submit_button("Add to Inventory")

if submit and prod_name and qty:
    new_row = [prod_name, qty, str(rec_date), msds, notes]
    if sheet_service is not None:
        try:
            sheet_service.values().append(
                spreadsheetId=SPREADSHEET_ID, range='Sheet1', 
                valueInputOption='USER_ENTERED', body={'values': [new_row]}
            ).execute()
            st.sidebar.success(f"Successfully logged {prod_name}!")
            st.rerun()
        except Exception as write_error:
            st.sidebar.error(f"Write Failure: {write_error}")

# --- NEW SIDEBAR FEATURE: EDIT QUANTITY ---
if not df.empty and sheet_service is not None:
    st.sidebar.markdown("---")
    st.sidebar.header("✏️ Update Existing Stock")
    
    # Let the user pick which product they want to update
    product_list = df['product_name'].tolist()
    selected_prod = st.sidebar.selectbox("Select chemical to update:", product_list)
    
    # Find current record details based on choice
    matched_row = df[df['product_name'] == selected_prod].iloc[0]
    target_sheet_row = int(matched_row['sheet_row_idx'])
    current_qty = matched_row['quantity']
    
    with st.sidebar.form("edit_form"):
        st.write(f"Current Quantity: **{current_qty}**")
        new_qty = st.text_input("New Quantity / Level:", value=str(current_qty))
        update_submit = st.form_submit_button("Save Changes")
        
    if update_submit:
        try:
            # In Google Sheets API, column B is usually 'quantity' if product_name is column A.
            # We target the exact cell: e.g., 'Sheet1!B5'
            cell_range = f"Sheet1!B{target_sheet_row}"
            
            sheet_service.values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=cell_range,
                valueInputOption='USER_ENTERED',
                body={'values': [[new_qty]]}
            ).execute()
            
            st.sidebar.success(f"Updated {selected_prod} level to {new_qty}!")
            st.rerun()
        except Exception as update_err:
            st.sidebar.error(f"Update failed: {update_err}")

# --- MAIN PAGE: VIEW & SEARCH ---
if not df.empty and len(df) > 0:
    st.metric(label="Total Samples Accounted For", value=len(df))
    search_query = st.text_input("🔍 Filter samples by name...", "")
    display_df = df.copy()
    
    if search_query:
        display_df['product_name'] = display_df['product_name'].astype(str)
        display_df = display_df[display_df['product_name'].str.contains(search_query, case=False, na=False)]
        
    # Clean up display columns (hiding our background index tracker)
    available_cols = [c for c in DEFAULT_COLS if c in display_df.columns]
    
    st.dataframe(
        display_df[available_cols],
        column_config={
            "product_name": "Product Name",
            "quantity": "Amount / Volume",
            "received_date": "Date Received",
            "msds_link": st.column_config.LinkColumn("MSDS Link", display_text="Open MSDS"),
            "notes": "Notes / Hazards"
        },
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Your chemical inventory sheet is currently empty or unreadable. Start logging samples in the sidebar!")
