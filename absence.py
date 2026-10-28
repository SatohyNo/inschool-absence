#!/usr/bin/env python3
"""How many double lessons you can still skip per subject this school year (10% absence limit).

Since 1 Aug 2025 absence in Norwegian upper secondary school is settled once, at the end of the
school year, against the subject's yearly hours (årstimer), see opplæringsforskrifta § 9-8.
There is no separate limit per half-year and nothing resets after New Year.

Usage: python3 absence.py   (log in first: node login.mjs <your-school>.inschool.visma.no)
"""
import collections
import datetime as dt
import math
import statistics
import sys

from inschool import AuthError, get

LIMIT = 0.10            # more than 10% absence in a subject → no grade
DEFAULT_PAIR = 1.5      # double lesson = 2 × 45 min; InSchool counts absence in 60-minute hours

Lesson = collections.namedtuple("Lesson", "code start end hours")


def week(learner, day):
    w = get(f"/control/timetablev2/learner/{learner}/fetch/ALL/0/current"
            f"?forWeek={day:%d/%m/%Y}&extra-info=true&types=LESSON,SUBSTITUTION")
    out = []
    for i in w.get("timetableItems", []):
        if not i.get("subjectCode"):
            continue
        s, e = (dt.datetime.strptime(f"{i['date']} {i[k]}", "%d/%m/%Y %H:%M") for k in ("startTime", "endTime"))
        out.append(Lesson(i["subjectCode"], s, e, (e - s).seconds / 3600))
    return out


def pairs(lessons):
    """Merges back-to-back lessons of the same subject (break ≤ 15 min) into double lessons."""
    out = []
    for l in sorted(lessons, key=lambda l: (l.code, l.start)):
        p = out[-1] if out else None
        if p and p.code == l.code and l.start < p.end:      # the same lesson listed twice (e.g. a substitution)
            continue
        if p and p.code == l.code and l.start - p.end <= dt.timedelta(minutes=15):
            out[-1] = Lesson(l.code, p.start, l.end, p.hours + l.hours)
        else:
            out.append(l)
    return out


def main():
    today = dt.date.today()
    monday = today - dt.timedelta(days=today.weekday())
    try:
        me = get("/control/permissions/user")
        L, Y = me["learnerId"], me["academicYearId"]
        subjects = [s for s in get(f"/control/attendance/subject-groups/learner/{L}/academic-year/{Y}")
                    if s.get("learnerInTeachingGroup", True)]
        lessons = week(L, monday) + week(L, monday + dt.timedelta(weeks=1))   # to learn how long a double lesson is
    except AuthError as e:
        sys.exit(f"!! {e}")

    pair_len = collections.defaultdict(list)
    for p in pairs(lessons):
        pair_len[p.code].append(p.hours)

    rows = []
    for s in subjects:
        hours = s.get("yearlyHours") or s.get("totalScheduledHours")   # årstimer from the curriculum
        if not hours:
            continue
        absent = s["totalAbsence"]
        pair = statistics.mode(pair_len[s["subjectCode"]]) if pair_len[s["subjectCode"]] else DEFAULT_PAIR
        spare = LIMIT * hours - absent                          # hours you can still miss before 10%
        can = math.floor(spare / pair + 1e-9) if spare >= 0 else -1
        note = "❌ already over 10%" if can < 0 else "⚠️ no more" if can == 0 else ""
        name = (s.get("subjectShortName") or s["subjectName"]).split(",")[0].strip()
        rows.append((can, name, f"{hours:g} h", f"{100 * absent / hours:.2f}%", str(max(can, 0)), note))

    start = today.year if today.month >= 8 else today.year - 1
    print(f"Absence, school year {start}/{(start + 1) % 100:02d} — {dt.datetime.now():%d.%m.%Y %H:%M}\n")
    head = ("Subject", "Hours/year", "Now", "Double lessons left", "")
    w = [max(len(r[i + 1]) for r in rows + [(0,) + head]) for i in range(len(head))]
    for r in [(0,) + head] + sorted(rows):
        print("  ".join(c.ljust(w[i]) for i, c in enumerate(r[1:])).rstrip())
    print(f"\nLimit: {LIMIT:.0%} of the subject's yearly hours (årstimer), settled once at the end of the school year."
          "\nDouble lesson = 2 × 45 min; only whole double lessons are counted."
          "\nData comes from InSchool: an absence shows up once the teacher has registered it.")


if __name__ == "__main__":
    main()
