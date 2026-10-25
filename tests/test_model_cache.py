"""Concurrency contract for the Whisper model cache.

`api_transcribe` is a sync endpoint, so Starlette runs every request on a worker
thread. Two windows, or one window plus a second tab on the same port, reach
`get_model` concurrently. These tests pin what that may and may not do:

  * a cached model is loaded once and handed out as the same object;
  * concurrent cold misses build exactly one model;
  * reading the cache while another size is loading never raises;
  * `single_job` serialises whole jobs, which is what makes the one-slot cache
    swap in `get_model` safe.
"""
import sys
import threading
import time
import types

import pytest

import hinglish_upgrades as hu


class StubModel:
    """Slow-to-construct stand-in for faster_whisper.WhisperModel.

    Real weight loading takes seconds; without the delay the interleavings this
    file checks for close on their own and the tests would pass on broken code.
    """

    built = []
    active = 0
    max_active = 0
    delay = 0.0
    guard = threading.Lock()

    def __init__(self, size, device=None, compute_type=None):
        cls = type(self)
        with cls.guard:
            cls.built.append(size)
            cls.active += 1
            cls.max_active = max(cls.max_active, cls.active)
        try:
            time.sleep(cls.delay)
            self.size = size
            self.device = device
        finally:
            with cls.guard:
                cls.active -= 1

    @classmethod
    def reset(cls, delay=0.0):
        with cls.guard:
            cls.built = []
            cls.active = 0
            cls.max_active = 0
            cls.delay = delay

    def transcribe(self, *args, **kwargs):
        return [], None


@pytest.fixture
def stub(monkeypatch):
    module = types.ModuleType("faster_whisper")
    module.WhisperModel = StubModel
    monkeypatch.setitem(sys.modules, "faster_whisper", module)
    hu._MODELS.clear()
    StubModel.reset()
    yield StubModel
    hu._MODELS.clear()
    StubModel.reset()


def _run(targets, timeout=10):
    threads = [threading.Thread(target=t) for t in targets]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout)
    assert not any(thread.is_alive() for thread in threads), "a worker hung"


def test_a_cached_model_is_loaded_once(stub):
    first = hu.get_model("medium", "cuda", "float16")
    second = hu.get_model("medium", "cuda", "float16")

    assert first is second
    assert stub.built == ["medium"]


def test_concurrent_cold_misses_build_one_model(stub):
    stub.reset(delay=0.2)
    handed_out, errors = [], []

    def call():
        try:
            handed_out.append(hu.get_model("medium", "cuda", "float16"))
        except BaseException as exc:              # noqa: BLE001 - the test reports it
            errors.append(exc)

    _run([call] * 4)

    assert errors == []
    assert stub.built == ["medium"], "four cold misses must load one model"
    assert len({id(model) for model in handed_out}) == 1
    assert stub.max_active == 1


def test_reading_the_cache_while_another_size_loads_never_raises(stub):
    # The old code tested `key not in _MODELS`, then dereferenced `_MODELS[key]`
    # on the next line. A different size clearing the dict in between turned a
    # cache hit into a KeyError, and the request into a 500.
    stub.reset(delay=0.2)
    hu.get_model("medium", "cuda", "float16")
    errors = []

    def switch_size():
        try:
            hu.get_model("large-v3", "cuda", "float16")
        except BaseException as exc:              # noqa: BLE001
            errors.append(exc)

    def read_cache():
        for _ in range(2):
            try:
                hu.get_model("medium", "cuda", "float16")
            except BaseException as exc:          # noqa: BLE001
                errors.append(exc)

    _run([switch_size, read_cache])

    assert errors == [], f"concurrent cache access raised: {errors!r}"
    assert stub.max_active == 1, "two models were built at once"
    assert len(hu._MODELS) == 1, "the cache keeps a single slot"


def test_switching_size_drops_the_previous_key(stub):
    hu.get_model("medium", "cuda", "float16")
    hu.get_model("large-v3", "cuda", "float16")

    assert list(hu._MODELS) == [("large-v3", "cuda", "float16")]


def test_single_job_serialises_jobs(stub):
    events = []

    @hu.single_job
    def job(name):
        events.append(("start", name))
        time.sleep(0.15)
        events.append(("end", name))
        return name

    results = []
    _run([lambda n=name: results.append(job(n)) for name in ("first", "second")])

    assert [kind for kind, _ in events] == ["start", "end", "start", "end"], (
        "jobs overlapped: " + repr(events)
    )
    assert sorted(results) == ["first", "second"]


def test_single_job_preserves_the_wrapped_function(stub):
    @hu.single_job
    def add(a, b=1):
        return a + b

    assert add(1, b=2) == 3
    assert add.__name__ == "add"
    assert hasattr(add, "__wrapped__")


def test_both_engines_run_under_the_job_lock():
    # If a future edit drops the decorator, the cache swap loses its guarantee
    # while these tests keep passing, so pin it at the entry points.
    from hinglish_engine import generate_subtitles
    from hindi_to_english_engine import generate_english_subtitles

    for entry in (generate_subtitles, generate_english_subtitles):
        assert hasattr(entry, "__wrapped__"), f"{entry.__name__} is not serialised"


def test_a_second_transcription_gets_409_instead_of_waiting(stub):
    from fastapi.testclient import TestClient
    from server import app

    assert hu.claim_job_slot() is True
    try:
        client = TestClient(app)
        response = client.post(
            "/api/transcribe",
            files={"video": ("clip.mp4", b"not really a video", "video/mp4")},
            data={"language": "mixed", "model_size": "medium", "device": "auto"},
        )
    finally:
        hu.release_job_slot()

    assert response.status_code == 409
    assert "already running" in response.json()["detail"]


def test_the_endpoint_slot_is_released_when_the_job_fails():
    from server import _single_job_endpoint

    @_single_job_endpoint
    def boom():
        raise RuntimeError("engine blew up")

    with pytest.raises(RuntimeError):
        boom()

    # The slot must be free again, or every later transcription would 409.
    assert hu.claim_job_slot() is True
    hu.release_job_slot()
