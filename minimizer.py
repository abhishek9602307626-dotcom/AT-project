# minimizer.py - Remove unreachable states, partition refinement, and clean_dfa pipeline

# Finds all states reachable from the start state via BFS.
# Input: dfa (dict)
# Output: set of reachable state names
def get_reachable_states(dfa):
    visited = set([dfa["start"]])
    queue = [dfa["start"]]

    while queue:
        curr = queue.pop(0)
        for sym in dfa["alphabet"]:
            tgt = dfa["transitions"].get((curr, sym))
            if tgt and tgt not in visited:
                visited.add(tgt)
                queue.append(tgt)

    return visited


# Removes unreachable states from a DFA.
# Input: dfa (dict)
# Output: new cleaned DFA (dict)
def remove_unreachable(dfa):
    reachable = get_reachable_states(dfa)
    new_states = [s for s in dfa["states"] if s in reachable]
    new_accept = [s for s in dfa["accept"] if s in reachable]
    new_transitions = {
        (s, sym): tgt for (s, sym), tgt in dfa["transitions"].items()
        if s in reachable and tgt in reachable
    }

    return {
        "states": new_states,
        "alphabet": dfa["alphabet"],
        "start": dfa["start"],
        "accept": new_accept,
        "transitions": new_transitions
    }


# Formats a list of sets into a readable string for display.
# Input: partition (list of sets)
# Output: string (e.g. "[ {q0, q1}, {q2} ]")
def format_partition(partition):
    parts = []
    for group in partition:
        sorted_elems = sorted(list(group))
        parts.append("{" + ", ".join(sorted_elems) + "}")
    return "[ " + ", ".join(parts) + " ]"


# Minimizes a DFA using the Partition Refinement algorithm (Hopcroft/Moore style).
# Input: dfa (dict)
# Output: (minimized_dfa, partition_history_list)
def minimize_dfa(dfa):
    cleaned = remove_unreachable(dfa)
    states = set(cleaned["states"])
    accept_set = set(cleaned["accept"])
    non_accept = states - accept_set

    # Initial partition: Accept states and Non-Accept states
    partition = []
    if non_accept:
        partition.append(non_accept)
    if accept_set:
        partition.append(accept_set)

    history = [f"P0 (Initial): {format_partition(partition)}"]
    step_num = 1

    changed = True
    while changed:
        changed = False
        new_partition = []

        state_to_group = {}
        for idx, group in enumerate(partition):
            for st in group:
                state_to_group[st] = idx

        for group in partition:
            if len(group) <= 1:
                new_partition.append(group)
                continue

            subgroups = {}
            for st in group:
                signature = []
                for sym in cleaned["alphabet"]:
                    tgt = cleaned["transitions"].get((st, sym), None)
                    tgt_group = state_to_group.get(tgt, -1)
                    signature.append((sym, tgt_group))
                signature_key = tuple(signature)

                if signature_key not in subgroups:
                    subgroups[signature_key] = set()
                subgroups[signature_key].add(st)

            if len(subgroups) > 1:
                changed = True
            for sg in subgroups.values():
                new_partition.append(sg)

        partition = new_partition
        history.append(f"P{step_num}: {format_partition(partition)}")
        step_num += 1

    # Sort groups so start state is in first group if possible
    sorted_groups = []
    for g in partition:
        if cleaned["start"] in g:
            sorted_groups.insert(0, g)
        else:
            sorted_groups.append(g)

    group_map = {}
    min_states = []
    for idx, g in enumerate(sorted_groups):
        name = f"m{idx}"
        min_states.append(name)
        for st in g:
            group_map[st] = name

    min_start = group_map[cleaned["start"]]
    min_accept = []
    for idx, g in enumerate(sorted_groups):
        name = f"m{idx}"
        if any(st in cleaned["accept"] for st in g):
            min_accept.append(name)

    min_transitions = {}
    for (s, sym), tgt in cleaned["transitions"].items():
        src_min = group_map[s]
        tgt_min = group_map[tgt]
        min_transitions[(src_min, sym)] = tgt_min

    minimized = {
        "states": min_states,
        "alphabet": cleaned["alphabet"],
        "start": min_start,
        "accept": min_accept,
        "transitions": min_transitions
    }

    return minimized, history


