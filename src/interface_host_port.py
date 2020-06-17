#!/usr/bin/env python3
import socket
from time import sleep
  
import logging

from ops.framework import (
    Object,
)

logger = logging.getLogger()


class HostPortAvailableEvent(EventBase):
    def __init__(self, handle, host_port):
        super().__init__(handle)
        self._host_port = host_port

    @property
    def host_port(self):
        return self._host_port


class HostPortEvents(ObjectEvents):
    host_port_available = EventSource(HostPortAvailableEvent)


class HostPortRequires(Object):
    on = HostPortEvents()

    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)

        self.framework.observe(
            charm.on[relation_name].relation_changed,
            self._on_relation_changed
        )

    def _on_relation_changed(self, event):
        host_port = event.relation.data[event.unit].get('host_port', None)
        if host_port:
            logger.info(f"the host_port is : {host_port}")
        else:
            logger.warning("port host is not in relation data")


class HostPortProvides(Object):
    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)

        self.framework.observe(
            charm.on[relation_name].relation_joined,
            self._on_relation_joined
        )

    def _on_relation_joined(self, event):
        event.relation.data[self.model.unit]['host_port'] = f'{socket.gethostname()}:6819'
