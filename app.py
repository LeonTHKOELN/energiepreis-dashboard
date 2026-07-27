"""
Energiepreis-Monitoring – Streamlit-Dashboard (eigenständig, Design im Skript)

Datenfluss:  Browse AI  ->  Google Sheets (ein Sheet pro Lieferjahr)  ->  Streamlit
Start:       py -m streamlit run app.py
Zugriff:     Sheets freigeben auf "Jeder mit dem Link -> Betrachter".

Hinweis: Das gesamte Design steckt hier im Skript (CSS unten).
Eine .streamlit/config.toml wird nicht mehr benoetigt.
"""

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# --------------------------------------------------------------------------
# Konfiguration
# --------------------------------------------------------------------------
st.set_page_config(page_title="Energiepreis-Monitoring", page_icon="⚡", layout="wide")

BASE_DIR = Path(__file__).resolve().parent
LOGO = BASE_DIR / "logo.png"

SHEETS = {
    "2027": "https://docs.google.com/spreadsheets/d/1StFUHaubVCMPV-VuKDlUPBx0_wQLwp8mEXQ563KsVOQ/edit",
    "2028": "https://docs.google.com/spreadsheets/d/1bssO6n9-u-FX4U6KelvqHfhs8WJS5CTimYB4gp7M1zU/edit",
    "2029": "https://docs.google.com/spreadsheets/d/1glQGEQmyhM_tgmA1ID5LTkuayLrzsDTTk9AKFhp0Heg/edit",
}

EINHEIT = "EUR/MWh"
AMPEL_SCHWELLE = 1.0

# Klar unterscheidbare Farben pro Lieferjahr (Cyan / Blau / Violett)
FARBEN = {"2027": "#34E0FF", "2028": "#5B8DEF", "2029": "#C084FC"}

conn = st.connection("gsheets", type=GSheetsConnection)

