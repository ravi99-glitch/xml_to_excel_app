import xml.etree.ElementTree as ET
import pandas as pd

# Pfad zur XML-Datei
xml_file = r"File\986590_camt.054_SIC_04_054609003505_NN_0546090035050005_20241104_172037942_302.xml"

# XML-Datei einlesen und Root-Element extrahieren
tree = ET.parse(xml_file)
root = tree.getroot()

# Funktion, um XML-Daten in eine Liste von Dictionaries umzuwandeln
def parse_element(element, parent_key=""):
    data = {}
    for child in element:
        key = f"{parent_key}.{child.tag}" if parent_key else child.tag
        if len(child) > 0:  # Wenn das Kind weitere Elemente enthält
            nested_data = parse_element(child, key)
            data.update(nested_data)
        else:  # Wenn es ein Blattknoten ist
            data[key] = child.text
    return data

# Alle relevanten Datensätze extrahieren
records = []
for item in root:
    records.append(parse_element(item))

# In ein Pandas-DataFrame umwandeln
df = pd.DataFrame(records)

# Ausgabe als Excel-Datei
output_file = "output_beautified.xlsx"
df.to_excel(output_file, index=False)

print(f"Schön formatierte Excel-Datei wurde erfolgreich als {output_file} gespeichert!")
