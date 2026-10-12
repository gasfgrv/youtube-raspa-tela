import re
import sys
import time
from pathlib import Path
from typing import Final, Iterable, Mapping

from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait

from src.video import Video

WAIT_SECONDS: Final[int] = 60
MAX_IDLE_SCROLLS: Final[int] = 1
PLAYLIST_ITEM_SELECTOR: Final[str] = "ytd-playlist-video-renderer"
DURATION_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?<!\d)(?:\d{1,3}:)?\d{1,2}:\d{2}(?!\d)")
BATCH_EXTRACTION_SCRIPT: Final[str] = """
const durationSelectors = [
    ".ytBadgeShapeText",
    ".thumbnail-overlay-badge-shape badge-shape",
    "badge-shape[aria-label]",
    "#time-status span#text",
    "ytd-thumbnail-overlay-time-status-renderer span",
    "ytd-thumbnail-overlay-time-status-renderer",
    "#overlays badge-shape",
];

function text(value) {
    return (value || "").trim();
}

function findDuration(item) {
    for (const selector of durationSelectors) {
        for (const element of item.querySelectorAll(selector)) {
            for (const attribute of ["textContent", "aria-label", "title"]) {
                const candidate = text(
                    attribute === "textContent"
                        ? element.textContent
                        : element.getAttribute(attribute)
                );

                const match = candidate.match(/(?<!\\d)(?:\\d{1,3}:)?\\d{1,2}:\\d{2}(?!\\d)/);
                if (match) return match[0];
                if (/minuto|segundo/i.test(candidate)) return candidate;
            }
        }
    }
    return "";
}

return arguments[0].map((item) => {
    const titleElement = item.querySelector("a#video-title");
    const title = titleElement
        ? text(titleElement.getAttribute("title") || titleElement.textContent)
        : "";

    return {
        title,
        url: titleElement ? text(titleElement.getAttribute("href")) : "",
        channel: text(item.querySelector("ytd-channel-name a")?.textContent),
        duration: findDuration(item),
    };
});
"""


def get_browser_user_data_dir() -> Path:
    """Retorna o diretório de dados de usuário do Brave por plataforma.

    Returns:
        Caminho usado no argumento '--user-data-dir' do navegador.
    """
    if sys.platform == "win32":
        return Path.home() / "AppData" / "Local" / "BraveSoftware" / "Brave-Browser" / "User Data"

    if sys.platform == "linux":
        return Path.home() / ".config" / "BraveSoftware" / "Brave-Browser"

    return Path.home() / ".config" / "brave"


def create_driver(profile_name: str = "Default") -> WebDriver:
    """Cria uma instância do Brave controlada pelo Selenium.

    Args:
        profile_name: Nome do perfil do Brave a reutilizar.

    Returns:
        Driver do Selenium configurado com janela de 1440x1000 píxeis.

    Raises:
        WebDriverException: Se o navegador ou o driver não puder ser iniciado.
    """
    options = Options()
    options.binary_location = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
    options.add_argument(f"--user-data-dir={get_browser_user_data_dir()}")
    options.add_argument(f"--profile-directory={profile_name}")

    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1440, 1000)
    return driver


def playlist_items(driver: WebDriver) -> list[WebElement]:
    """Localiza os vídeos atualmente renderizados na playlist.

    Args:
        driver: Driver Selenium conectado à página da playlist.

    Returns:
        Lista de elementos 'ytd-playlist-video-renderer' presentes no DOM.
    """
    return driver.find_elements(By.CSS_SELECTOR, PLAYLIST_ITEM_SELECTOR)


def wait_for_playlist(driver: WebDriver) -> None:
    """Aguarda até que o primeiro lote de vídeos apareça no DOM.

    O timeout é tratado localmente: a função informa o problema e retorna
    para que o chamador possa encerrar o driver com segurança.

    Args:
        driver: Driver Selenium conectado à página da playlist.
    """
    try:
        WebDriverWait(driver, WAIT_SECONDS).until(playlist_items)
    except TimeoutException:
        print(
            "A playlist não carregou. Verifique o login e se a página abriu corretamente.")


def duration_from_text(value: str) -> str:
    """Extrai uma duração padronizada ou uma duração escrita por extenso.

    Args:
        value: Texto obtido de um atributo ou elemento HTML.

    Returns:
        Duração no formato 'HH:MM:SS', texto contendo 'minuto' ou
        'segundo', ou string vazia quando nada é encontrado.
    """
    text = value.strip()
    match = DURATION_PATTERN.search(text)

    if match:
        parts = [int(part) for part in match.group(0).split(":")]

        if len(parts) == 2:
            hours, minutes, seconds = 0, *parts
        else:
            hours, minutes, seconds = parts

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    return text if "hora" in text.lower() or "minuto" in text.lower() or "segundo" in text.lower() else ""


