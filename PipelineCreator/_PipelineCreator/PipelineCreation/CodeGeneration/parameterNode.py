import networkx as nx

from _PipelineCreator.PipelineCreation.CodeGeneration.util import CodePiece

from _PipelineCreator.PipelineCreation.util import (
    getStep,
)

from _PipelineCreator.PipelineCreation.CodeGeneration.util import (
    CodePiece,
    cleanupImports,
    importCodeForTypes,
    typeAsCode,
)


def createParameterPack(name: str, step: int, pipeline: nx.DiGraph, tab: str=" "*4):
    # the overall input will be put in a parameterNodeWrapper
    params, _ = getStep(step, pipeline)

    imports = f'''
from slicer.parameterNodeWrapper import parameterPack
{importCodeForTypes(params, pipeline)}
'''
    code = f'''
@parameterPack
class {name}:'''.lstrip()

    for param in params:
        code += f"\n{tab}{param[2]}: {typeAsCode(pipeline.nodes[param]['datatype'])}"

    return CodePiece(imports=cleanupImports(imports), code=code)


def createParameterNode(name: str,
                        pipeline: nx.DiGraph,
                        tab: str = " "*4) -> CodePiece:
    inputsCode = createParameterPack(f"{name}Inputs", 0, pipeline, tab)
    outputsCode = createParameterPack(f"{name}Outputs", -1, pipeline, tab)

    imports = "\n".join([
        inputsCode.imports,
        outputsCode.imports,
        "from slicer.parameterNodeWrapper import parameterNodeWrapper",
    ]) + "\n" 

        # code
    code = f'''
#
# {name}Inputs
#

{inputsCode.code}


#
# {name}Outputs
#

{outputsCode.code}


#
# {name}ParameterNode
#

@parameterNodeWrapper
class {name}ParameterNode:
{tab}inputs: {name}Inputs
{tab}outputs: {name}Outputs
'''.strip()
    
    return CodePiece(imports, code)
