"""
Energiepreis-Monitoring – Streamlit-Dashboard (eigenständig, Design im Skript)

Datenfluss:  Browse AI  ->  Google Sheets (ein Sheet pro Lieferjahr)  ->  Streamlit
Start:       py -m streamlit run app.py
Zugriff:     Sheets freigeben auf "Jeder mit dem Link -> Betrachter".

Hinweis: Das gesamte Design steckt hier im Skript (CSS unten).
Eine .streamlit/config.toml wird nicht mehr benoetigt.
"""

from pathlib import Path
from uuid import uuid4

import altair as alt
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# --------------------------------------------------------------------------
# Konfiguration
# --------------------------------------------------------------------------
st.set_page_config(page_title="Energiepreis-Monitoring", page_icon="⚡",
                   layout="wide", initial_sidebar_state="collapsed")

BASE_DIR = Path(__file__).resolve().parent
LOGO = BASE_DIR / "logo.png"

SHEETS = {
    "2027": "https://docs.google.com/spreadsheets/d/1StFUHaubVCMPV-VuKDlUPBx0_wQLwp8mEXQ563KsVOQ/edit",
    "2028": "https://docs.google.com/spreadsheets/d/1bssO6n9-u-FX4U6KelvqHfhs8WJS5CTimYB4gp7M1zU/edit",
    "2029": "https://docs.google.com/spreadsheets/d/1glQGEQmyhM_tgmA1ID5LTkuayLrzsDTTk9AKFhp0Heg/edit",
}

# Sheet mit der taeglich ueberschriebenen KI-Marktanalyse (ein Textblock)
KI_SHEET_URL = "https://docs.google.com/spreadsheets/d/1sWpKfXkTIA-0G6HlhkWiM32ZZcu7rL73zsbPOLTB7_4/edit"

# Gemeinsames Google Sheet für dauerhaft gespeicherte Ampel-Grenzwerte
# und gespeicherte Angebote.
DASHBOARD_STORE_URL = "https://docs.google.com/spreadsheets/d/1gKuHzknlzCSyuWf1IdkrbKm2OoN5VYv0YZqf_Ho0Tsg/edit"

ROH_EINHEIT = "EUR/MWh"   # Einheit, wie sie in den Google Sheets steht
AMPEL_SCHWELLE = 1.0

# Standardwerte für die Bewertung des Vergabepreis-Aufschlags.
# Die Werte können später direkt im Dashboard angepasst werden.
AUFSCHLAG_GRUEN_MAX_DEFAULT = 20.0
AUFSCHLAG_GELB_MAX_DEFAULT = 28.0

# Anzeige-Einheiten: Label -> (Faktor gegenüber EUR/MWh, Nachkommastellen)
EINHEITEN = {"EUR/MWh": (1.0, 2), "ct/kWh": (0.1, 2)}

# Klar unterscheidbare Farben pro Lieferjahr (Cyan / Blau / Violett)
FARBEN = {"2027": "#34E0FF", "2028": "#5B8DEF", "2029": "#C084FC"}


conn = st.connection("gsheets", type=GSheetsConnection)

STORE_COLUMNS = [
    "Typ",
    "ID",
    "Wert",
    "Zeitstempel",
    "Anbieter",
    "Lieferjahr",
    "Marktpreis_ct_kWh",
    "Vergabepreis_ct_kWh",
    "Aufschlag_ct_kWh",
    "Aufschlag_pct",
    "Bewertung",
    "Status",
]


def _empty_store() -> pd.DataFrame:
    return pd.DataFrame(columns=STORE_COLUMNS)


def load_dashboard_store() -> pd.DataFrame:
    """Liest Einstellungen und Angebote ohne Cache aus dem gemeinsamen Google Sheet."""
    try:
        raw = conn.read(spreadsheet=DASHBOARD_STORE_URL, ttl=0)
        if raw is None or raw.empty:
            return _empty_store()

        raw = raw.dropna(how="all").copy()
        for column in STORE_COLUMNS:
            if column not in raw.columns:
                raw[column] = None
        return raw[STORE_COLUMNS]
    except Exception:
        # Ein komplett leeres Sheet kann beim ersten Abruf je nach Connector
        # noch keine Spalten enthalten. In diesem Fall startet die App leer.
        return _empty_store()


