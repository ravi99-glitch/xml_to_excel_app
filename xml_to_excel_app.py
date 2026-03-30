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
        
        # Namespace automatisch erkennen
        namespace = root.tag.split('}')[0].strip('{') if '}' in root.tag else ''
        ns = {"n": namespace} if namespace else {}
        
        extracted_data = []
        # Alle Buchungseinträge finden
        entries = root.findall('.//n:Ntry', ns) if ns else root.findall('.//Ntry')

        for entry in entries:
            # 1. Datum extrahieren
            bookg_date = entry.find('.//n:BookgDt//n:Dt', ns) if ns else entry.find('.//BookgDt//Dt')
            date_val = pd.to_datetime(bookg_date.text).strftime('%d.%m.%Y') if bookg_date is not None else "Unbekannt"
            
            # 2. Transaktionsdetails suchen (TxDtls)
            transactions = entry.findall('.//n:TxDtls', ns) if ns else entry.findall('.//TxDtls')

            if transactions:
                # Mehrere Transaktionen pro Buchung möglich (z.B. Sammelgutschrift)
                for tx in transactions:
                    # --- MIETER / EINZAHLER FINDEN ---
                    # Wir suchen in allen möglichen Namensfeldern
                    dbtr_name = tx.find('.//n:Dbtr//n:Nm', ns) 
                    ultmt_dbtr = tx.find('.//n:UltmtDbtr//n:Nm', ns)
                    
                    if dbtr_name is not None:
                        name = dbtr_name.text
                    elif ultmt_dbtr is not None:
                        name = ultmt_dbtr.text
                    else:
                        name = "Name nicht im Datensatz"

                    # --- BETRAG ---
                    amt_node = tx.find('.//n:TxAmt//n:Amt', ns)
                    betrag = float(amt_node.text) if amt_node is not None else 0.0

                    # --- BEMERKUNG / REFERENZ ---
                    # Suche nach unstrukturierter Mitteilung (Ustrd) oder QR-Referenz (Ref)
                    remittance = tx.find('.//n:RmtInf//n:Ustrd', ns)
                    qr_ref = tx.find('.//n:RmtInf//n:Strd//n:CdtrRefInf//n:Ref', ns)
                    
                    bemerkung_parts = []
                    if remittance is not None: bemerkung_parts.append(remittance.text)
                    if qr_ref is not None: bemerkung_parts.append(f"QR-Ref: {qr_ref.text}")
                    
                    bemerkung = " | ".join(bemerkung_parts) if bemerkung_parts else "-"

                    extracted_data.append({
                        "Datum": date_val,
                        "Mieter / Einzahler": name,
                        "Betrag": betrag,
                        "Bemerkung": bemerkung
                    })
            else:
                # FALLBACK: Falls keine TxDtls da sind (wie in deinem UBS-Beispiel)
                # Hier nehmen wir die Infos direkt aus dem Ntry-Block
                amt_node = entry.find('./n:Amt', ns) if ns else entry.find('./Amt')
                inf_node = entry.find('./n:AddtlNtryInf', ns) if ns else entry.find('./AddtlNtryInf')
                
                # In Sammelbuchungen steht der Name oft im Infotext
                info_text = inf_node.text if inf_node is not None else "Keine Details vorhanden"
                
                extracted_data.append({
                    "Datum": date_val,
                    "Mieter / Einzahler": "Sammelbuchung (siehe Bemerkung)",
                    "Betrag": float(amt_node.text) if amt_node is not None else 0.0,
                    "Bemerkung": info_text
                })
                
        return pd.DataFrame(extracted_data)
    except Exception as e:
        st.error(f"Fehler bei der Analyse der XML: {e}")
        return pd.DataFrame()

# --- STREAMLIT OBERFLÄCHE ---
st.set_page_config(page_title="Mieteingangs-Tool", page_icon="🏢", layout="wide")

st.title("🏢 Mieteingänge aus Bank-XML extrahieren")
st.markdown("""
Lade deine Bankdateien (**camt.053** oder **camt.054**) hoch. 
Das Tool sucht automatisch nach den Namen der Mieter, den Beträgen und den Zahlungsreferenzen.
""")

uploaded_files = st.file_uploader("XML-Dateien hier reinziehen", accept_multiple_files=True, type=['xml'])

if uploaded_files:
    all_data = []
    for f in uploaded_files:
        df = extract_xml_data_to_df(f)
        if not df.empty:
            all_data.append(df)
            
    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        
        # Anzeige der Tabelle
        st.subheader("Gefundene Zahlungen")
        # Betrag formatieren für die Anzeige
        display_df = final_df.copy()
        display_df['Betrag'] = display_df['Betrag'].map('{:,.2f} CHF'.format)
        st.dataframe(display_df, use_container_width=True)
        
        # Statistiken
        st.write(f"**Anzahl Zahlungen:** {len(final_df)} | **Gesamtsumme:** {final_df['Betrag'].sum():,.2f} CHF")

        # Excel Export
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            final_df.to_excel(writer, index=False, sheet_name='Mieteingänge')
        
        tz = pytz.timezone('Europe/Zurich')
        date_str = datetime.now(tz).strftime("%d.%m.%Y_%H%M")
        
        st.download_button(
            label="📊 Diese Liste als Excel speichern",
            data=buffer.getvalue(),
            file_name=f"Mieteingange_{date_str}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("Keine Buchungsdaten gefunden. Stelle sicher, dass die XML-Datei Zahlungen enthält.")

st.divider()
st.caption("Dieses Tool ist für Schweizer Bankformate (ISO 20022) optimiert.")