# --------------------------------------------------------------------------
# Styling – komplettes Theme per CSS (keine config.toml noetig)
# --------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap');

    /* Grundflaechen dunkel */
    html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }
    .stApp {
        color: #C9DAE6;
        background:
          radial-gradient(1000px 480px at 15% -12%, #16283a 0%, rgba(22,40,58,0) 55%),
          radial-gradient(820px 460px at 100% 0%, #10202f 0%, rgba(16,32,47,0) 50%),
          #0a1018;
    }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stToolbar"] { display: none; }
    footer { display: none; }
    .block-container { padding-top: 2.2rem; padding-bottom: 3rem; }

    /* Sidebar dunkel + helle Schrift */
    [data-testid="stSidebar"] {
        background: #0E1B2A;
        border-right: 1px solid rgba(0,194,255,.14);
    }
    [data-testid="stSidebar"] *, [data-testid="stWidgetLabel"] * { color: #D7E6F0 !important; }

    /* Titel / Ueberschriften / Bildunterschriften fest hell */
    h1 { color: #EEF6FC !important; font-weight: 700 !important; }
    h2, h3 { color: #DCEAF3 !important; }
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * { color: #9DB3C4 !important; }

    /* Auswahl-Tags (Multiselect) in Cyan statt Rot */
    [data-baseweb="tag"] { background-color: #0E7FB0 !important; }
    [data-baseweb="tag"] span, [data-baseweb="tag"] svg { color: #EAFBFF !important; fill: #EAFBFF !important; }

    /* Logo als weisses Chip, damit es auf Dunkel sauber sitzt */
    [data-testid="stImage"] img { background: #ffffff; padding: 10px 16px; border-radius: 12px; }

    /* Eyebrow-Label ueber Sektionen */
    .eyebrow {
        color: #5FCBF2; font-size: .72rem; letter-spacing: .22em;
        text-transform: uppercase; font-weight: 600; margin: .2rem 0 -.2rem 0;
    }

    /* KPI-Karte im Instrument-Look */
    .kpi-card {
        position: relative; overflow: hidden;
        background: linear-gradient(160deg, rgba(23,169,224,.10), rgba(18,36,54,.55));
        border: 1px solid rgba(0,194,255,.28);
        border-radius: 16px; padding: 18px 20px 22px;
        box-shadow: 0 0 26px rgba(0,150,220,.10), inset 0 1px 0 rgba(255,255,255,.04);
    }
    .kpi-eyebrow { color: #7FB8D9; font-size: .74rem; letter-spacing: .18em; text-transform: uppercase; font-weight: 600; }
    .kpi-price {
        font-family: 'JetBrains Mono', monospace; font-weight: 700;
        font-size: 2.15rem; color: #EAF6FF; line-height: 1.1; margin: 6px 0 2px;
        font-variant-numeric: tabular-nums;
    }
    .kpi-unit { font-size: .8rem; color: #7FA3BC; margin-left: 8px; font-weight: 500; }
    .kpi-delta { font-family: 'JetBrains Mono', monospace; font-size: .92rem; font-weight: 700; }
    .kpi-delta.up   { color: #FF6B7A; }
    .kpi-delta.down { color: #37E6A6; }
    .kpi-delta.flat { color: #FFC24B; }
    .kpi-amp { margin-top: 12px; font-size: .9rem; color: #B8C6D0; display: flex; align-items: center; gap: 9px; }
    .dot { width: 11px; height: 11px; border-radius: 50%; display: inline-block; }
    .dot.red    { background: #FF5A6E; box-shadow: 0 0 11px #FF5A6E; }
    .dot.green  { background: #2FE6A4; box-shadow: 0 0 11px #2FE6A4; }
    .dot.yellow { background: #FFC24B; box-shadow: 0 0 11px #FFC24B; }
    .kpi-bar { height: 3px; border-radius: 3px; margin-top: 16px; }
    .kpi-bar.up   { background: linear-gradient(90deg,#FF6B7A,rgba(255,107,122,0)); }
    .kpi-bar.down { background: linear-gradient(90deg,#37E6A6,rgba(55,230,166,0)); }
    .kpi-bar.flat { background: linear-gradient(90deg,#FFC24B,rgba(255,194,75,0)); }

    /* Datentabelle dunkel (eigenes HTML statt st.dataframe) */
    .tbl-wrap { max-height: 360px; overflow-y: auto; border: 1px solid rgba(0,194,255,.16); border-radius: 12px; }
    table.tbl { width: 100%; border-collapse: collapse; font-size: .9rem; }
    table.tbl thead th {
        position: sticky; top: 0; background: #12283c; color: #9FC3DA;
        text-align: left; padding: 10px 14px; font-weight: 600;
        letter-spacing: .04em; border-bottom: 1px solid rgba(0,194,255,.2);
    }
    table.tbl td { padding: 9px 14px; border-bottom: 1px solid rgba(255,255,255,.05); color: #D4E3EE; }
    table.tbl td.num, table.tbl th.num { text-align: right; font-family: 'JetBrains Mono', monospace; }
    table.tbl tbody tr:hover td { background: rgba(0,194,255,.06); }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------
# Laden & Normalisieren  ->  Datum | Preis | Lieferjahr
# --------------------------------------------------------------------------
@st.cache_data(ttl=600)
def load_sheet(url: str, jahr: str) -> pd.DataFrame:
    raw = conn.read(spreadsheet=url).dropna(how="all")
    date_col = next(
        (c for c in raw.columns if "date" in str(c).lower() or "datum" in str(c).lower()),
        None,
    )
    price_col = next((c for c in raw.columns if "preis" in str(c).lower()), None)
    if date_col is None or price_col is None:
        raise ValueError(f"Spalten nicht gefunden: {raw.columns.tolist()}")

    df = pd.DataFrame()
    df["Datum"] = pd.to_datetime(raw[date_col], errors="coerce", dayfirst=True)
    df["Preis"] = pd.to_numeric(
        raw[price_col].astype(str)
        .str.replace(EINHEIT, "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.strip(),
        errors="coerce",
    )
    df["Lieferjahr"] = jahr
    return df.dropna(subset=["Datum", "Preis"])


frames = []
for jahr, url in SHEETS.items():
    if not url or url.startswith("HIER_"):
        continue
    try:
        frames.append(load_sheet(url, jahr))
    except Exception as exc:
        st.warning(f"Lieferjahr {jahr} konnte nicht geladen werden: {exc}")

if not frames:
    st.error("Keine Daten geladen. URLs eintragen und Sheets freigeben.")
    st.stop()

data = pd.concat(frames, ignore_index=True).sort_values("Datum")
alle_jahre = sorted(data["Lieferjahr"].unique())


# --------------------------------------------------------------------------
# Sidebar – Filter
# --------------------------------------------------------------------------
st.sidebar.header("Filter")
auswahl = st.sidebar.multiselect("Lieferjahr", options=alle_jahre, default=alle_jahre)
tage = st.sidebar.radio(
    "Zeitraum", options=[30, 60, 90], index=0, format_func=lambda d: f"Letzte {d} Tage"
)

max_date = data["Datum"].max()
start = max_date - pd.Timedelta(days=tage)
df = data[(data["Lieferjahr"].isin(auswahl)) & (data["Datum"] >= start)]


# --------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------
head_logo, head_titel = st.columns([1, 5], vertical_alignment="center")
with head_logo:
    if LOGO.exists():
        st.image(LOGO, width=210)
with head_titel:
    st.markdown('<div class="eyebrow">Energiebeschaffung · EEX-Kalenderjahr-Futures</div>',
                unsafe_allow_html=True)
    st.title("Energiepreis-Monitoring")

st.caption(
    f"Letzter Handelstag: {max_date.strftime('%d.%m.%Y')}  ·  "
    f"Trend über die letzten {tage} Tage  ·  Ampel: 🟢 gefallen · 🟡 stabil · 🔴 gestiegen"
)


# --------------------------------------------------------------------------
# KPI-Karten
# --------------------------------------------------------------------------
def kpi_html(jahr, cur, delta, pct):
    if pct > AMPEL_SCHWELLE:
        dot, amp = "red", "Preis gestiegen"
    elif pct < -AMPEL_SCHWELLE:
        dot, amp = "green", "Preis gefallen"
    else:
        dot, amp = "yellow", "stabil"
    if pct > 0:
        richtung, pfeil = "up", "▲"
    elif pct < 0:
        richtung, pfeil = "down", "▼"
    else:
        richtung, pfeil = "flat", "▬"
    return f"""
    <div class="kpi-card">
      <div class="kpi-eyebrow">Cal {jahr}</div>
      <div class="kpi-price">{cur:.2f}<span class="kpi-unit">{EINHEIT}</span></div>
      <div class="kpi-delta {richtung}">{pfeil} {delta:+.2f} ({pct:+.1f} %)</div>
      <div class="kpi-amp"><span class="dot {dot}"></span>{amp}</div>
      <div class="kpi-bar {richtung}"></div>
    </div>
    """


if auswahl:
    cols = st.columns(len(auswahl))
    for col, jahr in zip(cols, auswahl):
        reihe = df[df["Lieferjahr"] == jahr].sort_values("Datum")
        if reihe.empty:
            col.info(f"Cal {jahr}: keine Daten")
            continue
        cur = reihe["Preis"].iloc[-1]
        ref = reihe["Preis"].iloc[0]
        delta = cur - ref
        pct = (delta / ref * 100) if ref else 0.0
        col.markdown(kpi_html(jahr, cur, delta, pct), unsafe_allow_html=True)
else:
    st.info("Bitte mindestens ein Lieferjahr auswählen.")


# --------------------------------------------------------------------------
# Preisverlauf (Altair, dunkel)
# --------------------------------------------------------------------------
st.markdown('<div class="eyebrow">Verlauf</div>', unsafe_allow_html=True)
st.subheader(f"Preisverlauf ({EINHEIT})")

if not df.empty:
    jahre_im_chart = [j for j in FARBEN if j in df["Lieferjahr"].unique()]
    chart = (
        alt.Chart(df)
        .mark_line(strokeWidth=2.6, interpolate="monotone")
        .encode(
            x=alt.X("Datum:T", title="Handelstag"),
            y=alt.Y("Preis:Q", title=EINHEIT, scale=alt.Scale(zero=False)),
            color=alt.Color(
                "Lieferjahr:N",
                scale=alt.Scale(domain=jahre_im_chart,
                                range=[FARBEN[j] for j in jahre_im_chart]),
                legend=alt.Legend(title="Lieferjahr", orient="bottom"),
            ),
            tooltip=[
                alt.Tooltip("Datum:T", title="Datum"),
                alt.Tooltip("Lieferjahr:N", title="Lieferjahr"),
                alt.Tooltip("Preis:Q", title=EINHEIT, format=".2f"),
            ],
        )
        .properties(height=380)
        .configure(background="transparent")
        .configure_view(strokeWidth=0)
        .configure_axis(grid=True, gridColor="#1E3A52", domainColor="#1E3A52",
                        tickColor="#1E3A52", labelColor="#8FA9BC", titleColor="#8FA9BC")
        .configure_legend(labelColor="#E6F1F8", titleColor="#8FA9BC")
    )
    st.altair_chart(chart, use_container_width=True, theme=None)
    st.caption(
        "Jede Linie steht für ein Lieferjahr (EEX-Kalenderjahr-Future). "
        "Der Wert ist der Börsen-Settlementpreis in EUR/MWh, zu dem Strom für "
        "Lieferung im jeweiligen Jahr gehandelt wird. "
        "x-Achse: Handelstag · y-Achse: Preis · steigende Linie = Beschaffung wird teurer."
    )


# --------------------------------------------------------------------------
# Tabelle (eigenes dunkles HTML)
# --------------------------------------------------------------------------
st.markdown('<div class="eyebrow">Rohdaten</div>', unsafe_allow_html=True)
st.subheader("Daten")
if not df.empty:
    tab = df.sort_values("Datum", ascending=False)
    zeilen = "".join(
        f"<tr><td>{d.strftime('%d.%m.%Y')}</td>"
        f"<td class='num'>{p:.2f}</td><td>{j}</td></tr>"
        for d, p, j in zip(tab["Datum"], tab["Preis"], tab["Lieferjahr"])
    )
    st.markdown(
        f"""
        <div class="tbl-wrap"><table class="tbl">
          <thead><tr><th>Datum</th><th class="num">Preis ({EINHEIT})</th><th>Lieferjahr</th></tr></thead>
          <tbody>{zeilen}</tbody>
        </table></div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------
# KI-Zusammenfassung (Platzhalter – SAIA-Anbindung folgt)
# --------------------------------------------------------------------------
st.markdown('<div class="eyebrow">Analyse</div>', unsafe_allow_html=True)
st.subheader("KI-Zusammenfassung")
st.caption("Nächster Schritt: SAIA/KISSKI-Aufruf aus Finale.py einhängen (Key aus st.secrets).")
if st.button("Zusammenfassung erstellen"):
    st.info("SAIA-Anbindung folgt.")
