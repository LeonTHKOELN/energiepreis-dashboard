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
st.set_page_config(page_title="Energiepreis-Monitoring", page_icon="⚡",
                   layout="wide", initial_sidebar_state="collapsed")

BASE_DIR = Path(__file__).resolve().parent
LOGO = BASE_DIR / "logo.png"

SHEETS = {
    "2027": "https://docs.google.com/spreadsheets/d/1StFUHaubVCMPV-VuKDlUPBx0_wQLwp8mEXQ563KsVOQ/edit",
    "2028": "https://docs.google.com/spreadsheets/d/1bssO6n9-u-FX4U6KelvqHfhs8WJS5CTimYB4gp7M1zU/edit",
    "2029": "https://docs.google.com/spreadsheets/d/1glQGEQmyhM_tgmA1ID5LTkuayLrzsDTTk9AKFhp0Heg/edit",
}

ROH_EINHEIT = "EUR/MWh"   # Einheit, wie sie in den Google Sheets steht
AMPEL_SCHWELLE = 1.0

# Anzeige-Einheiten: Label -> (Faktor gegenüber EUR/MWh, Nachkommastellen)
EINHEITEN = {"EUR/MWh": (1.0, 2), "ct/kWh": (0.1, 2)}

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
with st.expander("🔎 Filter", expanded=True):
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
    with st.expander("Statistik im Zeitraum", expanded=True):
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
# Vergabepreis-Vergleich (immer in ct/kWh)
# --------------------------------------------------------------------------
st.markdown('<div class="eyebrow">Vergabe</div>', unsafe_allow_html=True)
st.subheader("Vergabepreis-Vergleich")

V_FAKTOR, V_NK, V_EINHEIT = 0.1, 2, "ct/kWh"   # EUR/MWh -> ct/kWh

v1, v2 = st.columns([1, 1])
with v1:
    ref_jahr = st.selectbox("Lieferjahr", options=alle_jahre, index=0)
reihe_ref = data[data["Lieferjahr"] == ref_jahr].sort_values("Datum")
marktpreis = round(reihe_ref["Preis"].iloc[-1] * V_FAKTOR, V_NK) if not reihe_ref.empty else 0.0
with v2:
    vergabepreis = st.number_input(
        f"Vergabepreis ({V_EINHEIT})",
        min_value=0.0, value=marktpreis, step=0.01, format=f"%.{V_NK}f",
    )

if vergabepreis > 0 and marktpreis > 0:
    auf_wert = vergabepreis - marktpreis
    auf_pct = auf_wert / marktpreis * 100
    eps = 0.5 * 10 ** (-V_NK)   # halbe Anzeigestelle Toleranz
    if auf_wert > eps:
        farbe, label = "#FF6B7A", "Aufschlag über Marktpreis"
    elif auf_wert < -eps:
        farbe, label = "#37E6A6", "Abschlag unter Marktpreis"
    else:
        farbe, label = "#FFC24B", "auf Marktpreisniveau"
    st.markdown(
        f"""
        <div class="kpi-card">
          <div class="kpi-eyebrow">{label} · Cal {ref_jahr}</div>
          <div class="kpi-price" style="color:{farbe}">{auf_wert:+.{V_NK}f}<span class="kpi-unit">{V_EINHEIT}</span></div>
          <div class="kpi-delta" style="color:{farbe}">{auf_pct:+.1f} % gegenüber Marktpreis</div>
          <div class="kpi-amp">Marktpreis {marktpreis:.{V_NK}f} · Vergabepreis {vergabepreis:.{V_NK}f} {V_EINHEIT}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        "Marktpreis = aktueller EEX-Settlementpreis des gewählten Lieferjahres, umgerechnet in ct/kWh. "
        "Der Aufschlag ist die Differenz deines Vergabepreises dazu (z. B. Marge, Netzentgelte, Vertrieb)."
    )


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
