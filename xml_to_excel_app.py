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
            # 1. Datum
            bookg_date = entry.find('.//n:BookgDt//n:Dt', ns) if ns else entry.find('.//BookgDt//Dt')
            date_val = pd.to_datetime(bookg_date.text).strftime('%d.%m.%Y') if bookg_date is not None else ""
            
            # 2. Suche nach Transaktionsdetails (TxDtls)
            transactions = entry.findall('.//n:TxDtls', ns) if ns else entry.findall('.//TxDtls')

            if transactions:
                for tx in transactions:
                    # Tiefe Suche nach dem Namen des Einzahlers (Debtor)
                    # Wir prüfen verschiedene Pfade, falls die Bank den Namen verschachtelt
                    name_paths = [
                        './/n:Dbtr/n:Nm', 
                        './/n:UltmtDbtr/n:Nm',
                        './/n:RltdPties/n:Dbtr/n:Nm',
                        './/n:RltdPties/n:UltmtDbtr/n:Nm'
                    ]
                    
                    name = "Name nicht in Datei gefunden"
                    for path in name_paths:
                        found_node = tx.find(path, ns) if ns else tx.find(path.replace('n:', ''))
                        if found_node is not None and found_node.text:
                            name = found_node.text
                            break

                    # Betrag
                    amt_node = tx.find('.//n:TxAmt//n:Amt', ns) or tx.find('.//n:Amt', ns)
                    betrag = float(amt_node.text) if amt_node is not None else 0.0

                    # Bemerkung (Mitteilung oder Referenz)
                    ustrd = tx.find('.//n:RmtInf/n:Ustrd', ns)
                    ref = tx.find('.//n:RmtInf//n:Ref', ns)
                    bemerkung = (ustrd.text if ustrd is not None else "") + (" " + ref.text if ref is not None else "")

                    extracted_data.append({
                        "Datum": date_val,
                        "Mieter / Einzahler": name,
                        "Betrag": betrag,
                        "Bemerkung": bemerkung.strip() or "-"
                    })
            else:
                # Spezialfall: Sammelbuchung ohne Details (wie in deiner UBS-Datei)
                amt_node = entry.find('./n:Amt', ns)
                inf_node = entry.find('./n:AddtlNtryInf', ns)
                
                extracted_data.append({
                    "Datum": date_val,
                    "Mieter / Einzahler": "⚠️ Keine Details (Bitte camt.054 hochladen)",
                    "Betrag": float(amt_node.text) if amt_node is not None else 0.0,
                    "Bemerkung": inf_node.text if inf_node is not None else "Sammelbuchung"
                })
                
        return pd.DataFrame(extracted_data)
    except Exception as e:
        st.error(f"Fehler: {e}")
        return pd.DataFrame()

# --- STREAMLIT UI ---
st.set_page_config(page_title="Mieteingang-Konverter", page_icon="🏠", layout="wide")

st.title("🏠 Bank-Export für Mieteingänge")
st.info("Tipp: Wenn 'Keine Details' erscheint, lade zusätzlich die camt.054 Datei (Gutschriftsanzeige) aus deinem E-Banking hoch.")

uploaded_files = st.file_uploader("XML-Dateien hochladen", accept_multiple_files=True, type=['xml'])

if uploaded_files:
    dfs = [extract_xml_data_to_df(f) for f in uploaded_files]
    combined_df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    if not combined_df.empty:
        st.subheader("Extrahierte Zahlungen")
        st.dataframe(combined_df, use_container_width=True)
        
        # Excel Export
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            combined_df.to_excel(writer, index=False, sheet_name='Zahlungen')
        
        st.download_button(
            label="📊 Als Excel herunterladen",
            data=buffer.getvalue(),
            file_name=f"Mieteingange_Export.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
