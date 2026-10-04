"""Generates the 20 benchmark tasks for DebugArena."""

import json
from pathlib import Path

TASKS = [
    # -------------------------------------------------------------
    # EASY (7 tasks)
    # -------------------------------------------------------------
    {
        "task_id": "t01_off_by_one",
        "difficulty": "easy",
        "bug_type": "off_by_one",
        "description": "sum_range(a, b) should return the sum of all integers from a to b inclusive, but it currently excludes b.",
        "repo_files": {
            "mathutils.py": (
                "def sum_range(a: int, b: int) -> int:\n"
                "    \"\"\"Return the sum of integers from a to b inclusive.\"\"\"\n"
                "    if a > b:\n"
                "        return 0\n"
                "    return sum(range(a, b))\n"
            )
        },
        "tests": {
            "test_mathutils.py": (
                "from mathutils import sum_range\n\n"
                "def test_invalid_range():\n"
                "    # Baseline test that passes before fix\n"
                "    assert sum_range(5, 2) == 0\n\n"
                "def test_single_element():\n"
                "    assert sum_range(4, 4) == 4\n\n"
                "def test_basic_range():\n"
                "    assert sum_range(1, 3) == 6\n\n"
                "def test_larger_range():\n"
                "    assert sum_range(1, 10) == 55\n"
            )
        },
        "reference_fix": {
            "mathutils.py": (
                "def sum_range(a: int, b: int) -> int:\n"
                "    \"\"\"Return the sum of integers from a to b inclusive.\"\"\"\n"
                "    if a > b:\n"
                "        return 0\n"
                "    return sum(range(a, b + 1))\n"
            )
        },
    },
    {
        "task_id": "t02_wrong_operator",
        "difficulty": "easy",
        "bug_type": "wrong_operator",
        "description": "filter_passing_scores(scores, threshold) should return all scores that are greater than or equal to threshold, but it strictly filters out scores equal to threshold.",
        "repo_files": {
            "grader.py": (
                "def filter_passing_scores(scores: list[int], threshold: int = 50) -> list[int]:\n"
                "    \"\"\"Filter scores >= threshold.\"\"\"\n"
                "    return [s for s in scores if s > threshold]\n"
            )
        },
        "tests": {
            "test_grader.py": (
                "from grader import filter_passing_scores\n\n"
                "def test_strictly_above():\n"
                "    # Passes before fix\n"
                "    assert filter_passing_scores([60, 70, 80], 50) == [60, 70, 80]\n\n"
                "def test_boundary_score():\n"
                "    assert filter_passing_scores([50], 50) == [50]\n\n"
                "def test_mixed_scores():\n"
                "    assert filter_passing_scores([49, 50, 51], 50) == [50, 51]\n\n"
                "def test_empty_scores():\n"
                "    assert filter_passing_scores([], 50) == []\n"
            )
        },
        "reference_fix": {
            "grader.py": (
                "def filter_passing_scores(scores: list[int], threshold: int = 50) -> list[int]:\n"
                "    \"\"\"Filter scores >= threshold.\"\"\"\n"
                "    return [s for s in scores if s >= threshold]\n"
            )
        },
    },
    {
        "task_id": "t03_wrong_return",
        "difficulty": "easy",
        "bug_type": "wrong_return_value",
        "description": "factorial(n) returns 0 for n == 0 instead of 1.",
        "repo_files": {
            "factorials.py": (
                "def factorial(n: int) -> int:\n"
                "    \"\"\"Return n factorial.\"\"\"\n"
                "    if n < 0:\n"
                "        raise ValueError('Negative values not allowed')\n"
                "    if n == 0:\n"
                "        return 0\n"
                "    result = 1\n"
                "    for i in range(1, n + 1):\n"
                "        result *= i\n"
                "    return result\n"
            )
        },
        "tests": {
            "test_factorials.py": (
                "import pytest\n"
                "from factorials import factorial\n\n"
                "def test_positive():\n"
                "    # Passes before fix\n"
                "    assert factorial(3) == 6\n"
                "    assert factorial(5) == 120\n\n"
                "def test_zero():\n"
                "    assert factorial(0) == 1\n\n"
                "def test_one():\n"
                "    assert factorial(1) == 1\n\n"
                "def test_negative_raises():\n"
                "    with pytest.raises(ValueError):\n"
                "        factorial(-1)\n"
            )
        },
        "reference_fix": {
            "factorials.py": (
                "def factorial(n: int) -> int:\n"
                "    \"\"\"Return n factorial.\"\"\"\n"
                "    if n < 0:\n"
                "        raise ValueError('Negative values not allowed')\n"
                "    if n == 0:\n"
                "        return 1\n"
                "    result = 1\n"
                "    for i in range(1, n + 1):\n"
                "        result *= i\n"
                "    return result\n"
            )
        },
    },
    {
        "task_id": "t04_variable_typo",
        "difficulty": "easy",
        "bug_type": "variable_typo",
        "description": "calculate_variance(nums) contains a NameError typo referencing `sum_diffs` as `sum_diff`.",
        "repo_files": {
            "stats.py": (
                "def calculate_variance(nums: list[float]) -> float:\n"
                "    \"\"\"Calculate population variance of numbers.\"\"\"\n"
                "    if not nums:\n"
                "        return 0.0\n"
                "    mean = sum(nums) / len(nums)\n"
                "    sum_diffs = sum((x - mean) ** 2 for x in nums)\n"
                "    return sum_diff / len(nums)\n"
            )
        },
        "tests": {
            "test_stats.py": (
                "from stats import calculate_variance\n\n"
                "def test_empty():\n"
                "    # Passes before fix\n"
                "    assert calculate_variance([]) == 0.0\n\n"
                "def test_single_val():\n"
                "    assert calculate_variance([5.0]) == 0.0\n\n"
                "def test_uniform():\n"
                "    assert calculate_variance([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]) == 4.0\n\n"
                "def test_identical():\n"
                "    assert calculate_variance([3.0, 3.0, 3.0]) == 0.0\n"
            )
        },
        "reference_fix": {
            "stats.py": (
                "def calculate_variance(nums: list[float]) -> float:\n"
                "    \"\"\"Calculate population variance of numbers.\"\"\"\n"
                "    if not nums:\n"
                "        return 0.0\n"
                "    mean = sum(nums) / len(nums)\n"
                "    sum_diffs = sum((x - mean) ** 2 for x in nums)\n"
                "    return sum_diffs / len(nums)\n"
            )
        },
    },
    {
        "task_id": "t05_string_reverse_words",
        "difficulty": "easy",
        "bug_type": "string_reversal",
        "description": "reverse_words(sentence) reverses every character in the string instead of reversing the order of words.",
        "repo_files": {
            "textutils.py": (
                "def reverse_words(sentence: str) -> str:\n"
                "    \"\"\"Reverse the order of words in sentence while keeping words intact.\"\"\"\n"
                "    if not sentence:\n"
                "        return \"\"\n"
                "    return sentence[::-1]\n"
            )
        },
        "tests": {
            "test_textutils.py": (
                "from textutils import reverse_words\n\n"
                "def test_empty():\n"
                "    # Passes before fix\n"
                "    assert reverse_words(\"\") == \"\"\n\n"
                "def test_single_word():\n"
                "    # Should not reverse letters inside the word!\n"
                "    assert reverse_words(\"hello\") == \"hello\"\n\n"
                "def test_two_words():\n"
                "    assert reverse_words(\"hello world\") == \"world hello\"\n\n"
                "def test_three_words():\n"
                "    assert reverse_words(\"quick brown fox\") == \"fox brown quick\"\n"
            )
        },
        "reference_fix": {
            "textutils.py": (
                "def reverse_words(sentence: str) -> str:\n"
                "    \"\"\"Reverse the order of words in sentence while keeping words intact.\"\"\"\n"
                "    if not sentence:\n"
                "        return \"\"\n"
                "    return \" \".join(sentence.split()[::-1])\n"
            )
        },
    },
    {
        "task_id": "t06_clamp_boundary",
        "difficulty": "easy",
        "bug_type": "logic_swap",
        "description": "clamp(val, low, high) swapped the min and max boundary logic.",
        "repo_files": {
            "mathclamp.py": (
                "def clamp(val: float, low: float, high: float) -> float:\n"
                "    \"\"\"Restricts val to be within [low, high].\"\"\"\n"
                "    # Inverted min/max logic bug\n"
                "    return min(low, max(high, val))\n"
            )
        },
        "tests": {
            "test_mathclamp.py": (
                "from mathclamp import clamp\n\n"
                "def test_equal_boundaries():\n"
                "    # Passes before fix\n"
                "    assert clamp(5.0, 5.0, 5.0) == 5.0\n\n"
                "def test_within_range():\n"
                "    assert clamp(5.0, 0.0, 10.0) == 5.0\n\n"
                "def test_below_low():\n"
                "    assert clamp(-2.0, 0.0, 10.0) == 0.0\n\n"
                "def test_above_high():\n"
                "    assert clamp(15.0, 0.0, 10.0) == 10.0\n"
            )
        },
        "reference_fix": {
            "mathclamp.py": (
                "def clamp(val: float, low: float, high: float) -> float:\n"
                "    \"\"\"Restricts val to be within [low, high].\"\"\"\n"
                "    return max(low, min(high, val))\n"
            )
        },
    },
    {
        "task_id": "t07_discount_calc",
        "difficulty": "easy",
        "bug_type": "calculation_bug",
        "description": "apply_discount(price, discount_pct) treats discount_pct as a whole number deduction rather than a percentage reduction.",
        "repo_files": {
            "pricing.py": (
                "def apply_discount(price: float, discount_pct: float) -> float:\n"
                "    \"\"\"Applies percentage discount (0 to 100) to price.\"\"\"\n"
                "    if discount_pct < 0 or discount_pct > 100:\n"
                "        raise ValueError('Invalid discount percentage')\n"
                "    # Bug: subtracts discount_pct directly instead of percentage\n"
                "    return round(price - discount_pct, 2)\n"
            )
        },
        "tests": {
            "test_pricing.py": (
                "import pytest\n"
                "from pricing import apply_discount\n\n"
                "def test_invalid_pct():\n"
                "    # Passes before fix\n"
                "    with pytest.raises(ValueError):\n"
                "        apply_discount(100.0, 105.0)\n\n"
                "def test_zero_discount():\n"
                "    assert apply_discount(100.0, 0.0) == 100.0\n\n"
                "def test_fifty_percent():\n"
                "    assert apply_discount(200.0, 50.0) == 100.0\n\n"
                "def test_twenty_percent():\n"
                "    assert apply_discount(50.0, 20.0) == 40.0\n"
            )
        },
        "reference_fix": {
            "pricing.py": (
                "def apply_discount(price: float, discount_pct: float) -> float:\n"
                "    \"\"\"Applies percentage discount (0 to 100) to price.\"\"\"\n"
                "    if discount_pct < 0 or discount_pct > 100:\n"
                "        raise ValueError('Invalid discount percentage')\n"
                "    return round(price * (1.0 - discount_pct / 100.0), 2)\n"
            )
        },
    },

    # -------------------------------------------------------------
    # MEDIUM (9 tasks)
    # -------------------------------------------------------------
    {
        "task_id": "t08_empty_list_edge_case",
        "difficulty": "medium",
        "bug_type": "missing_edge_case",
        "description": "calculate_mean(values, default=0.0) crashes with ZeroDivisionError when passed an empty list.",
        "repo_files": {
            "aggregates.py": (
                "def calculate_mean(values: list[float], default: float = 0.0) -> float:\n"
                "    \"\"\"Return the arithmetic mean of values, or default if empty.\"\"\"\n"
                "    return sum(values) / len(values)\n"
            )
        },
        "tests": {
            "test_aggregates.py": (
                "from aggregates import calculate_mean\n\n"
                "def test_single():\n"
                "    # Passes before fix\n"
                "    assert calculate_mean([10.0]) == 10.0\n\n"
                "def test_multiple():\n"
                "    assert calculate_mean([1.0, 2.0, 3.0]) == 2.0\n\n"
                "def test_empty_default():\n"
                "    assert calculate_mean([]) == 0.0\n\n"
                "def test_empty_custom_default():\n"
                "    assert calculate_mean([], default=-1.0) == -1.0\n"
            )
        },
        "reference_fix": {
            "aggregates.py": (
                "def calculate_mean(values: list[float], default: float = 0.0) -> float:\n"
                "    \"\"\"Return the arithmetic mean of values, or default if empty.\"\"\"\n"
                "    if not values:\n"
                "        return default\n"
                "    return sum(values) / len(values)\n"
            )
        },
    },
    {
        "task_id": "t09_mutable_default_arg",
        "difficulty": "medium",
        "bug_type": "mutable_default_argument",
        "description": "add_item(item, basket=[]) uses a mutable default argument, retaining items across independent calls.",
        "repo_files": {
            "cart.py": (
                "def add_item(item: str, basket: list[str] = []) -> list[str]:\n"
                "    \"\"\"Appends item to basket and returns the basket.\"\"\"\n"
                "    basket.append(item)\n"
                "    return basket\n"
            )
        },
        "tests": {
            "test_cart.py": (
                "from cart import add_item\n\n"
                "def test_with_explicit_basket():\n"
                "    # Passes before fix\n"
                "    my_basket = [\"apple\"]\n"
                "    assert add_item(\"banana\", my_basket) == [\"apple\", \"banana\"]\n\n"
                "def test_first_call_default():\n"
                "    assert add_item(\"orange\") == [\"orange\"]\n\n"
                "def test_second_call_default_isolation():\n"
                "    # Default list should not retain previously added items\n"
                "    assert add_item(\"grape\") == [\"grape\"]\n\n"
                "def test_third_call_default_isolation():\n"
                "    assert add_item(\"melon\") == [\"melon\"]\n"
            )
        },
        "reference_fix": {
            "cart.py": (
                "from typing import Optional\n\n"
                "def add_item(item: str, basket: Optional[list[str]] = None) -> list[str]:\n"
                "    \"\"\"Appends item to basket and returns the basket.\"\"\"\n"
                "    if basket is None:\n"
                "        basket = []\n"
                "    basket.append(item)\n"
                "    return basket\n"
            )
        },
    },
    {
        "task_id": "t10_wrong_slicing",
        "difficulty": "medium",
        "bug_type": "wrong_string_slicing",
        "description": "extract_domain(email) extracts the domain between @ and .com/etc, but slicing misses the first character after @.",
        "repo_files": {
            "emailutils.py": (
                "def extract_domain(email: str) -> str:\n"
                "    \"\"\"Extract domain name from email (e.g. user@domain.com -> domain.com).\"\"\"\n"
                "    if \"@\" not in email:\n"
                "        return \"\"\n"
                "    idx = email.index(\"@\")\n"
                "    # Bug: idx + 2 skips the first char of domain\n"
                "    return email[idx + 2 :]\n"
            )
        },
        "tests": {
            "test_emailutils.py": (
                "from emailutils import extract_domain\n\n"
                "def test_no_at_symbol():\n"
                "    # Passes before fix\n"
                "    assert extract_domain(\"invalid-email\") == \"\"\n\n"
                "def test_standard_email():\n"
                "    assert extract_domain(\"alice@example.com\") == \"example.com\"\n\n"
                "def test_short_domain():\n"
                "    assert extract_domain(\"bob@ai.org\") == \"ai.org\"\n\n"
                "def test_subdomain():\n"
                "    assert extract_domain(\"test@sub.domain.co\") == \"sub.domain.co\"\n"
            )
        },
        "reference_fix": {
            "emailutils.py": (
                "def extract_domain(email: str) -> str:\n"
                "    \"\"\"Extract domain name from email (e.g. user@domain.com -> domain.com).\"\"\"\n"
                "    if \"@\" not in email:\n"
                "        return \"\"\n"
                "    idx = email.index(\"@\")\n"
                "    return email[idx + 1 :]\n"
            )
        },
    },
    {
        "task_id": "t11_int_vs_float_div",
        "difficulty": "medium",
        "bug_type": "integer_vs_float_division",
        "description": "calculate_aspect_ratio(width, height) uses integer division // causing truncation instead of true floating point ratio.",
        "repo_files": {
            "dimensions.py": (
                "def calculate_aspect_ratio(width: int, height: int) -> float:\n"
                "    \"\"\"Return aspect ratio (width / height) rounded to 2 decimal places.\"\"\"\n"
                "    if height <= 0 or width <= 0:\n"
                "        raise ValueError('Dimensions must be positive')\n"
                "    # Bug: integer division\n"
                "    return float(width // height)\n"
            )
        },
        "tests": {
            "test_dimensions.py": (
                "import pytest\n"
                "from dimensions import calculate_aspect_ratio\n\n"
                "def test_invalid_dimension():\n"
                "    # Passes before fix\n"
                "    with pytest.raises(ValueError):\n"
                "        calculate_aspect_ratio(0, 100)\n\n"
                "def test_integer_ratio():\n"
                "    # Passes before fix (4 // 2 == 2.0)\n"
                "    assert calculate_aspect_ratio(400, 200) == 2.0\n\n"
                "def test_sixteen_nine():\n"
                "    assert calculate_aspect_ratio(1920, 1080) == 1.78\n\n"
                "def test_fractional_less_than_one():\n"
                "    assert calculate_aspect_ratio(1080, 1920) == 0.56\n"
            )
        },
        "reference_fix": {
            "dimensions.py": (
                "def calculate_aspect_ratio(width: int, height: int) -> float:\n"
                "    \"\"\"Return aspect ratio (width / height) rounded to 2 decimal places.\"\"\"\n"
                "    if height <= 0 or width <= 0:\n"
                "        raise ValueError('Dimensions must be positive')\n"
                "    return round(width / height, 2)\n"
            )
        },
    },
    {
        "task_id": "t12_dict_key_handling",
        "difficulty": "medium",
        "bug_type": "missing_dict_key",
        "description": "get_user_role(users_dict, user_id, default='guest') raises KeyError if user_id is missing or profile has no 'role'.",
        "repo_files": {
            "roles.py": (
                "def get_user_role(users_dict: dict, user_id: str, default: str = 'guest') -> str:\n"
                "    \"\"\"Returns user's role or default if user/role is not found.\"\"\"\n"
                "    # Bug: direct indexing causes KeyError\n"
                "    return users_dict[user_id]['role']\n"
            )
        },
        "tests": {
            "test_roles.py": (
                "from roles import get_user_role\n\n"
                "def test_existing_user():\n"
                "    # Passes before fix\n"
                "    data = {'u1': {'role': 'admin'}}\n"
                "    assert get_user_role(data, 'u1') == 'admin'\n\n"
                "def test_missing_user():\n"
                "    data = {'u1': {'role': 'admin'}}\n"
                "    assert get_user_role(data, 'u2') == 'guest'\n\n"
                "def test_missing_role_key():\n"
                "    data = {'u1': {'name': 'Alice'}}\n"
                "    assert get_user_role(data, 'u1') == 'guest'\n\n"
                "def test_custom_default():\n"
                "    assert get_user_role({}, 'unknown', default='anonymous') == 'anonymous'\n"
            )
        },
        "reference_fix": {
            "roles.py": (
                "def get_user_role(users_dict: dict, user_id: str, default: str = 'guest') -> str:\n"
                "    \"\"\"Returns user's role or default if user/role is not found.\"\"\"\n"
                "    user = users_dict.get(user_id)\n"
                "    if isinstance(user, dict):\n"
                "        return user.get('role', default)\n"
                "    return default\n"
            )
        },
    },
    {
        "task_id": "t13_flatten_nested",
        "difficulty": "medium",
        "bug_type": "recursion_edge_case",
        "description": "flatten(lst) only unpacks 1 level of nesting and fails on deeply nested lists.",
        "repo_files": {
            "lists.py": (
                "def flatten(lst: list) -> list:\n"
                "    \"\"\"Recursively flatten arbitrarily nested lists into a single 1D list.\"\"\"\n"
                "    # Bug: only flattens one level\n"
                "    res = []\n"
                "    for item in lst:\n"
                "        if isinstance(item, list):\n"
                "            res.extend(item)\n"
                "        else:\n"
                "            res.append(item)\n"
                "    return res\n"
            )
        },
        "tests": {
            "test_lists.py": (
                "from lists import flatten\n\n"
                "def test_already_flat():\n"
                "    # Passes before fix\n"
                "    assert flatten([1, 2, 3]) == [1, 2, 3]\n\n"
                "def test_single_level():\n"
                "    # Passes before fix\n"
                "    assert flatten([[1, 2], [3, 4]]) == [1, 2, 3, 4]\n\n"
                "def test_multi_level():\n"
                "    assert flatten([1, [2, [3, [4]], 5]]) == [1, 2, 3, 4, 5]\n\n"
                "def test_empty_sublists():\n"
                "    assert flatten([[], [1, []], [[], 2]]) == [1, 2]\n"
            )
        },
        "reference_fix": {
            "lists.py": (
                "def flatten(lst: list) -> list:\n"
                "    \"\"\"Recursively flatten arbitrarily nested lists into a single 1D list.\"\"\"\n"
                "    res = []\n"
                "    for item in lst:\n"
                "        if isinstance(item, list):\n"
                "            res.extend(flatten(item))\n"
                "        else:\n"
                "            res.append(item)\n"
                "    return res\n"
            )
        },
    },
    {
        "task_id": "t14_moving_average",
        "difficulty": "medium",
        "bug_type": "index_misalignment",
        "description": "moving_average(series, window) computes averages with index offset i instead of sliding window range.",
        "repo_files": {
            "timeseries.py": (
                "def moving_average(series: list[float], window: int) -> list[float]:\n"
                "    \"\"\"Compute simple moving average with window size.\"\"\"\n"
                "    if window <= 0 or len(series) < window:\n"
                "        return []\n"
                "    result = []\n"
                "    # Bug: window sum slice misses elements\n"
                "    for i in range(len(series) - window + 1):\n"
                "        w_sum = sum(series[i : i + window - 1])\n"
                "        result.append(round(w_sum / window, 2))\n"
                "    return result\n"
            )
        },
        "tests": {
            "test_timeseries.py": (
                "from timeseries import moving_average\n\n"
                "def test_short_series():\n"
                "    # Passes before fix\n"
                "    assert moving_average([1.0, 2.0], 3) == []\n\n"
                "def test_window_size_one():\n"
                "    # Window of 1 should equal series\n"
                "    assert moving_average([1.0, 2.0, 3.0], 1) == [1.0, 2.0, 3.0]\n\n"
                "def test_window_two():\n"
                "    assert moving_average([1.0, 3.0, 5.0, 7.0], 2) == [2.0, 4.0, 6.0]\n\n"
                "def test_window_three():\n"
                "    assert moving_average([10.0, 20.0, 30.0, 40.0], 3) == [20.0, 30.0]\n"
            )
        },
        "reference_fix": {
            "timeseries.py": (
                "def moving_average(series: list[float], window: int) -> list[float]:\n"
                "    \"\"\"Compute simple moving average with window size.\"\"\"\n"
                "    if window <= 0 or len(series) < window:\n"
                "        return []\n"
                "    result = []\n"
                "    for i in range(len(series) - window + 1):\n"
                "        w_sum = sum(series[i : i + window])\n"
                "        result.append(round(w_sum / window, 2))\n"
                "    return result\n"
            )
        },
    },
    {
        "task_id": "t15_matrix_transpose",
        "difficulty": "medium",
        "bug_type": "index_bounds_error",
        "description": "transpose(matrix) works for square matrices but crashes or produces wrong dimension for non-square rectangular matrices.",
        "repo_files": {
            "matrix.py": (
                "def transpose(matrix: list[list[int]]) -> list[list[int]]:\n"
                "    \"\"\"Transpose a 2D matrix.\"\"\"\n"
                "    if not matrix or not matrix[0]:\n"
                "        return []\n"
                "    rows = len(matrix)\n"
                "    # Bug assumes square matrix dimensions rows x rows\n"
                "    return [[matrix[r][c] for r in range(rows)] for c in range(rows)]\n"
            )
        },
        "tests": {
            "test_matrix.py": (
                "from matrix import transpose\n\n"
                "def test_empty():\n"
                "    # Passes before fix\n"
                "    assert transpose([]) == []\n\n"
                "def test_square_matrix():\n"
                "    # Passes before fix\n"
                "    sq = [[1, 2], [3, 4]]\n"
                "    assert transpose(sq) == [[1, 3], [2, 4]]\n\n"
                "def test_rectangular_2x3():\n"
                "    rect = [[1, 2, 3], [4, 5, 6]]\n"
                "    assert transpose(rect) == [[1, 4], [2, 5], [3, 6]]\n\n"
                "def test_single_row():\n"
                "    assert transpose([[10, 20, 30]]) == [[10], [20], [30]]\n"
            )
        },
        "reference_fix": {
            "matrix.py": (
                "def transpose(matrix: list[list[int]]) -> list[list[int]]:\n"
                "    \"\"\"Transpose a 2D matrix.\"\"\"\n"
                "    if not matrix or not matrix[0]:\n"
                "        return []\n"
                "    rows = len(matrix)\n"
                "    cols = len(matrix[0])\n"
                "    return [[matrix[r][c] for r in range(rows)] for c in range(cols)]\n"
            )
        },
    },
    {
        "task_id": "t16_lru_cache_eviction",
        "difficulty": "medium",
        "bug_type": "cache_eviction_logic",
        "description": "LRUCache get(key) retrieves value but does not move key to the most-recently-used position.",
        "repo_files": {
            "cache.py": (
                "from collections import OrderedDict\n\n"
                "class LRUCache:\n"
                "    def __init__(self, capacity: int):\n"
                "        self.capacity = capacity\n"
                "        self.store = OrderedDict()\n\n"
                "    def get(self, key: str) -> int:\n"
                "        if key not in self.store:\n"
                "            return -1\n"
                "        # Bug: missed moving accessed key to end\n"
                "        return self.store[key]\n\n"
                "    def put(self, key: str, value: int) -> None:\n"
                "        if key in self.store:\n"
                "            self.store.move_to_end(key)\n"
                "        self.store[key] = value\n"
                "        if len(self.store) > self.capacity:\n"
                "            self.store.popitem(last=False)\n"
            )
        },
        "tests": {
            "test_cache.py": (
                "from cache import LRUCache\n\n"
                "def test_missing_key():\n"
                "    # Passes before fix\n"
                "    c = LRUCache(2)\n"
                "    assert c.get('missing') == -1\n\n"
                "def test_basic_put_get():\n"
                "    # Passes before fix\n"
                "    c = LRUCache(2)\n"
                "    c.put('a', 1)\n"
                "    assert c.get('a') == 1\n\n"
                "def test_eviction_order():\n"
                "    c = LRUCache(2)\n"
                "    c.put('a', 1)\n"
                "    c.put('b', 2)\n"
                "    # Access 'a', making 'b' the least recently used\n"
                "    assert c.get('a') == 1\n"
                "    # Put 'c', should evict 'b'\n"
                "    c.put('c', 3)\n"
                "    assert c.get('b') == -1\n"
                "    assert c.get('a') == 1\n"
                "    assert c.get('c') == 3\n"
            )
        },
        "reference_fix": {
            "cache.py": (
                "from collections import OrderedDict\n\n"
                "class LRUCache:\n"
                "    def __init__(self, capacity: int):\n"
                "        self.capacity = capacity\n"
                "        self.store = OrderedDict()\n\n"
                "    def get(self, key: str) -> int:\n"
                "        if key not in self.store:\n"
                "            return -1\n"
                "        self.store.move_to_end(key)\n"
                "        return self.store[key]\n\n"
                "    def put(self, key: str, value: int) -> None:\n"
                "        if key in self.store:\n"
                "            self.store.move_to_end(key)\n"
                "        self.store[key] = value\n"
                "        if len(self.store) > self.capacity:\n"
                "            self.store.popitem(last=False)\n"
            )
        },
    },

    # -------------------------------------------------------------
    # HARDER (4 tasks)
    # -------------------------------------------------------------
    {
        "task_id": "t17_two_file_import_bug",
        "difficulty": "hard",
        "bug_type": "multi_file_interface_mismatch",
        "description": "Multi-file task: `data_loader.py` parses record rows, but `pipeline.py` calls it with incompatible key names causing a KeyError.",
        "repo_files": {
            "data_loader.py": (
                "def load_records(raw_rows: list[str]) -> list[dict]:\n"
                "    \"\"\"Parses csv formatted string rows into list of dictionaries.\"\"\"\n"
                "    records = []\n"
                "    for row in raw_rows:\n"
                "        parts = row.strip().split(',')\n"
                "        if len(parts) >= 2:\n"
                "            records.append({'user_id': parts[0].strip(), 'score': float(parts[1].strip())})\n"
                "    return records\n"
            ),
            "pipeline.py": (
                "from data_loader import load_records\n\n"
                "def compute_top_user(raw_rows: list[str]) -> str:\n"
                "    \"\"\"Finds user with the highest score from raw rows.\"\"\"\n"
                "    records = load_records(raw_rows)\n"
                "    if not records:\n"
                "        return ''\n"
                "    # Bug: pipeline expects 'id' instead of 'user_id'\n"
                "    best = max(records, key=lambda r: r['score'])\n"
                "    return best['id']\n"
            ),
        },
        "tests": {
            "test_pipeline.py": (
                "from pipeline import compute_top_user\n"
                "from data_loader import load_records\n\n"
                "def test_empty_rows():\n"
                "    # Passes before fix\n"
                "    assert compute_top_user([]) == ''\n\n"
                "def test_data_loader_structure():\n"
                "    # Loader works standalone\n"
                "    res = load_records(['alice,90.5'])\n"
                "    assert res == [{'user_id': 'alice', 'score': 90.5}]\n\n"
                "def test_top_user_single():\n"
                "    rows = ['alice, 88.0']\n"
                "    assert compute_top_user(rows) == 'alice'\n\n"
                "def test_top_user_multiple():\n"
                "    rows = ['alice, 75.0', 'bob, 94.5', 'charlie, 82.0']\n"
                "    assert compute_top_user(rows) == 'bob'\n"
            )
        },
        "reference_fix": {
            "pipeline.py": (
                "from data_loader import load_records\n\n"
                "def compute_top_user(raw_rows: list[str]) -> str:\n"
                "    \"\"\"Finds user with the highest score from raw rows.\"\"\"\n"
                "    records = load_records(raw_rows)\n"
                "    if not records:\n"
                "        return ''\n"
                "    best = max(records, key=lambda r: r['score'])\n"
                "    return best['user_id']\n"
            )
        },
    },
    {
        "task_id": "t18_stateful_quote_lexer",
        "difficulty": "hard",
        "bug_type": "stateful_loop_lexer",
        "description": "tokenize_quoted_string(text) splits words by space except inside double quotes, but fails to handle escaped double quotes `\\\"`.",
        "repo_files": {
            "lexer.py": (
                "def tokenize(text: str) -> list[str]:\n"
                "    \"\"\"Tokenizes string by space, preserving quoted substrings and handles escaped quotes.\"\"\"\n"
                "    tokens = []\n"
                "    current = []\n"
                "    in_quotes = False\n"
                "    for char in text:\n"
                "        if char == '\"':\n"
                "            in_quotes = not in_quotes\n"
                "        elif char == ' ' and not in_quotes:\n"
                "            if current:\n"
                "                tokens.append(''.join(current))\n"
                "                current = []\n"
                "        else:\n"
                "            current.append(char)\n"
                "    if current:\n"
                "        tokens.append(''.join(current))\n"
                "    return tokens\n"
            )
        },
        "tests": {
            "test_lexer.py": (
                "from lexer import tokenize\n\n"
                "def test_empty():\n"
                "    # Passes before fix\n"
                "    assert tokenize(\"\") == []\n\n"
                "def test_plain_words():\n"
                "    # Passes before fix\n"
                "    assert tokenize(\"hello world foo\") == [\"hello\", \"world\", \"foo\"]\n\n"
                "def test_simple_quoted():\n"
                "    # Passes before fix\n"
                "    assert tokenize('name \"hello world\" age') == [\"name\", \"hello world\", \"age\"]\n\n"
                "def test_escaped_quote():\n"
                "    # Escaped quote inside string should be preserved as quote\n"
                "    assert tokenize('msg \"he said \\\\\"hi\\\\\"\" now') == [\"msg\", 'he said \"hi\"', \"now\"]\n"
            )
        },
        "reference_fix": {
            "lexer.py": (
                "def tokenize(text: str) -> list[str]:\n"
                "    \"\"\"Tokenizes string by space, preserving quoted substrings and handles escaped quotes.\"\"\"\n"
                "    tokens = []\n"
                "    current = []\n"
                "    in_quotes = False\n"
                "    escaped = False\n"
                "    for char in text:\n"
                "        if escaped:\n"
                "            current.append(char)\n"
                "            escaped = False\n"
                "        elif char == '\\\\':\n"
                "            escaped = True\n"
                "        elif char == '\"':\n"
                "            in_quotes = not in_quotes\n"
                "        elif char == ' ' and not in_quotes:\n"
                "            if current:\n"
                "                tokens.append(''.join(current))\n"
                "                current = []\n"
                "        else:\n"
                "            current.append(char)\n"
                "    if current:\n"
                "        tokens.append(''.join(current))\n"
                "    return tokens\n"
            )
        },
    },
    {
        "task_id": "t19_custom_sort_priority",
        "difficulty": "hard",
        "bug_type": "custom_sort_key",
        "description": "sort_tasks(tasks) should sort items by priority (high > medium > low) then deadline ascending, but inverted priority values cause low priority to be sorted first.",
        "repo_files": {
            "taskmgr.py": (
                "def sort_tasks(tasks: list[dict]) -> list[dict]:\n"
                "    \"\"\"Sort tasks by priority descending (high > medium > low) then deadline ascending.\"\"\"\n"
                "    # Bug: inverted rank puts low priority first\n"
                "    priority_order = {'high': 3, 'medium': 2, 'low': 1}\n"
                "    return sorted(tasks, key=lambda t: (priority_order.get(t['priority'], 99), t['deadline']))\n"
            )
        },
        "tests": {
            "test_taskmgr.py": (
                "from taskmgr import sort_tasks\n\n"
                "def test_empty():\n"
                "    # Passes before fix\n"
                "    assert sort_tasks([]) == []\n\n"
                "def test_same_priority_deadline_order():\n"
                "    # Passes before fix (same priority)\n"
                "    t = [\n"
                "        {'id': 1, 'priority': 'high', 'deadline': 5},\n"
                "        {'id': 2, 'priority': 'high', 'deadline': 2},\n"
                "    ]\n"
                "    res = sort_tasks(t)\n"
                "    assert [x['id'] for x in res] == [2, 1]\n\n"
                "def test_multi_priority():\n"
                "    t = [\n"
                "        {'id': 1, 'priority': 'low', 'deadline': 1},\n"
                "        {'id': 2, 'priority': 'high', 'deadline': 10},\n"
                "        {'id': 3, 'priority': 'medium', 'deadline': 5},\n"
                "    ]\n"
                "    res = sort_tasks(t)\n"
                "    # high should come first, then medium, then low\n"
                "    assert [x['id'] for x in res] == [2, 3, 1]\n\n"
                "def test_tie_breaking():\n"
                "    t = [\n"
                "        {'id': 1, 'priority': 'medium', 'deadline': 8},\n"
                "        {'id': 2, 'priority': 'high', 'deadline': 3},\n"
                "        {'id': 3, 'priority': 'high', 'deadline': 1},\n"
                "    ]\n"
                "    res = sort_tasks(t)\n"
                "    assert [x['id'] for x in res] == [3, 2, 1]\n"
            )
        },
        "reference_fix": {
            "taskmgr.py": (
                "def sort_tasks(tasks: list[dict]) -> list[dict]:\n"
                "    \"\"\"Sort tasks by priority descending (high > medium > low) then deadline ascending.\"\"\"\n"
                "    priority_order = {'high': 1, 'medium': 2, 'low': 3}\n"
                "    return sorted(tasks, key=lambda t: (priority_order.get(t['priority'], 99), t['deadline']))\n"
            )
        },
    },
    {
        "task_id": "t20_retry_decorator",
        "difficulty": "hard",
        "bug_type": "decorator_state_counter",
        "description": "retry(max_attempts=3) decorator catches exceptions and retries, but does not decrement or track remaining attempts, retrying infinitely or failing immediately.",
        "repo_files": {
            "retrier.py": (
                "from functools import wraps\n\n"
                "def retry(max_attempts: int = 3):\n"
                "    \"\"\"Decorator that retries a function up to max_attempts times on Exception.\"\"\"\n"
                "    def decorator(func):\n"
                "        @wraps(func)\n"
                "        def wrapper(*args, **kwargs):\n"
                "            # Bug: only tries once and raises\n"
                "            try:\n"
                "                return func(*args, **kwargs)\n"
                "            except Exception as e:\n"
                "                raise e\n"
                "        return wrapper\n"
                "    return decorator\n"
            )
        },
        "tests": {
            "test_retrier.py": (
                "import pytest\n"
                "from retrier import retry\n\n"
                "def test_immediate_success():\n"
                "    # Passes before fix\n"
                "    @retry(max_attempts=3)\n"
                "    def succ():\n"
                "        return 'ok'\n"
                "    assert succ() == 'ok'\n\n"
                "def test_retry_eventual_success():\n"
                "    calls = 0\n"
                "    @retry(max_attempts=3)\n"
                "    def flaky():\n"
                "        nonlocal calls\n"
                "        calls += 1\n"
                "        if calls < 3:\n"
                "            raise ConnectionError('Temporary error')\n"
                "        return 'recovered'\n"
                "    assert flaky() == 'recovered'\n"
                "    assert calls == 3\n\n"
                "def test_exhausted_retries_raises():\n"
                "    calls = 0\n"
                "    @retry(max_attempts=2)\n"
                "    def always_fail():\n"
                "        nonlocal calls\n"
                "        calls += 1\n"
                "        raise ValueError('Fatal')\n"
                "    with pytest.raises(ValueError):\n"
                "        always_fail()\n"
                "    assert calls == 2\n"
            )
        },
        "reference_fix": {
            "retrier.py": (
                "from functools import wraps\n\n"
                "def retry(max_attempts: int = 3):\n"
                "    \"\"\"Decorator that retries a function up to max_attempts times on Exception.\"\"\"\n"
                "    def decorator(func):\n"
                "        @wraps(func)\n"
                "        def wrapper(*args, **kwargs):\n"
                "            last_err = None\n"
                "            for _ in range(max_attempts):\n"
                "                try:\n"
                "                    return func(*args, **kwargs)\n"
                "                except Exception as e:\n"
                "                    last_err = e\n"
                "            if last_err is not None:\n"
                "                raise last_err\n"
                "        return wrapper\n"
                "    return decorator\n"
            )
        },
    },
]

def generate_all(target_dir: str = "tasks"):
    base_path = Path(target_dir)
    base_path.mkdir(parents=True, exist_ok=True)
    for task in TASKS:
        tid = task["task_id"]
        task_dir = base_path / tid
        task_dir.mkdir(parents=True, exist_ok=True)
        task_file = task_dir / "task.json"
        with open(task_file, "w", encoding="utf-8") as f:
            json.dump(task, f, indent=2)
        print(f"Generated task: {tid}")

if __name__ == "__main__":
    generate_all()
