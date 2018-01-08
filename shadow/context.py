# store some config and context


class Context(object):
    out_protocol_stack = []
    in_protocol_stack = []
    out_host = b'127.0.0.1'
    # out_host = None
    out_port = 3343
    # out_port = None
    logger = None
    password = b'explorer'


context = Context()
