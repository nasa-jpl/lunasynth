#  Copyright (c) 2024. Jet Propulsion Laboratory. All rights reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
from pathlib import Path
from typing import Any

import yaml


class ConfigLoader:
    """Wrapper of yaml loading with support for !include directive and updates.

    1. Load yaml file with support for !include directive to include other yaml files.
    2. Optionally update the yaml data with a dictionary of updates.

    Usage:
    ```
    config = ConfigLoader('main.yaml', {'key1': 'value1', 'key2': 'value2'}) # dict style
    config = ConfigLoader('main.yaml', ['key1=value1', 'key2=value2']) # args style
    ```
    """

    def __init__(self, config_file: str, args_updates: list[str] | dict | None = None) -> None:
        """Load yaml file and optionally update the yaml data with a dictionary of updates.

        Args:
        ----
            config_file (str): Path to the yaml file.
            updates (dict, optional): Dictionary of updates to apply to the yaml data. Defaults to False.

        Returns:
        -------
            dict: The yaml data.

        """

        class LoaderWithInclude(yaml.SafeLoader):
            pass

        def yaml_include(loader: yaml.Loader, node: yaml.Node) -> dict:
            # Get the path out of the yaml file relative to the current yaml file
            parent_path = Path(loader.name).parent
            included_file_path = Path(parent_path, node.value)
            with open(included_file_path) as f:
                return yaml.load(f, LoaderWithInclude)

        self.config_file = config_file
        LoaderWithInclude.add_constructor("!include", yaml_include)
        with open(config_file) as f:
            config = yaml.load(f, LoaderWithInclude)

        if args_updates is not None:
            if isinstance(args_updates, list):
                args_updates = self.args_to_dict(args_updates)
            config = self.update_yaml(config, args_updates)
        self.config = config

    def args_to_dict(self, args: list[str]) -> dict[str, Any]:
        """Convert a list of arguments to a dictionary of updates.

        Args:
        ----
            args (list[str]): List of arguments in the form key=value.

        Returns:
        -------
            dict: Dictionary of updates.

        """
        updates: dict[str, Any] = {}
        for item in args:
            # check if item is in the form key=value
            if "=" not in item:
                print(f"Invalid argument: {item}")
                continue
            key, value = item.split("=", 1)

            # Convert value to appropriate type
            if value.startswith("[") and value.endswith("]"):
                value = value[1:-1].split(",")  # type: ignore[assignment]
                updates[key] = value
            elif value.lower() == "true":
                updates[key] = True
            elif value.lower() == "false":
                updates[key] = False
            elif value.isdigit():
                updates[key] = int(value)
            elif value.replace(".", "", 1).isdigit():
                updates[key] = float(value)
            else:
                # check if value is is a dictioanry
                if value.startswith("{") and value.endswith("}"):
                    updates[key] = yaml.safe_load(value)
                if value.lstrip().startswith("!include"):
                    local_included_file = value.split(" ")[1]
                    included_file = Path(self.config_file).parent / local_included_file
                    with open(included_file) as f:
                        updates[key] = yaml.safe_load(f)
                else:
                    updates[key] = value
        return updates

    def update_yaml(self, data: dict, updates: dict) -> dict:
        """Update yaml data with a dictionary of updates.

        Args:
        ----
            data (dict): The yaml data.
            updates (dict): Dictionary of updates to apply to the yaml data.

        Returns:
        -------
            dict: The updated yaml data.

        """
        for key, value in updates.items():
            keys = key.split(".")
            d = data
            for k in keys[:-1]:
                d = d.setdefault(k, {})
            d[keys[-1]] = value
        return data
