import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st
import pytz
import io
from datetime import datetime

# --- PRO-LOGIK: GETRENNTE SPALTEN FÜR SOLL/HABEN ---
def extract_xml_data_to_df(xml_file):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        namespace = root.tag.split('}')[0].strip('{') if '}' in root.tag else ''
        ns = {"n": namespace} if namespace else {}
        
        extracted_data = []
        entries = root.findall('.//n:Ntry', ns) if ns else root.findall('.//n:Ntry', ns)

        for entry in entries:
            bank_ref = entry.find('.//n:AcctSvcrRef', ns)
            ref_id = bank_ref.text if bank_ref is not None else "Keine ID"
            
            bookg_date = entry.find('.//n:BookgDt//n:Dt', ns) if ns else entry.find('.//BookgDt//Dt')
            date_val = pd.to_datetime(bookg_date.text).strftime('%d.%m.%Y') if bookg_date is not None else ""
            
            # Richtung bestimmen: CRDT (Gutschrift) oder DBIT (Belastung)
            indicator = entry.find('.//n:CdtDbtInd', ns)
            is_credit = indicator is not None and indicator.text == "CRDT"

            entry_inf = entry.find('./n:AddtlNtryInf', ns)
            entry_inf_text = entry_inf.text if entry_inf is not None else ""

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
                    
                    if not name and not is_credit:
                        cdtr = tx.find('.//n:Cdtr/n:Nm', ns)
                        if cdtr is not None: name = f"An: {cdtr.text}"

                    amt_node = tx.find('.//n:TxAmt//n:Amt', ns) or tx.find('.//n:Amt', ns)
                    betrag = float(amt_node.text) if amt_node is not None else 0.0

                    # Zuteilung auf zwei Spalten
                    gutschrift = betrag if is_credit else 0.0
                    belastung = betrag if not is_credit else 0.0

                    # Zusatzinfo (Feld 2430...)
                    qr_zusatz = tx.find('.//n:RmtInf/n:Strd/n:AddtlRmtInf', ns)
                    tx_zusatz = tx.find('.//n:AddtlTxInf', ns)
                    final_zusatz = qr_zusatz.text if qr_zusatz is not None else (tx_zusatz.text if tx_zusatz is not None else entry_inf_text)

                    # Referenz
                    ref = tx.find('.//n:RmtInf//n:Ref', ns)
                    ustrd = tx.find('.//n:RmtInf/n:Ustrd', ns)
                    bemerkung = (ref.text if ref is not None else "") + (" | " + ustrd.text if ustrd is not None else "")

                    extracted_data.append({
                        "ID": ref_id,
                        "Datum": date_val,
                        "Partner / Mieter": name,
                        "Eingang (+)": gutschrift,
                        "Ausgang (-)": belastung,
                        "Bemerkung / Ref": bemerkung.strip(" | ") or "-",
                        "Zusatzinfo (z.B. 2430...)": final_zusatz or "-",
                        "Quelle": xml_file.name
                    })
            else:
                amt_node = entry.find('./n:Amt', ns)
                val = float(amt_node.text) if amt_node is not None else 0.0
                extracted_data.append({
                    "ID": ref_id, "Datum": date_val, "Partner / Mieter": None,
                    "Eingang (+)": val if is_credit else 0.0,
                    "Ausgang (-)": val if not is_credit else 0.0,
                    "Bemerkung / Ref": "-", "Zusatzinfo (z.B. 2430...)": entry_inf_text,
                    "Quelle": xml_file.name
                })
        return pd.DataFrame(extracted_data)
    except Exception:
        return pd.DataFrame()

# --- STREAMLIT UI ---
st.set_page_config(page_title="XML-Konverter", layout="wide")
st.title("🏠 XML - Konverter für Rechnungen")

files = st.file_uploader("XML-Dateien hochladen", accept_multiple_files=True, type=['xml'])

if files:
    all_dfs = [extract_xml_data_to_df(f) for f in files]
    df = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()

    if not df.empty:
        # Sortierung: Namen bevorzugen für Duplikat-Check
        df = df.sort_values(by=["ID", "Partner / Mieter"], ascending=[True, False], na_position='last')
        
        df["Status"] = "✅ Original"
        is_dup = df.duplicated(subset=["ID", "Eingang (+)", "Ausgang (-)"], keep='first')
        df.loc[is_dup, "Status"] = "📂 Duplikat"
        
        df["Partner / Mieter"] = df["Partner / Mieter"].fillna("Keine Details")

        # Spaltenreihenfolge für Profis
        cols = ["Status", "Datum", "Partner / Mieter", "Eingang (+)", "Ausgang (-)", "Bemerkung / Ref", "Zusatzinfo (z.B. 2430...)", "Quelle"]
        final_df = df[cols]
        
        st.subheader("Buchungsübersicht")
        st.dataframe(final_df, use_container_width=True)
        
        # Metriken
        original_df = df[df["Status"] == "✅ Original"]
        tot_in = original_df["Eingang (+)"].sum()
        tot_out = original_df["Ausgang (-)"].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Anzahl Buchungen", len(original_df))
        c2.metric("Total Eingänge", f"{tot_in:,.2f} CHF", delta_color="normal")
        c3.metric("Total Ausgänge", f"{tot_out:,.2f} CHF", delta="-")
        
        # Excel Export
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            final_df.to_excel(writer, index=False, sheet_name='Kontoauszug')
        
        st.download_button(
            label="📊 Professionelle Excel-Liste speichern",
            data=buffer.getvalue(),
            file_name=f"Bank_Pro_Export_{datetime.now().strftime('%d_%m_%Y')}.xlsx"
        )
