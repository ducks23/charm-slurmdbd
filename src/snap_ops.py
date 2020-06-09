import subprocess, logging, os

from pathlib import Path

logger = logging.getLogger()

def set_snap_mode(snap_mode):
    command = f"snap.mode={snap_mode}"
    subprocess.call(["snap", "set", "slurm", command])


def snap_connect(slot=None):
    connect_commands = [
        ["snap", "connect", "slurm:network-control"],
        ["snap", "connect", "slurm:system-observe"],
        ["snap", "connect", "slurm:hardware-observe"],
    ]

    for connect_command in connect_commands:
        if slot:
            connect_command.append(slot)
        try:
            subprocess.call(connect_command)
        except subprocess.CalledProcessError as e:
            logger.error("Could not connect snap interface: {}".format(e), exc_info=True)


def install_snap(channel="--edge"):
    resource = ""
    try:
        resource = subprocess.check_output(['resource-get', 'slurm'])
        resource = resource.decode().strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Resource could not be found when executing: {e}", exc_info=True)

    # Create the snap install command.
    snap_install_cmd = ["snap", "install"]
    if Path(resource).exists() and os.stat(resource).st_size != 0:
        snap_install_cmd.append(resource)
        snap_install_cmd.append("--dangerous")
    else:
        snap_install_cmd.append("slurm")
        snap_install_cmd.append(channel)
    # Execute the snap install command.
    try:
        subprocess.call(snap_install_cmd)
    except subprocess.CalledProcessError as e:
        logger.error(f"Could not install the slurm snap using the command: {e}", exc_info=True)
