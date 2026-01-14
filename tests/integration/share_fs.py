import os
import time
from dataclasses import dataclass
from pathlib import PureWindowsPath
from typing import Callable, Optional

import smbclient
from smbclient import ClientConfig
from smbprotocol.exceptions import SMBOSError


def _join_unc(root_unc: str, *parts: str) -> str:
    p = PureWindowsPath(root_unc)
    for part in parts:
        part = part.replace("/", "\\")
        p = p / part
    return str(p)


@dataclass(frozen=True)
class SMBShareFS:
    source_root_unc: str
    archive_root_unc: str
    username: str
    password: str

    def __post_init__(self):
        ClientConfig(username=self.username, password=self.password)

    def src(self, rel_path: str) -> str:
        return _join_unc(self.source_root_unc, rel_path)

    def arc(self, filename: str) -> str:
        return _join_unc(self.archive_root_unc, filename)

    def archived_from_src_unc(self, src_abs_unc: str) -> str:
        rel = os.path.relpath(src_abs_unc, self.source_root_unc)
        if rel.startswith(".."):
            rel = os.path.basename(src_abs_unc)
        return _join_unc(self.archive_root_unc, rel)

    def write(self, rel_path: str, content: bytes):
        unc = self.src(rel_path)
        parent = str(PureWindowsPath(unc).parent)
        smbclient.makedirs(parent, exist_ok=True)
        with smbclient.open_file(unc, mode="wb") as f:
            f.write(content)

    def write_slow(self, rel_path: str, content: bytes, chunk_size: int = 256 * 1024, sleep_s: float = 0.5):
        unc = self.src(rel_path)
        parent = str(PureWindowsPath(unc).parent)
        smbclient.makedirs(parent, exist_ok=True)
        with smbclient.open_file(unc, mode="wb") as f:
            i = 0
            while i < len(content):
                f.write(content[i:i + chunk_size])
                f.flush()
                i += chunk_size
                time.sleep(sleep_s)

    def exists_source(self, rel_path: str) -> bool:
        try:
            smbclient.stat(self.src(rel_path))
            return True
        except (FileNotFoundError, SMBOSError):
            return False

    def exists_archive(self, filename: str) -> bool:
        try:
            smbclient.stat(self.arc(filename))
            return True
        except (FileNotFoundError, SMBOSError):
            return False

    def exists_archived_from_source(self, rel_path: str) -> bool:
        """
        Check if the archived destination (computed from source rel_path) exists.
        """
        src = self.src(rel_path)
        dst = self.archived_from_src_unc(src)
        try:
            smbclient.stat(dst)
            return True
        except (FileNotFoundError, SMBOSError):
            return False

    def remove_archived_from_source_if_exists(self, rel_path: str):
        """
        Remove the archived destination (computed from source rel_path) if it exists.
        """
        src = self.src(rel_path)
        dst = self.archived_from_src_unc(src)
        try:
            smbclient.remove(dst)
        except FileNotFoundError:
            pass
        except SMBOSError:
            pass

    def remove_source_if_exists(self, rel_path: str):
        p = self.src(rel_path)
        try:
            smbclient.remove(p)
        except (FileNotFoundError, SMBOSError):
            pass

    def remove_archive_if_exists(self, filename: str):
        p = self.arc(filename)
        try:
            smbclient.remove(p)
        except (FileNotFoundError, SMBOSError):
            pass

    def _cleanup_empty_parents(self, start_dir_unc: str, stop_root_unc: str) -> None:
        start = str(PureWindowsPath(start_dir_unc))
        stop = str(PureWindowsPath(stop_root_unc))
        start_l = start.rstrip("\\/").lower()
        stop_l = stop.rstrip("\\/").lower()
        if not start_l.startswith(stop_l):
            return

        cur = PureWindowsPath(start)
        root = PureWindowsPath(stop)

        while True:
            if str(cur).rstrip("\\/").lower() == stop_l:
                return
            if not str(cur).rstrip("\\/").lower().startswith(stop_l):
                return
            try:
                smbclient.rmdir(str(cur))
            except Exception:
                return
            cur = cur.parent

    def cleanup_empty_dirs_for_rel_path(self, rel_path: str) -> None:
        """
        Best-effort removal of empty folders created/left behind by the test.
        Only removes directories under source_root_unc/archive_root_unc and never removes the roots.
        """
        src_abs = self.src(rel_path)
        src_parent = str(PureWindowsPath(src_abs).parent)
        self._cleanup_empty_parents(src_parent, self.source_root_unc)

        dst_abs = self.archived_from_src_unc(src_abs)
        dst_parent = str(PureWindowsPath(dst_abs).parent)
        self._cleanup_empty_parents(dst_parent, self.archive_root_unc)

    def list_archive(self):
        return smbclient.listdir(self.archive_root_unc)

    def wait_moved_to_archive(self, rel_path: str, timeout_s: float = 90.0, require_source_gone: bool = False):
        filename = rel_path.split("/")[-1]
        src = self.src(rel_path)
        arc = self.archived_from_src_unc(src)

        deadline = time.time() + timeout_s
        last_src = None
        last_dst = None

        while time.time() < deadline:
            try:
                smbclient.stat(src)
                src_exists = True
            except (FileNotFoundError, SMBOSError):
                src_exists = False
            except Exception as e:
                last_src = e
                src_exists = True

            try:
                smbclient.stat(arc)
                dst_exists = True
            except (FileNotFoundError, SMBOSError):
                dst_exists = False
            except Exception as e:
                last_dst = e
                dst_exists = False

            if (not src_exists) and dst_exists:
                return arc

            time.sleep(1.0)

        raise AssertionError(
            f"File not archived within {timeout_s}s\n"
            f" source={src} exists={self.exists_source(rel_path)}\n"
            f" archive={arc} exists={self.exists_archive(filename)}\n"
            f" archive_root={self.archive_root_unc}\n"
        )


