"""
Smoke-Test für das Energiepreis-Dashboard.

Ausführen:
    py -m pip install pytest
    py -m pytest -v test_app.py

Hinweis: Der Test führt die echte App aus und lädt dabei live die Google Sheets.
Er braucht also Internet, und die Sheets müssen freigegeben sein
("Jeder mit dem Link -> Betrachter"). Schlägt ein Sheet fehl, meldet das
test_daten_geladen – genau so soll es sein.
"""

from streamlit.testing.v1 import AppTest


def _run():
    at = AppTest.from_file("app.py", default_timeout=60)
    return at.run()


def test_app_laeuft_ohne_fehler():
    at = _run()
    assert not at.exception, at.exception


def test_daten_geladen():
    # Wenn die Sheets erreichbar sind, darf kein "Keine Daten"-Fehler kommen
    at = _run()
    assert not at.error, [e.value for e in at.error]


def test_titel_vorhanden():
    at = _run()
    assert any("Energiepreis-Monitoring" in t.value for t in at.title)


def test_kernsektionen_da():
    at = _run()
    subs = [s.value for s in at.subheader]
    assert any("Preisverlauf" in s for s in subs)
    assert any("Vergabepreis" in s for s in subs)


def test_einheit_umschalten_ok():
    at = _run()
    for r in at.radio:
        if "ct/kWh" in r.options:
            r.set_value("ct/kWh").run()
            break
    assert not at.exception


def test_zeitraum_umschalten_ok():
    at = _run()
    for r in at.radio:
        if "Letzte 90 Tage" in r.options:
            r.set_value("Letzte 90 Tage").run()
            break
    assert not at.exception
