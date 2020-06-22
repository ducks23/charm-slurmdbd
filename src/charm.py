#! /usr/bin/env python3

from pathlib import Path

import subprocess, os, sys, socket, logging

sys.path.append('lib')

from ops.framework import StoredState

from ops.charm import CharmBase

from ops.main import main

from ops.model import ActiveStatus, BlockedStatus

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

        self._state.set_default(db_info=None)
        self._state.set_default(munge_key=None)
        
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
            self.fw_adapter,
            self.slurm_snap,
            self._state,
        )

    def _on_database_available(self, event):
        handle_database_available(
            event,
            self.fw_adapter,
            self._state,
        )

    def _on_munge_available(self, event):
        handle_munge_available(
            event,
            self.fw_adapter,
            self.slurm_snap,
        )


def handle_install(event, fw_adapter, slurm_snap, dbd_provides):
    """
    installs the slurm snap from edge channel if not provided as a resource
    then connects to the network
    """
    slurm_snap.install()
    fw_adapter.set_unit_status(ActiveStatus("snap installed"))
    
    port = "6819"
    protocol = "tcp"
    run(["open-port", f"{port}{protocol}"])


def handle_start(event, fw_adapter, slurm_snap, state):
    """Check to ensure we have the two things we need to
    successfully start slurmdbd; the munge_key from slurmctld,
    and the mysql db info.

    Set a blocked status if we don't have the munge_key and the db_info.
    """
    if state.db_info is None or state.munge_key is None:
        fw_adapter.set_unit_status(
            BlockedStatus("Need munge key and db info to continue...")
        )
        event.defer()
        return

    slurm_snap.write_config(state.db_info)
    slurm_snap.set_snap_mode()
    fw_adapter.set_unit_status(ActiveStatus("slurmdbd running"))


def handle_munge_available(event, fw_adapter, slurm_snap, state):
    slurm_snap.write_munge(event.munge.munge)
    state.munge_key = event.munge.munge
    fw_adapter.set_unit_status(ActiveStatus("munge available"))


def handle_database_available(event, fw_adapter, state):
    """Render the database details into the slurmdbd.yaml and
    set the snap.mode.
    """

    ## Render the slurmdbd config with data from the relation.
    #slurm_snap.write_config({
    #    'user': event.db_info.user,
    #    'password': event.db_info.password,
    #    'host': event.db_info.host,
    #    'port': event.db_info.port,
    #    'database': event.db_info.database,
    #})
    # Set the snap.mode
    #slurm_snap.set_snap_mode()
    #fw_adapter.set_unit_status(ActiveStatus("snap mode set"))

    state.db_info = {
        'user': event.db_info.user,
        'password': event.db_info.password,
        'host': event.db_info.host,
        'port': event.db_info.port,
        'database': event.db_info.database,
    }
    fw_adapter.set_unit_status(ActiveStatus("mysql available"))


if __name__ == "__main__":
    main(SlurmdbdCharm)
