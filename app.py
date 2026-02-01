import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Moto ERP Cloud", layout="wide")

# Αυτόματη ανανέωση κάθε 15 δευτερόλεπτα
st_autorefresh(interval=15000, key="datarefresh")

# Σύνδεση με Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    return conn.read(ttl=0) # ttl=0 για να παίρνει πάντα τα πιο φρέσκα δεδομένα

df = get_data()

# --- SIDEBAR ---
st.sidebar.header("🏢 ΕΤΑΙΡΕΙΕΣ")
brands = ["Honda", "Mototrend", "Πετρόπουλος", "Ducati", "Kawasaki", "KSR"]
brand_filter = st.sidebar.radio("Επιλέξτε:", brands)

# --- ΝΕΑ ΚΑΤΑΧΩΡΗΣΗ ---
with st.expander("➕ ΝΕΑ ΠΑΡΑΓΓΕΛΙΑ"):
    with st.form("quick_form", clear_on_submit=True):
        f_parts = st.text_area("Ανταλλακτικά (Κωδικός X Ποσότητα)")
        c1, c2, c3, c4 = st.columns(4)
        f_cust = c1.text_input("Πελάτης")
        f_phone = c2.text_input("Τηλέφωνο")
        f_notes = c3.text_input("Σχόλια")
        f_depo = c4.text_input("Προκαταβολή")
        
        if st.form_submit_button("✅ ΚΑΤΑΧΩΡΗΣΗ"):
            new_row = pd.DataFrame([{
                "ΑΝΤΑΛΛΑΚΤΙΚΑ & ΠΟΣΟΤΗΤΑ": f_parts, "ΠΕΛΑΤΗΣ": f_cust,
                "ΣΧΟΛΙΑ": f_notes, "ΤΗΛΕΦΩΝΟ": f_phone, "ΠΡΟΚΑΤΑΒΟΛΗ": f_depo,
                "ΗΜΕΡΟΜΗΝΙΑ": datetime.now().strftime("%d/%m/%Y"),
                "ΚΑΤΑΣΤΑΣΗ": "ΕΚΚΡΕΜΕΙ", "ΕΤΑΙΡΕΙΑ": brand_filter
            }])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(data=updated_df)
            st.success("Έγινε η καταχώρηση!")
            st.rerun()

# --- TABS ---
t_active, t_done, t_cancel = st.tabs(["⚡ ΤΡΕΧΟΥΣΕΣ", "✅ ΟΛΟΚΛΗΡΩΜΕΝΑ", "❌ ΑΚΥΡΩΜΕΝΑ"])
brand_df = df[df["ΕΤΑΙΡΕΙΑ"] == brand_filter]
view_cols = ["ΑΝΤΑΛΛΑΚΤΙΚΑ & ΠΟΣΟΤΗΤΑ", "ΠΕΛΑΤΗΣ", "ΣΧΟΛΙΑ", "ΤΗΛΕΦΩΝΟ", "ΠΡΟΚΑΤΑΒΟΛΗ", "ΗΜΕΡΟΜΗΝΙΑ", "ΚΑΤΑΣΤΑΣΗ"]

def data_manager(status_list, key):
    subset = brand_df[brand_df["ΚΑΤΑΣΤΑΣΗ"].isin(status_list)][view_cols]
    edited_df = st.data_editor(subset, use_container_width=True, num_rows="dynamic", key=key)

    if not edited_df.equals(subset):
        # Ενημέρωση των αλλαγών πίσω στο αρχικό dataframe
        for index, row in edited_df.iterrows():
            df.loc[index, view_cols] = row.values
        conn.update(data=df)
        st.rerun()

with t_active: data_manager(["ΕΚΚΡΕΜΕΙ", "ΗΡΘΕ"], "active_editor")
with t_done: data_manager(["ΤΟ ΠΗΡΕ"], "done_editor")
with t_cancel: data_manager(["ΑΚΥΡΩΘΗΚΕ"], "cancel_editor")
