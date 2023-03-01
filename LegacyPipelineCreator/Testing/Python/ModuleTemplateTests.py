import unittest

from LegacyPipelineCreatorLib._Private.ModuleTemplate import ModuleTemplate

class TestModuleTemplate(unittest.TestCase):
  def test_simple(self):
    t = ModuleTemplate("{{name}} is here")
    self.assertEqual("frank is here", t.substitute({"name":"frank"}))
    self.assertEqual("frank is here", t.safe_substitute({"name":"frank"}))

  def test_missing(self):
    t = ModuleTemplate("{{greeting}}, {{name}}")
    with self.assertRaises(KeyError):
      t.substitute({"greeting":"hello"})
    self.assertEqual("hello, {{name}}", t.safe_substitute({"greeting":"hello"}))

  def test_escaped(self):
    t = ModuleTemplate("{{{ {{{{{{")
    self.assertEqual("{{ {{{{", t.substitute({}))
    self.assertEqual("{{ {{{{", t.safe_substitute({}))

if __name__ == '__main__':
    unittest.main()
