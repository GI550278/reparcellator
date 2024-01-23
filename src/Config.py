import os
import sys
import yaml


class Config:
    def __init__(self):
        self.application_path = None
        if getattr(sys, 'frozen', False):
            self.application_path = os.path.dirname(os.path.dirname(sys.executable))
        elif __file__:
            self.application_path = os.path.dirname(os.path.dirname(__file__))
        else:
            print('Cannot find application path')
            return

        config_file = self.application_path + '/config.yml'
        self.params = {}
        if not os.path.exists(config_file):
            print('Config file missing: ' + config_file)
        else:
            with open(config_file, 'r') as file:
                self.params = yaml.safe_load(file)


config = Config()