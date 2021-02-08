from collections import namedtuple

Command = namedtuple('Command', 'name impl')


def command():
    def decorator(func):
        func._is_cmd = True
        return func

    return decorator


class CommandsMeta(type):
    def __new__(cls, name, bases, dct):
        commands = dct.get('commands', [])

        for member_name, member_value in dct.items():
            if getattr(member_value, '_is_cmd', False):
                commands.append(Command(name=member_name,
                                        impl=member_value))

        dct['commands'] = commands
        return super(CommandsMeta, cls).__new__(cls, name, bases, dct)
