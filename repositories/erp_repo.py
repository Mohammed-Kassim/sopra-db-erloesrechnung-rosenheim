"""
repositories/erp_repo.py
Datenzugriffsschicht für die ERPDB – Rosenheim.
"""

import os, urllib.parse
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

_DIR = os.path.dirname(__file__)
_SALES_CSV    = os.path.join(_DIR, "dbo_V_LIST_MONTHLY_SALES.csv")
_COSTS_CSV    = os.path.join(_DIR, "dbo_V_LIST_MONTHLY_COSTS.csv")
_CUSTOMER_CSV = os.path.join(_DIR, "dbo_T_CUSTOMER.csv")

STORE_NAME = "Rosenheim"

_engine = None

class ERPAuthError(Exception):
    """Interner Fehler fuer ERPDEV-Anmeldung und Datenbankzugriff."""


def _get_config(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value not in (None, ""):
        return value
    try:
        import streamlit as st
        if name in st.secrets:
            secret_value = st.secrets[name]
            return str(secret_value) if secret_value not in (None, "") else default
    except Exception:
        pass
    return default


def _is_true(name: str, default: str = "false") -> bool:
    return str(_get_config(name, default)).strip().lower() in {"1", "true", "yes", "ja"}


def _build_engine(username: str | None = None, password: str | None = None):
    from sqlalchemy import create_engine

    server = _get_config("MSSQL_SERVER")
    database = _get_config("MSSQL_DATABASE")
    username = username if username is not None else _get_config("MSSQL_USERNAME")
    password = password if password is not None else _get_config("MSSQL_PASSWORD")
    driver = _get_config("MSSQL_DRIVER", "ODBC Driver 18 for SQL Server")
    encrypt = _get_config("SQL_ENCRYPT", "yes")
    trust = _is_true("TRUST_SERVER_CERTIFICATE")

    missing = [
        name for name, value in {
            "MSSQL_SERVER": server,
            "MSSQL_DATABASE": database,
            "MSSQL_USERNAME": username,
            "MSSQL_PASSWORD": password,
        }.items()
        if value in (None, "")
    ]
    if missing:
        raise ERPAuthError(
            "Die Datenbankverbindung ist unvollstaendig konfiguriert: "
            + ", ".join(missing)
        )

    params = urllib.parse.quote_plus(
        f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};"
        f"UID={username};PWD={password};Encrypt={encrypt};"
        f"TrustServerCertificate={'Yes' if trust else 'No'};Connection Timeout=10;"
    )
    return create_engine(f"mssql+pyodbc:///?odbc_connect={params}")


def _get_engine():
    global _engine
    if _engine is not None:
        return _engine
    _engine = _build_engine()
    return _engine

def _use_demo() -> bool:
    if _is_true("USE_DEMO_DATA"):
        return True
    return not (os.path.exists(_SALES_CSV) and os.path.exists(_COSTS_CSV))


def debug_mode() -> bool:
    return _is_true("DEBUG_MODE")


def get_database_label() -> str:
    database = _get_config("MSSQL_DATABASE", "ERPDEV")
    server = _get_config("MSSQL_SERVER")
    if server:
        return f"{database} auf {server}"
    return database or "ERPDEV"


def authenticate_erp_user(username: str, password: str) -> tuple[bool, str | None]:
    """Prueft, ob die eingegebenen ERPDEV-Zugangsdaten eine DB-Verbindung erlauben."""
    username = (username or "").strip()
    if not username or not password:
        return False, "Bitte ERPDEV-Benutzername und Passwort eingeben."

    engine = None
    try:
        from sqlalchemy import text
        engine = _build_engine(username=username, password=password)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, None
    except ERPAuthError as exc:
        return False, str(exc)
    except Exception as exc:
        return False, f"{exc.__class__.__name__}: Verbindung oder Anmeldung fehlgeschlagen."
    finally:
        if engine is not None:
            engine.dispose()

def _norm_month(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, dayfirst=True).dt.strftime("%Y%m")


def get_sales_data() -> pd.DataFrame:
    if _use_demo():
        from repositories.demo_data import get_sales_data as _d
        return _d()

    from sqlalchemy import text
    query = text("SELECT * FROM dbo.V_LIST_MONTHLY_SALES WHERE StoreName = :store")
    with _get_engine().connect() as conn:
        df = pd.read_sql(query, conn, params={"store": STORE_NAME})
    df["ID_CALMONTH"] = _norm_month(df["ID_CALMONTH"])
    df["Kampagne"]    = df["Kampagne"].fillna("Keine")
    df["KampagneTyp"] = df["KampagneTyp"].fillna("Keine")
    df["ID_CAMPAIGN"] = df["ID_CAMPAIGN"].fillna(0).astype(int)
    return df.reset_index(drop=True)


def get_costs_data() -> pd.DataFrame:
    if _use_demo():
        from repositories.demo_data import get_costs_data as _d
        return _d()

    from sqlalchemy import text
    query = text(
        "SELECT * FROM dbo.V_LIST_MONTHLY_COSTS "
        "WHERE ID_STORE = (SELECT TOP 1 ID_STORE FROM dbo.V_LIST_MONTHLY_SALES WHERE StoreName = :store)"
    )
    with _get_engine().connect() as conn:
        df = pd.read_sql(query, conn, params={"store": STORE_NAME})
    df["ID_CALMONTH"] = _norm_month(df["ID_CALMONTH"])
    return df.reset_index(drop=True)


def get_customers() -> pd.DataFrame:
    if not os.path.exists(_CUSTOMER_CSV):
        return pd.DataFrame({"ANSPRECHPERSON_INTERN": []})
    df = pd.read_csv(_CUSTOMER_CSV, encoding="utf-8-sig")
    df = df.dropna(subset=["ANSPRECHPERSON_INTERN"])
    df["ANSPRECHPERSON_INTERN"] = df["ANSPRECHPERSON_INTERN"].str.strip()
    return df.sort_values("ANSPRECHPERSON_INTERN").reset_index(drop=True)


def get_b2b_discounts() -> pd.DataFrame:
    return pd.DataFrame()


def get_materials() -> pd.DataFrame:
    return pd.DataFrame()
