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

from interface_host_port import HostPortProvides

from interface_munge import MungeRequires

logger = logging.getLogger()


class SlurmdbdCharm(CharmBase):
    _state = StoredState() 
    slurm_instance_manager_cls = SlurmSnapInstanceManager

    def __init__(self, *args):
        super().__init__(*args)
        
        # provides host port to slurmctld
        self.dbd_provides = HostPortProvides(self, "slurmdbd-host-port", f'{socket.gethostname()}', '6819')
        self.slurm_snap = self.slurm_instance_manager_cls(self, "slurmdbd")
        self.fw_adapter = FrameworkAdapter(self.framework) 
        self.db = MySQLClient(self, "db")
        self.munge = MungeRequires(self, "munge")

        event_handler_bindings = {
            self.db.on.database_available: self._on_database_available,
            self.munge.on.munge_available: self._on_munge_available,
            self.on.install: self._on_install,
            self.on.start: self._on_start,
        }
        for event, handler in event_handler_bindings.items():
            self.fw_adapter.observe(event, handler)
        
        self._state.set_default(mysql=dict())
        self._state.set_default(db_configured=False)
        self._state.set_default(munge_configured=False)

    def _on_install(self, event):
        handle_install(
            event,
            self.fw_adapter,
            self.slurm_snap,
            self.dbd_provides,
        )

    def _on_start(self, event):
        handle_start(
            event,
            self._state,
            self.fw_adapter,
            self.slurm_snap,
        )

    def _on_database_available(self, event):
        handle_database_available(
            event,
            self._state,
            self.slurm_snap,
            self.fw_adapter,
        )
    def _on_munge_available(self, event):
        handle_munge_available(
            event,
            self._state,
            self.fw_adapter,
            self.slurm_snap,
        )


def handle_munge_available(event, state, fw_adapter, slurm_snap):
    slurm_snap.write_munge(event.munge.munge)
    state.munge_configured = True
    fw_adapter.set_unit_status(ActiveStatus("munge available"))



def handle_install(event, fw_adapter, slurm_snap, dbd_provides):
    """
    installs the slurm snap from edge channel if not provided as a resource
    then connects to the network
    """
    slurm_snap.install()
    fw_adapter.set_unit_status(ActiveStatus("snap installed"))
    

def handle_database_available(event, state, slurm_snap, fw_adapter):
    """Render the database details into the slurmdbd.yaml and
    set the snap.mode.
    """

    # Render the slurmdbd config with data from the relation.
    slurm_snap.write_config({
        'user': event.db_info.user,
        'password': event.db_info.password,
        'host': event.db_info.host,
        'port': event.db_info.port,
        'database': event.db_info.database,
    })
    state.db_configure = True

def handle_start(event, state, fw_adapter, slurm_snap):
    if state.db_configured is not False and state.munge_configured is not False:
        slurm_snap.set_snap_mode()
        logger.info("set the snap mode")
        port = "6819"
        protocol = "tcp"
        subprocess.run(["open-port", f"{port}{protocol}"])
        fw_adapter.set_unit_status(ActiveStatus("snap mode set"))
    else:
        logger.warning("event deferred")
        event.defer()
        return




if __name__ == "__main__":
    main(SlurmdbdCharm)
