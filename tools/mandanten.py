"""
Mandanten-Onboarding & Verwaltung – Checkliste und Validierung.

Features:
- Onboarding-Checkliste für neue Mandanten
- Steuer-ID / USt-IdNr Validierung (Prüfziffer)
- DBA-Relevanzprüfung (international tätige Mandanten)
- Dokumenten-Checkliste nach Mandantentyp
- Risikobewertung für GwG-Pflichten
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class MandantTyp(Enum):
    PRIVATPERSON = "Privatperson"
    EINZELUNTERNEHMER = "Einzelunternehmer"
    FREIBERUFLER = "Freiberufler"
    GMBH = "GmbH"
    UG = "UG (haftungsbeschränkt)"
    GMBH_CO_KG = "GmbH & Co. KG"
    OHG = "OHG"
    KG = "KG"
    AG = "AG"
    VEREIN = "Verein"
    STIFTUNG = "Stiftung"


class Leistung(Enum):
    FIBU = "Finanzbuchhaltung"
    LOHN = "Lohnbuchhaltung"
    JAHRESABSCHLUSS = "Jahresabschluss"
    EST_ERKLAERUNG = "Einkommensteuererklärung"
    KST_ERKLAERUNG = "Körperschaftsteuererklärung"
    UST_ERKLAERUNG = "Umsatzsteuererklärung"
    GEWST_ERKLAERUNG = "Gewerbesteuererklärung"
    BERATUNG = "Steuerberatung"
    DBA_BERATUNG = "DBA-Beratung (international)"
    GRUENDUNG = "Gründungsberatung"
    NACHFOLGE = "Nachfolgeberatung"
    BETRIEBSPRUEFUNG = "Betriebsprüfungsbegleitung"


class RisikoStufe(Enum):
    NIEDRIG = "niedrig"
    MITTEL = "mittel"
    HOCH = "hoch"
    SEHR_HOCH = "sehr hoch"


@dataclass
class ChecklistenPunkt:
    bezeichnung: str
    pflicht: bool
    erledigt: bool = False
    notiz: str = ""
    faellig_bis: Optional[date] = None


@dataclass
class Mandant:
    name: str
    typ: MandantTyp
    steuer_id: Optional[str] = None
    ust_idnr: Optional[str] = None
    steuernummer: Optional[str] = None
    land: str = "DE"
    zweites_land: Optional[str] = None  # Für DBA-Fälle
    leistungen: list[Leistung] = field(default_factory=list)
    onboarding_datum: Optional[date] = None
    checkliste: list[ChecklistenPunkt] = field(default_factory=list)


# --- Validierung ---

def validiere_steuer_id(steuer_id: str) -> dict:
    """
    Validiert deutsche Steuer-Identifikationsnummer (IdNr).
    11 Ziffern, Prüfziffernverfahren nach BMF.
    """
    # Grundformat prüfen
    clean = steuer_id.replace(" ", "").replace("/", "").replace("-", "")

    if not clean.isdigit():
        return {"gueltig": False, "fehler": "Enthält nicht-numerische Zeichen"}

    if len(clean) != 11:
        return {"gueltig": False, "fehler": f"Erwartet 11 Ziffern, erhalten: {len(clean)}"}

    if clean[0] == "0":
        return {"gueltig": False, "fehler": "Erste Ziffer darf nicht 0 sein"}

    # Prüfziffer nach ISO 7064, Mod 11,10
    produkt = 10
    for i in range(10):
        summe = (int(clean[i]) + produkt) % 10
        if summe == 0:
            summe = 10
        produkt = (summe * 2) % 11

    pruefziffer = (11 - produkt) % 10
    if pruefziffer != int(clean[10]):
        return {
            "gueltig": False,
            "fehler": f"Prüfziffer ungültig (erwartet: {pruefziffer}, erhalten: {clean[10]})",
        }

    return {"gueltig": True, "steuer_id": clean}


def validiere_ust_idnr(ust_idnr: str) -> dict:
    """
    Validiert USt-IdNr (Format-Prüfung).
    DE + 9 Ziffern für deutsche USt-IdNr.
    """
    clean = ust_idnr.replace(" ", "").upper()

    if len(clean) < 3:
        return {"gueltig": False, "fehler": "Zu kurz"}

    land = clean[:2]
    nummer = clean[2:]

    formate = {
        "DE": (9, "9 Ziffern"),
        "AT": (9, "U + 8 Ziffern"),
        "TR": (10, "10 Ziffern"),
        "NL": (12, "12 Zeichen"),
        "FR": (11, "11 Zeichen"),
        "IT": (11, "11 Ziffern"),
        "ES": (9, "9 Zeichen"),
        "PL": (10, "10 Ziffern"),
    }

    if land not in formate:
        return {"gueltig": False, "fehler": f"Unbekanntes Länderkennzeichen: {land}"}

    erwartete_laenge, beschreibung = formate[land]

    if land == "DE":
        if not nummer.isdigit() or len(nummer) != erwartete_laenge:
            return {
                "gueltig": False,
                "fehler": f"DE USt-IdNr erfordert {beschreibung}, erhalten: {nummer}",
            }

    return {
        "gueltig": True,
        "land": land,
        "nummer": nummer,
        "formatiert": f"{land}{nummer}",
    }


# --- Onboarding-Checkliste ---

def erstelle_onboarding_checkliste(mandant: Mandant) -> list[ChecklistenPunkt]:
    """Erstellt mandantenspezifische Onboarding-Checkliste."""
    checkliste = []

    # Allgemeine Punkte (alle Mandanten)
    checkliste.extend([
        ChecklistenPunkt("Mandantenvertrag / Vollmacht unterschrieben", pflicht=True),
        ChecklistenPunkt("Personalausweis / Reisepass kopiert (GwG)", pflicht=True),
        ChecklistenPunkt("Stammdaten in Kanzleisoftware erfasst", pflicht=True),
        ChecklistenPunkt("Steuernummer beim Finanzamt verifiziert", pflicht=True),
        ChecklistenPunkt("DATEV-Zugang eingerichtet", pflicht=False),
        ChecklistenPunkt("Kommunikationsweg vereinbart (E-Mail/Portal)", pflicht=True),
    ])

    # Privatperson
    if mandant.typ == MandantTyp.PRIVATPERSON:
        checkliste.extend([
            ChecklistenPunkt("Steuer-ID (IdNr) erfasst", pflicht=True),
            ChecklistenPunkt("Bankverbindung für Erstattungen", pflicht=True),
            ChecklistenPunkt("Vorjahresbescheide angefordert", pflicht=True),
            ChecklistenPunkt("Lohnsteuerbescheinigungen vorhanden", pflicht=False),
        ])

    # Unternehmen / Selbständige
    if mandant.typ in (
        MandantTyp.EINZELUNTERNEHMER, MandantTyp.FREIBERUFLER,
        MandantTyp.GMBH, MandantTyp.UG, MandantTyp.GMBH_CO_KG,
        MandantTyp.OHG, MandantTyp.KG, MandantTyp.AG,
    ):
        checkliste.extend([
            ChecklistenPunkt("Gewerbeanmeldung / Fragebogen zur steuerl. Erfassung", pflicht=True),
            ChecklistenPunkt("USt-IdNr beantragt / vorhanden", pflicht=True),
            ChecklistenPunkt("Kontenrahmen festgelegt (SKR03/SKR04)", pflicht=True),
            ChecklistenPunkt("Bankzugang für automatischen Kontoabruf", pflicht=False),
            ChecklistenPunkt("Vorjahres-Jahresabschluss erhalten", pflicht=True),
        ])

    # Kapitalgesellschaften
    if mandant.typ in (MandantTyp.GMBH, MandantTyp.UG, MandantTyp.AG):
        checkliste.extend([
            ChecklistenPunkt("Handelsregisterauszug aktuell", pflicht=True),
            ChecklistenPunkt("Gesellschaftsvertrag / Satzung erhalten", pflicht=True),
            ChecklistenPunkt("Gesellschafterliste aktuell", pflicht=True),
            ChecklistenPunkt("Geschäftsführervertrag geprüft (vGA-Risiko)", pflicht=True),
            ChecklistenPunkt("Transparenzregister-Eintrag geprüft", pflicht=True),
        ])

    # UG-spezifisch
    if mandant.typ == MandantTyp.UG:
        checkliste.append(
            ChecklistenPunkt("Rücklagenpflicht (25% Gewinn) dokumentiert", pflicht=True)
        )

    # Lohnbuchhaltung
    if Leistung.LOHN in mandant.leistungen:
        checkliste.extend([
            ChecklistenPunkt("Betriebsnummer bei BA vorhanden", pflicht=True),
            ChecklistenPunkt("Personalstammdaten aller Mitarbeiter", pflicht=True),
            ChecklistenPunkt("SV-Meldungen-Zugang (sv.net / ITSG)", pflicht=True),
            ChecklistenPunkt("Arbeitsverträge zur Prüfung erhalten", pflicht=False),
        ])

    # DBA / International
    if mandant.zweites_land or Leistung.DBA_BERATUNG in mandant.leistungen:
        checkliste.extend([
            ChecklistenPunkt(
                f"DBA {mandant.land}-{mandant.zweites_land or '??'} Anwendbarkeit geprüft",
                pflicht=True,
            ),
            ChecklistenPunkt("Ansässigkeitsbescheinigung beantragt", pflicht=True),
            ChecklistenPunkt("183-Tage-Regelung dokumentiert", pflicht=True),
            ChecklistenPunkt("Ausländische Steuerbescheide angefordert", pflicht=True),
        ])

    return checkliste


# --- GwG-Risikobewertung ---

def gwg_risikobewertung(mandant: Mandant) -> dict:
    """
    Vereinfachte Risikobewertung nach GwG (Geldwäschegesetz).
    StB haben nach §2 Abs. 1 Nr. 12 GwG Sorgfaltspflichten.
    """
    score = 0
    faktoren = []

    # Länderrisiko
    hochrisiko_laender = {"TR", "RU", "AE", "CN", "NG", "PK", "IR", "KP", "SY"}
    if mandant.land in hochrisiko_laender or mandant.zweites_land in hochrisiko_laender:
        score += 3
        faktoren.append("Erhöhtes Länderrisiko")

    # Rechtsformrisiko
    if mandant.typ in (MandantTyp.STIFTUNG, MandantTyp.VEREIN):
        score += 2
        faktoren.append("Rechtsform mit erhöhtem Risiko (Stiftung/Verein)")

    # Komplexe Strukturen
    if mandant.typ == MandantTyp.GMBH_CO_KG:
        score += 1
        faktoren.append("Komplexe Gesellschaftsstruktur")

    # Internationale Bezüge
    if mandant.zweites_land:
        score += 1
        faktoren.append("Internationale Geschäftsbeziehungen")

    # Bargeldintensive Branche (vereinfacht)
    if mandant.typ in (MandantTyp.EINZELUNTERNEHMER, MandantTyp.OHG):
        score += 1
        faktoren.append("Potentiell bargeldintensiv")

    # Risikostufe bestimmen
    if score >= 5:
        stufe = RisikoStufe.SEHR_HOCH
        massnahmen = [
            "Verstärkte Sorgfaltspflichten nach §15 GwG",
            "Häufigere Überprüfung der Geschäftsbeziehung",
            "Senior Management muss Aufnahme genehmigen",
            "Herkunft der Vermögenswerte klären",
        ]
    elif score >= 3:
        stufe = RisikoStufe.HOCH
        massnahmen = [
            "Erweiterte Prüfung des wirtschaftlich Berechtigten",
            "Regelmäßige Überprüfung (mind. jährlich)",
            "Dokumentation der Risikobewertung",
        ]
    elif score >= 1:
        stufe = RisikoStufe.MITTEL
        massnahmen = [
            "Standardmäßige Sorgfaltspflichten nach §10 GwG",
            "Überprüfung bei wesentlichen Änderungen",
        ]
    else:
        stufe = RisikoStufe.NIEDRIG
        massnahmen = [
            "Vereinfachte Sorgfaltspflichten nach §14 GwG möglich",
        ]

    return {
        "risikostufe": stufe.value,
        "score": score,
        "faktoren": faktoren,
        "massnahmen": massnahmen,
    }


# --- Mandanten-Übersicht ---

def mandanten_zusammenfassung(mandant: Mandant) -> dict:
    """Erstellt eine Zusammenfassung des Mandanten-Status."""
    checkliste = mandant.checkliste or erstelle_onboarding_checkliste(mandant)

    pflicht_gesamt = sum(1 for p in checkliste if p.pflicht)
    pflicht_erledigt = sum(1 for p in checkliste if p.pflicht and p.erledigt)
    optional_gesamt = sum(1 for p in checkliste if not p.pflicht)
    optional_erledigt = sum(1 for p in checkliste if not p.pflicht and p.erledigt)

    risiko = gwg_risikobewertung(mandant)

    validierungen = {}
    if mandant.steuer_id:
        validierungen["steuer_id"] = validiere_steuer_id(mandant.steuer_id)
    if mandant.ust_idnr:
        validierungen["ust_idnr"] = validiere_ust_idnr(mandant.ust_idnr)

    fortschritt = (pflicht_erledigt / pflicht_gesamt * 100) if pflicht_gesamt > 0 else 100

    return {
        "mandant": mandant.name,
        "typ": mandant.typ.value,
        "onboarding_fortschritt": f"{fortschritt:.0f}%",
        "pflichtaufgaben": f"{pflicht_erledigt}/{pflicht_gesamt}",
        "optionale_aufgaben": f"{optional_erledigt}/{optional_gesamt}",
        "gwg_risiko": risiko,
        "validierungen": validierungen,
        "leistungen": [l.value for l in mandant.leistungen],
        "dba_relevant": mandant.zweites_land is not None,
    }


# --- CLI-Modus ---

if __name__ == "__main__":
    print("=== Mandanten-Onboarding Demo ===\n")

    # Beispiel: Deutsch-türkischer GmbH-Mandant
    mandant = Mandant(
        name="Yılmaz Consulting GmbH",
        typ=MandantTyp.GMBH,
        steuer_id="12345678911",
        ust_idnr="DE123456789",
        land="DE",
        zweites_land="TR",
        leistungen=[
            Leistung.FIBU,
            Leistung.JAHRESABSCHLUSS,
            Leistung.KST_ERKLAERUNG,
            Leistung.DBA_BERATUNG,
            Leistung.LOHN,
        ],
        onboarding_datum=date.today(),
    )

    # Checkliste erstellen
    checkliste = erstelle_onboarding_checkliste(mandant)
    mandant.checkliste = checkliste

    print(f"Mandant: {mandant.name}")
    print(f"Typ: {mandant.typ.value}")
    print(f"DBA-relevant: {mandant.land}-{mandant.zweites_land}")
    print(f"\nOnboarding-Checkliste ({len(checkliste)} Punkte):")

    for punkt in checkliste:
        status = "✓" if punkt.erledigt else "○"
        pflicht = "[P]" if punkt.pflicht else "[O]"
        print(f"  {status} {pflicht} {punkt.bezeichnung}")

    # Validierungen
    print("\n--- Validierungen ---")
    print(f"  Steuer-ID: {validiere_steuer_id(mandant.steuer_id)}")
    print(f"  USt-IdNr:  {validiere_ust_idnr(mandant.ust_idnr)}")

    # GwG-Risiko
    print("\n--- GwG-Risikobewertung ---")
    risiko = gwg_risikobewertung(mandant)
    print(f"  Stufe: {risiko['risikostufe']} (Score: {risiko['score']})")
    for f in risiko["faktoren"]:
        print(f"  - {f}")
    print("  Maßnahmen:")
    for m in risiko["massnahmen"]:
        print(f"    → {m}")
