"""
Fristen-Manager – Steuerliche Fristen und Termine verwalten.

Features:
- Alle relevanten Steuerfristen DE (ESt, KSt, USt, GewSt, Lohnsteuer)
- Fristverlängerung bei Steuerberater-Mandaten
- Warnungen vor ablaufenden Fristen
- Feiertagsberücksichtigung (Verschiebung auf nächsten Werktag)
- iCal-Export für Kalenderintegration
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Optional


class Steuerart(Enum):
    EST = "Einkommensteuer"
    KIST = "Kirchensteuer"
    KST = "Körperschaftsteuer"
    GEWST = "Gewerbesteuer"
    UST = "Umsatzsteuer"
    LST = "Lohnsteuer"
    EUST = "Einfuhrumsatzsteuer"
    KFZST = "Kraftfahrzeugsteuer"


class FristTyp(Enum):
    ERKLAERUNG = "Steuererklärung"
    VORANMELDUNG = "Voranmeldung"
    VORAUSZAHLUNG = "Vorauszahlung"
    ZAHLUNG = "Zahlung"
    EINSPRUCH = "Einspruch"
    MELDUNG = "Meldung"


class Dringlichkeit(Enum):
    KRITISCH = "kritisch"       # < 3 Tage
    DRINGEND = "dringend"       # < 7 Tage
    BALD = "bald"               # < 14 Tage
    NORMAL = "normal"           # < 30 Tage
    ENTSPANNT = "entspannt"     # > 30 Tage


@dataclass
class Frist:
    steuerart: Steuerart
    typ: FristTyp
    faellig: date
    beschreibung: str
    mandant: Optional[str] = None
    erledigt: bool = False
    notizen: str = ""


@dataclass
class FristWarnung:
    frist: Frist
    dringlichkeit: Dringlichkeit
    tage_verbleibend: int
    hinweis: str


# --- Deutsche Feiertage (bundesweit) ---

def _bundesweite_feiertage(jahr: int) -> set[date]:
    """Berechnet bundesweite Feiertage für ein Jahr inkl. Osterdatum."""
    feiertage = {
        date(jahr, 1, 1),     # Neujahr
        date(jahr, 5, 1),     # Tag der Arbeit
        date(jahr, 10, 3),    # Tag der Deutschen Einheit
        date(jahr, 12, 25),   # 1. Weihnachtstag
        date(jahr, 12, 26),   # 2. Weihnachtstag
    }

    # Ostersonntag nach Gauß'scher Osterformel
    a = jahr % 19
    b = jahr // 100
    c = jahr % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    monat = (h + l - 7 * m + 114) // 31
    tag = ((h + l - 7 * m + 114) % 31) + 1
    ostern = date(jahr, monat, tag)

    feiertage.add(ostern - timedelta(days=2))   # Karfreitag
    feiertage.add(ostern + timedelta(days=1))   # Ostermontag
    feiertage.add(ostern + timedelta(days=39))  # Christi Himmelfahrt
    feiertage.add(ostern + timedelta(days=50))  # Pfingstmontag

    return feiertage


def naechster_werktag(datum: date) -> date:
    """Verschiebt auf nächsten Werktag falls Wochenende/Feiertag."""
    feiertage = _bundesweite_feiertage(datum.year)
    while datum.weekday() >= 5 or datum in feiertage:
        datum += timedelta(days=1)
        if datum.year != datum.year:
            feiertage = _bundesweite_feiertage(datum.year)
    return datum


# --- Standardfristen generieren ---

def ust_voranmeldungen(jahr: int, monatlich: bool = True) -> list[Frist]:
    """USt-Voranmeldungen: 10. des Folgemonats (oder Quartal)."""
    fristen = []
    monate = range(1, 13) if monatlich else [3, 6, 9, 12]

    for monat in monate:
        folgemonat = monat + 1
        folgejahr = jahr
        if folgemonat > 12:
            folgemonat = 1
            folgejahr = jahr + 1

        faellig = naechster_werktag(date(folgejahr, folgemonat, 10))
        zeitraum = f"{monat:02d}/{jahr}" if monatlich else f"Q{monat//3}/{jahr}"

        fristen.append(Frist(
            steuerart=Steuerart.UST,
            typ=FristTyp.VORANMELDUNG,
            faellig=faellig,
            beschreibung=f"USt-Voranmeldung {zeitraum}",
        ))
    return fristen


def lohnsteuer_anmeldungen(jahr: int) -> list[Frist]:
    """Lohnsteuer-Anmeldungen: 10. des Folgemonats."""
    fristen = []
    for monat in range(1, 13):
        folgemonat = monat + 1
        folgejahr = jahr
        if folgemonat > 12:
            folgemonat = 1
            folgejahr = jahr + 1

        faellig = naechster_werktag(date(folgejahr, folgemonat, 10))
        fristen.append(Frist(
            steuerart=Steuerart.LST,
            typ=FristTyp.VORANMELDUNG,
            faellig=faellig,
            beschreibung=f"Lohnsteuer-Anmeldung {monat:02d}/{jahr}",
        ))
    return fristen


def est_vorauszahlungen(jahr: int) -> list[Frist]:
    """ESt-Vorauszahlungen: 10.03., 10.06., 10.09., 10.12."""
    termine = [
        (3, 10, "Q1"),
        (6, 10, "Q2"),
        (9, 10, "Q3"),
        (12, 10, "Q4"),
    ]
    return [
        Frist(
            steuerart=Steuerart.EST,
            typ=FristTyp.VORAUSZAHLUNG,
            faellig=naechster_werktag(date(jahr, m, t)),
            beschreibung=f"ESt-Vorauszahlung {q} {jahr}",
        )
        for m, t, q in termine
    ]


def jahreserklaerungen(
    jahr: int,
    steuerberater: bool = False,
) -> list[Frist]:
    """
    Abgabefristen für Jahressteuererklärungen.
    Ohne StB: 31.07. des Folgejahres
    Mit StB:  28.02. des übernächsten Jahres (verlängerte Frist)
    """
    if steuerberater:
        faellig_datum = date(jahr + 2, 2, 28)
    else:
        faellig_datum = date(jahr + 1, 7, 31)

    faellig_datum = naechster_werktag(faellig_datum)

    erklaerungen = [
        (Steuerart.EST, "Einkommensteuererklärung"),
        (Steuerart.UST, "Umsatzsteuererklärung"),
        (Steuerart.GEWST, "Gewerbesteuererklärung"),
        (Steuerart.KST, "Körperschaftsteuererklärung"),
    ]

    return [
        Frist(
            steuerart=sa,
            typ=FristTyp.ERKLAERUNG,
            faellig=faellig_datum,
            beschreibung=f"{beschr} {jahr}",
        )
        for sa, beschr in erklaerungen
    ]


def einspruchsfrist(bescheiddatum: date) -> Frist:
    """Einspruchsfrist: 1 Monat nach Bekanntgabe (+ 3 Tage Zugangsfiktion)."""
    bekanntgabe = bescheiddatum + timedelta(days=3)

    # 1 Monat nach Bekanntgabe
    monat = bekanntgabe.month + 1
    jahr = bekanntgabe.year
    if monat > 12:
        monat = 1
        jahr += 1

    # Tag beibehalten, ggf. auf letzten Tag des Monats kürzen
    tag = min(bekanntgabe.day, 28)  # Sicherheitshalber
    frist_ende = naechster_werktag(date(jahr, monat, tag))

    return Frist(
        steuerart=Steuerart.EST,
        typ=FristTyp.EINSPRUCH,
        faellig=frist_ende,
        beschreibung=f"Einspruchsfrist (Bescheid vom {bescheiddatum.isoformat()})",
    )


# --- Warnungen ---

def pruefe_fristen(
    fristen: list[Frist],
    stichtag: Optional[date] = None,
) -> list[FristWarnung]:
    """Prüft alle Fristen und gibt Warnungen nach Dringlichkeit."""
    if stichtag is None:
        stichtag = date.today()

    warnungen = []
    for frist in fristen:
        if frist.erledigt:
            continue

        tage = (frist.faellig - stichtag).days

        if tage < 0:
            dringlichkeit = Dringlichkeit.KRITISCH
            hinweis = f"ÜBERFÄLLIG seit {abs(tage)} Tag(en)!"
        elif tage <= 3:
            dringlichkeit = Dringlichkeit.KRITISCH
            hinweis = f"Nur noch {tage} Tag(e)!"
        elif tage <= 7:
            dringlichkeit = Dringlichkeit.DRINGEND
            hinweis = f"Noch {tage} Tage – bitte zeitnah erledigen."
        elif tage <= 14:
            dringlichkeit = Dringlichkeit.BALD
            hinweis = f"Noch {tage} Tage."
        elif tage <= 30:
            dringlichkeit = Dringlichkeit.NORMAL
            hinweis = f"Fällig in {tage} Tagen."
        else:
            dringlichkeit = Dringlichkeit.ENTSPANNT
            hinweis = f"Fällig in {tage} Tagen – kein Handlungsbedarf."

        warnungen.append(FristWarnung(
            frist=frist,
            dringlichkeit=dringlichkeit,
            tage_verbleibend=tage,
            hinweis=hinweis,
        ))

    # Sortiert nach Dringlichkeit (kritischste zuerst)
    prio = {
        Dringlichkeit.KRITISCH: 0,
        Dringlichkeit.DRINGEND: 1,
        Dringlichkeit.BALD: 2,
        Dringlichkeit.NORMAL: 3,
        Dringlichkeit.ENTSPANNT: 4,
    }
    warnungen.sort(key=lambda w: (prio[w.dringlichkeit], w.tage_verbleibend))
    return warnungen


# --- iCal-Export ---

def exportiere_ical(fristen: list[Frist]) -> str:
    """Exportiert Fristen als iCal-Datei (.ics)."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Tekin Steuerberater-Toolkit//Fristen//DE",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for i, frist in enumerate(fristen):
        uid = f"frist-{i}-{frist.faellig.isoformat()}@tekin-toolkit"
        datum_str = frist.faellig.strftime("%Y%m%d")

        summary = frist.beschreibung
        if frist.mandant:
            summary = f"[{frist.mandant}] {summary}"

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTART;VALUE=DATE:{datum_str}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{frist.typ.value} - {frist.steuerart.value}",
            "BEGIN:VALARM",
            "TRIGGER:-P3D",
            "ACTION:DISPLAY",
            "DESCRIPTION:Steuerliche Frist in 3 Tagen!",
            "END:VALARM",
            "BEGIN:VALARM",
            "TRIGGER:-P1D",
            "ACTION:DISPLAY",
            "DESCRIPTION:Steuerliche Frist MORGEN!",
            "END:VALARM",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


