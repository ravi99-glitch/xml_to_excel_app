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
        "Straße": None,
        "Hausnummer": None,
        "Postleitzahl": None,
        "Stadt": None,
        "Referenznummer": None,
        "Zusätzliche Remittanzinformationen": None,
        "Adresse": None
    }

    # FrDtTm (Zahlungsdatum) extrahieren und formatieren
    fr_dt_tm = root.find(f'.//{{{namespace}}}BkToCstmrDbtCdtNtfctn//{{{namespace}}}Ntfctn//{{{namespace}}}FrToDt//{{{namespace}}}FrDtTm')
    if fr_dt_tm is not None:
        data["Zahlungsdatum"] = pd.to_datetime(fr_dt_tm.text).strftime('%d-%m-%Y %H:%M:%S')  # Formatierung zu "DD-MM-YYYY HH:MM:SS"

    # TxAmt (Betrag) extrahieren
    tx_amt = root.find(f'.//{{{namespace}}}BkToCstmrDbtCdtNtfctn//{{{namespace}}}Ntfctn//{{{namespace}}}Ntry//{{{namespace}}}NtryDtls//{{{namespace}}}TxDtls//{{{namespace}}}AmtDtls//{{{namespace}}}TxAmt//{{{namespace}}}Amt')
    if tx_amt is not None:
        data["Betrag"] = tx_amt.text

    # Debitor Name extrahieren
    dbtr_name = root.find(f'.//{{{namespace}}}BkToCstmrDbtCdtNtfctn//{{{namespace}}}Ntfctn//{{{namespace}}}Ntry//{{{namespace}}}NtryDtls//{{{namespace}}}TxDtls//{{{namespace}}}RltdPties//{{{namespace}}}Dbtr//{{{namespace}}}Nm')
    if dbtr_name is not None:
        data["Debitor Name"] = dbtr_name.text

    # Straße extrahieren
    dbtr_street = root.find(f'.//{{{namespace}}}BkToCstmrDbtCdtNtfctn//{{{namespace}}}Ntfctn//{{{namespace}}}Ntry//{{{namespace}}}NtryDtls//{{{namespace}}}TxDtls//{{{namespace}}}RltdPties//{{{namespace}}}Dbtr//{{{namespace}}}PstlAdr//{{{namespace}}}StrtNm')
    if dbtr_street is not None:
        data["Straße"] = dbtr_street.text

    # Hausnummer extrahieren
    dbtr_bldg = root.find(f'.//{{{namespace}}}BkToCstmrDbtCdtNtfctn//{{{namespace}}}Ntfctn//{{{namespace}}}Ntry//{{{namespace}}}NtryDtls//{{{namespace}}}TxDtls//{{{namespace}}}RltdPties//{{{namespace}}}Dbtr//{{{namespace}}}PstlAdr//{{{namespace}}}BldgNb')
    if dbtr_bldg is not None:
        data["Hausnummer"] = dbtr_bldg.text

    # Postleitzahl extrahieren
    dbtr_postal_code = root.find(f'.//{{{namespace}}}BkToCstmrDbtCdtNtfctn//{{{namespace}}}Ntfctn//{{{namespace}}}Ntry//{{{namespace}}}NtryDtls//{{{namespace}}}TxDtls//{{{namespace}}}RltdPties//{{{namespace}}}Dbtr//{{{namespace}}}PstlAdr//{{{namespace}}}PstCd')
    if dbtr_postal_code is not None:
        data["Postleitzahl"] = dbtr_postal_code.text

    # Stadt extrahieren
    dbtr_city = root.find(f'.//{{{namespace}}}BkToCstmrDbtCdtNtfctn//{{{namespace}}}Ntfctn//{{{namespace}}}Ntry//{{{namespace}}}NtryDtls//{{{namespace}}}TxDtls//{{{namespace}}}RltdPties//{{{namespace}}}Dbtr//{{{namespace}}}PstlAdr//{{{namespace}}}TwnNm')
    if dbtr_city is not None:
        data["Stadt"] = dbtr_city.text

    # Referenznummer extrahieren
    ntry_ref = root.find(f'.//{{{namespace}}}BkToCstmrDbtCdtNtfctn//{{{namespace}}}Ntfctn//{{{namespace}}}NtryRef')
    if ntry_ref is not None:
        data["Referenznummer"] = ntry_ref.text

    # Zusätzliche Remittanzinformationen extrahieren
    additional_remit_info = root.find(f'.//{{{namespace}}}BkToCstmrDbtCdtNtfctn//{{{namespace}}}Ntfctn//{{{namespace}}}Ntry//{{{namespace}}}NtryDtls//{{{namespace}}}TxDtls//{{{namespace}}}RmtInf//{{{namespace}}}Strd//{{{namespace}}}AddtlRmtInf')
    if additional_remit_info is not None:
        data["Zusätzliche Remittanzinformationen"] = additional_remit_info.text

    # Adresse zusammenstellen (falls mehrere Adresszeilen existieren)
    address_lines = []
    for adr_line in root.findall(f'.//{{{namespace}}}BkToCstmrDbtCdtNtfctn//{{{namespace}}}Ntfctn//{{{namespace}}}Ntry//{{{namespace}}}NtryDtls//{{{namespace}}}TxDtls//{{{namespace}}}RltdPties//{{{namespace}}}Dbtr//{{{namespace}}}PstlAdr//{{{namespace}}}AdrLine'):
        if adr_line is not None:
            address_lines.append(adr_line.text)
    
    if address_lines:
        data["Adresse"] = ", ".join(address_lines)
    else:
        data["Adresse"] = "Nicht verfügbar"

    # DataFrame erstellen
    df = pd.DataFrame([data])


def process_uploaded_files(uploaded_files):
    dfs = []
    for uploaded_file in uploaded_files:
        with open(uploaded_file.name, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        dfs.append(extract_xml_data_to_df(uploaded_file.name))
    return pd.concat(dfs, ignore_index=True)


# Streamlit App Layout
st.title("XML zu Excel Konverter")
st.write("Lade deine XML-Dateien hoch, um die extrahierten Daten in eine Excel-Datei umzuwandeln.")

uploaded_files = st.file_uploader("Wähle eine oder mehrere XML-Dateien aus", accept_multiple_files=True, type=['xml'])

if uploaded_files:
    combined_df = process_uploaded_files(uploaded_files)
    st.dataframe(combined_df)

    # Downloadlink für Excel-Datei
    excel_file = "extrahierte_daten.xlsx"
    combined_df.to_excel(excel_file, index=False)

    with open(excel_file, "rb") as f:
        st.download_button(
            label="Excel-Datei herunterladen",
            data=f,
            file_name="extrahierte_daten.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
