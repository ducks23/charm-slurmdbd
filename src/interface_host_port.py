from time import sleep
  
import logging

from ops.framework import (
    EventSource,
    EventBase,
    Object,
    ObjectEvents,
)

logger = logging.getLogger()


class HostPortProvides(Object):
    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)
        self.framework.observe(
            charm.on[relation_name].relation_joined,
            self._on_relation_joined
        )
        self._host = ""
        self._port = ""


    def _on_relation_joined(self, event):
        event.relation.data[self.model.unit]['port'] = 'foo'
        event.relation.data[self.model.unit]['host'] = 'bar'

    def set_host(self, host):
        self._host = str(host)

    def set_port(self, port):
        self._port = str(port)

