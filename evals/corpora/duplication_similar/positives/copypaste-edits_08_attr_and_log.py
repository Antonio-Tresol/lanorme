# why: positive - copy-paste drift combining an attribute swap (.read vs .write) with one extra metric line; both are incidental edits over a shared body.
from __future__ import annotations


def measure_read_latency(probe, samples):
    durations = []
    for _ in range(samples):
        start = probe.clock()
        probe.read()
        durations.append(probe.clock() - start)
    durations.sort()
    median = durations[len(durations) // 2]
    return median


def measure_write_latency(probe, samples):
    durations = []
    for _ in range(samples):
        start = probe.clock()
        probe.write()
        durations.append(probe.clock() - start)
    durations.sort()
    probe.emit("samples", samples)
    median = durations[len(durations) // 2]
    return median
