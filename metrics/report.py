"""Genera reportes comparativos (markdown + gráficos) de motores de decisión."""

from __future__ import annotations

import csv
import re
import statistics
from pathlib import Path
from typing import Dict, List, Union

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402 - backend debe fijarse antes de importar pyplot

_RUN_NAME_RE = re.compile(r"^(?P<engine>.+)_seed(?P<seed>\d+)_(?P<kind>decisions|timeseries)\.csv$")

# Precio de referencia en USD por cada 1000 decisiones (estimado, septiembre 2026).
# Fuente: documentación pública de cada proveedor / typesafe.ai (ver TECHNICAL.md para detalle y caveats).
PRICING_PER_1K_DECISIONS_USD = {
    "rule": 0.0,
    "ollama": 0.0,
    "openai": 0.15,
    "anthropic": 0.20,
    "jev": 0.0042,
}

# Características cualitativas relevadas manualmente (no medidas en la corrida local).
FEATURE_MATRIX = {
    "rule": {
        "Determinismo": "Total",
        "Latencia típica": "< 1 ms",
        "Riesgo de alucinación": "Ninguno",
        "Explicabilidad": "Total (fórmula cerrada)",
        "Requiere red/API key": "No",
        "Costo marginal": "Ninguno",
    },
    "ollama": {
        "Determinismo": "Bajo-medio (según temperature)",
        "Latencia típica": "1s - 8s (según hardware local)",
        "Riesgo de alucinación": "Medio (mitigado con salida estructurada)",
        "Explicabilidad": "Baja (texto libre)",
        "Requiere red/API key": "No (servidor local)",
        "Costo marginal": "Cómputo local, sin costo de API",
    },
    "openai": {
        "Determinismo": "Bajo-medio (según temperature)",
        "Latencia típica": "0.5s - 5s",
        "Riesgo de alucinación": "Medio (mitigado con salida estructurada)",
        "Explicabilidad": "Baja (texto libre)",
        "Requiere red/API key": "Sí (OPENAI_API_KEY)",
        "Costo marginal": "~$0.15 / 1000 decisiones (estimado)",
    },
    "anthropic": {
        "Determinismo": "Bajo-medio (según temperature)",
        "Latencia típica": "0.5s - 6s",
        "Riesgo de alucinación": "Medio (mitigado con salida estructurada)",
        "Explicabilidad": "Baja (texto libre)",
        "Requiere red/API key": "Sí (ANTHROPIC_API_KEY)",
        "Costo marginal": "~$0.20 / 1000 decisiones (estimado)",
    },
    "jev": {
        "Determinismo": "Medio (probabilístico, calibrado)",
        "Latencia típica": "70 ms - 500 ms",
        "Riesgo de alucinación": "Ninguno por construcción (salida tipada)",
        "Explicabilidad": "Media (probabilidad + confidence, sin razonamiento textual)",
        "Requiere red/API key": "Sí (TYPESAFE_API_KEY)",
        "Costo marginal": "~$0.0042 / 1000 decisiones",
    },
}


def discover_runs(results_dir: Union[str, Path]) -> Dict[str, Dict[str, List[Path]]]:
    """Agrupa los CSV de `results_dir` por engine -> {"decisions": [...], "timeseries": [...]}."""
    results_dir = Path(results_dir)
    runs: Dict[str, Dict[str, List[Path]]] = {}
    for csv_path in sorted(results_dir.glob("*.csv")):
        match = _RUN_NAME_RE.match(csv_path.name)
        if not match:
            continue
        runs.setdefault(match.group("engine"), {"decisions": [], "timeseries": []})[match.group("kind")].append(
            csv_path
        )
    return runs


def _read_csv_rows(paths: List[Path]) -> List[dict]:
    rows: List[dict] = []
    for path in paths:
        with path.open(newline="", encoding="utf-8") as fh:
            rows.extend(csv.DictReader(fh))
    return rows


def summarize_engine(decision_rows: List[dict]) -> dict:
    latencies = [
        float(r["latency_ms"])
        for r in decision_rows
        if r.get("error") in ("", None) and r.get("from_cache") in ("False", "", None)
    ]
    errors = sum(1 for r in decision_rows if r.get("error") not in ("", None))
    total = len(decision_rows)
    latencies.sort()
    return {
        "total_decisions": total,
        "error_rate": errors / total if total else 0.0,
        "mean_latency_ms": statistics.mean(latencies) if latencies else 0.0,
        "p95_latency_ms": latencies[int(0.95 * (len(latencies) - 1))] if latencies else 0.0,
    }


