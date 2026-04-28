"""
CLI entry point for nanocode.

Enables running the package as a module:
    python -m nanocode

This redirects to the CLI REPL loop after loading configuration.
"""

from nanocode.cli.main import main as cli_main


def main() -> None:
    """
    Entry point for `python -m nanocode`.

    Loads environment configuration and starts the interactive REPL.
    """
    cli_main()


if __name__ == "__main__":
    main()
