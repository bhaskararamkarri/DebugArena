# DebugArena Expert Review Pack (Tendem / Toloka)

This review package contains AI-generated coding agent bug fixes for human expert quality assessment.
Please review each episode and score it based on correctness, idiomacy, and side effects.

---

## Episode 1: `t01_off_by_one` [EASY]
**Task ID:** `t01_off_by_one`  
**Model:** `nvidia/llama-3.1-nemotron-nano-4b-instruct`  
**Episode ID:** `ep_0001`  
**Pass Rate:** `100%` (automated tests passed)  

### 1. Problem Description
> sum_range(a, b) should return the sum of all integers from a to b inclusive, but it currently excludes b.

### 2. Original Buggy File
```py
def sum_range(a: int, b: int) -> int:
    """Return the sum of integers from a to b inclusive."""
    if a > b:
        return 0
    return sum(range(a, b))
```

### 3. Agent Fix Diff
```diff
--- a/mathutils.py (buggy)
+++ b/mathutils.py (agent fix)
@@ -2,4 +2,4 @@
     """Return the sum of integers from a to b inclusive."""
     if a > b:
         return 0
-    return sum(range(a, b))
+    return sum(range(a, b + 1))
```

### 4. Expert Review Questions
- **Q1 - Correctness:** Does this fix address the root cause correctly? `[ ] Yes  [ ] No`
- **Q2 - Idiomatic Style:** Is the fix clean, pythonic, and readable? `[ ] Yes  [ ] No`
- **Q3 - Side Effects:** Does this introduce performance or safety regressions? `[ ] Yes  [ ] No`
- **Q4 - Score (1 to 5):** `[ ]` (1=Broken, 2=Hacky, 3=Suboptimal, 4=Clean, 5=Exemplary)
- **Q5 - Comments / Rationale:** `[                                                ]`

---

## Episode 2: `t02_wrong_operator` [EASY]
**Task ID:** `t02_wrong_operator`  
**Model:** `nvidia/llama-3.1-nemotron-nano-4b-instruct`  
**Episode ID:** `ep_0002`  
**Pass Rate:** `100%` (automated tests passed)  

### 1. Problem Description
> filter_passing_scores(scores, threshold) should return all scores that are greater than or equal to threshold, but it strictly filters out scores equal to threshold.

### 2. Original Buggy File
```py
def filter_passing_scores(scores: list[int], threshold: int = 50) -> list[int]:
    """Filter scores >= threshold."""
    return [s for s in scores if s > threshold]
```

### 3. Agent Fix Diff
```diff
--- a/grader.py (buggy)
+++ b/grader.py (agent fix)
@@ -1,3 +1,3 @@
 def filter_passing_scores(scores: list[int], threshold: int = 50) -> list[int]:
     """Filter scores >= threshold."""
-    return [s for s in scores if s > threshold]
+    return [s for s in scores if s >= threshold]
```

### 4. Expert Review Questions
- **Q1 - Correctness:** Does this fix address the root cause correctly? `[ ] Yes  [ ] No`
- **Q2 - Idiomatic Style:** Is the fix clean, pythonic, and readable? `[ ] Yes  [ ] No`
- **Q3 - Side Effects:** Does this introduce performance or safety regressions? `[ ] Yes  [ ] No`
- **Q4 - Score (1 to 5):** `[ ]` (1=Broken, 2=Hacky, 3=Suboptimal, 4=Clean, 5=Exemplary)
- **Q5 - Comments / Rationale:** `[                                                ]`

---

## Episode 3: `t03_wrong_return` [EASY]
**Task ID:** `t03_wrong_return`  
**Model:** `nvidia/llama-3.1-nemotron-nano-4b-instruct`  
**Episode ID:** `ep_0003`  
**Pass Rate:** `100%` (automated tests passed)  

### 1. Problem Description
> factorial(n) returns 0 for n == 0 instead of 1.

### 2. Original Buggy File
```py
def factorial(n: int) -> int:
    """Return n factorial."""
    if n < 0:
        raise ValueError('Negative values not allowed')
    if n == 0:
        return 0
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result
```

