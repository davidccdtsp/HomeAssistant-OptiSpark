import json
import os


class ConfigurationService:
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ConfigurationService, cls).__new__(cls)
        return cls._instance

    def __init__(self, config_file=None):
        if config_file and not ConfigurationService._initialized:
            self.config_file = config_file
            self.config_data = self._load_config()
            ConfigurationService._initialized = True

    def _load_config(self):
        script_path = os.path.abspath(__file__)
        parent_dir = os.path.dirname(script_path)
        file_path = os.path.join(parent_dir, self.config_file)
        try:
            with open(file_path, "r") as file:
                return json.load(file)
        except FileNotFoundError:
            print(f"Error: The configuration file {self.config_file} was not found.")
            return {}
        except json.JSONDecodeError:
            print(
                f"Error: The configuration file {self.config_file} is not a valid JSON."
            )
            return {}

    def get(self, path):
        if not ConfigurationService._initialized:
            raise Exception("ConfigurationService must be initialized with a config file before use.")

        keys = path.split('.')
        data = self.config_data
        for key in keys:
            data = data.get(key, {})
            if data == {}:
                break
        return data


config_service = ConfigurationService(config_file='./config/config.json')