import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st
import pytz
import openpyxl

# --- ULTIMATE PINK & FALLING GLITTER STYLING (Update) ---
def apply_glitter_rain():
    st.markdown(
        """
        <style>
        /* Main background */
        .stApp {
            background: linear-gradient(to bottom, #FFF0F5, #FFB6C1);
            background-attachment: fixed;
        }

        /* --- DRAG AND DROP FIELD MATCHING --- */
        /* Targets the outer container of the uploader */
        [data-testid="stFileUploader"] {
            background-color: rgba(255, 182, 193, 0.3); /* Soft pink overlay */
            border-radius: 20px;
            padding: 20px;
        }

        /* Targets the actual dropzone box */
        [data-testid="stFileUploadDropzone"] {
            background-color: rgba(255, 255, 255, 0.5); /* Semi-transparent white */
            border: 2px dashed #FF1493 !important; /* Hot pink dashed border */
            border-radius: 15px;
            transition: 0.3s;
        }

        /* Hover effect for the dropzone */
        [data-testid="stFileUploadDropzone"]:hover {
            border: 2px solid #FF1493 !important;
            background-color: rgba(255, 255, 255, 0.8);
            box-shadow: 0 0 15px #FF69B4;
        }

        /* Changing the "Drag and drop files here" text color */
        [data-testid="stFileUploadDropzone"] div div span {
            color: #4B0082 !important; /* Dark Indigo */
            font-weight: bold;
        }
        
        /* Changing the "Limit 200MB" small text color */
        [data-testid="stFileUploadDropzone"] div div small {
            color: #8A2BE2 !important; /* Blue Violet */
        }

        /* Global Text & Headers */
        p, label, h1 {
            color: #FF1493 !important;
            font-family: 'Comic Sans MS', cursive, sans-serif;
        }
        
        p, label {
            color: #4B0082 !important; /* Darker for readability */
            font-weight: 600;
        }

        /* Glitter Animation */
        @keyframes glitter-fall {
            0% { transform: translateY(-10vh) rotate(0deg); opacity: 1; }
            100% { transform: translateY(100vh) rotate(360deg); opacity: 0; }
        }

        .glitter {
            position: absolute; width: 8px; height: 8px;
            background: white; border-radius: 50%;
            box-shadow: 0 0 10px #FFF, 0 0 20px #FF69B4;
            animation: glitter-fall 5s linear infinite;
            z-index: 0; pointer-events: none;
        }

        .g1 { left: 10%; animation-duration: 4s; }
        .g2 { left: 30%; animation-duration: 6s; }
        .g3 { left: 50%; animation-duration: 3s; }
        .g4 { left: 70%; animation-duration: 7s; }
        .g5 { left: 90%; animation-duration: 5s; }
        </style>

        <div class="glitter g1"></div>
        <div class="glitter g2"></div>
        <div class="glitter g3"></div>
        <div class="glitter g4"></div>
        <div class="glitter g5"></div>
        """,
        unsafe_allow_html=True
    )

def extract_xml_data_to_df(xml_file):
    # (Dieser Teil bleibt unverändert, da er nur die Logik enthält)
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        namespace = root.tag.split('}')[0].strip('{')
        extracted_data = []
        entries = root.findall(f'.//{{{namespace}}}Ntry')

        for entry in entries:
            bookg_date = entry.find(f'.//{{{namespace}}}BookgDt//{{{namespace}}}Dt')
            bookg_date_str = pd.to_datetime(bookg_date.text).strftime('%d.%m.%Y') if bookg_date is not None else None
            transactions = entry.findall(f'.//{{{namespace}}}TxDtls')

            for transaction in transactions:
                data = {
                    "Buchungsdatum": bookg_date_str,
                    "Transaktionsbetrag": None,
                    "Debitor": None
                }
                tx_amt = transaction.find(f'.//{{{namespace}}}TxAmt//{{{namespace}}}Amt')
                if tx_amt is not None:
                    currency = tx_amt.attrib.get("Ccy", "CHF")
                    data["Transaktionsbetrag"] = f"{currency} {float(tx_amt.text):,.2f}"

                dbtr_name = transaction.find(f'.//{{{namespace}}}Dbtr//{{{namespace}}}Nm')
                if dbtr_name is not None:
                    data["Debitor"] = dbtr_name.text

                extracted_data.append(data)
        return pd.DataFrame(extracted_data)
    except Exception as e:
        return pd.DataFrame()

# --- APP START ---
st.set_page_config(page_title="Glitzer Converter", page_icon="✨")
apply_glitter_rain()

st.title("✨ XML Magic Converter ✨")
# Dieser Text wird jetzt dunkel sein:
st.write("Lade deine Dateien hoch und sieh zu, wie sie funkeln!") 

# Dieses Label wird jetzt dunkel sein:
uploaded_files = st.file_uploader("Wähle XML-Dateien", accept_multiple_files=True, type=['xml'])

if uploaded_files:
    dfs = [extract_xml_data_to_df(f) for f in uploaded_files]
    combined_df = pd.concat(dfs, ignore_index=True) if dfs else None

    if combined_df is not None and not combined_df.empty:
        st.success("Dateien erfolgreich verarbeitet! ✨")
        st.dataframe(combined_df)
        
        excel_file = "glitzer_export.xlsx"
        combined_df.to_excel(excel_file, index=False)
        
        with open(excel_file, "rb") as f:
            st.download_button("💖 Download Glitzer-Excel 💖", f, file_name=excel_file, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    elif combined_df is not None and combined_df.empty:
         st.warning("Die XML-Dateien konnten gelesen werden, enthielten aber keine passenden Daten.")
