from string import Template

#
# ModuleTemplate
#
class ModuleTemplate(Template):
  """
  Custom template class with special syntax
  because CMake's variable syntax is the same
  as the default Template's replace syntax
  """
  delimiter = '{{'
  # only really want braced, but need both groups "named" and "braced" to exist
  pattern = r"""\{\{(?:
    (?P<escaped>\{) |
    (?P<named>[_a-z][_a-z0-9]*)}} |
    (?P<braced>[_a-z][_a-z0-9]*)}} |
    (?P<invalid>)
  )"""
