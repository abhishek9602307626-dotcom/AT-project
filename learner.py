# learner.py - Input validation, Prefix Tree Acceptor (PTA), state merging (RPNI style),
#              language parser (make_checker), and counterexample-guided learning loop.

import itertools
import re
from minimizer import clean_dfa
from tester import simulate_dfa

# Validates the alphabet and all sample strings, returning detailed plain-English errors.
# Input: alphabet_str (e.g. "0, 1"), pos_str (accepted strings), neg_str (rejected strings)
# Output: (alphabet list, pos list, neg list, error string or None)
def validate_inputs(alphabet_str, pos_str, neg_str):
    raw_alpha = [s.strip() for s in alphabet_str.replace(",", " ").split() if s.strip()]
    alphabet  = sorted(list(set(raw_alpha)))

    if not alphabet:
        return None, None, None, "Empty alphabet. Please enter at least one symbol (e.g. 0, 1)."

    alpha_set = set(alphabet)

    pos_list = [s.strip() for s in pos_str.replace(",", " ").replace("\n", " ").split() if s.strip()]
    neg_list = [s.strip() for s in neg_str.replace(",", " ").replace("\n", " ").split() if s.strip()]

    pos_seen = []
    for w in pos_list:
        if w not in pos_seen:
            pos_seen.append(w)
    pos_list = pos_seen

    neg_seen = []
    for w in neg_list:
        if w not in neg_seen:
            neg_seen.append(w)
    neg_list = neg_seen

    for w in pos_list:
        bad_symbols = set(w) - alpha_set
        if bad_symbols:
            bad_sym = sorted(list(bad_symbols))[0]
            return None, None, None, (
                f"Positive string '{w}' contains the symbol '{bad_sym}' "
                f"which is not in the alphabet {sorted(list(alpha_set))}."
            )

    for w in neg_list:
        bad_symbols = set(w) - alpha_set
        if bad_symbols:
            bad_sym = sorted(list(bad_symbols))[0]
            return None, None, None, (
                f"Negative string '{w}' contains the symbol '{bad_sym}' "
                f"which is not in the alphabet {sorted(list(alpha_set))}."
            )

    pos_set = set(pos_list)
    neg_set = set(neg_list)
    overlap = sorted(list(pos_set & neg_set))
    if overlap:
        w = overlap[0]
        return None, None, None, (
            f"String '{w}' is in both the positive and negative lists. "
            f"Each string must be labelled as either accepted or rejected, not both."
        )

    return alphabet, pos_list, neg_list, None


# Builds a Prefix Tree Acceptor (PTA) from positive strings.
# Input: alphabet (list), pos_strings (list of str)
# Output: DFA dict representing the tree
def build_pta(alphabet, pos_strings):
    states = [""]
    transitions = {}
    accept_states = []

    for word in pos_strings:
        curr = ""
        for symbol in word:
            next_state = curr + symbol
            if next_state not in states:
                states.append(next_state)
            transitions[(curr, symbol)] = next_state
            curr = next_state
        if curr not in accept_states:
            accept_states.append(curr)

    state_map = {st: f"q{i}" for i, st in enumerate(states)}
    mapped_trans = {(state_map[st], sym): state_map[nxt]
                    for (st, sym), nxt in transitions.items()}
    return {
        "states": [state_map[s] for s in states],
        "alphabet": alphabet,
        "start": "q0",
        "accept": [state_map[s] for s in accept_states],
        "transitions": mapped_trans
    }


# Union-Find: finds the root representative of an item (with path compression).
# Input: item (str), parent (dict)
# Output: root representative string
def find_rep(item, parent):
    if item not in parent:
        parent[item] = item
        return item
    path = []
    while parent[item] != item:
        path.append(item)
        item = parent[item]
    for p in path:
        parent[p] = item
    return item


# Union-Find: merges the sets of two items.
# Input: a (str), b (str), parent (dict)
# Output: None
def union_sets(a, b, parent):
    root_a = find_rep(a, parent)
    root_b = find_rep(b, parent)
    if root_a != root_b:
        if root_a < root_b:
            parent[root_b] = root_a
        else:
            parent[root_a] = root_b


# Folds the automaton so it stays deterministic after a merge.
# Input: dfa (dict), parent (dict)
# Output: modified parent dict
def fold_automaton(dfa, parent):
    changed = True
    while changed:
        changed = False
        reps = list({find_rep(s, parent) for s in dfa["states"]})
        for rep in reps:
            for sym in dfa["alphabet"]:
                targets = {
                    find_rep(tgt, parent)
                    for (s, a), tgt in dfa["transitions"].items()
                    if find_rep(s, parent) == rep and a == sym
                }
                if len(targets) > 1:
                    target_list = list(targets)
                    for other in target_list[1:]:
                        if find_rep(target_list[0], parent) != find_rep(other, parent):
                            union_sets(target_list[0], other, parent)
                            changed = True
                            break
                if changed:
                    break
            if changed:
                break
    return parent


