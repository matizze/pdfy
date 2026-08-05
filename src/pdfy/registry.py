"""Single public component type to renderer association."""

from __future__ import annotations

from types import MappingProxyType

from pdfy.components.callout import RENDERER as CALLOUT
from pdfy.components.cards import RENDERER as CARDS
from pdfy.components.chart import RENDERER as CHART
from pdfy.components.comparison import RENDERER as COMPARISON
from pdfy.components.highlights import RENDERER as HIGHLIGHTS
from pdfy.components.investment import RENDERER as INVESTMENT
from pdfy.components.list import RENDERER as LIST
from pdfy.components.metrics import RENDERER as METRICS
from pdfy.components.signature import RENDERER as SIGNATURE
from pdfy.components.steps import RENDERER as STEPS
from pdfy.components.table import RENDERER as TABLE
from pdfy.components.text import RENDERER as TEXT
from pdfy.components.timeline import RENDERER as TIMELINE


COMPONENT_RENDERERS = MappingProxyType({
    renderer.type_name: renderer
    for renderer in (
        TEXT,
        METRICS,
        HIGHLIGHTS,
        CARDS,
        CALLOUT,
        COMPARISON,
        CHART,
        STEPS,
        TIMELINE,
        TABLE,
        INVESTMENT,
        LIST,
        SIGNATURE,
    )
})


def get_renderer(component_type: str):
    try:
        return COMPONENT_RENDERERS[component_type]
    except KeyError as exc:
        supported = ", ".join(COMPONENT_RENDERERS)
        raise ValueError(
            f"Componente desconhecido: {component_type!r}. Tipos aceitos: {supported}."
        ) from exc


def supported_component_types() -> tuple[str, ...]:
    return tuple(COMPONENT_RENDERERS)
