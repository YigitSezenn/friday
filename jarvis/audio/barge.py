"""Ses seviyesi ölçümü."""

from __future__ import annotations

import array


def peak(pcm: bytes) -> float:
    usable = pcm[: len(pcm) // 2 * 2]
    if not usable:
        return 0.0
    samples = array.array("h")
    samples.frombytes(usable)
    if not samples:
        return 0.0
    return max(abs(sample) for sample in samples) / 32768.0
