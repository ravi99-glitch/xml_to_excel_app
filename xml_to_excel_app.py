import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st
import pytz
import io
from datetime import datetime

# --- LOGIK ZUR DATENEXTRAKTION ---
def extract_xml_data_to_df(xml_file):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        # Namespace extrahieren
        namespace = root.tag.split('}')[0].strip('{') if '}' in root.tag else ''
        extracted_data = []
        
        # Suche nach Einträgen (Ntry)
        entries = root.findall(f'.//{{{namespace}}}Ntry') if namespace else root.findall('.//Ntry')

        for entry in entries:
            bookg_date = entry.find(f'.//{{{namespace}}}BookgDt//{{{namespace}}}Dt') if namespace else entry.find('.//BookgDt//Dt')
            bookg_date_str = pd.to_datetime(bookg_date.text).strftime('%d.%m.%Y') if bookg_date is not None else None
            
            transactions = entry.findall(f'.//{{{namespace}}}TxDtls') if namespace else entry.findall('.//TxDtls')

            for transaction in transactions:
                data = {
                    "Buchungsdatum": bookg_date_str,
                    "Transaktionsbetrag": None,
                    "Debitor": None
                }
                
                # Betrag und Währung
                tx_amt = transaction.find(f'.//{{{namespace}}}TxAmt//{{{namespace}}}Amt') if namespace else transaction.find('.//TxAmt//Amt')
                if tx_amt is not None:
                    currency = tx_amt.attrib.get("Ccy", "CHF")
                    data["Transaktionsbetrag"] = f"{currency} {float(tx_amt.text):,.2f}"

                # Debitor Name
                dbtr_name = transaction.find(f'.//{{{namespace}}}Dbtr//{{{namespace}}}Nm') if namespace else transaction.find('.//Dbtr//Nm')
                if dbtr_name is not None:
                    data["Debitor"] = dbtr_name.text

                extracted_data.append(data)
        return pd.DataFrame(extracted_data)
    except Exception as e:
        st.error(f"Fehler bei der Verarbeitung: {e}")
        return pd.DataFrame()

# --- APP START ---
st.set_page_config(page_title="XML Converter", page_icon="📄")

st.title("XML-Datenextraktion & Konvertierung")
st.write("Laden Sie Ihre XML-Dateien hoch, um sie in eine konsolidierte Excel-Liste umzuwandeln.")

uploaded_files = st.file_uploader("XML-Dateien auswählen", accept_multiple_files=True, type=['xml'])

if uploaded_files:
    dfs = [extract_xml_data_to_df(f) for f in uploaded_files]
    combined_df = pd.concat(dfs, ignore_index=True) if dfs else None

    if combined_df is not None and not combined_df.empty:
        st.success("Dateien erfolgreich verarbeitet!")
        st.dataframe(combined_df, use_container_width=True)
        
        # --- EXCEL EXPORT (IM SPEICHER) ---
        tz = pytz.timezone('Europe/Zurich')
        now = datetime.now(tz)
        datum_heute = now.strftime("%d.%m.%Y")
        excel_name = f"XML_Export_{datum_heute}.xlsx"
        
        # BytesIO nutzen, um Datei im RAM zu halten
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            combined_df.to_excel(writer, index=False, sheet_name='Daten')
        
        st.download_button(
            label="Excel-Datei herunterladen",
            data=buffer.getvalue(),
            file_name=excel_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    elif combined_df is not None and combined_df.empty:
        st.warning("Keine passenden Daten in den XML-Dateien gefunden.")
