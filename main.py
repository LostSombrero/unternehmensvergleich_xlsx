"""
main.py  –  Unternehmens-Vergleich  (Excel-Listen ⇨ Ranking nach Häufigkeit + Online-Reputation)

• liest 2–4 Excel-Dateien ein
• Spaltennamen für Rating / Reviewcount flexibel:  („Google Bewertung“, „Bewertung“, „Trustpilot Rating“, …)
• mehrere Quellen ⇒ review-gewichteter Durchschnitt
• alle Parameter (ALPHA, BETA, LOG_BASE, FALLBACK_SCORE, MIN_REVIEW_COUNT) stehen in config.csv
"""

import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import filedialog, simpledialog
import os, re, csv, pathlib
from urllib.parse import urlparse

# ──────────────────────────────────────────────────────────────────────────────
# 1) Parameter aus config.csv laden  ───────────────────────────────────────────
# ──────────────────────────────────────────────────────────────────────────────
DEFAULTS = {
    "ALPHA": 10,
    "BETA": 0.5,
    "LOG_BASE": 10,
    "FALLBACK_SCORE": 0,
    "MIN_REVIEW_COUNT": 0,
    "SHOW_PLOTS": 1,
}
cfg_path = pathlib.Path(__file__).with_name("config.csv")
if cfg_path.exists():
    with cfg_path.open(newline="") as f:
        reader = csv.DictReader(f)
        DEFAULTS.update({row["key"]: float(row["value"]) for row in reader})
else:
    print("⚠️  config.csv nicht gefunden – Standardwerte werden genutzt")

ALPHA          = DEFAULTS["ALPHA"]
BETA           = DEFAULTS["BETA"]
LOG_BASE       = DEFAULTS["LOG_BASE"]
FALLBACK_SCORE = DEFAULTS["FALLBACK_SCORE"]
MIN_REVIEWS    = DEFAULTS["MIN_REVIEW_COUNT"]
SHOW_PLOTS = bool(DEFAULTS["SHOW_PLOTS"])

# --------------------------------------------------
# Importiere matplotlib nur bei Bedarf
# --------------------------------------------------
if SHOW_PLOTS:
    import matplotlib.pyplot as plt

# ──────────────────────────────────────────────────────────────────────────────
# 2) flexible Spalten­kandidaten für Ratings & Counts  ──────────────────────────
# ──────────────────────────────────────────────────────────────────────────────
RATING_COLS = ["Google Bewertung", "Bewertung", "Trustpilot Rating", "Rating"]
COUNT_COLS  = ["Anzahl Bewertungen", "Review Count", "Bewertungen", "Reviews"]

def first_match(candidates, columns):
    """gibt den ersten Kandidaten zurück, der in columns vorkommt"""
    return next((c for c in candidates if c in columns), None)

# ──────────────────────────────────────────────────────────────────────────────
# 3) Hilfsfunktionen  ──────────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────────────────────
def extract_main_domain(url: str) -> str:
    """Domain ohne www, Pfad, Query – funktioniert auch ohne http://"""
    if pd.isna(url) or not str(url).strip():
        return ""
    url = str(url).strip()
    if "://" not in url:
        url = "//" + url
    parsed = urlparse(url)
    netloc = parsed.netloc or parsed.path
    netloc = netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc

def parse_rating(val) -> float:
    if pd.isna(val):
        return np.nan
    m = re.search(r"(\d+[.,]?\d*)", str(val))
    return float(m.group(1).replace(",", ".")) if m else np.nan

def parse_count(val) -> float:
    if pd.isna(val):
        return np.nan
    digits = re.sub(r"[^\d]", "", str(val))
    return float(digits) if digits else np.nan

def review_score(rating, reviews) -> float:
    """
    Bewertungs-Score:
        • wenn rating fehlt ODER reviews < MIN_REVIEWS  → FALLBACK_SCORE
        • sonst: rating * (1 + log_base(1 + reviews))
    """
    if np.isnan(rating) or reviews < MIN_REVIEWS:
        return FALLBACK_SCORE
    log_part = np.log1p(reviews) / np.log(LOG_BASE)
    return rating * (1 + log_part)

# ──────────────────────────────────────────────────────────────────────────────
# 4) Excel-Dateien wählen  ─────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────────────────────
root = tk.Tk(); root.withdraw()
file_paths = filedialog.askopenfilenames(
    title="Wähle 2–4 Excel-Dateien aus",
    filetypes=[("Excel-Dateien", "*.xlsx *.xls")]
)
if not (2 <= len(file_paths) <= 4):
    raise ValueError("Bitte genau 2–4 Dateien auswählen.")

file_labels = [f"Datei {i+1}" for i in range(len(file_paths))]
frames = []

