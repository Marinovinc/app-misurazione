#!/usr/bin/env bash
# Ricostruisce il branch gh-pages con i soli file statici dell'app.
#
# Il sito e' servito da un branch separato invece che da app/ perche' GitHub
# Pages pubblica solo dalla radice del branch o da docs/, e duplicare i file in
# docs/ significherebbe tenerne allineate due copie a mano.
#
# `server.py` resta fuori: appartiene allo sviluppo locale e in un sito statico
# non ha nulla da fare. `.nojekyll` impedisce a Jekyll di elaborare la cartella
# — altrimenti ignorerebbe i file che iniziano con underscore.
#
#   bash pubblica.sh
#
# Prima di pubblicare deve essere verde il gate: mypy + pytest. Il test
# `test_nessun_percorso_assoluto_negli_asset` e' quello che protegge proprio
# questo passaggio, perche' l'app vive in una sottocartella (/app-misurazione/).
set -euo pipefail

RADICE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAVORO="$(mktemp -d)"
STATICI=(index.html core.js rileva.js sw.js manifest.webmanifest icon-512.png)

cd "$RADICE"
echo "verifico il gate prima di pubblicare..."
.venv/Scripts/python -m mypy >/dev/null
.venv/Scripts/python -m pytest -q >/dev/null
echo "gate verde"

git worktree add "$LAVORO" gh-pages >/dev/null 2>&1
trap 'git worktree remove "$LAVORO" --force >/dev/null 2>&1 || true' EXIT

cd "$LAVORO"
git rm -rq --ignore-unmatch .
for f in "${STATICI[@]}"; do cp "$RADICE/app/$f" .; done
touch .nojekyll

if git diff --cached --quiet && git diff --quiet; then
  echo "nessuna modifica da pubblicare"
  exit 0
fi

git add -A
git commit -q -m "pubblica: $(cd "$RADICE" && git log -1 --format=%s main)"
git push -q origin gh-pages
echo "pubblicato -> https://marinovinc.github.io/app-misurazione/"
echo "il rilascio impiega circa un minuto ad arrivare online"
