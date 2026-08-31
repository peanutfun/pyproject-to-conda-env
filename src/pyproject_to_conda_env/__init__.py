import warnings

from .argparse import parse_args
from .funcs import (
    assert_transform,
    read_pyproject,
    read_transform,
    read_dependencies,
    add_dependencies,
    remove_dependencies,
    convert_dependencies,
    write_environment_file,
    ADDITIONS,
    DELETIONS,
    CONVERSIONS,
    PIP_REQUIREMENTS,
    PROJECT_NAME
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
    dependencies = read_dependencies(pyproject_data, optional)
    dependencies = remove_dependencies(dependencies, transform[DELETIONS])
    dependencies = convert_dependencies(dependencies, transform[CONVERSIONS])
    dependencies = add_dependencies(
        sorted(dependencies), transform[ADDITIONS], transform[PIP_REQUIREMENTS]
    )

    # Output
    write_environment_file(
        dependencies, args.output, transform["name"], transform["channels"]
    )
