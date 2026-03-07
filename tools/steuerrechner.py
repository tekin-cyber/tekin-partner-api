"""
Steuerrechner – Einkommensteuer DE & TR mit DBA-Methoden.

Berechnet:
- Deutsche Einkommensteuer (Grundtarif + Splittingtarif)
- Türkische Gelir Vergisi (progressive Stufen)
- Progressionsvorbehalt bei Freistellung
- Anrechnungsmethode (§34c EStG)
- Solidaritätszuschlag und Kirchensteuer
"""

from dataclasses import dataclass
from enum import Enum


class DBAMethode(Enum):
    ANRECHNUNG = "anrechnung"
    FREISTELLUNG = "freistellung"


class Tarif(Enum):
    GRUND = "grundtarif"
    SPLITTING = "splittingtarif"


@dataclass
class SteuerErgebnis:
    zu_versteuerndes_einkommen: float
    einkommensteuer: float
    solidaritaetszuschlag: float
    kirchensteuer: float
    gesamt_belastung: float
    grenzsteuersatz: float
    durchschnittssteuersatz: float


@dataclass
class DBAErgebnis:
    methode: DBAMethode
    inlaendische_einkuenfte: float
    auslaendische_einkuenfte: float
    steuer_ohne_dba: float
    steuer_mit_dba: float
    entlastung: float
    erklaerung: str


# --- Deutsche Einkommensteuer 2024/2025 ---

def _est_grundtarif_2025(zve: float) -> float:
    """Berechnet ESt nach §32a EStG – Grundtarif 2025."""
    if zve <= 0:
        return 0.0

    # Grundfreibetrag
    if zve <= 12_096:
        return 0.0

    # Zone 2: 12.097 – 17.443
    if zve <= 17_443:
        y = (zve - 12_096) / 10_000
        return (922.98 * y + 1_400) * y

    # Zone 3: 17.444 – 66.760
    if zve <= 66_760:
        z = (zve - 17_443) / 10_000
        return (181.19 * z + 2_397) * z + 1_025.38

    # Zone 4: 66.761 – 277.825
    if zve <= 277_825:
        return 0.42 * zve - 10_636.31

    # Zone 5: ab 277.826 (Reichensteuer)
    return 0.45 * zve - 18_971.06


def _est_splittingtarif_2025(zve: float) -> float:
    """Splittingtarif: 2x Grundtarif auf halbes zvE."""
    return 2 * _est_grundtarif_2025(zve / 2)


def berechne_est_de(
    zve: float,
    tarif: Tarif = Tarif.GRUND,
    kirchensteuer_satz: float = 0.0,
) -> SteuerErgebnis:
    """Berechnet deutsche Einkommensteuer mit Soli und KiSt."""
    if tarif == Tarif.SPLITTING:
        est = _est_splittingtarif_2025(zve)
    else:
        est = _est_grundtarif_2025(zve)

    est = round(est, 2)

    # Soli: 5,5% der ESt, aber nur wenn ESt > Freigrenze (18.130 € Grund / 36.260 € Splitting)
    soli_freigrenze = 18_130 if tarif == Tarif.GRUND else 36_260
    if est <= soli_freigrenze:
        soli = 0.0
    else:
        soli = round(est * 0.055, 2)

    kist = round(est * kirchensteuer_satz, 2) if kirchensteuer_satz > 0 else 0.0

    gesamt = est + soli + kist
    durchschnitt = (est / zve * 100) if zve > 0 else 0.0
    grenz = _grenzsteuersatz_de(zve, tarif)

    return SteuerErgebnis(
        zu_versteuerndes_einkommen=zve,
        einkommensteuer=est,
        solidaritaetszuschlag=soli,
        kirchensteuer=kist,
        gesamt_belastung=round(gesamt, 2),
        grenzsteuersatz=round(grenz, 2),
        durchschnittssteuersatz=round(durchschnitt, 2),
    )


def _grenzsteuersatz_de(zve: float, tarif: Tarif) -> float:
    """Grenzsteuersatz durch Differenzrechnung."""
    fn = _est_splittingtarif_2025 if tarif == Tarif.SPLITTING else _est_grundtarif_2025
    delta = 1.0
    if zve <= 0:
        return 0.0
    return (fn(zve + delta) - fn(zve)) / delta * 100


# --- Türkische Einkommensteuer (Gelir Vergisi) 2024 ---

_TR_STUFEN_2024 = [
    (110_000, 0.15),
    (230_000, 0.20),
    (580_000, 0.27),
    (3_000_000, 0.35),
    (float("inf"), 0.40),
]


def berechne_gelir_vergisi(einkommen_try: float) -> dict:
    """Berechnet türkische Einkommensteuer (progressive Stufen)."""
    if einkommen_try <= 0:
        return {"einkommen_try": 0, "steuer_try": 0, "effektiv_prozent": 0}

    steuer = 0.0
    vorherige_grenze = 0.0

    for grenze, satz in _TR_STUFEN_2024:
        schicht = min(einkommen_try, grenze) - vorherige_grenze
        if schicht <= 0:
            break
        steuer += schicht * satz
        vorherige_grenze = grenze

    effektiv = (steuer / einkommen_try) * 100

    return {
        "einkommen_try": einkommen_try,
        "steuer_try": round(steuer, 2),
        "effektiv_prozent": round(effektiv, 2),
    }


# --- DBA-Methoden ---

