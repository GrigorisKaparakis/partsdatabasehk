import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh

# 1. Βασικές Ρυθμίσεις
st.set_page_config(page_title="Moto ERP Cloud 2026", layout="wide")

# 2. Σύνδεση με Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        # Χρησιμοποιούμε ttl="30s" για να μειώσουμε τα Read Requests στη Google
        data = conn.read(ttl="30s")
        if data is None or data.empty:
            return pd.DataFrame(columns=["ΑΝΤΑΛΛΑΚΤΙΚΑ & ΠΟΣΟΤΗΤΑ", "ΠΕΛΑΤΗΣ", "ΣΧΟΛΙΑ", "ΤΗΛΕΦΩΝΟ", "ΠΡΟΚΑΤΑΒΟΛΗ", "ΗΜΕΡΟΜΗΝΙΑ", "ΚΑΤΑΣΤΑΣΗ", "ΕΤΑΙΡΕΙΑ"])
        return data
    except Exception:
        return pd.DataFrame(columns=["ΑΝΤΑΛΛΑΚΤΙΚΑ & ΠΟΣΟΤΗΤΑ", "ΠΕΛΑΤΗΣ", "ΣΧΟΛΙΑ", "ΤΗΛΕΦΩΝΟ", "ΠΡΟΚΑΤΑΒΟΛΗ", "ΗΜΕΡΟΜΗΝΙΑ", "ΚΑΤΑΣΤΑΣΗ", "ΕΤΑΙΡΕΙΑ"])

# Φόρτωση δεδομένων
df = get_data()

# Διασφάλιση στηλών
required_cols = ["ΑΝΤΑΛΛΑΚΤΙΚΑ & ΠΟΣΟΤΗΤΑ", "ΠΕΛΑΤΗΣ", "ΣΧΟΛΙΑ", "ΤΗΛΕΦΩΝΟ", "ΠΡΟΚΑΤΑΒΟΛΗ", "ΗΜΕΡΟΜΗΝΙΑ", "ΚΑΤΑΣΤΑΣΗ", "ΕΤΑΙΡΕΙΑ"]
for col in required_cols:
    if col not in df.columns:
        df[col] = ""

# --- SIDEBAR ---
st.sidebar.header("🏢 ΕΤΑΙΡΕΙΕΣ")
brands = ["Honda", "Mototrend", "Πετρόπουλος", "Ducati", "Kawasaki", "KSR"]
brand_filter = st.sidebar.radio("Επιλέξτε:", brands)

# 3. ΟΡΙΣΜΟΣ ΣΥΝΑΡΤΗΣΗΣ data_manager (ΠΡΕΠΕΙ ΝΑ ΕΙΝΑΙ ΕΔΩ)
def data_manager(status_list, key, brand_df, view_cols):
    # Φιλτράρισμα για το συγκεκριμένο Tab και Status
    subset = brand_df[brand_df["ΚΑΤΑΣΤΑΣΗ"].isin(status_list)][view_cols]
    
    edited_df = st.data_editor(
        subset,
        column_config={
            "ΑΝΤΑΛΛΑΚΤΙΚΑ & ΠΟΣΟΤΗΤΑ": st.column_config.TextColumn(width="large"),
            "ΚΑΤΑΣΤΑΣΗ": st.column_config.SelectboxColumn(
                options=["ΕΚΚΡΕΜΕΙ", "ΗΡΘΕ", "ΤΟ ΠΗΡΕ", "ΑΚΥΡΩΘΗΚΕ"],
                required=True
            ),
            "ΗΜΕΡΟΜΗΝΙΑ": st.column_config.TextColumn(disabled=True)
        },
        width="stretch",
        num_rows="dynamic",
        key=key
    )

    # Αυτόματη αποθήκευση αν υπάρξει αλλαγή
    if not edited_df.equals(subset):
        # Ενημέρωση του κεντρικού df
        for index in edited_df.index:
            df.loc[index, view_cols] = edited_df.loc[index].values
        
        conn.update(data=df)
        st.cache_data.clear() # Καθαρίζουμε τη μνήμη για να δούμε αμέσως την αλλαγή
        st.rerun()

# --- ΚΥΡΙΩΣ ΕΦΑΡΜΟΓΗ ---
st.title(f"Διαχείριση: {brand_filter}")

# Φόρμα Καταχώρησης
with st.expander("➕ ΝΕΑ ΠΑΡΑΓΓΕΛΙΑ"):
    with st.form("quick_form", clear_on_submit=True):
        f_parts = st.text_area("Ανταλλακτικά (Κωδικός X Ποσότητα)", height=100)
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
            st.cache_data.clear()
            st.rerun()

# --- TABS ---
t_active, t_done, t_cancel = st.tabs(["⚡ ΤΡΕΧΟΥΣΕΣ", "✅ ΟΛΟΚΛΗΡΩΜΕΝΑ", "❌ ΑΚΥΡΩΜΕΝΑ"])

brand_df = df[df["ΕΤΑΙΡΕΙΑ"] == brand_filter]
view_cols = ["ΑΝΤΑΛΛΑΚΤΙΚΑ & ΠΟΣΟΤΗΤΑ", "ΠΕΛΑΤΗΣ", "ΣΧΟΛΙΑ", "ΤΗΛΕΦΩΝΟ", "ΠΡΟΚΑΤΑΒΟΛΗ", "ΗΜΕΡΟΜΗΝΙΑ", "ΚΑΤΑΣΤΑΣΗ"]

with t_active:
    # Refresh ΜΟΝΟ εδώ - κάθε 45 δευτερόλεπτα για ασφάλεια Quota
    st_autorefresh(interval=45000, key="active_refresh")
    st.subheader("Εκκρεμή & Ήρθαν")
    data_manager(["ΕΚΚΡΕΜΕΙ", "ΗΡΘΕ"], "active_editor", brand_df, view_cols)

with t_done:
    st.subheader("Ιστορικό (Το πήρε)")
    data_manager(["ΤΟ ΠΗΡΕ"], "done_editor", brand_df, view_cols)

with t_cancel:
    st.subheader("Ακυρωμένα")
    data_manager(["ΑΚΥΡΩΘΗΚΕ"], "cancel_editor", brand_df, view_cols)
