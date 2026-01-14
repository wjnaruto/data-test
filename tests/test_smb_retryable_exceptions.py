import errno

from smbprotocol.exceptions import SMBAuthenticationError, SMBConnectionClosed, SMBOSError
from smbprotocol.header import NtStatus

from services.smb_service import _is_retryable_smb_exception


def test_value_error_is_not_retryable():
    assert _is_retryable_smb_exception(ValueError("bad input")) is False


def test_file_not_found_is_not_retryable():
    assert _is_retryable_smb_exception(FileNotFoundError("missing")) is False


def test_timeout_error_is_retryable():
    assert _is_retryable_smb_exception(TimeoutError("timeout")) is True


def test_transient_os_error_is_retryable():
    assert _is_retryable_smb_exception(OSError(errno.ECONNRESET, "connection reset")) is True


def test_non_transient_os_error_is_not_retryable():
    assert _is_retryable_smb_exception(OSError(errno.EINVAL, "invalid")) is False


def test_smb_connection_closed_is_retryable():
    assert _is_retryable_smb_exception(SMBConnectionClosed()) is True


def test_smb_auth_error_is_not_retryable():
    assert _is_retryable_smb_exception(SMBAuthenticationError("bad creds")) is False


def test_smb_os_error_transient_ntstatus_is_retryable():
    e = SMBOSError(NtStatus.STATUS_IO_TIMEOUT, "file")
    assert _is_retryable_smb_exception(e) is True


def test_smb_os_error_permanent_ntstatus_is_not_retryable():
    e = SMBOSError(NtStatus.STATUS_ACCESS_DENIED, "file")
    assert _is_retryable_smb_exception(e) is False

