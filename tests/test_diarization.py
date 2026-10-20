"""
test_diarization.py - Automated tests for acoustic speaker diarization engine, server API, and UI integration.
"""

import os
import pytest
import numpy as np
from diarization import extract_segment_features, diarize_segments


def test_extract_segment_features_synthetic_audio():
    sr = 16000
    # 2 seconds of synthetic sine wave audio
    t = np.linspace(0, 2.0, int(sr * 2.0), endpoint=False)
    y = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    feat = extract_segment_features(y, sr, 0.0, 1.0)
    assert feat is not None
    assert isinstance(feat, np.ndarray)
    assert len(feat) == 28  # 13 mean + 13 std + 1 centroid mean + 1 centroid std


def test_extract_segment_features_too_short():
    sr = 16000
    y = np.zeros(16000, dtype=np.float32)
    # 0.05 seconds is too short
    feat = extract_segment_features(y, sr, 0.0, 0.05)
    assert feat is None


def test_diarize_segments_monologue():
    sr = 16000
    # 6 seconds of single speaker-like tone
    t = np.linspace(0, 6.0, int(sr * 6.0), endpoint=False)
    y = (0.4 * np.sin(2 * np.pi * 300 * t)).astype(np.float32)

    segments = [
        {"start": 0.0, "end": 1.5, "text": "Segment 1"},
        {"start": 1.8, "end": 3.2, "text": "Segment 2"},
        {"start": 3.5, "end": 5.0, "text": "Segment 3"}
    ]

    diarized = diarize_segments(y, segments, sr=sr)
    assert len(diarized) == 3
    for s in diarized:
        assert s["speaker"] == "Speaker 1"


def test_diarize_segments_dialogue():
    sr = 16000
    t1 = np.linspace(0, 2.0, int(sr * 2.0), endpoint=False)
    # Speaker 1: Low fundamental pitch (150 Hz)
    y1 = (0.5 * np.sin(2 * np.pi * 150 * t1)).astype(np.float32)

    # Speaker 2: High fundamental pitch (900 Hz)
    t2 = np.linspace(0, 2.0, int(sr * 2.0), endpoint=False)
    y2 = (0.5 * np.sin(2 * np.pi * 900 * t2)).astype(np.float32)

    y_dialogue = np.concatenate([y1, y2, y1, y2])

    segments = [
        {"start": 0.0, "end": 1.8, "text": "Speaker A turn 1"},
        {"start": 2.0, "end": 3.8, "text": "Speaker B turn 1"},
        {"start": 4.0, "end": 5.8, "text": "Speaker A turn 2"},
        {"start": 6.0, "end": 7.8, "text": "Speaker B turn 2"}
    ]

    diarized = diarize_segments(y_dialogue, segments, sr=sr)
    assert len(diarized) == 4
    # Ensure both Speaker 1 and Speaker 2 are identified
    speakers = {s["speaker"] for s in diarized}
    assert "Speaker 1" in speakers
    assert "Speaker 2" in speakers


def test_server_transcribe_accepts_enable_diarization():
    from fastapi.testclient import TestClient
    from server import app

    client = TestClient(app)
    openapi = app.openapi()
    schemas = openapi["components"]["schemas"]
    body_schema = schemas.get("Body_api_transcribe_api_transcribe_post", {})
    assert "enable_diarization" in body_schema.get("properties", {})
