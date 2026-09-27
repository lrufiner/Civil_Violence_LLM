"""El modo "regla" debe reproducir exactamente el Modelo 1 de Epstein de la referencia de Mesa."""

import pytest
from mesa.examples.advanced.epstein_civil_violence.model import EpsteinCivilViolence, EpsteinScenario

from model import EpsteinCivilViolenceLLM


def _snapshot(model):
    """Tipo, posición y estado de cada agente (los nombres de clase difieren entre implementaciones)."""
    return sorted(
        ("cop" if type(agent).__name__ == "Cop" else "citizen", agent.cell.coordinate,
         getattr(agent, "state", None) and agent.state.name)
        for agent in model.agents
    )


@pytest.mark.parametrize("seed, legitimacy", [(7, 0.6), (3, 0.5), (1, 0.8)])
def test_rule_mode_matches_mesa_reference_step_by_step(seed, legitimacy):
    # Misma visión para ciudadanos y policías: la referencia usa cop_vision para ambos
    reference = EpsteinCivilViolence(width=20, height=20, scenario=EpsteinScenario(rng=seed, legitimacy=legitimacy))
    ours = EpsteinCivilViolenceLLM(
        width=20, height=20, seed=seed, legitimacy=legitimacy, citizen_density=0.7, cop_density=0.074,
        citizen_vision=7, cop_vision=7, max_jail_term=1000, active_threshold=0.1, arrest_prob_constant=2.3,
        decision_kind="rule",
    )

    for step in range(40):
        assert _snapshot(ours) == _snapshot(reference), f"divergencia en el paso {step}"
        reference.step()
        ours.step()
