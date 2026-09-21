from app.main import app


def test_fastapi_project_shell_exposes_application_metadata() -> None:
    assert app.title == "LogistiAI"
    assert app.version == "0.1.0"
