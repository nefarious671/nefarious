# AGENTS.MD – Upgrade Roadmap for `nefarious` Recursive Agent

> **Goal**
> Transform the existing research‑assistant into a local “mini‑operating‑system” agent with multi‑step reasoning, an extensible command framework, and a transparent Streamlit UI.
> Changes are delivered in **phases** so that Copilot/Codex can apply them incrementally.

> **Changelog & Documentation**
> - After each change, append an entry to `CHANGELOG.md` summarizing the update and noting the current phase.
> - Include clear docstrings and comments so future agents can navigate the codebase.
> - Keep the user-facing `README.md` up to date as features are added.
- Maintain `JOURNAL.md` with notes or pain points discovered while implementing each phase. Future agents can consult this journal before starting new work.
- Agents may propose improvements or modifications to this roadmap and should update the relevant phase descriptions before implementing them.
- Review `laser_lens/outputs/GEMINIOUTPUT.md` for automated notes from Gemini. Use this file and `laser_lens/outputs/GEMINIINPUT.md` to exchange messages between agents. When new feedback appears, add a phase update here and record the timestamp below.

Last feedback synced: 2025-06-25 10:01 UTC

### Phase Status

| Phase | Status |
| ----- | ------ |
| 0 – Project Setup | ✅ Completed |
| 1 – Agent Reasoning Core | ✅ Completed |
| 2 – Command Framework Expansion | ✅ Completed |
| 3 – Streamlit UX | ✅ Completed |
| 4 – Hardening & Tests | ✅ Completed |
| 5 – Optional Enhancements | ✅ Completed |
| 6 – Context Overflow Handling | ✅ Completed |
| 7 – OS Awareness & Chunked Reading | ✅ Completed |
| 8 – File I/O Refinements | ✅ Completed |
| 9 – Transparency & Dry Run | ✅ Completed |
| 10 – Pause Messaging & UI Improvements | ✅ Completed |
| 11 – Extended HELP & Python Sandbox | ✅ Completed |
| 12 – Resume Rendering Fix | ✅ Completed |
| 13 – Documentation Overhaul | ✅ Completed |
| 14 – Improved EXEC Quoting | ✅ Completed |
| 15 – Pause Reason Display | ✅ Completed |
| 16 – Gemini API Key Management | ✅ Completed |
| 17 – UI Button Refresh | ☐ Proposed |

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
* Add `WORD_COUNT` command to report line and word counts.

## Phase 6 – Context Overflow Handling

When a single uploaded file is larger than `max_context_tokens`, the current
behaviour drops the entire buffer. Instead, implement graceful truncation.

1. Add `_truncate_large_file` helper in `context_manager.py`.
   - Keep the first and last portion of the file with a `...[truncated]...`
     marker so that length never exceeds the limit.
   - Log an `INFO` notice when truncation occurs.
2. Use this helper inside `upload_context` before storing the text.
3. Unit test that oversize files are truncated rather than discarded.
4. Document this behaviour in `README.md`.

> **Acceptance**: Uploading a huge file still results in a trimmed context
string returned by `get_context()`.

---

## Phase 7 – OS Awareness & Chunked Reading

1. **Persist truncated uploads**
   - When `_truncate_large_file` trims content, also save the full text to
     `outputs/` as `full_<name>` and mention this file in the stored buffer.
   - Provide a `READ_LINES` command so the agent can request specific line
     ranges from these files.
2. **HELP command & prompt update**
   - Add a `HELP` handler returning OS details and the registered command list.
   - Update the system prompt to explain that the agent operates inside a
     constrained OS and may issue `[[COMMAND: HELP]]` to review capabilities.
3. **Feedback loop**
   - Encourage agents to record OS review notes in `outputs/feedback.md` using
     existing write commands so future phases can improve the environment.

> **Acceptance**: Agent can call `HELP` for environment info and retrieve
lines from a saved oversize file using `READ_LINES`.

---

## Phase 8 – File I/O Refinements

Gemini testing revealed weaknesses when writing multi-line text and
verifying file contents. To make the sandbox more reliable:

1. **APPEND_FILE command**
   - Provide a handler that appends text to an existing file under
     `outputs/` without needing to `CAT` then `WRITE_FILE`.
2. **Improve WRITE_FILE**
   - Ensure any valid string (including newlines) is written intact.
3. **Truncation notices**
   - When CAT/READ_FILE output is shortened, prepend a warning describing
     the original and truncated size.
4. **Better error messages**
   - Surface which argument failed validation when command parsing or
     execution errors occur.

> **Acceptance**: Agent can reliably append to files and receives clear
warnings whenever output is truncated or parameters are invalid.

---

## Phase 9 – Transparency & Dry Run

Building on Gemini feedback, increase clarity and safety:

1. **Truncation warnings**
   - Whenever uploaded context or command output is shortened, prefix the text
     with `WARNING:` and include original vs truncated size.
2. **Detailed errors**
   - Return which argument failed validation when commands raise parsing errors.
3. **Dry run option**
   - Add `dry_run=True` parameter for `EXEC` and `WRITE_FILE` commands that
     prints the would-be action without executing.
