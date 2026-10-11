from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Video:
    """Representa um vídeo coletado da playlist do YouTube.

    A instância é imutável para evitar alterações acidentais antes da
    deduplicação e da exportação.
    """

    title: str
    url: str
    duration: str
    channel: str
