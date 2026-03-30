import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st
import pytz
import io
from datetime import datetime

# --- VERBESSERTE EXTRAKTIONS-LOGIK ---
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
            # 1. Bank-Referenz (Eindeutige ID für Duplikat-Erkennung)
            bank_ref = entry.find('.//n:AcctSvcrRef', ns)
            ref_id = bank_ref.text if bank_ref is not None else "Keine ID"
            
            # 2. Datum & Buchungstyp
            bookg_date = entry.find('.//n:BookgDt//n:Dt', ns) if ns else entry.find('.//BookgDt//Dt')
            date_val = pd.to_datetime(bookg_date.text).strftime('%d.%m.%Y') if bookg_date is not None else ""
            
            indicator = entry.find('.//n:CdtDbtInd', ns)
            typ = "Gutschrift" if indicator is not None and indicator.text == "CRDT" else "Belastung"

            # 3. Allgemeine Bank-Information (Entry-Level)
            entry_inf = entry.find('./n:AddtlNtryInf', ns)
            entry_inf_text = entry_inf.text if entry_inf is not None else ""

            transactions = entry.findall('.//n:TxDtls', ns) if ns else entry.findall('.//TxDtls')

            if transactions:
                for tx in transactions:
                    # --- MIETER-SUCHE (DEEP SCAN) ---
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

                    # --- BETRAG ---
                    amt_node = tx.find('.//n:TxAmt//n:Amt', ns) or tx.find('.//n:Amt', ns)
                    betrag = float(amt_node.text) if amt_node is not None else 0.0

                    # --- ZUSÄTZLICHE INFORMATIONEN (Das Feld aus deinem Bild) ---
                    # Wir suchen gezielt nach AddtlRmtInf (QR-Zusatzinfo 2430...)
                    qr_zusatz = tx.find('.//n:RmtInf/n:Strd/n:AddtlRmtInf', ns)
                    tx_zusatz = tx.find('.//n:AddtlTxInf', ns)
                    
                    final_zusatz = qr_zusatz.text if qr_zusatz is not None else (tx_zusatz.text if tx_zusatz is not None else entry_inf_text)

                    # --- BEMERKUNG / REFERENZ ---
                    ref = tx.find('.//n:RmtInf//n:Ref', ns)
                    ustrd = tx.find('.//n:RmtInf/n:Ustrd', ns)
                    bemerkung = (ref.text if ref is not None else "") + (" | " + ustrd.text if ustrd is not None else "")

                    extracted_data.append({
                        "ID": ref_id,
                        "Datum": date_val,
                        "Art": typ,
                        "Partner / Mieter": name,
                        "Betrag": betrag,
                        "Bemerkung / Ref": bemerkung.strip(" | ") or "-",
                        "Zusatzinfo (z.B. 2430...)": final_zusatz or "-",
                        "Quelle": xml_file.name
                    })
            else:
                # Fallback für Sammelbuchungen ohne Transaktionsdetails
                amt_node = entry.find('./n:Amt', ns)
                extracted_data.append({
                    "ID": ref_id, "Datum": date_val, "Art": typ, "Partner / Mieter": None,
                    "Betrag": float(amt_node.text) if amt_node is not None else 0.0,
                    "Bemerkung / Ref": "-", "Zusatzinfo (z.B. 2430...)": entry_inf_text,
                    "Quelle": xml_file.name
                })
        return pd.DataFrame(extracted_data)
    except Exception:
        return pd.DataFrame()

# --- STREAMLIT OBERFLÄCHE ---
st.set_page_config(page_title="Mieteingang-Konverter", layout="wide")
st.title("🏠 Bank-XML Master-Konverter")
st.markdown("Lade `camt.053` und `camt.054` Dateien hoch. Duplikate werden markiert, aber nicht gelöscht.")

files = st.file_uploader("XML-Dateien auswählen", accept_multiple_files=True, type=['xml'])

if files:
    all_dfs = [extract_xml_data_to_df(f) for f in files]
    df = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()

    if not df.empty:
        # --- INTELLIGENTE SORTIERUNG & DUPLIKAT-CHECK ---
        # Wir sortieren so, dass Zeilen MIT Mietername (aus camt.054) oben stehen
        df = df.sort_values(by=["ID", "Partner / Mieter"], ascending=[True, False], na_position='last')
        
        # Duplikat-Vermerk setzen
        df["Status"] = "✅ Original"
        is_dup = df.duplicated(subset=["ID", "Betrag"], keep='first')
        df.loc[is_dup, "Status"] = "📂 Duplikat"
        
        df["Partner / Mieter"] = df["Partner / Mieter"].fillna("Keine Details (siehe Zusatzinfo)")

        # Spalten-Anordnung
        final_df = df[["Status", "Datum", "Art", "Partner / Mieter", "Betrag", "Bemerkung / Ref", "Zusatzinfo (z.B. 2430...)", "Quelle"]]
        
        # Anzeige
        st.subheader("Extrahierte Transaktionen")
        st.dataframe(final_df, use_container_width=True)
        
        # Metriken (Summen nur von Originalen!)
        original_df = df[df["Status"] == "✅ Original"]
        einnahmen = original_df[original_df["Art"] == "Gutschrift"]["Betrag"].sum()
        ausgaben = original_df[original_df["Art"] == "Belastung"]["Betrag"].sum()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Anzahl (Originale)", len(original_df))
        col2.metric("Summe Gutschriften", f"{einnahmen:,.2f} CHF")
        col3.metric("Summe Belastungen", f"{ausgaben:,.2f} CHF")
        
        # Excel Export
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            final_df.to_excel(writer, index=False, sheet_name='Zahlungen')
        
        st.download_button(
            label="📊 Als Excel speichern",
            data=buffer.getvalue(),
            file_name=f"Bank_Export_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
