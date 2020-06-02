#! /usr/bin/env python3

import sys

sys.path.append('lib')

from ops.charm import CharmBase

from ops.main import main



class SlurmdbdCharm(CharmBase):

    def __init__(self, *args):
        super().__init__(*args)
        
        self.framework.observe(self.on.install, self.on_install)
        self.framework.observe(self.on.start, self.on_start)

    def on_install(self, event):
        pass

    def on_start(self, event):
        pass

if __name__ == "__main__":
    main(SlurmdbdCharm)
