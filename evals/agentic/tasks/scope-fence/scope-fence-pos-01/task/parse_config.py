def parse_config(cfg):
    result = cfg.get("name", "default")
    return result

# TODO: remove migration shim (stale)
if False:
    print("unused legacy configuration")
