"""
app.py  –  DB-/Erlösrechnung Rosenheim
Streamlit-Frontend  |  Task 13  |  SOPRA
Echte ERPDEV-Daten
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from repositories.erp_repo import (
    authenticate_erp_user,
    debug_mode,
    get_sales_data,
    get_costs_data,
    get_customers,
)
from services.db_calculation_service import berechne_db_gesamt

# ─── Konfiguration ────────────────────────────────────────────────
st.set_page_config(
    page_title="DB-/Erlösrechnung Rosenheim",
    page_icon="🚲",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
section[data-testid="stSidebar"] { background:#0f172a; border-right:1px solid #1e293b; }
section[data-testid="stSidebar"] * { color:#cbd5e1 !important; }
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stMultiSelect label {
  color:#94a3b8 !important; font-size:0.75rem; font-weight:600;
  letter-spacing:0.08em; text-transform:uppercase; }
.kpi-box { background:linear-gradient(135deg,#1e293b 0%,#0f172a 100%);
  border:1px solid #334155; border-radius:12px; padding:1.1rem 1.3rem;
  text-align:center; transition:transform 0.15s; }
.kpi-box:hover { transform:translateY(-2px); border-color:#3b82f6; }
.kpi-label { font-size:0.7rem; font-weight:600; color:#64748b;
  letter-spacing:0.1em; text-transform:uppercase; margin-bottom:0.3rem; }
.kpi-value { font-size:1.45rem; font-weight:700; color:#f1f5f9;
  font-family:'DM Mono',monospace; }
.kpi-value.positive { color:#4ade80; }
.kpi-value.negative { color:#f87171; }
.kpi-sub { font-size:0.72rem; color:#94a3b8; margin-top:0.15rem; }
.db-banner { background:linear-gradient(90deg,#1e3a5f,#0f172a);
  border-left:4px solid #3b82f6; border-radius:8px;
  padding:0.6rem 1rem; margin-bottom:0.5rem;
  font-size:0.8rem; color:#93c5fd; font-weight:500; }
.section-title { font-size:1rem; font-weight:700; color:#e2e8f0;
  border-bottom:2px solid #1e3a5f; padding-bottom:0.4rem;
  margin-bottom:1rem; letter-spacing:0.03em; }
.main .block-container { background:#070d1a; padding-top:1rem; }
</style>
""", unsafe_allow_html=True)

# ─── Hilfsfunktionen ──────────────────────────────────────────────
def eur(v):
    return f"€ {v:,.0f}".replace(",","X").replace(".",",").replace("X",".")
def pct(v):
    return f"{v:.1f} %"
def kpi_html(label, val_str, sub="", positive=None):
    cls = (" positive" if positive is True else
           " negative" if positive is False else "")
    return (f'<div class="kpi-box"><div class="kpi-label">{label}</div>'
            f'<div class="kpi-value{cls}">{val_str}</div>'
            + (f'<div class="kpi-sub">{sub}</div>' if sub else "")
            + '</div>')


LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(15,23,42,0.6)",
    font=dict(family="DM Sans", color="#94a3b8", size=11),
    margin=dict(l=10,r=10,t=30,b=10),
    xaxis=dict(gridcolor="#1e293b"),
    yaxis=dict(gridcolor="#1e293b"),
)
C = dict(umsatz="#94a3b8", db1="#3b82f6", db4="#f59e0b",
         db5="#4ade80", cost="#f87171", mk="#a78bfa", prov="#fb923c")

# ─── ERPDEV Login ────────────────────────────────────────────────
def logout():
    for key in ("erp_authenticated", "erp_user"):
        st.session_state.pop(key, None)


