import csv
import typing
import os
from copy import copy

import logging


class _IteratorParameterFileIterator(object):
    """
    Internal class used to iterate over the input rows
    """
    def __init__(self, rows: list[dict[str, str]]) -> None:
        self._rows = copy(rows)

    def __iter__(self):
        return self
    
    def __next__(self) -> dict[str, str]:
        if len(self._rows) == 0:
            raise StopIteration
        
        return self._rows.pop(0)
            

class IteratorParameterFile(object):
    """
    This class represents the inputs and outputs of the case iterator it can
        - read a set of parameters from a file
        - create a template for filling in parameters
        - verify if a give file is valid for the given parameters
        - iterate over the input parameters
    """
    def __init__(self,
                 inputs: dict[str, typing.Any],
                 inputFile: str = None,
                 ignores: list[str] = ['delete_intermediate_nodes']) -> None:
        self._inputs = inputs
        self._ignores = ignores
        self._headers = [f"{key}:{value.__name__}" for key, value in self._inputs.items() if key not in ignores]
        self._rows: list[dict[str, str]] = []

        if inputFile is not None:
            self._rows = self.readParameters(inputFile)

    def __iter__(self):
        return _IteratorParameterFileIterator(self._rows)

    def validate(self, fileName : str) -> bool:
        """Validates a file"""
        with open(fileName) as file:
            reader = csv.reader(file)
            headers = next(reader)
            headers = [header.split(":")[0] for header in headers]

            if not self._validate(headers):
                return False
        return True

    def _validate(self, fileHeaders: list[str]) -> bool:
        """Validates a set of headers against the given parameters, the headers need
        to include _at least_ all of the given parameters, headers are expected to
        be stripped of the type notation
        """
        inputNames = [key for key, value in self._inputs.items() if key not in self._ignores]
        print(f'InputNames : {inputNames}\nHeaders : {fileHeaders}')
        return all([value in fileHeaders for value in inputNames])

    def createTemplate(self, fileName: str):
        """Creates a template .csv file that can be used to drive the
        pipeline with the give parameters
        """
        with open(fileName, mode='w+') as file:
            writer = csv.writer(file)
            writer.writerow(self._headers)

    def readParameters(self, fileName: str) -> list[dict[str, str]]:
        """Reads all rows from a given input file, checks whether the file headers
        match the expected headers, extraneous headers will be ignored
        """
        parameters = []

        with open(fileName) as file:
            # Clean up the header row, accept either parameter name or parameter name (type) and strip the type
            reader = csv.reader(file)
            headers = next(reader)
            headers = [header.split(":")[0] for header in headers]

            if not self._validate(headers):
                print("The file does not satisfy all requested input parameters")
                return []

            for index, row in enumerate(reader):
                if len(row) != len(headers):
                    print(f'Missing parameters in row {index}')
                    continue
                else:
                    parameters.append({key: value for key, value in zip(headers, row)})

            self._rows = parameters

        return parameters
