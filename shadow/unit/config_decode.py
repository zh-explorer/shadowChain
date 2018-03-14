import json
import jsonschema
from ..context import context
from .. import protocols
from functools import partial
from .conf_schema import schema as schema_data

top_validator = None
client_validator = None


def extend_with_default(validator_class):
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        for property, subschema in properties.items():
            if "default" in subschema:
                instance.setdefault(property, subschema["default"])

        for error in validate_properties(
                validator, properties, instance, schema,
        ):
            yield error

    return jsonschema.validators.extend(
        validator_class, {"properties": set_defaults},
    )


def load_json(file_name):
    with open(file_name, 'r') as fp:
        data = fp.read()
    return json.loads(data)


def make_validator():
    global top_validator, client_validator
    top_schema, client_schema = schema_data["top_schema"], schema_data["client_schema"]
    default_validating = extend_with_default(jsonschema.Draft4Validator)
    top_validator = default_validating(top_schema, format_checker=jsonschema.FormatChecker())
    client_validator = default_validating(client_schema, format_checker=jsonschema.FormatChecker())


def load_conf(conf):
    top_validator.validate(conf)
    context.password = conf["password"].encode()
    context.is_reverse_server = conf["is_reverse_server"]
    context.is_reverse_client = conf["is_reverse_client"]
    context.server_host = conf['server_host']
    context.server_port = conf['server_port']

    first = True
    for protocol in conf['in_protocol']:
        if isinstance(protocol, str):
            protocol_name = protocol
            protocol_dict = None
        else:
            protocol_name = protocol['name']
            protocol_dict = protocol

        if protocol_name not in protocols.protocol_map:
            context.logger.error("protocol unknown")
            exit(-1)
        else:
            protocol_class_name = protocols.protocol_map[protocol_name]['server']
            if protocol_class_name is None:
                context.logger.error("%s do not have server protocol" % protocol_name)
                exit(-1)
            protocol_data = protocols.protocol_list[protocol_class_name]
            if first:
                if protocol_data['type'] != 'server':
                    context.logger.error("the first in protocol type must be server")
                    exit(-1)
                first = False
            factory = protocol_data['protocol_factory'](protocol_dict)
            context.in_protocol_stack.append(factory)

    first_client = True
    index = 0
    cache_host = None
    cache_port = None
    for protocol in conf['out_protocol']:
        if isinstance(protocol, str):
            protocol_name = protocol
            protocol_dict = None
        else:
            protocol_name = protocol['name']
            protocol_dict = protocol

        if protocol_name not in protocols.protocol_map:
            context.main_loop.error("protocol unknow")
            exit(0)
        else:
            protocol_class_name = protocols.protocol_map[protocol_name]['client']
            if protocol_class_name is None:
                context.logger.error("%s do not have server protocol" % protocol_name)
                exit(-1)
            protocol_data = protocols.protocol_list[protocol_class_name]
            if protocol_data['type'] == "base":
                factory = protocol_data['protocol_factory'](protocol_dict)
                context.out_protocol_stack.append(factory)
            elif protocol_data['type'] == 'client':
                client_validator.validate(protocol_dict)

                factory = protocol_data['protocol_factory'](protocol_dict)
                if first_client:
                    context.out_protocol_stack.append(factory)
                    context.first_client = index
                    first_client = False
                    cache_host = protocol_dict['host']
                    cache_port = protocol_dict['port']
                else:
                    factory = partial(factory, target_host=cache_host, target_port=cache_port)
                    context.out_protocol_stack.append(factory)
                    cache_host = protocol_dict['host']
                    cache_port = protocol_dict['port']
        index += 1

    context.target_host = cache_host
    context.target_port = cache_port


def load_conf_file(filename):
    make_validator()
    conf = load_json(filename)
    load_conf(conf)
