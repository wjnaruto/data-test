import types

import pytest

from services.smb_service import SmbService


@pytest.fixture
def svc(monkeypatch) -> SmbService:
    # Avoid touching real SMB client config in unit tests.
    monkeypatch.setattr("services.smb_service.smbclient.ClientConfig", lambda *_args, **_kwargs: None)
    return SmbService(
        src_root="\\\\server\\share\\source",
        src_user="u",
        src_pwd="p",
        archive_root="\\\\server\\share\\archive",
    )


@pytest.fixture
def no_thread_and_no_sleep(monkeypatch):
    async def _to_thread(func, /, *args, **kwargs):
        return func(*args, **kwargs)

    async def _sleep(_s):
        return None

    monkeypatch.setattr("services.smb_service.asyncio.to_thread", _to_thread)
    monkeypatch.setattr("services.smb_service.asyncio.sleep", _sleep)


@pytest.mark.asyncio
async def test_is_stable_returns_false_when_stat_fails(svc, no_thread_and_no_sleep, monkeypatch):
    def _raise(_path):
        raise RuntimeError("stat failed")

    monkeypatch.setattr("services.smb_service.smbclient.stat", _raise)
    assert await svc.is_stable("\\\\server\\share\\source\\a.txt") is False


@pytest.mark.asyncio
async def test_is_stable_returns_false_when_stat_missing_size_or_times(svc, no_thread_and_no_sleep, monkeypatch):
    st = types.SimpleNamespace(st_size=None, st_mtime=None, st_chgtime=None)
    monkeypatch.setattr("services.smb_service.smbclient.stat", lambda _path: st)
    assert await svc.is_stable("\\\\server\\share\\source\\a.txt") is False


@pytest.mark.asyncio
async def test_is_stable_min_age_mode_true_when_old_enough(svc, no_thread_and_no_sleep, monkeypatch):
    # last change=100, now=105, min_age_s=3 => stable.
    st = types.SimpleNamespace(st_size=123, st_mtime=100.0, st_chgtime=100.0)
    monkeypatch.setattr("services.smb_service.smbclient.stat", lambda _path: st)
    monkeypatch.setattr("services.smb_service.time.time", lambda: 105.0)
    assert await svc.is_stable("\\\\server\\share\\source\\a.txt", min_age_s=3.0) is True


@pytest.mark.asyncio
async def test_is_stable_min_age_mode_false_when_too_new(svc, no_thread_and_no_sleep, monkeypatch):
    # last change=100, now=102, min_age_s=3 => unstable.
    st = types.SimpleNamespace(st_size=123, st_mtime=100.0, st_chgtime=100.0)
    monkeypatch.setattr("services.smb_service.smbclient.stat", lambda _path: st)
    monkeypatch.setattr("services.smb_service.time.time", lambda: 102.0)
    assert await svc.is_stable("\\\\server\\share\\source\\a.txt", min_age_s=3.0) is False


@pytest.mark.asyncio
async def test_is_stable_min_age_prefers_latest_of_mtime_and_chgtime(svc, no_thread_and_no_sleep, monkeypatch):
    # If st_mtime is old but st_chgtime is recent, the file is considered "recently changed" => unstable.
    st = types.SimpleNamespace(st_size=123, st_mtime=50.0, st_chgtime=100.0)
    monkeypatch.setattr("services.smb_service.smbclient.stat", lambda _path: st)
    monkeypatch.setattr("services.smb_service.time.time", lambda: 102.0)
    assert await svc.is_stable("\\\\server\\share\\source\\a.txt", min_age_s=3.0) is False


@pytest.mark.asyncio
async def test_is_stable_multi_sample_mode_true_when_unchanged(svc, no_thread_and_no_sleep, monkeypatch):
    monkeypatch.setattr("services.smb_service.settings.SMB_STABILITY_MIN_AGE_S", None)
    seq = [
        types.SimpleNamespace(st_size=10, st_mtime=100.0, st_chgtime=100.0),
        types.SimpleNamespace(st_size=10, st_mtime=100.0, st_chgtime=100.0),
        types.SimpleNamespace(st_size=10, st_mtime=100.0, st_chgtime=100.0),
    ]

    def _stat(_path):
        return seq.pop(0)

    monkeypatch.setattr("services.smb_service.smbclient.stat", _stat)
    assert (
        await svc.is_stable(
            "\\\\server\\share\\source\\a.txt",
            min_age_s=None,
            check_interval_s=0.01,
            check_count=3,
        )
        is True
    )


@pytest.mark.asyncio
async def test_is_stable_multi_sample_mode_false_when_changed(svc, no_thread_and_no_sleep, monkeypatch):
    monkeypatch.setattr("services.smb_service.settings.SMB_STABILITY_MIN_AGE_S", None)
    seq = [
        types.SimpleNamespace(st_size=10, st_mtime=100.0, st_chgtime=100.0),
        types.SimpleNamespace(st_size=11, st_mtime=100.0, st_chgtime=100.0),
    ]

    def _stat(_path):
        return seq.pop(0)

    monkeypatch.setattr("services.smb_service.smbclient.stat", _stat)
    assert (
        await svc.is_stable(
            "\\\\server\\share\\source\\a.txt",
            min_age_s=None,
            check_interval_s=0.01,
            check_count=2,
        )
        is False
    )


@pytest.mark.asyncio
async def test_is_stable_multi_sample_mode_false_when_stat_fails_midway(svc, no_thread_and_no_sleep, monkeypatch):
    monkeypatch.setattr("services.smb_service.settings.SMB_STABILITY_MIN_AGE_S", None)
    calls = {"n": 0}

    def _stat(_path):
        calls["n"] += 1
        if calls["n"] == 1:
            return types.SimpleNamespace(st_size=10, st_mtime=100.0, st_chgtime=100.0)
        raise RuntimeError("stat failed")

    monkeypatch.setattr("services.smb_service.smbclient.stat", _stat)
    assert (
        await svc.is_stable(
            "\\\\server\\share\\source\\a.txt",
            min_age_s=None,
            check_interval_s=0.01,
            check_count=2,
        )
        is False
    )
