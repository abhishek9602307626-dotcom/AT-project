# test_divisible_by_3.py - Verify Fix 1, 2, 3, 4, 5
import sys
sys.path.insert(0, r"C:\Users\USER\.gemini\antigravity\scratch\formal_language_reverse_engineer")

from learner import make_checker, learn_with_language, validate_inputs, build_pta, merge_states_rpni
from minimizer import clean_dfa
from tester import simulate_dfa
from regex_tools import dfa_to_regex

def test_divisible_by_3():
    checker, desc = make_checker("binary strings divisible by 3", ["0", "1"])
    assert checker is not None
    assert "divisible by 3" in desc

    # Run counterexample learning
    dfa, log, status_msg, is_verified, pos_data, neg_data = learn_with_language(["0", "1"], checker)

    print("Status message:", status_msg)
    print("DFA states:", dfa["states"])
    print("DFA transitions:", dfa["transitions"])
    print("DFA start:", dfa["start"])
    print("DFA accept:", dfa["accept"])

    # Fix 4 requirements: exactly 3 states, no dead state!
    assert len(dfa["states"]) == 3, f"Expected 3 states, got {len(dfa['states'])}"
    assert "dead" not in dfa["states"], "Divisible by 3 must NOT have a dead state!"
    assert is_verified is True, "Must be verified on all strings up to length 12"

    # Test specified strings:
    pos_cases = ["0", "11", "110", "1001", "10101", "111111"]
    neg_cases = ["1", "10", "100", "101", "1010"]

    for w in pos_cases:
        acc, _, _, st = simulate_dfa(dfa, w)
        assert acc is True, f"Failed on positive {w} (ended at {st})"

    for w in neg_cases:
        acc, _, _, st = simulate_dfa(dfa, w)
        assert acc is False, f"Failed on negative {w} (ended at {st})"

    print("✅ All positive & negative test cases for divisible by 3 passed!")

    # Check transition structure matches modulo 3 arithmetic:
    # q0: 0->q0, 1->q1
    # q1: 0->q2, 1->q0
    # q2: 0->q1, 1->q2
    t = dfa["transitions"]
    assert t[("q0", "0")] == "q0" and t[("q0", "1")] == "q1"
    assert t[("q1", "0")] == "q2" and t[("q1", "1")] == "q0"
    assert t[("q2", "0")] == "q1" and t[("q2", "1")] == "q2"
    print("✅ Transition structure perfectly matches textbook mod-3 DFA!")

def test_other_languages():
    # 1. ends with 01
    c1, d1 = make_checker("ends with 01", ["0", "1"])
    dfa1, _, _, v1, _, _ = learn_with_language(["0", "1"], c1)
    assert v1 is True
    acc, _, _, _ = simulate_dfa(dfa1, "1101")
    assert acc is True
    acc, _, _, _ = simulate_dfa(dfa1, "1110")
    assert acc is False
    print("✅ 'ends with 01' passed!")

    # 2. even number of 0s
    c2, d2 = make_checker("even number of 0s", ["0", "1"])
    dfa2, _, _, v2, _, _ = learn_with_language(["0", "1"], c2)
    assert v2 is True
    assert len(dfa2["states"]) == 2
    acc, _, _, _ = simulate_dfa(dfa2, "010")
    assert acc is True
    acc, _, _, _ = simulate_dfa(dfa2, "0100")
    assert acc is False
    print("✅ 'even number of 0s' passed!")

    # 3. Regex (0|1)*01
    c3, d3 = make_checker("(0|1)*01", ["0", "1"])
    dfa3, _, _, v3, _, _ = learn_with_language(["0", "1"], c3)
    assert v3 is True
    print("✅ Regex '(0|1)*01' passed!")

    # 4. Old example with no language: pos {01,101,1101}, neg {10,111,100}
    alpha, pos, neg, _ = validate_inputs("0, 1", "01, 101, 1101", "10, 111, 100")
    pta = build_pta(alpha, pos)
    raw, _ = merge_states_rpni(pta, pos, neg)
    clean, _ = clean_dfa(raw, pos, neg)
    for w in pos:
        acc, _, _, _ = simulate_dfa(clean, w)
        assert acc is True
    for w in neg:
        acc, _, _, _ = simulate_dfa(clean, w)
        assert acc is False
    print("✅ Old manual example with no language passed!")

if __name__ == "__main__":
    test_divisible_by_3()
    test_other_languages()
