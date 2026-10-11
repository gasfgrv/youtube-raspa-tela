from typing import Final

from src.file_writer import export_csv
from src.web_driver import create_driver, wait_for_playlist, collect_all_videos

WATCH_LATER_URL: Final[str] = "https://www.youtube.com/playlist?list=WL"


def main() -> None:
    """Abre o Brave, coleta a playlist e exporta os vídeos para CSV.

    O navegador é encerrado ao final, inclusive quando ocorre uma exceção
    durante a navegação ou a exportação.
    """
    driver = create_driver()

    try:
        driver.get(WATCH_LATER_URL)
        print("Se necessário, faça login no YouTube na janela aberta.")
        wait_for_playlist(driver)

        videos = collect_all_videos(driver)
        export_csv(videos)

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
