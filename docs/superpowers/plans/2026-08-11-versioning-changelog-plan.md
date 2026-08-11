# Versioning & CHANGELOG.md Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a single-source-of-truth `VERSION` file and a Keep-a-Changelog-formatted `CHANGELOG.md`, cut the first release (`v1.0.0`), and remove a stale hardcoded plugin-standard version reference in `generate_manifest.py`.

**Architecture:** Two new plain files at the repo root (`VERSION`, `CHANGELOG.md`) plus a two-line edit in an existing Python script. Everything lands in one release commit, tagged.

**Tech Stack:** Plain text, Markdown, Python 3 (one log-string edit).

## Global Constraints

Aus `docs/superpowers/specs/2026-08-11-versioning-changelog-design.md`:

- `VERSION`: Repo-Root, Inhalt exakt `1.0.0` (keine trailing Newline-Überraschungen — ein Wort, ein Trailing-Newline ist ok, kein zusätzlicher Whitespace).
- `CHANGELOG.md`: Repo-Root, Keep-a-Changelog-Format, ein Eintrag `## [1.0.0] - 2026-08-11`, `### Added` mit "Initiale versionierte Veröffentlichung." — kein rückwirkender Eintrag pro historischem Commit.
- `scripts/generate_manifest.py:21,36`: hartkodierte `v1.2`-Referenz entfernen, generischer Text ohne Versionsnummer.
- Release-Commit bündelt alle drei Änderungen, danach ein annotierter Tag `v1.0.0` auf genau diesem Commit.
- Kein Push zu `origin`, kein Deploy — beides außerhalb dieses Plans.

---

### Task 1: `VERSION`, `CHANGELOG.md`, `generate_manifest.py`-Fix, Release-Commit + Tag

**Files:**
- Create: `VERSION`
- Create: `CHANGELOG.md`
- Modify: `scripts/generate_manifest.py:21` und `:36`

**Interfaces:** Keine — reine neue Dateien + ein Log-String-Fix, nichts, was andere Skripte konsumieren.

- [ ] **Step 1: `VERSION` anlegen**

Mit dem Write-Tool `VERSION` mit exakt folgendem Inhalt anlegen (ein Wort,
ein abschließender Zeilenumbruch):
```
1.0.0
```

- [ ] **Step 2: `CHANGELOG.md` anlegen**

Mit dem Write-Tool `CHANGELOG.md` mit folgendem Inhalt anlegen:
```markdown
# Changelog

Alle wichtigen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Format basiert auf [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
Versionierung folgt [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-08-11

### Added
- Initiale versionierte Veröffentlichung.
```

- [ ] **Step 3: Stale `v1.2`-Referenz in `generate_manifest.py` entfernen**

Mit dem Edit-Tool `old_string`:
```python
# Quellen (Migriert auf v1.2 Standard)
WORK_DIR = os.path.join(PROJECT_ROOT, "work")
```
ersetzen durch `new_string`:
```python
# Quellen
WORK_DIR = os.path.join(PROJECT_ROOT, "work")
```

Mit dem Edit-Tool `old_string`:
```python
    log_info("Generating Manifest according to Plugin-Standard (v1.2)...")
```
ersetzen durch `new_string`:
```python
    log_info("Generating Manifest according to Plugin-Standard...")
```

- [ ] **Step 4: `VERSION`-Inhalt exakt prüfen**

Run: `cat VERSION && echo "---" && wc -c VERSION`
Expected: `1.0.0` gefolgt von `---`, `wc -c` zeigt `6 VERSION` (5 Zeichen
`1.0.0` + 1 Byte Zeilenumbruch — bei Abweichung Datei erneut mit exaktem
Inhalt schreiben, kein zusätzlicher Whitespace).

- [ ] **Step 5: `generate_manifest.py` läuft weiterhin fehlerfrei, keine `v1.2`-Referenz mehr**

Voraussetzung: `work/openskimap.pmtiles` muss existieren (aus einem
vorherigen `run.sh`/`convert.sh`-Lauf). Falls nicht vorhanden, ist dieser
Schritt trotzdem aussagekräftig über `grep` allein (siehe unten) —
`generate_manifest.py` selbst muss dann nicht zwingend laufen, da dieser
Task keine inhaltliche Pipeline-Änderung vornimmt, nur eine Logzeile.

Run: `grep -n "v1.2\|v1\.2" scripts/generate_manifest.py`
Expected: keine Treffer (leere Ausgabe, Exit-Code 1 von `grep`).

Falls `work/openskimap.pmtiles` vorhanden ist, zusätzlich:
Run: `python3 scripts/generate_manifest.py 2>&1 | grep "Generating Manifest"`
Expected: `ℹ Generating Manifest according to Plugin-Standard...` (ohne
Versionsnummer).

- [ ] **Step 6: `CHANGELOG.md` und `VERSION` inhaltlich gegenlesen**

Run: `cat CHANGELOG.md`
Expected: exakt der in Step 2 geschriebene Inhalt, gültiges Markdown
(Überschriften-Hierarchie `#`/`##`/`###` korrekt verschachtelt).

- [ ] **Step 7: Commit**

```bash
git add VERSION CHANGELOG.md scripts/generate_manifest.py
git commit -m "$(cat <<'EOF'
chore(release): cut v1.0.0

Introduces VERSION (single source of truth, plain text, root-level — this
repo has no package.json/pyproject.toml to hold it) and CHANGELOG.md
(Keep a Changelog format) per oe5ith-coding-rules §4. No retroactive entry
per historical commit — the first entry marks the starting point; from
here on, changes get dated [Unreleased] journal blocks consolidated at
each release.

1.0.0 rather than 0.1.0 to match how the oe5ith-coding-rules and
geodata-plugin-standard submodules were versioned at their own initial
extraction — the manifest.json/layer-list.json interface this repo
produces is already consumed by the external deployment system in
production, not an early 0.x development stage.

Also removes generate_manifest.py's stale hardcoded "v1.2" log reference
to the plugin *standard*'s version (a different concept from this repo's
own release version) — orphaned since the standard's version now lives in
the geodata-plugin-standard submodule's own git tag (currently v1.0.0),
not duplicated here.

See docs/superpowers/specs/2026-08-11-versioning-changelog-design.md for
the full design.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 8: Annotierten Tag setzen**

```bash
git tag -a v1.0.0 -m "v1.0.0"
git tag -l -n1 v1.0.0
```
Expected: `git tag -l -n1 v1.0.0` zeigt `v1.0.0          v1.0.0` (Tag
existiert, zeigt auf den Release-Commit aus Step 7 — mit
`git rev-parse v1.0.0` gegen `git rev-parse HEAD` bestätigen, dass beide
identisch sind).

---

## Self-Review

**Spec coverage:** Alle sechs Design-Entscheidungen umgesetzt: `VERSION`-Datei
(Step 1), Startversion 1.0.0 (Step 1/2), stale-Referenz-Fix (Step 3), kein
rückwirkender Changelog-Eintrag (Step 2, nur ein Startpunkt-Eintrag),
Release-Commit bündelt alles (Step 7), Tag auf dem Release-Commit (Step 8).
Kein Push, kein Deploy — nicht Teil dieses Plans, keine Steps dafür.

**Placeholder-Scan:** Kein TBD/TODO, jeder Step enthält vollständigen
Datei-Inhalt bzw. exakten `old_string`/`new_string`.

**Typkonsistenz:** Version `1.0.0` konsistent in `VERSION`, `CHANGELOG.md`
und der Commit-Message. Datum `2026-08-11` konsistent im Changelog-Eintrag
und der Spec.
