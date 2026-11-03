import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch


def test_normalize_key_path_existing_direct(tmp_path):
    """Test when key file exists directly at given path."""
    from app.config import normalize_key_path

    key_file = tmp_path / "my_key.pem"
    key_file.write_text("DUMMY_KEY_CONTENT")

    resolved = normalize_key_path(str(key_file))
    assert resolved == str(key_file)
    assert Path(resolved).exists()


def test_normalize_key_path_with_tilde_expansion(tmp_path, monkeypatch):
    """Test tilde expansion in path."""
    from app.config import normalize_key_path

    monkeypatch.setenv("HOME", str(tmp_path))
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()
    key_file = ssh_dir / "oci_key.pem"
    key_file.write_text("DUMMY_KEY")

    resolved = normalize_key_path("~/.ssh/oci_key.pem")
    assert resolved == str(key_file)
    assert Path(resolved).exists()


def test_normalize_key_path_fallback_to_root_ssh(tmp_path, monkeypatch):
    """
    Test when host path (e.g. /home/user/.ssh/my_key.pem) doesn't exist,
    but the file is available in /root/.ssh/my_key.pem (container mount).
    """
    from app.config import normalize_key_path

    # Simulate container /root directory inside tmp_path
    mock_root = tmp_path / "root"
    mock_ssh = mock_root / ".ssh"
    mock_ssh.mkdir(parents=True)
    mounted_key = mock_ssh / "my_key.pem"
    mounted_key.write_text("DUMMY_KEY")

    with patch("app.config.FALLBACK_DIRS", [str(mock_ssh)]):
        resolved = normalize_key_path("/home/someuser/.ssh/my_key.pem")
        assert resolved == str(mounted_key)


def test_normalize_key_path_fallback_to_root_oci(tmp_path):
    """
    Test when host path doesn't exist, but basename is inside /root/.oci/
    """
    from app.config import normalize_key_path

    mock_oci = tmp_path / "root" / ".oci"
    mock_oci.mkdir(parents=True)
    mounted_key = mock_oci / "dev_key.pem"
    mounted_key.write_text("DUMMY_KEY")

    with patch("app.config.FALLBACK_DIRS", [str(mock_oci)]):
        resolved = normalize_key_path("/Users/dev/keys/dev_key.pem")
        assert resolved == str(mounted_key)


def test_normalize_key_path_not_found_raises():
    """Test that FileNotFoundError is raised with helpful message when key is not found."""
    from app.config import normalize_key_path

    with pytest.raises(FileNotFoundError) as exc_info:
        normalize_key_path("/non/existent/path/missing_key.pem")
    assert "missing_key.pem" in str(exc_info.value)
