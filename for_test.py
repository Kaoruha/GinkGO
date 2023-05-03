from functools import singledispatchmethod


class halo(object):
    @singledispatchmethod
    def do(self):
        pass

    @do.register
    def _(self, a: int, b: int):
        print("This is function 1")

    @do.register
    def _(self, a: str):
        print("This is function 2")


h = halo()

h.do(1, 2)
h.do("1")