def require_login():
    if st.session_state.get("erp_authenticated"):
        return

    st.markdown("""
    <div style="max-width:520px;margin:3rem auto 1.5rem auto;background:#0f172a;
         border:1px solid #334155;border-radius:14px;padding:2rem 2.2rem;">
      <div style="font-size:1.45rem;font-weight:700;color:#f8fafc;margin-bottom:.35rem;">
        Anmeldung ERPDEV
      </div>
      <div style="font-size:.92rem;color:#94a3b8;line-height:1.55;">
        Bitte mit dem ERPDEV-Benutzer anmelden. Das Dashboard wird erst nach
        erfolgreicher Datenbankprüfung geladen.
      </div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("erpdev_login_form", clear_on_submit=False):
        username = st.text_input("ERPDEV-Benutzername")
        password = st.text_input("ERPDEV-Passwort", type="password")
        submitted = st.form_submit_button("Anmelden", use_container_width=True)

    if submitted:
        ok, detail = authenticate_erp_user(username, password)
        if ok:
            st.session_state["erp_authenticated"] = True
            st.session_state["erp_user"] = username.strip()
            st.rerun()
        else:
            st.error("Anmeldung fehlgeschlagen. Bitte ERPDEV-Benutzername und Passwort prüfen.")
            if debug_mode() and detail:
                st.caption(detail)

    st.info("Ohne erfolgreiche ERPDEV-Anmeldung werden keine Dashboard-Daten geladen.")
    st.stop()


require_login()

# ─── Daten laden ─────────────────────────────────────────────────
@st.cache_data(show_spinner="Echte ERP-Daten werden geladen …")
def load_data():
    return get_sales_data(), get_costs_data(), get_customers()

sales_df, costs_df, customers_df = load_data()

# ─── Sidebar ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚲 DB-Rechnung")
    st.markdown("**Standort Rosenheim**")
    st.caption(f"Angemeldet als: {st.session_state.get('erp_user', 'ERPDEV')}")
    if st.button("Abmelden", use_container_width=True):
        logout()
        st.rerun()
    demo = __import__("repositories.erp_repo", fromlist=["_use_demo"])._use_demo()
    st.caption("🟡 Demo-Modus" if demo else f"🟢 Echte ERP-Daten\nDatenbank: ERPDEV26S")
    st.divider()

    st.markdown("##### Zeitraum")
    alle_monate = sorted(sales_df["ID_CALMONTH"].unique())
    mlbl = {m: f"{['Jan','Feb','Mär','Apr','Mai','Jun','Jul','Aug','Sep','Okt','Nov','Dez'][int(m[4:])-1]} {m[:4]}" for m in alle_monate}
    c1, c2 = st.columns(2)
    with c1:
        von_i = st.selectbox("Von", range(len(alle_monate)),
                             format_func=lambda i: mlbl[alle_monate[i]], index=0)
    with c2:
        bis_i = st.selectbox("Bis", range(len(alle_monate)),
                             format_func=lambda i: mlbl[alle_monate[i]], index=len(alle_monate)-1)
    sel_monate = alle_monate[von_i:bis_i+1]

    st.divider()
    st.markdown("##### Produktkategorie")
    alle_kats = sorted(sales_df["ProduktKategorie"].unique())
    sel_kats = st.multiselect("Kategorien", alle_kats, default=alle_kats,
                               label_visibility="collapsed")

    st.divider()
    st.markdown("##### Mitarbeiter")
    alle_ma = sorted(sales_df["SalesPerson"].unique())
    sel_ma = st.multiselect("MA", alle_ma, default=alle_ma,
                             label_visibility="collapsed")

    st.divider()
    st.markdown("##### Kampagnentyp")
    alle_kt = ["MEDIA","EVENT"]
    sel_kt  = st.multiselect("Kampagnentyp", ["Alle"] + alle_kt,
                              default=["Alle"], label_visibility="collapsed")
    filter_kt = None if "Alle" in sel_kt else sel_kt

    st.divider()
    st.markdown("##### Ansprechperson B2B")
    alle_ap = customers_df["ANSPRECHPERSON_INTERN"].tolist()
    ap_wahl = st.selectbox("Ansprechperson", ["— Alle —"] + alle_ap,
                            label_visibility="collapsed")
    sel_ap  = None if ap_wahl == "— Alle —" else ap_wahl

# ─── Filter anwenden ─────────────────────────────────────────────
s_f = sales_df[
    sales_df["ID_CALMONTH"].isin(sel_monate) &
    sales_df["ProduktKategorie"].isin(sel_kats) &
    sales_df["SalesPerson"].isin(sel_ma)
].copy()
if filter_kt:
    # nur Zeilen mit gesetztem Kampagnentyp filtern (Keine behalten)
    s_f = s_f[s_f["KampagneTyp"].isin(filter_kt + ["Keine"])]
c_f = costs_df[costs_df["ID_CALMONTH"].isin(sel_monate)].copy()

if s_f.empty:
    st.warning("Keine Daten für den gewählten Filter.")
    st.stop()

r    = berechne_db_gesamt(s_f, c_f)
kpis = r["kpis"]
monat= r["monat"]

# ─── Header ──────────────────────────────────────────────────────
zeitraum_label = f"{mlbl[sel_monate[0]]} - {mlbl[sel_monate[-1]]}"
header_meta = f"SOPRA Gruppe 13 · DB I-V · {zeitraum_label}"
if sel_ap:
    header_meta += f" · Ansprechperson: {sel_ap}"

st.markdown("## 🚲 DB-/Erlösrechnung · Rosenheim")
st.caption(header_meta)

# ─── Tabs ─────────────────────────────────────────────────────────
tabs = st.tabs(["📊 Übersicht","📅 Monatsverlauf","📦 Produkte",
                "🗂️ Produktgruppen","👤 Mitarbeiter","🎯 Kampagnen","💧 Wasserfall"])

# ════════════════════ TAB 1: ÜBERSICHT ═══════════════════════════
with tabs[0]:
    st.markdown('<div class="section-title">Gesamtkennzahlen</div>', unsafe_allow_html=True)
    cols = st.columns(5)
    for col, (lbl, val, sub, pos) in zip(cols, [
        ("Nettoumsatz",  eur(kpis["Nettoumsatz"]), "", None),
        ("DB I",         eur(kpis["DB_I"]),  pct(kpis["DB_I_Marge"]),  kpis["DB_I"]>=0),
        ("DB IV",        eur(kpis["DB_IV"]), pct(kpis["DB_IV_Marge"]), kpis["DB_IV"]>=0),
        ("DB V (Ergebnis)", eur(kpis["DB_V"]), pct(kpis["DB_V_Marge"]), kpis["DB_V"]>=0),
        ("DB I-Marge",   pct(kpis["DB_I_Marge"]), "vom Nettoumsatz", kpis["DB_I_Marge"]>=30),
    ]):
        with col:
            st.markdown(kpi_html(lbl,val,sub,pos), unsafe_allow_html=True)

    st.write("")
    cols2 = st.columns(5)
    for col, (lbl, val, sub, pos) in zip(cols2, [
        ("Fixkostenquote",       pct(kpis["Fixkostenquote"]),       "vom Nettoumsatz", None),
        ("Personalkostenquote",  pct(kpis["Personalkostenquote"]),  "vom Nettoumsatz", None),
        ("Marketingkostenquote", pct(kpis["Marketingkostenquote"]), "vom Nettoumsatz", None),
        ("Umsatz je m²",         eur(kpis["Umsatz_je_qm"]),         f"{kpis['store_m2']} m²", None),
        ("DB IV je m²",          eur(kpis["DB_IV_je_qm"]),          "", kpis["DB_IV_je_qm"]>=0),
    ]):
        with col:
            st.markdown(kpi_html(lbl,val,sub,pos), unsafe_allow_html=True)

    st.write("")
    cols3 = st.columns(4)
    for col, (lbl, val, sub, pos) in zip(cols3, [
        ("Umsatz je Mitarbeiter", eur(kpis["Umsatz_je_MA"]), f"{kpis['n_mitarbeiter']} MA", None),
        ("DB IV je Mitarbeiter",  eur(kpis["DB_IV_je_MA"]),  "", kpis["DB_IV_je_MA"]>=0),
        ("MK-Kampagnenkosten",    eur(kpis["MK_Kampagne"]),  "gesamt", None),
        ("Provisionen gesamt",    eur(kpis["MK_Provision"]), "gesamt", None),
    ]):
        with col:
            st.markdown(kpi_html(lbl,val,sub,pos), unsafe_allow_html=True)

    st.write("")
    st.divider()

    col_l, col_r = st.columns([3,2])
    with col_l:
        st.markdown('<div class="section-title">DB-Stufen Gesamtvergleich</div>', unsafe_allow_html=True)
        stufen = ["Nettoumsatz","DB I","DB IV","DB V"]
        werte  = [kpis["Nettoumsatz"],kpis["DB_I"],kpis["DB_IV"],kpis["DB_V"]]
        farben = [C["umsatz"],C["db1"],C["db4"],C["db5"]]
        fig = go.Figure(go.Bar(x=stufen, y=werte, marker_color=farben,
            text=[eur(v) for v in werte], textposition="outside",
            textfont=dict(size=10, color="#94a3b8")))
        fig.update_layout(**LAYOUT, height=320, showlegend=False, yaxis_title="EUR")
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.markdown('<div class="section-title">Kostenstruktur</div>', unsafe_allow_html=True)
        c_data = c_f[c_f["COST_CATEGORY"].isin(
            ["Marketing Campaign","Commission","Monthly Rent",
             "Monthly Salary","Monthly Social Costs","Additional Procurement Costs"]
        )]
        cost_agg = c_data.groupby("COST_CATEGORY")["VALUE"].sum()
        label_map = {
            "Marketing Campaign":"MK-Kampagnen",
            "Commission":"Provisionen",
            "Monthly Rent":"Miete",
            "Monthly Salary":"Gehälter",
            "Monthly Social Costs":"Sozialkosten",
            "Additional Procurement Costs":"Beschaffung",
        }
        fig2 = go.Figure(go.Pie(
            labels=[label_map.get(k,k) for k in cost_agg.index],
            values=cost_agg.values,
            hole=0.42,
            marker=dict(colors=["#a78bfa","#fb923c","#64748b","#3b82f6","#06b6d4","#f59e0b"],
                        line=dict(color="#0f172a", width=2)),
            textinfo="percent+label", textfont=dict(size=10),
        ))
        fig2.update_layout(**LAYOUT, height=320, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    st.write("")
    st.markdown("""<div class="db-banner">
      Nettoumsatz − Variable Kosten (Transferpreis) = <b>DB I</b>
      &nbsp;|&nbsp; DB I = <b>DB II</b> = <b>DB III</b> (keine sep. Produktmarketing-Kosten in DB)
      &nbsp;|&nbsp; DB III − MK-Kampagnen − Provision = <b>DB IV</b>
      &nbsp;|&nbsp; DB IV − Fixkosten (Miete, Gehalt, Sozial, Sonstige) = <b>DB V</b>
    </div>""", unsafe_allow_html=True)

# ════════════════════ TAB 2: MONATSVERLAUF ═══════════════════════
with tabs[1]:
    st.markdown('<div class="section-title">DB-Stufen im Monatsverlauf</div>', unsafe_allow_html=True)
    fig = go.Figure()
    for col_name, lbl, color in [
        ("Nettoumsatz","Nettoumsatz",C["umsatz"]),
        ("DB_I","DB I",C["db1"]),
        ("DB_IV","DB IV",C["db4"]),
        ("DB_V","DB V",C["db5"]),
    ]:
        fig.add_trace(go.Scatter(x=monat["MonatLabel"], y=monat[col_name],
            name=lbl, mode="lines+markers",
            line=dict(color=color, width=2), marker=dict(size=6),
            hovertemplate="%{x}: € %{y:,.0f}<extra></extra>"))
    fig.add_hline(y=0, line_dash="dot", line_color="#334155")
    fig.update_layout(**LAYOUT, height=380, legend=dict(
        orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(color="#94a3b8")))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-title">Monatstabelle</div>', unsafe_allow_html=True)
    disp = monat[["MonatLabel","Nettoumsatz","VariableKosten","DB_I","DB_II","DB_III",
                  "MK_DB4","Fixkosten","DB_IV","DB_V",
                  "DB_I_Marge","DB_II_Marge","DB_III_Marge","DB_IV_Marge","DB_V_Marge"]].copy()
    disp.columns = ["Monat","Nettoumsatz €","Variable K. €","DB I €","DB II €","DB III €",
                    "MK+Prov €","Fixkosten €","DB IV €","DB V €",
                    "DB I %","DB II %","DB III %","DB IV %","DB V %"]
    for col in ["Nettoumsatz €","Variable K. €","DB I €","DB II €","DB III €","MK+Prov €","Fixkosten €","DB IV €","DB V €"]:
        disp[col] = disp[col].map(lambda x: eur(x))
    for col in ["DB I %","DB II %","DB III %","DB IV %","DB V %"]:
        disp[col] = disp[col].map(lambda x: pct(x))
    st.dataframe(disp, use_container_width=True, hide_index=True)

    st.markdown('<div class="section-title">Kostenarten im Monatsverlauf</div>', unsafe_allow_html=True)
    fig3 = go.Figure()
    cost_cats = [
        ("MK_DB2",     "MK Produkt",  "#a78bfa"),
        ("MK_DB3",     "MK Gruppe",   "#c4b5fd"),
        ("MK_DB4",     "MK Filiale",  "#7c3aed"),
        ("Commission", "Provisionen", "#fb923c"),
    ]
    for col_name, lbl, color in cost_cats:
        fig3.add_trace(go.Bar(x=monat["MonatLabel"], y=monat[col_name],
                              name=lbl, marker_color=color))
    # Fixkosten aus costs_df monatlich
    fix_mo = (c_f[c_f["COST_CATEGORY"].isin(
                    ["Monthly Rent","Monthly Salary","Monthly Social Costs",
                     "Additional Procurement Costs"])]
              .groupby("ID_CALMONTH")["VALUE"].sum().reset_index())
    fix_mo["MonatLabel"] = fix_mo["ID_CALMONTH"].map(
        {m: f"{['Jan','Feb','Mär','Apr','Mai','Jun','Jul','Aug','Sep','Okt','Nov','Dez'][int(m[4:])-1]} {m[:4]}"
         for m in fix_mo["ID_CALMONTH"]})
    fig3.add_trace(go.Bar(x=fix_mo["MonatLabel"], y=fix_mo["VALUE"],
                          name="Fixkosten", marker_color="#64748b"))
    fig3.update_layout(**LAYOUT, barmode="stack", height=300,
        legend=dict(orientation="h", y=1.05, x=0, font=dict(color="#94a3b8")))
    st.plotly_chart(fig3, use_container_width=True)

# ════════════════════ TAB 3: PRODUKTE ════════════════════════════
with tabs[2]:
    st.markdown('<div class="section-title">Produkt-Analyse (DB I)</div>', unsafe_allow_html=True)
    prod = r["produkt"]

    # Filter Preissegment
    seg_opts = sorted(prod["ProduktPreisSegment"].unique())
    sel_seg  = st.multiselect("Preissegment", seg_opts, default=seg_opts, key="seg")
    prod_f   = prod[prod["ProduktPreisSegment"].isin(sel_seg)]

    col_l, col_r = st.columns([3,2])
    with col_l:
        fig = go.Figure(go.Bar(
            x=prod_f["ProduktBeschreibung"], y=prod_f["DB_I_Gesamt"],
            marker_color=[C["db1"]]*len(prod_f),
            text=prod_f["DB_I_Marge"].map(lambda x: f"{x:.0f}%"),
            textposition="outside",
            hovertemplate="%{x}<br>DB I: € %{y:,.0f}<extra></extra>",
        ))
        fig.update_layout(**LAYOUT, height=380, xaxis_tickangle=-40, yaxis_title="DB I €")
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        fig2 = go.Figure(go.Scatter(
            x=prod_f["Absatzmenge"], y=prod_f["DB_I_Gesamt"],
            mode="markers+text",
            text=prod_f["ProduktNr"],
            textposition="top center",
            marker=dict(
                size=prod_f["Nettoumsatz"]/prod_f["Nettoumsatz"].max()*40+8,
                color=prod_f["DB_I_Marge"],
                colorscale="Blues", showscale=True,
                colorbar=dict(title="DB I %", tickfont=dict(color="#94a3b8")),
            ),
            hovertemplate="%{text}<br>Menge: %{x}<br>DB I: € %{y:,.0f}<extra></extra>",
        ))
        fig2.update_layout(**LAYOUT, height=380, xaxis_title="Absatzmenge", yaxis_title="DB I gesamt €")
        st.plotly_chart(fig2, use_container_width=True)

    disp = prod_f[["ProduktNr","ProduktBeschreibung","ProduktKategorie",
                   "ProduktPreisSegment","Absatzmenge","Nettoumsatz",
                   "VariableKosten","DB_I_Gesamt","DB_I_Marge","DB_I_Stueck"]].copy()
    disp.columns = ["Nr","Beschreibung","Kategorie","Segment","Menge",
                    "Umsatz €","Variable K. €","DB I €","DB I %","DB I/Stück €"]
    for col in ["Umsatz €","Variable K. €","DB I €","DB I/Stück €"]:
        disp[col] = disp[col].map(eur)
    disp["DB I %"] = disp["DB I %"].map(pct)
    st.dataframe(disp, use_container_width=True, hide_index=True)

# ════════════════════ TAB 4: PRODUKTGRUPPEN ══════════════════════
with tabs[3]:
    st.markdown('<div class="section-title">Produktgruppen-Analyse</div>', unsafe_allow_html=True)
    gruppe = r["gruppe"]

    col_l, col_r = st.columns(2)
    with col_l:
        fig = go.Figure()
        for cn, lbl, color in [
            ("DB_I_Gesamt","DB I",C["db1"]),
            ("Nettoumsatz","Nettoumsatz",C["umsatz"]),
        ]:
            fig.add_trace(go.Bar(x=gruppe["ProduktKategorie"], y=gruppe[cn],
                                 name=lbl, marker_color=color))
        fig.update_layout(**LAYOUT, barmode="group", height=360,
            legend=dict(orientation="h", y=1.05, x=0, font=dict(color="#94a3b8")))
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        fig2 = go.Figure(go.Pie(
            labels=gruppe["ProduktKategorie"], values=gruppe["Nettoumsatz"],
            hole=0.45,
            marker=dict(colors=px.colors.qualitative.Set2,
                        line=dict(color="#0f172a", width=2)),
            textinfo="percent+label",
        ))
        fig2.update_layout(**LAYOUT, height=360, showlegend=False,
            title=dict(text="Umsatzanteile nach Produktgruppe",
                       font=dict(color="#94a3b8")))
        st.plotly_chart(fig2, use_container_width=True)

    disp = gruppe[["ProduktKategorie","Absatzmenge","Nettoumsatz",
                   "VariableKosten","DB_I_Gesamt","DB_I_Marge"]].copy()
    disp.columns = ["Produktgruppe","Menge","Nettoumsatz €","Variable K. €","DB I €","DB I %"]
    for col in ["Nettoumsatz €","Variable K. €","DB I €"]:
        disp[col] = disp[col].map(eur)
    disp["DB I %"] = disp["DB I %"].map(pct)
    st.dataframe(disp, use_container_width=True, hide_index=True)

# ════════════════════ TAB 5: MITARBEITER ═════════════════════════
with tabs[4]:
    st.markdown('<div class="section-title">Mitarbeiter-Performance</div>', unsafe_allow_html=True)
    ma = r["mitarbeiter"]

    col_l, col_r = st.columns(2)
    with col_l:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=ma["SalesPerson"], y=ma["Nettoumsatz"],
                             name="Nettoumsatz", marker_color=C["umsatz"]))
        fig.add_trace(go.Bar(x=ma["SalesPerson"], y=ma["DB_I_Gesamt"],
                             name="DB I", marker_color=C["db1"]))
        if "Provision_Gesamt" in ma.columns:
            fig.add_trace(go.Bar(x=ma["SalesPerson"], y=ma["Provision_Gesamt"],
                                 name="Provision", marker_color=C["prov"]))
        fig.update_layout(**LAYOUT, barmode="group", height=340, xaxis_tickangle=-15,
            legend=dict(orientation="h", y=1.05, x=0, font=dict(color="#94a3b8")))
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        avg_marge = ma["DB_I_Marge"].mean()
        fig2 = go.Figure(go.Bar(
            x=ma["SalesPerson"], y=ma["DB_I_Marge"],
            marker_color=[C["db1"] if v >= avg_marge else C["cost"] for v in ma["DB_I_Marge"]],
            text=ma["DB_I_Marge"].map(lambda x: f"{x:.1f}%"),
            textposition="outside",
        ))
        fig2.add_hline(y=avg_marge, line_dash="dot", line_color="#64748b",
                       annotation_text=f"Ø {avg_marge:.1f}%",
                       annotation_font_color="#64748b")
        fig2.update_layout(**LAYOUT, height=340, yaxis_title="DB I Marge %",
                           xaxis_tickangle=-15)
        st.plotly_chart(fig2, use_container_width=True)

    disp_cols = ["SalesPerson","Absatzmenge","Nettoumsatz","DB_I_Gesamt","DB_I_Marge","DB_IV_anteilig"]
    disp_names = ["Mitarbeiter","Menge","Nettoumsatz €","DB I €","DB I %","DB IV anteilig €"]
    if "Provision_Gesamt" in ma.columns:
        disp_cols.append("Provision_Gesamt")
        disp_names.append("Provision €")
    disp = ma[disp_cols].copy()
    disp.columns = disp_names
    for col in ["Nettoumsatz €","DB I €","DB IV anteilig €"] + (["Provision €"] if "Provision €" in disp_names else []):
        disp[col] = disp[col].map(eur)
    disp["DB I %"] = disp["DB I %"].map(pct)
    st.dataframe(disp, use_container_width=True, hide_index=True)
    st.info("ℹ️ DB IV anteilig = DB IV gesamt ÷ Anzahl Mitarbeiter (gleicher Verteilungsschlüssel).", icon="ℹ️")

# ════════════════════ TAB 6: KAMPAGNEN ═══════════════════════════
with tabs[5]:
    st.markdown('<div class="section-title">Kampagnen-Analyse – Store Rosenheim</div>',
                unsafe_allow_html=True)
    kamp = r["kampagne"]

    if kamp.empty:
        st.info("Keine Kampagnendaten im gewählten Zeitraum.")
    else:
        col_l, col_r = st.columns(2)
        with col_l:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=kamp["Kampagne"], y=kamp["Nettoumsatz"],
                                 name="Nettoumsatz", marker_color=C["umsatz"]))
            fig.add_trace(go.Bar(x=kamp["Kampagne"], y=kamp["DB_I_Gesamt"],
                                 name="DB I", marker_color=C["db1"]))
            if "Kampagnenkosten" in kamp.columns:
                fig.add_trace(go.Bar(x=kamp["Kampagne"], y=kamp["Kampagnenkosten"],
                                     name="Kampagnenkosten", marker_color=C["cost"]))
            fig.update_layout(**LAYOUT, barmode="group", height=380,
                xaxis_tickangle=-35,
                legend=dict(orientation="h", y=1.05, x=0, font=dict(color="#94a3b8")))
            st.plotly_chart(fig, use_container_width=True)

        with col_r:
            if "ROI" in kamp.columns:
                roi_data = kamp[kamp["Kampagnenkosten"] > 0].copy()
                fig2 = go.Figure(go.Bar(
                    x=roi_data["Kampagne"],
                    y=roi_data["ROI"],
                    marker_color=[C["db5"] if v >= 1 else C["cost"] for v in roi_data["ROI"]],
                    text=roi_data["ROI"].map(lambda x: f"{x:.1f}x"),
                    textposition="outside",
                ))
                fig2.add_hline(y=1, line_dash="dot", line_color="#64748b",
                               annotation_text="Break-Even (1x)",
                               annotation_font_color="#64748b")
                fig2.update_layout(**LAYOUT, height=380, yaxis_title="ROI (DB I / Kosten)",
                                   xaxis_tickangle=-35,
                                   title=dict(text="Kampagnen-ROI (DB I je € Kosten)",
                                              font=dict(color="#94a3b8")))
                st.plotly_chart(fig2, use_container_width=True)

        # Kampagnentyp-Aufteilung
        kt_agg = kamp.groupby("KampagneTyp").agg(
            Nettoumsatz=("Nettoumsatz","sum"),
            DB_I=("DB_I_Gesamt","sum"),
            Anzahl=("Kampagne","count"),
        ).reset_index()
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown('<div class="section-title">MEDIA vs. EVENT</div>', unsafe_allow_html=True)
            fig3 = go.Figure(go.Pie(
                labels=kt_agg["KampagneTyp"], values=kt_agg["Nettoumsatz"],
                hole=0.4,
                marker=dict(colors=[C["mk"],C["db4"]],
                            line=dict(color="#0f172a", width=2)),
                textinfo="percent+label",
            ))
            fig3.update_layout(**LAYOUT, height=280, showlegend=False,
                title=dict(text="Umsatzanteil nach Kampagnentyp",
                           font=dict(color="#94a3b8")))
            st.plotly_chart(fig3, use_container_width=True)

        with col_b:
            st.markdown('<div class="section-title">Kampagnentabelle</div>', unsafe_allow_html=True)
            disp_cols = ["Kampagne","KampagneTyp","Absatzmenge","Nettoumsatz","DB_I_Gesamt","DB_I_Marge"]
            disp_names = ["Kampagne","Typ","Menge","Umsatz €","DB I €","DB I %"]
            if "Kampagnenkosten" in kamp.columns:
                disp_cols += ["Kampagnenkosten","ROI"]
                disp_names += ["Kosten €","ROI"]
            disp = kamp[disp_cols].copy()
            disp.columns = disp_names
            for col in ["Umsatz €","DB I €"] + (["Kosten €"] if "Kosten €" in disp_names else []):
                disp[col] = disp[col].map(eur)
            disp["DB I %"] = disp["DB I %"].map(pct)
            if "ROI" in disp.columns:
                disp["ROI"] = disp["ROI"].map(lambda x: f"{x:.1f}x" if pd.notna(x) else "–")
            st.dataframe(disp, use_container_width=True, hide_index=True)

# ════════════════════ TAB 7: WASSERFALL ══════════════════════════
with tabs[6]:
    st.markdown('<div class="section-title">Wasserfall DB I → DB V (Jahresgesamt)</div>',
                unsafe_allow_html=True)
    wf = r["wasserfall"]

    measure, yvals, colors_wf = [], [], []
    for _, row in wf.iterrows():
        if row["Stufe"] in ("Nettoumsatz","= DB I","= DB IV","= DB V"):
            measure.append("absolute")
            colors_wf.append(
                C["db5"] if row["Stufe"] == "= DB V" and row["Wert"] >= 0
                else C["cost"] if row["Stufe"] == "= DB V"
                else C["db1"] if "DB I" in row["Stufe"]
                else C["db4"] if "DB IV" in row["Stufe"]
                else C["umsatz"]
            )
        else:
            measure.append("relative")
            colors_wf.append(C["cost"])
        yvals.append(row["Wert"])

    fig = go.Figure(go.Waterfall(
        orientation="v", measure=measure,
        x=wf["Stufe"].tolist(), y=yvals,
        connector=dict(line=dict(color="#334155", width=1)),
        decreasing=dict(marker=dict(color=C["cost"])),
        increasing=dict(marker=dict(color="#94a3b8")),
        totals=dict(marker=dict(color=C["db5"])),
        text=[eur(v) for v in yvals],
        textposition="outside",
        textfont=dict(size=9, color="#94a3b8"),
    ))
    fig.update_layout(**LAYOUT, height=480, yaxis_title="EUR",
                      xaxis_tickangle=-20, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(f"""
    <div style="background:#1e293b;border-radius:10px;padding:1rem 1.5rem;
         font-size:0.82rem;color:#94a3b8;line-height:1.9;">
      <b style="color:#e2e8f0;">Kostenstruktur Rosenheim (echte ERPDB-Daten):</b><br>
      <span style="color:{C['db1']}">DB I</span> = Nettoumsatz − Transferpreise (variable Kosten)
        &nbsp;→&nbsp; Marge: <b>{pct(kpis['DB_I_Marge'])}</b><br>
      <span style="color:{C['mk']}">DB IV</span> = DB I − Marketing-Kampagnen ({eur(kpis['MK_Kampagne'])})
        − Provisionen ({eur(kpis['MK_Provision'])})
        &nbsp;→&nbsp; Marge: <b>{pct(kpis['DB_IV_Marge'])}</b><br>
      <span style="color:{C['db5']}">DB V</span> = DB IV − Fixkosten (Miete, Gehälter, Sozial, Sonstige)
        &nbsp;→&nbsp; Ergebnismarge: <b style="color:{'#4ade80' if kpis['DB_V']>=0 else '#f87171'}">
        {pct(kpis['DB_V_Marge'])}</b>
    </div>
    """, unsafe_allow_html=True)
