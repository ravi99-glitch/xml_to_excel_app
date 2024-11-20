import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st

def extract_xml_data_to_df(xml_file):
    """
    Extract relevant data from an XML document and return it as a Pandas DataFrame.
    """
    tree = ET.parse(xml_file)
    root = tree.getroot()
    namespace = root.tag.split('}')[0].strip('{')

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

    # FrDtTm (Zahlungsdatum)
    fr_dt_tm = root.find(f'.//{{{namespace}}}FrDtTm')
    if fr_dt_tm is not None:
        data["Zahlungsdatum"] = pd.to_datetime(fr_dt_tm.text).strftime('%d-%m-%Y %H:%M:%S')

    # TxAmt (Betrag)
    tx_amt = root.find(f'.//{{{namespace}}}TxAmt//{{{namespace}}}Amt')
    if tx_amt is not None:
        data["Betrag"] = tx_amt.text

    # Debitor Name
    dbtr_name = root.find(f'.//{{{namespace}}}Dbtr//{{{namespace}}}Nm')
    if dbtr_name is not None:
        data["Debitor Name"] = dbtr_name.text

    # Strasse
    dbtr_street = root.find(f'.//{{{namespace}}}Dbtr//{{{namespace}}}PstlAdr//{{{namespace}}}StrtNm')
    if dbtr_street is not None:
        data["Strasse"] = dbtr_street.text

    # Hausnummer
    dbtr_bldg = root.find(f'.//{{{namespace}}}Dbtr//{{{namespace}}}PstlAdr//{{{namespace}}}BldgNb')
    if dbtr_bldg is not None:
        data["Hausnummer"] = dbtr_bldg.text

    # Postleitzahl
    dbtr_postal_code = root.find(f'.//{{{namespace}}}Dbtr//{{{namespace}}}PstlAdr//{{{namespace}}}PstCd')
    if dbtr_postal_code is not None:
        data["Postleitzahl"] = dbtr_postal_code.text

    # Stadt
    dbtr_city = root.find(f'.//{{{namespace}}}Dbtr//{{{namespace}}}PstlAdr//{{{namespace}}}TwnNm')
    if dbtr_city is not None:
        data["Stadt"] = dbtr_city.text

    # Referenznummer
    ntry_ref = root.find(f'.//{{{namespace}}}NtryRef')
    if ntry_ref is not None:
        data["Referenznummer"] = ntry_ref.text

    # Zusätzliche Remittanzinformationen
    additional_remit_info = root.find(f'.//{{{namespace}}}AddtlRmtInf')
    if additional_remit_info is not None:
        data["Zusätzliche Remittanzinformationen"] = additional_remit_info.text

    # Adresse zusammenstellen
    address_lines = [
        adr_line.text
        for adr_line in root.findall(f'.//{{{namespace}}}Dbtr//{{{namespace}}}PstlAdr//{{{namespace}}}AdrLine')
        if adr_line is not None
    ]
    data["Adresse"] = ", ".join(address_lines) if address_lines else "Nicht verfügbar"

    return pd.DataFrame([data])


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
