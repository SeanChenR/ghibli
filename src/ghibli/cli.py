from typing import Annotated, Optional

import click
import typer

from ghibli import __version__, agent, sessions
from ghibli.exceptions import GhibliError
from ghibli.output import render_text

app = typer.Typer(invoke_without_command=True)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"ghibli {__version__}")
        raise typer.Exit()


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

    while True:
        try:
            user_input = typer.prompt(
                "You", prompt_suffix="> ", default="", show_default=False
            )
        except (KeyboardInterrupt, EOFError, click.exceptions.Abort):
            typer.echo("\nBye!")
            break

        if not user_input.strip():
            typer.echo("Bye!")
            break

        try:
            response = agent.chat(user_input, session_id, json_output)
            render_text(response, json_output)
        except GhibliError as e:
            typer.echo(f"Error: {e}")
            continue
