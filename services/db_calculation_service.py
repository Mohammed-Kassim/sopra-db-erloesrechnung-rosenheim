"""
services/db_calculation_service.py
Berechnet DB I–V für den Store Rosenheim.

Kostenstruktur laut Fachkonzept:
  DB I   = Nettoumsatz − variable Kosten (TransferPriceEUR)
  DB II  = DB I − produktbezogene Marketingkosten (DISCOUNT-Kampagnen)
  DB III = DB II − produktgruppenbezogene Marketingkosten (EVENT-Kampagnen)
  DB IV  = DB III − filialbezogene Marketingkosten (MEDIA/SPONSORING/SPECIALS) − Commission
  DB V   = DB IV − Fixkosten (Monthly Rent, Monthly Salary, Monthly Social Costs,
                               Additional Procurement Costs)
"""

import pandas as pd

_MONATE_DE = ["Jan","Feb","Mär","Apr","Mai","Jun",
              "Jul","Aug","Sep","Okt","Nov","Dez"]

def _fmt_month(calmonth: str) -> str:
    y, m = calmonth[:4], int(calmonth[4:])
    return f"{_MONATE_DE[m-1]} {y}"

# Kampagnentyp → DB-Stufe
_DISCOUNT_TYPEN  = {"DISCOUNT"}                          # → DB II
_EVENT_TYPEN     = {"EVENT", "FESTIVAL"}                 # → DB III
_FILIAL_TYPEN    = {"MEDIA", "SPONSORING", "SPECIALS"}   # → DB IV

# Kostenarten → DB-Stufe
_CAT_DB4 = {"Commission"}
_CAT_DB5 = {"Monthly Rent", "Monthly Salary",
             "Monthly Social Costs", "Additional Procurement Costs"}


