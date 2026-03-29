"""
emotion_detector.py

Lightweight prosody-based emotion heuristic for short spoken audio clips.

Install dependencies:
    pip install numpy librosa soundfile

If librosa is hard to install on Windows, consider using conda or prebuilt wheels, or ask me for a lighter fallback.
"""
from typing import Dict, Any
import numpy as np
import librosa
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

DEFAULT_SR = 22050

def safe_mean(xs):
    xs = np.array(xs)
    xs = xs[~np.isnan(xs)]
    return float(xs.mean()) if xs.size > 0 else 0.0

def analyze_audio_array(y: np.ndarray, sr: int = DEFAULT_SR) -> Dict[str, Any]:
    if y.ndim > 1:
        y = librosa.to_mono(y)

    y_trim, _ = librosa.effects.trim(y, top_db=30)
    if y_trim.size < 256:
        return {"emotion": "neutral", "confidence": 0.4, "features": {}}

    hop_length = 512
    frame_length = 1024

    rms = librosa.feature.rms(y=y_trim, frame_length=frame_length, hop_length=hop_length)[0]
    mean_rms = float(np.mean(rms))
    std_rms = float(np.std(rms))

    spec_cent = librosa.feature.spectral_centroid(y=y_trim, sr=sr, hop_length=hop_length)[0]
    mean_cent = float(np.mean(spec_cent))

    try:
        onset_env = librosa.onset.onset_strength(y=y_trim, sr=sr)
        tempo = float(librosa.beat.tempo(onset_envelope=onset_env, sr=sr).mean())
    except Exception:
        tempo = 0.0

    try:
        f0 = librosa.yin(y_trim, fmin=50, fmax=600, sr=sr, frame_length=frame_length, hop_length=hop_length)
        mean_f0 = safe_mean(f0)
        std_f0 = float(np.nanstd(f0))
        voiced_ratio = float(np.sum(~np.isnan(f0)) / float(len(f0))) if len(f0) > 0 else 0.0
    except Exception:
        mean_f0 = 0.0
        std_f0 = 0.0
        voiced_ratio = 0.0

    features = {
        "mean_rms": mean_rms,
        "std_rms": std_rms,
        "mean_centroid": mean_cent,
        "tempo": tempo,
        "mean_f0": mean_f0,
        "std_f0": std_f0,
        "voiced_ratio": voiced_ratio,
        "duration_s": float(len(y_trim)) / float(sr)
    }

    emotion_scores = {"happy": 0.0, "neutral": 0.0, "sad": 0.0, "angry": 0.0, "anxious": 0.0, "pain": 0.0}

    rms_norm = mean_rms
    f0_val = mean_f0
    f0_var = std_f0
    cent = mean_cent
    vratio = voiced_ratio
    dur = features["duration_s"]

    if rms_norm > 0.05 and f0_val > 220 and cent > 2000:
        emotion_scores["happy"] += 0.8
    if rms_norm > 0.08 and f0_val > 180 and f0_var > 80:
        emotion_scores["angry"] += 0.8
    if f0_var > 60 and vratio < 0.6 and rms_norm > 0.04:
        emotion_scores["anxious"] += 0.7
    if rms_norm < 0.02 and f0_val > 0 and f0_val < 170:
        emotion_scores["sad"] += 0.9
    if f0_var > 100 and rms_norm > 0.03 and dur < 5:
        emotion_scores["pain"] += 0.5

    emotion_scores["neutral"] += 0.2
    if 0.03 < rms_norm < 0.06 and 160 < f0_val < 230:
        emotion_scores["happy"] += 0.1
    if rms_norm > 0.12:
        emotion_scores["angry"] += 0.3

    labels = list(emotion_scores.keys())
    vals = np.array([emotion_scores[k] for k in labels], dtype=float)
    if np.all(vals == 0):
        chosen = "neutral"
        conf = 0.5
    else:
        vals = np.maximum(vals, 0.0)
        s = vals.sum()
        probs = vals / s if s > 0 else np.ones_like(vals) / len(vals)
        idx = int(np.argmax(probs))
        chosen = labels[idx]
        conf = float(probs[idx])

    return {"emotion": chosen, "confidence": round(conf, 3), "features": features}

def analyze_file(path: str) -> Dict[str, Any]:
    try:
        y, sr = librosa.load(path, sr=DEFAULT_SR, mono=True)
    except Exception as e:
        return {"emotion": "neutral", "confidence": 0.0, "features": {"error": str(e)}}
    return analyze_audio_array(y, sr=sr)

if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 2:
        print("Usage: python emotion_detector.py <audio-file.wav>")
        raise SystemExit(1)
    out = analyze_file(sys.argv[1])
    print(json.dumps(out, indent=2))