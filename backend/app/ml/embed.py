"""Multilingual sentence embeddings (ONNX via fastembed, CPU only, no PyTorch).

Optional: if fastembed or the model files are unavailable, or SAMAJSEVAK_EMBEDDINGS=0,
`available()` is False and the engine falls back to TF-IDF only.
"""
import hashlib
import os
from pathlib import Path

import numpy as np

MODEL = os.getenv("SAMAJSEVAK_EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
CACHE_DIR = Path(os.getenv("FASTEMBED_CACHE_PATH", Path(__file__).resolve().parents[2] / "models" / "fastembed_cache"))
MIN_MEMORY_MB = 1024  # the model plus ONNX Runtime need about 0.5 GB on top of the app


def _memory_limit_mb():
    """The container's memory limit (cgroup v2, then v1), or None when there is none / not Linux."""
    for path in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        try:
            value = Path(path).read_text().strip()
        except OSError:
            continue
        if value.isdigit():
            return int(value) / 2 ** 20
    return None


def _disabled() -> bool:
    """SAMAJSEVAK_EMBEDDINGS=0/1 decides when set. Unset: on, except in a container too small to hold
    the model (a 512 MB free instance is killed for running out of memory during startup)."""
    setting = os.getenv("SAMAJSEVAK_EMBEDDINGS")
    if setting is not None:
        return setting == "0"
    limit = _memory_limit_mb()
    if limit is not None and limit < MIN_MEMORY_MB:
        print(f"[embed] container memory limit is {limit:.0f} MB; embeddings off, using TF-IDF only")
        return True
    return False


_model = None
_failed = _disabled()
_memo: dict[str, np.ndarray] = {}
_unsaved = 0
DISK_CACHE = CACHE_DIR.parent / "embedding_cache.npz"  # vectors keyed by text hash; safe to delete


def _load():
    global _model, _failed
    if _model is None and not _failed:
        try:
            from fastembed import TextEmbedding
            _model = TextEmbedding(MODEL, cache_dir=str(CACHE_DIR))
            load_cache()
        except Exception as e:  # not installed / no network on first run
            _failed = True
            print(f"[embed] embeddings disabled ({e.__class__.__name__}: {e}); using TF-IDF only")
    return _model


def available() -> bool:
    return _load() is not None


def embed(texts: list[str]) -> np.ndarray:
    """L2-normalised vectors, one row per text. Repeated texts are served from memory."""
    keys = [hashlib.sha1(t.encode()).hexdigest() for t in texts]
    global _unsaved
    todo = {k: t for k, t in zip(keys, texts) if k not in _memo}
    if todo:
        vecs = np.array(list(_load().embed(list(todo.values()))), dtype=np.float32)
        vecs /= np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9
        if len(_memo) > 20000:
            _memo.clear()
        _memo.update(zip(todo, vecs))
        _unsaved += len(todo)
    return np.array([_memo[k] for k in keys])


def load_cache():
    if DISK_CACHE.exists() and not _memo:
        with np.load(DISK_CACHE) as z:
            if str(z["model"]) == MODEL:
                _memo.update(zip(z["keys"].tolist(), z["vecs"]))


def save_cache(min_new: int = 50):
    """Persist vectors so training and restarts do not re-embed; skipped for a handful of new texts."""
    global _unsaved
    if _unsaved >= min_new:
        np.savez(DISK_CACHE, model=MODEL, keys=np.array(list(_memo)), vecs=np.array(list(_memo.values())))
        _unsaved = 0
