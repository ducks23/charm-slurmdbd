#!/usr/bin/env python3
import socket
from time import sleep
  
import logging

from ops.framework import (
    Object,
    ObjectEvents,
    EventSource,
    EventBase,
)

logger = logging.getLogger()


class HostPortAvailableEvent(EventBase):
    def __init__(self, handle, host_port):
        super().__init__(handle)
        logger.info(handle)
        self._host_port = host_port

    @property
    def host_port(self):
        return self._host_port

    def snapshot(self):
        return self._host_port.snapshot()

    def restore(self, snapshot):
        self._host_port = HPInfo.restore(snapshot)

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
        host = event.relation.data[event.unit].get('host', None)
        port = event.relation.data[event.unit].get('port', None)
        host_port = HPInfo(host, port)
        if host and port:
            logger.info(f"the host_port is : {host} {port}")
            self.on.host_port_available.emit(host_port)
        else:
            logger.warning("host port interface is not in relation data")



class HPInfo:

    def __init__(self, host=None,port=None):
        self.set_address(host, port)

    def set_address(self, host, port):
        self._host = host
        self._port = port

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port

    @classmethod
    def restore(cls, snapshot):
        return cls(
            host=snapshot['host_port.host'],
            port=snapshot['host_port.port'],
        )

    def snapshot(self):
        return {
            'host_port.host': self.host,
            'host_port.port': self.port,
        }


class HostPortProvides(Object):
    def __init__(self, charm, relation_name, host, port):
        super().__init__(charm, relation_name)
        self._host = host
        self._port = port

        self.framework.observe(
            charm.on[relation_name].relation_joined,
            self._on_relation_joined
        )

    def _on_relation_joined(self, event):
        logger.info(self._host)
        logger.info(self._port)
        event.relation.data[self.model.unit]['host'] = self._host
        event.relation.data[self.model.unit]['port'] = self._port
