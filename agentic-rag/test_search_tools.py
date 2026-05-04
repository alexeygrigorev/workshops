from search_tools import SearchTools


class FakeIndex:
    def search(self, query, num_results):
        return [
            {
                "title": "Dashboards",
                "description": "Dashboard docs",
                "content": "Create a dashboard with a report and panels.",
                "filename": "docs/dashboard.md",
            }
        ][:num_results]


class FakeHighlighter:
    def highlight(self, query, search_results):
        highlighted = []
        for result in search_results:
            item = dict(result)
            item["content"] = ["Create a dashboard with a report and panels."]
            highlighted.append(item)
        return highlighted


def test_search_returns_highlighted_snippets():
    tools = SearchTools(
        index=FakeIndex(),
        highlighter=FakeHighlighter(),
        file_index={"docs/dashboard.md": "full dashboard document"},
    )

    results = tools.search("create dashboard")

    assert results[0]["filename"] == "docs/dashboard.md"
    assert results[0]["content"] == ["Create a dashboard with a report and panels."]


def test_get_file_returns_full_document():
    tools = SearchTools(
        index=FakeIndex(),
        highlighter=FakeHighlighter(),
        file_index={"docs/dashboard.md": "full dashboard document"},
    )

    assert tools.get_file("docs/dashboard.md") == "full dashboard document"


def test_get_file_returns_clear_message_for_missing_file():
    tools = SearchTools(index=FakeIndex(), highlighter=FakeHighlighter(), file_index={})

    assert tools.get_file("missing.md") == "file missing.md does not exist"
