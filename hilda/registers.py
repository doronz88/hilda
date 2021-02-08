class Registers(object):
    """
    Wrapper for more convenient access to modify current frame's registers
    """

    def __init__(self, client):
        self.__dict__['_client'] = client

    def __getattr__(self, item):
        return self._client.get_register(item)

    def __getitem__(self, item):
        return self._client.get_register(item)

    def __setattr__(self, key, value):
        return self._client.set_register(key, value)

    def __setitem__(self, key, value):
        return self._client.set_register(key, value)

    def __dir__(self):
        result = []
        for group in self._client.frame.register.regs:
            for register in group:
                result.append(register.name)
        return result

    def show(self):
        """ Show current frame's registers """
        print(self._client.frame.register.regs)
