import re
from collections.abc import Mapping, Sequence

_CSS_RULE = re.compile(r"(?P<selectors>[^{}]+)\{(?P<body>[^{}]*)\}")


def _normalize(value: str) -> str:
    return " ".join(value.split())


def _matching_rule_declarations(css: str, selectors: Sequence[str]) -> tuple[dict[str, str], ...]:
    expected_selectors = frozenset(_normalize(selector) for selector in selectors)
    matches: list[dict[str, str]] = []

    for rule in _CSS_RULE.finditer(css):
        actual_selectors = frozenset(
            _normalize(selector) for selector in rule.group("selectors").split(",")
        )
        if actual_selectors != expected_selectors:
            continue

        declarations: dict[str, str] = {}
        for declaration in rule.group("body").split(";"):
            if ":" not in declaration:
                continue
            name, value = declaration.split(":", 1)
            declarations[_normalize(name)] = _normalize(value)
        matches.append(declarations)

    return tuple(matches)


def assert_css_rule(
    css: str,
    selectors: Sequence[str],
    expected_declarations: Mapping[str, str],
) -> None:
    """Assert a static declaration on one exact selector group, ignoring formatting."""
    rules = _matching_rule_declarations(css, selectors)
    selector_label = ", ".join(selectors)
    assert rules, f"CSS rule not found for exact selector group: {selector_label}"

    normalized_expected = {
        _normalize(name): _normalize(value) for name, value in expected_declarations.items()
    }
    for declarations in rules:
        if all(declarations.get(name) == value for name, value in normalized_expected.items()):
            return

    expected_label = ", ".join(
        f"{name}: expected {value!r}" for name, value in normalized_expected.items()
    )
    raise AssertionError(
        f"CSS rule {selector_label} does not satisfy {expected_label}; "
        f"matching declarations: {rules!r}"
    )
