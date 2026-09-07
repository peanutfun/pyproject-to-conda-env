import warnings

from .argparse import parse_args
from .funcs import (
    ADDITIONS,
    CONVERSIONS,
    DELETIONS,
    PIP_REQUIREMENTS,
    PROJECT_NAME,
    add_dependencies,
    assert_transform,
    convert_dependencies,
    read_dependencies,
    read_pyproject,
    read_transform,
    remove_dependencies,
    write_environment_file,
)


def main():
    # Parse arguments
    args = parse_args()
    optional = args.optional

    # Normalize
    if isinstance(optional, list) and any(opt is True for opt in optional):
        warnings.warn("Ignoring ")
        optional = True

    # Check consistency
    if args.no_optional:
        if optional:
            raise RuntimeError(
                "'--no-optional' contradicts specifying '--optional' dependencies"
            )
        optional = False

    # Read pyproject.toml
    pyproject_data = read_pyproject(args.pyproject)

    # Read transform or use default
    transform = {
        "name": "myenv",
        "channels": [
            "conda-forge",
            "nodefaults",
        ],
        ADDITIONS: [],
        DELETIONS: [],
        CONVERSIONS: {},
        PIP_REQUIREMENTS: [],
    }
    if args.transform is not None:
        transform = read_transform(args.transform)
    assert_transform(transform)

    # Transformations
    dependencies = read_dependencies(pyproject_data, optional, args.dependency_group)
    dependencies = remove_dependencies(dependencies, transform[DELETIONS])
    dependencies = convert_dependencies(dependencies, transform[CONVERSIONS])
    dependencies = add_dependencies(
        sorted(dependencies), transform[ADDITIONS], transform[PIP_REQUIREMENTS]
    )

    # Output
    write_environment_file(
        dependencies, args.output, transform["name"], transform["channels"]
    )


__all__ = [
    "ADDITIONS",
    "CONVERSIONS",
    "DELETIONS",
    "PIP_REQUIREMENTS",
    "PROJECT_NAME",
    "add_dependencies",
    "assert_transform",
    "convert_dependencies",
    "read_dependencies",
    "read_pyproject",
    "read_transform",
    "remove_dependencies",
    "write_environment_file",
    "main",
]
