# TODO Archive

Erledigte Punkte aus `docs/TODO.md` (Historie, kein Nachschlagewerk für die
laufende Aufgabe — siehe `oe5ith-coding-rules/AGENT_INSTRUCTIONS.md` §3).

## `datetime.utcnow()` DeprecationWarning in generate_manifest.py

*Erledigt: 2026-08-11 (Commit `fix(manifest): replace deprecated
datetime.utcnow() with timezone-aware call`)*

`scripts/generate_manifest.py:90` nutzte `datetime.utcnow()` für `generated_at`
im Manifest — unter aktuellem Python 3 (3.13, siehe `.venv`) als deprecated
markiert, geplante Entfernung in künftiger Version:

```
scripts/generate_manifest.py:90: DeprecationWarning: datetime.datetime.utcnow() is deprecated
and scheduled for removal in a future version. Use timezone-aware objects to represent
datetimes in UTC: datetime.datetime.now(datetime.UTC).
```

Fix: `timezone.utc` (Python 3.2+, kompatibler als `datetime.UTC` ab 3.11)
statt `datetime.utcnow()`. Beim Restrukturierungs-Build (2026-08-11,
`update.sh`/`run.sh`-Einführung) entdeckt, außerhalb des dortigen Scopes,
daher zunächst nur dokumentiert statt mitgefixt — dann als eigener
Mini-Zyklus (D) im Zuge der TODO-Abarbeitung umgesetzt.
