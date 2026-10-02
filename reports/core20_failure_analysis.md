# Core-20 Failure Analysis Report

This report analyzes every failed episode from the empirical Core-20 benchmark evaluation across NVIDIA Nemotron Nano and NVIDIA Nemotron Super.

---

## 1. Summary of Failures

| Run ID | Model | Task ID | Steps | Final Action | Final Pass Rate | Assigned Category |
|---|---|---|---|---|---|---|
| `run1_nemotron_nano` | `nvidia/nemotron-3-nano-30b-a3b` | `t15_matrix_transpose` | 2 | `{"type": "submit"}` | 0.0% | **regression** |
| `run1_nemotron_nano` | `nvidia/nemotron-3-nano-30b-a3b` | `t16_lru_cache_eviction` | 2 | `{"type": "submit"}` | 0.0% | **regression** |
| `run1_nemotron_super` | `nvidia/nemotron-3-super-120b-a12b` | `t18_stateful_quote_lexer` | 5 | `{"type": "run", "cmd": "..."}` | 75.0% | **timeout/out of steps** |

---

## 2. In-Depth Diagnosis per Failed Episode

### Episode 1: `run1_nemotron_nano` on `t15_matrix_transpose`
- **Task ID:** `t15_matrix_transpose`
- **Steps:** 2
- **Final Action:** `{"type": "submit"}`
- **Pass Rate:** 0.0% (dropped from baseline 50.0%)
- **Category:** **regression**
- **Diagnosis:**
  In Step 1, Nemotron Nano generated logically sound matrix transpose code but serialized its file content with double-escaped literal `\n` characters instead of raw multi-line strings. When written into `matrix.py`, this compressed the file into an invalid single-line syntax payload. When the environment executed the pytest test suite, syntax errors broke the 2 baseline tests that had originally passed (dropping the pass rate from 50.0% to 0.0%). On Step 2, the agent immediately submitted without inspecting execution output, resulting in an automated regression penalty (-0.20) and a net return of -0.92.

### Episode 2: `run1_nemotron_nano` on `t16_lru_cache_eviction`
- **Task ID:** `t16_lru_cache_eviction`
- **Steps:** 2
- **Final Action:** `{"type": "submit"}`
- **Pass Rate:** 0.0% (dropped from baseline 66.7%)
- **Category:** **regression**
- **Diagnosis:**
  Similar to `t15`, the agent attempted to fix the LRU cache eviction ordering using `collections.OrderedDict`, but returned literal `\n` escape sequences in its edit payload. Writing this single-line string destroyed valid Python syntax in `cache.py`, causing all 3 test cases to fail (a regression from the 2/3 tests that initially passed). The agent then submitted blindly on Step 2 without running exploratory tests, triggering a regression penalty and finishing with a net return of -1.09.

### Episode 3: `run1_nemotron_super` on `t18_stateful_quote_lexer`
- **Task ID:** `t18_stateful_quote_lexer`
- **Steps:** 5
- **Final Action:** `{"type": "run", "cmd": "python3 -c \"import lexer; ...\""}`
- **Pass Rate:** 75.0% (improved from baseline 25.0%)
- **Category:** **timeout/out of steps**
- **Diagnosis:**
  In Step 1, Nemotron Super successfully refactored `lexer.py` to handle escaped quotes and whitespace tokenization, raising test pass rate from 25.0% to 75.0% (3 of 4 tests passing). However, during Steps 2 through 5, instead of making a final edit or submitting, the agent attempted to run custom verification scripts using bash-specific heredoc syntax (`cat << 'EOF'`) and `python3`, which failed on the local Windows shell. The agent exhausted its step budget (5 steps) while debugging its shell commands, and timed out before submitting its solution.

---

## 3. Ambiguity Assessment
- None of the failures were caused by ambiguous task specifications or flaky test suites (**0 ambiguous tasks**).
- All 20 Core tasks have unambiguous specifications and pass 100% under their deterministic reference fixes.
