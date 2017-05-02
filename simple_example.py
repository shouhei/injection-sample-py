from injector import Injector, inject

class Inner(object):
    def __init__(self):
        self.forty_two = 42

class Outer(object):
    @inject
    def __init__(self, inner: Inner):
        self.inner = inner

if __name__ == "__main__":
    injector = Injector()
    outer = injector.get(Outer)
    print(outer.inner.forty_two)
