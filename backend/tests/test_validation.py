from decimal import Decimal

import pytest
from cryptography.fernet import Fernet

from app.schemas.camera import CameraAreaUpdate
from app.schemas.zone import validate_polygon
from app.services.credentials import (
    CredentialError, build_stream_url, decrypt_credentials,
    encrypt_credentials, split_credentials,
)
from app.services.video_source import build_warnings


# ---------- camera area ----------
def test_area_from_length_and_width():
    assert CameraAreaUpdate(area_length_m=20, area_width_m=15).computed_area() == Decimal("300.00")


def test_area_is_rounded_to_two_decimals():
    assert CameraAreaUpdate(area_length_m=12.345, area_width_m=3.333).computed_area() == Decimal("41.15")


def test_area_given_directly():
    assert CameraAreaUpdate(area_sqm=250).computed_area() == Decimal("250.00")


@pytest.mark.parametrize("body", [
    {},
    {"area_length_m": 20},
    {"area_sqm": 0},
    {"area_sqm": -1},
    {"area_length_m": 20, "area_width_m": 15, "area_sqm": 300},
])
def test_invalid_area_is_rejected(body):
    with pytest.raises(ValueError):
        CameraAreaUpdate(**body)


# ---------- zone polygon ----------
def test_valid_polygon_is_accepted():
    assert validate_polygon([[0, 0], [1, 0], [1, 1]]) == [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]]


@pytest.mark.parametrize("points", [
    [[0, 0], [1, 1]],                      # fewer than 3 points
    [[0, 0], [1.5, 0], [1, 1]],            # outside 0..1
    [[0, 0], [-0.1, 0.5], [1, 1]],         # negative
    [[0, 0], [0.5, 0.5], [1, 1]],          # all on one line
    [[0, 0, 1], [1, 0, 1], [1, 1, 1]],     # not [x, y]
])
def test_invalid_polygon_is_rejected(points):
    with pytest.raises(ValueError):
        validate_polygon(points)


# ---------- video source warnings (SRS section 15) ----------
def test_good_source_has_no_warnings():
    assert build_warnings(1280, 720, 30) == []
    assert build_warnings(1920, 1080, 10) == []      # exactly 10 FPS is fine


def test_low_resolution_warns():
    warnings = build_warnings(640, 360, 30)
    assert len(warnings) == 1 and "Resolution" in warnings[0]


def test_low_fps_warns():
    warnings = build_warnings(1280, 720, 5)
    assert len(warnings) == 1 and "Frame rate" in warnings[0]


def test_both_problems_give_two_warnings():
    assert len(build_warnings(640, 360, 5)) == 2


def test_portrait_video_is_not_flagged_by_orientation():
    assert build_warnings(720, 1280, 30) == []


def test_unknown_fps_warns():
    assert build_warnings(1280, 720, None) == ["Frame rate could not be determined"]


# ---------- RTSP credentials ----------
@pytest.fixture
def key(monkeypatch):
    value = Fernet.generate_key().decode()   # a throwaway key, never your real one
    monkeypatch.setenv("CAMERA_CRED_KEY", value)
    return value


def test_split_removes_credentials_from_url():
    clean, creds = split_credentials("rtsp://user:p%40ss@10.0.0.5:554/s1")
    assert clean == "rtsp://10.0.0.5:554/s1"
    assert creds == ("user", "p@ss")


def test_url_without_credentials_is_unchanged():
    assert split_credentials("rtsp://10.0.0.5:554/s1") == ("rtsp://10.0.0.5:554/s1", None)


def test_encrypt_decrypt_round_trip(key):
    token = encrypt_credentials("user", "p@ss:word/1")
    assert "p@ss" not in token
    assert decrypt_credentials(token) == ("user", "p@ss:word/1")


def test_stream_url_is_rebuilt_with_encoding(key):
    token = encrypt_credentials("user", "p@ss")
    assert build_stream_url("rtsp://10.0.0.5:554/s1", token) == "rtsp://user:p%40ss@10.0.0.5:554/s1"
    assert build_stream_url("rtsp://10.0.0.5:554/s1", None) == "rtsp://10.0.0.5:554/s1"


def test_wrong_key_cannot_decrypt(key, monkeypatch):
    token = encrypt_credentials("user", "secret")
    monkeypatch.setenv("CAMERA_CRED_KEY", Fernet.generate_key().decode())
    with pytest.raises(CredentialError):
        decrypt_credentials(token)


def test_missing_key_raises_clear_error(monkeypatch):
    monkeypatch.delenv("CAMERA_CRED_KEY", raising=False)
    with pytest.raises(CredentialError):
        encrypt_credentials("user", "secret")