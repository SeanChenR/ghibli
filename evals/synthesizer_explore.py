"""One-shot Synthesizer exploration.

Generates 15 LLM-authored queries via DeepEval's Synthesizer to compare against
our 30 manually curated GitHub queries. Output is dumped to
`evals/synthesized-queries/<ISO-timestamp>.json` for offline review and a
findings document.

Not part of the production validation set — see findings.md for why.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path

from dotenv import load_dotenv

OUTPUT_DIR = Path("evals/synthesized-queries")

SUBJECT = "GitHub natural language query about open-source repos, releases, issues, contributors"
TASK = "answer technical questions by searching GitHub"

EVOLUTIONS_TO_USE = ["REASONING", "COMPARATIVE", "MULTICONTEXT"]
NUM_GOLDENS = 15


def main() -> None:
    load_dotenv()

    from deepeval.models import GeminiModel
    from deepeval.synthesizer import Synthesizer
    from deepeval.synthesizer.config import EvolutionConfig, StylingConfig
    from deepeval.synthesizer.types import Evolution

    judge_model = GeminiModel(model="gemini-2.5-flash")

    # Spread 15 goldens evenly across the three evolution types
    evolutions = {
        Evolution[name]: 1.0 / len(EVOLUTIONS_TO_USE) for name in EVOLUTIONS_TO_USE
    }

    synthesizer = Synthesizer(
        model=judge_model,
        evolution_config=EvolutionConfig(num_evolutions=1, evolutions=evolutions),
        styling_config=StylingConfig(
            scenario=SUBJECT,
            task=TASK,
            input_format="A short, natural-language question a developer might type into a CLI",
            expected_output_format="A concise factual answer grounded in real GitHub data",
        ),
    )

    print(f"Generating {NUM_GOLDENS} goldens with evolutions {EVOLUTIONS_TO_USE} ...")
    goldens = synthesizer.generate_goldens_from_scratch(num_goldens=NUM_GOLDENS)
    print(f"Got {len(goldens)} goldens.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    output_path = OUTPUT_DIR / f"{timestamp}.json"

    payload = {
        "subject": SUBJECT,
        "task": TASK,
        "evolutions_requested": EVOLUTIONS_TO_USE,
        "num_requested": NUM_GOLDENS,
        "goldens": [
            {
                "input": g.input,
                "expected_output": g.expected_output,
                "additional_metadata": g.additional_metadata,
            }
            for g in goldens
        ],
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ Wrote {output_path}")


if __name__ == "__main__":
    main()