### 3. Agent Fix Diff
```diff
--- a/factorials.py (buggy)
+++ b/factorials.py (agent fix)
@@ -3,7 +3,7 @@
     if n < 0:
         raise ValueError('Negative values not allowed')
     if n == 0:
-        return 0
+        return 1
     result = 1
     for i in range(1, n + 1):
         result *= i
```

### 4. Expert Review Questions
- **Q1 - Correctness:** Does this fix address the root cause correctly? `[ ] Yes  [ ] No`
- **Q2 - Idiomatic Style:** Is the fix clean, pythonic, and readable? `[ ] Yes  [ ] No`
- **Q3 - Side Effects:** Does this introduce performance or safety regressions? `[ ] Yes  [ ] No`
- **Q4 - Score (1 to 5):** `[ ]` (1=Broken, 2=Hacky, 3=Suboptimal, 4=Clean, 5=Exemplary)
- **Q5 - Comments / Rationale:** `[                                                ]`

---

## Episode 4: `t04_variable_typo` [EASY]
**Task ID:** `t04_variable_typo`  
**Model:** `nvidia/llama-3.1-nemotron-nano-4b-instruct`  
**Episode ID:** `ep_0004`  
**Pass Rate:** `100%` (automated tests passed)  

### 1. Problem Description
> calculate_variance(nums) contains a NameError typo referencing `sum_diffs` as `sum_diff`.

### 2. Original Buggy File
```py
def calculate_variance(nums: list[float]) -> float:
    """Calculate population variance of numbers."""
    if not nums:
        return 0.0
    mean = sum(nums) / len(nums)
    sum_diffs = sum((x - mean) ** 2 for x in nums)
    return sum_diff / len(nums)
```

### 3. Agent Fix Diff
```diff
--- a/stats.py (buggy)
+++ b/stats.py (agent fix)
@@ -4,4 +4,4 @@
         return 0.0
     mean = sum(nums) / len(nums)
     sum_diffs = sum((x - mean) ** 2 for x in nums)
-    return sum_diff / len(nums)
+    return sum_diffs / len(nums)
```

### 4. Expert Review Questions
- **Q1 - Correctness:** Does this fix address the root cause correctly? `[ ] Yes  [ ] No`
- **Q2 - Idiomatic Style:** Is the fix clean, pythonic, and readable? `[ ] Yes  [ ] No`
- **Q3 - Side Effects:** Does this introduce performance or safety regressions? `[ ] Yes  [ ] No`
- **Q4 - Score (1 to 5):** `[ ]` (1=Broken, 2=Hacky, 3=Suboptimal, 4=Clean, 5=Exemplary)
- **Q5 - Comments / Rationale:** `[                                                ]`

---

## Episode 5: `t05_string_reverse_words` [EASY]
**Task ID:** `t05_string_reverse_words`  
**Model:** `nvidia/llama-3.1-nemotron-nano-4b-instruct`  
**Episode ID:** `ep_0005`  
**Pass Rate:** `100%` (automated tests passed)  

### 1. Problem Description
> reverse_words(sentence) reverses every character in the string instead of reversing the order of words.

### 2. Original Buggy File
```py
def reverse_words(sentence: str) -> str:
    """Reverse the order of words in sentence while keeping words intact."""
    if not sentence:
        return ""
    return sentence[::-1]
```

### 3. Agent Fix Diff
```diff
--- a/textutils.py (buggy)
+++ b/textutils.py (agent fix)
@@ -2,4 +2,4 @@
     """Reverse the order of words in sentence while keeping words intact."""
     if not sentence:
         return ""
-    return sentence[::-1]
+    return " ".join(sentence.split()[::-1])
```

### 4. Expert Review Questions
- **Q1 - Correctness:** Does this fix address the root cause correctly? `[ ] Yes  [ ] No`
- **Q2 - Idiomatic Style:** Is the fix clean, pythonic, and readable? `[ ] Yes  [ ] No`
- **Q3 - Side Effects:** Does this introduce performance or safety regressions? `[ ] Yes  [ ] No`
- **Q4 - Score (1 to 5):** `[ ]` (1=Broken, 2=Hacky, 3=Suboptimal, 4=Clean, 5=Exemplary)
- **Q5 - Comments / Rationale:** `[                                                ]`

---

