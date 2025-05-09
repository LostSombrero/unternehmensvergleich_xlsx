# Unternehmens‑Vergleich

Dieses Projekt vergleicht bis zu **vier Excel‑Dateien** mit Firmenlisten und erstellt daraus ein Ranking.

* **Häufigkeit**: Wie oft (und in welchen, von dir gewichteten) Listen taucht das Unternehmen auf?
* **Online‑Reputation**: Ø‑Rating × Review‑Anzahl – Quellen können Google, Trustpilot … sein.
* Ergebnis: `unternehmensvergleich_ergebnis.xlsx` **plus** zwei Diagnose‑Plots.

---

## 1  Installation

```bash
python -m venv .venv && source .venv/bin/activate  # optional
pip install -r requirements.txt                    # pandas, numpy, openpyxl, matplotlib
```

`tkinter` ist in Standard‑Python bereits enthalten.

---

## 2  Eingabedateien

Mindestens **eine Website‑Spalte** ist Pflicht.  Groß/Klein wird ignoriert.

| Zweck                 | Akzeptierte Spaltennamen                                       |
| --------------------- | -------------------------------------------------------------- |
| **Website** (Pflicht) | `Webseite`, `Website`, `URL`                                   |
| Unternehmensname      | `Unternehmen`, `Firma`                                         |
| Telefon               | `Telefonnummer`, `Telefon`                                     |
| Adresse               | `Adresse`, `Address`                                           |
| **Rating**            | `Google Bewertung`, `Bewertung`, `Trustpilot Rating`, `Rating` |
| **Review‑Anzahl**     | `Anzahl Bewertungen`, `Review Count`, `Bewertungen`, `Reviews` |

Fehlen Rating/Reviews komplett ⇒ Firma erhält den Fallback‑Score.

---

## 3  Konfiguration (`config.csv`)

```csv
key,value
ALPHA,10            # Gewicht Häufigkeit
BETA,0.5            # Gewicht Bewertung
LOG_BASE,10         # Basis von log_b(1+Reviews)
FALLBACK_SCORE,0    # Score ohne Rating
MIN_REVIEW_COUNT,0  # Mindest‑Reviews, sonst Fallback
SHOW_PLOTS,1        # 0 = Plots unterdrücken
```

Werte ändern → Skript neu starten – kein Code‑Edit nötig.

---

## 4  Formeln

**### 1 Domain‑Matching**

\`\`\`

[https://www.beispiel.de/shop](https://www.beispiel.de/shop)  →  beispiel.de

\`\`\`

\`[www.\`‑Präfix](http://www.`‑Präfix) & Pfad werden entfernt; Sub‑Domains wie *\*shop.\** bleiben bestehen.

**### 2 Häufigkeits‑Score (HS)**

\$\$

HS = \sum\_{i=1}^{n} w\_i\\,I\_i

\$\$

\* *\*n\** – Zahl der eingelesenen Dateien (2 – 4)

\* *\*wᵢ\** – Gewicht Datei *\*i\** (GUI, Default 1)

\* *\*Iᵢ\** – 1, wenn Firma in Datei *\*i\** vorkommt, sonst 0\\

**### 3 Bewertungs‑Score (BS)**

Zuerst über alle Dateien ein **\*\*Review‑gewichteter Durchschnitt\*\***:

\$\$

R\_{mix}=\frac{\sum R\_i v\_i}{\sum v\_i},\qquad v\_{mix}=\sum v\_i

\$\$

Danach:

\$\$

BS = \begin{cases}

R\_{mix}\\,\bigl(1+\log\_{b}(1+v\_{mix})\bigr), & v\_{mix} \ge \text{MIN\\\_REVIEW\\\_COUNT}\\\\\[6pt]

\text{FALLBACK\\\_SCORE}, & \text{sonst}

\end{cases}

\$\$

**### 4 Gesamt‑Score (GS)**

\$\$

GS = \alpha\\,HS + \beta\\,BS

\$\$

\* \$\alpha = \text{ALPHA}\$   \$\beta = \text{BETA}\$

\---

## 5  Plots

Wenn `SHOW_PLOTS = 1`, erscheinen zwei Scatter‑Plots direkt nach dem Lauf.

| Plot         | Achsen         | Gute Signatur                         | Problem‑Hinweis                                   |
| ------------ | -------------- | ------------------------------------- | ------------------------------------------------- |
| **HS vs GS** | x = HS, y = GS | Vertikale Stränge (Abstand ≈ `ALPHA`) | Stränge verschmelzen → `ALPHA` zu klein           |
| **BS vs GS** | x = BS, y = GS | Parallele Linien (Steigung ≈ `BETA`)  | Linie zu flach/steil → `BETA`/`LOG_BASE` anpassen |

Markergröße ∝ Review‑Summe – so stechen Firmen mit vielen Bewertungen heraus.

---

## 6  Ausführen

```bash
python main.py
```

1. Dateien wählen (2–4 Excel).
2. Für jede Datei ein Gewicht eingeben (Return = 1).
3. Ergebnis‑Excel erscheint im Ordner der ersten Datei; Plots öffnen sich (falls aktiviert).

---

## 7  Feintuning‑Spickzettel

| Ziel                            | Drehknopf                  | Plot‑Effekt                                  |
| ------------------------------- | -------------------------- | -------------------------------------------- |
| Häufigkeit soll dominieren      | `ALPHA` ↑                  | größerer Abstand der Stränge (HS vs GS)      |
| Reputation soll stärker wirken  | `BETA` ↑ oder `LOG_BASE` ↓ | steilere Stränge (BS vs GS)                  |
| Sehr wenige Reviews igno­rieren | `MIN_REVIEW_COUNT` ↑       | Punkte links unten fallen auf Fallback‑Linie |
| Plots abschalten                | `SHOW_PLOTS = 0`           | keine Plot‑Fenster                           |

---
