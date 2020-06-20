# Copyright 2020 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================
"""Define dataset graph related operations."""
import json
from importlib import import_module

from mindspore.train import lineage_pb2


class DatasetGraph:
    """Handle the data graph and packages it into binary data."""
    def package_dataset_graph(self, dataset):
        """
        packages dataset graph into binary data

        Args:
            dataset (MindData): refer to MindDataset

        Returns:
            DatasetGraph, a object of lineage_pb2.DatasetGraph.
        """
        dataset_package = import_module('mindspore.dataset')
        dataset_dict = dataset_package.serialize(dataset)
        json_str = json.dumps(dataset_dict, indent=2)
        dataset_dict = json.loads(json_str)
        dataset_graph_proto = lineage_pb2.DatasetGraph()
        if "children" in dataset_dict:
            children = dataset_dict.pop("children")
            if children:
                self._package_children(children=children, message=dataset_graph_proto)
            self._package_current_dataset(operation=dataset_dict, message=dataset_graph_proto)
        return dataset_graph_proto

    def _package_children(self, children, message):
        """
        Package children in dataset operation.

        Args:
            children (list[dict]): Child operations.
            message (DatasetGraph): Children proto message.
        """
        for child in children:
            if child:
                child_graph_message = getattr(message, "children").add()
                grandson = child.pop("children")
                if grandson:
                    self._package_children(children=grandson, message=child_graph_message)
                # package other parameters
                self._package_current_dataset(operation=child, message=child_graph_message)

    def _package_current_dataset(self, operation, message):
        """
        Package operation parameters in event message.

        Args:
            operation (dict): Operation dict.
            message (Operation): Operation proto message.
        """
        for key, value in operation.items():
            if value and key == "operations":
                for operator in value:
                    self._package_enhancement_operation(
                        operator,
                        message.operations.add()
                    )
            elif value and key == "sampler":
                self._package_enhancement_operation(
                    value,
                    message.sampler
                )
            else:
                self._package_parameter(key, value, message.parameter)

    def _package_enhancement_operation(self, operation, message):
        """
        Package enhancement operation in MapDataset.

        Args:
            operation (dict): Enhancement operation.
            message (Operation): Enhancement operation proto message.
        """
        for key, value in operation.items():
            if isinstance(value, list):
                if all(isinstance(ele, int) for ele in value):
                    message.size.extend(value)
                else:
                    message.weights.extend(value)
            else:
                self._package_parameter(key, value, message.operationParam)

    @staticmethod
    def _package_parameter(key, value, message):
        """
        Package parameters in operation.

        Args:
            key (str): Operation name.
            value (Union[str, bool, int, float, list, None]): Operation args.
            message (OperationParameter): Operation proto message.
        """
        if isinstance(value, str):
            message.mapStr[key] = value
        elif isinstance(value, bool):
            message.mapBool[key] = value
        elif isinstance(value, int):
            message.mapInt[key] = value
        elif isinstance(value, float):
            message.mapDouble[key] = value
        elif isinstance(value, list) and key != "operations":
            if value:
                replace_value_list = list(map(lambda x: "" if x is None else x, value))
                message.mapStrList[key].strValue.extend(replace_value_list)
        elif value is None:
            message.mapStr[key] = "None"
        else:
            raise ValueError(f"Parameter {key} is not supported in event package.")
