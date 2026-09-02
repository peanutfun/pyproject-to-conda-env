# pyproject-to-conda-env

A simple Python tool for converting dependencies specified in a `pyproject.toml` into a Conda `environment.yml` file.

Its main purpose is to be used as automated pre-commit hook to automatically align dependency specifications.

## Installation

Just use `pip` to install the package into your current Python environment:
```
pip install pyproject-to-conda-env@git+https://github.com/peanutfun/pyproject-to-conda-env
```

## Usage

After installation, the package provides a shell script `pyproject-to-conda-env` for creating a Conda environment file.

```shell
pyproject-to-conda-env <pyproject> [options]
```

Arguments and options:

| Argument | Explanation | Required | Type | Default Value |
|---|---|---|---|---|
| `pyproject` | Path to the `pyproject.toml` file | Yes | Path | None |
| `--output`, `-o` | Path to the output environment file | No | Path | `environment.yml` |
| `--optional`, `-d` | Optional dependencies to include. Use without value to include all. Can be specified multiple times. | No | str | None |
| `--no-optional`, `-n` | Do not use any optional dependecies | No | None | None |
| `--dependency-group`, `-g` | Dependency group to include. Can be stated multiple times. | No | str | None |
| `--transform`, `-t` | Path to a transformation YAML file | No | Path | None |

### Notes on additional dependencies

The default behavior for [**optional dependencies**](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#dependencies-optional-dependencies) is to include any optional dependencies if no options are specified.
If `-d` is given without an argument, all optional dependencies are collected, and an error is raised if none are listed in `pyproject`.
If `-d <opt>` is given, only the optional dependencies listed under `<opt>` are included, and an error is raised if it cannot be found.
This option may be stated multiple times.
If `-n` is given, no optional dependencies are included.

By default, [**dependency groups**](https://packaging.python.org/en/latest/specifications/dependency-groups/) are **not** included.
Using the `-g` option, they can be added manually.

### Transform file

The script supports additional input via a "transform" YAML file to support disparities between Conda and PyPI package specifications.
The file supports setting a custom Conda environment name, Conda channels, package additions, package deletions, package "conversions" (renaming a package), and pip requirements (requirements that are to be installed via pip exclusively).

For deletion and conversion, matching between the transform file and the `pyproject.toml` specs is done in a relaxed fashion: Either the names, or the exact specs have to match.
Note that conversion values (the value converted to) can only state package names, **not** entire specs.
If you need to change specs, delete a package and add it with another spec.

Consider a package that specifies `dependencies = ["numpy", "pandas>2", "tables>3.0"]` in its `pyproject.toml` and the following `transform.yml`:

```yaml
name: my-fancy-env
channels: [conda-forge]
additions:
  - numpy>1.1
deletions:
  - numpy
conversions:
  tables: pytables
pip-requirements:
  - pandas
```

Executing the script
```
pyproject-to-conda-env pyproject.toml -t transform.yml
```
will yield the following `environment.yml`:

```yaml
name: my-fancy-env
channels:
  - conda-forge
dependencies:
  - numpy>1.1
  - pip
  - pytables>3.0
  - pip:
    - pandas>2
```

### Execution order

The script follows this order when running:

* Collect the dependencies
* If specified, collect dependency groups.
* Collect any optional dependencies, unless specified otherwise.
* If a transform file is given ...
    - remove dependencies as stated,
    - convert dependencies as stated,
    - add dependencies as stated, and
    - move or add dependencies to pip requirements.
    - If pip requirments are present, add pip to the dependencies unless it is already given.
* Write the environment file.


## Pre-commit hook

Register the script as pre-commit hook to automatically update Conda environment files when you change your `pyproject.toml`.

When using [pre-commit](https://pre-commit.com/), you can write a `.pre-commit-config.yaml` like so:

```yaml
repos:
  - repo: https://github.com/peanutfun/pyproject-to-conda-env
    rev: 1.0
    hooks:
      - id: pyproject_to_conda_env
        files: ^(pyproject\.toml|transform\.yml|environment\.yml)$
        args: [pyproject.toml, -t, transform.yml]
```
