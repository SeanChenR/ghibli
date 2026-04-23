import os
import sys
from pathlib import Path
from typing import Annotated, Optional

import click
import typer
from dotenv import load_dotenv
from rich.console import Console

from ghibli import __version__, agent, picker, sessions
from ghibli.exceptions import GhibliError
from ghibli.output import render_text

# Only load the project's own .env — never walk up to home or an ancestor
# directory, which would silently leak unrelated credentials into the picker
# (e.g., a `GOOGLE_CLOUD_PROJECT` in `~/.env`).
load_dotenv(dotenv_path=Path.cwd() / ".env", override=True)
app = typer.Typer(invoke_without_command=True, add_completion=False)


def _should_prompt_interactively() -> bool:
    """True when the CLI can prompt the user (TTY + no explicit GHIBLI_MODEL override).

    Extracted so tests can patch without fighting CliRunner's stdin replacement.
    """
    return sys.stdin.isatty() and not os.environ.get("GHIBLI_MODEL")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"ghibli {__version__}")
        raise typer.Exit()


def _format_tool_args(args: dict, max_len: int = 60) -> str:
    """Render tool args for visualization — truncate long values for readability."""
    parts = []
    for k, v in args.items():
        text = repr(v) if isinstance(v, str) else str(v)
        if len(text) > max_len:
            text = text[: max_len - 3] + "..."
        parts.append(f"{k}={text}")
    return ", ".join(parts)


@app.callback()
def main(
    session: Annotated[
        Optional[str],
        typer.Option("--session", help="Resume a session by ID"),
    ] = None,
    list_sessions: Annotated[
        bool,
        typer.Option("--list-sessions", help="List all past sessions and exit"),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output raw JSON instead of Rich formatting"),
    ] = False,
    model: Annotated[
        Optional[str],
        typer.Option(
            "--model",
            help=(
                "Model to use. Examples: gemini-2.5-flash, openai:gpt-4o-mini, "
                "gemini:gemma-4-26b-a4b-it, ollama:qwen3.5:cloud. "
                "Overrides GHIBLI_MODEL env var and .ghibli/last_model."
            ),
        ),
    ] = None,
    model_picker: Annotated[
        bool,
        typer.Option(
            "--model-picker",
            help="Force the model picker (ignores --model / GHIBLI_MODEL / last_model)",
        ),
    ] = False,
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Print version and exit",
        ),
    ] = None,
) -> None:
    if list_sessions:
        all_sessions = sessions.list_all_sessions()
        if not all_sessions:
            typer.echo("No sessions found.")
        else:
            for s in all_sessions:
                title = s.get("title") or ""
                typer.echo(f"{s['id']}  {s['created_at']}  {title}")
        raise typer.Exit()

    # Validate --session BEFORE model resolution — if the session id is bogus,
    # bail out immediately rather than forcing the user through picker first.
    session_id: str
    if session is not None:
        existing = sessions.get_session(session)
        if existing is None:
            typer.echo(f"Error: session '{session}' not found", err=True)
            raise typer.Exit(code=1)
        session_id = session
        typer.echo(f"Resuming session {session_id}...")
    else:
        session_id = sessions.create_session()

    # Resolve the model. `--model-picker` forces interactive selection even
    # when other sources are set; otherwise the explicit priority is:
    #   1. --model <id>           (already bound to `model`)
    #   2. GHIBLI_MODEL env var
    #   3. <cwd>/.ghibli/last_model
    #   4. picker.choose_model()  (interactive; writes back to last_model)
    # When everything falls through (e.g. non-TTY + no flag/env/last_model),
    # exit with code 1 — do NOT silently fall back to a hard-coded model.
    if model_picker:
        model = picker.choose_model()
    else:
        if model is None:
            model = os.environ.get("GHIBLI_MODEL")
        if model is None:
            model = picker.read_last_model()
        if model is None:
            # choose_model() handles prompt + onboarding + write_last_model.
            model = picker.choose_model()
    if model is None:
        typer.echo(
            "No model specified. Pass --model <id>, set GHIBLI_MODEL, "
            "or run `ghibli --model-picker` in a TTY to pick interactively.",
            err=True,
        )
        raise typer.Exit(code=1)

    # Credential check: ensure the resolved model's required env var is present.
    # Missing + TTY → onboard in place. Missing + non-TTY → exit 1 with clear message.
    try:
        picker.ensure_credentials(model)
    except GhibliError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

    console = Console()
    displayed_model = model or os.environ.get("GHIBLI_MODEL", "gemini-2.5-flash")

    # Welcome banner — shown once, before the first prompt
    typer.echo("─" * 64)
    typer.echo(f"  ghibli {__version__}  ·  model: {displayed_model}")
    typer.echo(f"  session: {session_id}")
    typer.echo("  Press Ctrl+D or enter a blank line to exit.")
    typer.echo("─" * 64)

    def _on_tool_call(name: str, args: dict) -> None:
        typer.echo(f"  → {name}({_format_tool_args(args)})")

    while True:
        try:
            user_input = typer.prompt(
                "You", prompt_suffix="> ", default="", show_default=False
            )
        except (KeyboardInterrupt, EOFError, click.exceptions.Abort):
            typer.echo("")
            break

        if not user_input.strip():
            break

        try:
            with console.status("Thinking...", spinner="dots"):
                response = agent.chat(
                    user_input,
                    session_id,
                    json_output,
                    model=model,
                    on_tool_call=_on_tool_call,
                )
            render_text(response, json_output)
        except GhibliError as e:
            typer.echo(f"Error: {e}")
            continue

    # Exit hint: only when the session has actual content; empty session is cleaned up
    turns = sessions.count_turns(session_id)
    if turns > 0:
        typer.echo(f"Session saved: {session_id} ({turns} turns)")
        typer.echo(f"Resume with: ghibli --session {session_id}")
    else:
        sessions.delete_session(session_id)
        typer.echo("Bye!")
