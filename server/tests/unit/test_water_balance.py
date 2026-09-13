from datetime import date, timedelta

import pytest

from app.services.water.advisory import build_irrigation_advisory
from app.services.water.balance import calculate_paddy_balance
from app.services.water.contracts import DailyWeather, IrrigationDepth, WaterObservation, WaterState
from app.services.water.profiles import CAUVERY_PADDY_V1, PROFILE_METADATA
from app.services.water.irrigation import normalize_irrigation

pytestmark = pytest.mark.unit


def weather(days, rainfall=0.0, et0=4.0, kind="historical"):
    start = date(2025, 6, 1)
    return [DailyWeather(start + timedelta(days=index), rainfall, et0, kind) for index in range(days)]


def test_one_day_balance_closes_and_uses_etc_equals_et0_times_kc():
    result = calculate_paddy_balance(
        weather(1), [], CAUVERY_PADDY_V1, date(2025, 6, 1),
        initial_state=WaterState(0, 25), initial_state_source="measured",
        cycle_start_source="transplanting_date", irrigation_history_complete=True,
    )
    row = result["daily"][0]
    assert row["potential_etc_mm"] == pytest.approx(4.2)
    assert row["seepage_percolation_mm"] == pytest.approx(3.0)
    assert row["ponded_water_mm"] == pytest.approx(17.8)
    assert abs(row["conservation_residual_mm"]) < 1e-6
    assert result["evidence_level"] == "high"


def test_rainfall_and_irrigation_cannot_increase_deficit():
    dry = calculate_paddy_balance(weather(4), [], CAUVERY_PADDY_V1, date(2025, 6, 1))
    wet = calculate_paddy_balance(weather(4, rainfall=5), [], CAUVERY_PADDY_V1, date(2025, 6, 1))
    irrigated = calculate_paddy_balance(
        weather(4), [IrrigationDepth(date(2025, 6, 3), 20)], CAUVERY_PADDY_V1, date(2025, 6, 1)
    )
    assert wet["water_deficit_mm"] <= dry["water_deficit_mm"]
    assert irrigated["water_deficit_mm"] <= dry["water_deficit_mm"]


def test_heavy_rain_is_bounded_by_bund_and_records_runoff():
    result = calculate_paddy_balance(
        weather(1, rainfall=100, et0=0), [], CAUVERY_PADDY_V1, date(2025, 6, 1),
        initial_state=WaterState(0, 25),
    )
    row = result["daily"][0]
    assert row["runoff_mm"] == pytest.approx(75)
    assert row["ponded_water_mm"] == pytest.approx(47)
    assert abs(row["conservation_residual_mm"]) < 1e-6


def test_weather_dates_must_be_consecutive_and_values_nonnegative():
    rows = [DailyWeather(date(2025, 6, 1), 0, 4), DailyWeather(date(2025, 6, 3), 0, 4)]
    with pytest.raises(ValueError, match="consecutive"):
        calculate_paddy_balance(rows, [], CAUVERY_PADDY_V1, date(2025, 6, 1))
    with pytest.raises(ValueError, match="rainfall"):
        calculate_paddy_balance([DailyWeather(date(2025, 6, 1), -1, 4)], [], CAUVERY_PADDY_V1, date(2025, 6, 1))


def test_sensitivity_range_and_missing_irrigation_warning_are_explicit():
    result = calculate_paddy_balance(weather(10), [], CAUVERY_PADDY_V1, date(2025, 6, 1))
    assert result["water_deficit_low_mm"] <= result["water_deficit_mm"] <= result["water_deficit_high_mm"]
    assert result["evidence_level"] == "low"
    assert any("not proof of zero" in warning for warning in result["warnings"])


def test_mm_to_volume_and_efficiency_are_exact():
    balance = {
        "status": "completed", "evidence_level": "high", "warnings": [],
        "daily": [{"date": "2025-06-01", "water_deficit_mm": 10.0, "trigger_crossed": True}],
    }
    forecast = [{"date": f"2025-06-0{day}", "rainfall_mm": 0, "trigger_crossed": True, "water_deficit_mm": 10} for day in range(2, 7)]
    result = build_irrigation_advisory(balance, forecast, field_area_m2=10_000, irrigation_efficiency=0.5)
    assert result["action"] == "irrigate_now"
    assert result["net_depth_mm"] == 10
    assert result["gross_depth_mm"] == 20
    assert result["volume_m3"] == 200


