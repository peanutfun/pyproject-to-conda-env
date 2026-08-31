import pytest
from pathlib import Path
import subprocess
import sys

import yaml
from tomlkit import document, table, dumps

from pyproject_to_conda_env import main


@pytest.fixture
def run_command(tmp_path):
    def cmd(
        *args: str,
        name: str = "pyproject-to-conda-env",
        timeout: float = 1,
        cwd=tmp_path,
    ):
        try:
            subprocess.run(
                [name, *args],
                capture_output=True,
                check=True,
                timeout=timeout,
                cwd=cwd,
            )
        except subprocess.CalledProcessError as err:
            print(err.output)
            print(err.stderr)
            raise

    return cmd


def write_toml(data, filepath):
    content = dumps(data)
    print(f"Content:\n{content}")
    with open(filepath, "w") as file:
        file.write(content)


def load_yaml(filepath):
    assert filepath.is_file()
    with open(filepath, "r") as file:
        return yaml.safe_load(file)


@pytest.fixture
def default_outfile(tmp_path):
    return tmp_path / "environment.yml"


@pytest.fixture
def pyproject_base():
    pyproj = document()

    project = table()
    project["name"] = "test"
    project["dependencies"] = ["dep1>1.0", "dep2<2.0", "dep3=1.0"]
    pyproj["project"] = project

    return pyproj


@pytest.fixture
def pyproject(pyproject_base):
    opt_deps = table()
    opt_deps["foo"] = ["opt1<1.0"]
    opt_deps["bar"] = ["opt2>1.1"]
    pyproject_base["project"].add("optional-dependencies", opt_deps)
    return pyproject_base


@pytest.fixture
def pyproject_file_no_ops(pyproject_base, tmp_path):
    outpath = tmp_path / "pyproject.toml"
    write_toml(pyproject_base, tmp_path / "pyproject.toml")
    return outpath


@pytest.fixture
def pyproject_file(pyproject, tmp_path):
    outpath = tmp_path / "pyproject.toml"
    write_toml(pyproject, tmp_path / "pyproject.toml")
    return outpath


@pytest.fixture
def assert_default(default_outfile):
    def check(outfile=default_outfile):
        out = load_yaml(outfile)
        assert out["name"] == "myenv"
        assert out["channels"] == ["conda-forge", "nodefaults"]
        assert out["dependencies"] == [
            "dep1>1.0",
            "dep2<2.0",
            "dep3=1.0",
            "opt1<1.0",
            "opt2>1.1",
        ]

    return check


def test_default(pyproject_file, run_command, assert_default):
    run_command(str(pyproject_file))
    assert_default()


def test_outpath(pyproject_file, tmp_path, run_command, assert_default):
    outfile = tmp_path / "out.yml"
    run_command(str(pyproject_file), "-o", str(outfile))
    assert_default(outfile)


def test_optional(pyproject_file, run_command, assert_default):
    run_command(str(pyproject_file), "-d")
    assert_default()


def test_optional_any(pyproject_file_no_ops, run_command, default_outfile):
    """No error if no optional dependencies are found"""
    run_command(str(pyproject_file_no_ops))
    out = load_yaml(default_outfile)
    assert out["dependencies"] == [
        "dep1>1.0",
        "dep2<2.0",
        "dep3=1.0",
    ]


@pytest.mark.parametrize("opt", ["-n", "--no-optional"])
def test_no_optional(pyproject_file, run_command, default_outfile, opt):
    run_command(str(pyproject_file), opt)
    out = load_yaml(default_outfile)
    assert out["dependencies"] == ["dep1>1.0", "dep2<2.0", "dep3=1.0"]


@pytest.mark.parametrize("opt", [["foo"], ["bar"], ["foo", "bar"]])
def test_optional_args(pyproject_file, run_command, default_outfile, opt):
    args = []
    for oo in opt:
        args.extend(["-d", oo])
    run_command(str(pyproject_file), *args)
    out = load_yaml(default_outfile)

    assert out["dependencies"][:3] == ["dep1>1.0", "dep2<2.0", "dep3=1.0"]
    assert ("opt1<1.0" in out["dependencies"]) == ("foo" in opt)
    assert ("opt2>1.1" in out["dependencies"]) == ("bar" in opt)


def test_optional_error(pyproject_file, run_command):
    with pytest.raises(subprocess.CalledProcessError):
        run_command(str(pyproject_file), "-d", "foo", "-n")
