# Formal Language Reverse Engineer

A Theory of Computation (TOC) interactive web app that infers a DFA from positive and negative string examples, then lets you convert, minimize, visualize, test, and compare automata.

## 🚀 Quick Start

```bash
# 1. Navigate to the project folder
cd formal_language_reverse_engineer

# 2. Install required packages
pip install -r requirements.txt

# 3. Launch the app
streamlit run app.py
```

The browser opens automatically at `http://localhost:8501`

---

## 📂 File-by-File Explanation

| File | Role | Key Algorithm |
|------|------|---------------|
| `app.py` | Streamlit UI — 8 tabs, session state, tables, downloads | Layout & navigation |
| `learner.py` | Validates input, builds PTA, merges states | RPNI (Anguin/Oncina-style) + Union-Find |
| `nfa_tools.py` | Parses NFA text, simulates, converts to DFA | ε-closure, Subset / Powerset Construction |
| `regex_tools.py` | Regex ↔ ε-NFA and DFA → Regex | Thompson's Construction + State Elimination (GNFA) |
| `minimizer.py` | Removes dead states, minimizes DFA | Partition Refinement (Hopcroft / Moore) |
| `tester.py` | Step-by-step simulation + equivalence check | BFS on Product Automaton |
| `visualizer.py` | Draws any automaton as a figure | NetworkX + Matplotlib |
| `test_logic.py` | Unit tests verifying all modules | Runs without Streamlit |

---

## 🔬 Algorithm Descriptions (Simple Language)

### 1. `learner.py` — PTA & State Merging
1. **Build PTA:** Every prefix of every accepted string becomes a state. Accepted strings end in accepting states. This creates a tree-shaped automaton that correctly accepts all positive examples.
2. **RPNI Merging:** Try merging pairs of states (from smaller states to larger). After each merge, fold the DFA to stay deterministic. Keep the merge only if no negative string is now accepted. Use Union-Find data structure to efficiently track which states are grouped together.

### 2. `nfa_tools.py` — Subset Construction
1. **ε-closure:** From a set of NFA states, follow all ε (epsilon) transitions to find all reachable states without consuming any symbol.
2. **Subset Construction:** Each DFA state represents a *set* of NFA states. Start with ε-closure(start). For each symbol, compute the new set of NFA states reachable via that symbol + ε-closure. Mark as accepting any DFA state whose NFA subset contains an NFA accepting state.

### 3. `regex_tools.py` — Thompson's Construction & State Elimination
1. **Thompson's Construction:** Converts regex to ε-NFA using recursive rules: a literal `a` → two states with an `a` edge; `r|s` → new start/accept connected to both sub-NFAs via ε; `r.s` → chain via ε; `r*` → loop via ε and bypass.
2. **State Elimination:** Add global start and accept, then delete intermediate DFA states one by one, encoding path labels as compound regex expressions on the remaining edges.

### 4. `minimizer.py` — Partition Refinement
Begin with two equivalence classes: accepting and non-accepting states. Iteratively split each class when two states have transitions on the same symbol that lead to *different* classes. Repeat until no more splits occur. Each final class becomes one minimized state.

### 5. `tester.py` — Product Automaton Equivalence
To check if L(M1) = L(M2), simulate both DFAs in parallel. Each state is a pair (s1, s2). If a reachable pair has one state accepting and the other rejecting, the languages differ (the word that led to that pair is a counterexample).

---

## 🧪 Verified Test Case

| Input | Alphabet: {0, 1} |
|-------|-----------------|
| Positive S⁺ | `01`, `101`, `1101` |
| Negative S⁻ | `10`, `111`, `100` |

**Result:** Learned DFA has **3 states**. All positive strings accepted, all negative strings rejected. Minimized DFA is equivalent.

The inferred pattern is: strings ending in `...01` (number of leading `1`s followed by `01`).

---

## 🎓 Viva Questions & Short Answers

**Q1. What is a DFA? How is it represented in your code?**
> A Deterministic Finite Automaton has one unique next state for every (state, symbol) pair. In code it's a plain Python dict: `{"states": [...], "alphabet": [...], "start": "q0", "accept": [...], "transitions": {("q0","a"): "q1", ...}}`.

**Q2. What is the difference between a DFA and an NFA?**
> In a DFA, each state has exactly one transition per symbol. In an NFA, a state can have zero, one, or many transitions per symbol, plus ε-transitions that consume no input. Both recognise the same set of languages (regular languages).

**Q3. What is a Prefix Tree Acceptor (PTA)?**
> A PTA is a tree-shaped DFA where every unique prefix of every accepted string is a separate state. It correctly accepts all positive training examples but is usually far too large. It is the starting point for RPNI merging.

**Q4. How does RPNI state merging work?**
> We try merging pairs of states in a fixed order. After each merge we "fold" the automaton to restore determinism (by forcing states that now have conflicting transitions to merge too). We keep the merge only if no negative example is accepted. This is essentially greedy generalisation.

**Q5. What is Subset (Powerset) Construction?**
> It converts an NFA into an equivalent DFA. Each DFA state represents a *set* of NFA states. Starting from ε-closure(start), we compute transitions for every symbol until no new DFA states appear. If the DFA subset contains any NFA accepting state, the DFA state is accepting.

**Q6. What is Thompson's Construction?**
> An algorithm to convert a regular expression into an ε-NFA by applying structural rules: each atom gets two states, alternation `|` adds a new start/accept connected by ε, concatenation chains two NFAs via ε, and Kleene star `*` adds an ε bypass and loop.

**Q7. Why minimize a DFA? What theorem guarantees a unique minimal DFA?**
> Minimisation reduces the number of states, making the automaton more efficient and revealing the canonical structure. The **Myhill–Nerode Theorem** guarantees that for every regular language there exists a unique minimal DFA (up to state renaming).

**Q8. How does the product automaton prove language equivalence?**
> Simulate two DFAs in parallel: states are pairs (s1, s2). If any reachable pair has one side accepting and the other rejecting, the word leading there is a counterexample and L(M1) ≠ L(M2). If no such pair is found, L(M1) = L(M2).

---

## 📦 Requirements

```
streamlit>=1.30.0
networkx>=3.0
matplotlib>=3.7.0
pandas>=2.0.0
```