# --- CLI-Modus ---

if __name__ == "__main__":
    from datetime import date as d

    jahr = 2025

    print(f"=== Steuerliche Fristen {jahr} ===\n")

    alle_fristen = []
    alle_fristen.extend(ust_voranmeldungen(jahr))
    alle_fristen.extend(lohnsteuer_anmeldungen(jahr))
    alle_fristen.extend(est_vorauszahlungen(jahr))
    alle_fristen.extend(jahreserklaerungen(jahr - 1, steuerberater=True))

    warnungen = pruefe_fristen(alle_fristen)

    for w in warnungen[:10]:
        symbol = {
            Dringlichkeit.KRITISCH: "[!!!]",
            Dringlichkeit.DRINGEND: "[!! ]",
            Dringlichkeit.BALD: "[!  ]",
            Dringlichkeit.NORMAL: "[   ]",
            Dringlichkeit.ENTSPANNT: "[   ]",
        }[w.dringlichkeit]

        print(
            f"  {symbol} {w.frist.faellig.isoformat()} | "
            f"{w.frist.beschreibung:<45} | {w.hinweis}"
        )

    print(f"\n  ... und {len(warnungen) - 10} weitere Fristen")

    print("\n=== Einspruchsfrist ===")
    ef = einspruchsfrist(d(2025, 3, 15))
    print(f"  Bescheid vom 15.03.2025 → Einspruch bis {ef.faellig.isoformat()}")
