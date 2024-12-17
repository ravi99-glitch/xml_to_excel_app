import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st
import openpyxl

def ns_find(element, namespace, path):
    """
    Hilfsfunktion, die einen XPath-Pfad mit Namespace ergänzt und auswertet.
    """
    full_path = '/'.join([f'{{{namespace}}}{tag}' for tag in path.split('/')])
    return element.find(full_path)

def extract_xml_data_to_df(xml_file):
    """
    Extrahiert alle Zahlungen aus einem XML-Dokument und gibt sie als Pandas DataFrame zurück.
    """
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        namespace = root.tag.split('}')[0].strip('{')
        extracted_data = []
        entries = ns_find(root, namespace, 'Ntry')

        for entry in entries:
            bookg_date = ns_find(entry, namespace, 'BookgDt/Dt')
            bookg_date_str = pd.to_datetime(bookg_date.text).strftime('%d.%m.%Y') if bookg_date is not None else None

            transactions = ns_find(entry, namespace, 'TxDtls')
            for transaction in transactions:
                data = {
                    "Buchungsdatum": bookg_date_str,
                    "Transaktionsbetrag": None,
                    "Ultimativer Schuldnername": None,
                    "Zusätzliche Remittanzinformationen": None,
                    "Adresse": None,
                }
                try:
                    tx_amt = ns_find(transaction, namespace, 'TxAmt/Amt')
                    if tx_amt is not None:
                        currency = tx_amt.attrib.get("Ccy", "CHF")
                        data["Transaktionsbetrag"] = f"{currency} {float(tx_amt.text):,.2f}".replace(",", " ")

                    ultmt_dbtr_name = ns_find(transaction, namespace, 'UltmtDbtr/Nm')
                    if ultmt_dbtr_name is not None:
                        data["Ultimativer Schuldnername"] = ultmt_dbtr_name.text

                    addtl_rmt_inf = ns_find(transaction, namespace, 'AddtlRmtInf')
                    if addtl_rmt_inf is not None:
                        data["Zusätzliche Remittanzinformationen"] = addtl_rmt_inf.text

                    street = ns_find(transaction, namespace, 'StrtNm')
                    building = ns_find(transaction, namespace, 'BldgNb')
                    postal_code = ns_find(transaction, namespace, 'PstCd')
                    city = ns_find(transaction, namespace, 'TwnNm')
                    address_components = [
                        street.text if street is not None else "",
                        building.text if building is not None else "",
                        postal_code.text if postal_code is not None else "",
                        city.text if city is not None else ""
                    ]
                    data["Adresse"] = ", ".join(filter(None, address_components))
                except AttributeError as e:
                    st.warning(f"Ein erwartetes XML-Tag fehlt: {e}")
                extracted_data.append(data)

        return pd.DataFrame(extracted_data)

    except ET.ParseError as e:
        raise ET.ParseError(f"Die Datei '{xml_file}' ist kein gültiges XML-Dokument: {e}")
    except Exception as e:
        raise Exception(f"Ein unerwarteter Fehler ist aufgetreten: {e}")

def process_uploaded_files(uploaded_files):
    """
    Verarbeitet hochgeladene XML-Dateien und kombiniert die extrahierten Daten in einen DataFrame.
    """
    dfs = []
    for uploaded_file in uploaded_files:
        if uploaded_file.size == 0:
            st.error(f"Die Datei '{uploaded_file.name}' ist leer und wurde übersprungen.")
            continue

        try:
            dfs.append(extract_xml_data_to_df(uploaded_file))
            st.success(f"Die Datei '{uploaded_file.name}' wurde erfolgreich verarbeitet!")
        except ET.ParseError as e:
            st.error(f"Fehler beim Verarbeiten der Datei '{uploaded_file.name}': {e}")
        except Exception as e:
            st.error(f"Ein unerwarteter Fehler ist bei der Datei '{uploaded_file.name}' aufgetreten: {e}")

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
        st.dataframe(combined_df.head(10))  # Vorschau der ersten 10 Zeilen

        excel_file = "extrahierte_daten.xlsx"
        combined_df.to_excel(excel_file, index=False)

        with open(excel_file, "rb") as f:
            st.download_button(
                label="Excel-Datei herunterladen",
                data=f,
                file_name="extrahierte_daten.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
