import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st
import pytz
import openpyxl

# --- ULTIMATE PINK & FALLING GLITTER STYLING ---
def apply_glitter_rain():
    st.markdown(
        """
        <style>
        /* Hintergrund & Basis-Design */
        .stApp {
            background: linear-gradient(to bottom, #FFF0F5, #FFB6C1);
            background-attachment: fixed;
            overflow: hidden;
        }

        /* Titel-Styling */
        h1 {
            color: #FF1493 !important;
            text-shadow: 0 0 10px #FFF, 0 0 20px #FF69B4;
            text-align: center;
            font-family: 'Comic Sans MS', cursive;
        }

        /* Fallender Glitzer Effekt */
        @keyframes glitter-fall {
            0% { transform: translateY(-10vh) translateX(0) rotate(0deg); opacity: 1; }
            100% { transform: translateY(100vh) translateX(20px) rotate(360deg); opacity: 0; }
        }

        /* Erstellung der Partikel per CSS */
        .glitter {
            position: absolute;
            width: 8px;
            height: 8px;
            background: white;
            border-radius: 50%;
            box-shadow: 0 0 10px #FFF, 0 0 20px #FF69B4;
            animation: glitter-fall 5s linear infinite;
            z-index: 0;
        }

        /* Verschiedene Positionen für den Glitzer */
        .g1 { left: 10%; animation-duration: 4s; }
        .g2 { left: 30%; animation-duration: 6s; animation-delay: 1s; }
        .g3 { left: 50%; animation-duration: 3s; animation-delay: 2s; }
        .g4 { left: 70%; animation-duration: 7s; animation-delay: 0.5s; }
        .g5 { left: 90%; animation-duration: 5s; animation-delay: 3s; }

        /* Button Styling */
        .stButton>button, .stDownloadButton>button {
            background: linear-gradient(45deg, #FF69B4, #FF1493);
            color: white !important;
            border-radius: 50px;
            border: 2px solid white;
            box-shadow: 0 0 15px #FF1493;
            transition: 0.3s;
        }
        .stButton>button:hover {
            transform: scale(1.1);
            box-shadow: 0 0 25px #FF1493;
        }
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
st.write("Lade deine Dateien hoch und sieh zu, wie sie funkeln!")

uploaded_files = st.file_uploader("Wähle XML-Dateien", accept_multiple_files=True, type=['xml'])

if uploaded_files:
    dfs = [extract_xml_data_to_df(f) for f in uploaded_files]
    combined_df = pd.concat(dfs, ignore_index=True) if dfs else None

    if combined_df is not None:
        st.success("Dateien verarbeitet! ✨")
        st.dataframe(combined_df)
        
        excel_file = "glitzer_export.xlsx"
        combined_df.to_excel(excel_file, index=False)
        
        with open(excel_file, "rb") as f:
            st.download_button("💖 Download Glitzer-Excel 💖", f, file_name=excel_file)
