from pathlib import Path

from app.main import DEFAULT_DATABASE_URL, app


def test_fastapi_project_shell_exposes_application_metadata() -> None:
    assert app.title == "LogistiAI"
    assert app.version == "0.1.0"


def test_default_database_is_located_under_backend_regardless_of_process_directory() -> None:
    path = Path(DEFAULT_DATABASE_URL.removeprefix("sqlite:///"))

    assert path.parent.name == "data"
    assert path.parent.parent.name == "backend"
