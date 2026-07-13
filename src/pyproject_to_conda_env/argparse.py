import argparse
from pathlib import Path


def parse_args():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
        prog="pyproject_to_conda_env",
        description="Transform pyproject.toml dependencies into a conda env file",
    )
    parser.add_argument("pyproject", type=Path, help="Path to the pyproject.toml file")
    parser.add_argument("transform", type=Path, help="Path to the transform YAML file")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default="environment.yml",
        help="Conda environment file output path",
    )
    parser.add_argument(
        "--dev", action="store_true", help="Include 'dev' dependency group"
    )
    parser.add_argument(
        "-d",
        "--optional",
        nargs="*",
        default=True,
        help="Optional dependencies to include",
    )
    parser.add_argument(
        "-n",
        "--no-optional",
        action="store_true",
        help="Do not include optional dependencies",
    )

    # Parse arguments
    args = parser.parse_args()

    # Check arguments
    if args.optional is not True and args.no_optional:
        raise RuntimeError(
            "'--no-optional' contradicts specifying '--optional' dependencies"
        )

    # Return arguments
    return args
