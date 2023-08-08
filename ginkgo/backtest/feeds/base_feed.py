"""
The `Handler` class should deal with the event.
"""
from ginkgo.libs import GinkgoSingleLinkedList


class BaseFeed(object):
    def __init__(self, *args, **kwargs):
        self._subscribers = GinkgoSingleLinkedList()

    @property
    def subscribers(self):
        return self._subscribers

    def subscribe(self, guys):
        # TODO Type Filter
        self._subscribers.append(guys)

    def broadcast(self):
        raise NotImplementedError()
