import unittest
import pickle
from typing import Annotated


from _PipelineCreator.PipelineCreation.CodeGeneration.util import \
    annotatedAsCode, typeAsCode

from slicer.parameterNodeWrapper import Decimals, Default, Maximum, Minimum, SingleStep, WithinRange

class _SomeClass:
    pass

class PipelineCreatorGenerationUtilTest(unittest.TestCase):
    def test_cleanType(self) -> None:
        from _PipelineCreator.PipelineCreation.CodeGeneration.util import \
            typeAsCode
        self.assertEqual(typeAsCode(int), "int")
        self.assertEqual(typeAsCode(float), "float")
        self.assertEqual(typeAsCode(bool), "bool")
        self.assertEqual(typeAsCode(str), "str")
        self.assertEqual(typeAsCode(list[int]), "list[int]")
        self.assertEqual(typeAsCode(dict[str, int]), "dict[str, int]")
        self.assertEqual(typeAsCode(tuple[bool, float]), "tuple[bool, float]")
        self.assertEqual(typeAsCode(list[dict[tuple[str, int], list[bool]]]),
                         "list[dict[tuple[str, int], list[bool]]]")

        self.assertEqual(_SomeClass, eval(typeAsCode(_SomeClass)))

    def test_annotated_to_code(self) -> None:
        # unannotated should be the same as typeAsCode
        self.assertEqual(annotatedAsCode(int), typeAsCode(int))

        self.assertEqual(annotatedAsCode(Annotated[int, Minimum(0)]), "Annotated[int, Minimum(0)]")
        self.assertEqual(annotatedAsCode(Annotated[int, Maximum(20)]), "Annotated[int, Maximum(20)]")
        self.assertEqual(annotatedAsCode(Annotated[int, Default(100)]), "Annotated[int, Default(value=100, generator=None)]")
        self.assertEqual(annotatedAsCode(Annotated[int, Decimals(4)]), "Annotated[int, Decimals(value=4)]")
        self.assertEqual(annotatedAsCode(Annotated[int, SingleStep(4)]), "Annotated[int, SingleStep(value=4)]")
        self.assertEqual(annotatedAsCode(Annotated[int, WithinRange(10, 15)]), "Annotated[int, WithinRange(10, 15)]")
