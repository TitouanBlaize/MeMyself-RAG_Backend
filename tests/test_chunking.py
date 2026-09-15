from app.chunking import chunk_markdown_qa


def test_splits_multiple_top_level_sections():
    text = "# Question 1\nAnswer 1\n\n# Question 2\nAnswer 2\n"
    assert chunk_markdown_qa(text) == [
        "Question 1\nAnswer 1",
        "Question 2\nAnswer 2",
    ]


def test_nested_headings_stay_in_same_chunk():
    text = "# Question 1\nIntro\n## Detail\nMore info\n### Sub-detail\nEven more\n"
    chunks = chunk_markdown_qa(text)
    assert len(chunks) == 1
    assert "## Detail" in chunks[0]
    assert "### Sub-detail" in chunks[0]


def test_empty_input_returns_no_chunks():
    assert chunk_markdown_qa("") == []
    assert chunk_markdown_qa("   \n  ") == []


def test_crlf_is_normalized():
    text = "# Q1\r\nA1\r\n\r\n# Q2\r\nA2\r\n"
    assert chunk_markdown_qa(text) == ["Q1\nA1", "Q2\nA2"]


def test_heading_with_no_body():
    assert chunk_markdown_qa("# Just a question") == ["Just a question"]
