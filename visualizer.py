# visualizer.py - Draws any DFA, NFA or ε-NFA as a clear, textbook Graphviz DOT diagram.

# Returns the DOT source string for an automaton formatted like a classic TOC textbook diagram.
# Input:
#   automaton       - dict with keys: states, alphabet, start, accept, transitions
#   title           - string shown as the graph label
#   highlight_path  - optional list of state names visited during simulation (highlighted orange)
#   show_dead_state - bool, whether to include the 'dead' / trap state and its incident edges
# Output: DOT source string (pass to st.graphviz_chart)
def build_dot(automaton, title="", highlight_path=None, show_dead_state=False):
    all_states  = automaton.get("states", [])
    start       = automaton.get("start", "")
    accept_set  = set(automaton.get("accept", []))
    transitions = automaton.get("transitions", {})

    # Filter out dead state if show_dead_state is False
    if not show_dead_state:
        states = [s for s in all_states if s != "dead"]
    else:
        states = list(all_states)

    visited_states = set(highlight_path) if highlight_path else set()

    # Collect consecutive edges in highlight_path
    highlighted_edges = set()
    if highlight_path and len(highlight_path) >= 2:
        for i in range(len(highlight_path) - 1):
            highlighted_edges.add((highlight_path[i], highlight_path[i + 1]))

    # Merge transitions with the same (src, tgt)
    edge_labels = {}
    for (src, sym), targets in transitions.items():
        if not show_dead_state and src == "dead":
            continue
        target_list = targets if isinstance(targets, list) else [targets]
        for tgt in target_list:
            if not tgt:
                continue
            if not show_dead_state and tgt == "dead":
                continue
            key = (src, tgt)
            if key not in edge_labels:
                edge_labels[key] = []
            if sym not in edge_labels[key]:
                edge_labels[key].append(sym)

    # Sort labels cleanly, e.g. "0,1"
    def sort_labels(labels):
        normal = sorted([l for l in labels if l != "ε"])
        eps    = ["ε"] if "ε" in labels else []
        return ",".join(normal + eps)

    lines = []
    lines.append("digraph automaton {")
    lines.append('  rankdir=LR;')
    lines.append('  nodesep=0.8;')
    lines.append('  ranksep=1.2;')
    if title:
        lines.append(f'  graph [label="{title}" fontsize=18 labelloc=t fontname="Helvetica"];')
    lines.append('  node [fontname="Helvetica" fontsize=18 fixedsize=true width=0.9 penwidth=1.5];')
    lines.append('  edge [fontname="Helvetica" fontsize=16 arrowsize=1.1 penwidth=1.5];')

    # Invisible point node for the start arrow
    lines.append('  __start__ [shape=point style=invis width=0];')

    for state in states:
        is_dead   = (state == "dead")
        in_path   = state in visited_states
        is_accept = state in accept_set

        if is_dead:
            # Trap / dead state drawn lightly (grey, dashed)
            shape = "circle"
            style = "dashed,filled"
            fill  = "#F1F5F9"
            color = "#94A3B8"
            fontc = "#64748B"
        elif in_path:
            # Highlighted path state in orange
            shape = "doublecircle" if is_accept else "circle"
            style = "filled"
            fill  = "#FED7AA"
            color = "#EA580C"
            fontc = "#000000"
        elif is_accept:
            # Textbook accepting state: double circle + light green fill
            shape = "doublecircle"
            style = "filled"
            fill  = "#DCFCE7"
            color = "#16A34A"
            fontc = "#000000"
        else:
            # Normal textbook state: single circle, white fill, black border
            shape = "circle"
            style = "filled"
            fill  = "#FFFFFF"
            color = "#000000"
            fontc = "#000000"

        lines.append(
            f'  "{state}" [shape={shape} style="{style}" fillcolor="{fill}" '
            f'color="{color}" fontcolor="{fontc}" label="{state}"];'
        )

    # Start arrow from the left
    if start and (show_dead_state or start != "dead"):
        lines.append(f'  __start__ -> "{start}" [label="start" fontsize=13 color="#000000" penwidth=1.5];')

    # Add merged edges
    for (src, tgt), labels in edge_labels.items():
        combined = sort_labels(labels)
        is_dead_edge = (src == "dead" or tgt == "dead")
        
        if (src, tgt) in highlighted_edges:
            edge_color = "#EA580C"
            font_color = "#C2410C"
            penwidth   = "2.8"
            style      = "solid"
        elif is_dead_edge:
            edge_color = "#94A3B8"
            font_color = "#64748B"
            penwidth   = "1.2"
            style      = "dashed"
        else:
            edge_color = "#000000"
            font_color = "#000000"
            penwidth   = "1.5"
            style      = "solid"

        lines.append(
            f'  "{src}" -> "{tgt}" [label=" {combined} " color="{edge_color}" '
            f'fontcolor="{font_color}" penwidth={penwidth} style="{style}"];'
        )

    lines.append("}")
    return "\n".join(lines)


# Builds a textbook transition table as a list of row-dicts for use with st.dataframe.
# Rows = states (marked with → for start, * for accepting), Columns = symbols.
# Input: automaton (dict), show_dead_state (bool)
# Output: list of dicts
def build_table_rows(automaton, show_dead_state=False):
    all_states  = automaton.get("states", [])
    alphabet    = sorted(list(automaton.get("alphabet", [])))
    trans       = automaton.get("transitions", {})
    start       = automaton.get("start", "")
    accept_set  = set(automaton.get("accept", []))

    if not show_dead_state:
        states = [s for s in all_states if s != "dead"]
    else:
        states = list(all_states)

    rows = []
    for s in states:
        prefix = ""
        if s == start:
            prefix += "→ "
        if s in accept_set:
            prefix += "* "
        row = {"State": f"{prefix}{s}"}
        for sym in alphabet:
            tgt = trans.get((s, sym), None)
            if tgt is None:
                row[f"δ({sym})"] = "∅"
            elif isinstance(tgt, list):
                filtered = [t for t in tgt if show_dead_state or t != "dead"]
                row[f"δ({sym})"] = "{" + ", ".join(filtered) + "}" if filtered else "∅"
            else:
                if not show_dead_state and tgt == "dead":
                    row[f"δ({sym})"] = "∅"
                else:
                    row[f"δ({sym})"] = tgt
        # Include epsilon if present
        eps_targets = trans.get((s, "ε"), None)
        if eps_targets is not None:
            filtered_eps = [t for t in eps_targets if show_dead_state or t != "dead"]
            row["δ(ε)"] = "{" + ", ".join(filtered_eps) + "}" if filtered_eps else "∅"
        rows.append(row)
    return rows
