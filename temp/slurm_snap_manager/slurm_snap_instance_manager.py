import logging
import os
import socket
import subprocess

from base64 import (
    b64encode,
    b64decode,
)

from pathlib import Path

from ops.framework import (
    Object,
    StoredState,
    EventBase,
    EventSource,
    ObjectEvents,
)

from ops.model import (
    ModelError,
    ActiveStatus,
    MaintenanceStatus,
)

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

    _stored = StoredState()

    on = SlurmSnapInstanceManagerEvents()

    logger = logging.getLogger()

    MUNGE_KEY_PATH = Path("/var/snap/slurm/common/etc/munge/munge.key")
    SLURM_CONFIGURATOR_TEMPLATES_DIR = Path(
        "/var/snap/slurm/common/etc/slurm-configurator"
    )
    TEMPLATE_DIR = Path(f"{os.getcwd()}/templates")


    def __init__(self, charm, key):
        super().__init__(charm, key)
        self.snap_mode = key
        self.fw_adapter = FrameworkAdapter(self.framework)

        # Set the template and config file paths based on the snap.mode.
        # Throw an exception if initialized with an unsupported snap.mode.
        if self.snap_mode == "slurmdbd":
            self.slurm_config_yaml = self.SLURM_CONFIGURATOR_TEMPLATES_DIR / 'slurmdbd.yaml'
            self.slurm_config_template = self.TEMPLATE_DIR / 'slurmdbd.yaml.tmpl'
        elif self.snap_mode in ["slurmd", "slurmrestd", "slurmctld"]:
            self.slurm_config_yaml = self.SLURM_CONFIGURATOR_TEMPLATES_DIR / 'slurm.yaml'
            self.slurm_config_template = self.TEMPLATE_DIR / 'slurm.yaml.tmpl'
        else:
            self.logger.error(
                f"Slurm component not supported: {self.snap_mode}",
                exc_info=True
            )

    @property
    def _hostname(self):
        return socket.gethostname().split(".")[0]

    def set_snap_mode(self):
        """Set the snap mode, thorw an exception if it fails.
        """
        try:
            subprocess.call([
                "snap",
                "set",
                "slurm",
                f"snap.mode={self.snap_mode}",
            ])
        except subprocess.CalledProcessError as e:
            self.logger.error(
               f"Setting the snap.mode failed. snap.mode={self.snap_mode} - {e}",
                exc_info=True
            )

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
                self.logger.error(
                    f"Could not connect snap interface: {e}",
                    exc_info=True,
                )


    def _install_snap(self):
        snap_install_cmd = ["snap", "install"]
        resource_path = None
        try:
            resource_path = self.model.resources.fetch('slurm')
        except ModelError as e:
            logger.error(
                f"Resource could not be found when executing: {e}",
                exc_info=True,
            )
        if resource_path:
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
                f"Could not install the slurm snap using the command: {e}",
                exc_info=True
            )

    def write_munge_key(self, munge_key):
        munge = b64decode(munge_key.encode())
        self.MUNGE_KEY_PATH.write_bytes(munge)


    def write_config(self, context):

        ctxt = {}
        source = self.slurm_config_template
        target = self.slurm_config_yaml

        if not type(context) == dict:
            self.framework.set_unit_status(
                MaintenanceStatus("context not of type dict")
            )
            return
        else:
            ctxt = {**{"hostname": self._hostname}, **context}
        if not source.exists():
           # raise Exception(f"Source config {source} does not exist - Please debug.")
            self.framework.set_unit_status(MaintenanceStatus("source doesn't exist"))
        if target.exists():
            target.unlink()

        target.write_text(source.read_text().format(**ctxt))
