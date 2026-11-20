# app.py - Streamlit UI for the Formal Language Reverse Engineer
# Features active counterexample learning, clean DFA generation, and textbook diagrams.

import streamlit as st
import pandas as pd
import io

from learner     import validate_inputs, build_pta, merge_states_rpni, make_checker, learn_with_language
from nfa_tools   import nfa_to_dfa, dfa_to_nfa, dfa_to_enfa, simulate_nfa
from regex_tools import regex_to_nfa, dfa_to_regex, simplify_regex
from minimizer   import clean_dfa, minimize_dfa
from tester      import simulate_dfa, check_dfa_equivalence
from visualizer  import build_dot, build_table_rows

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Formal Language Reverse Engineer",
    page_icon="🔍",
    layout="wide"
)

# ── Session state defaults ────────────────────────────────────────────────────
for key, default in [
    ("alphabet",       ["0", "1"]),
    ("pos_examples",   []),
    ("neg_examples",   []),
    ("raw_dfa",        None),
    ("dfa",            None),        # Cleaned, minimized canonical DFA
    ("has_dead_state", False),
    ("merge_log",      []),
    ("lang_desc",      ""),
    ("verify_status",  ""),
    ("is_verified",    False),
    ("input_alphabet", "0, 1"),
    ("input_pos",      ""),
    ("input_neg",      ""),
    ("input_lang",     "binary strings divisible by 3"),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Helpers ───────────────────────────────────────────────────────────────────

# Builds verification table showing how the DFA classifies each sample.
def build_verification_table(dfa, pos_list, neg_list):
    rows = []
    # Show up to 30 positive samples
    for w in pos_list[:30]:
        acc, _, _, _ = simulate_dfa(dfa, w)
        rows.append({
            "String":   f"'{w}'" if w != "" else "ε (empty string)",
            "Label":    "positive (accepted)",
            "DFA":      "ACCEPT" if acc else "REJECT",
            "Correct?": "✅" if acc else "❌"
        })
    # Show up to 30 negative samples
    for w in neg_list[:30]:
        acc, _, _, _ = simulate_dfa(dfa, w)
        rows.append({
            "String":   f"'{w}'" if w != "" else "ε (empty string)",
            "Label":    "negative (rejected)",
            "DFA":      "ACCEPT" if acc else "REJECT",
            "Correct?": "✅" if not acc else "❌"
        })
    return pd.DataFrame(rows)


# Renders the formal 5-tuple specification box for a DFA.
def render_5tuple_box(dfa, show_dead=False):
    all_states = dfa.get("states", [])
    states = [s for s in all_states if show_dead or s != "dead"]
    q_str = "{" + ", ".join(states) + "}"
    sigma_str = "{" + ", ".join(dfa.get("alphabet", [])) + "}"
    start_str = dfa.get("start", "")
    f_str = "{" + ", ".join(dfa.get("accept", [])) + "}"
    
    st.markdown(
        f"""
        > **Formal 5-Tuple Specification:**  
        > $M = (Q, \\Sigma, \\delta, q_0, F)$  
        > - $Q = {q_str}$  
        > - $\\Sigma = {sigma_str}$  
        > - $\\delta$: state transition function (see table below)  
        > - $q_0 = {start_str}$  
        > - $F = {f_str}$  
        """
    )


# ── Header ────────────────────────────────────────────────────────────────────
st.title("🔍 Formal Language Reverse Engineer")

caption = "Theory of Computation — Regular Language Inference & Automata Analysis"
if st.session_state.lang_desc:
    caption += f"  |  Language: *{st.session_state.lang_desc}*"
st.caption(caption)

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "1. Input",
    "2. DFA Engineering",
    "3. NFA",
    "4. ε-NFA",
    "5. Regex",
    "6. String Testing",
    "7. Comparison",
])

