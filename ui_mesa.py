"""Ajustes a la interfaz genérica de Mesa (`SolaraViz`): idioma de sus textos y layout de paneles.

Mesa 3.5 no expone ni la traducción de sus controles ni la grilla de paneles, así que acá
se reemplazan dos nombres del módulo `mesa.visualization.solara_viz`:

- `solara`: un proxy que traduce los textos fijos (títulos, labels, botones) antes de
  pasarlos a Solara. Si una versión futura de Mesa cambia un texto, simplemente queda en inglés.
- `make_initial_grid_layout`: devuelve un layout propio según la cantidad de paneles de cada
  pestaña, en lugar de la grilla fija de Mesa (6 columnas x 10 filas por panel), que hace
  que los paneles altos se superpongan.

Además registra en `parametros_pendientes` los parámetros iniciales que el usuario cambió
y que todavía no se aplicaron: Mesa solo los usa al tocar "Reset", sin avisarlo.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional, Sequence

import mesa.visualization.solara_viz as solara_viz
import solara

# Labels de los parámetros iniciales cambiados desde el último "Reset" (una por sesión del navegador)
parametros_pendientes = solara.reactive(frozenset())
_etiquetas_parametros: frozenset = frozenset()

# Configuración activa (ver `instalar`)
_textos: Dict[str, str] = {}
_nombres_vistas: Sequence[str] = ()
_formato_paso = "Step: {}"

_PATRON_TIEMPO = re.compile(r"^Time: (\d+)(?:\.0)?$")
_PATRON_VISTA = re.compile(r"^Page (\d+)$")


def traducir(texto: Any) -> Any:
    if not isinstance(texto, str):
        return texto
    if texto in _textos:
        return _textos[texto]
    if match := _PATRON_TIEMPO.match(texto):
        return _formato_paso.format(match.group(1))
    if (match := _PATRON_VISTA.match(texto)) and int(match.group(1)) < len(_nombres_vistas):
        return _nombres_vistas[int(match.group(1))]
    return texto


def _marcar_pendiente(label: str, on_value: Callable) -> Callable:
    def on_value_marcado(value):
        parametros_pendientes.value = parametros_pendientes.value | {label}
        on_value(value)

    return on_value_marcado


def _con_textos_traducidos(func: Callable) -> Callable:
    def envoltura(*args, **kwargs):
        label = args[0] if args else kwargs.get("label")
        if label in _etiquetas_parametros and kwargs.get("on_value") is not None:
            kwargs["on_value"] = _marcar_pendiente(label, kwargs["on_value"])
        args = tuple(traducir(a) for a in args)
        for clave in ("label", "title"):
            if clave in kwargs:
                kwargs[clave] = traducir(kwargs[clave])
        if isinstance(kwargs.get("children"), list):
            kwargs["children"] = [traducir(c) for c in kwargs["children"]]
        return func(*args, **kwargs)

    return envoltura


class _ModuloTraducido:
    """Proxy de un módulo que traduce los textos de ciertas funciones y delega el resto."""

    def __init__(self, modulo: Any, envolver: set, submodulos: Optional[Dict[str, set]] = None):
        self._modulo = modulo
        self._envolver = envolver
        self._submodulos = submodulos or {}

    def __getattr__(self, nombre: str) -> Any:
        atributo = getattr(self._modulo, nombre)
        if nombre in self._envolver:
            return _con_textos_traducidos(atributo)
        if nombre in self._submodulos:
            return _ModuloTraducido(atributo, self._submodulos[nombre])
        return atributo


def instalar(
    textos: Optional[Dict[str, str]] = None,
    nombres_vistas: Sequence[str] = (),
    formato_paso: str = "Step: {}",
    layouts: Optional[Dict[int, List[dict]]] = None,
    parametros_iniciales: Optional[set] = None,
) -> None:
    """Configura los textos y el layout de SolaraViz.

    - `textos`: traducción de los textos fijos de Mesa (vacío = quedan en inglés).
    - `nombres_vistas`: nombres de las pestañas, en lugar de "Page 0", "Page 1"...
    - `formato_paso`: cómo se muestra "Time: N" en la tarjeta de información.
    - `layouts`: layout de la grilla según la cantidad de paneles de la pestaña.
    - `parametros_iniciales`: labels de los controles del panel izquierdo cuyos cambios se
      registran en `parametros_pendientes` hasta el próximo "Reset".
    """
    global _textos, _nombres_vistas, _formato_paso, _etiquetas_parametros
    _textos = dict(textos or {})
    _nombres_vistas = tuple(nombres_vistas)
    _formato_paso = formato_paso
    _etiquetas_parametros = frozenset(parametros_iniciales or ())

    if not isinstance(solara_viz.solara, _ModuloTraducido):
        solara_viz.solara = _ModuloTraducido(
            solara_viz.solara,
            envolver={"Card", "Text", "Button", "Checkbox", "SliderInt", "SliderFloat", "Error", "Select", "InputText"},
            submodulos={"v": {"Tab"}},
        )

    if layouts:
        layout_mesa = getattr(solara_viz.make_initial_grid_layout, "original", solara_viz.make_initial_grid_layout)

        def make_initial_grid_layout(num_components: int) -> List[dict]:
            if num_components in layouts:
                return [dict(item) for item in layouts[num_components]]
            return layout_mesa(num_components)

        make_initial_grid_layout.original = layout_mesa  # type: ignore[attr-defined]
        solara_viz.make_initial_grid_layout = make_initial_grid_layout