def build_share_fs_from_env() -> SMBShareFS:
    return SMBShareFS(
        source_root_unc=os.environ["SMB_UNC_PATH"],
        archive_root_unc=os.environ["SMB_ARCHIVE_SUBPATH"],
        username=os.environ["IT_SMB_USERNAME"],
        password=os.environ["IT_SMB_PASSWORD"],
    )


class RecordingShareFS:
    """
    A thin wrapper around SMBShareFS that records written rel_paths for cleanup.
    """

    def __init__(self, inner: SMBShareFS, *, on_write: Optional[Callable[[str], None]] = None):
        self._inner = inner
        self._written: list[str] = []
        self._on_write = on_write

    @property
    def written_rel_paths(self) -> list[str]:
        return list(dict.fromkeys(self._written))

    def record(self, rel_path: str) -> None:
        if rel_path:
            self._written.append(rel_path)
            if self._on_write is not None:
                self._on_write(rel_path)

    def write(self, rel_path: str, content: bytes):
        self.record(rel_path)
        return self._inner.write(rel_path, content)

    def write_slow(self, rel_path: str, content: bytes, chunk_size: int = 256 * 1024, sleep_s: float = 0.5):
        self.record(rel_path)
        return self._inner.write_slow(rel_path, content, chunk_size=chunk_size, sleep_s=sleep_s)

    def cleanup_written(self) -> None:
        failures: list[str] = []
        for rel_path in self.written_rel_paths:
            # Best-effort retry: SMB rename/close can be eventually consistent.
            for _ in range(3):
                try:
                    self._inner.remove_source_if_exists(rel_path)
                except Exception:
                    pass
                try:
                    self._inner.remove_archived_from_source_if_exists(rel_path)
                except Exception:
                    pass

                if (not self._inner.exists_source(rel_path)) and (not self._inner.exists_archived_from_source(rel_path)):
                    break
                time.sleep(0.5)

            if self._inner.exists_source(rel_path) or self._inner.exists_archived_from_source(rel_path):
                failures.append(rel_path)

            try:
                self._inner.cleanup_empty_dirs_for_rel_path(rel_path)
            except Exception:
                pass

        if failures:
            print(f"[IT] cleanup could not remove {len(failures)} file(s): {failures}")

    def __getattr__(self, item):
        return getattr(self._inner, item)