# ==============================================================================
# TAB 1 — INPUT
# ==============================================================================
with tab1:
    st.subheader("Language Specification & Training Samples")

    col_eg1, col_eg2 = st.columns(2)
    with col_eg1:
        if st.button("📥 Load 'Divisible by 3' Example"):
            st.session_state.input_alphabet = "0, 1"
            st.session_state.input_pos      = ""
            st.session_state.input_neg      = ""
            st.session_state.input_lang     = "binary strings divisible by 3"
            st.rerun()
    with col_eg2:
        if st.button("📥 Load '01, 101, 1101' Example"):
            st.session_state.input_alphabet = "0, 1"
            st.session_state.input_pos      = "01, 101, 1101"
            st.session_state.input_neg      = "10, 111, 100"
            st.session_state.input_lang     = ""
            st.rerun()

    c1, c2, c3 = st.columns(3)
    with c1:
        alphabet_in = st.text_input(
            "Alphabet Σ (comma or space-separated):",
            value=st.session_state.input_alphabet
        )
    with c2:
        pos_in = st.text_area(
            "Positive strings S⁺ (accepted):",
            value=st.session_state.input_pos, height=110,
            placeholder="e.g. 01, 101, 1101"
        )
    with c3:
        neg_in = st.text_area(
            "Negative strings S⁻ (rejected):",
            value=st.session_state.input_neg, height=110,
            placeholder="e.g. 10, 111, 100"
        )

    lang_in = st.text_input(
        "Language (optional) — e.g. binary strings divisible by 3, (0|1)*01, ends with 01, even number of 0s:",
        value=st.session_state.input_lang,
        placeholder="e.g. binary strings divisible by 3"
    )

    if st.button("🚀 Validate & Learn DFA", type="primary"):
        # Parse inputs
        raw_alpha = [s.strip() for s in alphabet_in.replace(",", " ").split() if s.strip()]
        alpha = sorted(list(set(raw_alpha)))
        if not alpha:
            st.error("Empty alphabet. Please enter at least one symbol (e.g. 0, 1).")
            st.stop()

        checker, lang_desc = make_checker(lang_in, alpha)

        # Validate manual examples if provided
        pos_list = [s.strip() for s in pos_in.replace(",", " ").replace("\n", " ").split() if s.strip()]
        neg_list = [s.strip() for s in neg_in.replace(",", " ").replace("\n", " ").split() if s.strip()]

        if pos_list or neg_list:
            alpha_v, p_v, n_v, err = validate_inputs(alphabet_in, pos_in, neg_in)
            if err:
                st.error(err)
                st.stop()
            pos_list, neg_list = p_v, n_v

        # Learn with checker or manually
        if checker:
            st.caption(f"Language understood: {lang_desc}")
            cleaned_dfa, merge_log, verify_status, is_verified, trained_pos, trained_neg = learn_with_language(
                alpha, checker, pos_list, neg_list
            )
            raw_dfa = cleaned_dfa
            has_dead = ("dead" in cleaned_dfa["states"])
            final_pos = trained_pos
            final_neg = trained_neg
        else:
            if lang_in.strip():
                st.warning("Could not understand this language, learning from your examples only")
            if not pos_list:
                st.error("Please enter at least one positive string, or specify a valid Language.")
                st.stop()
            
            pta = build_pta(alpha, pos_list)
            raw_dfa, merge_log = merge_states_rpni(pta, pos_list, neg_list)
            cleaned_dfa, has_dead = clean_dfa(raw_dfa, pos_list, neg_list)
            verify_status = "Learned from provided training examples"
            is_verified = True
            final_pos = pos_list
            final_neg = neg_list
            lang_desc = ""

        # Update session state
        st.session_state.alphabet       = alpha
        st.session_state.pos_examples   = final_pos
        st.session_state.neg_examples   = final_neg
        st.session_state.raw_dfa        = raw_dfa
        st.session_state.dfa            = cleaned_dfa
        st.session_state.has_dead_state = has_dead
        st.session_state.merge_log      = merge_log
        st.session_state.lang_desc      = lang_desc
        st.session_state.verify_status  = verify_status
        st.session_state.is_verified    = is_verified
        st.session_state.input_alphabet = alphabet_in
        st.session_state.input_pos      = pos_in
        st.session_state.input_neg      = neg_in
        st.session_state.input_lang     = lang_in

        non_dead_count = len([s for s in cleaned_dfa["states"] if s != "dead"])
        st.success(f"✅ Learned DFA has **{non_dead_count}** states (after minimization).")

        if checker:
            if is_verified:
                st.success(f"🟢 {verify_status}")
            else:
                st.error(f"🔴 {verify_status}")

