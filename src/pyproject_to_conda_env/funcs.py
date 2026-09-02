from platform import release
import tomllib
from pathlib import Path
from typing import Any
from collections.abc import Mapping
import warnings

import yaml
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from .dependency_groups import resolve, normalize_group_names

ADDITIONS = "additions"
DELETIONS = "deletions"
CONVERSIONS = "conversions"
PIP_REQUIREMENTS = "pip-requirements"

PROJECT_NAME = "pyproject-to-conda-env"


def relaxed_eq(precise: Requirement, relaxed: str) -> bool:
    relaxed = relaxed.strip()
    if canonicalize_name(relaxed) == canonicalize_name(precise.name):
        return True
    return precise == Requirement(relaxed)


def read_pyproject(path: str | Path = "pyproject.toml") -> dict[str, Any]:
    """Read the pyproject file as dict"""
    with open(path, "rb") as file:
        return tomllib.load(file)


def read_transform(path: str | Path) -> dict[str, Any]:
    """Read the transformation YAML file"""
    with open(path, "r") as file:
        return yaml.safe_load(file) or {}


def assert_transform(transform: dict[str, Any]):
    """Assert transformation structure"""
    assert "name" in transform
    assert isinstance(transform["name"], str)
    assert "channels" in transform
    assert isinstance(transform["channels"], list)
    assert ADDITIONS in transform
    assert DELETIONS in transform
    assert CONVERSIONS in transform
    assert PIP_REQUIREMENTS in transform


def read_dependencies(
    pyproj_data: dict[str, Any],
    optional_dependencies: bool | list[str],
    dependency_groups: list[str] | None = None,
) -> list[str]:
    """Read all dependencies (also optional) and merge them

    Handling of ``optional_dependencies``:

    - A list of values: Throw an error if any cannot be found
    - True: Use all. Throw an error if none can be found
    - Empty list: Use all that can be found (including none)
    - False: Use none.
    """
    dependencies: list[str] = pyproj_data["project"]["dependencies"].copy()
    if dependency_groups:
        dep_groups = normalize_group_names(pyproj_data.get("dependency-groups", {}))
        if not dep_groups:
            raise LookupError("No dependency groups found")
        for group in dependency_groups:
            dependencies.extend(resolve(dep_groups, group))

    if optional_dependencies is False:
        return dependencies

    opt_deps = pyproj_data["project"].get("optional-dependencies", {})
    opt_dep_groups = list(opt_deps.keys())
    if optional_dependencies:
        if not opt_deps:
            raise RuntimeError("No optional dependencies found in pyproject data")
        if optional_dependencies is not True:
            opt_dep_groups = optional_dependencies

    # Take all that are listed
    for group in opt_dep_groups:
        try:
            dependencies.extend(opt_deps[group])
        except KeyError as err:
            if optional_dependencies:
                raise LookupError(f"Optional dependency not found: {group}") from err

    return dependencies


def remove_dependencies(dep_list: list[str], deletions: list[str] | None) -> list[str]:
    """Remove dependencies"""
    if deletions is None:
        return dep_list.copy()

    requirements = [Requirement(dep) for dep in dep_list]
    return [
        str(req)
        for req in requirements
        if not any(relaxed_eq(req, dd) for dd in deletions)
    ]


# TODO: Just use find str.replace for conversion?
def convert_dependencies(
    dep_list: list[str], conversion_table: Mapping[str, str] | None
) -> list[str]:
    """Convert dependency names"""
    if conversion_table is None:
        return dep_list.copy()

    requirements = [Requirement(dep) for dep in dep_list]
    for dep_from, dep_to in conversion_table.items():
        dep_from = dep_from.strip()
        matched = False
        for req in requirements:
            if relaxed_eq(req, dep_from):
                req.name = dep_to.strip()
                matched = True
        if not matched:
            warnings.warn(f"No match for conversion found: {dep_from}", RuntimeWarning)

    return [str(req) for req in requirements]


def add_dependencies(
    dep_list: list[str], additions: list[str] | None, pip_requirements: list[str] | None
) -> list[str]:
    """Add dependencies"""
    dep_list = dep_list.copy()
    if additions:
        dep_list.extend(additions)
        dep_list.sort()
    if pip_requirements:
        # NOTE: Need to keep the deleted entries to preserve version specs
        dep_list_no_pip = remove_dependencies(dep_list, pip_requirements)
        pip_reqs_with_versions = list(set(dep_list) - set(dep_list_no_pip))

        def version_given(dependency: str) -> bool:
            for dep_ver in pip_reqs_with_versions:
                if dependency == Requirement(dep_ver).name:
                    return True
            return False

        pip_reqs_without_versions = [
            dep for dep in pip_requirements if not version_given(dep)
        ]
        pip_reqs = pip_reqs_with_versions + pip_reqs_without_versions
        if not pip_reqs:
            pass

        if "pip" not in dep_list:
            dep_list_no_pip.append("pip")
        dep_list_no_pip.sort()
        dep_list_no_pip.append({"pip": sorted(pip_reqs)})
        dep_list = dep_list_no_pip
    return dep_list


def write_environment_file(
    dependencies: list[str | dict[str, list[str]]],
    output_path: str | Path,
    name: str,
    channels: list[str],
):
    """Write the conda environment file"""
    # Merge content
    data = {
        "name": name,
        "channels": channels,
        "dependencies": dependencies,
    }
    content = yaml.dump(data)
    content = (
        "# DO NOT MODIFY!\n"
        f"# This file was automatically generated by '{PROJECT_NAME}'\n"
    ) + content

    # Write file
    with open(output_path, "w") as file:
        file.writelines(content)