4. **Tests & docs**
   - Unit tests cover dry run and warning behaviour. Document in README.

> **Acceptance**: Agent sees explicit truncation notices and can preview an
`EXEC` command using `dry_run`.

---

## Phase 10 – Pause Messaging & UI Improvements

Incorporate Gemini feedback on conversation flow:

1. **Pause/Cancel reasons**
   - `PAUSE` and `CANCEL` commands now require a `reason` argument.
   - UI buttons forward the text from the sidebar "Reason" field.
2. **Sidebar messaging**
   - When paused, a text box becomes enabled allowing the user to add
     short notes to the context.
3. **Collapsible loops**
   - Each loop’s output is rendered inside a collapsible expander with a
     one‑click copy button.

> **Acceptance**: User can pause the agent, send a note, and resume without
losing prior output.

---

## Phase 11 – Extended HELP & Python Sandbox

Gemini feedback proposes richer command assistance and the ability to run
Python code inside the sandbox.

1. **Detailed HELP**
   - `HELP` lists each command with its required and optional arguments and a
     short description.
2. **RUN_PYTHON command**
   - New handler executes provided Python code within `outputs/`.
3. **Sandbox environment**
   - Document how to create a virtual environment via `python -m venv .venv`
     and install requirements using `pip`.

> **Acceptance**: Agent can run Python snippets and consult enhanced HELP
output.

---

## Phase 12 – Resume Rendering Fix

When an agent resumes from a pause, the UI currently scrolls back to the top of
prior logs.

1. **Continuation**
   - Resume should continue rendering from the last output position instead of
     restarting the scroll at the beginning.

> **Acceptance**: Output picks up seamlessly after resuming.

---

## Phase 13 – Documentation Overhaul

Consolidate existing documentation into a formal docs site.

1. **Sphinx site**
   - Generate API documentation from docstrings under a new `docs/` folder.
   - Provide a short Makefile or script so `make html` builds the docs.
2. **Content reorganisation**
   - Move extended command descriptions out of `README.md` into the docs.
   - Link to generated docs from the README and UI footer.

> **Acceptance**: `make html` builds without warnings and README links to `/docs`.

---

## Phase 14 – Improved EXEC Quoting

Gemini feedback highlighted quoting problems when running ``EXEC`` commands on
Windows. The parser only accepted double quoted arguments which made nested
quotes difficult.

1. **Parser update**
   - ``CommandExecutor`` now accepts single- or double-quoted argument values.
2. **Docs**
   - README and ``docs/commands.rst`` include guidance on wrapping the ``cmd``
     value in single quotes when it contains double quotes.
3. **Tests**
   - Added unit test covering single-quoted arguments.


> **Acceptance**: ``[[COMMAND: EXEC cmd='echo "hi"']]`` executes successfully.

---

## Phase 15 – Pause Reason Display

UI feedback highlighted that reasons provided by ``PAUSE`` or ``CANCEL`` were
not shown after the agent triggered them. The input box in the sidebar now
displays the agent's reason in read-only mode and messages sent during a pause
are preserved for the next loop.

1. **UI Update**
   - ``ui_main.py`` disables the ``Reason`` field when a pause or cancel reason
     is present and shows that text.
2. **Inline Messages**
   - Added a test ensuring ``ContextManager.add_inline_context`` stores notes
     for later prompts.

> **Acceptance**: After pausing via ``[[COMMAND: PAUSE reason="break"]]`` the
> sidebar shows "break" and messages sent while paused appear in the next
> iteration.

---

## Phase 16 – Gemini API Key Management

Enable multiple Gemini API keys so users can switch between them in the UI.

1. **Key Storage**
   - Store keys with names and optional descriptions in a local file.
2. **UI Integration**
   - Dropdown to select a saved key before starting the agent.
   - "Add Key" button opens a popup to enter key value and description.

> **Acceptance**: UI lists existing keys and the agent uses the selected one.

---

## Phase 17 – UI Button Refresh

Update the sidebar control buttons for better usability.

1. **Layout**
   - Buttons should be larger square icons placed close together.
2. **Styling**
   - Remove borders and excess padding for a cleaner look.

> **Acceptance**: Sidebar buttons appear larger and evenly spaced.

---

## File‑by‑File TODO (cheat‑sheet for Copilot)

| Path                  | Touch? | Key edits                 |
| --------------------- | ------ | ------------------------- |
| `handlers.py`         | ✅      | add `EXEC`, alias map     |
| `recursive_agent.py`  | ✅      | prompt injection, history |
| `command_executor.py` | 🔄     | case‑insensitive lookup   |
| `ui_main.py`          | 🎨     | pause reason display      |
| `config.py`           | 🔄     | expose `SAFE_OUTPUT_DIR`  |
| `tests/test_exec.py`  | ➕      | new tests                 |
| `tests/test_inline_context.py` | ➕      | pause message test |

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
7. **Scope PRs Carefully** – When a feature request involves multiple large improvements, add them as new phases here instead of bundling everything into one PR.

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
