from job_search.filters.hh_formatter import HHFilterFormatter


class TestBuildFrom:
    """
    Тесты для метода build_from.
    """

    def test_build_from_all_empty_returns_none(self) -> None:
        fmt = HHFilterFormatter()
        result = fmt.build_from({})
        assert result is None

    def test_build_from_combines_blocks(self) -> None:
        fmt = HHFilterFormatter()
        answers = {"salary_from": 100, "contains_name": "python", "url": "http://example.com"}

        result = fmt.build_from(answers)
        assert result is not None

        assert "salary_from" in result
        assert "name_vacancy" in result
        assert "url_vacancy" in result

    def test_build_from_ignores_exceptions_in_blocks(self) -> None:
        fmt = HHFilterFormatter()

        class Bad:
            def __str__(self) -> str:
                raise ValueError("boom")

        answers = {"contains_name": Bad()}

        result = fmt.build_from(answers)
        assert result is None


class TestFormatSalaryBlock:
    """
    Тесты для метода _format_salary_block.
    """

    def test_salary_block_empty(self) -> None:
        assert HHFilterFormatter._format_salary_block({}) is None

    def test_salary_from_and_to(self) -> None:
        result = HHFilterFormatter._format_salary_block({"salary_from": 101.2, "salary_to": 199.8})
        assert result is not None

        assert result["salary_from"] == {"gte": 101}
        assert result["salary_to"] == {"lte": 200}

    def test_salary_currency(self) -> None:
        result = HHFilterFormatter._format_salary_block({"currency": " rur "})
        assert result is not None

        assert result["currency"] == {"eq": "RUR"}

    def test_salary_from_greater_than_to(self) -> None:
        result = HHFilterFormatter._format_salary_block({"salary_from": 200, "salary_to": 100})
        assert result is not None

        assert "salary_from" in result
        assert "salary_to" in result

    def test_salary_invalid_types(self) -> None:
        result = HHFilterFormatter._format_salary_block({"salary_from": "abc", "salary_to": None, "currency": 123})

        assert result is None


class TestFormatKeywords:
    """
    Тесты для метода _format_keywords.
    """

    def test_keywords_empty(self) -> None:
        assert HHFilterFormatter._format_keywords({}) is None

    def test_keywords_name_string(self) -> None:
        result = HHFilterFormatter._format_keywords({"contains_name": " Python Developer "})
        assert result is not None

        assert result["name_vacancy"] == {"contains": "python developer"}

    def test_keywords_name_list(self) -> None:
        result = HHFilterFormatter._format_keywords({"contains_name": [" Python ", " Dev ", "   "]})
        assert result is not None

        assert result["name_vacancy"] == {"in": ["python", "dev"]}

    def test_keywords_description(self) -> None:
        result = HHFilterFormatter._format_keywords({"contains_description": "  backend developer "})
        assert result is not None

        assert result["description"] == {"contains": "backend developer"}

    def test_keywords_invalid_name_type(self) -> None:
        result = HHFilterFormatter._format_keywords({"contains_name": 123})

        assert result is None


class TestFormatLinks:
    """
    Тесты для метода _format_links.
    """

    def test_links_empty(self) -> None:
        assert HHFilterFormatter._format_links({}) is None

    def test_links_single_url(self) -> None:
        result = HHFilterFormatter._format_links({"url": "HTTP://Example.com/test "})
        assert result is not None

        assert result["url_vacancy"] == {"eq": "http://example.com/test"}

    def test_links_url_list(self) -> None:
        result = HHFilterFormatter._format_links({"url": [" http://a.com ", "invalid", " https://b.com "]})
        assert result is not None

        assert result["url_vacancy"] == {"in": ["http://a.com", "https://b.com"]}

    def test_links_alternate_url(self) -> None:
        result = HHFilterFormatter._format_links({"alternate_url": " https://alt.com "})
        assert result is not None

        assert result["alternate_url"] == {"eq": "https://alt.com"}

    def test_links_invalid_url_type(self) -> None:
        result = HHFilterFormatter._format_links({"url": 123})
        assert result is not None

        assert result is None
