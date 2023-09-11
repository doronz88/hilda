from datetime import datetime
from typing import Any, List, Mapping, Tuple, Union

CfSerializable = Union[
    Mapping[str, Any], List, Tuple[Any, ...], str, bool, float, bytes, datetime, None]
