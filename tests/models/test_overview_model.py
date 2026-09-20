from pathlib import Path
from types import SimpleNamespace

import pytest

from app.models.overview_model import OverviewModel


@pytest.mark.parametrize(
    ("width", "height", "expected"),
    [
        (400, 1600, (400, 1600)),
        (399, 600, (900, 600)),
        (900, 1601, (900, 600)),
        (2000, 2000, (900, 600)),
    ],
)
def test_validate_window_custom_size(width: int, height: int, expected: tuple[int, int]) -> None:
    assert OverviewModel.validate_window_custom_size(width, height) == expected


def test_defaults_and_properties(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "app.models.overview_model.AppInfo", lambda: SimpleNamespace(app_settings_file=tmp_path / "settings.json")
    )
    model = OverviewModel()

    assert model.output_directory == Path()
    assert model.job_number == ""
    model.output_directory = tmp_path
    model.job_number = "JOB-2"
    assert model.output_directory == tmp_path
    assert model.job_number == "JOB-2"
