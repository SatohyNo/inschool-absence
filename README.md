# inschool-absence

A small read-only command-line tool for students in Norwegian upper secondary school (videregående) whose school uses
**Visma InSchool**. For every subject it shows:

- the subject's yearly hours (*årstimer*),
- your absence so far, in percent (the same number as on the *Fravær* page in InSchool),
- how many **whole double lessons** you can still skip this school year without going over the 10% absence limit
  (*fraværsgrensen*).

Example output (made-up numbers):

```
Absence, school year 2026/27 — 28.10.2026 18:00

Subject           Hours/year  Now    Double lessons left
Norsk             113 h       9.29%  0                    ⚠️ no more
Naturfag          140 h       8.04%  1
Engelsk           140 h       6.43%  3
Kroppsøving       56 h        0.00%  3
Samfunnskunnskap  84 h        3.57%  3
Matematikk 1P     140 h       1.07%  8

Limit: 10% of the subject's yearly hours (årstimer), settled once at the end of the school year.
Double lesson = 2 × 45 min; only whole double lessons are counted.
Data comes from InSchool: an absence shows up once the teacher has registered it.
```

## Requirements

- Python 3.9+ (standard library only)
- Node.js 22+ and Google Chrome, for the one-time login

## Usage

1. Log in once (and again whenever the session expires):

   ```
   node login.mjs <your-school>.inschool.visma.no [start-url]
   ```

   A separate Chrome window opens. Log in the way you normally do (for example with Feide) and open InSchool.
   The window closes by itself once InSchool answers. If the plain InSchool address doesn't lead you to the login, pass
   your school's portal page as `start-url`.

2. Run the calculator:

   ```
   python3 absence.py
   ```

Environment variables (all optional):

| Variable           | Meaning                                                    |
|--------------------|------------------------------------------------------------|
| `INSCHOOL_SESSION` | session file (default `~/.visma-inschool-session.json`)    |
| `INSCHOOL_HOST`    | InSchool host, if you don't want it read from the session  |
| `CHROME_PATH`      | Chrome executable for `login.mjs` (default: macOS location) |

## How it is calculated

Since 1 August 2025 absence is settled **once, at the end of the school year**, instead of twice a year
([regjeringen.no, 21.11.2024](https://www.regjeringen.no/no/aktuelt/kunnskapsministeren-endrer-fravarsreglene-i-videregaende-skole/id3075576/)).
The limit is 10% of the subject's yearly hours
([opplæringsforskrifta § 9-8](https://udir.no/regelverkstolkninger/opplaring/forskrift-om-grunnskoleopplaringa-og-den-vidaregaande-opplaringa-opplaringsforskrifta/tredje-delen--fellesreglar-for-grunnskoleopplaringa-og-den-vidaregaande-opplaringa-for-barn-og-unge/kapittel-9-individuell-vurdering/i.-generelle-reglar/-9-8-fravarsgrense-i-vidaregaande-skole)).
There is no separate limit per half-year, and nothing resets after New Year.

For each subject:

```
hours left           = 10% × yearly hours − hours absent this school year
double lessons left  = floor(hours left / length of a double lesson)
```

- *Yearly hours* and *hours absent* come from InSchool's attendance data (`yearlyHours`, `totalAbsence`).
- InSchool counts absence in 60-minute hours, so a 45-minute lesson is 0.75 h and a double lesson is 1.5 h.
  The length of a double lesson is taken from your timetable for this and next week.
- "More than 10%" is over the limit, so reaching exactly 10% is still allowed.
- Documented absence (doctor, funeral, driving test, etc.) does not count toward the limit once the school has
  accepted the documentation. In special cases the principal may still give a grade at up to 15%, but that is an
  exception, not a right.

The rules and how your school applies them can change, so check with your school if you are close to the limit.

## Privacy

- `login.mjs` never sees your password: you type it into the browser yourself.
- Only InSchool's session cookies are saved, in `~/.visma-inschool-session.json` with mode 600. The file is outside
  the repository; never commit it.
- `absence.py` only sends GET requests to your school's InSchool host and changes nothing.

## Disclaimer

Unofficial tool, not affiliated with Visma, Udir or any school. It reads the same data the InSchool web app shows you.
The numbers are guidance; your school's decision is what counts.

## License

[MIT](LICENSE)