# ──────────────────────────────────────────────────────────────────────────────
# 5) Einlesen & Normalisieren  ────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────────────────────
for lbl, path in zip(file_labels, file_paths):
    df = pd.read_excel(path)
    df.columns = df.columns.str.strip()

    # passende Rating/Count-Spalten suchen
    r_col = first_match(RATING_COLS, df.columns)
    c_col = first_match(COUNT_COLS,  df.columns)

    if r_col:
        df[r_col] = df[r_col].apply(parse_rating)
        df.rename(columns={r_col: "Rating"}, inplace=True)
    else:
        df["Rating"] = np.nan

    if c_col:
        df[c_col] = df[c_col].apply(parse_count)
        df.rename(columns={c_col: "Reviews"}, inplace=True)
    else:
        df["Reviews"] = np.nan

    df["Quelle"] = lbl
    frames.append(df)

combined = pd.concat(frames, ignore_index=True)
combined["Domain"] = combined["Webseite"].apply(extract_main_domain)

# das Produkt Rating*Reviews für die gruppierte Summe
combined["RatingTimesReviews"] = combined["Rating"] * combined["Reviews"]

# ──────────────────────────────────────────────────────────────────────────────
# 6) Gewichte pro Datei per GUI abfragen  ─────────────────────────────────────
# ──────────────────────────────────────────────────────────────────────────────
weights = {}
for lbl, path in zip(file_labels, file_paths):
    default = 1.0
    ans = simpledialog.askfloat(
        "Gewicht festlegen",
        f"Gewicht für\n{os.path.basename(path)} ({lbl})\n(Standard = 1):",
        minvalue=0.0
    )
    weights[lbl] = ans if ans is not None else default

# ──────────────────────────────────────────────────────────────────────────────
# 7) Gruppieren & Aggregieren  ────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────────────────────
agg = combined.groupby("Domain", dropna=False).agg(
    Webseite         = ("Webseite", "first"),
    Telefonnummer    = ("Telefonnummer", "first"),
    Adresse          = ("Adresse", "first"),
    Unternehmen      = ("Unternehmen", lambda x: list(pd.unique(x.dropna().astype(str)))),
    Quelle           = ("Quelle", list),
    Total_Reviews    = ("Reviews", "sum"),
    Sum_RxR          = ("RatingTimesReviews", "sum")
).reset_index()

# gewichteter Durchschnitt
agg["Durchschn_Rating"] = agg["Sum_RxR"] / agg["Total_Reviews"]
agg.loc[agg["Total_Reviews"] == 0, "Durchschn_Rating"] = np.nan

# Firmennamen-Flag
agg["Firmennamen abweichend"] = agg["Unternehmen"].apply(lambda l: "Ja" if len(l) > 1 else "Nein")
agg["Unternehmen"] = agg["Unternehmen"].apply(lambda l: ", ".join(l))

# Datei-Indikatoren + Häufigkeits-Score
for lbl in file_labels:
    agg[lbl] = agg["Quelle"].apply(lambda lst: int(lbl in lst))
agg["Häufigkeits-Score"] = sum(agg[lbl] * weights[lbl] for lbl in file_labels)

# ──────────────────────────────────────────────────────────────────────────────
# 8) Bewertungs- und Gesamt-Score  ────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────────────────────
agg["Bewertungs-Score"] = agg.apply(
    lambda r: review_score(r["Durchschn_Rating"], r["Total_Reviews"]),
    axis=1
)
agg["Gesamt-Score"] = ALPHA * agg["Häufigkeits-Score"] + BETA * agg["Bewertungs-Score"]

agg.drop(columns=["Quelle", "Sum_RxR"], inplace=True)
agg.sort_values("Gesamt-Score", ascending=False, inplace=True)

# ──────────────────────────────────────────────────────────────────────────────
# 9) Export  ──────────────────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────────────────────
out_path = os.path.join(
    os.path.dirname(file_paths[0]),
    "unternehmensvergleich_ergebnis.xlsx"
)
agg.to_excel(out_path, index=False)
print(f"\n✅ Vergleich abgeschlossen.\nDatei gespeichert unter:\n{out_path}")

# ────────────────────────────────────────────────────────────────
# 10) Scatter-Plots  (optional)
# ────────────────────────────────────────────────────────────────
if SHOW_PLOTS:
    size = np.clip(agg["Total_Reviews"], 10, 1000)   # Markergröße
    plt.figure()
    plt.scatter(agg["Häufigkeits-Score"], agg["Gesamt-Score"], s=size/5, alpha=0.7)
    plt.xlabel("Häufigkeits-Score (HS)")
    plt.ylabel("Gesamt-Score (GS)")
    plt.title("HS vs. GS")
    plt.grid(True, linestyle="--", linewidth=0.5, alpha=0.3)

    plt.figure()
    plt.scatter(agg["Bewertungs-Score"], agg["Gesamt-Score"], s=size/5, alpha=0.7)
    plt.xlabel("Bewertungs-Score (BS)")
    plt.ylabel("Gesamt-Score (GS)")
    plt.title("BS vs. GS")
    plt.grid(True, linestyle="--", linewidth=0.5, alpha=0.3)

    plt.show()
