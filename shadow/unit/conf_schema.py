schema = {
    "top_schema": {
        "definitions": {
            "protocol": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string"
                    }
                },
                "required": [
                    "name"
                ]
            },
            "protocols": {
                "type": "array",
                "items": {
                    "anyOf": [
                        {
                            "$ref": "#/definitions/protocol"
                        },
                        {
                            "type": "string"
                        }
                    ]
                }
            },
            "ip": {
                "type": "string",
                "format": "ipv4"
            },
            "port": {
                "type": "integer",
                "minimum": 1,
                "maximum": 65535
            }
        },
        "title": "shadow chain schema",
        "description": "use this to check the shadow chain conf is valid",
        "type": "object",
        "properties": {
            "out_protocol": {
                "$ref": "#/definitions/protocols"
            },
            "in_protocol": {
                "allOf": [
                    {
                        "$ref": "#/definitions/protocols"
                    },
                    {
                        "minItems": 1
                    }
                ]
            },
            "server_host": {
                "$ref": "#/definitions/ip"
            },
            "server_port": {
                "$ref": "#/definitions/port"
            },
            "password": {
                "type": "string"
            },
            "is_reverse_server": {
                "type": "boolean",
                "default": False
            },
            "is_reverse_client": {
                "type": "boolean",
                "default": False
            }
        },
        "required": [
            "in_protocol",
            "out_protocol",
            "server_host",
            "server_port"
        ]
    },
    "client_schema": {
        "definitions": {
            "ip": {
                "type": "string",
                "format": "ipv4"
            },
            "port": {
                "type": "integer",
                "minimum": 1,
                "maximum": 65535
            }
        },
        "description": "The client has addition host and port",
        "type": "object",
        "properties": {
            "name": {
                "type": "string"
            },
            "host": {
                "$ref": "#/definitions/ip"
            },
            "port": {
                "$ref": "#/definitions/port"
            }
        },
        "required": [
            "name",
            "host",
            "port"
        ]
    }
}
