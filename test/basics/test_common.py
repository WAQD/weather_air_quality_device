import os

from waqd_installer.common import assure_file_exists, assure_file_does_not_exist


def test_assure_file_exists_creates_file_without_chown_when_dir_writable(tmp_path, mocker):
    os_system = mocker.patch("waqd_installer.common.os.system")
    target = tmp_path / "nested" / "file.conf"

    existed = assure_file_exists(target)

    assert existed is False
    assert target.exists()
    os_system.assert_not_called()


def test_assure_file_exists_chowns_when_dir_not_writable(tmp_path, mocker):
    os_system = mocker.patch("waqd_installer.common.os.system")
    os_access = mocker.patch("waqd_installer.common.os.access", return_value=False)
    target = tmp_path / "file.conf"

    existed = assure_file_exists(target)

    assert existed is False
    assert target.exists()
    os_access.assert_called_with(tmp_path, os.W_OK)
    os_system.assert_called_once()
    assert "sudo chown" in os_system.call_args[0][0]


def test_assure_file_does_not_exist_removes_without_chown_when_dir_writable(tmp_path, mocker):
    os_system = mocker.patch("waqd_installer.common.os.system")
    target = tmp_path / "file.conf"
    target.write_text("content")

    existed = assure_file_does_not_exist(target)

    assert existed is False
    assert not target.exists()
    os_system.assert_not_called()


def test_assure_file_does_not_exist_chowns_when_dir_not_writable(tmp_path, mocker):
    os_system = mocker.patch("waqd_installer.common.os.system")
    os_access = mocker.patch("waqd_installer.common.os.access", return_value=False)
    target = tmp_path / "file.conf"
    target.write_text("content")

    existed = assure_file_does_not_exist(target)

    assert existed is False
    assert not target.exists()
    os_access.assert_called_with(tmp_path, os.W_OK)
    os_system.assert_called_once()
    assert "sudo chown" in os_system.call_args[0][0]
