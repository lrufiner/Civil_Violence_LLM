from decision.types import DecisionResult
from metrics.collector import PerformanceRecorder
from model import ThreadSafeDataCollector


def test_recorder_incremental_stats_match_full_summary():
    recorder = PerformanceRecorder()
    recorder.record(1, 1, DecisionResult(active=True, probability=1.0, source="rule", latency_ms=2.0))
    recorder.record(1, 2, DecisionResult(active=False, probability=0.0, source="rule", latency_ms=4.0))
    recorder.record(1, 3, DecisionResult(active=False, probability=0.0, source="llm", latency_ms=0.0, from_cache=True))
    recorder.record(1, 4, DecisionResult.failure("llm", 9.0, RuntimeError("timeout")))

    assert recorder.error_count() == 1
    assert recorder.mean_latency_ms() == recorder.latency_summary()["mean_ms"] == 3.0


def test_datacollector_ignores_row_being_collected():
    collector = ThreadSafeDataCollector(model_reporters={"a": lambda m: 1, "b": lambda m: 2})
    # Simula una lectura desde el hilo de la UI a mitad de `collect()`: "a" ya tiene la fila nueva, "b" todavía no.
    collector.model_vars = {"a": [1, 1], "b": [2]}

    df = collector.get_model_vars_dataframe()

    assert len(df) == 1
    assert df.to_dict("list") == {"a": [1], "b": [2]}


def test_recorder_stats_by_source_separate_rule_from_llm():
    recorder = PerformanceRecorder()
    recorder.record(1, 1, DecisionResult(active=False, probability=0.0, source="rule", latency_ms=0.01))
    recorder.record(1, 2, DecisionResult(active=True, probability=0.8, source="llm:x", latency_ms=1000.0))
    recorder.record(1, 3, DecisionResult(active=True, probability=0.8, source="llm:x", latency_ms=0.0, from_cache=True))

    stats = recorder.by_source()

    assert stats["rule"].decisions == 1
    assert (stats["llm:x"].decisions, stats["llm:x"].cache_hits, stats["llm:x"].mean_latency_ms) == (2, 1, 1000.0)
