# XML-Datenextraktion und -Konvertierung in Excel

Dieses Projekt bietet eine einfache Möglichkeit, XML-Daten zu extrahieren und in ein Excel-Dokument zu konvertieren. Die Anwendung ermöglicht das Hochladen von XML-Dateien, die dann analysiert und die extrahierten Daten in eine Excel-Datei exportiert werden.

## Funktionsweise

1. **XML-Daten extrahieren**: Die Anwendung extrahiert relevante Informationen aus XML-Dateien, die mit dem **ISO 20022** Standard (oder einem ähnlichen Format) übereinstimmen.
2. **Datenanzeige**: Alle extrahierten Daten werden in einer Tabelle angezeigt, die im Streamlit-Dashboard sichtbar ist.
3. **Export in Excel**: Nachdem die Daten extrahiert wurden, können Benutzer die Daten als Excel-Datei herunterladen.

### Extrahierte Daten
Die folgenden Daten werden aus der XML-Datei extrahiert:

- **Zahlungsdatum**: Datum und Uhrzeit der Zahlungstransaktion.
- **Betrag**: Der Betrag der Transaktion.
- **Debitor Name**: Name des Debitors (z. B. des Zahlers).
- **Strasse**: Strasse des Debitors.
- **Hausnummer**: Hausnummer des Debitors.
- **Postleitzahl**: Postleitzahl des Debitors.
- **Stadt**: Stadt des Debitors.
- **Referenznummer**: Eine eindeutige Referenznummer für die Transaktion.
- **Zusätzliche Remittanzinformationen**: Weitere zusätzliche Informationen zur Zahlung.
- **Adresse**: Eine vollständige Adresse, zusammengesetzt aus mehreren Adresszeilen.

## Installation

### 1. Voraussetzungen

Stelle sicher, dass Python 3.7+ und `pip` installiert sind. Wenn du nicht sicher bist, ob du Python installiert hast, kannst du dies mit folgendem Befehl überprüfen:

python --version

### 2. Abhängigkeiten installieren

Erstelle eine virtuelle Umgebung und installiere die benötigten Python-Pakete:

# Erstelle eine virtuelle Umgebung

python -m venv venv

# Aktiviere die virtuelle Umgebung
# Auf Windows

venv\Scripts\activate
# Auf macOS/Linux
source venv/bin/activate

# Installiere die Abhängigkeiten
pip install -r requirements.txt



## Lizenz

Dieses Projekt ist urheberrechtlich geschützt und darf nur mit ausdrücklicher Genehmigung des Autors verwendet, modifiziert oder weiterverbreitet werden.

© 2024 Ravidu Nakandalage . Alle Rechte vorbehalten.

---

Für weitere Fragen oder Probleme, öffne bitte ein Issue oder sende eine E-Mail an [ravidu.nakandalage@hotmail.com](mailto:ravidu.nakandalage@hotmail.com).
