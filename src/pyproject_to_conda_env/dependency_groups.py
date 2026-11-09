"""
Dependency group implementations from
https://packaging.python.org/en/latest/specifications/dependency-groups/
"""

import re
import sys
import tomllib
from collections import defaultdict

from packaging.requirements import Requirement


def _normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def normalize_group_names(dependency_groups: dict) -> dict:
    original_names = defaultdict(list)
    normalized_groups = {}

    for group_name, value in dependency_groups.items():
        normed_group_name = _normalize_name(group_name)
        original_names[normed_group_name].append(group_name)
        normalized_groups[normed_group_name] = value

    errors = []
    for normed_name, names in original_names.items():
        if len(names) > 1:
            errors.append(f"{normed_name} ({', '.join(names)})")
    if errors:
        raise ValueError(f"Duplicate dependency group names: {', '.join(errors)}")

    return normalized_groups


def _resolve_dependency_group(
    dependency_groups: dict, group: str, past_groups: tuple[str, ...] = ()
) -> list[str]:
    if group in past_groups:
        raise ValueError(f"Cyclic dependency group include: {group} -> {past_groups}")

    if group not in dependency_groups:
        raise LookupError(f"Dependency group '{group}' not found")

    raw_group = dependency_groups[group]
    if not isinstance(raw_group, list):
        raise ValueError(f"Dependency group '{group}' is not a list")

    realized_group = []
    for item in raw_group:
        if isinstance(item, str):
            # packaging.requirements.Requirement parsing ensures that this
            # is a valid dependency specifier
            # raises InvalidRequirement on failure
            Requirement(item)
            realized_group.append(item)
        elif isinstance(item, dict):
            if tuple(item.keys()) != ("include-group",):
                raise ValueError(f"Invalid dependency group item: {item}")

            include_group = _normalize_name(next(iter(item.values())))
            realized_group.extend(
                _resolve_dependency_group(
                    dependency_groups, include_group, past_groups + (group,)
                )
            )
        else:
            raise ValueError(f"Invalid dependency group item: {item}")

    return realized_group


def resolve(dependency_groups: dict, group: str) -> list[str]:
    if not isinstance(dependency_groups, dict):
        raise TypeError("Dependency groups table is not a dict")
    if not isinstance(group, str):
        raise TypeError("Dependency group name is not a str")
    return _resolve_dependency_group(dependency_groups, group)


if __name__ == "__main__":
    with open("pyproject.toml", "rb") as fp:
        pyproject = tomllib.load(fp)

    dependency_groups_raw = pyproject["dependency-groups"]
    dependency_groups = normalize_group_names(dependency_groups_raw)
    print("\n".join(resolve(dependency_groups, sys.argv[1])))
