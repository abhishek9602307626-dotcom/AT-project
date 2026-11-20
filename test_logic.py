# test_logic.py - Unit test checking all modules and the required example
from learner import validate_inputs, build_pta, merge_states_rpni
from nfa_tools import parse_nfa_text, simulate_nfa, nfa_to_dfa
from regex_tools import regex_to_nfa, dfa_to_regex
from minimizer import minimize_dfa
from tester import simulate_dfa, check_dfa_equivalence

def test_example():
    alpha, pos, neg, err = validate_inputs("0, 1", "01, 101, 1101", "10, 111, 100")
    assert err is None
    pta = build_pta(alpha, pos)
    dfa = merge_states_rpni(pta, pos, neg)
    
    # Check all positive accepted
    for w in pos:
        acc, _, _, _ = simulate_dfa(dfa, w)
        assert acc is True, f"Failed on positive {w}"
    # Check all negative rejected
    for w in neg:
        acc, _, _, _ = simulate_dfa(dfa, w)
        assert acc is False, f"Failed on negative {w}"
        
    print("Test passed! DFA states:", len(dfa["states"]), "transitions:", len(dfa["transitions"]))
    
    # Test Minimization
    min_dfa, hist = minimize_dfa(dfa)
    assert len(min_dfa["states"]) <= len(dfa["states"])
    eq, _, _ = check_dfa_equivalence(dfa, min_dfa)
    assert eq is True, "Minimized DFA must be equivalent to learned DFA"
    print("Minimization passed! Equivalence confirmed.")

    # Test Regex conversion
    reg = dfa_to_regex(min_dfa)
    print("DFA to Regex:", reg)

    # Test NFA subset construction
    nfa_sample = """
    states: q0, q1
    alphabet: 0, 1
    start: q0
    accept: q1
    transitions:
    q0, 0 -> q0, q1
    q0, 1 -> q0
    """
    nfa, _ = parse_nfa_text(nfa_sample)
    d, _ = nfa_to_dfa(nfa)
    print("NFA to DFA conversion passed, states:", len(d["states"]))

if __name__ == "__main__":
    test_example()
