import qt

class IntegerParameter(object):
  """
  Creates a parameter for getting integer values conforming to the
  PipelineCreator's needs that has a UI of both a slider and a spinbox
  in a horizontal layout.
  """
  def __init__(self, value=None, minimum=None, maximum=None, singleStep=None):
    self._hlayout = qt.QHBoxLayout()
    self._slider = qt.QSlider(qt.Qt.Horizontal)
    self._spinbox = qt.QSpinBox()
    if singleStep is not None:
      self._spinbox.setSingleStep(singleStep)
      self._slider.setSingleStep(singleStep)
    if minimum is not None:
      self._spinbox.setMinimum(minimum)
      self._slider.setMinimum(minimum)
    if maximum is not None:
      self._spinbox.setMaximum(maximum)
      self._slider.setMaximum(maximum)
    if value is not None:
      self._spinbox.value = value
      self._slider.value = value

    self._spinbox.valueChanged.connect(self._onSpinboxChanged)
    self._slider.valueChanged.connect(self._onSliderChanged)

    self._hlayout.addWidget(self._slider)
    self._hlayout.addWidget(self._spinbox)

  def _onSliderChanged(self):
    self._spinbox.value = self._slider.value

  def _onSpinboxChanged(self):
    self._slider.value = self._spinbox.value

  def GetUI(self):
    return self._hlayout

  def GetValue(self):
    return self._spinbox.value

class FloatParameter(object):
  """
  Creates a parameter for getting float values conforming to the
  PipelineCreator's needs that has a UI of both a slider and a spinbox
  in a horizontal layout.
  """
  def __init__(self, value=None, minimum=None, maximum=None, singleStep=None, decimals=2):
    self._hlayout = qt.QHBoxLayout()
    self._slider = qt.QSlider(qt.Qt.Horizontal)
    self._spinbox = qt.QDoubleSpinBox()
    self._spinbox.setDecimals(decimals)
    self._sliderMultiplier = 10**decimals
    if singleStep is not None:
      self._spinbox.setSingleStep(singleStep)
    if minimum is not None:
      self._spinbox.setMinimum(minimum)
      self._slider.setMinimum(minimum * self._sliderMultiplier)
    if maximum is not None:
      self._spinbox.setMaximum(maximum)
      self._slider.setMaximum(maximum * self._sliderMultiplier)
    if value is not None:
      self._spinbox.value = value
      self._slider.value = value * self._sliderMultiplier

    self._spinbox.valueChanged.connect(self._onSpinboxChanged)
    self._slider.valueChanged.connect(self._onSliderChanged)

    self._hlayout.addWidget(self._slider)
    self._hlayout.addWidget(self._spinbox)

  def _onSliderChanged(self):
    self._spinbox.value = self._slider.value / self._sliderMultiplier

  def _onSpinboxChanged(self):
    self._slider.value = self._spinbox.value * self._sliderMultiplier

  def GetUI(self):
    return self._hlayout

  def GetValue(self):
    return self._spinbox.value

class BooleanParameter(object):
  """
  Creates a parameter for getting boolean values conforming to the
  PipelineCreator's needs.
  """
  def __init__(self, defaultValue=False):
    self._checkbox = qt.QCheckBox("")
    self._checkbox.checked = defaultValue

  def GetUI(self):
    return self._checkbox

  def GetValue(self):
    return self._checkbox.checked

class StringComboBoxParameter(object):
  """
  Creates a parameter for getting a string value from a fixed set of string values.
  This class conforms to the PipelineCreator's needs.
  """
  def __init__(self, values):
    self._comboBox = qt.QComboBox()
    self._comboBox.addItems(values)

  def GetUI(self):
    return self._comboBox

  def GetValue(self):
    return self._comboBox.currentText
