from hilda.snippets import xpc


def test_from_xpc_object(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    xpc_object = hilda_client.evaluate_expression('''
        typedef void * xpc_object_t;
        typedef void * xpc_activity_t;
        typedef void (^xpc_activity_handler_t)(xpc_activity_t activity);
        extern xpc_object_t xpc_dictionary_create(const char * const *keys, const xpc_object_t *values, size_t);
        extern void xpc_activity_register(const char *, xpc_object_t criteria, xpc_activity_handler_t handler);
        extern void xpc_dictionary_set_int64(xpc_object_t xdict, const char *key, int64_t value);
        extern void xpc_dictionary_set_string(xpc_object_t xdict, const char *key, const char *string);

        xpc_object_t criteria = xpc_dictionary_create(NULL, NULL, 0);
        xpc_dictionary_set_int64(criteria, "Delay", 5);
        xpc_dictionary_set_int64(criteria, "GracePeriod", 1);
        xpc_dictionary_set_string(criteria, "Priority", "Utility");
        criteria;
    ''')
    assert xpc.from_xpc_object(xpc_object) == {'Delay': 5, 'Priority': 'Utility', 'GracePeriod': 1}
