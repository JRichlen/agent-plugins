def validate_config(cfg):
    if "name" not in cfg:
        raise KeyError("config missing required key: name")
    return cfg
