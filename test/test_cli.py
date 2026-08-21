import pytest
from pathlib import Path
import subprocess
import sys

from clirunner import CliRunner
import yaml

from pyproject_to_conda_env import main


def run_command(*args: str, name: str = "pyproject-to-conda-env", timeout: float = 1):
    """Run a command"""
    try:
        subprocess.run(
            [name, *args],
            capture_output=True,
            check=True,
            timeout=timeout,
        )
    except subprocess.CalledProcessError as err:
        print(err.output)
        print(err.stderr)
        raise


@pytest.fixture
def clirunner():
    return CliRunner()


@pytest.fixture
def thisdir():
    return Path(__file__).parent


# TODO: Add result as fixture
# TODO: Add dedicated testdir (maybe via conftest.py?)
def test1(tmpdir, thisdir):
    outfile = tmpdir / "environment.yml"
    # result = clirunner.invoke(
    #     main,
    #     [str(thisdir / "test1.toml"), str(thisdir / "test1.yml"), "-o", str(outfile)],
    # )
    # if result.exit_code != 0:
    #     print(result.exception)
    #     assert False, "CLI returned non-zero exit code"
    run_command(
        str(thisdir / "test1.toml"), "-t", str(thisdir / "test1.yml"), "-o", str(outfile)
    )

    assert outfile.isfile()
    with open(outfile, "r") as file:
        out = yaml.safe_load(file)
    with open(thisdir / "test1-result.yml") as file:
        assert out == yaml.safe_load(file)
