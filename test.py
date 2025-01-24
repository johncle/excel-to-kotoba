from collections import OrderedDict


class DefaultOrderedDict(OrderedDict):
    # Modified from http://stackoverflow.com/a/6190500/562769
    def __init__(self, *a, **kw):
        super().__init__(self, *a, **kw)
        self.default_factory = lambda: ([], [], [], [])

    def __getitem__(self, key):
        try:
            return super().__getitem__(self, key)
        except KeyError:
            return self.__missing__(key)

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        self[key] = value = self.default_factory()
        return value

    def __reduce__(self):
        if self.default_factory is None:
            args = tuple()
        else:
            args = (self.default_factory,)
        return type(self), args, None, None, self.items()

    def copy(self):
        return self.__copy__()

    def __copy__(self):
        return type(self)(self.default_factory, self)

    def __deepcopy__(self, memo):
        import copy

        return type(self)(self.default_factory, copy.deepcopy(self.items()))

    def __repr__(self):
        return f"OrderedDefaultDict({self.default_factory}, {super().__repr__(self)})"


od = DefaultOrderedDict()
print(od)