def video_from_data(data: Mapping[str, str]) -> Video | None:
    """Converte dados brutos de um item em um objeto 'Video'.

    Título e URL são obrigatórios; itens sem um deles são descartados.

    Args:
        data: Mapeamento com 'title', 'url', 'duration' e 'channel'.

    Returns:
        Um 'Video' normalizado ou 'None' para dados inválidos.
    """
    print(data)

    title = data.get("title", "").strip()
    url = data.get("url", "").strip()

    if not title or not url:
        return None

    return Video(
        title=title,
        url="https://www.youtube.com" + url,
        duration=duration_from_text(data.get("duration", "")),
        channel=data.get("channel", "").strip(),
    )


def extract_videos(driver: WebDriver, items: Iterable[WebElement] | None = None) -> list[Video]:
    """Extrai um lote de vídeos usando uma chamada JavaScript em grupo.

    Args:
        driver: Driver Selenium conectado à playlist.
        items: Elementos a processar. Se 'None', os itens atuais da página
            serão consultados.

    Returns:
        Vídeos válidos encontrados no lote. Itens sem título ou URL são
        ignorados.

    Raises:
        WebDriverException: Se o roteiro de extração não puder ser executado.
    """
    batch = list(items) if items is not None else playlist_items(driver)

    if not batch:
        return []

    raw_videos = driver.execute_script(BATCH_EXTRACTION_SCRIPT, batch)
    videos: list[Video] = []

    for data in raw_videos:
        video = video_from_data(data)

        if video is None:
            continue

        if not video.duration:
            print(f"Duração não encontrada: {video.title} | {video.url}")

        videos.append(video)

    return videos


def append_unique(videos_by_url: dict[str, Video], videos: Iterable[Video]) -> None:
    """Adiciona vídeos ao índice, preservando o primeiro por URL.

    Args:
        videos_by_url: Índice mutável no formato 'URL → Video'.
        videos: Vídeos que serão adicionados ao índice.
    """
    for video in videos:
        videos_by_url.setdefault(video.url, video)


def append_videos(driver: WebDriver,
                  videos_by_url: dict[str, Video],
                  items: Iterable[WebElement] | None = None) -> None:
    """Extrai e indexa um lote sem repetir URLs já coletadas.

    Args:
        driver: Driver Selenium conectado à playlist.
        videos_by_url: Índice mutável usado para deduplicação.
        items: Elementos do lote atual. Se 'None', os itens renderizados serão
            consultados pelo driver.
    """
    append_unique(videos_by_url, extract_videos(driver, items))


def wait_for_more_items(driver: WebDriver, previous_count: int) -> None:
    """Aguarda o carregamento de pelo menos um novo item.

    Args:
        driver: Driver Selenium conectado à playlist.
        previous_count: Quantidade de itens observada antes da rolagem.

    Raises:
        TimeoutException: Se nenhum item novo aparecer no tempo configurado.
    """
    WebDriverWait(driver, WAIT_SECONDS).until(
        lambda browser: len(playlist_items(browser)) > previous_count)


def scroll_last_item(driver: WebDriver, items: list[WebElement]) -> None:
    """Rola a página até o último item atualmente renderizado.

    Args:
        driver: Driver Selenium conectado à playlist.
        items: Lista não vazia de itens renderizados.

    Raises:
        IndexError: Se 'items' estiver vazia.
    """
    driver.execute_script(
        "arguments[0].scrollIntoView({block: 'end'});", items[-1])


def collect_all_videos(driver: WebDriver) -> list[Video]:
    """Percorre a playlist e processa cada lote novo uma única vez.

    A coleta rola até o fim dos itens renderizados, espera o carregamento de
    novos elementos e encerra após atingir 'MAX_IDLE_SCROLLS' tentativas sem
    progresso. Os vídeos são indexados por URL para eliminar duplicatas.

    Args:
        driver: Driver Selenium conectado à playlist "Assistir mais tarde".

    Returns:
        Lista de vídeos únicos na ordem em que foram encontrados.
    """
    videos_by_url: dict[str, Video] = {}
    processed_count = 0
    idle_scrolls = 0

    while idle_scrolls < MAX_IDLE_SCROLLS:
        items = playlist_items(driver)
        new_items = items[processed_count:]
        append_videos(driver, videos_by_url, new_items)
        processed_count = len(items)

        print(
            f"Elementos no DOM: {len(items)} | "
            f"Vídeos únicos coletados: {len(videos_by_url)}"
        )

        if not items:
            break

        scroll_last_item(driver, items)

        try:
            wait_for_more_items(driver, processed_count)
            idle_scrolls = 0
        except TimeoutException:
            idle_scrolls += 1
            print(
                "Nenhum novo elemento carregado. "
                f"Tentativa sem progresso: {idle_scrolls}/{MAX_IDLE_SCROLLS}"
            )
            driver.execute_script("window.scrollBy(0, window.innerHeight);")
            time.sleep(1)

    print(f"Total final: {len(videos_by_url)} vídeos")
    return list(videos_by_url.values())
