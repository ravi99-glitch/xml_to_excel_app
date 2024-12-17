import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st
import openpyxl
import os

def extract_xml_data_to_df(xml_file):
    """
    Diese Funktion extrahiert relevante Daten aus einem XML-Dokument
    und gibt sie als Pandas DataFrame zurück.
    """
    try:
        # XML-Datei einlesen und Root-Element extrahieren
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Namespace extrahieren
        namespace = root.tag.split('}')[0].strip('{')

        # Die Daten, die extrahiert werden sollen
        data = {
            "Buchungsdatum": None,
            "Transaktionsbetrag": None,
            "Ultimativer Schuldnername": None,
            "Zusätzliche Remittanzinformationen": None,
            "Adresse": None
        }

        # Buchungsdatum (BookgDt.Dt) extrahieren und formatieren
        bookg_date = root.find(f'.//{{{namespace}}}BookgDt//{{{namespace}}}Dt')
        if bookg_date is not None:
            data["Buchungsdatum"] = pd.to_datetime(bookg_date.text).strftime('%d.%m.%Y')

        # Transaktionsbetrag (TxAmt.Amt) extrahieren und formatieren
        tx_amt = root.find(f'.//{{{namespace}}}TxAmt//{{{namespace}}}Amt')
        if tx_amt is not None:
            data["Transaktionsbetrag"] = f"CHF {float(tx_amt.text):,.2f}".replace(",", " ")

        # Ultimativer Schuldnername (UltmtDbtr.Nm) extrahieren
        ultmt_dbtr_name = root.find(f'.//{{{namespace}}}UltmtDbtr//{{{namespace}}}Nm')
        if ultmt_dbtr_name is not None:
            data["Ultimativer Schuldnername"] = ultmt_dbtr_name.text

        # Zusätzliche Remittanzinformationen (AddtlRmtInf) extrahieren
        addtl_rmt_inf = root.find(f'.//{{{namespace}}}AddtlRmtInf')
        if addtl_rmt_inf is not None:
            data["Zusätzliche Remittanzinformationen"] = addtl_rmt_inf.text

        # Adresse (Strasse, Hausnummer, PLZ, Stadt) kombinieren
        street = root.find(f'.//{{{namespace}}}StrtNm')
        building = root.find(f'.//{{{namespace}}}BldgNb')
        postal_code = root.find(f'.//{{{namespace}}}PstCd')
        city = root.find(f'.//{{{namespace}}}TwnNm')
        address_components = [
            street.text if street is not None else "",
            building.text if building is not None else "",
            postal_code.text if postal_code is not None else "",
            city.text if city is not None else ""
        ]
        data["Adresse"] = ", ".join(filter(None, address_components))

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
