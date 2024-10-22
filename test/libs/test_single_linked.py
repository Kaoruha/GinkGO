import unittest
from ginkgo.libs.ginkgo_links import GinkgoSingleLinkedList


class SingleLinkedListTest(unittest.TestCase):
    def __init__(self, *args, **kwargs) -> None:
        super(SingleLinkedListTest, self).__init__(*args, **kwargs)

    def test_SL_init(self):
        l = GinkgoSingleLinkedList()
        self.assertEqual(l.head.value, None)
        self.assertEqual(len(l), 0)

    def test_SL_append(self):
        l = GinkgoSingleLinkedList()
        l.append(1)
        self.assertEqual(len(l), 1)
        l.append(2)
        self.assertEqual(len(l), 2)
        l.append(3)
        self.assertEqual(len(l), 3)
        for i in range(3):
            print(i)

    def test_SL_insert(self):
        import random

        try_counts = 100
        insert_max = 200

        for r in range(try_counts):
            l = GinkgoSingleLinkedList()
            for i in range(insert_max):
                l.append(i + 1)
            r = int(random.random() * insert_max) + 1
            l.insert(r, 1111)
            count = 0
            for item in l:
                count += 1
                # print(f"current:{count}", end="\r")
                if count <= r:
                    self.assertEqual(count, item.value)
                elif count == r + 1:
                    self.assertEqual(1111, item.value)
                else:
                    self.assertEqual(count - 1, item.value)

    def test_SL_iter(self):
        l = GinkgoSingleLinkedList()
        l.append(1)
        l.append(2)
        l.append(3)
        l.append(4)
        l.append(5)
        count = 0
        for i in l:
            count += 1
            self.assertEqual(i.value, count)

        l = GinkgoSingleLinkedList()
        l.append(5)
        l.append(4)
        l.append(3)
        l.append(2)
        l.append(1)
        count = 6
        for i in l:
            count -= 1
            self.assertEqual(i.value, count)
