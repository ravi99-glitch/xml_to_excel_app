import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st
import pytz

def extract_xml_data_to_df(xml_file):
    """
    Extrahiert alle Zahlungen aus einem XML-Dokument und gibt sie als Pandas DataFrame zurück.
    """
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Namespace extrahieren
        namespace = root.tag.split('}')[0].strip('{')

        # Liste zur Speicherung der extrahierten Transaktionsdaten
        extracted_data = []

        # Alle Buchungseinträge (Ntry) finden
        entries = root.findall(f'.//{{{namespace}}}Ntry')

        for entry in entries:
            # Buchungsdatum (BookgDt.Dt) extrahieren
            bookg_date = entry.find(f'.//{{{namespace}}}BookgDt//{{{namespace}}}Dt')
            bookg_date_str = pd.to_datetime(bookg_date.text).strftime('%d.%m.%Y') if bookg_date is not None else None

            # Alle Transaktionsdetails (TxDtls) innerhalb eines Eintrags finden
            transactions = entry.findall(f'.//{{{namespace}}}TxDtls')

            for transaction in transactions:
                data = {
                    "Buchungsdatum": bookg_date_str,
                    "Transaktionsbetrag": None,
                    "Ultimativer Schuldnername": None,
                    "Zusätzliche Remittanzinformationen": None,
                    "Adresse": None,
                }

                try:
                    # Transaktionsbetrag (TxAmt.Amt) extrahieren
                    tx_amt = transaction.find(f'.//{{{namespace}}}TxAmt//{{{namespace}}}Amt')
                    if tx_amt is not None:
                        currency = tx_amt.attrib.get("Ccy", "CHF")
                        data["Transaktionsbetrag"] = f"{currency} {float(tx_amt.text):,.2f}".replace(",", " ")

                    # Ultimativer Schuldnername (UltmtDbtr.Nm) extrahieren
                    ultmt_dbtr_name = transaction.find(f'.//{{{namespace}}}UltmtDbtr//{{{namespace}}}Nm')
                    if ultmt_dbtr_name is not None:
                        data["Ultimativer Schuldnername"] = ultmt_dbtr_name.text

                    # Zusätzliche Remittanzinformationen (AddtlRmtInf) extrahieren
                    addtl_rmt_inf = transaction.find(f'.//{{{namespace}}}AddtlRmtInf')
                    if addtl_rmt_inf is not None:
                        data["Zusätzliche Remittanzinformationen"] = addtl_rmt_inf.text

                    # Adresse (Strasse, Hausnummer, PLZ, Stadt) kombinieren
                    street = transaction.find(f'.//{{{namespace}}}StrtNm')
                    building = transaction.find(f'.//{{{namespace}}}BldgNb')
                    postal_code = transaction.find(f'.//{{{namespace}}}PstCd')
                    city = transaction.find(f'.//{{{namespace}}}TwnNm')
                    address_components = [
                        street.text if street is not None else "",
                        building.text if building is not None else "",
                        postal_code.text if postal_code is not None else "",
                        city.text if city is not None else ""
                    ]
                    data["Adresse"] = ", ".join(filter(None, address_components))

                except AttributeError as e:
                    # Fehlende Tags ignorieren und eine Warnung ausgeben
                    st.warning(f"Ein erwartetes XML-Tag fehlt: {e}")
                except Exception as e:
                    # Allgemeine Fehlerbehandlung
                    st.warning(f"Fehler bei der Datenextraktion: {e}")

                # Hinzufügen der extrahierten Daten zur Liste
                extracted_data.append(data)

        # DataFrame aus den gesammelten Daten erstellen
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
        if uploaded_file.size == 0:  # Überprüfung, ob die Datei leer ist
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
        st.dataframe(combined_df)

        # Zeitstempel in einer bestimmten Zeitzone (z. B. 'Europe/Zurich') erstellen
        timezone = pytz.timezone('Europe/Zurich')
        current_time = pd.Timestamp.now(timezone)

        # Den Zeitstempel für den Dateinamen verwenden
        excel_file = f"extrahierte_daten_{current_time.strftime('%Y%m%d_%H%M%S')}.xlsx"
        combined_df.to_excel(excel_file, index=False)

        # Downloadlink für Excel-Datei
        with open(excel_file, "rb") as f:
            st.download_button(
                label="Excel-Datei herunterladen",
                data=f,
                file_name=excel_file,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
