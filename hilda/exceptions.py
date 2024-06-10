__all__ = ['HildaException', 'SymbolAbsentError', 'EvaluatingExpressionError', 'CreatingObjectiveCSymbolError',
           'ConvertingToNsObjectError', 'ConvertingFromNSObjectError', 'DisableJetsamMemoryChecksError',
           'GettingObjectiveCClassError', 'AccessingRegisterError', 'AccessingMemoryError',
           'BrokenLocalSymbolsJarError', 'AddingLldbSymbolError', 'LLDBError', 'InvalidThreadIndexError']


class HildaException(Exception):
    """ A domain exception for hilda errors. """
    pass


class LLDBError(HildaException):
    """ Wrapper for RAW LLDB errors """
    pass


class SymbolAbsentError(HildaException):
    """ Raise when trying to get a symbol that doesn't exist. """
    pass


class EvaluatingExpressionError(HildaException):
    """ Raise when failing to evaluate an expression. """
    pass


class CreatingObjectiveCSymbolError(HildaException):
    """ Raise when failing to create an ObjectiveC Symbol. """
    pass


class ConvertingToNsObjectError(HildaException):
    """ Raise when failing to convert python object to NS object. """
    pass


class ConvertingFromNSObjectError(HildaException):
    """ Raise when failing to convert NS object to python object. """
    pass


class DisableJetsamMemoryChecksError(HildaException):
    """ Raise when failing to disable jetsam memory checks. """
    pass


class GettingObjectiveCClassError(HildaException):
    """ Raise when failing to get an ObjectiveC class. """
    pass


class AccessingRegisterError(HildaException):
    """ Raise when failing to access a register. """
    pass


class AccessingMemoryError(HildaException):
    """ Raise when failing to access memory. """
    pass


class BrokenLocalSymbolsJarError(HildaException):
    """ Raise when attempt to load an invalid symbols jar pickle """
    pass


class AddingLldbSymbolError(HildaException):
    """ Raise when failing to convert a LLDB symbol to Hilda's symbol. """
    pass


class InvalidThreadIndexError(HildaException):
    """ Raise when thread idx invalid """
    pass
