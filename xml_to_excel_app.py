import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st
import pytz
import io
from datetime import datetime

# --- EXTRAKTIONS-LOGIK ---
def extract_xml_data_to_df(xml_file):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        namespace = root.tag.split('}')[0].strip('{') if '}' in root.tag else ''
        ns = {"n": namespace} if namespace else {}
        
        extracted_data = []
        entries = root.findall('.//n:Ntry', ns) if ns else root.findall('.//Ntry')

        for entry in entries:
            bank_ref = entry.find('.//n:AcctSvcrRef', ns)
            ref_id = bank_ref.text if bank_ref is not None else "Keine ID"
            
            bookg_date = entry.find('.//n:BookgDt//n:Dt', ns) if ns else entry.find('.//BookgDt//Dt')
            date_val = pd.to_datetime(bookg_date.text).strftime('%d.%m.%Y') if bookg_date is not None else ""
            
            indicator = entry.find('.//n:CdtDbtInd', ns)
            typ = "Gutschrift" if indicator is not None and indicator.text == "CRDT" else "Belastung"

            entry_addtl_inf = entry.find('./n:AddtlNtryInf', ns)
            entry_inf_text = entry_addtl_inf.text if entry_addtl_inf is not None else ""

            transactions = entry.findall('.//n:TxDtls', ns) if ns else entry.findall('.//TxDtls')

            if transactions:
                for tx in transactions:
                    # Mieter-Suche
                    possible_names = [
                        tx.find('.//n:Dbtr/n:Nm', ns), 
                        tx.find('.//n:UltmtDbtr/n:Nm', ns),
                        tx.find('.//n:RltdPties/n:Dbtr/n:Nm', ns),
                        tx.find('.//n:RltdPties/n:UltmtDbtr/n:Nm', ns)
                    ]
                    name = next((node.text for node in possible_names if node is not None and node.text), None)
                    
                    if not name and typ == "Belastung":
                        cdtr = tx.find('.//n:Cdtr/n:Nm', ns)
                        if cdtr is not None: name = f"An: {cdtr.text}"

                    amt_node = tx.find('.//n:TxAmt//n:Amt', ns) or tx.find('.//n:Amt', ns)
                    betrag = float(amt_node.text) if amt_node is not None else 0.0

                    ustrd = tx.find('.//n:RmtInf/n:Ustrd', ns)
                    ref = tx.find('.//n:RmtInf//n:Ref', ns)
                    bemerkung = (ustrd.text if ustrd is not None else "") + (" " + ref.text if ref is not None else "")

                    tx_addtl_inf = tx.find('.//n:AddtlTxInf', ns)
                    zusatz_info = tx_addtl_inf.text if tx_addtl_inf is not None else entry_inf_text

                    extracted_data.append({
                        "ID": ref_id,
                        "Datum": date_val,
                        "Art": typ,
                        "Partner / Mieter": name,
                        "Betrag": betrag,
                        "Bemerkung": bemerkung.strip() or "-",
                        "Zusatzinfo": zusatz_info or "-",
                        "Quelle": xml_file.name
                    })
            else:
                amt_node = entry.find('./n:Amt', ns)
                extracted_data.append({
                    "ID": ref_id,
                    "Datum": date_val,
                    "Art": typ,
                    "Partner / Mieter": None,
                    "Betrag": float(amt_node.text) if amt_node is not None else 0.0,
                    "Bemerkung": "-",
                    "Zusatzinfo": entry_inf_text or "Sammelbuchung",
                    "Quelle": xml_file.name
                })
        return pd.DataFrame(extracted_data)
    except Exception:
        return pd.DataFrame()

# --- APP ---
st.set_page_config(page_title="Miet-Konverter", layout="wide")
st.title("🏠 Bank-XML mit Duplikat-Vermerk")

files = st.file_uploader("XML-Dateien hochladen", accept_multiple_files=True, type=['xml'])

if files:
    all_data = pd.concat([extract_xml_data_to_df(f) for f in files], ignore_index=True)
    
    if not all_data.empty:
        # Sortieren: ID wichtig, Partner/Mieter (damit Zeilen mit Namen oben stehen)
        all_data = all_data.sort_values(by=["ID", "Partner / Mieter"], ascending=[True, False], na_position='last')
        
        # --- DUPLIKAT-VERMERK LOGIK ---
        # Markiert alle Zeilen, die dieselbe ID und denselben Betrag haben, außer der ersten
        all_data["Status"] = "✅ Original / Primär"
        is_dup = all_data.duplicated(subset=["ID", "Betrag"], keep='first')
        all_data.loc[is_dup, "Status"] = "📂 Duplikat (Wiederholung)"
        
        all_data["Partner / Mieter"] = all_data["Partner / Mieter"].fillna("Keine Details")
        
        # Anzeige-Spalten
        display_df = all_data[["Status", "Datum", "Art", "Partner / Mieter", "Betrag", "Bemerkung", "Zusatzinfo", "Quelle"]]
        
        st.subheader("Alle extrahierten Transaktionen")
        st.dataframe(display_df, use_container_width=True)
        
        # Echte Summe berechnen (nur Originale zählen!)
        echte_summe = all_data[all_data["Status"] == "✅ Original / Primär"]["Betrag"].sum()
        st.metric("Bereinigte Gesamtsumme (ohne Duplikate)", f"{echte_summe:,.2f} CHF")
        
        # Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            display_df.to_excel(writer, index=False, sheet_name='Zahlungen')
        st.download_button("📊 Liste als Excel speichern", buffer.getvalue(), "Bank_Export_mit_Vermerk.xlsx")
