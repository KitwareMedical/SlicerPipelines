import csv
import typing
import os
from copy import copy

import slicer.util

import logging


class _IteratorParameterFileIterator(object):
    """
    Internal class used to iterate over the input rows
    """
    def __init__(self, rows : list[dict[str, str]]) -> None:
        self._rows = copy(rows)

    def __iter__(self):
        return self
    
    def __next__(self) -> dict[str, str]:
        if len(self._rows) == 0:
            raise StopIteration
        
        return self._rows.pop(0)
            

class IteratorParameterFile(object):
    """
    This class represents the inputs and outputs of the caseiterator it can 
        - read a set of parameters from a file
        - create a template for filling in parameters
        - verify if a give file is valid for the given parameters 
        - create a file with the input parameters and their outputs
        - iterate over the input parameters
    """


    def __init__(self, inputs : dict[str, typing.Any], inputFile = None, outputs = None) -> None : 
        self._inputs = inputs
        self._outputs = outputs
        self._headers = [f"{key}:{value.__name__}" for key, value in self._inputs.items()]
        self._rows : list[dict[str, str]] = []

        if inputFile is not None:
            self._rows = self.readParameters(inputFile)

    def __iter__(self):
        return _IteratorParameterFileIterator(self._rows)

    def _validate(self, parameters : list[dict[str, typing.Any]]) -> list[dict[str, typing.Any]]:
        validParameters = []
        for parameter in parameters:
            valid = True
            for key, value in parameter.items():
                if "Node" in key:
                    if not os.path.isfile(value):
                        logging.warning(f"File {value} does not exist, skipping")
                        valid = False
                        break
                else:
                    pass
            
            if valid:
                validParameters.append(parameter)

        return validParameters


    def createTemplate(self, fileName : str) -> bool :
        with open(fileName, mode = "w+") as file:
            writer = csv.writer(file)
            writer.writerow(self._headers)

    def readParameters(self, fileName : str) -> list[dict[str, str]] :
        parameters = []

        with open(fileName) as file:
            # Clean up the header row, accept either parameter name or parameter name (type) and strip the type
            reader = csv.reader(file)
            headers = next(reader)
            headers = [header.split(":")[0] for header in headers]
            for row in reader:
                if len(row) != len(headers):
                    continue
                else:
                    parameters.append({key : value for key, value in zip(headers, row)})

            self._rows = parameters

        return parameters
    

