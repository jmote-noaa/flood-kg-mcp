#!/usr/bin/env bash
# Scripted eval of the Flood KG agent in watsonx Orchestrate.
#
# Sends each gold question (eval/phoenix/datasets/flood-eval-0) to the live
# Orchestrate agent with `orchestrate chat ask`, saves every answer, and runs
# simple keyword checks. Keyword checks are a first pass only: anything marked
# REVIEW (and any FAIL) should be read against evaluation.xml by a person.
#
# Prerequisites (IBM Cloud Shell or any Linux shell):
#   pip install --user ibm-watsonx-orchestrate
#   export PATH=$HOME/.local/bin:$PATH
#   orchestrate env activate <your-env>
#
# Usage:
#   bash run_orchestrate_eval.sh [agent-name]

set -uo pipefail

AGENT="${1:-flood_kg_agent_jm}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="eval_results/orchestrate-${STAMP}"
mkdir -p "$OUT"
SUMMARY="$OUT/summary.csv"
echo "id,result,note" > "$SUMMARY"

QUESTIONS=(
  "How many flood events are in the graph?"
  "Which declarations included Public Assistance?"
  "Which counties have the lowest broadband access rates?"
  "Which declarations were associated with hurricanes?"
  "Which FEMA-designated counties have the highest poverty rates?"
  "How many counties received both NWS flood warnings and FEMA disaster declarations?"
  "Which counties are most vulnerable to flooding?"
  "What is the average duration of NWS flash flood warnings?"
  "Give each county a composite flood resilience score."
  "How many NFIP flood insurance claims were filed in Harris County?"
)

# Case-insensitive regex match against the agent's final answer only
# (the part after the agent's reply header), so tool output in any
# reasoning trace cannot produce a false PASS.
has() { sed -n '/🤖/,/👤 You:/p' "$2" | grep -Eqi -- "$1"; }

record() { echo "$1,$2,\"$3\"" >> "$SUMMARY"; printf '%-4s %-7s %s\n' "$1" "$2" "$3"; }

for i in "${!QUESTIONS[@]}"; do
  n=$((i + 1))
  q="${QUESTIONS[$i]}"
  f="$OUT/q${n}.txt"
  echo "Q${n}: ${q}"
  {
    echo "QUESTION: ${q}"
    echo "AGENT: ${AGENT}"
    echo "----"
    # chat ask stays in chat mode after answering; piping "exit" ends the
    # session so the script moves to the next question. Each call without
    # --thread-id starts a new conversation.
    echo exit | orchestrate chat ask --agent-name "$AGENT" "$q" 2>&1
  } > "$f"
  if ! grep -q '🤖' "$f"; then
    echo "  (no agent reply found; see $f)"
  fi

  case $n in
    1)  if has '1,?540' "$f"; then record Q1 PASS "1540 found"; else record Q1 FAIL "expected 1540"; fi ;;
    2)  if has '4781' "$f" && has '4798' "$f" && has '4879' "$f"; then record Q2 PASS "all 3 declarations"
        else record Q2 FAIL "expected 4781, 4798, 4879"; fi ;;
    3)  if has 'Foard' "$f" && has 'Somervell' "$f"; then record Q3 REVIEW "Foard and Somervell present; check order"
        else record Q3 FAIL "expected Foard first, Somervell 10th"; fi ;;
    4)  if has '4798' "$f" && ! has '4781|4879' "$f"; then record Q4 PASS "only 4798"
        else record Q4 FAIL "expected only 4798 (Hurricane Beryl)"; fi ;;
    5)  if has 'Starr' "$f" && has 'Kleberg' "$f" && ! has 'Dimmit' "$f"; then record Q5 REVIEW "Starr and Kleberg present, no Dimmit; check order"
        else record Q5 FAIL "expected Starr first; Dimmit means the FEMA filter was dropped"; fi ;;
    6)  if has '\b106\b' "$f"; then record Q6 PASS "106 found"; else record Q6 FAIL "expected 106"; fi ;;
    7)  if has 'Dimmit' "$f" && has 'Loving' "$f" && has 'Hudspeth' "$f" && ! has 'composite (score|index)[^.]*:' "$f"; then
          record Q7 REVIEW "indicator leaders present; check four separate rankings"
        else record Q7 FAIL "expected Dimmit, Loving, Hudspeth leaders"; fi ;;
    8)  if has '3\.3[0-9]|3\.4' "$f"; then record Q8 PASS "about 3.36 hours"; else record Q8 FAIL "expected ~3.36 hours"; fi ;;
    9)  if has 'not (supported|defined)|does not define|no composite|cannot' "$f" && has 'broadband' "$f"; then
          record Q9 REVIEW "declined and named indicators; confirm no score was computed"
        else record Q9 FAIL "expected a decline plus the four resilience indicators"; fi ;;
    10) if has 'not (included|available|contain|in the)|does not (contain|include)|cannot be answered' "$f"; then
          record Q10 PASS "stated data not in graph"
        else record Q10 FAIL "expected statement that NFIP data is not in the graph"; fi ;;
  esac
done

echo
echo "Answers and summary saved in: $OUT"
echo "Read every REVIEW or FAIL answer against eval/phoenix/datasets/flood-eval-0/evaluation.xml."
