"""
Demo-Daten für die DB-/Erlösrechnung Rosenheim.
Spiegelt das Schema von dbo.V_LIST_MONTHLY_SALES und dbo.V_LIST_MONTHLY_COSTS.
Ersetze get_sales_data() und get_costs_data() durch echte DB-Abfragen aus erp_repo.py.
"""

import pandas as pd
import numpy as np

STORE_NAME = "Rosenheim"
STORE_ID = "RO01"
STORE_M2 = 320

PRODUCTS = [
    # (ProduktNr, ProduktName, ProduktKategorie, ProduktLinie, SalesPriceEUR, TransferPriceEUR)
    ("P001", "Scott Genius 940", "Mountain", "Race",       2499.00, 1400.00),
    ("P002", "Scott Spark 960",  "Mountain", "Race",       3199.00, 1900.00),
    ("P003", "Scott Sub Cross",  "City",     "Urban",       799.00,  420.00),
    ("P004", "Town Lite Rohloff","City",     "Urban",      1299.00,  650.00),
    ("P005", "Scott E-Scale 720","E-Bike",   "Electric",   3499.00, 2100.00),
    ("P006", "Scott E-Sub Tour", "E-Bike",   "Electric",   2799.00, 1650.00),
    ("P007", "Scott Speedster",  "Race",     "Road",       1899.00, 1050.00),
    ("P008", "Scott Contessa",   "Trekking", "Tour",       1199.00,  620.00),
    ("P009", "Scott Aspect 760", "Mountain", "Trail",      1099.00,  570.00),
    ("P010", "Scott Roxter",     "Kids",     "Junior",      399.00,  190.00),
    ("P011", "Scott Bio Terra",  "Bio",      "Eco",        1599.00,  850.00),
    ("P012", "Scott Silence 20", "E-Bike",   "Electric",   4199.00, 2600.00),
]

EMPLOYEES = ["Müller, Anna", "Schmidt, Tobias", "Wagner, Lisa", "Bauer, Klaus", "Richter, Sarah"]
CAMPAIGNS = ["Frühjahrs-Sale", "E-Bike-Woche", "Keine", "Sommer-Aktion", "Keine", "Keine"]

MONTHS = [f"2025{m:02d}" for m in range(1, 13)]


def get_sales_data() -> pd.DataFrame:
    """
    Gibt Demo-Verkaufsdaten zurück.
    In der echten Anwendung: ersetze durch SQL-Abfrage auf dbo.V_LIST_MONTHLY_SALES.
    """
    rng = np.random.default_rng(42)
    rows = []

    for calmonth in MONTHS:
        month_idx = int(calmonth[4:]) - 1
        # Saisonalität: Frühling/Sommer höher
        season_factor = [0.6, 0.7, 1.0, 1.3, 1.5, 1.6, 1.5, 1.4, 1.1, 0.9, 0.7, 0.8][month_idx]

        for prod in PRODUCTS:
            prod_nr, prod_name, kategorie, linie, sale_price, transfer_price = prod

            # E-Bike und Race im Sommer stärker
            extra = 1.3 if kategorie in ("E-Bike", "Race") and month_idx in range(3, 8) else 1.0
            base_qty = {"Mountain": 8, "City": 10, "E-Bike": 5, "Race": 6,
                        "Trekking": 7, "Kids": 4, "Bio": 3}[kategorie]
            qty = max(1, int(rng.poisson(base_qty * season_factor * extra)))

            for emp in rng.choice(EMPLOYEES, size=min(qty, len(EMPLOYEES)), replace=False):
                emp_qty = max(1, qty // len(EMPLOYEES))
                campaign = rng.choice(CAMPAIGNS)
                discount_pct = rng.choice([0, 0, 0, 5, 10, 15]) / 100
                discount_eur = round(sale_price * emp_qty * discount_pct, 2)
                revenue_eur = round(sale_price * emp_qty - discount_eur, 2)

                rows.append({
                    "ID_STORE": STORE_ID,
                    "StoreName": STORE_NAME,
                    "StoreM2": STORE_M2,
                    "ID_CALMONTH": calmonth,
                    "ID_MATERIAL": prod_nr,
                    "ProduktNr": prod_nr,
                    "ProduktName": prod_name,
                    "ProduktKategorie": kategorie,
                    "ProduktLinie": linie,
                    "ID_EMPLOYEE": emp.split(",")[1].strip()[:3].upper() + "01",
                    "SalesPerson": emp,
                    "ID_CAMPAIGN": campaign.replace(" ", "_").upper() if campaign != "Keine" else None,
                    "Kampagne": campaign,
                    "SalesAmount": emp_qty,
                    "SalesPriceEUR": sale_price,
                    "TransferPriceEUR": transfer_price,
                    "DiscountEUR": discount_eur,
                    "RevenueEUR": revenue_eur,
                })

    return pd.DataFrame(rows)


def get_costs_data() -> pd.DataFrame:
    """
    Gibt Demo-Kostendaten zurück.
    In der echten Anwendung: ersetze durch SQL-Abfrage auf dbo.V_LIST_MONTHLY_COSTS.
    COST_CATEGORY: HR | Facility | Logistics | Marketing_Produkt |
                   Marketing_Gruppe | Marketing_Filiale | Provision
    """
    rows = []
    rng = np.random.default_rng(7)

    # Monatliche Fixkosten (annähernd stabil)
    base_costs = {
        "HR":                  14500,   # Gehälter
        "Facility":             4200,   # Miete, Nebenkosten
        "Logistics":            1800,   # Lager, Transport
        "Marketing_Filiale":    2500,   # filialweites Marketing
    }
    # Kampagnenkosten (produktbezogen / gruppenbezogen, nur bestimmte Monate)
    campaign_months = {
        "202503": ("Marketing_Produkt",  "E-Bike Frühjahrs-Aktionen",    3200),
        "202504": ("Marketing_Gruppe",   "Mountain & Race Frühling",      1800),
        "202506": ("Marketing_Produkt",  "Sommer E-Bike Deal",            2700),
        "202507": ("Marketing_Gruppe",   "Sommer-Sale alle Gruppen",      2200),
        "202509": ("Marketing_Filiale",  "Herbst-Kampagne Filiale",       1500),
        "202511": ("Marketing_Produkt",  "Black-Friday E-Bike",           3000),
    }

    for calmonth in MONTHS:
        for cat, val in base_costs.items():
            noise = int(rng.normal(0, val * 0.04))
            rows.append({
                "ID_STORE": STORE_ID,
                "ID_CALMONTH": calmonth,
                "COST_CATEGORY": cat,
                "COMMENT": f"{cat} {calmonth}",
                "VALUE": val + noise,
            })
        # Provision: 2% des Monatsumsatzes (approximiert)
        rows.append({
            "ID_STORE": STORE_ID,
            "ID_CALMONTH": calmonth,
            "COST_CATEGORY": "Provision",
            "COMMENT": "Verkäuferprovision 2%",
            "VALUE": int(rng.normal(1200, 150)),
        })
        if calmonth in campaign_months:
            cat, comment, val = campaign_months[calmonth]
            rows.append({
                "ID_STORE": STORE_ID,
                "ID_CALMONTH": calmonth,
                "COST_CATEGORY": cat,
                "COMMENT": comment,
                "VALUE": val,
            })

    return pd.DataFrame(rows)
