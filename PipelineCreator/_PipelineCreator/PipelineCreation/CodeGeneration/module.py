from _PipelineCreator.PipelineCreation.CodeGeneration.util import CodePiece, valueAsCode

def createModule(name: str,
                 title: str,
                 categories: list[str],
                 dependencies: list[str],
                 contributors: list[str],
                 helpText: str,
                 acknowledgementText: str,
                 tab=" "*4) -> CodePiece:
    imports = """
from slicer.ScriptedLoadableModule import ScriptedLoadableModule
"""
    code = f'''#
# {name}
#

class {name}(ScriptedLoadableModule):
{tab}"""Uses ScriptedLoadableModule base class, available at:
{tab}https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
{tab}"""

{tab}def __init__(self, parent):
{tab}{tab}ScriptedLoadableModule.__init__(self, parent)
{tab}{tab}self.parent.title = {valueAsCode(title)}
{tab}{tab}self.parent.categories = {valueAsCode(categories)}
{tab}{tab}self.parent.dependencies = {valueAsCode(dependencies)}
{tab}{tab}self.parent.contributors = {valueAsCode(contributors)}
{tab}{tab}self.parent.helpText = {valueAsCode(helpText)}
{tab}{tab}self.parent.acknowledgementText = {valueAsCode(acknowledgementText)}
'''.lstrip()

    return CodePiece(imports, code)
