# store some config and context


class Context(object):
    out_protocol_chains = []
    in_protocol_chains = []
    out_host = b'121.42.25.113'
    out_port = 3343
    logger = None
    password = b'explorer'


context = Context()
