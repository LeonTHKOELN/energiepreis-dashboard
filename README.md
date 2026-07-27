# Energiepreis-Monitoring

Streamlit-Dashboard zur Darstellung von EEX-Kalenderjahr-Futures aus Google Sheets.

## Datenfluss

`Browse AI → Google Sheets → Streamlit`

## Enthaltene Dateien

- `app.py` – vollständige Streamlit-Anwendung
- `requirements.txt` – Python-Abhängigkeiten für Streamlit Community Cloud
- `.gitignore` – verhindert das Hochladen lokaler Dateien und Zugangsdaten
- `logo.png` – optional; kann zusätzlich in den Hauptordner gelegt werden

## Lokal starten

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Auf GitHub hochladen

1. Auf GitHub ein neues Repository erstellen, zum Beispiel `energiepreis-dashboard`.
2. Alle Dateien aus diesem Ordner in das Repository hochladen.
3. Optional `logo.png` in den Hauptordner legen.
4. Änderungen committen.

## Auf Streamlit Community Cloud veröffentlichen

1. Bei Streamlit Community Cloud mit GitHub anmelden.
2. **Create app** auswählen.
3. Repository und Branch `main` auswählen.
4. Als Main file path `app.py` eintragen.
5. **Deploy** auswählen.

## Google-Sheets-Zugriff

Die aktuell eingebundenen Sheets müssen für den einfachen Prototyp auf
`Jeder mit dem Link → Betrachter` gestellt sein.

## Sicherheit

Keine API-Schlüssel oder Passwörter in `app.py` oder GitHub speichern.
Spätere Schlüssel gehören in Streamlit unter **App settings → Secrets**.
Die lokale Datei `.streamlit/secrets.toml` wird durch `.gitignore` ausgeschlossen.
