from ghibli.output import render_text


# --- 1.1: render_text accepts non-empty text; empty string prints placeholder ---

def test_render_text_accepts_nonempty_text():
    render_text("hello", json_output=False)


def test_render_text_empty_string_prints_placeholder(capsys):
    render_text("", json_output=False)
    captured = capsys.readouterr()
    assert "(no response)" in captured.out


# --- 1.2: Markdown output renders text ---

def test_markdown_output_renders_text(capsys):
    render_text("**bold**", json_output=False)
    captured = capsys.readouterr()
    assert captured.out != ""


# --- 1.3: JSON output wraps in response key ---

def test_json_output_wraps_in_response_key(capsys):
    render_text("找到 3 個倉庫", json_output=True)
    captured = capsys.readouterr()
    assert "response" in captured.out
    assert "找到 3 個倉庫" in captured.out