## Episode 6: `t06_clamp_boundary` [EASY]
**Task ID:** `t06_clamp_boundary`  
**Model:** `nvidia/llama-3.1-nemotron-nano-4b-instruct`  
**Episode ID:** `ep_0006`  
**Pass Rate:** `100%` (automated tests passed)  

### 1. Problem Description
> clamp(val, low, high) swapped the min and max boundary logic.

### 2. Original Buggy File
```py
def clamp(val: float, low: float, high: float) -> float:
    """Restricts val to be within [low, high]."""
    # Inverted min/max logic bug
    return min(low, max(high, val))
```

### 3. Agent Fix Diff
```diff
--- a/mathclamp.py (buggy)
+++ b/mathclamp.py (agent fix)
@@ -1,4 +1,3 @@
 def clamp(val: float, low: float, high: float) -> float:
     """Restricts val to be within [low, high]."""
-    # Inverted min/max logic bug
-    return min(low, max(high, val))
+    return max(low, min(high, val))
```

### 4. Expert Review Questions
- **Q1 - Correctness:** Does this fix address the root cause correctly? `[ ] Yes  [ ] No`
- **Q2 - Idiomatic Style:** Is the fix clean, pythonic, and readable? `[ ] Yes  [ ] No`
- **Q3 - Side Effects:** Does this introduce performance or safety regressions? `[ ] Yes  [ ] No`
- **Q4 - Score (1 to 5):** `[ ]` (1=Broken, 2=Hacky, 3=Suboptimal, 4=Clean, 5=Exemplary)
- **Q5 - Comments / Rationale:** `[                                                ]`

---

## Episode 7: `t07_discount_calc` [EASY]
**Task ID:** `t07_discount_calc`  
**Model:** `nvidia/llama-3.1-nemotron-nano-4b-instruct`  
**Episode ID:** `ep_0007`  
**Pass Rate:** `100%` (automated tests passed)  

### 1. Problem Description
> apply_discount(price, discount_pct) treats discount_pct as a whole number deduction rather than a percentage reduction.

### 2. Original Buggy File
```py
def apply_discount(price: float, discount_pct: float) -> float:
    """Applies percentage discount (0 to 100) to price."""
    if discount_pct < 0 or discount_pct > 100:
        raise ValueError('Invalid discount percentage')
    # Bug: subtracts discount_pct directly instead of percentage
    return round(price - discount_pct, 2)
```

### 3. Agent Fix Diff
```diff
--- a/pricing.py (buggy)
+++ b/pricing.py (agent fix)
@@ -2,5 +2,4 @@
     """Applies percentage discount (0 to 100) to price."""
     if discount_pct < 0 or discount_pct > 100:
         raise ValueError('Invalid discount percentage')
-    # Bug: subtracts discount_pct directly instead of percentage
-    return round(price - discount_pct, 2)
+    return round(price * (1.0 - discount_pct / 100.0), 2)
```

### 4. Expert Review Questions
- **Q1 - Correctness:** Does this fix address the root cause correctly? `[ ] Yes  [ ] No`
- **Q2 - Idiomatic Style:** Is the fix clean, pythonic, and readable? `[ ] Yes  [ ] No`
- **Q3 - Side Effects:** Does this introduce performance or safety regressions? `[ ] Yes  [ ] No`
- **Q4 - Score (1 to 5):** `[ ]` (1=Broken, 2=Hacky, 3=Suboptimal, 4=Clean, 5=Exemplary)
- **Q5 - Comments / Rationale:** `[                                                ]`

---

## Episode 8: `t08_empty_list_edge_case` [MEDIUM]
**Task ID:** `t08_empty_list_edge_case`  
**Model:** `nvidia/llama-3.1-nemotron-nano-4b-instruct`  
**Episode ID:** `ep_0008`  
**Pass Rate:** `100%` (automated tests passed)  

### 1. Problem Description
> calculate_mean(values, default=0.0) crashes with ZeroDivisionError when passed an empty list.

### 2. Original Buggy File
```py
def calculate_mean(values: list[float], default: float = 0.0) -> float:
    """Return the arithmetic mean of values, or default if empty."""
    return sum(values) / len(values)
```