def save_dashboard_store(store: pd.DataFrame) -> None:
    """Schreibt den vollständigen Einstellungs-/Angebotsspeicher zurück."""
    store = store.copy()
    for column in STORE_COLUMNS:
        if column not in store.columns:
            store[column] = None
    conn.update(spreadsheet=DASHBOARD_STORE_URL, data=store[STORE_COLUMNS])


def read_setting(store: pd.DataFrame, setting_id: str, default: float) -> float:
    rows = store[(store["Typ"] == "Einstellung") & (store["ID"] == setting_id)]
    if rows.empty:
        return float(default)
    value = pd.to_numeric(rows.iloc[-1]["Wert"], errors="coerce")
    return float(value) if pd.notna(value) else float(default)


def upsert_setting(store: pd.DataFrame, setting_id: str, value: float) -> pd.DataFrame:
    store = store.copy()
    mask = (store["Typ"] == "Einstellung") & (store["ID"] == setting_id)
    store = store.loc[~mask]
    row = {column: None for column in STORE_COLUMNS}
    row.update(
        {
            "Typ": "Einstellung",
            "ID": setting_id,
            "Wert": float(value),
            "Zeitstempel": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Status": "aktiv",
        }
    )
    return pd.concat([store, pd.DataFrame([row])], ignore_index=True)


def append_offer(store: pd.DataFrame, offer: dict) -> pd.DataFrame:
    row = {column: None for column in STORE_COLUMNS}
    row.update(offer)
    return pd.concat([store, pd.DataFrame([row])], ignore_index=True)


