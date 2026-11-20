# test_all_changes.py - Verifies all 6 changes from the new requirements

import sys
sys.path.insert(0, r"C:\Users\USER\.gemini\antigravity\scratch\formal_language_reverse_engineer")

from learner    import validate_inputs, build_pta, merge_states_rpni
from nfa_tools  import nfa_to_dfa, dfa_to_nfa, dfa_to_enfa, simulate_nfa, epsilon_closure
from regex_tools import regex_to_nfa, dfa_to_regex, generate_strings_from_regex, looks_like_plain_english
from minimizer  import minimize_dfa
from tester     import simulate_dfa, check_dfa_equivalence
from visualizer import build_dot, build_table_rows

ALPHA = ["0", "1"]
POS   = ["01", "101", "1101"]
NEG   = ["10", "111", "100"]

def test_validate_good_input():
    alpha, pos, neg, err = validate_inputs("0, 1", "01, 101, 1101", "10, 111, 100")
    assert err is None, f"Unexpected error: {err}"
    assert set(alpha) == {"0", "1"}
    print("PASS  validate good input")

def test_validate_bad_symbol():
    _, _, _, err = validate_inputs("0, 1", "012", "10")
    assert err is not None
    assert "012" in err and "2" in err
    print("PASS  validate bad symbol error:", err)

def test_validate_overlap():
    _, _, _, err = validate_inputs("0, 1", "01", "01")
    assert err is not None
    assert "both" in err.lower() or "01" in err
    print("PASS  validate overlap error:", err)

def test_validate_empty_alphabet():
    _, _, _, err = validate_inputs("", "01", "10")
    assert err is not None
    print("PASS  validate empty alphabet:", err)

def test_rpni_basic():
    alpha, pos, neg, _ = validate_inputs("0, 1", "01, 101, 1101", "10, 111, 100")
    pta = build_pta(alpha, pos)
    dfa, log = merge_states_rpni(pta, pos, neg)
    for w in pos:
        acc, _, _, _ = simulate_dfa(dfa, w)
        assert acc, f"Should accept '{w}'"
    for w in neg:
        acc, _, _, _ = simulate_dfa(dfa, w)
        assert not acc, f"Should reject '{w}'"
    assert len(log) > 0, "Merge log should not be empty"
    print(f"PASS  RPNI — {len(dfa['states'])} states, {len(log)} merge attempts")

def test_dfa_to_nfa():
    alpha, pos, neg, _ = validate_inputs("0, 1", "01, 101, 1101", "10, 111, 100")
    pta = build_pta(alpha, pos)
    dfa, _ = merge_states_rpni(pta, pos, neg)
    nfa = dfa_to_nfa(dfa)
    # Every transition value must be a list
    for v in nfa["transitions"].values():
        assert isinstance(v, list), "NFA targets must be lists"
    # Must have same states, start, accept
    assert nfa["states"] == list(dfa["states"])
    assert nfa["start"]  == dfa["start"]
    # Round-trip back to DFA and check equivalence
    back_dfa, _ = nfa_to_dfa(nfa)
    is_eq, _, _ = check_dfa_equivalence(dfa, back_dfa)
    assert is_eq, "DFA -> NFA -> DFA must be equivalent"
    print("PASS  dfa_to_nfa (DFA -> NFA -> DFA round-trip)")

def test_dfa_to_enfa():
    alpha, pos, neg, _ = validate_inputs("0, 1", "01, 101, 1101", "10, 111, 100")
    pta = build_pta(alpha, pos)
    dfa, _ = merge_states_rpni(pta, pos, neg)
    enfa = dfa_to_enfa(dfa)
    assert "s_new"  in enfa["states"]
    assert "f_new"  in enfa["states"]
    assert enfa["start"] == "s_new"
    assert enfa["accept"] == ["f_new"]
    # Epsilon from new start to old start
    assert dfa["start"] in enfa["transitions"].get(("s_new", "ε"), [])
    # Round-trip
    back_dfa, _ = nfa_to_dfa(enfa)
    is_eq, _, _ = check_dfa_equivalence(dfa, back_dfa)
    assert is_eq, "DFA -> ε-NFA -> DFA must be equivalent"
    print("PASS  dfa_to_enfa (DFA -> ε-NFA -> DFA round-trip)")

