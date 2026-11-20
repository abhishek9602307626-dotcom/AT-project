# regex_tools.py - Thompson's construction (regex -> ε-NFA), State Elimination (DFA -> regex),
#                  and regex simplification.

import itertools
import re

# Helper function to generate fresh state IDs.
class StateCounter:
    def __init__(self):
        self.count = 0
    def next_id(self):
        name = f"t{self.count}"
        self.count += 1
        return name


# Inserts explicit concatenation operator '.' into regular expression.
# Input: regex (str)
# Output: regex string with '.' inserted
def insert_concat_operator(regex):
    result = []
    clean_regex = "".join(regex.split())
    for i in range(len(clean_regex)):
        c1 = clean_regex[i]
        result.append(c1)
        if i + 1 < len(clean_regex):
            c2 = clean_regex[i + 1]
            c1_can_end = (c1 not in "(|")
            c2_can_start = (c2 not in ")*|")
            if c1_can_end and c2_can_start:
                result.append(".")
    return "".join(result)


# Converts infix regex with '.' to postfix using Shunting-yard algorithm.
# Input: regex_with_concat (str)
# Output: list of tokens in postfix order
def regex_to_postfix(regex_str):
    prec = {"*": 3, ".": 2, "|": 1}
    postfix = []
    stack = []

    for char in regex_str:
        if char == "(":
            stack.append(char)
        elif char == ")":
            while stack and stack[-1] != "(":
                postfix.append(stack.pop())
            if stack and stack[-1] == "(":
                stack.pop()
        elif char in prec:
            while stack and stack[-1] != "(" and prec.get(stack[-1], 0) >= prec[char]:
                postfix.append(stack.pop())
            stack.append(char)
        else:
            postfix.append(char)

    while stack:
        postfix.append(stack.pop())

    return postfix


# Converts a regular expression to an ε-NFA using Thompson's construction.
# Input: regex (str), alphabet (list of str or None)
# Output: nfa dict
def regex_to_nfa(regex, alphabet=None):
    if not regex:
        return {"states": ["t0"], "alphabet": alphabet or [], "start": "t0", "accept": ["t0"], "transitions": {}}

    formatted = insert_concat_operator(regex)
    postfix = regex_to_postfix(formatted)
    counter = StateCounter()
    stack = []

    for token in postfix:
        if token == "*":
            frag = stack.pop()
            s_start = counter.next_id()
            s_accept = counter.next_id()
            
            trans = dict(frag["transitions"])
            trans.setdefault((s_start, "ε"), []).extend([frag["start"], s_accept])
            trans.setdefault((frag["accept"], "ε"), []).extend([frag["start"], s_accept])

            stack.append({
                "states": frag["states"] + [s_start, s_accept],
                "start": s_start,
                "accept": s_accept,
                "transitions": trans
            })
        elif token == ".":
            frag2 = stack.pop()
            frag1 = stack.pop()
            trans = dict(frag1["transitions"])
            trans.update(frag2["transitions"])
            trans.setdefault((frag1["accept"], "ε"), []).append(frag2["start"])

            stack.append({
                "states": frag1["states"] + frag2["states"],
                "start": frag1["start"],
                "accept": frag2["accept"],
                "transitions": trans
            })
        elif token == "|":
            frag2 = stack.pop()
            frag1 = stack.pop()
            s_start = counter.next_id()
            s_accept = counter.next_id()

            trans = dict(frag1["transitions"])
            trans.update(frag2["transitions"])
            trans.setdefault((s_start, "ε"), []).extend([frag1["start"], frag2["start"]])
            trans.setdefault((frag1["accept"], "ε"), []).append(s_accept)
            trans.setdefault((frag2["accept"], "ε"), []).append(s_accept)

            stack.append({
                "states": frag1["states"] + frag2["states"] + [s_start, s_accept],
                "start": s_start,
                "accept": s_accept,
                "transitions": trans
            })
        else:
            s_start = counter.next_id()
            s_accept = counter.next_id()
            trans = {(s_start, token): [s_accept]}
            stack.append({
                "states": [s_start, s_accept],
                "start": s_start,
                "accept": s_accept,
                "transitions": trans
            })

    if not stack:
        return {"states": ["t0"], "alphabet": alphabet or [], "start": "t0", "accept": ["t0"], "transitions": {}}

    final_frag = stack.pop()
    all_syms = set()
    for (st, sym) in final_frag["transitions"].keys():
        if sym != "ε":
            all_syms.add(sym)
    if alphabet:
        all_syms = set(alphabet).union(all_syms)

    return {
        "states": sorted(list(set(final_frag["states"]))),
        "alphabet": sorted(list(all_syms)),
        "start": final_frag["start"],
        "accept": [final_frag["accept"]],
        "transitions": final_frag["transitions"]
    }


