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
        
        self.slurm_instance_manager = self.slurm_instance_manager_cls(self, "slurm")
        self.fw_adapter = FrameworkAdapter(self.framework) 
        self.db = MySQLClient(self, "db")

        event_handler_bindings = {
            self.db.on.database_available: self._on_database_available,
            self.slurm_instance_manager.on.config_changed: self._on_config_changed,
            self.on.install: self._on_install
        }
        for event, handler in event_handler_bindings.items():
            self.fw_adapter.observe(event, handler)

        self._state.set_default(configured=False)
    
    def _on_install(self, event):
        handle_install(
            self.fw_adapter,
            self.slurm_instance_manager
        )

    def _on_database_available(self, event):
        handle_config(
            event,
            self._state,
            self.fw_adapter,
            self.slurm_instance_manager
        )

    def _on_config_changed(self, event):
        handle_start(
            event,
            self._state,
            self.fw_adapter,
            self.slurm_instance_manager
        )


def handle_install(fw_adapter, slurm_inst):
    """
    installs the slurm snap from edge channel if not provided as a resource
    then connects to the network
    """
    slurm_inst.install()
    fw_adapter.set_unit_status(ActiveStatus("snap installed"))


def handle_config(event, state, fw_adapter, slurm_inst):
    """Render the context into the source template and write
    it to the target location.
    """
    if state.configured is False:   
        context = {
            'user': event.db_info.user,
            'password': event.db_info.password,
            'host': event.db_info.host,
            'port': event.db_info.port,
            'database': event.db_info.database,
        }
    hostname = socket.gethostname().split(".")[0]
    source = Path("template/slurmdbd.yaml.tmpl")
    target = Path("/var/snap/slurm/common/etc/slurm-configurator/slurmdbd.yaml")
    context = {**{"hostname": hostname}, **context}
    slurm_inst.write_config(source, target, context)
    
    fw_adapter.set_unit_status(ActiveStatus("config rendered"))
    state.configured = True


def handle_start(event, state, fw_adapter, slurm_inst ):
    """
    checks to see if snap is configured to mysql charm then sets the 
    snap mode to slurmdbd
    """
    #move snap_mode into config.yaml
    slurm_inst.set_snap_mode("slurmdbd")
    logger.info("snap mode set to slurmdbd")
    fw_adapter.set_unit_status(ActiveStatus("snap mode set to slurmdbd"))

if __name__ == "__main__":
    main(SlurmdbdCharm)
