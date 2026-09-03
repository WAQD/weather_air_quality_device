from waqd_station.settings import Settings
from waqd_station.components.updater import OnlineUpdater
from waqd_station.app.component_reg import ComponentRegistry

RASPI_BASE_IMAGE = "raspi/raspbian_py:1"
WAQD_IMAGE = "raspi/waqd_install:1"


def test_repo_is_reachable(base_fixture, mocker):
    # Inject a fake `github` module so the lazy `from github import Github` in
    # updater._connect_to_repository resolves offline (PyGithub is not in the
    # test extras). Github().get_repo(repo) returns a MagicMock repository.
    fake_repo = mocker.MagicMock(name="github_repo")
    fake_github_cls = mocker.MagicMock(name="Github")
    fake_github_cls.return_value.get_repo.return_value = fake_repo
    mocker.patch.dict(
        "sys.modules",
        {"github": mocker.MagicMock(name="github_pkg", Github=fake_github_cls)},
    )

    settings = Settings(base_fixture.testdata_path / "integration")
    comps = ComponentRegistry(settings)
    # config.ini has auto_updater_enabled=True and updater_use_beta_channel=False
    online_updater = OnlineUpdater(comps, settings=settings)
    online_updater._use_beta_channel = True
    online_updater._connect_to_repository()
    assert online_updater._repository  # only check if object exists


def test_check_should_update(base_fixture):
    import waqd_station.components.updater as updater  # access the loaded global WAQD_VERSION

    settings = Settings(base_fixture.testdata_path / "integration")
    comps = ComponentRegistry(settings)

    online_updater = OnlineUpdater(comps, settings=settings)
    online_updater._use_beta_channel = True  # config defaults to False; override for this suite
    # Main versions to Main versions
    updater.WAQD_VERSION = "1.1.0"
    # same version -  no update
    assert not online_updater._check_should_update("v1.1.0")  # use v to see if it is cut
    # lesser version - no update
    assert not online_updater._check_should_update("1.0.0")
    # higher version
    assert online_updater._check_should_update("1.2.0")

    # Main Version
    # Main version to Beta version
    # beta flag enabled
    # lesser version - no update
    assert not online_updater._check_should_update("1.0.0b19")
    # same version - but Beta -> must be older
    assert not online_updater._check_should_update("1.1.0b2")
    # higher version
    assert online_updater._check_should_update("1.2.0b0")

    # beta flag disabled - no update
    online_updater._use_beta_channel = False
    assert not online_updater._check_should_update("1.0.0b19")
    assert not online_updater._check_should_update("1.1.0b2")

    # Beta Version
    # Beta Version to Main Version
    updater.WAQD_VERSION = "1.1.0b1"
    assert not online_updater._check_should_update("1.0.0")
    assert online_updater._check_should_update("1.2.0")

    # Beta Version to Beta Version
    online_updater._use_beta_channel = True
    assert not online_updater._check_should_update("1.1.0b0")
    assert online_updater._check_should_update("1.1.0b2")
    online_updater._use_beta_channel = False
    assert not online_updater._check_should_update("1.1.0b2")

    # Beta Version to Alpha Version
    # negative test, not enabled
    assert not online_updater._check_should_update("1.1.0a2")
    # enable - higher version should work
    updater.waqd.DEBUG_LEVEL = 1
    online_updater._use_beta_channel = True
    assert online_updater._check_should_update("1.1.0a2")
    # lower or equal should not
    assert not online_updater._check_should_update("1.1.0a1")
    assert not online_updater._check_should_update("1.1.0a0")

    # Alpha Version
    updater.WAQD_VERSION = "1.1.0a1"
    online_updater._use_beta_channel = True
    updater.waqd.DEBUG_LEVEL = 1
    # to alpha
    assert online_updater._check_should_update("1.1.0a2")
    assert not online_updater._check_should_update("1.1.0a0")
    assert not online_updater._check_should_update("1.1.0a1")
    # to beta
    assert online_updater._check_should_update("1.1.0b2")
    assert online_updater._check_should_update("1.1.0b1")
    # TODO currently will always update to beta
    assert online_updater._check_should_update("1.1.0b0")
    # to main
    assert online_updater._check_should_update("1.1.0")
    assert online_updater._check_should_update("1.2.0")
    assert not online_updater._check_should_update("1.0.0")
    # disabled debug level - only update to beta or main
    updater.waqd.DEBUG_LEVEL = 0
    # TODO: updates from alpha to alpha
    assert online_updater._check_should_update("1.1.0a2")
    assert online_updater._check_should_update("1.1.0b1")
    assert online_updater._check_should_update("1.1.0")
