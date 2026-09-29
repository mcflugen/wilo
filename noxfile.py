from __future__ import annotations

import glob
import os
import shutil

import nox

ROOT = os.path.dirname(os.path.abspath(__file__))

nox.options.sessions = ("lint", "coverage")


@nox.session
def lint(session: nox.Session) -> None:
    """Run the linters."""
    session.install("pre-commit")
    session.run("pre-commit", "run", "--all-files")


@nox.session
def coverage(session: nox.Session) -> None:
    """Run coverage."""
    session.install("coverage", "pytest")
    session.install("-e", ".[optimize,tables]")

    session.run(
        "coverage",
        "run",
        "-m",
        "pytest",
        "src/wilo",
        "tests",
        "--doctest-modules",
        env={"COVERAGE_CORE": "sysmon"},
    )

    session.run("coverage", "report", "--ignore-errors", "--show-missing")
    if "CI" in os.environ:
        session.run("coverage", "xml", "-o", "coverage.xml")


@nox.session
def build(session: nox.Session) -> None:
    """Build sdist and wheel dists."""
    dists = _build(session, dest=os.path.join(ROOT, "dist"))
    for dist in dists:
        session.log(f"✅ {dist}")


@nox.session
def install(session: nox.Session) -> None:
    """Install package from source or, optionally, from a wheel."""
    _install_from_path(session, path=session.posargs[0] if session.posargs else None)


@nox.session
def test(session: nox.Session) -> None:
    """Run the tests."""
    _test(session, path=session.posargs[0] if session.posargs else None)


@nox.session(name="test-build")
def test_build(session: nox.Session) -> None:
    """Run the tests on a distribution."""
    dist_files = _build(session, dest=os.path.join(ROOT, "dist"))

    if len(dist_files) == 0:
        session.error("no distributions were built")

    wheel = next((dist for dist in dist_files if dist.endswith(".whl")), dist_files[0])

    session.log(f"✅ testing... {wheel}")
    _test(session, path=wheel)


def _test(session: nox.Session, path: str | None = None) -> None:
    session.install("pytest")
    _install_from_path(session, path=path)
    session.run("pytest", "--doctest-modules", "--pyargs", "wilo", "tests/")


def _build(session: nox.Session, dest=".") -> tuple[str, ...]:
    session.install("build")

    tmpdir = session.create_tmp()
    session.run("python", "-m", "build", "--outdir", tmpdir)

    wheels = glob.glob(os.path.join(tmpdir, "*.whl"))
    sdists = glob.glob(os.path.join(tmpdir, "*.tar.gz"))

    os.makedirs(dest, exist_ok=True)

    copied = []
    for src in wheels + sdists:
        fname = os.path.join(dest, os.path.basename(src))
        shutil.copy2(src, fname)
        copied.append(fname)

    return tuple(copied)


def _install_from_path(session: nox.Session, path: str | None = None) -> None:
    if path is None:
        session.install("-e", ".[optimize,tables]")
    elif os.path.isfile(path):
        session.install(f"{path}[optimize,tables]")
    elif os.path.isdir(path):
        session.install(
            "wilo",
            f"--find-links={path}",
            "--no-index",
        )
    else:
        session.error("path must be a source distribution or folder")
