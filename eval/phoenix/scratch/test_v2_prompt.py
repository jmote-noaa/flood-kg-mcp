"""
Validate system_prompt_v2.txt template filling via FloodKGAgent._load_system_prompt().

Tests that:
  1. Both placeholders are replaced (no literal {kg_schema} or {kg_guidelines} remain).
  2. county_designation_properties appears (from schema_prototype2.yml).
  3. hallucination_prevention appears (from prompt_guidelines2.yml).

Run with:
    uv run python eval/phoenix/scratch/test_v2_prompt.py
"""
import sys
from pathlib import Path

# Allow importing agent.py from eval/phoenix/ without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent import FloodKGAgent  # noqa: E402

# model= is required by the constructor but unused during prompt loading.
agent = FloodKGAgent(system_prompt_version="v2", model="placeholder-for-test")
filled = agent._load_system_prompt()

checks = {
    "no unfilled {kg_schema} placeholder":     "{kg_schema}" not in filled,
    "no unfilled {kg_guidelines} placeholder": "{kg_guidelines}" not in filled,
    "county_designation_properties present":   "county_designation_properties" in filled,
    "hallucination_prevention present":         "hallucination_prevention" in filled,
}

all_passed = True
for description, result in checks.items():
    status = "PASS" if result else "FAIL"
    print(f"  [{status}] {description}")
    if not result:
        all_passed = False

print()
if all_passed:
    print(f"All checks passed. Filled prompt: {len(filled)} chars.")
else:
    raise SystemExit("One or more checks failed.")