# ==============================================================================
# TAB 2 — DFA ENGINEERING (Textbook Drawing & 5-Tuple Box)
# ==============================================================================
with tab2:
    st.subheader("Learned Canonical DFA")

    if st.session_state.dfa is None:
        st.info("Please go to Tab 1, fill in the inputs, and click **Validate & Learn DFA**.")
    else:
        dfa = st.session_state.dfa
        non_dead_count = len([s for s in dfa["states"] if s != "dead"])
        st.write(f"Learned DFA has **{non_dead_count}** states (after minimization).")

        if st.session_state.verify_status:
            if st.session_state.is_verified:
                st.success(f"🟢 {st.session_state.verify_status}")
            else:
                st.error(f"🔴 {st.session_state.verify_status}")

        show_dead = False
        if st.session_state.has_dead_state:
            show_dead = st.checkbox("Show dead state (trap state)", value=False, key="toggle_dead_tab2")
            if not show_dead:
                st.caption("ℹ️ Missing arrows go to the dead state.")

        dot_src = build_dot(dfa, title="Learned DFA", show_dead_state=show_dead)
        st.graphviz_chart(dot_src, use_container_width=True)

        st.download_button(
            "💾 Download Diagram (DOT Source)",
            data=dot_src,
            file_name="learned_dfa.dot",
            mime="text/vnd.graphviz"
        )

        st.divider()

        # Regular expression representation
        try:
            desc_regex = dfa_to_regex(dfa)
            st.markdown(f"### 🎯 Language Recognized: `{desc_regex}`")
            if len(desc_regex) > 80:
                st.caption("Equivalent but not minimal regex")
        except Exception:
            pass

        render_5tuple_box(dfa, show_dead=show_dead)

        st.markdown("#### Transition Table")
        st.dataframe(pd.DataFrame(build_table_rows(dfa, show_dead_state=show_dead)), use_container_width=True)

        st.divider()

        # Merge log
        st.markdown("#### State Merging Log (RPNI)")
        if st.session_state.merge_log:
            st.dataframe(pd.DataFrame(st.session_state.merge_log), use_container_width=True)

        st.divider()

        # Verification table
        st.markdown("#### Training Set Verification")
        vdf = build_verification_table(
            dfa,
            st.session_state.pos_examples,
            st.session_state.neg_examples
        )
        def highlight_wrong(row):
            if row["Correct?"] == "❌":
                return ["background-color: #FFCCCC"] * len(row)
            return [""] * len(row)

        st.dataframe(vdf.style.apply(highlight_wrong, axis=1), use_container_width=True)

# ==============================================================================
# TAB 3 — NFA
# ==============================================================================
with tab3:
    st.subheader("NFA — Automatically Generated from Learned DFA")
    st.write("Constructed by wrapping deterministic transition targets into singleton sets.")

    if st.session_state.dfa is None:
        st.info("Learn a DFA in Tab 1 first.")
    else:
        nfa = dfa_to_nfa(st.session_state.dfa)
        show_dead_nfa = False
        if st.session_state.has_dead_state:
            show_dead_nfa = st.checkbox("Show dead state", value=False, key="toggle_dead_nfa")

        st.graphviz_chart(build_dot(nfa, title="NFA (from Cleaned DFA)", show_dead_state=show_dead_nfa), use_container_width=True)
        st.dataframe(pd.DataFrame(build_table_rows(nfa, show_dead_state=show_dead_nfa)), use_container_width=True)

        st.divider()
        st.markdown("#### Subset Construction Round-Trip (NFA ➔ DFA)")
        back_dfa, conv_table = nfa_to_dfa(nfa)
        st.graphviz_chart(build_dot(back_dfa, title="DFA from NFA (Subset Construction)"), use_container_width=True)
        st.dataframe(pd.DataFrame(conv_table), use_container_width=True)

        is_eq, _, _ = check_dfa_equivalence(st.session_state.dfa, back_dfa)
        if is_eq:
            st.success("✅ Equivalence confirmed: L(DFA) ≡ L(NFA ➔ DFA).")

# ==============================================================================
# TAB 4 — ε-NFA
# ==============================================================================
with tab4:
    st.subheader("ε-NFA — Automatically Generated from Learned DFA")
    st.write("Constructed by adding fresh `s_new` and `f_new` connected via $\\varepsilon$-transitions.")

    if st.session_state.dfa is None:
        st.info("Learn a DFA in Tab 1 first.")
    else:
        enfa = dfa_to_enfa(st.session_state.dfa)
        show_dead_enfa = False
        if st.session_state.has_dead_state:
            show_dead_enfa = st.checkbox("Show dead state", value=False, key="toggle_dead_enfa")

        st.graphviz_chart(build_dot(enfa, title="ε-NFA (from Cleaned DFA)", show_dead_state=show_dead_enfa), use_container_width=True)
        st.dataframe(pd.DataFrame(build_table_rows(enfa, show_dead_state=show_dead_enfa)), use_container_width=True)

        st.divider()
        st.markdown("#### Subset Construction with ε-Closure Round-Trip")
        back_dfa2, conv_table2 = nfa_to_dfa(enfa)
        st.graphviz_chart(build_dot(back_dfa2, title="DFA from ε-NFA"), use_container_width=True)
        st.dataframe(pd.DataFrame(conv_table2), use_container_width=True)

        is_eq2, _, _ = check_dfa_equivalence(st.session_state.dfa, back_dfa2)
        if is_eq2:
            st.success("✅ Equivalence confirmed: L(DFA) ≡ L(ε-NFA ➔ DFA).")