# Checks if candidate transitions are consistent with training examples.
# Input: dfa_cand (dict), pos_strings (list), neg_strings (list)
# Output: bool
def _check_dfa_consistent(dfa_cand, pos_strings, neg_strings):
    acc_set = set(dfa_cand["accept"])
    for w in pos_strings:
        curr = dfa_cand["start"]
        for sym in w:
            curr = dfa_cand["transitions"].get((curr, sym))
            if curr is None:
                return False
        if curr not in acc_set:
            return False

    for w in neg_strings:
        curr = dfa_cand["start"]
        parsed = True
        for sym in w:
            curr = dfa_cand["transitions"].get((curr, sym))
            if curr is None:
                parsed = False
                break
        if parsed and curr in acc_set:
            return False
    return True


# Cleans and completes the DFA intelligently without blindly adding dead states.
# Tries routing missing transitions to an existing state without violating pos/neg examples.
# Input: dfa (dict), pos_strings (list, optional), neg_strings (list, optional)
# Output: (cleaned_dfa dict, has_dead_state bool)
def clean_dfa(dfa, pos_strings=None, neg_strings=None):
    if pos_strings is None: pos_strings = []
    if neg_strings is None: neg_strings = []

    # 1 & 2: Remove unreachable states and minimize
    min_dfa, _ = minimize_dfa(dfa)

    alphabet = sorted(list(min_dfa["alphabet"]))
    curr_states = list(min_dfa["states"])
    curr_transitions = dict(min_dfa["transitions"])
    curr_accept = set(min_dfa["accept"])
    start_state = min_dfa["start"]

    # Try intelligent completion for missing transitions before creating a dead state
    missing_edges = []
    for s in curr_states:
        for sym in alphabet:
            if (s, sym) not in curr_transitions or curr_transitions[(s, sym)] is None:
                missing_edges.append((s, sym))

    # For each missing transition, try routing to an existing state that satisfies all pos & neg samples
    still_missing = []
    for (s, sym) in missing_edges:
        resolved = False
        for cand_target in curr_states:
            test_trans = dict(curr_transitions)
            test_trans[(s, sym)] = cand_target
            cand_dfa = {
                "states": curr_states,
                "alphabet": alphabet,
                "start": start_state,
                "accept": list(curr_accept),
                "transitions": test_trans
            }
            if _check_dfa_consistent(cand_dfa, pos_strings, neg_strings):
                curr_transitions[(s, sym)] = cand_target
                resolved = True
                break
        if not resolved:
            still_missing.append((s, sym))

    # If any transitions are still missing, route them to a dead state
    has_dead = len(still_missing) > 0
    dead_name = "dead"
    if has_dead:
        curr_states.append(dead_name)
        for sym in alphabet:
            curr_transitions[(dead_name, sym)] = dead_name
        for (s, sym) in still_missing:
            curr_transitions[(s, sym)] = dead_name

    # Canonical BFS renaming starting from start_state (q0, q1, ...)
    order = []
    visited = set([start_state])
    queue = [start_state]

    while queue:
        curr = queue.pop(0)
        order.append(curr)
        for sym in alphabet:
            nxt = curr_transitions.get((curr, sym))
            if nxt and nxt != dead_name and nxt not in visited:
                visited.add(nxt)
                queue.append(nxt)

    for s in curr_states:
        if s != dead_name and s not in visited:
            visited.add(s)
            order.append(s)

    name_map = {old: f"q{i}" for i, old in enumerate(order)}
    if has_dead:
        name_map[dead_name] = "dead"

    final_states = [name_map[s] for s in order]
    if has_dead:
        final_states.append("dead")

    final_start = name_map[start_state]
    final_accept = sorted([name_map[s] for s in curr_accept if s in name_map])

    final_transitions = {}
    for (s, sym), tgt in curr_transitions.items():
        if s in name_map and tgt in name_map:
            final_transitions[(name_map[s], sym)] = name_map[tgt]

    cleaned_result = {
        "states": final_states,
        "alphabet": alphabet,
        "start": final_start,
        "accept": final_accept,
        "transitions": final_transitions
    }

    return cleaned_result, has_dead