def set_offer_status(store: pd.DataFrame, offer_id: str, status: str) -> pd.DataFrame:
    store = store.copy()
    mask = (store["Typ"] == "Angebot") & (store["ID"].astype(str) == str(offer_id))
    store.loc[mask, "Status"] = status
    return store

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

    /* Sidebar wird nicht mehr gebraucht (Filter ist oben im Hauptbereich) */
    [data-testid="stSidebar"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"] { display: none !important; }

    /* Widget-Beschriftungen hell */
    [data-testid="stWidgetLabel"] * { color: #D7E6F0 !important; }

    /* Radio-Optionen (Zeitraum) gut lesbar */
    [data-testid="stRadio"] label,
    [data-testid="stRadio"] label div,
    [data-testid="stRadio"] label p,
    [data-testid="stRadio"] label span { color: #E6F1F8 !important; }

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
        .str.replace(ROH_EINHEIT, "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.strip(),
        errors="coerce",
    )
    df["Lieferjahr"] = jahr
    return df.dropna(subset=["Datum", "Preis"])


@st.cache_data(ttl=600)
def load_ki_text(url: str) -> str:
    """Liest den täglich überschriebenen KI-Analysetext (erste Spalte des Sheets)."""
    raw = conn.read(spreadsheet=url).dropna(how="all")
    if raw.empty:
        return ""
    col = raw.columns[0]
    return "\n".join(raw[col].dropna().astype(str)).strip()


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
# Zeitraum-Optionen
# --------------------------------------------------------------------------
ZEITRAEUME = {"Letzte 30 Tage": 30, "Letzte 60 Tage": 60,
              "Letzte 90 Tage": 90, "Benutzerdefiniert": None}
max_date = data["Datum"].max()
min_date = data["Datum"].min()


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


# --------------------------------------------------------------------------
# Filter (aufklappbar)
# --------------------------------------------------------------------------
with st.expander("🔎 Filter", expanded=False):
    f_jahr, f_zeit, f_einheit = st.columns([1.2, 1.8, 0.8])
    with f_jahr:
        auswahl = st.multiselect("Lieferjahr", options=alle_jahre, default=alle_jahre)
    with f_zeit:
        wahl = st.radio("Zeitraum", options=list(ZEITRAEUME), index=0, horizontal=True)
    with f_einheit:
        einheit = st.radio("Einheit", options=list(EINHEITEN), index=0)
    faktor, nk = EINHEITEN[einheit]

    if ZEITRAEUME[wahl] is None:
        default_von = max(min_date, max_date - pd.Timedelta(days=30)).date()
        sel = st.date_input(
            "Von – Bis",
            value=(default_von, max_date.date()),
            min_value=min_date.date(), max_value=max_date.date(),
            format="DD.MM.YYYY",
        )
        if isinstance(sel, (list, tuple)):
            von, bis = (sel[0], sel[1]) if len(sel) == 2 else (sel[0], sel[0])
        else:
            von = bis = sel
        zeit_label = f"{von.strftime('%d.%m.%Y')} – {bis.strftime('%d.%m.%Y')}"
        maske = (data["Datum"].dt.date >= von) & (data["Datum"].dt.date <= bis)
    else:
        tage = ZEITRAEUME[wahl]
        zeit_label = f"letzte {tage} Tage"
        maske = data["Datum"] >= (max_date - pd.Timedelta(days=tage))

df = data[(data["Lieferjahr"].isin(auswahl)) & maske].copy()
df["Wert"] = df["Preis"] * faktor

st.caption(
    f"Letzter Handelstag: {max_date.strftime('%d.%m.%Y')}  ·  "
    f"Trend: {zeit_label}  ·  Ampel: 🟢 gefallen · 🟡 stabil · 🔴 gestiegen"
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
    cur_d = cur * faktor
    delta_d = delta * faktor
    return f"""
    <div class="kpi-card">
      <div class="kpi-eyebrow">Cal {jahr}</div>
      <div class="kpi-price">{cur_d:.{nk}f}<span class="kpi-unit">{einheit}</span></div>
      <div class="kpi-delta {richtung}">{pfeil} {delta_d:+.{nk}f} ({pct:+.1f} %)</div>
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

with st.expander("Wie sind die Kennzahlen zu lesen?"):
    st.markdown(
        "- **Großer Wert:** aktueller Börsen-Settlementpreis (EUR/MWh) für das Lieferjahr.\n"
        "- **Pfeil + Prozent:** der Trend, also die Veränderung gegenüber dem Anfang des "
        "gewählten Zeitraums. Beispiel: ▲ +5 % heißt, der Preis liegt aktuell 5 % höher als "
        "zu Beginn des Zeitraums.\n"
        "- **Ampel:** 🟢 Preis gefallen (tendenziell günstiger für den Einkauf) · "
        "🟡 stabil · 🔴 Preis gestiegen (Beschaffung wird teurer).\n\n"
        "Kurz gesagt: Die Kennzahl zeigt, in welche Richtung sich der Beschaffungspreis "
        "zuletzt bewegt hat."
    )


# --------------------------------------------------------------------------
# Preisverlauf (Altair, dunkel)
# --------------------------------------------------------------------------
st.markdown('<div class="eyebrow">Verlauf</div>', unsafe_allow_html=True)
st.subheader(f"Preisverlauf ({einheit})")

if not df.empty:
    jahre_im_chart = [j for j in FARBEN if j in df["Lieferjahr"].unique()]
    chart = (
        alt.Chart(df)
        .mark_line(strokeWidth=2.6, interpolate="monotone")
        .encode(
            x=alt.X("Datum:T", title="Handelstag"),
            y=alt.Y("Wert:Q", title=einheit, scale=alt.Scale(zero=False)),
            color=alt.Color(
                "Lieferjahr:N",
                scale=alt.Scale(domain=jahre_im_chart,
                                range=[FARBEN[j] for j in jahre_im_chart]),
                legend=alt.Legend(title="Lieferjahr", orient="bottom"),
            ),
            tooltip=[
                alt.Tooltip("Datum:T", title="Datum"),
                alt.Tooltip("Lieferjahr:N", title="Lieferjahr"),
                alt.Tooltip("Wert:Q", title=einheit, format=f".{nk}f"),
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
        f"Der Wert ist der Börsen-Settlementpreis in {einheit}, zu dem Strom für "
        "Lieferung im jeweiligen Jahr gehandelt wird. "
        "x-Achse: Handelstag · y-Achse: Preis · steigende Linie = Beschaffung wird teurer."
    )

    # Statistik + Einordnung (aufklappbar)
    with st.expander("Statistik im Zeitraum", expanded=False):
        stats = df.groupby("Lieferjahr")["Wert"].agg(["min", "mean", "max"]).reset_index()
        zeilen_stat = "".join(
            f"<tr><td>{r['Lieferjahr']}</td>"
            f"<td class='num'>{r['min']:.{nk}f}</td>"
            f"<td class='num'>{r['mean']:.{nk}f}</td>"
            f"<td class='num'>{r['max']:.{nk}f}</td></tr>"
            for _, r in stats.iterrows()
        )
        st.markdown(
            f"""
            <div class="tbl-wrap"><table class="tbl">
              <thead><tr><th>Lieferjahr</th>
                <th class="num">Min ({einheit})</th>
                <th class="num">Ø ({einheit})</th>
                <th class="num">Max ({einheit})</th></tr></thead>
              <tbody>{zeilen_stat}</tbody>
            </table></div>
            """,
            unsafe_allow_html=True,
        )

        # Einordnung: aktueller Preis ggue. Durchschnitt (Ampel) + Lage zu Min/Max
        einordnung = ""
        for _, r in stats.iterrows():
            jahr, mn, avg, mx = r["Lieferjahr"], r["min"], r["mean"], r["max"]
            aktuell = df[df["Lieferjahr"] == jahr].sort_values("Datum")["Wert"].iloc[-1]
            abw = (aktuell - avg) / avg * 100 if avg else 0.0
            if abw > 1:
                dot, txt = "red", "über Ø (teurer als Schnitt)"
            elif abw < -1:
                dot, txt = "green", "unter Ø (günstiger als Schnitt)"
            else:
                dot, txt = "yellow", "auf Ø-Niveau"
            if mx > mn:
                anteil = (aktuell - mn) / (mx - mn)
                lage = "nahe Minimum" if anteil < 0.33 else ("nahe Maximum" if anteil > 0.66 else "im Mittelfeld")
            else:
                lage = "konstant"
            einordnung += (
                f"<div class='kpi-amp'><span class='dot {dot}'></span>"
                f"<b>Cal {jahr}</b>&nbsp;aktuell {aktuell:.{nk}f} {einheit} · "
                f"{abw:+.1f} % ggü. Ø · {txt} · {lage}</div>"
            )
        st.markdown(einordnung, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Vergabepreis-Vergleich, dauerhafte Grenzwerte und Angebotsablage
# --------------------------------------------------------------------------
dashboard_store = load_dashboard_store()

# Die Grenzwerte werden beim Öffnen aus Google Sheets gelesen.
gruen_max = read_setting(
    dashboard_store, "aufschlag_gruen_max", AUFSCHLAG_GRUEN_MAX_DEFAULT
)
gelb_max = read_setting(
    dashboard_store, "aufschlag_gelb_max", AUFSCHLAG_GELB_MAX_DEFAULT
)

# Schutz vor fehlerhaften gespeicherten Grenzen.
if gelb_max <= gruen_max:
    gruen_max = AUFSCHLAG_GRUEN_MAX_DEFAULT
    gelb_max = AUFSCHLAG_GELB_MAX_DEFAULT

with st.expander("Vergabepreis-Vergleich", expanded=False):
    V_FAKTOR, V_NK, V_EINHEIT = 0.1, 2, "ct/kWh"

    v1, v2 = st.columns([1, 1])
    with v1:
        ref_jahr = st.selectbox(
            "Lieferjahr",
            options=alle_jahre,
            index=0,
            key="vergabepreis_lieferjahr",
        )

    reihe_ref = data[data["Lieferjahr"] == ref_jahr].sort_values("Datum")
    marktpreis = (
        round(reihe_ref["Preis"].iloc[-1] * V_FAKTOR, V_NK)
        if not reihe_ref.empty
        else 0.0
    )
    marktpreis_datum = (
        reihe_ref["Datum"].iloc[-1].strftime("%d.%m.%Y")
        if not reihe_ref.empty
        else "–"
    )

    with v2:
        vergabepreis = st.number_input(
            f"Vergabepreis ({V_EINHEIT})",
            min_value=0.0,
            value=float(marktpreis),
            step=0.01,
            format=f"%.{V_NK}f",
            key=f"vergabepreis_{ref_jahr}",
        )

    auf_wert = 0.0
    auf_pct = 0.0
    label = "keine Bewertung"
    farbe = "#9DB3C4"

    if vergabepreis > 0 and marktpreis > 0:
        auf_wert = vergabepreis - marktpreis
        auf_pct = auf_wert / marktpreis * 100

        if auf_pct <= gruen_max:
            farbe, label = "#37E6A6", "günstiger als üblich"
        elif auf_pct <= gelb_max:
            farbe, label = "#FFC24B", "im üblichen Bereich"
        else:
            farbe, label = "#FF6B7A", "auffällig hoher Aufschlag"

        st.markdown(
            f"""
            <div class="kpi-card">
              <div class="kpi-eyebrow">{label} · Cal {ref_jahr}</div>
              <div class="kpi-price" style="color:{farbe}">{auf_wert:+.{V_NK}f}<span class="kpi-unit">{V_EINHEIT}</span></div>
              <div class="kpi-delta" style="color:{farbe}">{auf_pct:+.1f} % gegenüber Marktpreis</div>
              <div class="kpi-amp">
                Marktpreis {marktpreis:.{V_NK}f} · Vergabepreis {vergabepreis:.{V_NK}f} {V_EINHEIT}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(
            f"Verglichen wird mit dem neuesten verfügbaren EEX-Settlementpreis "
            f"vom {marktpreis_datum}. Der Aufschlag kann unter anderem Marge, "
            "Bilanzkreis-/Profilkosten und Risikoaufschläge enthalten."
        )

    st.divider()
    st.markdown("#### 💾 Angebot speichern")

    with st.form("angebot_speichern_form", clear_on_submit=True):
        anbieter = st.text_input(
            "Anbieter",
            placeholder="z. B. Stadtwerke Musterstadt",
        )
        angebot_notiz = st.text_input(
            "Optionale Notiz",
            placeholder="z. B. Erstangebot oder Preisbindung bis 15.08.",
        )
        angebot_speichern = st.form_submit_button(
            "Angebot dauerhaft speichern",
            use_container_width=True,
        )

    if angebot_speichern:
        if not anbieter.strip():
            st.error("Bitte einen Anbieter eingeben.")
        elif vergabepreis <= 0 or marktpreis <= 0:
            st.error("Marktpreis und Vergabepreis müssen größer als null sein.")
        else:
            try:
                offer_id = str(uuid4())
                gespeicherte_bewertung = label
                if angebot_notiz.strip():
                    gespeicherte_bewertung += f" · {angebot_notiz.strip()}"

                dashboard_store = append_offer(
                    load_dashboard_store(),
                    {
                        "Typ": "Angebot",
                        "ID": offer_id,
                        "Zeitstempel": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Anbieter": anbieter.strip(),
                        "Lieferjahr": ref_jahr,
                        "Marktpreis_ct_kWh": round(marktpreis, V_NK),
                        "Vergabepreis_ct_kWh": round(float(vergabepreis), V_NK),
                        "Aufschlag_ct_kWh": round(auf_wert, V_NK),
                        "Aufschlag_pct": round(auf_pct, 1),
                        "Bewertung": gespeicherte_bewertung,
                        "Status": "aktiv",
                    },
                )
                save_dashboard_store(dashboard_store)
                st.success(f"Angebot von {anbieter.strip()} wurde gespeichert.")
                st.rerun()
            except Exception as exc:
                st.error(
                    "Das Angebot konnte nicht gespeichert werden. "
                    "Prüfe die Schreibberechtigung des Google Sheets und die "
                    f"Streamlit-Secrets. Technischer Hinweis: {exc}"
                )

    st.divider()
    st.markdown("#### ⚙️ Ampel-Grenzwerte")

    grenzen_anzeigen = st.checkbox(
        "Grenzwerte anzeigen und dauerhaft anpassen",
        value=False,
    )

    if grenzen_anzeigen:
        st.caption(
            "Die Werte werden im Google Sheet gespeichert und gelten anschließend "
            "auch nach einem Neustart sowie für andere Nutzer des Dashboards."
        )

        with st.form("grenzwerte_form"):
            g1, g2 = st.columns(2)
            with g1:
                neue_gruene_grenze = st.number_input(
                    "Grün bis einschließlich (%)",
                    min_value=-100.0,
                    max_value=200.0,
                    value=float(gruen_max),
                    step=0.5,
                )
            with g2:
                neue_gelbe_grenze = st.number_input(
                    "Gelb bis einschließlich (%)",
                    min_value=-100.0,
                    max_value=200.0,
                    value=float(gelb_max),
                    step=0.5,
                )

            grenzen_speichern = st.form_submit_button(
                "Grenzwerte dauerhaft speichern",
                use_container_width=True,
            )

        st.markdown(
            f"""
            | Aufschlag gegenüber Marktpreis | Ampel | Bewertung |
            |---:|:---:|---|
            | **≤ {gruen_max:.1f} %** | 🟢 | Günstiger als üblich |
            | **> {gruen_max:.1f} % bis {gelb_max:.1f} %** | 🟡 | Im üblichen Bereich |
            | **> {gelb_max:.1f} %** | 🔴 | Auffällig hoher Aufschlag |
            """
        )

        if grenzen_speichern:
            if neue_gelbe_grenze <= neue_gruene_grenze:
                st.error(
                    "Die gelbe Obergrenze muss größer als die grüne Obergrenze sein."
                )
            else:
                try:
                    current_store = load_dashboard_store()
                    current_store = upsert_setting(
                        current_store,
                        "aufschlag_gruen_max",
                        neue_gruene_grenze,
                    )
                    current_store = upsert_setting(
                        current_store,
                        "aufschlag_gelb_max",
                        neue_gelbe_grenze,
                    )
                    save_dashboard_store(current_store)
                    st.success("Die Ampel-Grenzwerte wurden dauerhaft gespeichert.")
                    st.rerun()
                except Exception as exc:
                    st.error(
                        "Die Grenzwerte konnten nicht gespeichert werden. "
                        "Prüfe die Schreibberechtigung des Google Sheets und die "
                        f"Streamlit-Secrets. Technischer Hinweis: {exc}"
                    )

    st.divider()
    st.markdown("#### 📁 Gespeicherte Angebote")

    angebote = dashboard_store[dashboard_store["Typ"] == "Angebot"].copy()
    aktive_angebote = angebote[
        angebote["Status"].fillna("aktiv").astype(str).str.lower() != "archiviert"
    ].copy()
    archivierte_angebote = angebote[
        angebote["Status"].fillna("").astype(str).str.lower() == "archiviert"
    ].copy()

    if aktive_angebote.empty:
        st.info("Noch keine aktiven Angebote gespeichert.")
    else:
        aktive_angebote = aktive_angebote.sort_values(
            "Zeitstempel", ascending=False
        )
        for _, angebot in aktive_angebote.iterrows():
            angebot_id = str(angebot["ID"])
            anbieter_name = str(angebot.get("Anbieter") or "Unbekannter Anbieter")
            cal = str(angebot.get("Lieferjahr") or "–")
            preis = pd.to_numeric(
                angebot.get("Vergabepreis_ct_kWh"), errors="coerce"
            )
            prozent = pd.to_numeric(
                angebot.get("Aufschlag_pct"), errors="coerce"
            )
            zeit = str(angebot.get("Zeitstempel") or "–")
            bewertung = str(angebot.get("Bewertung") or "–")

            card_col, button_col = st.columns([5, 1], vertical_alignment="center")
            with card_col:
                preis_text = f"{preis:.2f}" if pd.notna(preis) else "–"
                pct_text = f"{prozent:+.1f} %" if pd.notna(prozent) else "–"
                st.markdown(
                    f"**{anbieter_name} · Cal {cal}**  \n"
                    f"{preis_text} ct/kWh · {pct_text} · {bewertung}  \n"
                    f"<span style='color:#8FA9BC;font-size:.82rem'>{zeit}</span>",
                    unsafe_allow_html=True,
                )
            with button_col:
                if st.button(
                    "Archivieren",
                    key=f"archivieren_{angebot_id}",
                    use_container_width=True,
                ):
                    try:
                        current_store = set_offer_status(
                            load_dashboard_store(), angebot_id, "archiviert"
                        )
                        save_dashboard_store(current_store)
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Archivieren nicht möglich: {exc}")

    with st.expander(
        f"Archivierte Angebote ({len(archivierte_angebote)})",
        expanded=False,
    ):
        if archivierte_angebote.empty:
            st.caption("Keine archivierten Angebote vorhanden.")
        else:
            archivierte_angebote = archivierte_angebote.sort_values(
                "Zeitstempel", ascending=False
            )
            for _, angebot in archivierte_angebote.iterrows():
                angebot_id = str(angebot["ID"])
                anbieter_name = str(
                    angebot.get("Anbieter") or "Unbekannter Anbieter"
                )
                cal = str(angebot.get("Lieferjahr") or "–")
                preis = pd.to_numeric(
                    angebot.get("Vergabepreis_ct_kWh"), errors="coerce"
                )
                preis_text = f"{preis:.2f}" if pd.notna(preis) else "–"

                info_col, restore_col = st.columns(
                    [5, 1], vertical_alignment="center"
                )
                with info_col:
                    st.markdown(
                        f"**{anbieter_name} · Cal {cal}** · "
                        f"{preis_text} ct/kWh"
                    )
                with restore_col:
                    if st.button(
                        "Zurückholen",
                        key=f"zurueckholen_{angebot_id}",
                        use_container_width=True,
                    ):
                        try:
                            current_store = set_offer_status(
                                load_dashboard_store(), angebot_id, "aktiv"
                            )
                            save_dashboard_store(current_store)
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Zurückholen nicht möglich: {exc}")


# --------------------------------------------------------------------------
# KI-Analyse (aufklappbar) – täglich überschriebenes Sheet
# --------------------------------------------------------------------------
with st.expander("KI-Analyse anzeigen", expanded=False):
    st.caption("Wird täglich automatisch aktualisiert. KI-generierte Einschätzung – keine Anlageberatung.")
    try:
        ki_text = load_ki_text(KI_SHEET_URL)
        if ki_text:
            st.markdown(ki_text)
        else:
            st.info("Aktuell keine KI-Analyse hinterlegt.")
    except Exception as exc:
        st.warning(f"KI-Analyse konnte nicht geladen werden: {exc}")


# --------------------------------------------------------------------------
# Tabelle (eigenes dunkles HTML, aufklappbar)
# --------------------------------------------------------------------------
if not df.empty:
    with st.expander("Rohdaten anzeigen", expanded=False):
        tab = df.sort_values("Datum", ascending=False)
        zeilen = "".join(
            f"<tr><td>{d.strftime('%d.%m.%Y')}</td>"
            f"<td class='num'>{w:.{nk}f}</td><td>{j}</td></tr>"
            for d, w, j in zip(tab["Datum"], tab["Wert"], tab["Lieferjahr"])
        )
        st.markdown(
            f"""
            <div class="tbl-wrap"><table class="tbl">
              <thead><tr><th>Datum</th><th class="num">Preis ({einheit})</th><th>Lieferjahr</th></tr></thead>
              <tbody>{zeilen}</tbody>
            </table></div>
            """,
            unsafe_allow_html=True,
        )
