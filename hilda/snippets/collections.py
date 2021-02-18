from hilda.objective_c_symbol import ObjectiveCSymbol


def iter_values(symbol: ObjectiveCSymbol):
    enum = symbol.objectEnumerator()
    item = enum.nextObject()
    while item != 0:
        yield item
        item = enum.nextObject()


def iter_keys(symbol: ObjectiveCSymbol):
    enum = symbol.keyEnumerator()
    item = enum.nextObject()
    while item != 0:
        yield item
        item = enum.nextObject()
