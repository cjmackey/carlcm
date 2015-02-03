
from .base import BaseModule

class DockerModule(BaseModule):
    def packages(self):
        return ['docker.io']
