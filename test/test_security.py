"""Tests for the Security service — kill switch, guardrails, and audit log."""

from __future__ import annotations

import pytest

from xyberos import Security, create_app
from xyberos.events.names import (
    SECURITY_KILL_DISENGAGED,
    SECURITY_KILL_ENGAGED,
)
from xyberos.exceptions.security import GuardrailTriggeredError, SecurityHaltError
from xyberos.kernel import Kernel
from xyberos.security import Guardrail, InMemoryAuditStore, KillSwitch, SqliteAuditStore

# ---------------------------------------------------------------------------
# KillSwitch
# ---------------------------------------------------------------------------

class TestKillSwitch:
    def test_defaults_inactive(self):
        ks = KillSwitch()
        assert ks.active is False
        assert ks.mode == "soft"
        assert ks.reason is None
        assert ks.activated_at is None

    def test_check_passes_when_inactive(self):
        ks = KillSwitch()
        ks.check()  # should not raise

    def test_engage_soft(self):
        ks = KillSwitch()
        ks.engage("testing", mode="soft")
        assert ks.active is True
        assert ks.mode == "soft"
        assert ks.reason == "testing"
        assert ks.activated_at is not None
        with pytest.raises(SecurityHaltError, match="testing"):
            ks.check()

    def test_engage_hard(self):
        ks = KillSwitch()
        ks.engage("emergency", mode="hard")
        assert ks.active is True
        assert ks.mode == "hard"
        with pytest.raises(SecurityHaltError, match="emergency"):
            ks.check()

    def test_engage_invalid_mode(self):
        ks = KillSwitch()
        with pytest.raises(ValueError, match="soft' or 'hard"):
            ks.engage(mode="invalid")

    def test_disengage(self):
        ks = KillSwitch()
        ks.engage("testing")
        assert ks.active is True
        ks.disengage()
        assert ks.active is False
        assert ks.mode == "soft"
        assert ks.reason is None
        assert ks.activated_at is None
        ks.check()  # should not raise

    def test_disengage_when_already_inactive(self):
        ks = KillSwitch()
        ks.disengage()  # no-op, no error
        assert ks.active is False

    def test_repr(self):
        ks = KillSwitch()
        assert "inactive" in repr(ks)
        ks.engage("test reason")
        assert "ACTIVE" in repr(ks)
        assert "test reason" in repr(ks)


# ---------------------------------------------------------------------------
# Guardrail
# ---------------------------------------------------------------------------

class TestGuardrail:
    def test_passes_when_check_returns_true(self):
        g = Guardrail("safe", lambda ctx: True)
        assert g.inspect(object()) is True

    def test_fails_when_check_returns_false(self):
        g = Guardrail("blocker", lambda ctx: False)
        assert g.inspect(object()) is False

    def test_invalid_name(self):
        with pytest.raises(ValueError):
            Guardrail("", lambda ctx: True)

    def test_non_callable_check(self):
        with pytest.raises(TypeError):
            Guardrail("bad", "not_a_callable")  # type: ignore[arg-type]

    def test_repr(self):
        g = Guardrail("my-guard", lambda ctx: True)
        assert "my-guard" in repr(g)


# ---------------------------------------------------------------------------
# Security service
# ---------------------------------------------------------------------------

class TestSecurity:
    def test_defaults(self):
        sec = Security()
        assert sec.kill_switch.active is False
        assert sec.guardrail_names == ()
        assert sec.audit_log == ()

    def test_engage_and_disengage_kill_switch(self):
        sec = Security()
        sec.engage_kill_switch("emergency maintenance")
        assert sec.kill_switch.active is True
        assert len(sec.audit_log) == 1
        assert sec.audit_log[0]["event"] == "kill_engaged"

        sec.disengage_kill_switch()
        assert sec.kill_switch.active is False
        assert sec.audit_log[1]["event"] == "kill_disengaged"

    def test_add_and_remove_guardrail(self):
        sec = Security()
        g = sec.add_guardrail(Guardrail("no-hack", lambda ctx: "hack" not in str(ctx)))
        assert sec.guardrail_names == ("no-hack",)

        removed = sec.remove_guardrail("no-hack")
        assert removed is g
        assert sec.guardrail_names == ()

    def test_remove_nonexistent_guardrail(self):
        sec = Security()
        with pytest.raises(KeyError):
            sec.remove_guardrail("nope")

    def test_guard_passes(self):
        sec = Security()
        sec.add_guardrail(Guardrail("pass", lambda ctx: True))
        sec.guard(object())  # should not raise

    def test_guard_blocks(self):
        sec = Security()
        sec.add_guardrail(Guardrail("block", lambda ctx: False))
        with pytest.raises(GuardrailTriggeredError, match="block"):
            sec.guard(object())

    def test_guard_blocks_via_exception(self):
        sec = Security()
        def check(ctx):
            raise GuardrailTriggeredError("bad-input", "contains threats")
        sec.add_guardrail(Guardrail("bad-input", check))
        with pytest.raises(GuardrailTriggeredError, match="bad-input"):
            sec.guard(object())
        assert sec.audit_log[0]["event"] == "guardrail_triggered"

    def test_block_request(self):
        sec = Security()
        sec.engage_kill_switch("test")
        with pytest.raises(SecurityHaltError, match="test"):
            sec.block_request(object())

    def test_name(self):
        sec = Security()
        assert sec.name == "security"

    def test_repr(self):
        sec = Security()
        assert "Security" in repr(sec)
        sec.add_guardrail(Guardrail("g1", lambda ctx: True))
        assert "guardrails=1" in repr(sec)

    def test_audit_log_is_immutable(self):
        sec = Security()
        sec.engage_kill_switch("test")
        log = sec.audit_log
        assert len(log) == 1
        # the returned tuple is a snapshot, not the live list
        sec.disengage_kill_switch()
        assert len(log) == 1  # unchanged