def berechne_anrechnung(
    gesamt_einkommen: float,
    auslaendische_einkuenfte: float,
    auslaendische_steuer: float,
    tarif: Tarif = Tarif.GRUND,
) -> DBAErgebnis:
    """
    Anrechnungsmethode nach §34c EStG / Art. 22 DBA DE-TR.
    Ausländische Steuer wird auf deutsche ESt angerechnet,
    max. bis zum Höchstbetrag (anteilige dt. Steuer auf ausl. Einkünfte).
    """
    est_gesamt = berechne_est_de(gesamt_einkommen, tarif)
    steuer_ohne_dba = est_gesamt.einkommensteuer

    # Höchstbetrag §34c Abs. 1 EStG
    if gesamt_einkommen > 0:
        hoechstbetrag = steuer_ohne_dba * (auslaendische_einkuenfte / gesamt_einkommen)
    else:
        hoechstbetrag = 0.0

    anrechnung = min(auslaendische_steuer, hoechstbetrag)
    steuer_mit_dba = steuer_ohne_dba - anrechnung

    return DBAErgebnis(
        methode=DBAMethode.ANRECHNUNG,
        inlaendische_einkuenfte=gesamt_einkommen - auslaendische_einkuenfte,
        auslaendische_einkuenfte=auslaendische_einkuenfte,
        steuer_ohne_dba=round(steuer_ohne_dba, 2),
        steuer_mit_dba=round(steuer_mit_dba, 2),
        entlastung=round(anrechnung, 2),
        erklaerung=(
            f"Anrechnung: {anrechnung:.2f} € "
            f"(Höchstbetrag: {hoechstbetrag:.2f} €, "
            f"gezahlte ausl. Steuer: {auslaendische_steuer:.2f} €)"
        ),
    )


def berechne_freistellung_mit_progressionsvorbehalt(
    inlaendische_einkuenfte: float,
    freigestellte_einkuenfte: float,
    tarif: Tarif = Tarif.GRUND,
) -> DBAErgebnis:
    """
    Freistellungsmethode mit Progressionsvorbehalt.
    Freigestellte Einkünfte werden nicht besteuert,
    aber der Steuersatz wird auf Basis des Gesamteinkommens berechnet.
    """
    gesamt = inlaendische_einkuenfte + freigestellte_einkuenfte
    fn = _est_splittingtarif_2025 if tarif == Tarif.SPLITTING else _est_grundtarif_2025

    # Steuersatz auf Gesamteinkommen
    est_gesamt = fn(gesamt)
    if gesamt > 0:
        steuersatz_gesamt = est_gesamt / gesamt
    else:
        steuersatz_gesamt = 0.0

    # Steuer nur auf inländische Einkünfte, aber mit erhöhtem Steuersatz
    steuer_mit_dba = round(inlaendische_einkuenfte * steuersatz_gesamt, 2)

    # Vergleich: Steuer ohne DBA (alles in DE besteuert)
    steuer_ohne_dba = round(fn(gesamt), 2)

    entlastung = round(steuer_ohne_dba - steuer_mit_dba, 2)

    return DBAErgebnis(
        methode=DBAMethode.FREISTELLUNG,
        inlaendische_einkuenfte=inlaendische_einkuenfte,
        auslaendische_einkuenfte=freigestellte_einkuenfte,
        steuer_ohne_dba=steuer_ohne_dba,
        steuer_mit_dba=steuer_mit_dba,
        entlastung=entlastung,
        erklaerung=(
            f"Freistellung mit Progressionsvorbehalt: "
            f"Steuersatz {steuersatz_gesamt*100:.2f}% "
            f"(berechnet auf Gesamteinkommen {gesamt:.2f} €), "
            f"angewandt auf inländ. Einkünfte {inlaendische_einkuenfte:.2f} €"
        ),
    )


# --- CLI-Modus ---

if __name__ == "__main__":
    print("=== Steuerrechner DE 2025 ===")
    for einkommen in [30_000, 60_000, 100_000, 200_000, 500_000]:
        erg = berechne_est_de(einkommen, kirchensteuer_satz=0.09)
        print(
            f"  zvE {einkommen:>10,.0f} € → "
            f"ESt {erg.einkommensteuer:>10,.2f} € | "
            f"Soli {erg.solidaritaetszuschlag:>7,.2f} € | "
            f"KiSt {erg.kirchensteuer:>7,.2f} € | "
            f"Gesamt {erg.gesamt_belastung:>10,.2f} € | "
            f"Grenz {erg.grenzsteuersatz:.1f}%"
        )

    print("\n=== Gelir Vergisi TR 2024 ===")
    for einkommen in [200_000, 500_000, 1_000_000, 5_000_000]:
        erg = berechne_gelir_vergisi(einkommen)
        print(
            f"  {einkommen:>12,.0f} ₺ → "
            f"Steuer {erg['steuer_try']:>12,.2f} ₺ | "
            f"Effektiv {erg['effektiv_prozent']:.1f}%"
        )

    print("\n=== DBA Anrechnung ===")
    dba = berechne_anrechnung(80_000, 30_000, 5_000)
    print(f"  {dba.erklaerung}")
    print(f"  Steuer ohne DBA: {dba.steuer_ohne_dba:,.2f} € → mit DBA: {dba.steuer_mit_dba:,.2f} €")

    print("\n=== DBA Freistellung mit Progressionsvorbehalt ===")
    dba2 = berechne_freistellung_mit_progressionsvorbehalt(50_000, 30_000)
    print(f"  {dba2.erklaerung}")
    print(f"  Steuer ohne DBA: {dba2.steuer_ohne_dba:,.2f} € → mit DBA: {dba2.steuer_mit_dba:,.2f} €")
