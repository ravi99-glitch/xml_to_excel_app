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
            # Eindeutige Referenz der Bank (um Duplikate zu vermeiden)
            bank_ref = entry.find('.//n:AcctSvcrRef', ns)
            ref_id = bank_ref.text if bank_ref is not None else "Keine ID"
            
            bookg_date = entry.find('.//n:BookgDt//n:Dt', ns) if ns else entry.find('.//BookgDt//Dt')
            date_val = pd.to_datetime(bookg_date.text).strftime('%d.%m.%Y') if bookg_date is not None else ""
            
            transactions = entry.findall('.//n:TxDtls', ns) if ns else entry.findall('.//TxDtls')

            if transactions:
                for tx in transactions:
                    dbtr_name = tx.find('.//n:Dbtr//n:Nm', ns) or tx.find('.//n:UltmtDbtr//n:Nm', ns)
                    name = dbtr_name.text if dbtr_name is not None else "Name nicht gefunden"

                    amt_node = tx.find('.//n:TxAmt//n:Amt', ns) or tx.find('.//n:Amt', ns)
                    betrag = float(amt_node.text) if amt_node is not None else 0.0

                    ustrd = tx.find('.//n:RmtInf/n:Ustrd', ns)
                    ref = tx.find('.//n:RmtInf//n:Ref', ns)
                    bemerkung = (ustrd.text if ustrd is not None else "") + (" " + ref.text if ref is not None else "")

                    extracted_data.append({
                        "ID": ref_id, # Hilfsspalte für Duplikate
                        "Datum": date_val,
                        "Mieter / Einzahler": name,
                        "Betrag": betrag,
                        "Bemerkung": bemerkung.strip() or "-"
                    })
            else:
                amt_node = entry.find('./n:Amt', ns)
                inf_node = entry.find('./n:AddtlNtryInf', ns)
                
                extracted_data.append({
                    "ID": ref_id,
                    "Datum": date_val,
                    "Mieter / Einzahler": None, # Wir lassen es leer, falls es ein camt.053 ohne Namen ist
                    "Betrag": float(amt_node.text) if amt_node is not None else 0.0,
                    "Bemerkung": inf_node.text if inf_node is not None else "Sammelbuchung"
                })
                
        return pd.DataFrame(extracted_data)
    except Exception as e:
        return pd.DataFrame()

# --- STREAMLIT UI ---
st.set_page_config(page_title="Mieteingang-Konverter", page_icon="🏠", layout="wide")
st.title("🏠 Mieteingänge (Ohne Duplikate)")

uploaded_files = st.file_uploader("Alle XML-Dateien hochladen", accept_multiple_files=True, type=['xml'])

if uploaded_files:
    all_dfs = [extract_xml_data_to_df(f) for f in uploaded_files]
    if all_dfs:
        df = pd.concat(all_dfs, ignore_index=True)
        
        # --- LOGIK GEGEN DOPPELTE EINTRÄGE ---
        # 1. Wir sortieren so, dass Zeilen MIT Namen oben stehen
        df = df.sort_values(by="Mieter / Einzahler", ascending=False)
        # 2. Wir löschen Duplikate basierend auf der Bank-ID (ID)
        df = df.drop_duplicates(subset=["ID", "Betrag"], keep="first")
        # 3. Falls noch "None" im Namen steht, ersetzen wir es durch Info
        df["Mieter / Einzahler"] = df["Mieter / Einzahler"].fillna("Details fehlen (camt.054 nötig)")
        
        # Spalten für die Anzeige aufräumen
        final_df = df[["Datum", "Mieter / Einzahler", "Betrag", "Bemerkung"]]
        
        st.subheader("Bereinigte Liste")
        st.dataframe(final_df, use_container_width=True)
        st.write(f"**Echte Anzahl Zahlungen:** {len(final_df)} | **Gesamtsumme:** {final_df['Betrag'].sum():,.2f} CHF")
        
        # Excel Export
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            final_df.to_excel(writer, index=False, sheet_name='Zahlungen')
        st.download_button(label="📊 Bereinigte Excel herunterladen", data=buffer.getvalue(), file_name="Mieteingange_Clean.xlsx")
