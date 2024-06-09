from datetime import datetime
from typing import Any, List, Mapping, Tuple, Union

import inquirer3
from inquirer3.themes import GreenPassion

CfSerializable = Union[
    Mapping[str, Any], List, Tuple[Any, ...], str, bool, float, bytes, datetime, None]


def selection_prompt(options_list: List):
    question = [inquirer3.List('choice', message='choose device', choices=options_list, carousel=True)]
    result = inquirer3.prompt(question, theme=GreenPassion(), raise_keyboard_interrupt=True)
    return result['choice']
