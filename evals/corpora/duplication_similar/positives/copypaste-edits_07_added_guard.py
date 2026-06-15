# why: positive - second function adds one early-return guard clause to an otherwise copied body; same core algorithm, an extract-helper candidate.
from __future__ import annotations


def normalise_scores(samples, ceiling):
    scaled = []
    largest = max(sample.value for sample in samples)
    for sample in samples:
        ratio = sample.value / largest
        scaled.append(ratio * ceiling)
    average = sum(scaled) / len(scaled)
    return scaled, average


def normalise_weights(samples, ceiling):
    if not samples:
        return [], 0.0
    scaled = []
    largest = max(sample.value for sample in samples)
    for sample in samples:
        ratio = sample.value / largest
        scaled.append(ratio * ceiling)
    average = sum(scaled) / len(scaled)
    return scaled, average
