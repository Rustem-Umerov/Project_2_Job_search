from unittest.mock import MagicMock, patch

import pytest
from requests import HTTPError, RequestException, Timeout

from job_search.api.head_hunter_api import HeadHunterAPI
from job_search.api.types import VacancyResult


class TestBuildURL:
    """
    Тесты для метода _build_url.
    """

    def test_build_url_basic(self) -> None:
        api = HeadHunterAPI(base_url="https://api.hh.ru")
        assert api._build_url("vacancies") == "https://api.hh.ru/vacancies"

    def test_build_url_with_slashes(self) -> None:
        api = HeadHunterAPI(base_url="https://api.hh.ru/")
        assert api._build_url("/vacancies") == "https://api.hh.ru/vacancies"


class TestConnect:
    """
    Тесты для метода _connect.
    """

    def test_connect_invalid_endpoint(self) -> None:
        api = HeadHunterAPI()
        with pytest.raises(ValueError):
            api._connect(endpoint=123, params={})

    def test_connect_invalid_params(self) -> None:
        api = HeadHunterAPI()
        with pytest.raises(ValueError):
            api._connect(endpoint="vacancies", params="not a dict")

    @patch.object(HeadHunterAPI, "_init_session")
    def test_connect_success(self, mock_session_init: MagicMock) -> None:
        # Mock session.get
        mock_session = MagicMock()
        mock_response = MagicMock()

        mock_response.json.return_value = {"items": [], "found": 0, "pages": 1}
        mock_response.raise_for_status.return_value = None

        mock_session.get.return_value = mock_response
        mock_session_init.return_value = mock_session

        api = HeadHunterAPI()
        result = api._connect(endpoint="vacancies", params={"text": "python"})

        assert result == {"items": [], "found": 0, "pages": 1}
        mock_session.get.assert_called_once()

    @patch.object(HeadHunterAPI, "_init_session")
    def test_connect_timeout(self, mock_session_init: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session.get.side_effect = Timeout("timeout")
        mock_session_init.return_value = mock_session

        api = HeadHunterAPI()

        with pytest.raises(RequestException):
            api._connect(endpoint="vacancies", params={})

    @patch.object(HeadHunterAPI, "_init_session")
    def test_connect_http_error(self, mock_session_init: MagicMock) -> None:
        mock_session = MagicMock()
        mock_response = MagicMock()

        mock_response.raise_for_status.side_effect = HTTPError("bad status")
        mock_response.status_code = 500

        mock_session.get.return_value = mock_response
        mock_session_init.return_value = mock_session

        api = HeadHunterAPI()

        with pytest.raises(RequestException):
            api._connect(endpoint="vacancies", params={})

    @patch.object(HeadHunterAPI, "_init_session")
    def test_connect_invalid_json(self, mock_session_init: MagicMock) -> None:
        mock_session = MagicMock()
        mock_response = MagicMock()

        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = ValueError("invalid json")

        mock_session.get.return_value = mock_response
        mock_session_init.return_value = mock_session

        api = HeadHunterAPI()

        with pytest.raises(RuntimeError):
            api._connect(endpoint="vacancies", params={})

    @patch.object(HeadHunterAPI, "_init_session")
    def test_connect_json_not_dict(self, mock_session_init: MagicMock) -> None:
        mock_session = MagicMock()
        mock_response = MagicMock()

        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = ["not", "a", "dict"]

        mock_session.get.return_value = mock_response
        mock_session_init.return_value = mock_session

        api = HeadHunterAPI()

        with pytest.raises(RuntimeError):
            api._connect(endpoint="vacancies", params={})

    @patch.object(HeadHunterAPI, "_init_session")
    def test_connect_json_contains_errors(self, mock_session_init: MagicMock) -> None:
        mock_session = MagicMock()
        mock_response = MagicMock()

        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"errors": ["bad request"]}

        mock_session.get.return_value = mock_response
        mock_session_init.return_value = mock_session

        api = HeadHunterAPI()

        with pytest.raises(RuntimeError):
            api._connect(endpoint="vacancies", params={})


class TestGetVacancies:
    """
    Тесты для метода get_vacancies.
    """

    def test_get_vacancies_empty_keyword(self) -> None:
        api = HeadHunterAPI()
        with pytest.raises(ValueError):
            api.get_vacancies("")

    @patch.object(HeadHunterAPI, "_connect")
    def test_get_vacancies_success(self, mock_connect: MagicMock) -> None:
        mock_connect.return_value = {"items": [{"id": 1}], "found": 1, "pages": 1}

        api = HeadHunterAPI()
        result = api.get_vacancies("python")

        assert isinstance(result, VacancyResult)
        assert result.total_count == 1
        assert result.total_pages == 1
        assert result.vacancies == [{"id": 1}]

    @patch.object(HeadHunterAPI, "_connect")
    def test_get_vacancies_items_not_list(self, mock_connect: MagicMock) -> None:
        mock_connect.return_value = {"items": "not a list"}

        api = HeadHunterAPI()

        with pytest.raises(RuntimeError):
            api.get_vacancies("python")

    @patch.object(HeadHunterAPI, "_connect")
    def test_get_vacancies_normalizes_per_page(self, mock_connect: MagicMock) -> None:
        mock_connect.return_value = {"items": [], "found": 0, "pages": 1}

        api = HeadHunterAPI()

        result = api.get_vacancies("python", per_page=999)
        assert result.page_size == 100

        result = api.get_vacancies("python", per_page=-5)
        assert result.page_size == 1


class TestGetAllVacancies:
    """
    Тесты для метода get_all_vacancies.
    """

    @patch.object(HeadHunterAPI, "get_vacancies")
    def test_get_all_vacancies_single_page(self, mock_get: MagicMock) -> None:
        mock_get.return_value = VacancyResult(
            vacancies=[{"id": 1}], total_count=1, total_pages=1, page_size=100, current_page=0, metadata=None
        )

        api = HeadHunterAPI()
        result = api.get_all_vacancies("python")

        assert result.total_count == 1
        assert result.vacancies == [{"id": 1}]
        assert mock_get.call_count == 1

    @patch.object(HeadHunterAPI, "get_vacancies")
    def test_get_all_vacancies_multiple_pages(self, mock_get: MagicMock) -> None:
        # page 0
        mock_get.side_effect = [
            VacancyResult(
                vacancies=[{"id": 1}], total_count=2, total_pages=2, page_size=100, current_page=0, metadata=None
            ),
            # page 1
            VacancyResult(
                vacancies=[{"id": 2}], total_count=2, total_pages=2, page_size=100, current_page=1, metadata=None
            ),
        ]

        api = HeadHunterAPI()
        result = api.get_all_vacancies("python")

        assert result.total_count == 2
        assert result.vacancies == [{"id": 1}, {"id": 2}]
        assert mock_get.call_count == 2
