"""Tests for the RFC-0016 Phase 3 trainer (offline distillation + artifacts)."""

import pytest

from xyberos.contracts import Episode, Intent
from xyberos.experience import InMemoryExperience
from xyberos.runtime.context import CognitiveContext
from xyberos.trainer import Trainer, engine_from_config, export_dataset
from xyberos.utils import intent_accuracy

_VOCAB = ("refund", "hello", "hours")


def _embedder(text):
    vector = [0.0] * len(_VOCAB)
    for word in text.lower().split():
        for index, term in enumerate(_VOCAB):
            if term in word or word in term:
                vector[index] += 1.0
    return vector


def _experience():
    store = InMemoryExperience()
    for prompt, intent_name in [
        ("please refund my order", "refund"),
        ("I want a refund", "refund"),
        ("hello there", "greeting"),
        ("what are your hours", "faq"),
    ]:
        episode = store.record(
            Episode(prompt=prompt, intent=Intent(name=intent_name), outcome="success")
        )
        store.feedback(episode.id, 1.0)
    return store


def test_export_dataset_extracts_prompt_label_rows():
    dataset = export_dataset(_experience())

    assert ("please refund my order", "refund") in dataset
    assert ("hello there", "greeting") in dataset


def test_trainer_embedding_distills_and_classifies():
    engine = Trainer(export_dataset(_experience())).train_intent_embedding(_embedder)

    assert (
        intent_accuracy(
            engine,
            [("please refund", "refund"), ("hello", "greeting"), ("hours?", "faq")],
        )
        == 1.0
    )


def test_trainer_embedding_artifact_round_trips(tmp_path):
    path = str(tmp_path / "model.json")
    trainer = Trainer(export_dataset(_experience()))
    trainer.save(path)

    engine = Trainer.load(path, embedder=_embedder)

    assert engine.classify(CognitiveContext("please refund")).name == "refund"


def test_engine_from_config_loads_model(tmp_path):
    path = str(tmp_path / "model.json")
    Trainer(export_dataset(_experience())).save(path)

    engine = engine_from_config({"learning.model": path}, embedder=_embedder)

    assert engine is not None
    assert engine.classify(CognitiveContext("hello")).name == "greeting"


def test_engine_from_config_returns_none_without_model():
    assert engine_from_config({}) is None


def test_trainer_requires_non_empty_dataset():
    with pytest.raises(ValueError):
        Trainer([])


def test_trainer_embedding_load_requires_embedder(tmp_path):
    path = str(tmp_path / "model.json")
    Trainer(export_dataset(_experience())).save(path)

    with pytest.raises(ValueError):
        Trainer.load(path)


def test_trainer_sklearn_round_trip(tmp_path):
    pytest.importorskip("sklearn")
    path = str(tmp_path / "model.joblib")
    trainer = Trainer(export_dataset(_experience()))

    trainer.save(path, algorithm="sklearn", embedder=_embedder)
    engine = Trainer.load(path)

    assert engine.classify(CognitiveContext("hello")).name == "greeting"