def plot_latency_comparison(summaries: Dict[str, dict], output_path: Union[str, Path]) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    engines = list(summaries.keys())
    means = [summaries[e]["mean_latency_ms"] for e in engines]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(engines, means, color="#648FFF")
    ax.set_ylabel("Latencia media por decisión (ms, escala log)")
    ax.set_title("Latencia por motor de decisión")
    ax.set_yscale("log")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_active_citizens_timeseries(timeseries_by_engine: Dict[str, List[dict]], output_path: Union[str, Path]) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    for engine, rows in timeseries_by_engine.items():
        steps = list(range(len(rows)))
        actives = [float(r.get("active_citizens", 0) or 0) for r in rows]
        ax.plot(steps, actives, label=engine)
    ax.set_xlabel("Paso de simulación")
    ax.set_ylabel("Ciudadanos activos")
    ax.set_title("Dinámica de ciudadanos activos por motor de decisión")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def _markdown_table(headers: List[str], rows: List[List[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)


def generate_comparison_report(results_dir: Union[str, Path], output_md_path: Union[str, Path]) -> Path:
    """Lee los CSV crudos de `results_dir`, calcula métricas y escribe un reporte markdown."""
    results_dir = Path(results_dir)
    output_md_path = Path(output_md_path)
    charts_dir = output_md_path.parent / "charts"

    runs = discover_runs(results_dir)
    if not runs:
        raise FileNotFoundError(f"No se encontraron CSVs de resultados en {results_dir}")

    summaries: Dict[str, dict] = {}
    timeseries_by_engine: Dict[str, List[dict]] = {}
    for engine, files in runs.items():
        summaries[engine] = summarize_engine(_read_csv_rows(files["decisions"]))
        if files["timeseries"]:
            timeseries_by_engine[engine] = _read_csv_rows(files["timeseries"][:1])

    charts = [plot_latency_comparison(summaries, charts_dir / "latency_comparison.png")]
    if timeseries_by_engine:
        charts.append(
            plot_active_citizens_timeseries(timeseries_by_engine, charts_dir / "active_citizens_timeseries.png")
        )

    perf_rows = [
        [
            engine,
            s["total_decisions"],
            f"{s['error_rate']:.1%}",
            f"{s['mean_latency_ms']:.2f}",
            f"{s['p95_latency_ms']:.2f}",
            f"{PRICING_PER_1K_DECISIONS_USD.get(engine, 0.0) * (s['total_decisions'] / 1000):.4f}",
        ]
        for engine, s in sorted(summaries.items())
    ]
    perf_table = _markdown_table(
        ["Motor", "Decisiones", "Tasa de error", "Latencia media (ms)", "P95 latencia (ms)", "Costo estimado (USD)"],
        perf_rows,
    )

    feature_keys = list(next(iter(FEATURE_MATRIX.values())).keys())
    feature_rows = [
        [engine] + [FEATURE_MATRIX.get(engine, {}).get(k, "—") for k in feature_keys]
        for engine in sorted(summaries.keys())
    ]
    feature_table = _markdown_table(["Motor"] + feature_keys, feature_rows)

    lines = [
        "# Reporte comparativo de motores de decisión",
        "",
        "Generado automáticamente por `metrics/report.py` a partir de corridas de `experiments/run_comparison.py`.",
        "",
        "## Desempeño medido",
        "",
        perf_table,
        "",
        f"![Latencia por motor]({charts[0].relative_to(output_md_path.parent).as_posix()})",
        "",
    ]
    if len(charts) > 1:
        lines += [f"![Ciudadanos activos en el tiempo]({charts[1].relative_to(output_md_path.parent).as_posix()})", ""]
    lines += [
        "## Características cualitativas de cada alternativa",
        "",
        feature_table,
        "",
        "> Los costos son estimaciones de referencia (septiembre 2026); verificar precios vigentes "
        "de cada proveedor antes de tomar decisiones de producción.",
    ]

    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.write_text("\n".join(lines), encoding="utf-8")
    return output_md_path
