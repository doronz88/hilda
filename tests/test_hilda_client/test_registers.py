import pytest

from hilda.exceptions import AccessingRegisterError


@pytest.mark.parametrize('register_name', ['x0', 'x28', 'w0', 'w28', 'sp', 'lr', 'pc'])
def test_register_dir(hilda_client, register_name: str):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    :param register_name: Register that suppose to appear in dir.
    """
    assert register_name in dir(hilda_client.registers)


def test_register_get(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    for i in range(29):
        register_name = f'x{i}'
        assert hilda_client.registers[register_name] == hilda_client.evaluate_expression(f'${register_name}')
        assert getattr(hilda_client.registers, register_name) == hilda_client.registers[register_name]

    for i in range(32):
        register_name = f'd{i}'
        assert hilda_client.registers[register_name] == hilda_client.evaluate_expression(f'${register_name}')
        assert getattr(hilda_client.registers, register_name) == hilda_client.registers[register_name]


def test_register_get_uppercase(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    assert hilda_client.registers.x0 == hilda_client.registers.X0
    assert hilda_client.registers.pc == hilda_client.registers.PC


def test_register_set(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    original_x0 = hilda_client.registers.x0
    hilda_client.registers.x0 = 1337
    assert hilda_client.registers.x0 == 1337
    hilda_client.registers['x0'] = 1338
    assert hilda_client.registers.x0 == 1338
    hilda_client.registers.x0 = original_x0
    hilda_client.registers.d0 = 133.7
    assert hilda_client.registers.d0 == 133.7


def test_register_set_uppercase(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    original_x0 = hilda_client.registers.x0
    hilda_client.registers['X0'] = 1339
    assert hilda_client.registers.x0 == 1339
    hilda_client.registers.x0 = original_x0


def test_get_register_error(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    with pytest.raises(AccessingRegisterError):
        hilda_client.registers.registerthatdoesntexist


def test_set_register_error(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    with pytest.raises(AccessingRegisterError):
        hilda_client.registers.registerthatdoesntexist = 2
