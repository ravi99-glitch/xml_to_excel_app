import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st
import pytz
import io
from datetime import datetime

# --- DIE MASTER-LOGIK: FINDET MIETER + ZUSATZINFOS ---
def extract_xml_data_to_df(xml_file):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        namespace = root.tag.split('}')[0].strip('{') if '}' in root.tag else ''
        ns = {"n": namespace} if namespace else {}
        
        extracted_data = []
        entries = root.findall('.//n:Ntry', ns) if ns else root.findall('.//Ntry')

        for entry in entries:
            # 1. Eindeutige Bank-Referenz (wichtig für Duplikats-Filter)
            bank_ref = entry.find('.//n:AcctSvcrRef', ns)
            ref_id = bank_ref.text if bank_ref is not None else "Keine ID"
            
            # 2. Datum & Art (Gutschrift/Belastung)
            bookg_date = entry.find('.//n:BookgDt//n:Dt', ns) if ns else entry.find('.//BookgDt//Dt')
            date_val = pd.to_datetime(bookg_date.text).strftime('%d.%m.%Y') if bookg_date is not None else ""
            
            indicator = entry.find('.//n:CdtDbtInd', ns)
            typ = "Gutschrift" if indicator is not None and indicator.text == "CRDT" else "Belastung"

            # 3. Info auf Beleg-Ebene (z.B. "Credit QR reference")
            entry_addtl_inf = entry.find('./n:AddtlNtryInf', ns)
            entry_inf_text = entry_addtl_inf.text if entry_addtl_inf is not None else ""

            transactions = entry.findall('.//n:TxDtls', ns) if ns else entry.findall('.//TxDtls')

            if transactions:
                for tx in transactions:
                    # --- MIETER-SUCHE (DEEP SCAN) ---
                    # Wir suchen in allen möglichen Pfaden nach dem Namen
                    possible_names = [
                        tx.find('.//n:Dbtr/n:Nm', ns), 
                        tx.find('.//n:UltmtDbtr/n:Nm', ns),
                        tx.find('.//n:RltdPties/n:Dbtr/n:Nm', ns),
                        tx.find('.//n:RltdPties/n:UltmtDbtr/n:Nm', ns)
                    ]
                    
                    name = None
                    for node in possible_names:
                        if node is not None and node.text:
                            name = node.text
                            break
                    
                    # Falls Belastung, Empfänger suchen
                    if not name and typ == "Belastung":
                        cdtr = tx.find('.//n:Cdtr/n:Nm', ns)
                        if cdtr is not None: name = f"An: {cdtr.text}"

                    # --- BETRAG ---
                    amt_node = tx.find('.//n:TxAmt//n:Amt', ns) or tx.find('.//n:Amt', ns)
                    betrag = float(amt_node.text) if amt_node is not None else 0.0

                    # --- BEMERKUNG (Referenzen) ---
                    ustrd = tx.find('.//n:RmtInf/n:Ustrd', ns)
                    ref = tx.find('.//n:RmtInf//n:Ref', ns)
                    bemerkung = (ustrd.text if ustrd is not None else "") + (" " + ref.text if ref is not None else "")

                    # --- ZUSÄTZLICHE INFOS ---
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
                # Fallback für Dateien ohne TxDtls (z.B. camt.053 Sammelbuchung)
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

st.title("🏠 Bank-XML Master-Konverter")
st.markdown("Lade `camt.053` und `camt.054` gleichzeitig hoch für maximale Details.")

uploaded_files = st.file_uploader("XML-Dateien hier reinziehen", accept_multiple_files=True, type=['xml'])

if uploaded_files:
    all_dfs = [extract_xml_data_to_df(f) for f in uploaded_files]
    if all_dfs:
        df = pd.concat(all_dfs, ignore_index=True)
        
        # --- INTELLIGENTER DUPLIKAT-FILTER ---
        # Wir sortieren so, dass Zeilen MIT Namen (aus camt.054) oben stehen
        df = df.sort_values(by="Partner / Mieter", ascending=False, na_position='last')
        # Wir löschen Duplikate (gleiche Bank-ID + gleicher Betrag), behalten aber den ersten (den mit Namen)
        df = df.drop_duplicates(subset=["ID", "Betrag"], keep="first")
        
        # Falls immer noch kein Name da ist (weil camt.054 fehlte)
        df["Partner / Mieter"] = df["Partner / Mieter"].fillna("⚠️ Name fehlt (camt.054 hochladen)")
        
        # Spalten-Auswahl und Reihenfolge
        final_df = df[["Datum", "Art", "Partner / Mieter", "Betrag", "Bemerkung", "Zusätzliche Informationen"]]
        
        # --- ANZEIGE ---
        st.subheader("Bereinigte Mieterliste")
        
        # Filter für Gutschriften
        nur_gut = st.checkbox("Nur Gutschriften (Mieteingänge) anzeigen", value=True)
        if nur_gut:
            final_df = final_df[final_df["Art"] == "Gutschrift"]

        st.dataframe(final_df, use_container_width=True)
        
        # Summen-Metriken
        gut_sum = final_df[final_df["Art"] == "Gutschrift"]["Betrag"].sum()
        bel_sum = final_df[final_df["Art"] == "Belastung"]["Betrag"].sum()
        
        c1, c2 = st.columns(2)
        c1.metric("Summe Mieteingänge", f"{gut_sum:,.2f} CHF")
        if not nur_gut:
            c2.metric("Summe Ausgaben", f"{bel_sum:,.2f} CHF")
        
        # Excel Export
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            final_df.to_excel(writer, index=False, sheet_name='Zahlungen')
        
        st.download_button(label="📊 Excel Datei speichern", data=buffer.getvalue(), file_name="Mieteingänge_Export.xlsx")
