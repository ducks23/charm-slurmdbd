#! /usr/bin/env python3

from pathlib import Path

import subprocess, os, sys, socket, logging

sys.path.append('lib')

from ops.framework import StoredState

from ops.charm import CharmBase

from ops.main import main

from ops.model import ActiveStatus

from adapters.framework import FrameworkAdapter

from interface_mysql import MySQLClient

from slurm_snap_instance_manager import SlurmSnapInstanceManager

logger = logging.getLogger()


class SlurmdbdCharm(CharmBase):
    _state = StoredState()
    
    slurm_instance_manager_cls = SlurmSnapInstanceManager

    def __init__(self, *args):
        super().__init__(*args)
        
        #things to consider:
        # testing the status of snap
        # testing db connection
        # seeing if you want to configure without mysql
        
        self.slurm_instance_manager = self.slurm_instance_manager_cls(self, "slurm")

        self.fw_adapter = FrameworkAdapter(self.framework) 
        self.db = MySQLClient(self, "db")
        self.framework.observe(
                self.db.on.database_available,
                self.on_database_available
        )
        self.framework.observe(self.on.install, self.on_install)
        self.framework.observe(self.on.start, self.on_start)

        self._state.set_default(configured=False)
        self._state.set_default(started=False)
    
    #need to set off hooks in this order
    #1
    def on_install(self, event):
        handle_install(
                event,
                self.fw_adapter,
                self.slurm_instance_manager
        )

    #2
    def on_database_available(self, event):
        handle_config(
                event,
                self._state,
                self.fw_adapter,
        )

    #3
    def on_start(self, event):
        handle_start(
                event,
                self._state,
                self.fw_adapter,
                self.slurm_instance_manager
        )


def handle_install(event, fw_adapter, slurm_inst):
    """
    installs the slurm snap from edge channel if not provided as a resource
    then connects to the network
    """
    slurm_inst.install_snap("--edge")
    slurm_inst.snap_connect()
    fw_adapter.set_unit_status(ActiveStatus("snap installed"))


def handle_start(event, state, fw_adapter, slurm_inst ):
    """
    checks to see if snap is configured to mysql charm then sets the 
    snap mode to slurmdbd
    """
    if not state.configured:
        logger.info("deferred config not rendered")
        event.defer()
    else:
        slurm_inst.set_snap_mode("slurmdbd")
        logger.info("snap mode set to slurmdbd")
        fw_adapter.set_unit_status(ActiveStatus("snap mode set to slurmdbd"))
        state.started = True


def handle_config(event, state, fw_adapter):
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

    fw_adapter.set_unit_status(ActiveStatus("config rendered"))
    state.configured = True


if __name__ == "__main__":
    main(SlurmdbdCharm)
