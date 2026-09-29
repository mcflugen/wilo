import pytest

from wilo._cli import main


def test_help(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.startswith("usage:")


def test_no_args(capsys):
    assert main([]) == 0
    assert capsys.readouterr().out.startswith("usage:")


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.startswith("wilo")