def test_generate_strings_from_regex():
    result = generate_strings_from_regex("(0|1)*01", ALPHA, max_len=5)
    assert "01"   in result["pos"], "'01' should be positive"
    assert "101"  in result["pos"], "'101' should be positive"
    assert "10"   in result["neg"], "'10' should be negative"
    assert "111"  in result["neg"], "'111' should be negative"
    print(f"PASS  generate_strings_from_regex — {len(result['pos'])} pos, {len(result['neg'])} neg")

def test_plain_english_detector():
    assert looks_like_plain_english("binary strings ending in 01")  == True
    assert looks_like_plain_english("(0|1)*01")                     == False
    assert looks_like_plain_english("strings with at least two 1s") == True
    print("PASS  looks_like_plain_english")

def test_build_dot():
    alpha, pos, neg, _ = validate_inputs("0, 1", "01, 101, 1101", "10, 111, 100")
    pta = build_pta(alpha, pos)
    dfa, _ = merge_states_rpni(pta, pos, neg)
    dot = build_dot(dfa, title="Test DFA")
    assert "digraph" in dot
    assert "doublecircle" in dot     # accepting states
    assert "rankdir=LR"   in dot
    assert "__start__"    in dot     # invisible start arrow node
    print("PASS  build_dot (Graphviz DOT output)")

def test_highlight_path():
    alpha, pos, neg, _ = validate_inputs("0, 1", "01, 101, 1101", "10, 111, 100")
    pta = build_pta(alpha, pos)
    dfa, _ = merge_states_rpni(pta, pos, neg)
    # Build path for "01"
    curr = dfa["start"]
    path = [curr]
    for sym in "01":
        curr = dfa["transitions"].get((curr, sym), curr)
        path.append(curr)
    dot = build_dot(dfa, title="Highlight Test", highlight_path=path)
    assert "#FED7AA" in dot or "#EA580C" in dot   # orange highlight colour
    print("PASS  build_dot with highlight_path")

def test_minimization_keeps_equivalence():
    alpha, pos, neg, _ = validate_inputs("0, 1", "01, 101, 1101", "10, 111, 100")
    pta = build_pta(alpha, pos)
    dfa, _ = merge_states_rpni(pta, pos, neg)
    min_dfa, hist = minimize_dfa(dfa)
    is_eq, _, _ = check_dfa_equivalence(dfa, min_dfa)
    assert is_eq, "Minimized DFA must be equivalent"
    assert len(hist) >= 1
    print(f"PASS  minimize_dfa — {len(dfa['states'])} -> {len(min_dfa['states'])} states, {len(hist)} partition steps")

def test_simulation_with_path():
    alpha, pos, neg, _ = validate_inputs("0, 1", "01, 101, 1101", "10, 111, 100")
    pta = build_pta(alpha, pos)
    dfa, _ = merge_states_rpni(pta, pos, neg)
    acc, steps, path, last = simulate_dfa(dfa, "01")
    assert acc  is True
    assert last is not None
    acc2, steps2, path2, last2 = simulate_dfa(dfa, "10")
    assert acc2 is False
    print("PASS  simulate_dfa (01 accepted, 10 rejected)")

if __name__ == "__main__":
    test_validate_good_input()
    test_validate_bad_symbol()
    test_validate_overlap()
    test_validate_empty_alphabet()
    test_rpni_basic()
    test_dfa_to_nfa()
    test_dfa_to_enfa()
    test_generate_strings_from_regex()
    test_plain_english_detector()
    test_build_dot()
    test_highlight_path()
    test_minimization_keeps_equivalence()
    test_simulation_with_path()
    print("\n✅ All tests passed!")
