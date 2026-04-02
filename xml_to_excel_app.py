import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st
import io
from datetime import datetime

# --- ROBUSTE EXTRAKTIONS-LOGIK ---
def extract_xml_data_to_df(xml_file):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Namespace
        namespace = root.tag.split('}')[0].strip('{') if '}' in root.tag else ''
        ns = {"n": namespace} if namespace else {}

        extracted_data = []
        entries = root.findall('.//n:Ntry', ns) if ns else root.findall('.//Ntry')

        for entry in entries:
            # Referenz
            bank_ref = entry.find('.//n:AcctSvcrRef', ns)
            ref_id = bank_ref.text if bank_ref is not None else "Keine ID"

            # Datum
            bookg_date = entry.find('.//n:BookgDt//n:Dt', ns) if ns else entry.find('.//BookgDt//Dt')
            date_obj = pd.to_datetime(bookg_date.text) if bookg_date is not None else None

            # Richtung
            indicator = entry.find('.//n:CdtDbtInd', ns)
            is_credit = indicator is not None and indicator.text == "CRDT"

            entry_inf = entry.find('./n:AddtlNtryInf', ns)
            entry_inf_text = entry_inf.text if entry_inf is not None else ""

            transactions = entry.findall('.//n:TxDtls', ns) if ns else entry.findall('.//TxDtls')

            if transactions:
                for tx in transactions:

                    # --- NAME EXTRACTION (ROBUST) ---
                    possible_names = [
                        tx.find('.//n:Dbtr/n:Nm', ns),
                        tx.find('.//n:UltmtDbtr/n:Nm', ns),
                        tx.find('.//n:RltdPties/n:Dbtr/n:Nm', ns),
                        tx.find('.//n:RltdPties/n:UltmtDbtr/n:Nm', ns),
                        tx.find('.//n:Cdtr/n:Nm', ns),
                        tx.find('.//n:UltmtCdtr/n:Nm', ns),
                        tx.find('.//n:RltdPties/n:Cdtr/n:Nm', ns),
                        tx.find('.//n:RltdPties/n:UltmtCdtr/n:Nm', ns),
                    ]

                    name = next((node.text for node in possible_names if node is not None and node.text), None)

                    # Fallback Logik (richtungsabhängig)
                    if not name:
                        if is_credit:
                            dbtr = tx.find('.//n:Dbtr/n:Nm', ns)
                            if dbtr is not None and dbtr.text:
                                name = dbtr.text
                        else:
                            cdtr = tx.find('.//n:Cdtr/n:Nm', ns)
                            if cdtr is not None and cdtr.text:
                                name = f"An: {cdtr.text}"

                    # Letzter Fallback → Referenz / Text
                    if not name:
                        ustrd = tx.find('.//n:RmtInf/n:Ustrd', ns)
                        if ustrd is not None and ustrd.text:
                            name = ustrd.text[:50]

                    # --- BETRAG ---
                    amt_node = tx.find('.//n:TxAmt//n:Amt', ns) or tx.find('.//n:Amt', ns)
                    betrag = float(amt_node.text) if amt_node is not None else 0.0

                    gutschrift = betrag if is_credit else 0.0
                    belastung = betrag if not is_credit else 0.0

                    # --- ZUSATZINFO ---
                    qr_zusatz = tx.find('.//n:RmtInf/n:Strd/n:AddtlRmtInf', ns)
                    tx_zusatz = tx.find('.//n:AddtlTxInf', ns)

                    final_zusatz = (
                        qr_zusatz.text if qr_zusatz is not None else
                        (tx_zusatz.text if tx_zusatz is not None else entry_inf_text)
                    )

                    # --- REFERENZ / BEMERKUNG ---
                    ref = tx.find('.//n:RmtInf//n:Ref', ns)
                    ustrd = tx.find('.//n:RmtInf/n:Ustrd', ns)

                    bemerkung = (
                        (ref.text if ref is not None else "") +
                        (" | " + ustrd.text if ustrd is not None else "")
                    ).strip(" | ")

                    extracted_data.append({
                        "ID": ref_id,
                        "Datum_Raw": date_obj,
                        "Partner / Mieter": name,
                        "Eingang (+)": gutschrift,
                        "Ausgang (-)": belastung,
                        "Bemerkung / Ref": bemerkung or "-",
                        "Zusatzinfo": final_zusatz or "-",
                        "Quelle": xml_file.name
                    })

            else:
                # Sammelbuchung
                amt_node = entry.find('./n:Amt', ns)
                val = float(amt_node.text) if amt_node is not None else 0.0

                extracted_data.append({
                    "ID": ref_id,
                    "Datum_Raw": date_obj,
                    "Partner / Mieter": "Sammelbuchung",
                    "Eingang (+)": val if is_credit else 0.0,
                    "Ausgang (-)": val if not is_credit else 0.0,
                    "Bemerkung / Ref": "-",
                    "Zusatzinfo": entry_inf_text or "Sammelbuchung",
                    "Quelle": xml_file.name
                })

        return pd.DataFrame(extracted_data)

    except Exception as e:
        print(f"Fehler beim Parsen: {e}")
        return pd.DataFrame()


# --- STREAMLIT APP ---
st.set_page_config(page_title="XML-Konverter", layout="wide")
st.title("🏠 XML-Konverter für Rechnungen")

files = st.file_uploader("XML-Dateien hochladen", accept_multiple_files=True, type=['xml'])

if files:
    all_dfs = [extract_xml_data_to_df(f) for f in files]
    df = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()

    if not df.empty:
        # Sortieren
        df = df.sort_values(
            by=["Datum_Raw", "ID", "Partner / Mieter"],
            ascending=[True, True, False],
            na_position='last'
        )

        # Duplikate
        df["Status"] = "✅ Original"
        is_dup = df.duplicated(subset=["ID", "Eingang (+)", "Ausgang (-)"], keep='first')
        df.loc[is_dup, "Status"] = "📂 Duplikat"

        # Datum formatieren
        df["Datum"] = df["Datum_Raw"].dt.strftime('%d.%m.%Y')
        df["Partner / Mieter"] = df["Partner / Mieter"].fillna("Keine Details")

        cols = [
            "Status", "Datum", "Partner / Mieter",
            "Eingang (+)", "Ausgang (-)",
            "Bemerkung / Ref", "Zusatzinfo", "Quelle"
        ]

        final_df = df[cols]

        st.subheader("Chronologische Buchungsübersicht")
        st.dataframe(final_df, use_container_width=True)

        # Metriken
        original_df = df[df["Status"] == "✅ Original"]

        tot_in = original_df["Eingang (+)"].sum()
        tot_out = original_df["Ausgang (-)"].sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("Anzahl Buchungen", len(original_df))
        c2.metric("Total Eingänge", f"{tot_in:,.2f} CHF")
        c3.metric("Total Ausgänge", f"{tot_out:,.2f} CHF")

        # Excel Export
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            final_df.to_excel(writer, index=False, sheet_name='Kontoauszug')

        st.download_button(
            label="📊 Excel-Liste speichern",
            data=buffer.getvalue(),
            file_name=f"Bank_Export_{datetime.now().strftime('%d_%m_%Y')}.xlsx"
        )