# ---------------------------------------------------------------------------
# Integration: Xyberos facade
# ---------------------------------------------------------------------------

class TestSecurityFacade:
    def test_app_exposes_security(self):
        app = create_app()
        assert app.security is not None
        assert app.security.kill_switch.active is False

    def test_kill_switch_blocks_chat(self):
        app = create_app()
        app.security.engage_kill_switch("emergency")
        with pytest.raises(SecurityHaltError, match="emergency"):
            app.chat("hello")

    def test_kill_switch_blocks_run(self):
        app = create_app()
        app.security.engage_kill_switch("down")
        with pytest.raises(SecurityHaltError, match="down"):
            app.run("hello")

    def test_disengaged_allows_chat(self):
        app = create_app()
        app.security.engage_kill_switch("test")
        app.security.disengage_kill_switch()
        result = app.chat("hello")
        assert result == "hello"  # EchoLLM default

    def test_guardrail_blocks_chat(self):
        app = create_app()
        app.security.add_guardrail(
            Guardrail("block-all", lambda ctx: False)
        )
        with pytest.raises(GuardrailTriggeredError, match="block-all"):
            app.chat("hello")

    def test_guardrail_allows_safe_prompt(self):
        app = create_app()
        app.security.add_guardrail(
            Guardrail("block-hack", lambda ctx: "hack" not in str(getattr(ctx, "prompt", "")))
        )
        result = app.chat("hello")
        assert result == "hello"


# ---------------------------------------------------------------------------
# Audit store
# ---------------------------------------------------------------------------

class TestAuditStore:
    def test_security_with_sqlite_audit_store_persists(self, tmp_path):
        path = str(tmp_path / "audit.db")
        store = SqliteAuditStore(path)
        security = Security(audit_store=store)
        security.engage_kill_switch("maintenance")
        security.disengage_kill_switch()
        store.close()

        reopened = SqliteAuditStore(path)
        assert [entry["event"] for entry in reopened.entries()] == [
            "kill_engaged",
            "kill_disengaged",
        ]
        reopened.close()

    def test_kernel_config_wires_persistent_audit_store(self, tmp_path):
        path = str(tmp_path / "audit.db")
        kernel = Kernel({"security.audit_path": path})
        assert isinstance(kernel.security.audit_store, SqliteAuditStore)
        kernel.security.engage_kill_switch("test")
        kernel.start()
        kernel.stop()

        reopened = SqliteAuditStore(path)
        assert any(entry["event"] == "kill_engaged" for entry in reopened.entries())
        reopened.close()

    def test_security_audit_store_property_exposes_backend(self):
        store = InMemoryAuditStore()
        security = Security(audit_store=store)

        assert security.audit_store is store


# ---------------------------------------------------------------------------
# Integration: async
# ---------------------------------------------------------------------------

class TestSecurityAsync:
    @pytest.mark.asyncio
    async def test_kill_switch_blocks_achat(self):
        app = create_app()
        app.security.engage_kill_switch("emergency")
        with pytest.raises(SecurityHaltError, match="emergency"):
            await app.achat("hello")

    @pytest.mark.asyncio
    async def test_kill_switch_blocks_arun(self):
        app = create_app()
        app.security.engage_kill_switch("down")
        with pytest.raises(SecurityHaltError, match="down"):
            await app.arun("hello")

    @pytest.mark.asyncio
    async def test_disengaged_allows_achat(self):
        app = create_app()
        app.security.engage_kill_switch("test")
        app.security.disengage_kill_switch()
        result = await app.achat("hello")
        assert result == "hello"


# ---------------------------------------------------------------------------
# Event integration
# ---------------------------------------------------------------------------

class TestSecurityEvents:
    def test_kill_engaged_event(self):
        app = create_app()
        events = []

        def listener(event):
            events.append(event.name)

        app.events.subscribe(SECURITY_KILL_ENGAGED, listener)
        app.security.engage_kill_switch("test")
        assert SECURITY_KILL_ENGAGED in events

    def test_kill_disengaged_event(self):
        app = create_app()
        events = []

        def listener(event):
            events.append(event.name)

        app.security.engage_kill_switch("test")
        app.events.subscribe(SECURITY_KILL_DISENGAGED, listener)
        app.security.disengage_kill_switch()
        assert SECURITY_KILL_DISENGAGED in events
