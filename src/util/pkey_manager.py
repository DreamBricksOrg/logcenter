import os
import re

class PKeyManager:
    def __init__(self, directory: str):
        self.directory = directory
        self._keys = self._load_keys()

    def _load_keys(self):
        keys = {}
        pattern = re.compile(r"^(\d{3})\.pem$")
        if not os.path.isdir(self.directory):
            return keys
        for filename in os.listdir(self.directory):
            match = pattern.match(filename)
            if match:
                index = int(match.group(1))
                try:
                    with open(os.path.join(self.directory, filename), "r") as f:
                        content = f.read()
                        keys[index] = content
                except Exception as e:
                    print(f"Could not read key file {filename}: {e}")
        return keys

    def get_content(self, index: int):
        return self._keys.get(index)
