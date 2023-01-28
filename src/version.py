import json

with open("version.json") as json_file:
    version_data = json.load(json_file)
    VERSION: str = version_data["version"]
