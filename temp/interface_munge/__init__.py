#!/usr/bin/env python3
import socket
from time import sleep
from base64 import b64encode 
import logging

from ops.framework import (
    Object,
    ObjectEvents,
    EventSource,
    EventBase,
)

logger = logging.getLogger()


class MungeAvailableEvent(EventBase):
    def __init__(self, handle, munge):
        super().__init__(handle)
        logger.info(handle)
        self._munge = munge

    @property
    def munge(self):
        return self._munge

    def snapshot(self):
        return self._munge.snapshot()

    def restore(self, snapshot):
        self._munge = MungeInfo.restore(snapshot)

class MungeEvents(ObjectEvents):
    munge_available = EventSource(MungeAvailableEvent)


class MungeRequires(Object):
    on = MungeEvents()

    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)

        self.framework.observe(
            charm.on[relation_name].relation_changed,
            self._on_relation_changed
        )

    def _on_relation_changed(self, event):
        munge = event.relation.data[event.unit].get('munge', None)
        m = MungeInfo(munge)
        if m:
            logger.info(f"munge key required")
            self.on.munge_available.emit(m)
        else:
            logger.warning("munge interface is not in relation data")



class MungeInfo:

    def __init__(self, munge=None):
        self.set_address(munge)

    def set_address(self, munge):
        self._munge = munge

    @property
    def munge(self):
        return self._munge

    @classmethod
    def restore(cls, snapshot):
        return cls(
            munge=snapshot['munge.munge'],
        )

    def snapshot(self):
        return {
            'munge.munge': self._munge,
        }



class MungeProvides(Object):
    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)
        self.framework.observe(
            charm.on[relation_name].relation_joined,
            self._on_relation_joined
        )

    def _on_relation_joined(self, event):
        munge = open("/var/snap/slurm/common/etc/munge/munge.key", "rb").read()
        munge_key = b64encode(munge).decode()
        event.relation.data[self.model.unit]['munge'] = munge_key

