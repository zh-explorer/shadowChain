# store some config and context


class Context(object):
    logger = None
    main_loop = None
    sock_pool = None
    pool_max_size = 50
    pool_size = 0

    password = None

    out_protocol_stack = []
    first_client = 0
    target_host = None
    target_port = None

    in_protocol_stack = []
    server_host = None
    server_port = None

    is_reverse_server = False
    is_reverse_client = False

    time_out = 30

context = Context()
