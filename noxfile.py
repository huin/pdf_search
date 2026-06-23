import nox
import nox_uv

nox.options.default_venv_backend = "uv"
nox.options.reuse_venv = "yes"
nox.options.sessions = [
    # Run format first to fix things before they are checked.
    "format",
    "check",
]

_PYTHON_PATHS = [
    "noxfile.py",
    "src/",
]


@nox_uv.session(uv_groups=["format"])
def format(session: nox.Session) -> None:
    """Format code."""
    session.run("isort", *_PYTHON_PATHS)
    session.run("ruff", "format", *_PYTHON_PATHS)


@nox_uv.session(uv_groups=["check"])
def check(session: nox.Session) -> None:
    """Statically check code."""
    session.run("flake8", *_PYTHON_PATHS)
    session.run("ty", "check", *_PYTHON_PATHS)
