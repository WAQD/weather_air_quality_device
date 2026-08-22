import os
import tarfile
import platform
import pytest
import waqd
from waqd import __version__ as VERSION
from waqd.settings import Settings, UPDATER_USER_BETA_CHANNEL, AUTO_UPDATER_ENABLED
#guestfish --ro -a /home/peter/2022-01-28-raspios-bullseye-arm64.img -m /dev/sda2:/ tar-out / - | docker import - waqd
# docker build . -t goszpeti/raspi-base:latest -f ./test/testdata/auto_updater/dockerfile_base
# docker run --privileged --name rpi -v /sys/fs/cgroup:/sys/fs/cgroup:ro -td goszpeti/waqd systemd

USERNAME = "pi"
RASPI_BASE_IMAGE = "goszpeti/raspi-base:latest"
WAQD_IMAGE = "goszpeti/waqd:latest"
#RUNAS_CMD = "runuser -u " + USERNAME

def test_install_in_docker_without_gui(base_fixture):
    """ Start an installation with the installer running without the updater ui. """
    from docker.client import DockerClient
    client = DockerClient()

    docker_base_cmd = f"docker build {str(base_fixture.base_path)} -t {WAQD_IMAGE} -f ./test/testdata/auto_updater/dockerfile_install"
    if platform.system() == "Linux":
        docker_base_cmd = docker_base_cmd + " | tee install.log"
    ret = os.system(docker_base_cmd)
    assert ret == 0
    cont = client.containers.run(
        WAQD_IMAGE, name="waqd-install-test", detach=True, auto_remove=True, privileged=True,
        volumes=["/sys/fs/cgroup:/sys/fs/cgroup:ro"], command="systemd")
    # RUN bash -lic "./home/pi/waqd-dev/script/installer/exec_install.sh && waqd_install"
    # check if pipx installed
    # cont.logs()
    res = cont.attach()
   
    res = cont.exec_run("./waqd-dev/script/installer/exec_install.sh", user="pi")
    res = cont.exec_run("python3 -m pipx --version", user="pi")
    assert res.exit_code == 0
    # check if pyqt-5 is installed
    res = cont.exec_run("qtchooser -l", user="pi")
    assert b"qt5" in res.output
    # check if waqd is installed
    res = cont.exec_run("/home/pi/.local/bin/waqd.{VERSION} --version")
    assert VERSION in res.output.decode("utf-8")
    # get waqd-start executable

    # check if it was set for autostart

    # check system setup
    # autostart
    #arch = cont.get_archive("/home/pi/.config/lxsession/LXDE-pi/autostart")

    # ... TODO
    #cont.attach()
    # TODO finally
    cont.stop()

    # TODO at the end
    client.images.prune()

