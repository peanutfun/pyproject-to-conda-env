import pytest
from pathlib import Path

from clirunner import CliRunner
import yaml

from pyproject_to_conda_env import main


@pytest.fixture
def clirunner():
    return CliRunner()


@pytest.fixture
def thisdir():
    return Path(__file__).parent

# TODO: Add result as fixture
# TODO: Add dedicated testdir (maybe via conftest.py?)
def test1(clirunner, tmpdir, thisdir):
    outfile = tmpdir / "environment.yml"
    result = clirunner.invoke(
        main,
        [str(thisdir / "test1.toml"), str(thisdir / "test1.yml"), "-o", str(outfile)],
    )
    if result.exit_code != 0:
        print(result.exception)
        assert False, "CLI returned non-zero exit code"

    assert outfile.isfile()
    with open(outfile, "r") as file:
        out = yaml.safe_load(file)
    with open(thisdir / "test1-result.yml") as file:
        assert out == yaml.safe_load(file)
    outfile.remove()
