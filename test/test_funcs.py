"""
Unit tests for the pyproject -> conda environment transformation utilities.

NOTE: These tests assume the functions under test live in a module called
``env_transform.py`` (adjust the import below to match the actual filename
of the module you shared, e.g. ``from make_environment import ...``).
"""

from pathlib import Path

import pytest
import yaml

from pyproject_to_conda_env import (
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


# ---------------------------------------------------------------------------
# read_pyproject
# ---------------------------------------------------------------------------


class TestReadPyproject:
    @pytest.fixture
    def content(self):
        return """
[project]
name = "demo"
dependencies = ["numpy", "pandas"]
"""

    def test_reads_valid_toml(self, tmp_path, content):
        path = tmp_path / "pyproject.toml"
        path.write_text(content)

        result = read_pyproject(path)
        assert result == {
            "project": {"name": "demo", "dependencies": ["numpy", "pandas"]}
        }

    def test_accepts_string_path(self, tmp_path, content):
        path = tmp_path / "pyproject.toml"
        path.write_text(content)

        result = read_pyproject(str(path))
        assert result == {
            "project": {"name": "demo", "dependencies": ["numpy", "pandas"]}
        }

    def test_missing_file_raises(self, tmp_path):
        missing = tmp_path / "does_not_exist.toml"
        with pytest.raises(FileNotFoundError):
            read_pyproject(missing)

    def test_invalid_toml_raises(self, tmp_path):
        path = tmp_path / "bad.toml"
        path.write_text("this is not [valid toml")
        with pytest.raises(Exception):
            read_pyproject(path)


# ---------------------------------------------------------------------------
# read_transform
# ---------------------------------------------------------------------------


class TestReadTransform:
    @pytest.fixture
    def content(self):
        return f"""
name: env
channels:
  - "conda-forge"
{ADDITIONS}: []
{DELETIONS}: []
{CONVERSIONS}: {{ }}
{PIP_REQUIREMENTS}: []
"""

    @pytest.fixture
    def data(self):
        return {
            "name": "env",
            "channels": ["conda-forge"],
            ADDITIONS: [],
            DELETIONS: [],
            CONVERSIONS: {},
            PIP_REQUIREMENTS: [],
        }

    @pytest.mark.parametrize("path_convert", [Path, str])
    def test_reads_valid_yaml(self, tmp_path, content, data, path_convert):
        path = tmp_path / "transform.yaml"
        path.write_text(content)

        result = read_transform(path_convert(path))
        assert result == data

    def test_empty_file_returns_none(self, tmp_path):
        path = tmp_path / "empty.yaml"
        path.write_text("")

        assert read_transform(path) == {}

    def test_missing_file_raises(self, tmp_path):
        missing = tmp_path / "does_not_exist.yaml"
        with pytest.raises(FileNotFoundError):
            read_transform(missing)


# ---------------------------------------------------------------------------
# assert_transform
# ---------------------------------------------------------------------------


class TestAssertTransform:
    @pytest.fixture
    def transform(self):
        return {
            "name": "myenv",
            "channels": ["conda-forge", "defaults"],
            ADDITIONS: ["extra-pkg"],
            DELETIONS: ["unwanted-pkg"],
            CONVERSIONS: {"foo": "bar"},
            PIP_REQUIREMENTS: ["some-pip-pkg"],
        }

    def test_valid_transform_passes(self, transform):
        # Should not raise
        assert_transform(transform)

    @pytest.mark.parametrize(
        "key",
        ["name", "channels", ADDITIONS, DELETIONS, CONVERSIONS, PIP_REQUIREMENTS],
    )
    def test_missing_key_raises(self, key, transform):
        del transform[key]
        with pytest.raises(AssertionError):
            assert_transform(transform)

    def test_name_wrong_type_raises(self, transform):
        transform["name"] = 123  # Not str
        with pytest.raises(AssertionError):
            assert_transform(transform)

    def test_channels_wrong_type_raises(self, transform):
        transform["channels"] = "not-a-list"
        with pytest.raises(AssertionError):
            assert_transform(transform)

    def test_values_of_additions_etc_can_be_none(self, transform):
        # The function only checks key presence, not value type/content
        transform[ADDITIONS] = None
        transform[DELETIONS] = None
        transform[CONVERSIONS] = None
        transform[PIP_REQUIREMENTS] = None
        assert_transform(transform)  # should not raise


# ---------------------------------------------------------------------------
# read_dependencies
# ---------------------------------------------------------------------------


class TestReadDependencies:
    @pytest.fixture
    def data(self):
        return {
            "project": {
                "dependencies": ["numpy", "pandas"],
                "optional-dependencies": {
                    "dev": ["pytest", "black"],
                    "docs": ["sphinx"],
                },
            }
        }

    def test_no_optional_dependencies_false(self, data):
        result = read_dependencies(data, False)
        assert result == ["numpy", "pandas"]

    def test_no_optional_dependencies_empty_list(self, data):
        result = read_dependencies(data, [])
        assert result == ["numpy", "pandas"]

    def test_all_optional_dependencies_true(self, data):
        result = read_dependencies(data, True)
        assert set(result) == {"numpy", "pandas", "pytest", "black", "sphinx"}

    def test_specific_optional_dependency_group(self, data):
        result = read_dependencies(data, ["dev"])
        assert set(result) == {"numpy", "pandas", "pytest", "black"}
        assert "sphinx" not in result

    def test_multiple_specific_groups(self, data):
        result = read_dependencies(data, ["dev", "docs"])
        assert set(result) == {"numpy", "pandas", "pytest", "black", "sphinx"}

    def test_unknown_group_raises_keyerror(self, data):
        with pytest.raises(KeyError, match="nonexistent"):
            read_dependencies(data, ["nonexistent"])

    def test_missing_optional_dependencies_key_with_true(self):
        data = {"project": {"dependencies": ["numpy"]}}
        with pytest.raises(KeyError, match="optional-dependencies"):
            read_dependencies(data, True)

    def test_data_not_mutated(self, data):
        original_list = data["project"]["dependencies"]
        read_dependencies(data, ["dev"])
        assert original_list == ["numpy", "pandas"]


# ---------------------------------------------------------------------------
# remove_dependencies
# ---------------------------------------------------------------------------


class TestRemoveDependencies:
    def test_deletions_none_returns_copy(self):
        deps = ["numpy", "pandas"]
        result = remove_dependencies(deps, None)
        assert result == deps
        assert result is not deps  # it's a copy

    def test_removes_exact_match(self):
        deps = ["numpy", "pandas", "scipy"]
        result = remove_dependencies(deps, ["pandas"])
        assert result == ["numpy", "scipy"]

    def test_removes_substring_match(self):
        deps = ["numpy==1.2.3", "pandas>=2.0", "scipy"]
        result = remove_dependencies(deps, ["numpy"])
        assert result == ["pandas>=2.0", "scipy"]

    def test_multiple_deletions(self):
        deps = ["numpy", "pandas", "scipy", "requests"]
        result = remove_dependencies(deps, ["numpy", "scipy"])
        assert result == ["pandas", "requests"]

    def test_empty_deletions_list_removes_nothing(self):
        deps = ["numpy", "pandas"]
        result = remove_dependencies(deps, [])
        assert result == deps

    def test_deletion_not_present_no_effect(self):
        deps = ["numpy", "pandas"]
        result = remove_dependencies(deps, ["nonexistent"])
        assert result == deps

    def test_does_not_mutate_input(self):
        deps = ["numpy", "pandas"]
        remove_dependencies(deps, ["numpy"])
        assert deps == ["numpy", "pandas"]

    def test_empty_dep_list(self):
        assert remove_dependencies([], ["numpy"]) == []


# ---------------------------------------------------------------------------
# convert_dependencies
# ---------------------------------------------------------------------------


class TestConvertDependencies:
    def test_conversion_table_none_returns_copy(self):
        deps = ["numpy", "pandas"]
        result = convert_dependencies(deps, None)
        assert result == deps
        assert result is not deps

    def test_converts_matching_substring(self):
        deps = ["pytorch", "pandas"]
        result = convert_dependencies(deps, {"pytorch": "pytorch-cpu"})
        assert result == ["pytorch-cpu", "pandas"]

    def test_converts_with_version_spec_preserved(self):
        deps = ["pytorch==2.0.0"]
        result = convert_dependencies(deps, {"pytorch": "pytorch-cpu"})
        assert result == ["pytorch-cpu==2.0.0"]

    def test_no_match_leaves_dependency_unchanged(self):
        deps = ["numpy", "pandas"]
        result = convert_dependencies(deps, {"scipy": "scipy-alt"})
        assert result == ["numpy", "pandas"]

    def test_empty_conversion_table(self):
        deps = ["numpy", "pandas"]
        result = convert_dependencies(deps, {})
        assert result == deps

    def test_first_matching_rule_applied_only(self):
        # dict iteration order == insertion order in modern Python
        deps = ["foobar"]
        result = convert_dependencies(deps, {"foo": "AAA", "foobar": "BBB"})
        assert result == ["AAAbar"]

    def test_does_not_mutate_input(self):
        deps = ["pytorch"]
        convert_dependencies(deps, {"pytorch": "pytorch-cpu"})
        assert deps == ["pytorch"]

    def test_empty_dep_list(self):
        deps = []
        result = convert_dependencies(deps, {"a": "b"})
        assert result == deps
        assert result is not deps


# ---------------------------------------------------------------------------
# add_dependencies
# ---------------------------------------------------------------------------


class TestAddDependencies:
    def test_additions_none_and_pip_none_returns_copy(self):
        deps = ["numpy"]
        result = add_dependencies(deps, None, None)
        assert result == ["numpy"]
        assert result is not deps

    def test_additions_only(self):
        deps = ["numpy"]
        result = add_dependencies(deps, ["scipy", "requests"], None)
        assert result == ["numpy", "scipy", "requests"]

    def test_empty_additions_list_no_effect(self):
        deps = ["numpy"]
        result = add_dependencies(deps, [], None)
        assert result == ["numpy"]

    def test_pip_requirements_moves_matching_deps_into_pip_block(self):
        deps = ["numpy", "some-pip-only-pkg==1.0"]
        result = add_dependencies(deps, None, ["some-pip-only-pkg"])

        # non-pip deps remain, "pip" is added, and a dict block is appended
        assert "numpy" in result
        assert "pip" in result
        pip_block = result[-1]
        assert isinstance(pip_block, dict)
        assert pip_block == {"pip": ["some-pip-only-pkg==1.0"]}

    def test_pip_requirements_no_matches(self):
        deps = ["numpy"]
        result = add_dependencies(deps, None, ["nonexistent-pkg"])
        assert "pip" in result
        assert result[-1] == {"pip": ["nonexistent-pkg"]}

    def test_pip_already_in_deps_not_duplicated(self):
        deps = ["numpy", "pip", "requests-pip-pkg"]
        result = add_dependencies(deps, None, ["requests-pip-pkg"])
        assert result.count("pip") == 1

    def test_pip_requirements_sorted_in_block(self):
        deps = ["zeta-pip==1.0", "alpha-pip==2.0"]
        result = add_dependencies(deps, None, ["pip"])
        pip_block = result[-1]
        assert pip_block["pip"] == sorted(pip_block["pip"])

    def test_additions_and_pip_requirements_together(self):
        deps = ["numpy"]
        result = add_dependencies(deps, ["scipy"], ["scipy"])
        # scipy was added then moved into the pip block
        assert "scipy" not in [dep for dep in result if isinstance(dep, str)]
        assert "pip" in result
        pip_block = result[-1]
        assert pip_block == {"pip": ["scipy"]}

    def test_does_not_mutate_input(self):
        deps = ["numpy"]
        add_dependencies(deps, ["scipy"], None)
        assert deps == ["numpy"]


# ---------------------------------------------------------------------------
# write_environment_file
# ---------------------------------------------------------------------------


class TestWriteEnvironmentFile:
    @pytest.mark.parametrize("path", [Path, str])
    def test_writes_expected_yaml_structure(self, tmp_path, path):
        output_path = tmp_path / "environment.yaml"
        deps = ["numpy", {"pip": ["some-pkg"]}]

        write_environment_file(deps, path(output_path), "myenv", ["conda-forge"])

        raw_content = output_path.read_text()
        assert "DO NOT MODIFY" in raw_content
        assert f"This file was automatically generated by {PROJECT_NAME}"
        parsed = yaml.safe_load(raw_content)

        assert parsed["name"] == "myenv"
        assert parsed["channels"] == ["conda-forge"]
        assert parsed["dependencies"] == deps

    def test_overwrites_existing_file(self, tmp_path):
        output_path = tmp_path / "environment.yaml"
        output_path.write_text("old content")

        write_environment_file(["numpy"], output_path, "myenv", ["conda-forge"])

        content = output_path.read_text()
        assert "old content" not in content
        assert "myenv" in content

    def test_empty_dependencies_list(self, tmp_path):
        output_path = tmp_path / "environment.yaml"
        write_environment_file([], output_path, "myenv", [])

        raw_content = output_path.read_text()
        yaml_body = "\n".join(
            line for line in raw_content.splitlines() if not line.startswith("#")
        )
        parsed = yaml.safe_load(yaml_body)
        assert parsed["dependencies"] == []
        assert parsed["channels"] == []
