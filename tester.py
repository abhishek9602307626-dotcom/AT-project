# tester.py - String testing with step path, and language equivalence check via product automaton

# Simulates a DFA on an input string, recording each step.
# Input: dfa (dict), word (str)
# Output: (is_accepted, step_records, formatted_path_str, final_state)
def simulate_dfa(dfa, word):
    curr = dfa["start"]
    path_nodes = [curr]
    path_edges = []
    step_records = []

    for sym in word:
        nxt = dfa["transitions"].get((curr, sym))
        step_records.append({"From State": curr, "Symbol": sym, "To State": nxt if nxt else "Dead (None)"})
        if nxt is None:
            # Trapped / rejected early
            return False, step_records, f"{curr} --({sym})--> [Dead]", None
        path_edges.append(f"--({sym})--> {nxt}")
        curr = nxt
        path_nodes.append(curr)

    is_accepted = (curr in dfa["accept"])
    path_str = path_nodes[0]
    for i in range(len(path_edges)):
        path_str += f" {path_edges[i]}"

    return is_accepted, step_records, path_str, curr


# Checks language equivalence between two DFAs using product automaton / BFS exploration.
# Input: dfa1 (dict), dfa2 (dict)
# Output: (is_equivalent, counterexample_word_or_None, explanation)
def check_dfa_equivalence(dfa1, dfa2):
    # Union of alphabets
    alphabet = sorted(list(set(dfa1["alphabet"]).union(set(dfa2["alphabet"]))))
    
    start_pair = (dfa1["start"], dfa2["start"])
    visited = set([start_pair])
    queue = [(start_pair, "")]

    acc1 = set(dfa1["accept"])
    acc2 = set(dfa2["accept"])

    while queue:
        (u, v), word = queue.pop(0)

        # Check if one is accepting and the other is not (symmetric difference)
        u_acc = (u in acc1)
        v_acc = (v in acc2)

        if u_acc != v_acc:
            # Found counterexample
            explanation = (
                f"Automata differ on word '{word}'! "
                f"DFA 1 {'accepts' if u_acc else 'rejects'}, "
                f"while DFA 2 {'accepts' if v_acc else 'rejects'}."
            )
            return False, word, explanation

        for sym in alphabet:
            nxt_u = dfa1["transitions"].get((u, sym), "DEAD1")
            nxt_v = dfa2["transitions"].get((v, sym), "DEAD2")
            nxt_pair = (nxt_u, nxt_v)

            if nxt_pair not in visited:
                visited.add(nxt_pair)
                queue.append((nxt_pair, word + sym))

    return True, None, "The two automata accept the exact same language (L(M1) = L(M2))."
