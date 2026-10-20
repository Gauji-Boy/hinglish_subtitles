"""
diarization.py - Local acoustic speaker diarization using MFCC voice feature clustering.
Clusters subtitle segments by speaker turn without external model downloads or cloud APIs.
"""

import os
import numpy as np
from typing import List, Dict, Any, Optional
import librosa
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import silhouette_score


def extract_segment_features(
    y: np.ndarray,
    sr: int,
    start_sec: float,
    end_sec: float,
    n_mfcc: int = 13
) -> Optional[np.ndarray]:
    """
    Extracts mean + std of MFCCs and spectral centroids for a time window.
    """
    start_sample = max(0, int(round(start_sec * sr)))
    end_sample = min(len(y), int(round(end_sec * sr)))

    # Need at least ~0.2s of audio for stable spectral estimation
    if end_sample - start_sample < int(sr * 0.15):
        return None

    clip = y[start_sample:end_sample]
    if len(clip) == 0 or np.max(np.abs(clip)) < 1e-4:
        return None

    # Compute MFCCs (13 coefficients)
    mfcc = librosa.feature.mfcc(y=clip, sr=sr, n_mfcc=n_mfcc)
    mfcc_mean = np.mean(mfcc, axis=1)
    mfcc_std = np.std(mfcc, axis=1)

    # Compute Spectral Centroid
    centroid = librosa.feature.spectral_centroid(y=clip, sr=sr)
    cent_mean = np.mean(centroid)
    cent_std = np.std(centroid)

    # Combined feature vector (28-dim)
    feat = np.hstack([mfcc_mean, mfcc_std, cent_mean, cent_std])
    return feat


def diarize_segments(
    audio_path_or_array: Any,
    segments: List[Dict[str, Any]],
    sr: int = 16000,
    max_speakers: int = 4
) -> List[Dict[str, Any]]:
    """
    Assigns a 'speaker' identifier (e.g. 'Speaker 1', 'Speaker 2') to each subtitle segment.
    """
    if not segments:
        return []

    # 1. Load audio if path provided
    if isinstance(audio_path_or_array, str):
        if not os.path.exists(audio_path_or_array):
            return segments
        try:
            # Use soundfile directly for wav/flac
            y, actual_sr = librosa.load(audio_path_or_array, sr=sr, mono=True)
        except Exception:
            # Fallback to ffmpeg audio extraction for mp4/mkv/mov
            from hinglish_engine import extract_audio_numpy
            y = extract_audio_numpy(audio_path_or_array, sampling_rate=sr)
    elif isinstance(audio_path_or_array, np.ndarray):
        y = audio_path_or_array
        if y.ndim > 1:
            y = np.mean(y, axis=0)
    else:
        return segments

    # 2. Extract feature vector per segment
    features = []
    valid_indices = []

    for idx, seg in enumerate(segments):
        start = seg.get("start", 0.0)
        end = seg.get("end", start + 1.0)
        feat = extract_segment_features(y, sr, start, end)
        if feat is not None:
            features.append(feat)
            valid_indices.append(idx)

    # If too few valid segments or uniform sound, label everything as Speaker 1
    if len(features) < 3:
        for seg in segments:
            seg["speaker"] = "Speaker 1"
        return segments

    X = np.array(features)

    # Calculate pairwise distances in feature space
    # In a monologue, all segments have nearly identical acoustic features (dist < 40)
    # In genuine multi-speaker audio, different speakers have high acoustic distance (dist > 100)
    pairwise_dists = []
    for i in range(len(X)):
        for j in range(i + 1, len(X)):
            pairwise_dists.append(np.linalg.norm(X[i] - X[j]))
    max_dist = max(pairwise_dists) if pairwise_dists else 0.0

    if max_dist < 60.0:
        # Acoustic distance is too low for distinct speakers -> Monologue
        for seg in segments:
            seg["speaker"] = "Speaker 1"
        return segments

    # Normalize features for clustering
    mean = np.mean(X, axis=0)
    std = np.std(X, axis=0) + 1e-6
    X_norm = (X - mean) / std

    # 3. Determine best speaker count (k between 2 and max_speakers) using Silhouette Score
    best_k = 1
    best_score = -1.0
    best_labels = None

    max_k = min(max_speakers, len(X) - 1)
    if max_k >= 2:
        for k in range(2, max_k + 1):
            try:
                clusterer = AgglomerativeClustering(n_clusters=k)
                labels = clusterer.fit_predict(X_norm)
                score = silhouette_score(X_norm, labels)
                # Require silhouette > 0.18 to avoid false splitting on single-speaker monologues
                if score > 0.18 and score > best_score:
                    best_score = score
                    best_k = k
                    best_labels = labels
            except Exception:
                pass

    # 4. Map clusters to chronological Speaker 1, Speaker 2 labels
    speaker_map = {}
    current_speaker_num = 1

    if best_labels is not None and best_k > 1:
        # First seen cluster gets Speaker 1, second Speaker 2, etc.
        for cluster_id in best_labels:
            if cluster_id not in speaker_map:
                speaker_map[cluster_id] = f"Speaker {current_speaker_num}"
                current_speaker_num += 1

        for local_idx, orig_idx in enumerate(valid_indices):
            cluster_id = best_labels[local_idx]
            segments[orig_idx]["speaker"] = speaker_map[cluster_id]
    else:
        for seg in segments:
            seg["speaker"] = "Speaker 1"

    # Fill in any segment that was too short for features with previous segment's speaker
    last_speaker = "Speaker 1"
    for seg in segments:
        if "speaker" not in seg:
            seg["speaker"] = last_speaker
        else:
            last_speaker = seg["speaker"]

    return segments
