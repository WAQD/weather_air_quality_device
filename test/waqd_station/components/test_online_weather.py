import json
from pathlib import Path
from freezegun import freeze_time

from waqd.components.weather import OpenMeteo, OpenTopoData


class MockOpenMeteo(OpenMeteo):
    daily_test_json = Path()
    hourly_test_json = Path()

    def _call_api(self, command: str, **kwargs):
        if "&hourly" in command:
            with open(self.hourly_test_json) as fp:
                return json.load(fp)
        elif "&daily" in command:
            with open(self.daily_test_json) as fp:
                return json.load(fp)
        return {}


def test_open_meteo_geocoder(base_fixture, mocker):
    test_json: Path = base_fixture.testdata_path / "online_weather/om_search_berlin.json"
    om = OpenMeteo()
    mock_call = mocker.Mock()
    mock_call.return_value = json.loads(test_json.read_text())
    mocker.patch("waqd.components.weather.open_meteo.OpenMeteo._call_api", mock_call)
    ret = om.find_location_candidates("Berlin", "de")
    assert len(ret) == 10
    assert ret[0].name == "Berlin"
    assert ret[0].country == "Deutschland"
    assert ret[0].state == "Berlin"
    assert ret[0].county == ""
    assert ret[0].altitude == 74
    assert ret[0].longitude == 13.41053
    assert ret[0].latitude == 52.52437


def test_open_meteo(base_fixture, mocker):
    daily_test_json: Path = (
        base_fixture.testdata_path / "online_weather/om_current_weather.json"
    )
    hourly_test_json: Path = (
        base_fixture.testdata_path / "online_weather/om_hourly_weather.json"
    )
    with freeze_time("2023-01-02 22:00:00"):
        om = MockOpenMeteo(13.41053, 52.52437)
        om.daily_test_json = daily_test_json
        om.hourly_test_json = hourly_test_json
        ret = om.get_current_weather()
        assert ret
        ret = om.get_7_day_forecast()
        assert ret
        assert len(ret) == 7


def test_open_topo():
    op = OpenTopoData()
    alt = op.get_altitude(48.2085, 12.3989)
    assert alt > 439 and alt < 440
    op._altitude_info["elevation"] = 0
    alt = op.get_altitude(48.2085, 12.3989)
    assert alt == 0
