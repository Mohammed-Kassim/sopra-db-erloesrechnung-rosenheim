# DB-/Erlösrechnung Rosenheim

Streamlit-Dashboard für die Filialleitung Rosenheim zur Analyse von Umsatz, Kosten und Deckungsbeiträgen auf Basis von ERPDEV-Daten.

## Anmeldung

Beim Start erscheint eine ERPDEV-Loginmaske. Nutzer geben ihren ERPDEV-Benutzernamen und ihr ERPDEV-Passwort ein. Die App prüft die Anmeldung über eine kurze Datenbankverbindung mit `SELECT 1`. Erst nach erfolgreicher Anmeldung werden Dashboard-Daten geladen.

Wichtig: Passwörter werden nicht im Code gespeichert und nicht im Frontend ausgegeben. Technische Details erscheinen nur, wenn `DEBUG_MODE=true` gesetzt ist.

## Benötigte Konfiguration

Lokal über `.env` oder in Streamlit Community Cloud über Secrets:

```toml
MSSQL_SERVER = "..."
MSSQL_DATABASE = "..."
MSSQL_USERNAME = "..."
MSSQL_PASSWORD = "..."
MSSQL_DRIVER = "ODBC Driver 17 for SQL Server"
SQL_ENCRYPT = "yes"
TRUST_SERVER_CERTIFICATE = "true"
USE_DEMO_DATA = "false"
DEBUG_MODE = "false"
```

Die Werte `MSSQL_SERVER` und `MSSQL_DATABASE` werden auch für die Loginprüfung benötigt. `MSSQL_USERNAME` und `MSSQL_PASSWORD` bleiben die technischen App-Zugangsdaten für das Laden der Dashboard-Daten nach erfolgreichem Login.

## Lokaler Start

```bash
uv run streamlit run app.py
```

## Sicherheitshinweise

- Niemals echte Zugangsdaten committen.
- `.env` und `.streamlit/secrets.toml` müssen lokal bleiben.
- Die Loginmaske ersetzt keine rollenbasierte ERPDEV-Berechtigungsverwaltung, verhindert aber den freien Zugriff auf das Streamlit-Dashboard.
