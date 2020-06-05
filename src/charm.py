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
        
        # to do:
        # clean this up with framework adapter :)
        # implement the control states of the charm
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
        handle_snap_install()
        self.unit.status = ActiveStatus("snap installed")

    #2
    def on_database_available(self, event):
        handle_config(event)
        self.unit.status = ActiveStatus("config rendered")
        self.state.configured = True

    #3
    def on_start(self, event):
        if not self.state.configured:
            logger.info("deferred config not set yet__________")
            event.defer()
            return
        else:
            handle_snap_mode("slurmdbd")
            self.unit.status = ActiveStatus("snap mode set: slurmdbd")
            self.state.started = True


def handle_snap_mode(snap_mode):
        command = f"snap.mode={snap_mode}"
        subprocess.call(["snap", "set", "slurm", command])

def handle_snap_install():
    """
    checks if slurm snap is supplied as a resouce else installs the from snap store"
    """
    resource = ""
    try:
        resource = subprocess.check_output(['resource-get', 'slurm'])
        resource = resource.decode().strip()
    except subprocess.CalledProcessError as e:
        logger.error("Resource could not be found when executing: {}".format(e), exc_info=True)

    if len(resource) > 0:
        cmd = ["snap", "install"]
        cmd.append(resource)
        cmd.append("--dangerous")
    else:
        cmd = "snap install --edge".split()

    subprocess.call(cmd)
    subprocess.call(["snap", "connect", "slurm:network-control"])
    subprocess.call(["snap", "connect", "slurm:system-observe"])
    subprocess.call(["snap", "connect", "slurm:hardware-observe"])


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
