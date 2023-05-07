from functools import singledispatch


class haha(object):
    @singledispatch
    def a(self):
        pass

    @a.register
    def _(self, string: str, string2: str):
        print(string + string2)

    @a.register
    def _(self, string: str):
        print(string)


sb = haha()
sb.a("halo", "loha")
