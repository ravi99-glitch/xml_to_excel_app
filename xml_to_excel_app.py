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
        
        # Namespace-Handling
        namespace = root.tag.split('}')[0].strip('{') if '}' in root.tag else ''
        ns = {"n": namespace} if namespace else {}
        
        extracted_data = []
        entries = root.findall('.//n:Ntry', ns) if ns else root.findall('.//Ntry')

        for entry in entries:
            # 1. Buchungsdatum
            bookg_date = entry.find('.//n:BookgDt//n:Dt', ns) if ns else entry.find('.//BookgDt//Dt')
            date_val = pd.to_datetime(bookg_date.text).strftime('%d.%m.%Y') if bookg_date is not None else ""
            
            # 2. Transaktionsdetails suchen
            transactions = entry.findall('.//n:TxDtls', ns) if ns else entry.findall('.//TxDtls')

            if transactions:
                for tx in transactions:
                    # --- NAME DES EINZAHLERS ---
                    # Suche in Debtor oder Ultimate Debtor
                    dbtr_name = tx.find('.//n:Dbtr//n:Nm', ns) or tx.find('.//n:UltmtDbtr//n:Nm', ns)
                    name = dbtr_name.text if dbtr_name is not None else "Unbekannter Einzahler"

                    # --- BETRAG ---
                    amt_node = tx.find('.//n:TxAmt//n:Amt', ns)
                    betrag = float(amt_node.text) if amt_node is not None else 0.0

                    # --- BEMERKUNG ---
                    # Wir suchen an verschiedenen Stellen nach der Mitteilung/Referenz
                    # 1. Unstrukturierte Info (Ustrd)
                    # 2. Strukturierte Referenz (QR-Referenz)
                    remittance = tx.find('.//n:RmtInf//n:Ustrd', ns)
                    qr_ref = tx.find('.//n:RmtInf//n:Strd//n:CdtrRefInf//n:Ref', ns)
                    
                    bemerkung = ""
                    if remittance is not None:
                        bemerkung = remittance.text
                    elif qr_ref is not None:
                        bemerkung = f"Ref: {qr_ref.text}"
                    else:
                        # Fallback auf allgemeine Info des Eintrags
                        add_inf = entry.find('.//n:AddtlNtryInf', ns)
                        bemerkung = add_inf.text if add_inf is not None else "-"

                    extracted_data.append({
                        "Datum": date_val,
                        "Einzahler / Mieter": name,
                        "Betrag": betrag,
                        "Bemerkung": bemerkung
                    })
            else:
                # Fallback für Sammelbuchungen ohne TxDtls (wie in deiner UBS-Datei)
                amt_node = entry.find('./n:Amt', ns)
                inf_node = entry.find('./n:AddtlNtryInf', ns)
                
                extracted_data.append({
                    "Datum": date_val,
                    "Einzahler / Mieter": "Siehe Bemerkung / Sammelbuchung",
                    "Betrag": float(amt_node.text) if amt_node is not None else 0.0,
                    "Bemerkung": inf_node.text if inf_node is not None else "-"
                })
                
        return pd.DataFrame(extracted_data)
    except Exception as e:
        st.error(f"Fehler: {e}")
        return pd.DataFrame()

# --- STREAMLIT UI ---
st.set_page_config(page_title="Mieteingang-Konverter", page_icon="🏠", layout="wide")

st.title("🏠 Bank-Export für Mieteingänge")
st.write("Extrahiert Einzahler, Betrag und Bemerkungen aus CAMT-Dateien.")

uploaded_files = st.file_uploader("XML-Dateien hochladen", accept_multiple_files=True, type=['xml'])

if uploaded_files:
    dfs = [extract_xml_data_to_df(f) for f in uploaded_files]
    combined_df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    if not combined_df.empty:
        # Spalten sortieren für bessere Übersicht
        combined_df = combined_df[["Datum", "Einzahler / Mieter", "Betrag", "Bemerkung"]]
        
        st.subheader("Vorschau der Daten")
        st.dataframe(combined_df, use_container_width=True)
        
        # Excel Export
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            combined_df.to_excel(writer, index=False, sheet_name='Zahlungen')
        
        tz = pytz.timezone('Europe/Zurich')
        date_str = datetime.now(tz).strftime("%d.%m.%Y")
        
        st.download_button(
            label="📊 Als Excel herunterladen",
            data=buffer.getvalue(),
            file_name=f"Mieteingänge_{date_str}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("Keine Daten gefunden. Prüfen Sie, ob die XML-Datei Buchungen enthält.")
