import os
from datetime import datetime

import pytest

from rompy.templating import (
    TemplateContext,
    TemplateError,
    apply_filter,
    apply_filters,
    parse_datetime,
    render_string,
    render_templates,
    shift_datetime,
)


class TestTemplateContext:
    def test_get_from_context(self):
        ctx = TemplateContext({"USER": "john", "HOME": "/home/john"})
        assert ctx.get("USER") == "john"
        assert ctx.get("HOME") == "/home/john"

    def test_get_with_default(self):
        ctx = TemplateContext({})
        assert ctx.get("MISSING", "default_value") == "default_value"

    def test_get_missing_strict(self):
        ctx = TemplateContext({})
        with pytest.raises(TemplateError, match="Variable.*not found"):
            ctx.get("MISSING")

    def test_set_variable(self):
        ctx = TemplateContext({})
        ctx.set("NEW_VAR", "new_value")
        assert ctx.get("NEW_VAR") == "new_value"

    def test_defaults_to_environ(self):
        ctx = TemplateContext()
        assert isinstance(ctx.context, dict)


class TestParseDatetime:
    def test_parse_iso_datetime(self):
        dt = parse_datetime("2023-01-01T12:00:00")
        assert dt == datetime(2023, 1, 1, 12, 0, 0)

    def test_parse_iso_date(self):
        dt = parse_datetime("2023-01-01")
        assert dt == datetime(2023, 1, 1)

    def test_parse_with_microseconds(self):
        dt = parse_datetime("2023-01-01T12:00:00.123456")
        assert dt == datetime(2023, 1, 1, 12, 0, 0, 123456)

    def test_parse_with_custom_format(self):
        dt = parse_datetime("01/15/2023", fmt="%m/%d/%Y")
        assert dt == datetime(2023, 1, 15)

    def test_parse_invalid_format(self):
        with pytest.raises(TemplateError, match="Cannot parse.*datetime"):
            parse_datetime("not-a-date")

    def test_parse_already_datetime(self):
        original = datetime(2023, 1, 1)
        result = parse_datetime(original)
        assert result == original


class TestShiftDatetime:
    def test_shift_days_positive(self):
        dt = datetime(2023, 1, 1)
        shifted = shift_datetime(dt, "+1d")
        assert shifted == datetime(2023, 1, 2)

    def test_shift_days_negative(self):
        dt = datetime(2023, 1, 1)
        shifted = shift_datetime(dt, "-1d")
        assert shifted == datetime(2022, 12, 31)

    def test_shift_hours(self):
        dt = datetime(2023, 1, 1, 12, 0)
        shifted = shift_datetime(dt, "+6h")
        assert shifted == datetime(2023, 1, 1, 18, 0)

    def test_shift_minutes(self):
        dt = datetime(2023, 1, 1, 12, 0)
        shifted = shift_datetime(dt, "+30m")
        assert shifted == datetime(2023, 1, 1, 12, 30)

    def test_shift_seconds(self):
        dt = datetime(2023, 1, 1, 12, 0, 0)
        shifted = shift_datetime(dt, "+90s")
        assert shifted == datetime(2023, 1, 1, 12, 1, 30)

    def test_shift_no_sign(self):
        dt = datetime(2023, 1, 1)
        shifted = shift_datetime(dt, "1d")
        assert shifted == datetime(2023, 1, 2)

    def test_shift_invalid_format(self):
        dt = datetime(2023, 1, 1)
        with pytest.raises(TemplateError, match="Invalid shift format"):
            shift_datetime(dt, "bad")

    def test_shift_invalid_unit(self):
        dt = datetime(2023, 1, 1)
        with pytest.raises(TemplateError, match="Invalid shift format"):
            shift_datetime(dt, "1x")


class TestApplyFilter:
    def test_as_datetime_filter(self):
        result = apply_filter("2023-01-01T12:00:00", "as_datetime")
        assert result == datetime(2023, 1, 1, 12, 0, 0)

    def test_as_datetime_with_format(self):
        result = apply_filter("01/15/2023", "as_datetime:%m/%d/%Y")
        assert result == datetime(2023, 1, 15)

    def test_strftime_filter(self):
        dt = datetime(2023, 1, 15, 12, 30)
        result = apply_filter(dt, "strftime:%Y%m%d")
        assert result == "20230115"

    def test_strftime_parses_string(self):
        result = apply_filter("2023-01-15", "strftime:%Y%m%d")
        assert result == "20230115"

    def test_strftime_missing_arg(self):
        with pytest.raises(TemplateError, match="requires format argument"):
            apply_filter(datetime(2023, 1, 1), "strftime")

    def test_shift_filter(self):
        dt = datetime(2023, 1, 1)
        result = apply_filter(dt, "shift:-1d")
        assert result == datetime(2022, 12, 31)

    def test_shift_parses_string(self):
        result = apply_filter("2023-01-01", "shift:+1d")
        assert result == datetime(2023, 1, 2)

    def test_shift_missing_arg(self):
        with pytest.raises(TemplateError, match="requires delta argument"):
            apply_filter(datetime(2023, 1, 1), "shift")

    def test_unknown_filter(self):
        with pytest.raises(TemplateError, match="Unknown filter"):
            apply_filter("value", "unknown_filter")


