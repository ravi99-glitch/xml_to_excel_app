import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st
import pytz
import io
from datetime import datetime

# --- VERBESSERTE EXTRAKTIONS-LOGIK MIT GUTSCHRIFT/BELASTUNG ---
def extract_xml_data_to_df(xml_file):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        namespace = root.tag.split('}')[0].strip('{') if '}' in root.tag else ''
        ns = {"n": namespace} if namespace else {}
        
        extracted_data = []
        entries = root.findall('.//n:Ntry', ns) if ns else root.findall('.//Ntry')

        for entry in entries:
            # Eindeutige Referenz zur Duplikat-Erkennung
            bank_ref = entry.find('.//n:AcctSvcrRef', ns)
            ref_id = bank_ref.text if bank_ref is not None else "Keine ID"
            
            # Datum
            bookg_date = entry.find('.//n:BookgDt//n:Dt', ns) if ns else entry.find('.//BookgDt//Dt')
            date_val = pd.to_datetime(bookg_date.text).strftime('%d.%m.%Y') if bookg_date is not None else ""
            
            # Gutschrift oder Belastung (CRDT = Credit, DBIT = Debit)
            indicator = entry.find('.//n:CdtDbtInd', ns)
            typ = "Gutschrift" if indicator is not None and indicator.text == "CRDT" else "Belastung"

            transactions = entry.findall('.//n:TxDtls', ns) if ns else entry.findall('.//TxDtls')

            if transactions:
                for tx in transactions:
                    # Namenssuche
                    dbtr_name = tx.find('.//n:Dbtr//n:Nm', ns) or tx.find('.//n:UltmtDbtr//n:Nm', ns)
                    # Falls es eine Belastung ist, suchen wir beim Creditor (Empfänger)
                    cdtr_name = tx.find('.//n:Cdtr//n:Nm', ns)
                    
                    if dbtr_name is not None:
                        name = dbtr_name.text
                    elif cdtr_name is not None:
                        name = f"An: {cdtr_name.text}"
                    else:
                        name = None

                    # Betrag
                    amt_node = tx.find('.//n:TxAmt//n:Amt', ns) or tx.find('.//n:Amt', ns)
                    betrag = float(amt_node.text) if amt_node is not None else 0.0

                    # Bemerkung
                    ustrd = tx.find('.//n:RmtInf/n:Ustrd', ns)
                    ref = tx.find('.//n:RmtInf//n:Ref', ns)
                    bemerkung = (ustrd.text if ustrd is not None else "") + (" " + ref.text if ref is not None else "")

                    extracted_data.append({
                        "ID": ref_id,
                        "Datum": date_val,
                        "Art": typ,
                        "Partner / Mieter": name,
                        "Betrag": betrag,
                        "Bemerkung": bemerkung.strip() or "-"
                    })
            else:
                # Fallback für Sammelbuchungen
                amt_node = entry.find('./n:Amt', ns)
                inf_node = entry.find('./n:AddtlNtryInf', ns)
                
                extracted_data.append({
                    "ID": ref_id,
                    "Datum": date_val,
                    "Art": typ,
                    "Partner / Mieter": None,
                    "Betrag": float(amt_node.text) if amt_node is not None else 0.0,
                    "Bemerkung": inf_node.text if inf_node is not None else "Sammelbuchung"
                })
                
        return pd.DataFrame(extracted_data)
    except Exception as e:
        return pd.DataFrame()

# --- STREAMLIT UI ---
st.set_page_config(page_title="Mieteingang-Konverter", page_icon="🏠", layout="wide")
st.title("🏠 Bank-XML Konverter (Gutschrift/Belastung)")

uploaded_files = st.file_uploader("XML-Dateien hochladen", accept_multiple_files=True, type=['xml'])

if uploaded_files:
    all_dfs = [extract_xml_data_to_df(f) for f in uploaded_files]
    if all_dfs:
        df = pd.concat(all_dfs, ignore_index=True)
        
        # Duplikate filtern (ID und Betrag müssen gleich sein)
        df = df.sort_values(by="Partner / Mieter", ascending=False)
        df = df.drop_duplicates(subset=["ID", "Betrag"], keep="first")
        
        # Namen korrigieren, falls leer
        df["Partner / Mieter"] = df["Partner / Mieter"].fillna("Keine Details in dieser Datei")
        
        # Spalten sortieren
        final_df = df[["Datum", "Art", "Partner / Mieter", "Betrag", "Bemerkung"]]
        
        # Anzeige
        st.subheader("Bereinigte Transaktionsliste")
        
        # Optional: Nur Gutschriften anzeigen?
        nur_gutschriften = st.checkbox("Nur Gutschriften (Einnahmen) anzeigen", value=False)
        if nur_gutschriften:
            final_df = final_df[final_df["Art"] == "Gutschrift"]

        st.dataframe(final_df, use_container_width=True)
        
        # Summen-Berechnung
        gutschriften_summe = final_df[final_df["Art"] == "Gutschrift"]["Betrag"].sum()
        belastungen_summe = final_df[final_df["Art"] == "Belastung"]["Betrag"].sum()
        
        col1, col2 = st.columns(2)
        col1.metric("Summe Gutschriften", f"{gutschriften_summe:,.2f} CHF")
        col2.metric("Summe Belastungen", f"{belastungen_summe:,.2f} CHF")
        
        # Excel Export
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            final_df.to_excel(writer, index=False, sheet_name='Zahlungen')
        
        st.download_button(label="📊 Excel herunterladen", data=buffer.getvalue(), file_name="Bank_Export_Bereinigt.xlsx")