# Simplifies a regex string using basic algebra rules:
# removes redundant brackets (e.g. (0)* -> 0*), ∅, ε, and duplicate options.
# Input: expr (str)
# Output: simplified regex string
def simplify_regex(expr):
    if not expr or expr == "∅":
        return expr
    
    prev = ""
    curr = expr.strip()
    
    for _ in range(10): # repeat normalization passes
        if curr == prev:
            break
        prev = curr

        # 1. Strip redundant outer parentheses: ((r)) -> (r)
        while curr.startswith("(") and curr.endswith(")"):
            # Ensure the outer parens actually match each other
            depth = 0
            matches_end = False
            for idx, ch in enumerate(curr):
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0 and idx == len(curr) - 1:
                        matches_end = True
                        break
                    elif depth == 0:
                        break
            if matches_end:
                curr = curr[1:-1].strip()
            else:
                break

        # 2. (single_alphanumeric)* -> single_alphanumeric* (e.g. (0)* -> 0*, (1)* -> 1*)
        curr = re.sub(r'\(([a-zA-Z0-9])\)\*', r'\1*', curr)

        # 3. ((single_alphanumeric)) -> single_alphanumeric
        curr = re.sub(r'\(([a-zA-Z0-9])\)', r'\1', curr)

        # 4. ε* -> ε
        curr = curr.replace("ε*", "ε")

        # 5. r|∅ -> r, ∅|r -> r
        curr = re.sub(r'\|∅', '', curr)
        curr = re.sub(r'∅\|', '', curr)

        # 6. rε -> r (when r is an alphanumeric), εr -> r
        curr = re.sub(r'([a-zA-Z0-9*])ε', r'\1', curr)
        curr = re.sub(r'ε([a-zA-Z0-9*])', r'\1', curr)

        # 7. Deduplicate identical options in unions: (A|A) -> A
        def dedupe_union(match):
            parts = match.group(1).split("|")
            seen = []
            for p in parts:
                if p not in seen:
                    seen.append(p)
            if len(seen) == 1:
                return seen[0]
            return f"({'|'.join(seen)})"

        curr = re.sub(r'\(([^()|]+\|[^()]+)\)', dedupe_union, curr)

    return curr if curr else "ε"


# Converts a DFA to a regular expression using the State Elimination algorithm.
# Input: dfa (dict)
# Output: simplified regular expression string
def dfa_to_regex(dfa):
    if not dfa["states"] or not dfa["accept"]:
        return "∅"

    new_start = "START_NODE"
    new_accept = "ACCEPT_NODE"
    gnfa = {}
    
    # Internal DFA transitions
    for (u, sym), v in dfa["transitions"].items():
        if (u, v) not in gnfa:
            gnfa[(u, v)] = sym
        else:
            gnfa[(u, v)] = f"({gnfa[(u, v)]}|{sym})"

    # Connect new start to start
    gnfa[(new_start, dfa["start"])] = "ε"

    # Connect all accept states to new accept
    for acc in dfa["accept"]:
        if (acc, new_accept) not in gnfa:
            gnfa[(acc, new_accept)] = "ε"
        else:
            gnfa[(acc, new_accept)] = f"({gnfa[(acc, new_accept)]}|ε)"

    # Eliminate intermediate states
    states_to_eliminate = [s for s in dfa["states"] if s != "dead"]

    for q in states_to_eliminate:
        r_qq = gnfa.get((q, q), None)
        loop_part = f"({r_qq})*" if r_qq else ""

        preds = [u for (u, v) in gnfa.keys() if v == q and u != q]
        succs = [v for (u, v) in gnfa.keys() if u == q and v != q]

        for p in preds:
            r_pq = gnfa[(p, q)]
            for s in succs:
                r_qs = gnfa[(q, s)]
                
                mid = []
                if r_pq != "ε":
                    mid.append(r_pq if len(r_pq) == 1 else f"({r_pq})")
                if loop_part:
                    mid.append(loop_part)
                if r_qs != "ε":
                    mid.append(r_qs if len(r_qs) == 1 else f"({r_qs})")
                
                bypass = "".join(mid) if mid else "ε"

                if (p, s) in gnfa:
                    existing = gnfa[(p, s)]
                    gnfa[(p, s)] = f"({existing}|{bypass})"
                else:
                    gnfa[(p, s)] = bypass

        keys_to_remove = [k for k in gnfa.keys() if k[0] == q or k[1] == q]
        for k in keys_to_remove:
            del gnfa[k]

    raw_expr = gnfa.get((new_start, new_accept), "∅")
    return simplify_regex(raw_expr)


# Legacy helper: checks whether text contains no regex special characters.
def looks_like_plain_english(text):
    regex_chars = set("()*+?|[]{}^$\\")
    return not any(c in regex_chars for c in text)

# Legacy helper: generates sample strings from regex.
def generate_strings_from_regex(regex, alphabet, max_len=6):
    from nfa_tools import nfa_to_dfa
    enfa = regex_to_nfa(regex, alphabet)
    dfa, _ = nfa_to_dfa(enfa)
    pos = []
    neg = []
    for length in range(max_len + 1):
        for combo in itertools.product(alphabet, repeat=length):
            word = "".join(combo)
            curr = dfa["start"]
            dead = False
            for sym in word:
                curr = dfa["transitions"].get((curr, sym), None)
                if curr is None:
                    dead = True
                    break
            if dead or curr not in dfa["accept"]:
                neg.append(word)
            else:
                pos.append(word)
    return {"pos": pos[:30], "neg": neg[:30]}
