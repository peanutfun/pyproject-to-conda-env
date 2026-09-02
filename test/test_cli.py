import pytest
import subprocess

import yaml
from tomlkit import document, table, dumps

from pyproject_to_conda_env import (
    ADDITIONS,
    DELETIONS,
    CONVERSIONS,
    PIP_REQUIREMENTS,
)


# ------------------------------ #
# FIXTURES
# ------------------------------ #


class CommandError(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


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
            print(err.output.decode("utf8"))
            print(err.stderr.decode("utf8"))
            raise CommandError(err.stderr.decode("utf8"))

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


# --- pyproject.toml fixtures --- #


@pytest.fixture
def pyproject_base():
    pyproj = document()

    project = table()
    project["name"] = "test"
    project["dependencies"] = ["dep1>1.0", "dep2<2.0", "dep3==1.0"]
    pyproj["project"] = project

    dep_groups = table()
    dep_groups["dev"] = [{"include-group": "test"}, "jupyter"]
    dep_groups["test"] = ["pytest"]
    dep_groups["coverage"] = ["coverage"]
    pyproj["dependency-groups"] = dep_groups

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
            "dep3==1.0",
            "opt1<1.0",
            "opt2>1.1",
        ]

    return check


# --- transform.yml fixtures --- #


@pytest.fixture
def transform_base():
    return {
        "name": "test1",
        "channels": ["foo"],
        ADDITIONS: ["dep4"],
        DELETIONS: ["dep1"],
        CONVERSIONS: {"dep3": "dep3-base", "opt": "arg", "opt1": "arg"},
        PIP_REQUIREMENTS: ["dep2"],
    }


@pytest.fixture
def transform(transform_base, tmp_path):
    transform_path = tmp_path / "transform.yml"
    content = yaml.dump(transform_base)
    with open(transform_path, "w") as file:
        file.writelines(content)
    return transform_path


# ------------------------------ #
# TESTS
# ------------------------------ #


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
        "dep3==1.0",
    ]


@pytest.mark.parametrize("opt", ["-n", "--no-optional"])
def test_no_optional(pyproject_file, run_command, default_outfile, opt):
    run_command(str(pyproject_file), opt)
    out = load_yaml(default_outfile)
    assert out["dependencies"] == ["dep1>1.0", "dep2<2.0", "dep3==1.0"]


@pytest.mark.parametrize("opt", [["foo"], ["bar"], ["foo", "bar"]])
def test_optional_args(pyproject_file, run_command, default_outfile, opt):
    args = []
    for oo in opt:
        args.extend(["-d", oo])
    run_command(str(pyproject_file), *args)
    out = load_yaml(default_outfile)

    assert out["dependencies"][:3] == ["dep1>1.0", "dep2<2.0", "dep3==1.0"]
    assert ("opt1<1.0" in out["dependencies"]) == ("foo" in opt)
    assert ("opt2>1.1" in out["dependencies"]) == ("bar" in opt)


def test_optional_error(pyproject_file, run_command):
    with pytest.raises(CommandError, match="'--no-optional' contradicts"):
        run_command(str(pyproject_file), "-d", "foo", "-n")


def test_default_transform(
    pyproject_file, run_command, transform, transform_base, default_outfile
):
    run_command(str(pyproject_file), "-t", str(transform))
    out = load_yaml(default_outfile)
    assert out["name"] == transform_base["name"]
    assert out["channels"] == transform_base["channels"]
    assert out["dependencies"] == [
        "arg<1.0",
        "dep3-base==1.0",
        "dep4",
        "opt2>1.1",
        "pip",
        {"pip": ["dep2<2.0"]},
    ]


def test_transform_no_optional(
    pyproject_file, run_command, transform, transform_base, default_outfile
):
    run_command(str(pyproject_file), "-t", str(transform), "-n")
    out = load_yaml(default_outfile)
    assert out["name"] == transform_base["name"]
    assert out["channels"] == transform_base["channels"]
    assert out["dependencies"] == [
        "dep3-base==1.0",
        "dep4",
        "pip",
        {"pip": ["dep2<2.0"]},
    ]


def test_dependency_group_recursive(pyproject_file, run_command, default_outfile):
    run_command(str(pyproject_file), "-g", "dev")
    out = load_yaml(default_outfile)
    assert "pytest" in out["dependencies"]
    assert "jupyter" in out["dependencies"]


def test_dependency_group_multiple(pyproject_file, run_command, default_outfile):
    run_command(str(pyproject_file), "-g", "test", "-g", "coverage")
    out = load_yaml(default_outfile)
    assert "pytest" in out["dependencies"]
    assert "coverage" in out["dependencies"]
