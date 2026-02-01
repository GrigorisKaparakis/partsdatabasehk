import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Moto ERP Cloud", layout="wide")

# ΑΥΞΗΣΗ ΧΡΟΝΟΥ: Ανανέωση κάθε 60 δευτερόλεπτα (60000ms) για να μην "χτυπάει" το Quota
st_autorefresh(interval=60000, key="datarefresh")

# Σύνδεση με Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        # Αλλάζουμε το ttl σε 10-20 δευτερόλεπτα. 
        # Έτσι, αν 3 άτομα πατήσουν refresh μαζί, θα πάρουν την ίδια "φρέσκια" εικόνα από τη μνήμη
        data = conn.read(ttl="20s") 
        if data is None or data.empty:
            return pd.DataFrame(columns=["ΑΝΤΑΛΛΑΚΤΙΚΑ & ΠΟΣΟΤΗΤΑ", "ΠΕΛΑΤΗΣ", "ΣΧΟΛΙΑ", "ΤΗΛΕΦΩΝΟ", "ΠΡΟΚΑΤΑΒΟΛΗ", "ΗΜΕΡΟΜΗΝΙΑ", "ΚΑΤΑΣΤΑΣΗ", "ΕΤΑΙΡΕΙΑ"])
        return data
    except Exception as e:
        st.error(f"Πρόβλημα σύνδεσης: {e}")
        return pd.DataFrame(columns=["ΑΝΤΑΛΛΑΚΤΙΚΑ & ΠΟΣΟΤΗΤΑ", "ΠΕΛΑΤΗΣ", "ΣΧΟΛΙΑ", "ΤΗΛΕΦΩΝΟ", "ΠΡΟΚΑΤΑΒΟΛΗ", "ΗΜΕΡΟΜΗΝΙΑ", "ΚΑΤΑΣΤΑΣΗ", "ΕΤΑΙΡΕΙΑ"])

df = get_data()

# Διασφάλιση ότι όλες οι στήλες υπάρχουν για να μην κρασάρει
required_cols = ["ΑΝΤΑΛΛΑΚΤΙΚΑ & ΠΟΣΟΤΗΤΑ", "ΠΕΛΑΤΗΣ", "ΣΧΟΛΙΑ", "ΤΗΛΕΦΩΝΟ", "ΠΡΟΚΑΤΑΒΟΛΗ", "ΗΜΕΡΟΜΗΝΙΑ", "ΚΑΤΑΣΤΑΣΗ", "ΕΤΑΙΡΕΙΑ"]
for col in required_cols:
    if col not in df.columns:
        df[col] = ""

# --- SIDEBAR ---
st.sidebar.header("🏢 ΕΤΑΙΡΕΙΕΣ")
brands = ["Honda", "Mototrend", "Πετρόπουλος", "Ducati", "Kawasaki", "KSR"]
brand_filter = st.sidebar.radio("Επιλέξτε:", brands)

# --- ΝΕΑ ΚΑΤΑΧΩΡΗΣΗ ---
with st.expander("➕ ΝΕΑ ΠΑΡΑΓΓΕΛΙΑ"):
    with st.form("quick_form", clear_on_submit=True):
        f_parts = st.text_area("Ανταλλακτικά (Κωδικός X Ποσότητα - Enter για νέα γραμμή)", height=100)
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
            st.rerun()

# --- TABS ---
t_active, t_done, t_cancel = st.tabs(["⚡ ΤΡΕΧΟΥΣΕΣ", "✅ ΟΛΟΚΛΗΡΩΜΕΝΑ", "❌ ΑΚΥΡΩΜΕΝΑ"])

# Φιλτράρισμα δεδομένων
brand_df = df[df["ΕΤΑΙΡΕΙΑ"] == brand_filter]
view_cols = ["ΑΝΤΑΛΛΑΚΤΙΚΑ & ΠΟΣΟΤΗΤΑ", "ΠΕΛΑΤΗΣ", "ΣΧΟΛΙΑ", "ΤΗΛΕΦΩΝΟ", "ΠΡΟΚΑΤΑΒΟΛΗ", "ΗΜΕΡΟΜΗΝΙΑ", "ΚΑΤΑΣΤΑΣΗ"]

# --- TAB: ΤΡΕΧΟΥΣΕΣ (ΕΔΩ ΜΟΝΟ ΤΟ REFRESH) ---
with t_active:
    # Ενεργοποιούμε το refresh ΜΟΝΟ μέσα σε αυτό το Tab
    st_autorefresh(interval=30000, key="active_refresh") 
    
    st.subheader("Εκκρεμή & Ήρθαν")
    data_manager(["ΕΚΚΡΕΜΕΙ", "ΗΡΘΕ"], "active_editor")

# --- TAB: ΟΛΟΚΛΗΡΩΜΕΝΑ ---
with t_done:
    st.subheader("Ιστορικό Παραλαβών")
    # Εδώ δεν υπάρχει autorefresh. Τα δεδομένα θα ανανεωθούν μόνο αν ο χρήστης 
    # αλλάξει εταιρεία ή πατήσει το κουμπί της καταχώρησης.
    data_manager(["ΤΟ ΠΗΡΕ"], "done_editor")

# --- TAB: ΑΚΥΡΩΜΕΝΑ ---
with t_cancel:
    st.subheader("Ακυρωμένες Παραγγελίες")
    data_manager(["ΑΚΥΡΩΘΗΚΕ"], "cancel_editor")

def data_manager(status_list, key):
    # Φιλτράρισμα δεδομένων για το συγκεκριμένο Tab
    subset = brand_df[brand_df["ΚΑΤΑΣΤΑΣΗ"].isin(status_list)][view_cols]
    
    # Χρήση width='stretch' αντί για use_container_width (Ενημέρωση 2026)
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
        # Ενημέρωση του κεντρικού dataframe (df) με βάση τα indexes του subset
        for index in edited_df.index:
            df.loc[index, view_cols] = edited_df.loc[index].values
        
        conn.update(data=df)
        st.rerun()

with t_active: data_manager(["ΕΚΚΡΕΜΕΙ", "ΗΡΘΕ"], "active_editor")
with t_done: data_manager(["ΤΟ ΠΗΡΕ"], "done_editor")
with t_cancel: data_manager(["ΑΚΥΡΩΘΗΚΕ"], "cancel_editor")
