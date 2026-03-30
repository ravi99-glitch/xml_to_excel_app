import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st
import pytz
import io
from datetime import datetime

# --- EXTRAKTIONS-LOGIK MIT ZUSÄTZLICHEN INFOS ---
def extract_xml_data_to_df(xml_file):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        namespace = root.tag.split('}')[0].strip('{') if '}' in root.tag else ''
        ns = {"n": namespace} if namespace else {}
        
        extracted_data = []
        entries = root.findall('.//n:Ntry', ns) if ns else root.findall('.//Ntry')

        for entry in entries:
            # Bank-ID für Duplikat-Check
            bank_ref = entry.find('.//n:AcctSvcrRef', ns)
            ref_id = bank_ref.text if bank_ref is not None else "Keine ID"
            
            # Datum & Art
            bookg_date = entry.find('.//n:BookgDt//n:Dt', ns) if ns else entry.find('.//BookgDt//Dt')
            date_val = pd.to_datetime(bookg_date.text).strftime('%d.%m.%Y') if bookg_date is not None else ""
            
            indicator = entry.find('.//n:CdtDbtInd', ns)
            typ = "Gutschrift" if indicator is not None and indicator.text == "CRDT" else "Belastung"

            # Information auf Beleg-Ebene (Entry)
            entry_addtl_inf = entry.find('./n:AddtlNtryInf', ns)
            entry_inf_text = entry_addtl_inf.text if entry_addtl_inf is not None else ""

            transactions = entry.findall('.//n:TxDtls', ns) if ns else entry.findall('.//TxDtls')

            if transactions:
                for tx in transactions:
                    # Partner finden
                    dbtr_name = tx.find('.//n:Dbtr//n:Nm', ns) or tx.find('.//n:UltmtDbtr//n:Nm', ns)
                    cdtr_name = tx.find('.//n:Cdtr//n:Nm', ns)
                    name = dbtr_name.text if dbtr_name is not None else (f"An: {cdtr_name.text}" if cdtr_name is not None else None)

                    # Betrag
                    amt_node = tx.find('.//n:TxAmt//n:Amt', ns) or tx.find('.//n:Amt', ns)
                    betrag = float(amt_node.text) if amt_node is not None else 0.0

                    # Bemerkung (Mitteilung / Referenz)
                    ustrd = tx.find('.//n:RmtInf/n:Ustrd', ns)
                    ref = tx.find('.//n:RmtInf//n:Ref', ns)
                    bemerkung = (ustrd.text if ustrd is not None else "") + (" " + ref.text if ref is not None else "")

                    # Zusätzliche Transaktions-Info (TxInf)
                    tx_addtl_inf = tx.find('.//n:AddtlTxInf', ns)
                    zusatz_info = tx_addtl_inf.text if tx_addtl_inf is not None else entry_inf_text

                    extracted_data.append({
                        "ID": ref_id,
                        "Datum": date_val,
                        "Art": typ,
                        "Partner / Mieter": name,
                        "Betrag": betrag,
                        "Bemerkung": bemerkung.strip() or "-",
                        "Zusätzliche Informationen": zusatz_info or "-"
                    })
            else:
                # Fallback für Sammelbuchungen
                amt_node = entry.find('./n:Amt', ns)
                extracted_data.append({
                    "ID": ref_id,
                    "Datum": date_val,
                    "Art": typ,
                    "Partner / Mieter": None,
                    "Betrag": float(amt_node.text) if amt_node is not None else 0.0,
                    "Bemerkung": "-",
                    "Zusätzliche Informationen": entry_inf_text or "Sammelbuchung"
                })
                
        return pd.DataFrame(extracted_data)
    except Exception as e:
        return pd.DataFrame()

# --- STREAMLIT UI ---
st.set_page_config(page_title="Mieteingang-Konverter", page_icon="🏠", layout="wide")
st.title("🏠 XML Konverter für Zahlungen")

uploaded_files = st.file_uploader("XML-Dateien hochladen", accept_multiple_files=True, type=['xml'])

if uploaded_files:
    all_dfs = [extract_xml_data_to_df(f) for f in uploaded_files]
    if all_dfs:
        df = pd.concat(all_dfs, ignore_index=True)
        
        # Duplikate filtern (ID und Betrag) - Bevorzugt Zeilen mit Namen
        df = df.sort_values(by="Partner / Mieter", ascending=False)
        df = df.drop_duplicates(subset=["ID", "Betrag"], keep="first")
        
        df["Partner / Mieter"] = df["Partner / Mieter"].fillna("Details in camt.054 suchen")
        
        # Neue Spaltenreihenfolge inkl. "Zusätzliche Informationen"
        final_df = df[["Datum", "Art", "Partner / Mieter", "Betrag", "Bemerkung", "Zusätzliche Informationen"]]
        
        st.subheader("Extrahiert & Bereinigt")
        st.dataframe(final_df, use_container_width=True)
        
        # Summen
        gut_sum = final_df[final_df["Art"] == "Gutschrift"]["Betrag"].sum()
        st.metric("Gesamtsumme Gutschriften", f"{gut_sum:,.2f} CHF")
        
        # Excel Export
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            final_df.to_excel(writer, index=False, sheet_name='Zahlungsliste')
        
        st.download_button(label="📊 Als Excel speichern", data=buffer.getvalue(), file_name="Bank_Export_Zusatzinfos.xlsx")
