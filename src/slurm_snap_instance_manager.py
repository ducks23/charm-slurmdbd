import subprocess, logging, os

from pathlib import Path

logger = logging.getLogger()

from ops.framework import (
        Object,
        StoredState,
        EventBase,
        EventSource,
        ObjectEvents,
)

from ops.model import ModelError

from adapters.framework import FrameworkAdapter


class SlurmConfigChangedEvent(EventBase):
    def __init__(self, handle):
        super().__init__(handle)
        self.config = True

    def is_configured(self):
        return self.config

class SlurmSnapInstanceManagerEvents(ObjectEvents):
    slurm_config_changed = EventSource(SlurmConfigChangedEvent)

class SlurmSnapInstanceManager(Object):
    """
    responsible for installing the slurm_snap, connecting to network, and
    setting the snap mode
    """
    on = SlurmSnapInstanceManagerEvents()

    _stored = StoredState()


    def __init__(self, charm, key):
        super().__init__(charm, key)
        self.fw_adapter = FrameworkAdapter(self.framework)

    def set_snap_mode(self, snap_mode):
        command = f"snap.mode={snap_mode}"
        subprocess.call(["snap", "set", "slurm", command])


    def install(self):
        self._install_snap()
        self._snap_connect()
    
    
    def _snap_connect(self, slot=None):
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


    def _install_snap(self):
        snap_install_cmd = ["snap", "install"]
        resource_path = "0"
        try:
            resource_path = self.model.resources.fetch('slurm')
        except ModelError as e:
            logger.error(f"Resource could not be found when executing: {e}", exc_info=True)
        if len(str(resource_path)) > 1 and Path(resource_path).exists():
            snap_install_cmd.append(resource_path)
            snap_install_cmd.append("--dangerous")
        else:
            snap_store_channel = self.fw_adapter.get_config("snap-store-channel")
            snap_install_cmd.append("slurm")
            snap_install_cmd.append(f"--{snap_store_channel}")
        
        try:
            subprocess.call(snap_install_cmd)
        except subprocess.CalledProcessError as e:
            logger.error(
                f"Could not install the slurm snap using the command: {e}", exc_info=True)

    def write_config(self, source, target, context):
        if context and type(context) == dict:
            ctxt = context
        else:
            raise TypeError(
                    f"Incorect type {type(context)} for context - Please debug.")

        if not source.exists():
            raise Exception(f"Source config {source} does not exist - Please debug.")

        if target.exists():
            target.unlink()

        with open(str(target), 'w') as f:
            f.write(open(str(source), 'r').read().format(**ctxt))

        self.on.slurm_config_changed.emit()
