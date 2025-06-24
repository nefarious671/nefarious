# AGENTS.MD – Upgrade Roadmap for `nefarious` Recursive Agent

> **Goal**
> Transform the existing research‑assistant into a local “mini‑operating‑system” agent with multi‑step reasoning, an extensible command framework, and a transparent Streamlit UI.
> Changes are delivered in **phases** so that Copilot/Codex can apply them incrementally.

> **Changelog & Documentation**
> - After each change, append an entry to `CHANGELOG.md` summarizing the update and noting the current phase.
> - Include clear docstrings and comments so future agents can navigate the codebase.
> - Keep the user-facing `README.md` up to date as features are added.
> - Maintain `JOURNAL.md` with notes or pain points discovered while implementing each phase. Future agents can consult this journal before starting new work.

---

## 📋 Prerequisites

| Requirement                  | Minimum Version     |
| ---------------------------- | ------------------- |
| Python                       | 3.9+                |
| Streamlit                    | ^1.33               |
| openai / google‑generativeai | latest              |
| OS                           | Linux/macOS/Windows |

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your API key
```

---

## Phase 0 – Project Setup  (≈1 PR)

1. **Create feature branch** `feat/recursive-os-agent`.
2. Ensure `config.py` exposes a single constant `SAFE_OUTPUT_DIR = Path("outputs")`.
3. Add `requirements.txt` with pinned libs.
4. Add `pytest` & `ruff` for lint/tests.

> **Acceptance**: Project runs `pytest -q` with dummy test & `streamlit run ui_main.py` still launches unchanged UI.

---

## Phase 1 – Agent Reasoning Core  (≈2 PRs)

### 1‑A. Inject command outputs into next prompt

* **File**: `recursive_agent.py`
* **Change**: In `_build_prompt`, append a **Tool Outputs** section formed from `agent_state.get_state("command_results")`.

```python
tool_context = "\n".join(f"◦ {n}: {r[:500]}" for n,r in results)
prompt_parts.append(f"\n\n## Tool Outputs\n{tool_context}")
```

### 1‑B. Persist loop history

* Keep last N loop thoughts in `agent_state["history"]` (deque).
* Include trimmed history in prompt.

> **Acceptance**: A test script issues `LS` → `CAT file.txt` in consecutive loops without user intervention.

---

## Phase 2 – Command Framework Expansion  (≈3 PRs)

### 2‑A. Add Sandbox `EXEC` Command

* **File**: `handlers.py`
* Use `subprocess.run([...], cwd=SAFE_OUTPUT_DIR, timeout=10, capture_output=True, text=True)`.
* Block dangerous patterns (`sudo`, `rm -rf /`, outbound network).

### 2‑B. Alias Commands for OS‑feel

| Alias | Existing Handler |
| ----- | ---------------- |
| `LS`  | `LIST_OUTPUTS`   |
| `CAT` | `READ_FILE`      |
| `RM`  | `DELETE_FILE`    |

```python
# command_registration.py
for alias, target in {"LS": "LIST_OUTPUTS", "CAT": "READ_FILE", "RM": "DELETE_FILE"}.items():
    ce.register_command(alias, ce._registry[target])
```

> **Acceptance**: Agent can emit `[[COMMAND: LS]]` and receive file list.

---

## Phase 3 – Streamlit UX  (≈2 PRs)

* **Intercept** command markers before render.
* Replace with:

```python
st.info(f"▶ {cmd_name} {arg_str}")
st.code(result, language="bash")
```

* Auto‑scroll to newest output (`st.experimental_rerun` hack).
* Enable **Download** button for final markdown.

> **Acceptance**: User sees separate blocks for thoughts vs. command results.

---

## Phase 4 – Hardening & Tests  (≈1 PR)

1. **Unit tests** for `sanitize_filename`, `EXEC` timeout.
2. **Doc**: Update `README.md` with new commands table.
3. **CI**: GitHub Actions running `ruff`, `pytest`.

---

## Phase 5 – Optional Enhancements

* CLI parity with UI (pretty printing tool output).
* Persist session metadata in `outputs/session.json`.
* Plug‑in support for user‑defined commands via entry‑points.

---

## File‑by‑File TODO (cheat‑sheet for Copilot)

| Path                  | Touch? | Key edits                 |
| --------------------- | ------ | ------------------------- |
| `handlers.py`         | ✅      | add `EXEC`, alias map     |
| `recursive_agent.py`  | ✅      | prompt injection, history |
| `command_executor.py` | 🔄     | case‑insensitive lookup   |
| `ui_main.py`          | 🎨     | command/output panes      |
| `config.py`           | 🔄     | expose `SAFE_OUTPUT_DIR`  |
| `tests/test_exec.py`  | ➕      | new tests                 |

---

## 📚 Documentation & Testing Strategy

To keep each phase manageable, follow this iterative workflow:

1. **Docstrings & Comments** – Every new function or class must include a
   docstring summarising its purpose and arguments. Inline comments should
   explain any non‑obvious logic.
2. **Changelog Updates** – After completing a phase task, append a bullet to
   `CHANGELOG.md` describing the change and noting the phase number.
3. **Tests** – Add or extend `tests/` with unit tests for new behaviour. Use
   `pytest` for execution and `ruff` for style checking. Aim to gradually raise
   coverage so phase‑4 can reach 80 %.
4. **Simulation** – If direct access to agents or models is unavailable, mock or simulate their behaviour in tests to validate logic.
5. **Automation** – Future PRs should include a minimal GitHub Actions workflow
   running `ruff` and `pytest -q`. This keeps the feedback loop automatic.
6. **README** – Document any user‑visible commands or UI changes so the next
   agent has up‑to‑date instructions.

This process ensures every phase is reviewable and that regressions are caught
early.

---

### Commit Message Template

```
feat(agent): phase 1‑A – inject tool outputs into prompt

* Append previous loop’s command results to context
* Maintain circular history of last 3 agent thoughts
* Verified with dummy READ/WRITE loop
```

> Repeat template for each task. Keep commits small & revert‑friendly.

---

## 🎉 Completion Criteria

* Agent demonstrates chained reasoning in demo topic.
* All commands restricted to `outputs/`.
* UI shows real‑time command logs & outputs.
* `pytest` passes with coverage ≥ 80 %.