class TestApplyFilters:
    def test_filter_chain(self):
        result = apply_filters("2023-01-01", "as_datetime|shift:-1d|strftime:%Y%m%d")
        assert result == "20221231"

    def test_single_filter(self):
        result = apply_filters("2023-01-01", "as_datetime")
        assert result == datetime(2023, 1, 1)

    def test_empty_filter(self):
        result = apply_filters("value", "")
        assert result == "value"


class TestRenderString:
    def test_simple_substitution(self):
        ctx = TemplateContext({"USER": "john"})
        result = render_string("Hello ${USER}", ctx)
        assert result == "Hello john"

    def test_multiple_substitutions(self):
        ctx = TemplateContext({"USER": "john", "HOME": "/home/john"})
        result = render_string("${USER} lives in ${HOME}", ctx)
        assert result == "john lives in /home/john"

    def test_exact_match_preserves_type_int(self):
        ctx = TemplateContext({"TIMEOUT": "3600"})
        result = render_string("${TIMEOUT}", ctx)
        assert result == 3600
        assert isinstance(result, int)

    def test_exact_match_preserves_type_bool_true(self):
        ctx = TemplateContext({"DEBUG": "true"})
        result = render_string("${DEBUG}", ctx)
        assert result is True

    def test_exact_match_preserves_type_bool_false(self):
        ctx = TemplateContext({"DEBUG": "false"})
        result = render_string("${DEBUG}", ctx)
        assert result is False

    def test_exact_match_preserves_type_float(self):
        ctx = TemplateContext({"PI": "3.14"})
        result = render_string("${PI}", ctx)
        assert result == 3.14
        assert isinstance(result, float)

    def test_embedded_always_string(self):
        ctx = TemplateContext({"NUM": "42"})
        result = render_string("value_${NUM}", ctx)
        assert result == "value_42"
        assert isinstance(result, str)

    def test_default_value(self):
        ctx = TemplateContext({})
        result = render_string("${MISSING:-default}", ctx)
        assert result == "default"

    def test_filter_in_exact_match(self):
        ctx = TemplateContext({"CYCLE": "2023-01-01"})
        result = render_string("${CYCLE|as_datetime}", ctx)
        assert result == datetime(2023, 1, 1)

    def test_filter_chain_in_exact_match(self):
        ctx = TemplateContext({"CYCLE": "2023-01-01"})
        result = render_string("${CYCLE|as_datetime|shift:-1d|strftime:%Y%m%d}", ctx)
        assert result == "20221231"

    def test_filter_in_embedded(self):
        ctx = TemplateContext({"CYCLE": "2023-01-01T12:00:00"})
        result = render_string("wind_${CYCLE|strftime:%Y%m%d}.nc", ctx)
        assert result == "wind_20230101.nc"

    def test_missing_variable_strict(self):
        ctx = TemplateContext({})
        with pytest.raises(TemplateError, match="not found"):
            render_string("${MISSING}", ctx, strict=True)

    def test_missing_variable_non_strict(self):
        ctx = TemplateContext({})
        result = render_string("${MISSING}", ctx, strict=False)
        assert result == "${MISSING}"

    def test_filter_error_strict(self):
        ctx = TemplateContext({"VAR": "value"})
        with pytest.raises(TemplateError, match="Filter error"):
            render_string("${VAR|unknown_filter}", ctx, strict=True)

    def test_filter_error_non_strict(self):
        ctx = TemplateContext({"VAR": "value"})
        result = render_string("${VAR|unknown_filter}", ctx, strict=False)
        assert result == "${VAR|unknown_filter}"


