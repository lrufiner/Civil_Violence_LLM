"""CLI para correr la simulación con distintos motores de decisión y comparar desempeño.

Ejemplo:
    python -m experiments.run_comparison --engines rule ollama jev --steps 30 --seeds 1 2 3
"""

from __future__ import annotations

import argparse
import logging
import random
from pathlib import Path

from config import configure_logging
from decision.factory import build_engine
from experiments.configs import PRESETS
from metrics.report import generate_comparison_report
from model import EpsteinCivilViolenceLLM

logger = logging.getLogger(__name__)


def _preset_by_key(key: str):
    for preset in PRESETS:
        if preset.key == key:
            return preset
    raise ValueError(f"Preset desconocido: '{key}'. Opciones: {[p.key for p in PRESETS]}")


def run_single(
    preset,
    seed: int,
    steps: int,
    width: int,
    height: int,
    citizen_density: float,
    cop_density: float,
    results_dir: Path,
) -> None:
    engine = build_engine(preset.kind, cache=True, rng=random.Random(seed), **preset.kwargs)
    model = EpsteinCivilViolenceLLM(
        width=width,
        height=height,
        citizen_density=citizen_density,
        cop_density=cop_density,
        seed=seed,
        decision_engine=engine,
    )

    for _ in range(steps):
        if not model.running:
            break
        model.step()

    results_dir.mkdir(parents=True, exist_ok=True)
    model.performance_recorder.to_csv(results_dir / f"{preset.key}_seed{seed}_decisions.csv")
    model.datacollector.get_model_vars_dataframe().to_csv(
        results_dir / f"{preset.key}_seed{seed}_timeseries.csv", index=False
    )
    logger.info(
        "Run completado: engine=%s seed=%s decisiones=%s", preset.key, seed, len(model.performance_recorder)
    )


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--engines", nargs="+", default=[p.key for p in PRESETS],
        help="Presets a comparar (ver experiments/configs.py)",
    )
    parser.add_argument("--steps", type=int, default=30, help="Pasos de simulación por corrida")
    parser.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3], help="Semillas aleatorias")
    parser.add_argument("--width", type=int, default=12, help="Ancho de grilla (chico para no disparar costos)")
    parser.add_argument("--height", type=int, default=12)
    parser.add_argument("--citizen-density", type=float, default=0.5)
    parser.add_argument("--cop-density", type=float, default=0.07)
    parser.add_argument("--results-dir", default="results/raw")
    parser.add_argument("--report-path", default="results/comparison_report.md")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    for engine_key in args.engines:
        preset = _preset_by_key(engine_key)
        for seed in args.seeds:
            logger.info("Corriendo preset=%s seed=%s", preset.key, seed)
            run_single(
                preset, seed, args.steps, args.width, args.height,
                args.citizen_density, args.cop_density, results_dir,
            )

    report_path = generate_comparison_report(results_dir, Path(args.report_path))
    logger.info("Reporte generado en %s", report_path)


if __name__ == "__main__":
    main()
