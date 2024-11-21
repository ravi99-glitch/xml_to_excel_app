import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st
import openpyxl
import os


def extract_xml_data_to_df(xml_file):
    """
    Diese Funktion extrahiert relevante Daten aus einem XML-Dokument
    und gibt sie als Pandas DataFrame zurück.
    
    Args:
        xml_file (str): Der Pfad zur XML-Datei.
        
    Returns:
        pd.DataFrame: Ein DataFrame mit den extrahierten Daten.
    """
    try:
        # XML-Datei einlesen und Root-Element extrahieren
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Namespace extrahieren
        namespace = root.tag.split('}')[0].strip('{')

        # Die Daten, die extrahiert werden sollen
        data = {
            "Zahlungsdatum": None,
            "Betrag": None,
            "Debitor Name": None,
            "Strasse": None,
            "Hausnummer": None,
            "Postleitzahl": None,
            "Stadt": None,
            "Referenznummer": None,
            "Zusätzliche Remittanzinformationen": None,
            "Adresse": None
        }

        # FrDtTm (Zahlungsdatum) extrahieren und formatieren
        fr_dt_tm = root.find(f'.//{{{namespace}}}FrDtTm')
        if fr_dt_tm is not None:
            data["Zahlungsdatum"] = pd.to_datetime(fr_dt_tm.text).strftime('%d-%m-%Y %H:%M:%S')

        # TxAmt (Betrag) extrahieren
        tx_amt = root.find(f'.//{{{namespace}}}Amt')
        if tx_amt is not None:
            data["Betrag"] = tx_amt.text

        # Debitor Name extrahieren
        dbtr_name = root.find(f'.//{{{namespace}}}Dbtr//{{{namespace}}}Nm')
        if dbtr_name is not None:
            data["Debitor Name"] = dbtr_name.text

        # Straße extrahieren
        dbtr_street = root.find(f'.//{{{namespace}}}PstlAdr//{{{namespace}}}StrtNm')
        if dbtr_street is not None:
            data["Strasse"] = dbtr_street.text

        # Hausnummer extrahieren
        dbtr_bldg = root.find(f'.//{{{namespace}}}PstlAdr//{{{namespace}}}BldgNb')
        if dbtr_bldg is not None:
            data["Hausnummer"] = dbtr_bldg.text

        # Postleitzahl extrahieren
        dbtr_postal_code = root.find(f'.//{{{namespace}}}PstlAdr//{{{namespace}}}PstCd')
        if dbtr_postal_code is not None:
            data["Postleitzahl"] = dbtr_postal_code.text

        # Stadt extrahieren
        dbtr_city = root.find(f'.//{{{namespace}}}PstlAdr//{{{namespace}}}TwnNm')
        if dbtr_city is not None:
            data["Stadt"] = dbtr_city.text

        # Referenznummer extrahieren
        ntry_ref = root.find(f'.//{{{namespace}}}NtryRef')
        if ntry_ref is not None:
            data["Referenznummer"] = ntry_ref.text

        # Zusätzliche Remittanzinformationen extrahieren
        additional_remit_info = root.find(f'.//{{{namespace}}}AddtlRmtInf')
        if additional_remit_info is not None:
            data["Zusätzliche Remittanzinformationen"] = additional_remit_info.text

        # Adresse zusammenstellen (falls mehrere Adresszeilen existieren)
        address_lines = []
        for adr_line in root.findall(f'.//{{{namespace}}}AdrLine'):
            if adr_line is not None:
                address_lines.append(adr_line.text)

        if address_lines:
            data["Adresse"] = ", ".join(address_lines)
        else:
            data["Adresse"] = "Nicht verfügbar"

        # DataFrame erstellen
        return pd.DataFrame([data])

    except ET.ParseError as e:
        raise ET.ParseError(f"Die Datei '{xml_file}' ist kein gültiges XML-Dokument: {e}")


def process_uploaded_files(uploaded_files):
    """
    Verarbeitet hochgeladene XML-Dateien und kombiniert die extrahierten Daten in einen DataFrame.
    """
    dfs = []
    for uploaded_file in uploaded_files:
        if uploaded_file.size == 0:  # Überprüfung, ob die Datei leer ist
            st.error(f"Die Datei '{uploaded_file.name}' ist leer und wurde übersprungen.")
            continue

        # Temporäre Datei speichern
        with open(uploaded_file.name, 'wb') as f:
            f.write(uploaded_file.getbuffer())

        # Versuch, die Datei zu verarbeiten
        try:
            dfs.append(extract_xml_data_to_df(uploaded_file.name))
        except ET.ParseError as e:
            st.error(f"Fehler beim Verarbeiten der Datei '{uploaded_file.name}': {e}")
            continue

    if dfs:
        return pd.concat(dfs, ignore_index=True)
    else:
        st.error("Keine gültigen XML-Dateien verarbeitet.")
        return None


# Streamlit App Layout
st.title("XML-Datenextraktion und -Konvertierung in Excel")
st.write("Lade deine XML-Dateien hoch, um die extrahierten Daten in eine Excel-Datei umzuwandeln.")

uploaded_files = st.file_uploader(
    "Wähle eine oder mehrere XML-Dateien aus", 
    accept_multiple_files=True, 
    type=['xml']
)

if uploaded_files:
    combined_df = process_uploaded_files(uploaded_files)

    if combined_df is not None:
        st.dataframe(combined_df)

        # Excel-Datei erstellen
        excel_file = "extrahierte_daten.xlsx"
        combined_df.to_excel(excel_file, index=False)

        # Downloadlink für Excel-Datei
        with open(excel_file, "rb") as f:
            st.download_button(
                label="Excel-Datei herunterladen",
                data=f,
                file_name="extrahierte_daten.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
