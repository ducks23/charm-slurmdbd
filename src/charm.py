#! /usr/bin/env python3

import sys

sys.path.append('lib')

from ops.charm import CharmBase

from ops.main import main

from ops.model import ActiveStatus

from handler import SlurmSnapOps

class SlurmdbdCharm(CharmBase):

    def __init__(self, *args):
        super().__init__(*args)
        
        self.framework.observe(self.on.install, self.on_install)
        self.framework.observe(self.on.start, self.on_start)

        self.slurm_snap = SlurmSnapOps()

    def on_install(self, event):
        self.slurm_snap.install()
        self.unit.status = ActiveStatus("snap installed")

    def on_start(self, event):
        self.slurm_snap.set_mode("slurmdbd")
        self.unit.status = ActiveStatus("snap mode set: slurmdbd")
if __name__ == "__main__":
    main(SlurmdbdCharm)
