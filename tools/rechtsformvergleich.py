"""
Rechtsformvergleich – Steuerbelastung verschiedener Rechtsformen simulieren.

Vergleicht:
- Einzelunternehmen (§15 EStG)
- GmbH (KSt + GewSt + Ausschüttung)
- UG (haftungsbeschränkt)
- GmbH & Co. KG (Mitunternehmerschaft)
- Freiberufler (§18 EStG, keine GewSt)

Berücksichtigt: ESt, KSt, GewSt, SolZ, KiSt, Ausschüttungsbelastung
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from tools.steuerrechner import (
    berechne_est_de,
    Tarif,
    _est_grundtarif_2025,
)


class Rechtsform(Enum):
    EINZELUNTERNEHMEN = "Einzelunternehmen"
    GMBH = "GmbH"
    UG = "UG (haftungsbeschränkt)"
    GMBH_CO_KG = "GmbH & Co. KG"
    FREIBERUFLER = "Freiberufler"


@dataclass
class RechtsformErgebnis:
    rechtsform: Rechtsform
    gewinn_vor_steuern: float
    gewerbesteuer: float
    koerperschaftsteuer: float
    einkommensteuer: float
    solidaritaetszuschlag: float
    kirchensteuer: float
    kapitalertragsteuer: float
    gesamtbelastung: float
    netto_nach_steuern: float
    effektive_steuerquote: float
    hinweise: list[str]


def _gewerbesteuer(
    gewinn: float,
    hebesatz: int = 400,
    freibetrag: float = 24_500,
    ist_kapitalgesellschaft: bool = False,
) -> float:
    """Berechnet Gewerbesteuer. Kapitalgesellschaften haben keinen Freibetrag."""
    if ist_kapitalgesellschaft:
        freibetrag = 0

    bemessungsgrundlage = max(0, gewinn - freibetrag)
    messbetrag = bemessungsgrundlage * 0.035  # Steuermesszahl 3,5%
    return round(messbetrag * hebesatz / 100, 2)


def _gewst_anrechnung_est(gewinn: float, hebesatz: int = 400) -> float:
    """GewSt-Anrechnung auf ESt: max. Faktor 4,0 des Messbetrag (§35 EStG)."""
    bemessungsgrundlage = max(0, gewinn - 24_500)
    messbetrag = bemessungsgrundlage * 0.035
    # Anrechnung: 4,0-faches des Messbetrag, max. tatsächliche GewSt
    anrechnung = messbetrag * 4.0
    tatsaechliche_gewst = messbetrag * hebesatz / 100
    return round(min(anrechnung, tatsaechliche_gewst), 2)


def berechne_einzelunternehmen(
    gewinn: float,
    hebesatz: int = 400,
    tarif: Tarif = Tarif.GRUND,
    kirchensteuer_satz: float = 0.0,
) -> RechtsformErgebnis:
    """Einzelunternehmen: ESt + GewSt (mit Anrechnung §35 EStG)."""
    gewst = _gewerbesteuer(gewinn, hebesatz)
    gewst_anrechnung = _gewst_anrechnung_est(gewinn, hebesatz)

    est_ergebnis = berechne_est_de(gewinn, tarif, kirchensteuer_satz)
    est_nach_anrechnung = max(0, est_ergebnis.einkommensteuer - gewst_anrechnung)

    soli = round(est_nach_anrechnung * 0.055, 2) if est_nach_anrechnung > 18_130 else 0
    kist = round(est_nach_anrechnung * kirchensteuer_satz, 2)

    gesamt = est_nach_anrechnung + gewst + soli + kist
    netto = gewinn - gesamt

    return RechtsformErgebnis(
        rechtsform=Rechtsform.EINZELUNTERNEHMEN,
        gewinn_vor_steuern=gewinn,
        gewerbesteuer=gewst,
        koerperschaftsteuer=0,
        einkommensteuer=est_nach_anrechnung,
        solidaritaetszuschlag=soli,
        kirchensteuer=kist,
        kapitalertragsteuer=0,
        gesamtbelastung=round(gesamt, 2),
        netto_nach_steuern=round(netto, 2),
        effektive_steuerquote=round(gesamt / gewinn * 100, 2) if gewinn > 0 else 0,
        hinweise=[
            f"GewSt-Anrechnung §35 EStG: {gewst_anrechnung:,.2f} €",
            f"Hebesatz: {hebesatz}%",
            "Volle Haftung mit Privatvermögen",
        ],
    )


def berechne_gmbh(
    gewinn: float,
    hebesatz: int = 400,
    geschaeftsfuehrer_gehalt: float = 0,
    ausschuettungsquote: float = 1.0,
    tarif: Tarif = Tarif.GRUND,
    kirchensteuer_satz: float = 0.0,
    ist_ug: bool = False,
) -> RechtsformErgebnis:
    """
    GmbH/UG: KSt + GewSt auf Gesellschaftsebene,
    dann KapESt auf Ausschüttung an Gesellschafter.
    GF-Gehalt mindert den Gewinn (Betriebsausgabe).
    """
    # Gewinn nach GF-Gehalt
    gewinn_gmbh = max(0, gewinn - geschaeftsfuehrer_gehalt)

    # Ebene 1: Gesellschaft
    kst = round(gewinn_gmbh * 0.15, 2)  # 15% KSt
    soli_kst = round(kst * 0.055, 2)    # 5,5% Soli auf KSt
    gewst = _gewerbesteuer(gewinn_gmbh, hebesatz, ist_kapitalgesellschaft=True)

    gewinn_nach_steuern = gewinn_gmbh - kst - soli_kst - gewst

    # UG: 25% Rücklage pflicht bis Stammkapital 25.000 € erreicht
    ruecklage = 0
    if ist_ug:
        ruecklage = round(gewinn_nach_steuern * 0.25, 2)
        gewinn_nach_steuern -= ruecklage

    # Ebene 2: Ausschüttung an Gesellschafter
    ausschuettung = gewinn_nach_steuern * ausschuettungsquote
    kapest = round(ausschuettung * 0.25, 2)    # 25% KapESt
    soli_kapest = round(kapest * 0.055, 2)
    kist_kapest = round(kapest * kirchensteuer_satz, 2)

    # Ebene 3: GF-Gehalt wird als Einkommen versteuert
    est_gf = 0
    soli_gf = 0
    kist_gf = 0
    if geschaeftsfuehrer_gehalt > 0:
        gf_ergebnis = berechne_est_de(geschaeftsfuehrer_gehalt, tarif, kirchensteuer_satz)
        est_gf = gf_ergebnis.einkommensteuer
        soli_gf = gf_ergebnis.solidaritaetszuschlag
        kist_gf = gf_ergebnis.kirchensteuer

    gesamt = kst + soli_kst + gewst + kapest + soli_kapest + kist_kapest + est_gf + soli_gf + kist_gf
    netto = gewinn - gesamt - ruecklage

    rechtsform = Rechtsform.UG if ist_ug else Rechtsform.GMBH

    hinweise = [
        f"KSt 15% + Soli: {kst + soli_kst:,.2f} €",
        f"GewSt (Hebesatz {hebesatz}%): {gewst:,.2f} €",
        f"Ausschüttung {ausschuettungsquote*100:.0f}%: KapESt {kapest:,.2f} €",
    ]
    if geschaeftsfuehrer_gehalt > 0:
        hinweise.append(f"GF-Gehalt {geschaeftsfuehrer_gehalt:,.0f} €: ESt {est_gf:,.2f} €")
    if ist_ug and ruecklage > 0:
        hinweise.append(f"UG-Rücklage (25%): {ruecklage:,.2f} €")
    hinweise.append("Haftung beschränkt auf Gesellschaftsvermögen")

    return RechtsformErgebnis(
        rechtsform=rechtsform,
        gewinn_vor_steuern=gewinn,
        gewerbesteuer=gewst,
        koerperschaftsteuer=kst + soli_kst,
        einkommensteuer=est_gf,
        solidaritaetszuschlag=soli_gf + soli_kapest,
        kirchensteuer=kist_gf + kist_kapest,
        kapitalertragsteuer=kapest,
        gesamtbelastung=round(gesamt, 2),
        netto_nach_steuern=round(netto, 2),
        effektive_steuerquote=round(gesamt / gewinn * 100, 2) if gewinn > 0 else 0,
        hinweise=hinweise,
    )


def berechne_freiberufler(
    gewinn: float,
    tarif: Tarif = Tarif.GRUND,
    kirchensteuer_satz: float = 0.0,
) -> RechtsformErgebnis:
    """Freiberufler §18 EStG: Nur ESt, keine Gewerbesteuer."""
    est_ergebnis = berechne_est_de(gewinn, tarif, kirchensteuer_satz)

    gesamt = est_ergebnis.gesamt_belastung
    netto = gewinn - gesamt

    return RechtsformErgebnis(
        rechtsform=Rechtsform.FREIBERUFLER,
        gewinn_vor_steuern=gewinn,
        gewerbesteuer=0,
        koerperschaftsteuer=0,
        einkommensteuer=est_ergebnis.einkommensteuer,
        solidaritaetszuschlag=est_ergebnis.solidaritaetszuschlag,
        kirchensteuer=est_ergebnis.kirchensteuer,
        kapitalertragsteuer=0,
        gesamtbelastung=round(gesamt, 2),
        netto_nach_steuern=round(netto, 2),
        effektive_steuerquote=round(gesamt / gewinn * 100, 2) if gewinn > 0 else 0,
        hinweise=[
            "Keine Gewerbesteuer (§18 EStG)",
            "Keine IHK-Pflichtmitgliedschaft",
            "Volle Haftung mit Privatvermögen",
            "Katalogberufe: Ärzte, Rechtsanwälte, Steuerberater, Ingenieure, etc.",
        ],
    )


def vergleiche_rechtsformen(
    gewinn: float,
    hebesatz: int = 400,
    geschaeftsfuehrer_gehalt: float = 0,
    kirchensteuer_satz: float = 0.0,
    tarif: Tarif = Tarif.GRUND,
) -> list[RechtsformErgebnis]:
    """Vergleicht alle Rechtsformen für gegebenen Gewinn."""
    return [
        berechne_einzelunternehmen(gewinn, hebesatz, tarif, kirchensteuer_satz),
        berechne_gmbh(gewinn, hebesatz, geschaeftsfuehrer_gehalt, 1.0, tarif, kirchensteuer_satz),
        berechne_gmbh(gewinn, hebesatz, geschaeftsfuehrer_gehalt, 1.0, tarif, kirchensteuer_satz, ist_ug=True),
        berechne_freiberufler(gewinn, tarif, kirchensteuer_satz),
    ]


# --- CLI-Modus ---

if __name__ == "__main__":
    print("=== Rechtsformvergleich ===\n")

    for gewinn in [50_000, 100_000, 200_000, 500_000]:
        print(f"--- Gewinn: {gewinn:,.0f} € (Hebesatz 400%, GF-Gehalt 60.000 €) ---")

        ergebnisse = vergleiche_rechtsformen(
            gewinn=gewinn,
            hebesatz=400,
            geschaeftsfuehrer_gehalt=60_000,
            kirchensteuer_satz=0.09,
        )

        for erg in ergebnisse:
            print(
                f"  {erg.rechtsform.value:<25} | "
                f"Gesamt: {erg.gesamtbelastung:>10,.2f} € | "
                f"Netto: {erg.netto_nach_steuern:>10,.2f} € | "
                f"Quote: {erg.effektive_steuerquote:>5.1f}%"
            )

        # Beste Option
        beste = min(ergebnisse, key=lambda e: e.gesamtbelastung)
        print(f"  → Günstigste Option: {beste.rechtsform.value}")
        print()