class TestRenderTemplates:
    def test_render_dict(self):
        data = {"user": "${USER}", "home": "${HOME}"}
        result = render_templates(data, {"USER": "john", "HOME": "/home/john"})
        assert result == {"user": "john", "home": "/home/john"}

    def test_render_nested_dict(self):
        data = {"outer": {"inner": "${VAR}"}}
        result = render_templates(data, {"VAR": "value"})
        assert result == {"outer": {"inner": "value"}}

    def test_render_list(self):
        data = ["${VAR1}", "${VAR2}"]
        result = render_templates(data, {"VAR1": "a", "VAR2": "b"})
        assert result == ["a", "b"]

    def test_render_mixed_structure(self):
        data = {
            "files": ["${DIR}/file1", "${DIR}/file2"],
            "config": {"timeout": "${TIMEOUT}"},
        }
        result = render_templates(data, {"DIR": "/data", "TIMEOUT": "3600"})
        assert result == {
            "files": ["/data/file1", "/data/file2"],
            "config": {"timeout": 3600},
        }

    def test_primitives_pass_through(self):
        data = {"int": 42, "float": 3.14, "bool": True, "none": None}
        result = render_templates(data, {})
        assert result == data

    def test_no_templates(self):
        data = {"key": "value", "number": 42}
        result = render_templates(data, {})
        assert result == data

    def test_defaults_to_environ(self):
        os.environ["TEST_VAR"] = "test_value"
        try:
            data = {"var": "${TEST_VAR}"}
            result = render_templates(data)
            assert result == {"var": "test_value"}
        finally:
            del os.environ["TEST_VAR"]

    def test_datetime_filters_in_config(self):
        data = {
            "run_id": "cycle_${CYCLE|strftime:%Y%m%d}",
            "start": "${CYCLE|as_datetime}",
            "end": "${CYCLE|as_datetime|shift:+1d}",
        }
        result = render_templates(data, {"CYCLE": "2023-01-01T00:00:00"})
        assert result == {
            "run_id": "cycle_20230101",
            "start": datetime(2023, 1, 1),
            "end": datetime(2023, 1, 2),
        }

    def test_realistic_config(self):
        data = {
            "run_id": "cycle_${CYCLE|strftime:%Y%m%d}",
            "period": {
                "start": "${CYCLE}",
                "end": "${CYCLE|as_datetime|shift:+1d}",
                "interval": "1H",
            },
            "output_dir": "${OUTPUT_ROOT:-./output}/cycle_${CYCLE|strftime:%Y%m%d}",
            "input_files": {
                "wind": "${DATA_ROOT}/wind/wind_${CYCLE|strftime:%Y%m%d}.nc",
                "wave": "${DATA_ROOT}/wave/wave_${CYCLE|strftime:%Y%m%d}.nc",
            },
        }
        context = {
            "CYCLE": "2023-01-01T00:00:00",
            "DATA_ROOT": "/scratch/data",
        }
        result = render_templates(data, context)
        assert result["run_id"] == "cycle_20230101"
        assert result["period"]["start"] == "2023-01-01T00:00:00"
        assert result["period"]["end"] == datetime(2023, 1, 2)
        assert result["output_dir"] == "./output/cycle_20230101"
        assert result["input_files"]["wind"] == "/scratch/data/wind/wind_20230101.nc"

    def test_render_dict_keys(self):
        data = {"prefix_${VAR}": "value"}
        result = render_templates(data, {"VAR": "key"})
        assert result == {"prefix_key": "value"}

    def test_strict_mode_raises(self):
        data = {"key": "${MISSING}"}
        with pytest.raises(TemplateError, match="not found"):
            render_templates(data, {}, strict=True)

    def test_non_strict_keeps_unresolved(self):
        data = {"key": "${MISSING}"}
        result = render_templates(data, {}, strict=False)
        assert result == {"key": "${MISSING}"}


class TestEdgeCases:
    def test_empty_dict(self):
        result = render_templates({}, {})
        assert result == {}

    def test_empty_list(self):
        result = render_templates([], {})
        assert result == []

    def test_empty_string(self):
        result = render_templates("", {})
        assert result == ""

    def test_nested_empty_structures(self):
        data = {"empty_dict": {}, "empty_list": [], "empty_str": ""}
        result = render_templates(data, {})
        assert result == data

    def test_special_characters_in_values(self):
        ctx = TemplateContext({"VAR": "value/with/slashes"})
        result = render_string("${VAR}", ctx)
        assert result == "value/with/slashes"

    def test_default_with_special_chars(self):
        ctx = TemplateContext({})
        result = render_string("${MISSING:-/default/path}", ctx)
        assert result == "/default/path"

    def test_unicode_in_values(self):
        ctx = TemplateContext({"VAR": "unicode_日本語"})
        result = render_string("${VAR}", ctx)
        assert result == "unicode_日本語"

    def test_bool_strings_case_insensitive(self):
        for val in ["true", "True", "TRUE", "yes", "Yes", "YES"]:
            ctx = TemplateContext({"BOOL": val})
            assert render_string("${BOOL}", ctx) is True

        for val in ["false", "False", "FALSE", "no", "No", "NO"]:
            ctx = TemplateContext({"BOOL": val})
            assert render_string("${BOOL}", ctx) is False


class TestIntegration:
    def test_rompy_use_case_wind_input(self):
        ctx = TemplateContext({"CYCLE": "2023-01-15T00:00:00"})
        result = render_string("/path/to/wind_input_${CYCLE|strftime:%Y%m%d}.nc", ctx)
        assert result == "/path/to/wind_input_20230115.nc"

    def test_rompy_use_case_lookback(self):
        ctx = TemplateContext({"CYCLE": "2023-01-15T00:00:00"})
        result = render_string("${CYCLE|as_datetime|shift:-1d|strftime:%Y-%m-%d}", ctx)
        assert result == "2023-01-14"

    def test_backend_config_with_env_vars(self):
        data = {
            "type": "local",
            "timeout": "${TIMEOUT:-3600}",
            "command": "python run.py",
            "env_vars": {
                "OMP_NUM_THREADS": "${NUM_THREADS:-4}",
                "DATA_DIR": "${DATA_ROOT}/inputs",
            },
        }
        context = {"DATA_ROOT": "/scratch"}
        result = render_templates(data, context)
        assert result["timeout"] == 3600
        assert result["env_vars"]["OMP_NUM_THREADS"] == 4
        assert result["env_vars"]["DATA_DIR"] == "/scratch/inputs"
