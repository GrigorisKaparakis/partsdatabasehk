import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Moto ERP Pro Search", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

cols = ["ΑΝΤΑΛΛΑΚΤΙΚΑ & ΠΟΣΟΤΗΤΑ", "ΠΕΛΑΤΗΣ", "ΣΧΟΛΙΑ", "ΤΗΛΕΦΩΝΟ", "ΠΡΟΚΑΤΑΒΟΛΗ", "ΗΜΕΡΟΜΗΝΙΑ", "ΚΑΤΑΣΤΑΣΗ", "ΕΤΑΙΡΕΙΑ"]

def get_sheet_data(worksheet_name):
    try:
        data = conn.read(worksheet=worksheet_name, ttl="10s")
        if data is None or data.empty:
            return pd.DataFrame(columns=cols)
        # Διασφάλιση ότι οι στήλες είναι ίδιες
        data = data.reindex(columns=cols).fillna("")
        return data
    except:
        return pd.DataFrame(columns=cols)

# --- SIDEBAR ---
st.sidebar.header("🏢 ΕΤΑΙΡΕΙΕΣ")
brands = ["Honda", "Mototrend", "Πετρόπουλος", "Ducati", "Kawasaki", "KSR"]
brand_filter = st.sidebar.radio("Επιλέξτε:", brands)

t_active, t_done, t_cancel = st.tabs(["⚡ ΤΡΕΧΟΥΣΕΣ", "✅ ΟΛΟΚΛΗΡΩΜΕΝΑ", "❌ ΑΚΥΡΩΜΕΝΑ"])

# --- TAB: ΤΡΕΧΟΥΣΕΣ (Sheet1) ---
with t_active:
    st_autorefresh(interval=45000, key="active_refresh")
    df_active = get_sheet_data("Sheet1")
    
    with st.expander("➕ ΝΕΑ ΠΑΡΑΓΓΕΛΙΑ"):
        with st.form("new_order", clear_on_submit=True):
            f_parts = st.text_area("Ανταλλακτικά")
            c1, c2, c3, c4 = st.columns(4)
            f_cust, f_phone, f_notes, f_depo = c1.text_input("Πελάτης"), c2.text_input("Τηλέφωνο"), c3.text_input("Σχόλια"), c4.text_input("Προκαταβολή")
            if st.form_submit_button("✅ ΚΑΤΑΧΩΡΗΣΗ"):
                new_row = pd.DataFrame([{"ΑΝΤΑΛΛΑΚΤΙΚΑ & ΠΟΣΟΤΗΤΑ": f_parts, "ΠΕΛΑΤΗΣ": f_cust, "ΣΧΟΛΙΑ": f_notes, "ΤΗΛΕΦΩΝΟ": f_phone, "ΠΡΟΚΑΤΑΒΟΛΗ": f_depo, "ΗΜΕΡΟΜΗΝΙΑ": datetime.now().strftime("%d/%m/%Y"), "ΚΑΤΑΣΤΑΣΗ": "ΕΚΚΡΕΜΕΙ", "ΕΤΑΙΡΕΙΑ": brand_filter}])
                df_updated = pd.concat([df_active, new_row], ignore_index=True).fillna("")
                conn.update(worksheet="Sheet1", data=df_updated)
                st.rerun()

    st.markdown("---")
    search_active = st.text_input("🔍 Αναζήτηση στις Τρέχουσες", key="search_act")
    brand_active = df_active[df_active["ΕΤΑΙΡΕΙΑ"] == brand_filter]
    
    if search_active:
        brand_active = brand_active[brand_active.astype(str).apply(lambda x: x.str.contains(search_active, case=False, na=False)).any(axis=1)]

    edited_active = st.data_editor(
        brand_active, 
        column_config={"ΚΑΤΑΣΤΑΣΗ": st.column_config.SelectboxColumn(options=["ΕΚΚΡΕΜΕΙ", "ΗΡΘΕ", "ΤΟ ΠΗΡΕ", "ΑΚΥΡΩΘΗΚΕ"], required=True)}, 
        width="stretch", 
        key="active_ed"
    )

    if not edited_active.equals(brand_active):
        # Φορτώνουμε τα άλλα sheets μόνο αν χρειαστεί μεταφορά
        needs_update_active = False
        
        for idx, row in edited_active.iterrows():
            if row["ΚΑΤΑΣΤΑΣΗ"] == "ΤΟ ΠΗΡΕ":
                df_done = get_sheet_data("Sheet2")
                # Μετατρέπουμε τη σειρά σε DataFrame και καθαρίζουμε
                move_row = pd.DataFrame([row]).reindex(columns=cols).fillna("")
                conn.update(worksheet="Sheet2", data=pd.concat([df_done, move_row], ignore_index=True))
                df_active = df_active.drop(idx)
                needs_update_active = True
            elif row["ΚΑΤΑΣΤΑΣΗ"] == "ΑΚΥΡΩΘΗΚΕ":
                df_cancel = get_sheet_data("Sheet3")
                move_row = pd.DataFrame([row]).reindex(columns=cols).fillna("")
                conn.update(worksheet="Sheet3", data=pd.concat([df_cancel, move_row], ignore_index=True))
                df_active = df_active.drop(idx)
                needs_update_active = True
            else:
                # Απλή αλλαγή εντός του Sheet1 (π.χ. από ΕΚΚΡΕΜΕΙ σε ΗΡΘΕ)
                if not df_active.loc[idx].equals(row):
                    df_active.loc[idx] = row
                    needs_update_active = True
        
        if needs_update_active:
            conn.update(worksheet="Sheet1", data=df_active.fillna(""))
            st.rerun()

# --- TAB: ΟΛΟΚΛΗΡΩΜΕΝΑ (Sheet2) ---
with t_done:
    search_done = st.text_input("🔍 Αναζήτηση στο Ιστορικό", key="search_done")
    df_done_view = get_sheet_data("Sheet2")
    brand_done = df_done_view[df_done_view["ΕΤΑΙΡΕΙΑ"] == brand_filter]
    if search_done:
        brand_done = brand_done[brand_done.astype(str).apply(lambda x: x.str.contains(search_done, case=False, na=False)).any(axis=1)]
    st.dataframe(brand_done, width="stretch")

# --- TAB: ΑΚΥΡΩΜΕΝΑ (Sheet3) ---
with t_cancel:
    search_cancel = st.text_input("🔍 Αναζήτηση στα Ακυρωμένα", key="search_cancel")
    df_cancel_view = get_sheet_data("Sheet3")
    brand_cancel = df_cancel_view[df_cancel_view["ΕΤΑΙΡΕΙΑ"] == brand_filter]
    if search_cancel:
        brand_cancel = brand_cancel[brand_cancel.astype(str).apply(lambda x: x.str.contains(search_cancel, case=False, na=False)).any(axis=1)]
    st.dataframe(brand_cancel, width="stretch")