# Checks whether the current merging is consistent with positive and negative samples.
# Input: pta (dict), parent (dict), pos_strings (list), neg_strings (list)
# Output: bool
def is_consistent(pta, parent, pos_strings, neg_strings):
    accept_reps = {find_rep(st, parent) for st in pta["accept"]}

    for w in pos_strings:
        curr = find_rep(pta["start"], parent)
        for sym in w:
            nxt = None
            for (s, a), tgt in pta["transitions"].items():
                if find_rep(s, parent) == curr and a == sym:
                    nxt = find_rep(tgt, parent)
                    break
            if nxt is None:
                return False
            curr = nxt
        if curr not in accept_reps:
            return False

    for w in neg_strings:
        curr = find_rep(pta["start"], parent)
        ok = True
        for sym in w:
            nxt = None
            for (s, a), tgt in pta["transitions"].items():
                if find_rep(s, parent) == curr and a == sym:
                    nxt = find_rep(tgt, parent)
                    break
            if nxt is None:
                ok = False
                break
            curr = nxt
        if ok and curr in accept_reps:
            return False

    return True


# Runs RPNI state merging on the PTA.
# Input: pta (dict), pos_strings (list), neg_strings (list)
# Output: (dfa dict, merge_log list)
def merge_states_rpni(pta, pos_strings, neg_strings):
    states = sorted(pta["states"], key=lambda s: (len(s), s))
    parent = {s: s for s in states}
    merge_log = []
    step_num = 1

    for i in range(len(states)):
        for j in range(i):
            s_i = states[i]
            s_j = states[j]
            rep_i = find_rep(s_i, parent)
            rep_j = find_rep(s_j, parent)
            if rep_i == rep_j:
                continue

            temp_parent = dict(parent)
            union_sets(rep_i, rep_j, temp_parent)
            fold_automaton(pta, temp_parent)

            if is_consistent(pta, temp_parent, pos_strings, neg_strings):
                parent = temp_parent
                merge_log.append({
                    "Step": step_num,
                    "States Tried": f"{s_i} ↔ {s_j}",
                    "Result": "✅ Merged",
                    "Reason": "No conflict with positive/negative samples."
                })
            else:
                merge_log.append({
                    "Step": step_num,
                    "States Tried": f"{s_i} ↔ {s_j}",
                    "Result": "❌ Rejected",
                    "Reason": "Conflict: an accepted and a rejected string would reach the same state."
                })
            step_num += 1

    rep_set = sorted({find_rep(s, parent) for s in states})
    state_map = {r: f"q{idx}" for idx, r in enumerate(rep_set)}

    new_start = state_map[find_rep(pta["start"], parent)]
    accept_reps = {find_rep(s, parent) for s in pta["accept"]}
    new_accept = [state_map[r] for r in rep_set if r in accept_reps]

    new_transitions = {}
    for (s, a), tgt in pta["transitions"].items():
        src_m = state_map[find_rep(s, parent)]
        tgt_m = state_map[find_rep(tgt, parent)]
        new_transitions[(src_m, a)] = tgt_m

    learned_dfa = {
        "states": [state_map[r] for r in rep_set],
        "alphabet": pta["alphabet"],
        "start": new_start,
        "accept": new_accept,
        "transitions": new_transitions
    }
    return learned_dfa, merge_log


