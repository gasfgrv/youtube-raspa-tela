import csv
from dataclasses import asdict
from logging import Logger, getLogger
from pathlib import Path
from typing import Final

from src.video import Video

OUTPUT_FILE: Final[Path] = Path("output/watch_later.csv")

logger: Logger = getLogger(__name__)


def export_csv(videos: list[Video]) -> None:
    """Exporta os vídeos para o arquivo CSV configurado.

    O arquivo usa BOM UTF-8 para facilitar a abertura no Excel e contém as colunas 'title', 'url', 'duration' e 'channel'.

    Args:
        videos: Lista de vídeos a gravar. Uma lista vazia gera somente o cabeçalho.

    Raises:
        OSError: Se o diretório ou o arquivo não puder ser criado, ou gravado.
    """
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open(mode="w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file,
                                fieldnames=["title", "url", "duration", "channel"])

        writer.writeheader()

        for video in videos:
            writer.writerow(asdict(video))

    logger.info(f"CSV salvo em: {OUTPUT_FILE.resolve()}")
    logger.info(f"Total de vídeos: {len(videos)}")
