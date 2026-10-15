from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from selenium.common import TimeoutException

import main
from src import file_writer, web_driver
from src.video import Video


@pytest.mark.parametrize(
    ("raw_text", "expected"),
    [
        (" 1:23 ", "00:01:23"),
        ("2:04:09", "02:04:09"),
        ("3 minutos", "3 minutos"),
        ("sem duração", ""),
    ],
)
def test_duration_from_text_returns_supported_formats(raw_text, expected):
    # Arrange
    value = raw_text

    # Act
    result = web_driver.duration_from_text(value)

    # Assert
    assert result == expected


@pytest.mark.parametrize(
    "data",
    [
        {"title": "", "url": "https://example.com/video"},
        {"title": "Título", "url": ""},
        {"title": "", "url": ""},
    ],
)
def test_video_from_data_discards_incomplete_data(data):
    # Arrange

    # Act
    result = web_driver.video_from_data(data)

    # Assert
    assert result is None


def test_video_from_data_strips_all_fields():
    # Arrange
    data = {
        "title": " Título ",
        "url": " /video ",
        "duration": " 1:23 ",
        "channel": " Canal ",
    }

    # Act
    result = web_driver.video_from_data(data)

    # Assert
    assert result == Video(
        "Título", "https://www.youtube.com/video", "00:01:23", "Canal")


def test_append_unique_preserves_the_first_video_for_duplicate_urls():
    # Arrange
    first = Video("Primeiro", "https://www.youtube.com/video", "1:00", "Canal")
    second = Video("Segundo", "https://www.youtube.com/video", "2:00", "Canal")
    videos_by_url = {}

    # Act
    web_driver.append_unique(videos_by_url, [first, second])

    # Assert
    assert videos_by_url == {first.url: first}


def test_extract_videos_executes_one_script_for_the_whole_batch():
    # Arrange
    driver = Mock()
    driver.execute_script.return_value = [
        {
            "title": "Título",
            "url": "/video",
            "duration": "1:23",
            "channel": "Canal",
        }
    ]
    items = [Mock(), Mock()]

    # Act
    result = web_driver.extract_videos(driver, items)

    # Assert
    assert result == [
        Video("Título", "https://www.youtube.com/video", "00:01:23", "Canal")]
    driver.execute_script.assert_called_once()


def test_extract_videos_does_not_call_browser_for_an_empty_batch():
    # Arrange
    driver = Mock()

    # Act
    result = web_driver.extract_videos(driver, [])

    # Assert
    assert result == []
    driver.execute_script.assert_not_called()


def test_create_driver_configures_the_requested_profile():
    # Arrange
    fake_driver = Mock()
    with patch("src.web_driver.webdriver.Chrome", return_value=fake_driver) as chrome:
        with patch(
                "src.web_driver.get_browser_user_data_dir",
                return_value=Path("C:/Brave/User Data"),
        ):
            # Act
            result = web_driver.create_driver("Work")

    # Assert
    assert result is fake_driver
    fake_driver.set_window_size.assert_called_once_with(1440, 1000)
    chrome.assert_called_once()
    options = chrome.call_args.kwargs["options"]
    assert "--profile-directory=Work" in options.arguments
    assert f"--user-data-dir={Path('C:/Brave/User Data')}" in options.arguments


def test_wait_for_playlist_reports_timeout_without_raising(caplog):
    # Arrange
    driver = Mock()
    wait = Mock()
    wait.until.side_effect = TimeoutException

    with patch("src.web_driver.WebDriverWait", return_value=wait):
        # Act
        web_driver.wait_for_playlist(driver)

    # Assert
    assert "A playlist não carregou" in caplog.text


def test_collect_all_videos_processes_only_new_batches():
    # Arrange
    driver = Mock()
    first_item = Mock(name="first_item")
    second_item = Mock(name="second_item")
    items_by_iteration = [
        [first_item],
        [first_item, second_item],
    ]
    collected_batches = []

    def append_batch(_driver, videos_by_url, items):
        collected_batches.append(list(items))
        for item in items:
            videos_by_url[item.name] = Video(
                item.name, item.name, "1:00", "Canal")

    with patch("src.web_driver.playlist_items", side_effect=items_by_iteration), \
            patch("src.web_driver.append_videos", side_effect=append_batch), \
            patch("src.web_driver.scroll_last_item"), \
            patch("src.web_driver.wait_for_more_items", side_effect=[None, TimeoutException]), \
            patch("src.web_driver.time.sleep"):
        # Act
        result = web_driver.collect_all_videos(driver)

    # Assert
    assert collected_batches == [[first_item], [second_item]]
    assert len(result) == 2


def test_export_csv_writes_headers_and_video_rows(tmp_path, caplog):
    # Arrange
    caplog.set_level("INFO")
    output_file = tmp_path / "watch_later.csv"
    videos = [Video("Título", "https://example.com/video", "1:23", "Canal")]

    with patch.object(file_writer, "OUTPUT_FILE", output_file):
        # Act
        file_writer.export_csv(videos)

    # Assert
    content = output_file.read_text(encoding="utf-8-sig")
    assert "title,url,duration,channel" in content
    assert "Título,https://example.com/video,1:23,Canal" in content
    assert "Total de vídeos: 1" in caplog.text


def test_main_always_quits_driver_and_exports_collected_videos():
    # Arrange
    driver = Mock()
    videos = [Video("Título", "https://example.com/video", "1:23", "Canal")]

    with patch("main.create_driver", return_value=driver), \
            patch("main.wait_for_playlist") as wait_for_playlist, \
            patch("main.collect_all_videos", return_value=videos), \
            patch("main.export_csv") as export_csv:
        # Act
        main.main()

    # Assert
    driver.get.assert_called_once_with(main.WATCH_LATER_URL)
    wait_for_playlist.assert_called_once_with(driver)
    export_csv.assert_called_once_with(videos)
    driver.quit.assert_called_once()


def test_main_quits_driver_when_collection_fails():
    # Arrange
    driver = Mock()
    error = RuntimeError("falha simulada")

    with patch("main.create_driver", return_value=driver), \
            patch("main.wait_for_playlist"), \
            patch("main.collect_all_videos", side_effect=error), \
            patch("main.export_csv"):
        # Act / Assert
        with pytest.raises(RuntimeError, match="falha simulada"):
            main.main()

    # Assert
    driver.quit.assert_called_once()
