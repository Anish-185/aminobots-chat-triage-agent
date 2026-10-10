"""`triage` command-line entry point."""

from importlib.metadata import version as pkg_version

import typer

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.callback()
def main() -> None:
    """Aminobots request triage (all actions simulated)."""


@app.command()
def version() -> None:
    """Print package, policy and prompt versions."""
    typer.echo(f"aminobots-triage {pkg_version('aminobots-triage')}")
    typer.echo("policy: not loaded (policy engine arrives in a later phase)")
    typer.echo("prompts: not loaded (prompt pack arrives in a later phase)")
