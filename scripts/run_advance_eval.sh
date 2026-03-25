#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PROMPTS="${RAIN_EVAL_PROMPTS:-data/eval/advance_prompts.txt}"
OUT_DIR="${RAIN_EVAL_OUT:-data/logs/advance_eval}"
mkdir -p "$OUT_DIR"
TS="$(date -u +%Y%m%d_%H%M%SZ)"
SUMMARY="$OUT_DIR/run_${TS}.txt"
export RAIN_ADVANCE_STACK="${RAIN_ADVANCE_STACK:-true}"
echo "RAIN_ADVANCE_STACK=$RAIN_ADVANCE_STACK" | tee "$SUMMARY"
echo "Outputs: $OUT_DIR/${TS}_*.txt" | tee -a "$SUMMARY"
i=0
while IFS= read -r line || [[ -n "$line" ]]; do
  [[ -z "${line// }" ]] && continue
  [[ "$line" == \#* ]] && continue
  i=$((i + 1))
  f="$OUT_DIR/${TS}_$(printf '%03d' "$i").txt"
  echo "--- prompt $i ---" | tee -a "$SUMMARY"
  echo "$line" | tee -a "$SUMMARY"
  set +e
  .venv/bin/python run.py "$line" 2>&1 | tee "$f" | tail -5 >>"$SUMMARY"
  ec=$?
  set -e
  echo "exit=$ec" >>"$SUMMARY"
done < "$PROMPTS"
echo "Done. Summary: $SUMMARY"
echo "Optional: python scripts/check_advance_eval.py --dir $OUT_DIR"
