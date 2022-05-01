class test(object):
    def __init__(self):
        self.a = 0

    def pls(self):
        self.a += 1
        print(self.a)
        return self.a >5


if __name__ == "__main__":
    a = test()
    for i in range(10):
        if a.pls():
            print("bigger than 5")
    print(a.a)

