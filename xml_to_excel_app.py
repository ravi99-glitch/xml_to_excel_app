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
        
        # Namespace-Handling: Extrahiere den Namespace aus dem Root-Tag
        namespace = root.tag.split('}')[0].strip('{') if '}' in root.tag else ''
        ns = {"n": namespace} if namespace else {}
        
        extracted_data = []
        # Suche nach allen Buchungseinträgen (Ntry)
        entries = root.findall('.//n:Ntry', ns) if ns else root.findall('.//Ntry')

        for entry in entries:
            # 1. Buchungsdatum finden
            bookg_date = entry.find('.//n:BookgDt//n:Dt', ns) if ns else entry.find('.//BookgDt//Dt')
            bookg_date_str = pd.to_datetime(bookg_date.text).strftime('%d.%m.%Y') if bookg_date is not None else "Unbekannt"
            
            # 2. Prüfen, ob detaillierte Transaktionsinformationen (TxDtls) vorhanden sind
            transactions = entry.findall('.//n:TxDtls', ns) if ns else entry.findall('.//TxDtls')

            if transactions:
                # Fall A: Einzeltransaktionen sind vorhanden
                for transaction in transactions:
                    data = {
                        "Buchungsdatum": bookg_date_str,
                        "Transaktionsbetrag": None,
                        "Währung": "CHF",
                        "Debitor/Info": "Nicht gefunden"
                    }
                    
                    # Betrag und Währung
                    tx_amt = transaction.find('.//n:TxAmt//n:Amt', ns) if ns else transaction.find('.//TxAmt//Amt')
                    if tx_amt is not None:
                        data["Währung"] = tx_amt.attrib.get("Ccy", "CHF")
                        data["Transaktionsbetrag"] = float(tx_amt.text)

                    # Debitor Name
                    dbtr_name = transaction.find('.//n:Dbtr//n:Nm', ns) if ns else transaction.find('.//Dbtr//Nm')
                    if dbtr_name is not None:
                        data["Debitor/Info"] = dbtr_name.text
                    
                    extracted_data.append(data)
            else:
                # Fall B: Sammelbuchung (Daten liegen direkt auf Ntry-Ebene, wie in deiner Datei)
                amt_node = entry.find('./n:Amt', ns) if ns else entry.find('./Amt')
                inf_node = entry.find('./n:AddtlNtryInf', ns) if ns else entry.find('./AddtlNtryInf')
                
                data = {
                    "Buchungsdatum": bookg_date_str,
                    "Transaktionsbetrag": float(amt_node.text) if amt_node is not None else 0.0,
                    "Währung": amt_node.attrib.get('Ccy', 'CHF') if amt_node is not None else "CHF",
                    "Debitor/Info": inf_node.text if inf_node is not None else "Sammelbuchung / Keine Details"
                }
                extracted_data.append(data)
                
        return pd.DataFrame(extracted_data)
    except Exception as e:
        st.error(f"Fehler bei der Verarbeitung einer Datei: {e}")
        return pd.DataFrame()

# --- STREAMLIT UI ---
st.set_page_config(page_title="XML Converter", page_icon="📊", layout="wide")

st.title("📊 Professioneller XML Daten-Export")
st.info("Dieses Tool konvertiert CAMT-Bankdateien (z.B. von UBS, Credit Suisse, ZKB) in eine übersichtliche Excel-Liste.")

uploaded_files = st.file_uploader("XML-Dateien hier hochladen", accept_multiple_files=True, type=['xml'])

if uploaded_files:
    all_dfs = []
    for f in uploaded_files:
        df = extract_xml_data_to_df(f)
        if not df.empty:
            all_dfs.append(df)
    
    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
        
        # Anzeige in der App
        st.subheader("Vorschau der extrahierten Daten")
        st.dataframe(combined_df, use_container_width=True)
        
        # --- EXCEL EXPORT ---
        # Zeitstempel für den Dateinamen
        tz = pytz.timezone('Europe/Zurich')
        now = datetime.now(tz)
        datum_heute = now.strftime("%Y-%m-%d_%H-%M")
        excel_name = f"Bank_Export_{datum_heute}.xlsx"
        
        # Datei im RAM erstellen
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            combined_df.to_excel(writer, index=False, sheet_name='Banktransaktionen')
        
        st.download_button(
            label="✅ Excel-Datei herunterladen",
            data=buffer.getvalue(),
            file_name=excel_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("In den hochgeladenen Dateien wurden keine verwertbaren Buchungsdaten gefunden.")

st.markdown("---")
st.caption("Hinweis: Dieses Tool verarbeitet die Daten lokal im Browser-Kontext und speichert keine Bankdaten dauerhaft.")
