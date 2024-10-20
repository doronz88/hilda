from datetime import datetime
from typing import Any, Union

import inquirer3
from inquirer3.themes import GreenPassion

CfSerializable = Union[
    dict[str, Any], list, tuple[Any, ...], str, bool, float, bytes, datetime, None]


def selection_prompt(options_list: list):
    question = [inquirer3.List('choice', message='choose device', choices=options_list, carousel=True)]
    result = inquirer3.prompt(question, theme=GreenPassion(), raise_keyboard_interrupt=True)
    return result['choice']