# Creates a language checker function is_in_language(s) from a regex or plain-English description.
# Input: text (str), alphabet (list of str)
# Output: (checker_func or None, description_text or None)
def make_checker(text, alphabet):
    if not text or not text.strip():
        return None, None

    raw = text.strip()
    low = raw.lower()

    # Rule 1: Divisible by N / Multiple of N (binary numbers)
    m = re.search(r'(?:divisible by|multiple of)\s*(\d+)', low)
    if m:
        n = int(m.group(1))
        if n > 0:
            def check_div(s):
                # empty string or 0 binary value counts as 0; 0 % n == 0
                val = 0 if not s else int(s, 2)
                return (val % n == 0)
            return check_div, f"binary strings divisible by {n}"

    # Rule 2: Even / Odd number of 0s / 1s / X
    m = re.search(r'(even|odd)\s+number\s+of\s+([a-zA-Z0-9])(?:s|\'s)?', low)
    if m:
        parity, sym = m.group(1), m.group(2)
        def check_parity(s):
            count = s.count(sym)
            return (count % 2 == 0) if parity == "even" else (count % 2 == 1)
        return check_parity, f"{parity} number of {sym}s"

    # Rule 3: Number of X divisible by N
    m = re.search(r'number\s+of\s+([a-zA-Z0-9])(?:s|\'s)?\s+divisible\s+by\s*(\d+)', low)
    if m:
        sym, n = m.group(1), int(m.group(2))
        if n > 0:
            def check_sym_div(s):
                return (s.count(sym) % n == 0)
            return check_sym_div, f"number of {sym}s divisible by {n}"

    # Rule 4: Length divisible by N
    m = re.search(r'length\s+divisible\s+by\s*(\d+)', low)
    if m:
        n = int(m.group(1))
        if n > 0:
            def check_len(s):
                return (len(s) % n == 0)
            return check_len, f"length divisible by {n}"

    # Rule 5: Ends with X
    m = re.search(r'ends?\s+with\s+([a-zA-Z0-9]+)', low)
    if m:
        sub = m.group(1)
        return (lambda s: s.endswith(sub)), f"ends with {sub}"

    # Rule 6: Starts with X
    m = re.search(r'starts?\s+with\s+([a-zA-Z0-9]+)', low)
    if m:
        sub = m.group(1)
        return (lambda s: s.startswith(sub)), f"starts with {sub}"

    # Rule 7: Does not contain X
    m = re.search(r'does\s+not\s+contain\s+([a-zA-Z0-9]+)', low)
    if m:
        sub = m.group(1)
        return (lambda s: sub not in s), f"does not contain {sub}"

    # Rule 8: Contains X
    m = re.search(r'contains?\s+([a-zA-Z0-9]+)', low)
    if m:
        sub = m.group(1)
        return (lambda s: sub in s), f"contains {sub}"

    # Rule 9: Regex pattern (e.g. (0|1)*01)
    try:
        compiled = re.compile(raw)
        def check_regex(s):
            return bool(compiled.fullmatch(s))
        return check_regex, f"regex {raw}"
    except Exception:
        pass

    return None, None


# Learns a minimal, canonical DFA from a checker function using an active counterexample loop.
# Input: alphabet (list), checker (func), user_pos (list), user_neg (list)
# Output: (cleaned_dfa, merge_log, status_message, is_verified_bool, trained_pos, trained_neg)
def learn_with_language(alphabet, checker, user_pos=None, user_neg=None):
    if user_pos is None: user_pos = []
    if user_neg is None: user_neg = []

    pos_set = set(user_pos)
    neg_set = set(user_neg)

    # 1. Start with initial training samples up to length 4 (keep initial PTA light and fast)
    for length in range(5):
        for combo in itertools.product(alphabet, repeat=length):
            w = "".join(combo)
            if checker(w):
                pos_set.add(w)
            else:
                neg_set.add(w)

    last_dfa = None
    last_log = []
    status_msg = ""
    is_verified = False

    # 2. Active counterexample refinement loop (up to 20 rounds)
    for round_num in range(1, 21):
        pos_list = sorted(list(pos_set))
        neg_list = sorted(list(neg_set))

        pta = build_pta(alphabet, pos_list)
        raw_dfa, merge_log = merge_states_rpni(pta, pos_list, neg_list)
        cleaned_dfa, _ = clean_dfa(raw_dfa, pos_list, neg_list)

        last_dfa = cleaned_dfa
        last_log = merge_log

        # 3. Verify on strings up to length 12
        counterexample = None
        for length in range(13):
            for combo in itertools.product(alphabet, repeat=length):
                w = "".join(combo)
                expected = checker(w)
                acc, _, _, _ = simulate_dfa(cleaned_dfa, w)
                if acc != expected:
                    counterexample = (w, expected)
                    break
            if counterexample:
                break

        if not counterexample:
            is_verified = True
            status_msg = "Verified correct on all strings up to length 12"
            break
        else:
            w, expected = counterexample
            # Add counterexample and all its prefixes to training data
            for i in range(len(w) + 1):
                pref = w[:i]
                if checker(pref):
                    pos_set.add(pref)
                    neg_set.discard(pref)
                else:
                    neg_set.add(pref)
                    pos_set.discard(pref)

    if not is_verified:
        status_msg = f"Warning: still differs on string '{counterexample[0]}'"

    return last_dfa, last_log, status_msg, is_verified, sorted(list(pos_set)), sorted(list(neg_set))
