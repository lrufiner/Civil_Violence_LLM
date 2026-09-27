"""Registro de cada decisión tomada durante una corrida, para medir desempeño."""

from __future__ import annotations

import csv
import statistics
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path
from typing import Dict, List, Optional, Union

from decision.types import DecisionResult


@dataclass
class DecisionRecord:
    step: int
    agent_id: int
    source: str
    active: bool
    probability: float
    latency_ms: float
    confidence: Optional[float]
    error: Optional[str]
    from_cache: bool
    explanation: Optional[str] = None


@dataclass
class SourceStats:
    """Totales acumulados de un motor de decisión (`DecisionResult.source`)."""

    decisions: int = 0
    errors: int = 0
    cache_hits: int = 0
    latency_sum_ms: float = 0.0
    latency_count: int = 0

    @property
    def mean_latency_ms(self) -> float:
        """Latencia media de consultas reales (sin errores ni hits de cache)."""
        return self.latency_sum_ms / self.latency_count if self.latency_count else 0.0


class PerformanceRecorder:
    """Acumula un `DecisionRecord` por cada decisión tomada durante una corrida de simulación."""

    def __init__(self) -> None:
        self._records: List[DecisionRecord] = []
        # Acumuladores O(1) para los reporters que se evalúan en cada paso de la simulación
        self._error_count = 0
        self._latency_sum_ms = 0.0
        self._latency_count = 0
        self._by_source: Dict[str, SourceStats] = {}

    def record(self, step: int, agent_id: int, result: DecisionResult) -> None:
        if result.error is not None:
            self._error_count += 1
        elif not result.from_cache:
            self._latency_sum_ms += result.latency_ms
            self._latency_count += 1
        stats = self._by_source.setdefault(result.source, SourceStats())
        stats.decisions += 1
        if result.error is not None:
            stats.errors += 1
        elif result.from_cache:
            stats.cache_hits += 1
        else:
            stats.latency_sum_ms += result.latency_ms
            stats.latency_count += 1
        self._records.append(
            DecisionRecord(
                step=step,
                agent_id=agent_id,
                source=result.source,
                active=result.active,
                probability=result.probability,
                latency_ms=result.latency_ms,
                confidence=result.confidence,
                error=result.error,
                from_cache=result.from_cache,
                explanation=result.explanation,
            )
        )

    def __len__(self) -> int:
        return len(self._records)

    @property
    def records(self) -> List[DecisionRecord]:
        return list(self._records)

    def by_source(self) -> Dict[str, SourceStats]:
        """Totales por motor, en O(1) por paso (útil en modo hybrid, donde se mezclan regla y LLM/Jev)."""
        return {source: replace(stats) for source, stats in self._by_source.items()}

    def error_count(self) -> int:
        return self._error_count

    def mean_latency_ms(self) -> float:
        """Latencia media de decisiones exitosas y no cacheadas (igual a `latency_summary()["mean_ms"]`)."""
        return self._latency_sum_ms / self._latency_count if self._latency_count else 0.0

    def error_rate(self) -> float:
        return self.error_count() / len(self._records) if self._records else 0.0

    def latency_summary(self) -> dict:
        latencies = sorted(r.latency_ms for r in self._records if r.error is None and not r.from_cache)
        if not latencies:
            return {"count": 0, "mean_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0}
        return {
            "count": len(latencies),
            "mean_ms": statistics.mean(latencies),
            "p50_ms": statistics.median(latencies),
            "p95_ms": latencies[int(0.95 * (len(latencies) - 1))],
        }

    def to_csv(self, path: Union[str, Path]) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [f.name for f in fields(DecisionRecord)]
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for record in self._records:
                writer.writerow(asdict(record))