# ==============================================================================
# TAB 5 — REGEX
# ==============================================================================
with tab5:
    st.subheader("Regular Expressions")

    reg_sub1, reg_sub2 = st.tabs([
        "DFA → Regular Expression",
        "Regex → ε-NFA (Thompson's Construction)"
    ])

    with reg_sub1:
        st.markdown("#### State Elimination Algorithm")
        if st.session_state.dfa is None:
            st.info("Learn a DFA in Tab 1 first.")
        else:
            regex_result = dfa_to_regex(st.session_state.dfa)
            st.success(f"**Simplified Regular Expression:** `{regex_result}`")
            if len(regex_result) > 80:
                st.caption("Equivalent but not minimal regex")
            st.download_button("💾 Download Regex (.txt)", data=regex_result, file_name="language_regex.txt", mime="text/plain")

    with reg_sub2:
        st.markdown("#### Thompson's Structural Construction")
        regex_input = st.text_input("Enter regex (supports |, *, concatenation, parentheses):", value="(0|1)*01")
        if st.button("Build ε-NFA from Regex"):
            try:
                t_nfa = regex_to_nfa(regex_input)
                st.success(f"Built Thompson ε-NFA with {len(t_nfa['states'])} state(s).")
                st.graphviz_chart(build_dot(t_nfa, title=f"Thompson ε-NFA for '{regex_input}'"), use_container_width=True)
                st.dataframe(pd.DataFrame(build_table_rows(t_nfa)), use_container_width=True)
            except Exception as exc:
                st.error(f"Could not parse regex: {exc}")

# ==============================================================================
# TAB 6 — STRING TESTING (Textbook Highlighting)
# ==============================================================================
with tab6:
    st.subheader("Interactive String Testing & Execution Tracer")

    if st.session_state.dfa is None:
        st.info("Learn a DFA in Tab 1 first.")
    else:
        test_word = st.text_input("Enter a string to test:", value="10101", key="test_word")
        dfa = st.session_state.dfa

        acc, steps, path_str, last_state = simulate_dfa(dfa, test_word)
        st.metric("Test Result", "ACCEPTED ✅" if acc else "REJECTED ❌", delta=f"Ended at state: {last_state}")

        def get_path_nodes(dfa, word):
            curr = dfa["start"]
            nodes = [curr]
            for sym in word:
                nxt = dfa["transitions"].get((curr, sym))
                if nxt is None:
                    break
                nodes.append(nxt)
                curr = nxt
            return nodes

        path_nodes = get_path_nodes(dfa, test_word)
        hit_dead = ("dead" in path_nodes)
        
        show_dead_test = False
        if st.session_state.has_dead_state:
            show_dead_test = st.checkbox("Show dead state", value=hit_dead, key="toggle_dead_test")

        st.markdown("#### Execution Path on Diagram (orange = visited)")
        dot_path = build_dot(dfa, title=f"Trace for '{test_word}'", highlight_path=path_nodes, show_dead_state=show_dead_test)
        st.graphviz_chart(dot_path, use_container_width=True)

        st.markdown("#### Step-by-Step Transition Sequence")
        st.code(path_str, language="text")
        st.dataframe(pd.DataFrame(steps), use_container_width=True)

# ==============================================================================
# TAB 7 — COMPARISON
# ==============================================================================
with tab7:
    st.subheader("Structural Comparison & Language Equivalence")

    if st.session_state.dfa is None or st.session_state.raw_dfa is None:
        st.info("Learn a DFA in Tab 1 first.")
    else:
        raw_dfa = st.session_state.raw_dfa
        cleaned_dfa = st.session_state.dfa

        is_eq, _, reason = check_dfa_equivalence(raw_dfa, cleaned_dfa)
        if is_eq:
            st.success(f"✅ State-Merged DFA ≡ Cleaned Canonical DFA — {reason}")

        metrics = [
            {
                "Model": "Raw Merged DFA",
                "States": len(raw_dfa["states"]),
                "Transitions": len(raw_dfa["transitions"]),
                "Accepting States": len(raw_dfa["accept"]),
                "Start": raw_dfa["start"]
            },
            {
                "Model": "Cleaned Canonical DFA",
                "States": len([s for s in cleaned_dfa["states"] if s != "dead"]),
                "Transitions": len(cleaned_dfa["transitions"]),
                "Accepting States": len(cleaned_dfa["accept"]),
                "Start": cleaned_dfa["start"]
            }
        ]
        st.dataframe(pd.DataFrame(metrics), use_container_width=True)

        c_d1, c_d2 = st.columns(2)
        with c_d1:
            st.markdown("#### Raw Merged DFA")
            st.graphviz_chart(build_dot(raw_dfa, title="Raw Merged DFA"), use_container_width=True)
        with c_d2:
            st.markdown("#### Cleaned Canonical DFA")
            st.graphviz_chart(build_dot(cleaned_dfa, title="Cleaned Canonical DFA"), use_container_width=True)
