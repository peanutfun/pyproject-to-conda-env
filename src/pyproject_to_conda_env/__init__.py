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
    PROJECT_NAME,
)


def main():
    args = parse_args()

    pyproject_data = read_pyproject(args.pyproject)
    transform = read_transform(args.transform)
    assert_transform(transform)

    dependencies = read_dependencies(pyproject_data, args.optional)
    dependencies = remove_dependencies(dependencies, transform[DELETIONS])
    dependencies = convert_dependencies(dependencies, transform[CONVERSIONS])
    dependencies = add_dependencies(
        sorted(dependencies), transform[ADDITIONS], transform[PIP_REQUIREMENTS]
    )

    write_environment_file(
        dependencies, args.output, transform["name"], transform["channels"]
    )

