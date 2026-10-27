"""Model registry tests - MOCKED Nightshift client (no network)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.config import Settings
from app.services.model_registry import ModelRegistry
from app.services.nightshift_client import (
    NightshiftClient, NightshiftQueryError, NightshiftResponse, NightshiftTimeoutError)

LIGHTNING = "nvidia/nemotron-3.5-lightning-30b-a3b"
ULTRA = "nvidia/nemotron-3-ultra-550b-a55b"
EMBED = "nvidia/nemotron-3-embed-1b"


def _cfg(**kw) -> Settings:
    base = dict(nightshift_model=LIGHTNING, nightshift_api_key="test-token", nightshift_model_skeptic=ULTRA,
                nightshift_model_planner="", nightshift_model_finder="", nightshift_model_reporter="", nightshift_model_embedding=EMBED, nightshift_model_rerank="")
    base.update(kw)
    return Settings(**base)


def _resp(model: str) -> NightshiftResponse:
    return NightshiftResponse(content="{}", model=model, provider="nvidia", latency_ms=3.0, usage={"completion_tokens": 7})


def _client(models, generate=None) -> MagicMock:
    c = MagicMock(spec=NightshiftClient)
    c.list_models.return_value = models
    if generate:
        c.generate.side_effect = generate
    return c


def test_role_routing_uses_verified_models_and_lightning_default():
    reg = ModelRegistry(_cfg(), _client([LIGHTNING, ULTRA, EMBED]))
    assert reg.assignment("planner").effective_model == LIGHTNING
    assert reg.assignment("reporter").effective_model == LIGHTNING
    sk = reg.assignment("skeptic")
    assert (sk.effective_model, sk.status, sk.fallback_model) == (ULTRA, "verified", LIGHTNING)


def test_unlisted_model_falls_back_and_says_so():
    reg = ModelRegistry(_cfg(), _client([LIGHTNING]))
    a = reg.assignment("skeptic")
    assert a.status == "fallback" and a.effective_model == LIGHTNING
    assert ULTRA in a.reason
    client = reg._client
    client.generate.return_value = _resp(LIGHTNING)
    _, rec = reg.generate("skeptic", [{"role": "user", "content": "x"}])
    assert rec.fallback_used and rec.requested_model == LIGHTNING and ULTRA in rec.fallback_reason


def test_specialist_failure_retries_once_on_fallback_and_records_it():
    calls = []

    def gen(**kw):
        calls.append(kw["model"])
        if kw["model"] == ULTRA:
            raise NightshiftTimeoutError("slow")
        return _resp(LIGHTNING)

    reg = ModelRegistry(_cfg(), _client([LIGHTNING, ULTRA], gen))
    resp, rec = reg.generate("skeptic", [{"role": "user", "content": "x"}])
    assert calls == [ULTRA, LIGHTNING]
    assert rec.fallback_used and "failed" in rec.fallback_reason
    assert rec.reported_model == LIGHTNING          # reported model comes from the response, not the plan
    assert rec.completion_tokens == 7


def test_reported_model_is_taken_from_response_and_mismatch_is_visible():
    reg = ModelRegistry(_cfg(), _client([LIGHTNING, ULTRA], lambda **kw: _resp("someone/else")))
    _, rec = reg.generate("skeptic", [{"role": "user", "content": "x"}])
    assert rec.requested_model == ULTRA and rec.reported_model == "someone/else" and rec.routed_as_requested is False


def test_fallback_failure_raises_structured_error():
    reg = ModelRegistry(_cfg(), _client([LIGHTNING], lambda **kw: (_ for _ in ()).throw(NightshiftQueryError("boom"))))
    with pytest.raises(NightshiftQueryError):
        reg.generate("planner", [{"role": "user", "content": "x"}])


def test_rerank_never_enabled_without_verified_route():
    reg = ModelRegistry(_cfg(), _client([LIGHTNING]))
    a = reg.assignment("rerank")
    assert a.status == "unavailable" and a.effective_model is None
    reg2 = ModelRegistry(_cfg(nightshift_model_rerank="nvidia/made-up-rerank"), _client([LIGHTNING]))
    assert reg2.assignment("rerank").effective_model is None


def test_embedding_requires_listing_and_working_route():
    client = _client([LIGHTNING, EMBED])
    reg = ModelRegistry(_cfg(), client)
    assert reg.assignment("embedding").status == "unverified"
    client.embed.side_effect = NightshiftQueryError("Nightshift embeddings returned HTTP 404")
    reg.probe_embeddings()
    a = reg.assignment("embedding")
    assert a.status == "unavailable" and "404" in a.reason and a.effective_model is None
    client.embed.side_effect = None
    client.embed.return_value = [[0.1, 0.2]]
    reg.probe_embeddings()
    assert reg.assignment("embedding").status == "verified"


def test_catalog_unavailable_is_reported_not_assumed():
    c = MagicMock(spec=NightshiftClient)
    c.list_models.side_effect = NightshiftQueryError("down")
    reg = ModelRegistry(_cfg(), c)
    assert reg.assignment("skeptic").status == "unverified"
    rep = reg.report()
    assert rep["catalog_checked"] is False and "down" in rep["catalog_error"]


def test_chat_roles_only():
    reg = ModelRegistry(_cfg(), _client([LIGHTNING]))
    with pytest.raises(ValueError):
        reg.generate("embedding", [])


def test_env_variable_names_in_env_example_actually_load(monkeypatch):
    monkeypatch.setenv("NIGHTSHIFT_MODEL_SKEPTIC", "nvidia/some-other-model")
    monkeypatch.setenv("NIGHTSHIFT_MODEL_RERANK", "nvidia/x-rerank")
    monkeypatch.setenv("WORKFLOW_MAX_ITERATIONS", "5")
    s = Settings()
    assert s.nightshift_model_skeptic == "nvidia/some-other-model" and s.nightshift_model_rerank == "nvidia/x-rerank"
    assert s.workflow_max_iterations == 5
