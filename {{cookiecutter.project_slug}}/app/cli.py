"""Management CLI — run with: uv run python -m app.cli <command>"""

from __future__ import annotations

from pathlib import Path

import typer

cli = typer.Typer(name="cli", add_completion=False, no_args_is_help=True)


@cli.command("new-module")
def new_module(
    name: str = typer.Argument(..., help="Snake-case module name, e.g. 'payments'"),
) -> None:
    """Scaffold a new feature module with all boilerplate files."""
    if not name.isidentifier() or name != name.lower():
        typer.echo(
            f"Error: '{name}' must be a lowercase snake_case identifier.", err=True
        )
        raise typer.Exit(1)

    base = Path("app") / "modules" / name
    if base.exists():
        typer.echo(f"Error: {base} already exists.", err=True)
        raise typer.Exit(1)

    _scaffold(base, name)
    typer.echo(f"✓ Created {base}/")
    typer.echo("  Next steps:")
    typer.echo(f"  1. Add routes to api.py: from app.modules.{name}.routes import")
    typer.echo(f"     {name}_router")
    typer.echo("  2. Import models in alembic/env.py")
    typer.echo(
        f"  3. Import app.modules.{name}.events.handlers in application.py "
        "once it has handlers"
    )
    typer.echo(f"  4. Run: make makemigrations m='add {name}'")
    typer.echo("  5. Run: make migrate")


def _scaffold(base: Path, name: str) -> None:
    prefix = name.replace("_", "-")

    _write(base / "__init__.py", "")

    _write(
        base / "models" / "__init__.py",
        f'"""ORM models for the {name} module."""\n'
        "\n"
        "from __future__ import annotations\n",
    )

    _write(
        base / "repositories" / "__init__.py",
        f'"""Repository adapters for the {name} module."""\n'
        "\n"
        "from __future__ import annotations\n",
    )

    _write(
        base / "usecases" / "__init__.py",
        f'"""Use cases for the {name} module."""\n'
        "\n"
        "from __future__ import annotations\n",
    )

    _write(
        base / "schemas" / "__init__.py",
        f'"""Pydantic schemas for the {name} module."""\n'
        "\n"
        "from __future__ import annotations\n",
    )

    _write(
        base / "routes" / "__init__.py",
        f'"""HTTP routers for the {name} module."""\n'
        "\n"
        "from __future__ import annotations\n"
        "\n"
        "from fastapi import APIRouter\n"
        "\n"
        f'{name}_router = APIRouter(prefix="/{prefix}", tags=["{name}"])\n',
    )

    _write(
        base / "deps.py",
        f'"""FastAPI dependencies for the {name} module."""\n'
        "\n"
        "from __future__ import annotations\n",
    )

    _write(
        base / "admin.py",
        f'"""SQLAdmin views for the {name} module."""\n'
        "\n"
        "from __future__ import annotations\n"
        "\n"
        "\n"
        "def register_admin(admin) -> None:  # type: ignore[no-untyped-def]\n"
        "    pass\n",
    )

    _write(
        base / "metrics.py",
        f'"""Business metrics for the {name} module."""\n'
        "\n"
        "from prometheus_client import Counter\n"
        "\n"
        f"{name}_operations_total = Counter(\n"
        f'    "{name}_operations_total",\n'
        f'    "Total number of {name} operations.",\n'
        '    ["outcome"],  # labels: "success" | "failure"\n'
        ")\n",
    )

    _write(
        base / "tasks" / "__init__.py",
        f'"""Background tasks for the {name} module.\n'
        "\n"
        "Define TaskIQ tasks here as ``async def`` functions decorated with\n"
        "``@broker.task``, importing ``broker`` from\n"
        '``app.infrastructure.broker``.\n"""\n'
        "\n"
        "from __future__ import annotations\n",
    )

    _write(
        base / "crons" / "__init__.py",
        f'"""Scheduled background tasks for the {name} module.\n'
        "\n"
        'Define them as ``@broker.task(schedule=[{"cron": "0 2 * * *"}])``\n'
        "functions; ``app.infrastructure.scheduler`` discovers them from the\n"
        'broker registry.\n"""\n'
        "\n"
        "from __future__ import annotations\n",
    )

    _write(
        base / "events" / "__init__.py",
        f'"""Event signal names for the {name} module.\n'
        "\n"
        "Name them ``<module>.<past_tense_verb>``, e.g.\n"
        f'``{name.upper()}_CREATED = "{name}.created"``.\n"""\n'
        "\n"
        "from __future__ import annotations\n",
    )

    _write(
        base / "events" / "handlers.py",
        f'"""Event handlers for the {name} module.\n'
        "\n"
        "Import this module from ``application.py`` so the handlers below\n"
        'subscribe before the first request is served.\n"""\n'
        "\n"
        "from __future__ import annotations\n"
        "\n"
        "from app.events import subscribe  # noqa: F401\n",
    )


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


@cli.command("seed")
def seed() -> None:
    """Load fixture data from fixtures/users.json into the database."""
    # Lazy imports: avoids pulling the full app (DB engine, settings) into the
    # CLI process until the `seed` sub-command is actually invoked.
    import asyncio
    import json

    async def _run() -> None:
        from app.database.session import get_session
        from app.modules.users.repositories.user_repository import UserRepository
        from app.security.passwords import hash_password

        fixtures_path = Path("fixtures") / "users.json"
        if not fixtures_path.exists():
            typer.echo(f"No fixture file found at {fixtures_path}", err=True)
            raise typer.Exit(1)

        users_data: list[dict[str, str]] = json.loads(fixtures_path.read_text())

        async for session in get_session():
            repo = UserRepository(session)
            created = 0
            for u in users_data:
                if await repo.get_by_email(u["email"]) is None:
                    await repo.create(
                        email=u["email"],
                        hashed_password=hash_password(u.get("password", "changeme")),
                        full_name=u.get("full_name"),
                    )
                    created += 1
            skipped = len(users_data) - created
            typer.echo(f"Seeded {created} user(s) (skipped {skipped} existing).")

    asyncio.run(_run())


if __name__ == "__main__":
    cli()
