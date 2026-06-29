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

def _get_engine():
    global _engine
    if _engine is not None:
        return _engine
    from sqlalchemy import create_engine
    server   = os.getenv("MSSQL_SERVER")
    database = os.getenv("MSSQL_DATABASE")
    username = os.getenv("MSSQL_USERNAME")
    password = os.getenv("MSSQL_PASSWORD")
    driver   = os.getenv("MSSQL_DRIVER", "ODBC Driver 18 for SQL Server")
    encrypt  = os.getenv("SQL_ENCRYPT", "yes")
    trust    = os.getenv("TRUST_SERVER_CERTIFICATE", "false").lower() == "true"
    params = urllib.parse.quote_plus(
        f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};"
        f"UID={username};PWD={password};Encrypt={encrypt};"
        f"TrustServerCertificate={'Yes' if trust else 'No'};Connection Timeout=10;"
    )
    _engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
    return _engine

def _use_demo() -> bool:
    if os.getenv("USE_DEMO_DATA", "").lower() == "true":
        return True
    return not (os.path.exists(_SALES_CSV) and os.path.exists(_COSTS_CSV))

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
