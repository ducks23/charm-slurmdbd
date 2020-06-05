#! /usr/bin/env python3

from pathlib import Path

import subprocess, os, sys, socket, logging

sys.path.append('lib')

from ops.framework import StoredState

from ops.charm import CharmBase

from ops.main import main

from ops.model import ActiveStatus

from interface_mysql import MySQLClient

logger = logging.getLogger()


class SlurmdbdCharm(CharmBase):
    state = StoredState()
    
    def __init__(self, *args):
        super().__init__(*args)
        
        self.db = MySQLClient(self, "db")
        self.framework.observe(
                self.db.on.database_available,
                self.on_database_available
        )
        self.framework.observe(self.on.install, self.on_install)
        self.framework.observe(self.on.start, self.on_start)

        self.state.set_default(configured=False)
        self.state.set_default(started=False)
    
    #need to set off hooks in this order
    #1
    def on_install(self, event):
        handle_snap_install("--edge")
        snap_connect()
        self.unit.status = ActiveStatus("snap installed")

    #2
    def on_database_available(self, event):
        handle_config(event)
        self.unit.status = ActiveStatus("config rendered")
        self.state.configured = True

    #3
    def on_start(self, event):
        if not self.state.configured:
            logger.info("deferred config not rendered")
            event.defer()
            return
        else:
            handle_snap_mode("slurmdbd")
            self.unit.status = ActiveStatus("snap mode set: slurmdbd")
            self.state.started = True


def handle_snap_mode(snap_mode):
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


def handle_snap_install(channel="--edge"):
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


def handle_config(event):
    """Render the context into the source template and write
    it to the target location.
    """
    context = {
        'user': event.db_info.user,
        'password': event.db_info.password,
        'host': event.db_info.host,
        'port': event.db_info.port,
        'database': event.db_info.database,
    }
    hostname = socket.gethostname().split(".")[0]
    source = "template/slurmdbd.yaml.tmpl"
    target = "/var/snap/slurm/common/etc/slurm-configurator/slurmdbd.yaml"
    context = {**{"hostname": hostname}, **context}
    
    source = Path(source)
    target = Path(target)

    if context and type(context) == dict:
        ctxt = context
    else:
        raise TypeError(
            f"Incorect type {type(context)} for context - Please debug."
        )

    if not source.exists():
        raise Exception(
            f"Source config {source} does not exist - Please debug."
        )

    if target.exists():
        target.unlink()

    with open(str(target), 'w') as f:
            f.write(open(str(source), 'r').read().format(**ctxt))


if __name__ == "__main__":
    main(SlurmdbdCharm)
