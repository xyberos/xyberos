"""Validation report model and rendering."""

from __future__ import annotations

from dataclasses import dataclass, field

STATUS_PASS = "pass"
STATUS_FAIL = "fail"
STATUS_WARN = "warn"
STATUS_SKIP = "skip"

_ICONS = {STATUS_PASS: "✅", STATUS_FAIL: "❌", STATUS_WARN: "⚠️", STATUS_SKIP: "⏭️"}


@dataclass
class Check:
    """One named validation check."""

    name: str
    status: str = STATUS_FAIL
    detail: str = ""

    @property
    def passed(self) -> bool:
        return self.status == STATUS_PASS


@dataclass
class Report:
    """The ordered result of validating one plugin package."""

    checks: list[Check] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(check.passed for check in self.checks)

    @property
    def failures(self) -> list[Check]:
        return [check for check in self.checks if check.status == STATUS_FAIL]

    def add(self, name: str, status: str, detail: str = "") -> Check:
        check = Check(name=name, status=status, detail=detail)
        self.checks.append(check)
        return check

    def pass_(self, name: str, detail: str = "") -> Check:
        return self.add(name, STATUS_PASS, detail)

    def fail(self, name: str, detail: str = "") -> Check:
        return self.add(name, STATUS_FAIL, detail)

    def warn(self, name: str, detail: str = "") -> Check:
        return self.add(name, STATUS_WARN, detail)

    def skip(self, name: str, detail: str = "") -> Check:
        return self.add(name, STATUS_SKIP, detail)

    def render(self) -> str:
        """Render a human-readable validation report."""
        lines = ["Xyberos plugin validation", "-" * 40]
        for check in self.checks:
            icon = _ICONS.get(check.status, "•")
            detail = f" — {check.detail}" if check.detail else ""
            lines.append(f"{icon} {check.name}: {check.status.upper()}{detail}")
        lines.append("-" * 40)
        lines.append(f"Result: {'PASS' if self.passed else 'FAIL'}")
        return "\n".join(lines)
