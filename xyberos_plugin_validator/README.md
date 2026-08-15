# xyberos-plugin-validator

Static + **live-kernel** validation for Xyberos plugins.

`xyberos plugin validate` (from `xyberos-cli`) reports, per check:
`structure`, `contract`, `configuration`, `testing`, `documentation`,
`compatibility` — then ends with `Result: PASS` or `Result: FAIL`.

## Checks

- **structure** — the expected files exist (`pyproject.toml`, package dir, tests)
- **contract** — the exported plugin is a `Plugin`, has a name, is concrete,
  and implements the abstract members of its contract
- **configuration** — a `xyberos.plugins` entry point is declared
- **testing** — test files exist (and can run, when invoked with `--run-tests`)
- **documentation** — a `README.md` exists
- **compatibility** — the plugin imports and **registers/unregisters against a
  real `create_app()` in an isolated subprocess** (live-kernel check)

The live check runs in a `subprocess` so validation never mutates the caller's
kernel or process state.

```python
from xyberos_plugin_validator import validate_plugin

report = validate_plugin(".")
print(report.render())
print("PASS" if report.passed else "FAIL")
```
