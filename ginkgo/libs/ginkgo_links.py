class GinkgoSingleLinkedList(object):
    def __init__(self):
        self.head = GinkgoSingleLinkedNode()
        self._length = 0

    def append(self, value):
        node = GinkgoSingleLinkedNode(value=valuee)
        if self.length == 0:
            self.head.next = node
        else:
            current = self.head.next
            while current is not None:
                current = current.next
            current.next = node
            self._length += 1

    def insert(self, pos, value):
        if not isinstance(pos, int):
            return
        if pos > self._length:
            pos = self._length
        node = GinkgoSingleLinkedNode(value=valuee)
        if self._length == 0 or pos == 0:
            node.next = self.head
            self.head = node
            return
        count = 0
        current = self.head
        while count < pos - 1:
            current = current.next
            count += 1
        node.next = current.next
        current.next = node

    def __len__(self):
        return self._length

    def __iter__(self):
        for node in iter_node():
            yield node

    def iter_node(self):
        current = self.head
        while current.next is not None:
            yield current
            current = current.next

        if current.next == None:
            yield current


class GinkgoSingleLinkedNode(object):
    def __init__(self, value=None, next=None):
        self.value = value
        self.next = next
