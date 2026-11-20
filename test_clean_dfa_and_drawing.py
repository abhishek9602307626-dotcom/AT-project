# test_clean_dfa_and_drawing.py - Test clean_dfa, renaming, completion, and diagram generation

import sys
sys.path.insert(0, r"C:\Users\USER\.gemini\antigravity\scratch\formal_language_reverse_engineer")

from learner import validate_inputs, build_pta, merge_states_rpni
from minimizer import clean_dfa
from tester import simulate_dfa, check_dfa_equivalence
from visualizer import build_dot, build_table_rows
from regex_tools import dfa_to_regex

def test_full_pipeline():
    alpha, pos, neg, err = validate_inputs("0, 1", "01, 101, 1101", "10, 111, 100")
    assert err is None
    pta = build_pta(alpha, pos)
    raw_dfa, _ = merge_states_rpni(pta, pos, neg)
    
    # Run clean_dfa
    cleaned, has_dead = clean_dfa(raw_dfa)

    print("States in cleaned DFA:", cleaned["states"])
    print("Start state:", cleaned["start"])
    print("Accept states:", cleaned["accept"])
    print("Has dead state:", has_dead)

    # 1. State naming verification: non-dead states MUST be q0, q1, ...
    non_dead = [s for s in cleaned["states"] if s != "dead"]
    for i, s in enumerate(non_dead):
        assert s == f"q{i}", f"Expected state name q{i}, got {s}"

    assert cleaned["start"] == "q0", f"Start state must be q0, got {cleaned['start']}"

    # 2. Positives & Negatives correctness
    for w in pos:
        acc, _, _, _ = simulate_dfa(cleaned, w)
        assert acc is True, f"Positive '{w}' was rejected!"
    for w in neg:
        acc, _, _, _ = simulate_dfa(cleaned, w)
        assert acc is False, f"Negative '{w}' was accepted!"

    # 3. Equivalence with raw merged DFA
    is_eq, counter, reason = check_dfa_equivalence(raw_dfa, cleaned)
    assert is_eq is True, f"Cleaned DFA not equivalent to raw DFA: {reason}"

    # 4. DOT diagram generation
    dot_no_dead = build_dot(cleaned, title="Learned DFA", show_dead_state=False)
    assert "q0" in dot_no_dead
    assert "doublecircle" in dot_no_dead
    assert "start" in dot_no_dead
    assert "nodesep=0.8" in dot_no_dead
    assert "ranksep=1.2" in dot_no_dead

    dot_with_dead = build_dot(cleaned, title="Learned DFA", show_dead_state=True)
    if has_dead:
        assert "dead" in dot_with_dead
        assert "dashed" in dot_with_dead

    # 5. Table rows
    rows = build_table_rows(cleaned, show_dead_state=False)
    assert len(rows) == len(non_dead)
    for r in rows:
        assert "State" in r and "δ(0)" in r and "δ(1)" in r

    print("Regex:", dfa_to_regex(cleaned))
    print("\n✅ All clean_dfa and drawing tests passed successfully!")

if __name__ == "__main__":
    test_full_pipeline()