def test_near_term_rain_can_delay_but_never_create_negative_depth():
    balance = {
        "status": "completed", "evidence_level": "medium", "warnings": [],
        "daily": [{"date": "2025-06-01", "water_deficit_mm": 8.0, "trigger_crossed": True}],
    }
    forecast = [{"date": "2025-06-02", "rainfall_mm": 10, "trigger_crossed": False, "water_deficit_mm": 0}]
    result = build_irrigation_advisory(balance, forecast, field_area_m2=1000, irrigation_efficiency=0.6)
    assert result["action"] == "delay_for_rain"
    assert result["gross_depth_mm"] == 0
    assert result["volume_m3"] == 0
    assert result["fallback_net_depth_mm"] == 8
    assert result["fallback_gross_depth_mm"] == pytest.approx(13.333, abs=1e-3)
    assert result["fallback_volume_m3"] == pytest.approx(13.333, abs=1e-3)
    assert result["recommended_timing"] == "recheck_after_forecast_rain"
    assert result["rule_version"] == "paddy-advisory-v2"


def test_one_mm_over_one_hectare_is_exactly_ten_cubic_metres():
    gross, net = normalize_irrigation(10, "m3", 10_000, 0.6)
    assert gross == 1.0
    assert net == 0.6


def test_maturity_does_not_trigger_ordinary_refill():
    cycle_start = date(2025, 6, 1)
    rows = [DailyWeather(cycle_start + timedelta(days=100 + index), 0, 8) for index in range(2)]
    result = calculate_paddy_balance(rows, [], CAUVERY_PADDY_V1, cycle_start, initial_state=WaterState(30, 0))
    assert result["daily"][-1]["stage"].startswith("Maturity")
    assert result["daily"][-1]["trigger_crossed"] is False


def test_missing_forecast_falls_back_to_current_state_monitoring():
    cycle_start = date(2025, 6, 1)
    balance = calculate_paddy_balance(weather(1, et0=0), [], CAUVERY_PADDY_V1, cycle_start)
    result = build_irrigation_advisory(balance, [], field_area_m2=10_000, irrigation_efficiency=0.6)
    assert result["status"] == "completed"
    assert result["action"] == "monitor"
    assert any("current deficit only" in item for item in result["warnings"])


def test_runtime_profile_is_loaded_from_versioned_visible_resource():
    assert CAUVERY_PADDY_V1.version == PROFILE_METADATA["version"] == "cauvery-paddy-v1"
    assert CAUVERY_PADDY_V1.seepage_percolation_mm_day == PROFILE_METADATA["parameters"]["seepage_percolation_mm_day"]["value"]
    assert PROFILE_METADATA["sources"]


def test_fao56_stress_coefficient_reduces_actual_etc_after_raw():
    cycle_start = date(2025, 6, 1)
    result = calculate_paddy_balance(
        [DailyWeather(cycle_start, 0, 10)], [], CAUVERY_PADDY_V1, cycle_start,
        initial_state=WaterState(80, 0), initial_state_source="measured",
        cycle_start_source="transplanting_date", irrigation_history_complete=True,
    )
    row = result["daily"][0]
    expected_ks = (100 - 80) / ((1 - row["depletion_fraction"]) * 100)
    assert row["stress_coefficient"] == pytest.approx(expected_ks, abs=1e-6)
    assert row["actual_etc_mm"] < row["potential_etc_mm"]
    assert row["unmet_etc_mm"] > 0
    assert abs(row["conservation_residual_mm"]) < 1e-6
    assert result["rule_version"] == "paddy-daily-v2"


def test_measured_ponding_is_assimilated_as_an_explicit_balanced_adjustment():
    cycle_start = date(2025, 6, 1)
    observation = WaterObservation(cycle_start, "ponded_depth", 30, reliability="high")
    result = calculate_paddy_balance(
        weather(1, et0=0), [], CAUVERY_PADDY_V1, cycle_start,
        initial_state=WaterState(0, 10), irrigation_history_complete=True,
        water_observations=[observation],
    )
    row = result["daily"][0]
    assert row["ponded_water_mm"] == 30
    assert row["state_adjustment_mm"] == 23
    assert row["assimilated_observation_types"] == ["ponded_depth"]
    assert abs(row["conservation_residual_mm"]) < 1e-6
    assert result["evidence_level"] == "high"


def test_validation_replay_can_disable_observation_assimilation():
    cycle_start = date(2025, 6, 1)
    observation = WaterObservation(cycle_start, "ponded_depth", 30, reliability="high")
    result = calculate_paddy_balance(
        weather(1, et0=0), [], CAUVERY_PADDY_V1, cycle_start,
        initial_state=WaterState(0, 10), water_observations=[observation], assimilate_observations=False,
    )
    assert result["daily"][0]["ponded_water_mm"] == 7
    assert result["daily"][0]["state_adjustment_mm"] == 0
    assert result["assumptions"]["assimilation_enabled"] is False
