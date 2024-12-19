import json
import os
import platform


def load_config():
    try:
        with open("config.json", "r") as base_config_file:
            config = json.load(base_config_file)
    except FileNotFoundError:
        raise FileNotFoundError("Base configuration file not found.")

    if platform.system() == "Windows" and os.path.exists("config.dev.json"):
        try:
            with open("config.dev.json", "r") as dev_config_file:
                dev_config = json.load(dev_config_file)
                config = always_merger.merge(config, dev_config)
        except FileNotFoundError:
            raise FileNotFoundError("Development configuration file not found.")

    return config


def validate_config(config):
    required_keys = ["directory_base", "log_files", "csv_url", "max_price", "expected_fields_count"]
    for key in required_keys:
        if key not in config:
            raise KeyError(f"Missing required configuration: {key}")
    if not isinstance(config["log_files"], list):
        raise TypeError("log_files must be a list of file paths")
    if not os.path.exists(config["directory_base"]):
        raise FileNotFoundError(f"Base directory does not exist: {config['directory_base']}")
