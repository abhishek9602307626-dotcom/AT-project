# nfa_tools.py - NFA simulation, epsilon closure, subset construction,
#                plus dfa_to_nfa and dfa_to_enfa converters

# We store the epsilon symbol as a module-level constant so there is no risk
# of encoding problems anywhere in the file.
EPSILON = "\u03b5"   # the Greek letter epsilon: ε


# Computes the epsilon closure for a given set of states.
# Follows all epsilon edges until no new states are found (BFS/DFS).
# Input: states (list or set of str), transitions (dict: (state,sym) -> list)
# Output: set of all states reachable by epsilon transitions alone
def epsilon_closure(states, transitions):
    closure = set(states)
    stack = list(states)
    while stack:
        curr = stack.pop()
        # Look for epsilon edges from curr
        for nxt in transitions.get((curr, EPSILON), []):
            if nxt not in closure:
                closure.add(nxt)
                stack.append(nxt)
    return closure


# Simulates an NFA or epsilon-NFA on an input string, step by step.
# Input: nfa (dict), word (str)
# Output: (is_accepted bool, list of step tuples (action, symbol, active_states))
def simulate_nfa(nfa, word):
    curr_states = epsilon_closure([nfa["start"]], nfa["transitions"])
    steps = [("Start (eps-closure)", "", sorted(list(curr_states)))]

    for sym in word:
        # Follow all direct transitions on this symbol
        direct = set()
        for st in curr_states:
            for tgt in nfa["transitions"].get((st, sym), []):
                direct.add(tgt)
        # Then close under epsilon
        curr_states = epsilon_closure(direct, nfa["transitions"])
        steps.append(("Read '" + sym + "'", sym, sorted(list(curr_states))))

    accept_set = set(nfa["accept"])
    is_accepted = bool(curr_states.intersection(accept_set))
    return is_accepted, steps


# Converts an NFA or epsilon-NFA to a DFA using the Subset Construction algorithm.
# Each DFA state = a frozenset of NFA states that can be active simultaneously.
# Input: nfa (dict)
# Output: (dfa dict, list of table-row dicts showing each step of the conversion)
def nfa_to_dfa(nfa):
    start_closure = frozenset(epsilon_closure([nfa["start"]], nfa["transitions"]))
    subset_to_name = {start_closure: "S0"}
    name_to_subset = {"S0": start_closure}
    queue = [start_closure]
    dfa_transitions = {}
    table_rows = []

    while queue:
        curr_subset = queue.pop(0)
        curr_name = subset_to_name[curr_subset]

        subset_str = "{" + ", ".join(sorted(curr_subset)) + "}"
        row_dict = {"DFA State": curr_name, "NFA Subset": subset_str}

        for sym in nfa["alphabet"]:
            # Collect all NFA states reachable on this symbol from curr_subset
            direct = set()
            for st in curr_subset:
                for tgt in nfa["transitions"].get((st, sym), []):
                    direct.add(tgt)
            # Then close under epsilon
            next_subset = frozenset(epsilon_closure(direct, nfa["transitions"]))

            # Assign a name to the new subset if we haven't seen it yet
            if next_subset not in subset_to_name:
                new_name = "S" + str(len(subset_to_name))
                subset_to_name[next_subset] = new_name
                name_to_subset[new_name] = next_subset
                queue.append(next_subset)

            tgt_name = subset_to_name[next_subset]
            dfa_transitions[(curr_name, sym)] = tgt_name
            next_str = "{" + ", ".join(sorted(next_subset)) + "}"
            row_dict["Move on '" + sym + "'"] = tgt_name + " (" + next_str + ")"

        table_rows.append(row_dict)

    accept_set = set(nfa["accept"])
    dfa_accept = [
        name for name, subset in name_to_subset.items()
        if subset.intersection(accept_set)
    ]

    dfa = {
        "states":      list(name_to_subset.keys()),
        "alphabet":    list(nfa["alphabet"]),
        "start":       "S0",
        "accept":      dfa_accept,
        "transitions": dfa_transitions
    }
    return dfa, table_rows


# Converts a DFA into an equivalent NFA.
# A DFA is already a special NFA; we just wrap each transition target in a list.
# Input: dfa (dict)
# Output: nfa (dict) where every transition value is a list of states
def dfa_to_nfa(dfa):
    nfa_transitions = {}
    for (state, sym), target in dfa["transitions"].items():
        nfa_transitions[(state, sym)] = [target]   # wrap single target in a list
    return {
        "states":      list(dfa["states"]),
        "alphabet":    list(dfa["alphabet"]),
        "start":       dfa["start"],
        "accept":      list(dfa["accept"]),
        "transitions": nfa_transitions
    }


# Converts a DFA into an epsilon-NFA by adding a new start and new accept state.
# new_start --eps--> old_start
# every old accept state --eps--> new_accept  (old accepts stop being accepting)
# Input: dfa (dict)
# Output: enfa (dict) with EPSILON transitions using the EPSILON constant
def dfa_to_enfa(dfa):
    new_start  = "s_new"
    new_accept = "f_new"
    enfa_transitions = {}

    # Copy all existing DFA transitions, wrapping targets in lists
    for (state, sym), target in dfa["transitions"].items():
        enfa_transitions[(state, sym)] = [target]

    # Add epsilon edge: new_start -> old start
    enfa_transitions[(new_start, EPSILON)] = [dfa["start"]]

    # Add epsilon edges: every old accepting state -> new_accept
    for acc in dfa["accept"]:
        key = (acc, EPSILON)
        if key not in enfa_transitions:
            enfa_transitions[key] = []
        enfa_transitions[key].append(new_accept)

    return {
        "states":      [new_start] + list(dfa["states"]) + [new_accept],
        "alphabet":    list(dfa["alphabet"]),
        "start":       new_start,
        "accept":      [new_accept],
        "transitions": enfa_transitions
    }
