"""`triage` command-line entry point: `uv run python -m triage.cli run <chat.txt> [--json]`."""

from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.callback()
def main() -> None:
    """Aminobots request triage (all actions simulated)."""


@app.command()
def version() -> None:
    """Print package, policy and prompt versions."""
    from triage.config import load_models
    from triage.policy import load_policy

    typer.echo(f"aminobots-triage {pkg_version('aminobots-triage')}")
    typer.echo(f"policy: v{load_policy().version}")
    typer.echo(f"prompt: extract/v{load_models().roles.extractor.prompt_version}")


@app.command()
def run(
    chat: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    json_out: Annotated[bool, typer.Option("--json", help="Print the full RunResult.")] = False,
) -> None:
    """Triage one WhatsApp .txt export. Simulated: only appends to runs/*.jsonl."""
    from triage import pipeline, route

    result = pipeline.run(chat, runs_dir=route.RUNS)
    if json_out:
        typer.echo(result.model_dump_json(indent=2))
        return
    typer.echo(f"run {result.run_id} · {result.chat} · {result.status} · now {result.now}")
    if result.status == "UNPROCESSED":
        typer.echo(f"UNPROCESSED — whole chat handed to the team: {result.error}")
        raise typer.Exit(1)
    rows = [("Gloss", "Sender (state)", "Grade", "Rule", "Evidence")]
    for r in result.requests:
        sender = f"{r.requester_name or route.mask(r.requester_phone)} ({r.identity.state})"
        rows.append(
            (
                r.candidate.gloss[:60],
                sender,
                r.grade,
                r.rule_id,
                " ".join(r.candidate.evidence_msg_ids),
            )
        )
    widths = [max(len(row[i]) for row in rows) for i in range(5)]
    for row in rows:
        typer.echo("  ".join(cell.ljust(w) for cell, w in zip(row, widths, strict=True)))
    typer.echo(
        f"{len(result.requests)} requests · {len(result.internal_requests)} internal (logged) · "
        f"{len(result.rejected)} rejected · simulated only, nothing executed"
    )


if __name__ == "__main__":
    app()
