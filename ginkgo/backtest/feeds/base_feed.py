"""
The `Handler` class should deal with the event.
"""
from ginkgo.libs import GinkgoSingleLinkedList


class BaseHandler:
    def __init__(self):
        self.subscribers = GinkgoSingleLinkedList()

    def subscribe(self, guys):
        # TODO Type Filter
        self.subscribers.append(guys)

    def broadcast(self):
        for i in self.subscribers:
            # Got data
            pass