### 3. Agent Fix Diff
```diff
--- a/aggregates.py (buggy)
+++ b/aggregates.py (agent fix)
@@ -1,3 +1,5 @@
 def calculate_mean(values: list[float], default: float = 0.0) -> float:
     """Return the arithmetic mean of values, or default if empty."""
+    if not values:
+        return default
     return sum(values) / len(values)
```

### 4. Expert Review Questions
- **Q1 - Correctness:** Does this fix address the root cause correctly? `[ ] Yes  [ ] No`
- **Q2 - Idiomatic Style:** Is the fix clean, pythonic, and readable? `[ ] Yes  [ ] No`
- **Q3 - Side Effects:** Does this introduce performance or safety regressions? `[ ] Yes  [ ] No`
- **Q4 - Score (1 to 5):** `[ ]` (1=Broken, 2=Hacky, 3=Suboptimal, 4=Clean, 5=Exemplary)
- **Q5 - Comments / Rationale:** `[                                                ]`

---

## Episode 9: `t09_mutable_default_arg` [MEDIUM]
**Task ID:** `t09_mutable_default_arg`  
**Model:** `nvidia/llama-3.1-nemotron-nano-4b-instruct`  
**Episode ID:** `ep_0009`  
**Pass Rate:** `100%` (automated tests passed)  

### 1. Problem Description
> add_item(item, basket=[]) uses a mutable default argument, retaining items across independent calls.

### 2. Original Buggy File
```py
def add_item(item: str, basket: list[str] = []) -> list[str]:
    """Appends item to basket and returns the basket."""
    basket.append(item)
    return basket
```

### 3. Agent Fix Diff
```diff
--- a/cart.py (buggy)
+++ b/cart.py (agent fix)
@@ -1,4 +1,8 @@
-def add_item(item: str, basket: list[str] = []) -> list[str]:
+from typing import Optional
+
+def add_item(item: str, basket: Optional[list[str]] = None) -> list[str]:
     """Appends item to basket and returns the basket."""
+    if basket is None:
+        basket = []
     basket.append(item)
     return basket
```

### 4. Expert Review Questions
- **Q1 - Correctness:** Does this fix address the root cause correctly? `[ ] Yes  [ ] No`
- **Q2 - Idiomatic Style:** Is the fix clean, pythonic, and readable? `[ ] Yes  [ ] No`
- **Q3 - Side Effects:** Does this introduce performance or safety regressions? `[ ] Yes  [ ] No`
- **Q4 - Score (1 to 5):** `[ ]` (1=Broken, 2=Hacky, 3=Suboptimal, 4=Clean, 5=Exemplary)
- **Q5 - Comments / Rationale:** `[                                                ]`

---

## Episode 10: `t10_wrong_slicing` [MEDIUM]
**Task ID:** `t10_wrong_slicing`  
**Model:** `nvidia/llama-3.1-nemotron-nano-4b-instruct`  
**Episode ID:** `ep_0010`  
**Pass Rate:** `100%` (automated tests passed)  

### 1. Problem Description
> extract_domain(email) extracts the domain between @ and .com/etc, but slicing misses the first character after @.

### 2. Original Buggy File
```py
def extract_domain(email: str) -> str:
    """Extract domain name from email (e.g. user@domain.com -> domain.com)."""
    if "@" not in email:
        return ""
    idx = email.index("@")
    # Bug: idx + 2 skips the first char of domain
    return email[idx + 2 :]
```

### 3. Agent Fix Diff
```diff
--- a/emailutils.py (buggy)
+++ b/emailutils.py (agent fix)
@@ -3,5 +3,4 @@
     if "@" not in email:
         return ""
     idx = email.index("@")
-    # Bug: idx + 2 skips the first char of domain
-    return email[idx + 2 :]
+    return email[idx + 1 :]
```

### 4. Expert Review Questions
- **Q1 - Correctness:** Does this fix address the root cause correctly? `[ ] Yes  [ ] No`
- **Q2 - Idiomatic Style:** Is the fix clean, pythonic, and readable? `[ ] Yes  [ ] No`
- **Q3 - Side Effects:** Does this introduce performance or safety regressions? `[ ] Yes  [ ] No`
- **Q4 - Score (1 to 5):** `[ ]` (1=Broken, 2=Hacky, 3=Suboptimal, 4=Clean, 5=Exemplary)
- **Q5 - Comments / Rationale:** `[                                                ]`

---
