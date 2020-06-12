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
        
        self.slurm_snap = self.slurm_instance_manager_cls(self, "slurm")
        self.fw_adapter = FrameworkAdapter(self.framework) 
        self.db = MySQLClient(self, "db")

        event_handler_bindings = {
            self.db.on.database_available: self._on_database_available,
            self.on.install: self._on_install,
            self.on.write_config: self._on_write_config,
        }
        for event, handler in event_handler_bindings.items():
            self.fw_adapter.observe(event, handler)
        
        self._state.set_default(mysql=dict())

    def _on_install(self, event):
        handle_install(
            self.fw_adapter,
            self.slurm_snap
        )

    def _on_database_available(self, event):
        handle_database_available(
            event,
            self._state
        )
    def _on_write_config(self, event):
        handle_write_config(
            event,
            self._state
        )


def handle_install(fw_adapter, slurm_snap):
    """
    installs the slurm snap from edge channel if not provided as a resource
    then connects to the network
    """
    slurm_snap.install()
    fw_adapter.set_unit_status(ActiveStatus("snap installed"))


def handle_database_available(event, state):
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
    state.mysql = context
    """
    hostname = socket.gethostname().split(".")[0]
    source = Path("template/slurmdbd.yaml.tmpl")
    target = Path("/var/snap/slurm/common/etc/slurm-configurator/slurmdbd.yaml")
    context = {**{"hostname": hostname}, **context}
    slurm_snap.write_config(source, target, context)
    snap_mode = fw_adapter.get_config("snap-mode")
    slurm_snap.set_snap_mode(snap_mode)
    
    fw_adapter.set_unit_status(ActiveStatus("slurmdbd started"))
    """

if __name__ == "__main__":
    main(SlurmdbdCharm)
