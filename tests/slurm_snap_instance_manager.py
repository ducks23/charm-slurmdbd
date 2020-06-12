#!/usr/bin/env python3

import unittest
import sys
sys.path.append('lib')
sys.path.append('src')

from ops import testing
from ops.model import ActiveStatus
from ops.framework import StoredState

from charm import SlurmdbdCharm
from slurm_snap_instance_manager import (
        SlurmSnapInstanceManager,
        SlurmSnapInstanceManagerEvents,
)

class TestSlurmSnapInstanceManager(SlurmSnapInstanceManager):
    # A type used to replace SlurmSnapInstanceManager during unit testing
    on = SlurmSnapInstanceManagerEvents()
    _stored = StoredState()

    def install(self):
        self._install_called = True
        super().install()
    
    def _install_snap(self ):
        pass

    def _snap_connect(self):
        pass

class TestSlurmdbdCharm(unittest.TestCase):
    def setUp(self):
        self.harness = testing.Harness(SlurmdbdCharm)
        self.harness._charm_cls.slurm_instance_manager_cls = TestSlurmSnapInstanceManager

    def test_install(self):
        self.harness.begin()
        self.harness.charm.on.install.emit()
        self.assertTrue(self.harness.charm.slurm_instance_manager._install_called)


if __name__ == "__main__":
    unittest.main()