def berechne_db_gesamt(sales_df: pd.DataFrame, costs_df: pd.DataFrame) -> dict:
    s = sales_df.copy()
    c = costs_df.copy()

    # ── 1. Basis ─────────────────────────────────────────────────
    s["Nettoumsatz"]    = s["RevenueEUR"]
    s["VariableKosten"] = s["TransferPriceEUR"]
    s["DB_I_Gesamt"]    = s["Nettoumsatz"] - s["VariableKosten"]

    # ── 2. Kampagnenkosten aus Costs aufteilen ───────────────────
    # COMMENT Format: "Marketing Campaign [ID]: Name"
    mk = c[c["COST_CATEGORY"] == "Marketing Campaign"].copy()
    mk["KampagneName"] = mk["COMMENT"].str.extract(r"\]: (.+)$").iloc[:, 0].str.strip()

    # Kampagnentyp aus Sales-Daten ermitteln
    kampagnen_typen = (s[s["Kampagne"] != "Keine"]
                       [["Kampagne", "KampagneTyp"]]
                       .drop_duplicates()
                       .rename(columns={"Kampagne": "KampagneName"}))

    mk = mk.merge(kampagnen_typen, on="KampagneName", how="left")
    mk["KampagneTyp"] = mk["KampagneTyp"].fillna("MEDIA")  # Default: filialbezogen

    # Monatliche Kosten je DB-Stufe
    def _mk_monat(typen):
        return (mk[mk["KampagneTyp"].isin(typen)]
                .groupby("ID_CALMONTH")["VALUE"].sum())

    mk_db2  = _mk_monat(_DISCOUNT_TYPEN)   # produktbezogen → DB II
    mk_db3  = _mk_monat(_EVENT_TYPEN)      # gruppenbezogen → DB III
    mk_db4  = _mk_monat(_FILIAL_TYPEN)     # filialbezogen  → DB IV

    # Commission aus Costs
    commission = (c[c["COST_CATEGORY"] == "Commission"]
                  .groupby("ID_CALMONTH")["VALUE"].sum())

    # Fixkosten
    fixkosten = (c[c["COST_CATEGORY"].isin(_CAT_DB5)]
                 .groupby("ID_CALMONTH")["VALUE"].sum())

    # ── 3. Monatliche Aggregation ─────────────────────────────────
    monat = s.groupby("ID_CALMONTH").agg(
        Nettoumsatz    = ("Nettoumsatz",    "sum"),
        VariableKosten = ("VariableKosten", "sum"),
        DB_I           = ("DB_I_Gesamt",    "sum"),
        Rabatte        = ("DiscountEUR",    "sum"),
        Absatzmenge    = ("SalesAmount",    "sum"),
    ).reset_index()

    monat["MK_DB2"]      = monat["ID_CALMONTH"].map(mk_db2).fillna(0)
    monat["MK_DB3"]      = monat["ID_CALMONTH"].map(mk_db3).fillna(0)
    monat["MK_DB4"]      = monat["ID_CALMONTH"].map(mk_db4).fillna(0)
    monat["Commission"]  = monat["ID_CALMONTH"].map(commission).fillna(0)
    monat["Fixkosten"]   = monat["ID_CALMONTH"].map(fixkosten).fillna(0)

    monat["DB_II"]  = monat["DB_I"]  - monat["MK_DB2"]
    monat["DB_III"] = monat["DB_II"] - monat["MK_DB3"]
    monat["DB_IV"]  = monat["DB_III"]- monat["MK_DB4"] - monat["Commission"]
    monat["DB_V"]   = monat["DB_IV"] - monat["Fixkosten"]

    monat["MonatLabel"]  = monat["ID_CALMONTH"].map(_fmt_month)
    monat["DB_I_Marge"]  = (monat["DB_I"]  / monat["Nettoumsatz"] * 100).round(1)
    monat["DB_II_Marge"] = (monat["DB_II"] / monat["Nettoumsatz"] * 100).round(1)
    monat["DB_III_Marge"]= (monat["DB_III"]/ monat["Nettoumsatz"] * 100).round(1)
    monat["DB_IV_Marge"] = (monat["DB_IV"] / monat["Nettoumsatz"] * 100).round(1)
    monat["DB_V_Marge"]  = (monat["DB_V"]  / monat["Nettoumsatz"] * 100).round(1)

    # ── 4. Produkt-Aggregation ────────────────────────────────────
    produkt = s.groupby(
        ["ProduktNr","ProduktBeschreibung","ProduktKategorie",
         "ProduktLinie","ProduktPreisSegment"]
    ).agg(
        Nettoumsatz    = ("Nettoumsatz",    "sum"),
        VariableKosten = ("VariableKosten", "sum"),
        DB_I_Gesamt    = ("DB_I_Gesamt",    "sum"),
        Absatzmenge    = ("SalesAmount",    "sum"),
        Rabatte        = ("DiscountEUR",    "sum"),
    ).reset_index()
    produkt["DB_I_Marge"]  = (produkt["DB_I_Gesamt"] / produkt["Nettoumsatz"] * 100).round(1)
    produkt["DB_I_Stueck"] = (produkt["DB_I_Gesamt"] / produkt["Absatzmenge"]).round(2)
    # DB II je Produkt: DB I − anteilige DISCOUNT-Kosten
    total_um = produkt["Nettoumsatz"].sum()
    total_mk_db2 = mk_db2.sum()
    produkt["DB_II_Gesamt"] = produkt["DB_I_Gesamt"] - (produkt["Nettoumsatz"] / total_um * total_mk_db2)
    produkt["DB_II_Marge"]  = (produkt["DB_II_Gesamt"] / produkt["Nettoumsatz"] * 100).round(1)
    produkt = produkt.sort_values("DB_I_Gesamt", ascending=False)

    # ── 5. Produktgruppen-Aggregation ─────────────────────────────
    gruppe = s.groupby("ProduktKategorie").agg(
        Nettoumsatz    = ("Nettoumsatz",    "sum"),
        VariableKosten = ("VariableKosten", "sum"),
        DB_I_Gesamt    = ("DB_I_Gesamt",    "sum"),
        Absatzmenge    = ("SalesAmount",    "sum"),
    ).reset_index()
    total_mk_db3 = mk_db3.sum()
    gruppe["DB_I_Marge"]    = (gruppe["DB_I_Gesamt"] / gruppe["Nettoumsatz"] * 100).round(1)
    gruppe["DB_II_Gesamt"]  = gruppe["DB_I_Gesamt"]  - (gruppe["Nettoumsatz"] / total_um * total_mk_db2)
    gruppe["DB_III_Gesamt"] = gruppe["DB_II_Gesamt"] - (gruppe["Nettoumsatz"] / total_um * total_mk_db3)
    gruppe["DB_III_Marge"]  = (gruppe["DB_III_Gesamt"] / gruppe["Nettoumsatz"] * 100).round(1)
    gruppe = gruppe.sort_values("DB_III_Gesamt", ascending=False)

    # ── 6. Mitarbeiter ────────────────────────────────────────────
    n_ma = s["SalesPerson"].nunique()
    mitarbeiter = s.groupby("SalesPerson").agg(
        Nettoumsatz = ("Nettoumsatz", "sum"),
        DB_I_Gesamt = ("DB_I_Gesamt", "sum"),
        Absatzmenge = ("SalesAmount", "sum"),
    ).reset_index()
    mitarbeiter["DB_I_Marge"]     = (mitarbeiter["DB_I_Gesamt"] / mitarbeiter["Nettoumsatz"] * 100).round(1)
    mitarbeiter["DB_IV_anteilig"] = round(monat["DB_IV"].sum() / n_ma, 0)
    prov = c[c["COST_CATEGORY"] == "Commission"].copy()
    if not prov.empty:
        prov["SalesPerson"] = prov["COMMENT"].str.extract(r"Commission for (.+?),")
        prov_ma = prov.groupby("SalesPerson")["VALUE"].sum().reset_index()
        prov_ma.columns = ["SalesPerson", "Provision_Gesamt"]
        mitarbeiter = mitarbeiter.merge(prov_ma, on="SalesPerson", how="left")
        mitarbeiter["Provision_Gesamt"] = mitarbeiter["Provision_Gesamt"].fillna(0)
    mitarbeiter = mitarbeiter.sort_values("Nettoumsatz", ascending=False)

    # ── 7. Kampagnen ──────────────────────────────────────────────
    kampagne_sales = (s[s["Kampagne"] != "Keine"]
                      .groupby(["Kampagne","KampagneTyp"]).agg(
                          Nettoumsatz = ("Nettoumsatz", "sum"),
                          DB_I_Gesamt = ("DB_I_Gesamt", "sum"),
                          Absatzmenge = ("SalesAmount", "sum"),
                          Rabatte     = ("DiscountEUR", "sum"),
                      ).reset_index())
    kamp_costs = mk.groupby("KampagneName")["VALUE"].sum().reset_index()
    kamp_costs.columns = ["Kampagne", "Kampagnenkosten"]
    kampagne_sales = kampagne_sales.merge(kamp_costs, on="Kampagne", how="left")
    kampagne_sales["Kampagnenkosten"] = kampagne_sales["Kampagnenkosten"].fillna(0)
    kampagne_sales["DB_nach_Kampagne"] = kampagne_sales["DB_I_Gesamt"] - kampagne_sales["Kampagnenkosten"]
    kampagne_sales["ROI"] = (kampagne_sales["DB_I_Gesamt"] /
                             kampagne_sales["Kampagnenkosten"].replace(0, float("nan"))).round(2)
    kampagne_sales["DB_I_Marge"] = (kampagne_sales["DB_I_Gesamt"] / kampagne_sales["Nettoumsatz"] * 100).round(1)
    kampagne_sales["DB_Stufe"] = kampagne_sales["KampagneTyp"].map(
        lambda t: "DB II" if t in _DISCOUNT_TYPEN
        else "DB III" if t in _EVENT_TYPEN
        else "DB IV"
    )

    # ── 8. Gesamt-KPIs ────────────────────────────────────────────
    store_m2     = int(s["StoreM2"].iloc[0])
    total_um     = monat["Nettoumsatz"].sum()
    total_db1    = monat["DB_I"].sum()
    total_db2    = monat["DB_II"].sum()
    total_db3    = monat["DB_III"].sum()
    total_db4    = monat["DB_IV"].sum()
    total_db5    = monat["DB_V"].sum()
    total_fixk   = monat["Fixkosten"].sum()
    total_comm   = monat["Commission"].sum()
    total_mk2    = monat["MK_DB2"].sum()
    total_mk3    = monat["MK_DB3"].sum()
    total_mk4    = monat["MK_DB4"].sum()
    gehalt_sum   = c[c["COST_CATEGORY"] == "Monthly Salary"]["VALUE"].sum()

    kpis = {
        "Nettoumsatz":         total_um,
        "DB_I":                total_db1,
        "DB_II":               total_db2,
        "DB_III":              total_db3,
        "DB_IV":               total_db4,
        "DB_V":                total_db5,
        "DB_I_Marge":          round(total_db1 / total_um * 100, 1),
        "DB_II_Marge":         round(total_db2 / total_um * 100, 1),
        "DB_III_Marge":        round(total_db3 / total_um * 100, 1),
        "DB_IV_Marge":         round(total_db4 / total_um * 100, 1),
        "DB_V_Marge":          round(total_db5 / total_um * 100, 1),
        "Fixkostenquote":      round(total_fixk / total_um * 100, 1),
        "Personalkostenquote": round(gehalt_sum  / total_um * 100, 1),
        "MK_Kampagne":         total_mk2 + total_mk3 + total_mk4,
        "Marketingkostenquote": round((total_mk2 + total_mk3 + total_mk4) / total_um * 100, 1),
        "MK_DB2":              total_mk2,
        "MK_DB3":              total_mk3,
        "MK_DB4":              total_mk4,
        "MK_Provision":        total_comm,
        "Umsatz_je_MA":        round(total_um  / n_ma, 0),
        "DB_IV_je_MA":         round(total_db4 / n_ma, 0),
        "Umsatz_je_qm":        round(total_um  / store_m2, 0),
        "DB_IV_je_qm":         round(total_db4 / store_m2, 0),
        "Gesamtrabatte":       s["DiscountEUR"].sum(),
        "n_mitarbeiter":       n_ma,
        "store_m2":            store_m2,
    }

    # ── 9. Wasserfall ─────────────────────────────────────────────
    wasserfall = pd.DataFrame([
        {"Stufe": "Nettoumsatz",      "Wert": total_um,    "Typ": "start"},
        {"Stufe": "− Variable K.",    "Wert": -(total_um - total_db1), "Typ": "cost"},
        {"Stufe": "= DB I",           "Wert": total_db1,   "Typ": "result"},
        {"Stufe": "− MK Produkt",     "Wert": -total_mk2,  "Typ": "cost"},
        {"Stufe": "= DB II",          "Wert": total_db2,   "Typ": "result"},
        {"Stufe": "− MK Gruppe",      "Wert": -total_mk3,  "Typ": "cost"},
        {"Stufe": "= DB III",         "Wert": total_db3,   "Typ": "result"},
        {"Stufe": "− MK Filiale",     "Wert": -total_mk4,  "Typ": "cost"},
        {"Stufe": "− Provision",      "Wert": -total_comm, "Typ": "cost"},
        {"Stufe": "= DB IV",          "Wert": total_db4,   "Typ": "result"},
        {"Stufe": "− Gehälter",       "Wert": -c[c["COST_CATEGORY"]=="Monthly Salary"]["VALUE"].sum(), "Typ": "cost"},
        {"Stufe": "− Sozialkosten",   "Wert": -c[c["COST_CATEGORY"]=="Monthly Social Costs"]["VALUE"].sum(), "Typ": "cost"},
        {"Stufe": "− Miete",          "Wert": -c[c["COST_CATEGORY"]=="Monthly Rent"]["VALUE"].sum(), "Typ": "cost"},
        {"Stufe": "− Beschaffung",    "Wert": -c[c["COST_CATEGORY"]=="Additional Procurement Costs"]["VALUE"].sum(), "Typ": "cost"},
        {"Stufe": "= DB V",           "Wert": total_db5,
         "Typ": "positive" if total_db5 >= 0 else "negative"},
    ])

    return {
        "monat":       monat,
        "produkt":     produkt,
        "gruppe":      gruppe,
        "mitarbeiter": mitarbeiter,
        "kampagne":    kampagne_sales,
        "kpis":        kpis,
        "wasserfall":  wasserfall,
        "sales_raw":   s,
        "costs_raw":   c,
    }
