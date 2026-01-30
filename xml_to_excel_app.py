import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st
import pytz
import openpyxl

# --- PINK & GLITTER STYLING ---
def apply_glitter_theme():
    st.markdown(
        """
        <style>
        /* Hintergrund mit Glitzer-Textur */
        .stApp {
            background-image: url("https://www.transparenttextures.com/patterns/stardust.png");
            background-color: #FFF0F5;
            background-attachment: fixed;
        }

        /* Titel-Styling mit Glow */
        h1 {
            color: #FF1493 !important;
            text-shadow: 2px 2px 8px #FFB6C1, 0 0 20px #FFF;
            text-align: center;
        }

        /* Buttons mit Glitzer-Animation */
        .stButton>button, .stDownloadButton>button {
            background: linear-gradient(45deg, #FF69B4, #FF1493, #FF69B4);
            background-size: 200% 200%;
            color: white !important;
            border: 2px solid #FFF;
            border-radius: 20px;
            animation: glitter-animation 3s ease infinite;
            font-weight: bold;
        }

        @keyframes glitter-animation {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        /* File Uploader Box */
        [data-testid="stFileUploadDropzone"] {
            background-color: rgba(255, 255, 255, 0.6);
            border: 2px dashed #FF69B4;
            border-radius: 15px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

def extract_xml_data_to_df(xml_file):
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
                    "Ultimativer Schuldnername": None,
                    "Debitor": None,
                    "Zusätzliche Remittanzinformationen": None,
                    "Adresse": None,
                }
                tx_amt = transaction.find(f'.//{{{namespace}}}TxAmt//{{{namespace}}}Amt')
                if tx_amt is not None:
                    currency = tx_amt.attrib.get("Ccy", "CHF")
                    data["Transaktionsbetrag"] = f"{currency} {float(tx_amt.text):,.2f}".replace(",", " ")

                dbtr_name = transaction.find(f'.//{{{namespace}}}Dbtr//{{{namespace}}}Nm')
                if dbtr_name is not None:
                    data["Debitor"] = dbtr_name.text

                addtl_rmt_inf = transaction.find(f'.//{{{namespace}}}AddtlRmtInf')
                if addtl_rmt_inf is not None:
                    data["Zusätzliche Remittanzinformationen"] = addtl_rmt_inf.text

                extracted_data.append(data)
        return pd.DataFrame(extracted_data)
    except Exception as e:
        st.error(f"Fehler: {e}")
        return pd.DataFrame()

# --- UI LAYOUT ---
st.set_page_config(page_title="Glitzer XML Converter", page_icon="✨")
apply_glitter_theme()

st.title("✨ XML Magic Converter ✨")
st.write("Verwandle deine XML-Daten in glänzende Excel-Tabellen!")

uploaded_files = st.file_uploader("Wähle XML-Dateien", accept_multiple_files=True, type=['xml'])

if uploaded_files:
    dfs = [extract_xml_data_to_df(f) for f in uploaded_files]
    combined_df = pd.concat(dfs, ignore_index=True) if dfs else None

    if combined_df is not None:
        st.dataframe(combined_df)
        excel_file = "glitzer_export.xlsx"
        combined_df.to_excel(excel_file, index=False)
        
        with open(excel_file, "rb") as f:
            st.download_button("💖 Excel mit Glitzer herunterladen 💖", f, file_name=excel_file)
