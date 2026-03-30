import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st
import pytz
import io
from datetime import datetime

def extract_xml_data_to_df(xml_file):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        namespace = root.tag.split('}')[0].strip('{') if '}' in root.tag else ''
        ns = {"n": namespace} if namespace else {}
        
        extracted_data = []
        entries = root.findall('.//n:Ntry', ns) if ns else root.findall('.//Ntry')

        for entry in entries:
            bookg_date = entry.find('.//n:BookgDt//n:Dt', ns) if ns else entry.find('.//BookgDt//Dt')
            date_val = pd.to_datetime(bookg_date.text).strftime('%d.%m.%Y') if bookg_date is not None else "Unbekannt"
            
            # Suche nach ALLEN Transaktionsdetails (TxDtls) im Eintrag
            transactions = entry.findall('.//n:TxDtls', ns) if ns else entry.findall('.//TxDtls')

            if transactions:
                for tx in transactions:
                    # Suche Namen in allen möglichen Feldern (Debtor, Ultimate Debtor, etc.)
                    # Wir gehen hier sehr tief in die Struktur
                    possible_name_paths = [
                        './/n:Dbtr/n:Nm', 
                        './/n:UltmtDbtr/n:Nm',
                        './/n:RltdPties/n:Dbtr/n:Nm',
                        './/n:RltdPties/n:Cdtr/n:Nm'
                    ]
                    
                    name = "Name nicht gefunden"
                    for path in possible_name_paths:
                        found_node = tx.find(path, ns) if ns else tx.find(path.replace('n:', ''))
                        if found_node is not None and found_node.text:
                            name = found_node.text
                            break

                    amt_node = tx.find('.//n:TxAmt//n:Amt', ns) or tx.find('.//n:Amt', ns)
                    betrag = float(amt_node.text) if amt_node is not None else 0.0

                    # Bemerkung extrahieren
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
                # Fallback für Dateien ohne Details (wie dein Screenshot)
                amt_node = entry.find('./n:Amt', ns)
                inf_node = entry.find('./n:AddtlNtryInf', ns)
                
                # Wenn wir im Infotext "Sammelbuchung" oder "QR reference" finden, 
                # geben wir einen Hinweis auf die camt.054 Datei
                info_text = inf_node.text if inf_node is not None else "Keine Details"
                
                extracted_data.append({
                    "Datum": date_val,
                    "Mieter / Einzahler": "⚠️ Fehlende Details (Bitte camt.054 nutzen)",
                    "Betrag": float(amt_node.text) if amt_node is not None else 0.0,
                    "Bemerkung": info_text
                })
                
        return pd.DataFrame(extracted_data)
    except Exception as e:
        st.error(f"Fehler: {e}")
        return pd.DataFrame()

# --- STREAMLIT UI ---
st.set_page_config(page_title="Mieteingangs-Tool", page_icon="🏢", layout="wide")
st.title("🏢 Mieteingänge aus Bank-XML extrahieren")

uploaded_files = st.file_uploader("XML-Dateien hochladen (Tipp: camt.054 für volle Details)", accept_multiple_files=True, type=['xml'])

if uploaded_files:
    dfs = [extract_xml_data_to_df(f) for f in uploaded_files]
    final_df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    if not final_df.empty:
        st.subheader("Gefundene Zahlungen")
        st.dataframe(final_df, use_container_width=True)
        
        # Excel Download
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            final_df.to_excel(writer, index=False, sheet_name='Zahlungen')
        st.download_button(label="📊 Excel herunterladen", data=buffer.getvalue(), file_name="Mieteingange.xlsx")
