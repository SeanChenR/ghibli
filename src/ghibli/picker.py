"""Interactive model picker, onboarding, `.env` writer, and `.ghibli/last_model` CRUD.

This module is the first-run UX layer for the ghibli CLI. `cli.py` consults
`choose_model()`; when the user picks a provider that lacks credentials, the
picker dispatches to a provider-specific onboarding sub-flow that prompts the
user and writes the relevant entry to `<cwd>/.env`.

State lives under `<cwd>/.ghibli/`:
- `last_model`: plain-text file with the most-recently-picked model identifier
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import typer

from ghibli.exceptions import SessionError


# ---------------------------------------------------------------------------
# .ghibli/ state helpers
# ---------------------------------------------------------------------------


def _ghibli_dir() -> Path:
    """Return <cwd>/.ghibli — the project-local state directory."""
    return Path.cwd() / ".ghibli"


def _last_model_path() -> Path:
    return _ghibli_dir() / "last_model"


def read_last_model() -> str | None:
    """Return the persisted model identifier, or None if unset / empty."""
    path = _last_model_path()
    if not path.exists():
        return None
    content = path.read_text(encoding="utf-8").strip()
    return content or None


def write_last_model(identifier: str) -> None:
    """Persist the selected model identifier to <cwd>/.ghibli/last_model."""
    _ghibli_dir().mkdir(parents=True, exist_ok=True)
    _last_model_path().write_text(f"{identifier}\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Provider catalog (5 options, always displayed)
# ---------------------------------------------------------------------------


def _ollama_identifier() -> str:
    return f"ollama:{os.environ.get('OLLAMA_CLOUD_MODEL', 'qwen3.5:cloud')}"


def _openai_identifier() -> str:
    """OpenAI defaults to gpt-4o-mini; override via OPENAI_MODEL env var.

    See https://developers.openai.com/api/docs/models/all for the full list
    of model slugs that the user's API key can access.
    """
    return f"openai:{os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')}"


@dataclass(frozen=True)
class _Provider:
    display: str
    identifier_fn: Callable[[], str]
    credential_env: str  # env var that must be non-empty to skip onboarding
    onboard: Callable[[], None]


def _onboard_api_key(env_var: str, key_url: str) -> None:
    """Prompt for an API key (hidden input) and append to .env."""
    print(f"Get your key at {key_url}")
    value = typer.prompt(f"Paste your {env_var}", hide_input=True)
    try:
        append_env_var(env_var, value)
    except SessionError as e:
        print(str(e))
        raise SystemExit(0)
    print("Saved to .env.")
    # Populate current process so immediate downstream calls see it
    os.environ[env_var] = value


def _onboard_vertex() -> None:
    """Guide the user through gcloud ADC setup and persist GOOGLE_CLOUD_PROJECT."""
    print("Vertex AI uses Application Default Credentials (ADC).")
    print(
        "Step 1: in another terminal, run: gcloud auth application-default login"
    )
    typer.prompt("Press Enter when done", default="", show_default=False)
    project = typer.prompt("Paste your GOOGLE_CLOUD_PROJECT")
    location = typer.prompt("GOOGLE_CLOUD_LOCATION", default="us-central1")
    try:
        append_env_var("GOOGLE_CLOUD_PROJECT", project)
        if location != "us-central1":
            append_env_var("GOOGLE_CLOUD_LOCATION", location)
    except SessionError as e:
        print(str(e))
        raise SystemExit(0)
    print("Saved to .env.")
    os.environ["GOOGLE_CLOUD_PROJECT"] = project
    if location != "us-central1":
        os.environ["GOOGLE_CLOUD_LOCATION"] = location


_PROVIDERS: list[_Provider] = [
    _Provider(
        display="Gemini 2.5 Flash (API Key)",
        identifier_fn=lambda: "gemini-2.5-flash",
        credential_env="GEMINI_API_KEY",
        onboard=lambda: _onboard_api_key(
            "GEMINI_API_KEY", "https://aistudio.google.com/app/apikey"
        ),
    ),
    _Provider(
        display="Gemini 2.5 Flash (Vertex AI)",
        identifier_fn=lambda: "gemini-2.5-flash",
        credential_env="GOOGLE_CLOUD_PROJECT",
        onboard=_onboard_vertex,
    ),
    _Provider(
        display="Gemma-4-26b (open-weight, via Gemini API)",
        identifier_fn=lambda: "gemma:gemma-4-26b-a4b-it",
        credential_env="GEMINI_API_KEY",
        onboard=lambda: _onboard_api_key(
            "GEMINI_API_KEY", "https://aistudio.google.com/app/apikey"
        ),
    ),
    _Provider(
        display="OpenAI",
        identifier_fn=_openai_identifier,
        credential_env="OPENAI_API_KEY",
        onboard=lambda: _onboard_api_key(
            "OPENAI_API_KEY", "https://platform.openai.com/api-keys"
        ),
    ),
    _Provider(
        display="Ollama Cloud",
        identifier_fn=_ollama_identifier,
        credential_env="OLLAMA_API_KEY",
        onboard=lambda: _onboard_api_key(
            "OLLAMA_API_KEY", "https://ollama.com/settings/keys"
        ),
    ),
]


# ---------------------------------------------------------------------------
# Picker entry point
# ---------------------------------------------------------------------------


def choose_model() -> str | None:
    """Prompt the user to pick one of the 5 supported providers.

    Returns the resolved model identifier (and persists it to
    `<cwd>/.ghibli/last_model`). Returns None only when picking is inappropriate
    (stdin is not a TTY, or `GHIBLI_MODEL` env var is explicitly set — the
    caller should honour those paths instead).

    When the selected provider lacks its credential env var, the picker
    dispatches to a provider-specific onboarding sub-flow that prompts the user
    and persists to `<cwd>/.env` before returning.
    """
    if not sys.stdin.isatty():
        return None
    if os.environ.get("GHIBLI_MODEL"):
        return None

    print("Select a model:")
    for i, p in enumerate(_PROVIDERS, start=1):
        print(f"  {i}) {p.display}")
    choice = typer.prompt("Select", default=1, type=int)
    idx = max(1, min(choice, len(_PROVIDERS))) - 1
    provider = _PROVIDERS[idx]

    if not os.environ.get(provider.credential_env):
        provider.onboard()

    # For OpenAI / Ollama, prompt for the concrete model slug — default from
    # the corresponding env var so users who set OPENAI_MODEL / OLLAMA_CLOUD_MODEL
    # in .env get that as the pre-filled answer. Press Enter to accept.
    if provider.display == "OpenAI":
        default_slug = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        slug = typer.prompt(
            "Which OpenAI model? (see https://developers.openai.com/api/docs/models/all)",
            default=default_slug,
        )
        identifier = f"openai:{slug}"
    elif provider.display == "Ollama Cloud":
        default_slug = os.environ.get("OLLAMA_CLOUD_MODEL", "qwen3.5:cloud")
        slug = typer.prompt(
            "Which Ollama Cloud model slug? (see https://ollama.com/search?c=cloud)",
            default=default_slug,
        )
        identifier = f"ollama:{slug}"
    else:
        identifier = provider.identifier_fn()

    write_last_model(identifier)
    return identifier


def ensure_credentials(model_id: str) -> None:
    """Check the resolved model has its required credential env var set.

    Behaviour when missing:
      - stdin is a TTY → dispatch to the provider's onboarding sub-flow
        (prompts for key / project id, writes `.env`, updates `os.environ`).
      - stdin is NOT a TTY → raise SessionError so the caller can exit cleanly.

    Called from `cli.main()` after model resolution (covers all sources:
    `--model`, `GHIBLI_MODEL`, `.ghibli/last_model`, and picker — picker
    already onboards inline, making this a no-op for that path).
    """
    if model_id.startswith("openai:"):
        if not os.environ.get("OPENAI_API_KEY"):
            _interactive_or_raise(
                lambda: _onboard_api_key(
                    "OPENAI_API_KEY", "https://platform.openai.com/api-keys"
                ),
                "OPENAI_API_KEY",
            )
        return
    if model_id.startswith("ollama:"):
        if not os.environ.get("OLLAMA_API_KEY"):
            _interactive_or_raise(
                lambda: _onboard_api_key(
                    "OLLAMA_API_KEY", "https://ollama.com/settings/keys"
                ),
                "OLLAMA_API_KEY",
            )
        return
    if model_id.startswith("gemma:"):
        if not os.environ.get("GEMINI_API_KEY"):
            _interactive_or_raise(
                lambda: _onboard_api_key(
                    "GEMINI_API_KEY", "https://aistudio.google.com/app/apikey"
                ),
                "GEMINI_API_KEY",
            )
        return
    # Bare model identifier → Gemini native SDK path; either auth works
    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get(
        "GOOGLE_CLOUD_PROJECT"
    ):
        _interactive_or_raise(_onboard_gemini_native, "GEMINI_API_KEY or GOOGLE_CLOUD_PROJECT")


def _interactive_or_raise(onboard_fn: Callable[[], None], env_desc: str) -> None:
    if sys.stdin.isatty():
        onboard_fn()
    else:
        raise SessionError(
            f"{env_desc} is required but missing — set it in .env / environment, "
            "or pass --model <id> with credentials already configured."
        )


def _onboard_gemini_native() -> None:
    """Bare Gemini identifier has two auth paths — ask which, then onboard."""
    print("Gemini needs one of:")
    print("  1) GEMINI_API_KEY (API Key mode)")
    print("  2) GOOGLE_CLOUD_PROJECT (Vertex AI, requires gcloud ADC)")
    choice = typer.prompt("Select", default=1, type=int)
    if choice == 2:
        _onboard_vertex()
    else:
        _onboard_api_key(
            "GEMINI_API_KEY", "https://aistudio.google.com/app/apikey"
        )


def run_onboarding() -> str:
    """Backwards-compatible wrapper: delegates to `choose_model`.

    Kept so external callers / v1 tests that used `run_onboarding()` as the
    zero-provider entry point still function. The new design merges the
    picking + onboarding paths into `choose_model()`.
    """
    result = choose_model()
    if result is None:
        # In the v1 test scenarios run_onboarding was never called outside TTY,
        # so this is a safety net rather than expected behaviour.
        raise SessionError("run_onboarding requires a TTY and no GHIBLI_MODEL override")
    return result


# ---------------------------------------------------------------------------
# .env writer
# ---------------------------------------------------------------------------


def append_env_var(
    key: str,
    value: str,
    env_path: Path | None = None,
) -> None:
    """Write KEY=value to a dotenv-format file.

    - File absent → create with single line `KEY=value\\n`.
    - File present, no `^KEY=` line → append `KEY=value\\n` (ensuring leading \\n
      if the existing file does not end with one).
    - File present and `^KEY=` already exists → raise SessionError, do NOT modify.

    UTF-8, explicit `\\n` line terminator.
    """
    if env_path is None:
        env_path = Path(".env")

    if not env_path.exists():
        env_path.write_text(f"{key}={value}\n", encoding="utf-8")
        return

    existing = env_path.read_text(encoding="utf-8")
    for line in existing.splitlines():
        if line.startswith(f"{key}="):
            raise SessionError(
                f"Key {key!r} already exists in .env — please edit it manually "
                "to change it."
            )

    separator = "" if existing.endswith("\n") else "\n"
    with env_path.open("a", encoding="utf-8") as f:
        f.write(f"{separator}{key}={value}\n")
