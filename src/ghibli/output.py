import json

from rich import print as rich_print
from rich.console import Console
from rich.markdown import Markdown


def render_text(text: str, json_output: bool) -> None:
    if not text:
        rich_print("(no response)")
        return
    if json_output:
        print(json.dumps({"response": text}, indent=2, ensure_ascii=False))
    else:
        Console().print(Markdown(text))
