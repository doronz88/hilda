def test_rebind_symbols(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    hilda_client.rebind_symbols()
    assert len(hilda_client.symbols) > 0
