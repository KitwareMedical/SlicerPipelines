import os
import qt
import ctk

class IntegerParameter(object):
  def __init__(self, value=None, minimum=None, maximum=None, singleStep=None, suffix=None):
    self._spinbox = qt.QSpinBox()
    if singleStep is not None:
      self._spinbox.setSingleStep(singleStep)
    if minimum is not None:
      self._spinbox.setMinimum(minimum)
    if maximum is not None:
      self._spinbox.setMaximum(maximum)
    if value is not None:
      self._spinbox.value = value
    if suffix is not None:
      self._spinbox.suffix = suffix

  def GetUI(self):
    return self._spinbox

  def GetValue(self):
    return self._spinbox.value

class FloatParameter(object):
  def __init__(self, value=None, minimum=None, maximum=None, singleStep=None, decimals=2, suffix=None):
    self._spinbox = qt.QDoubleSpinBox()
    self._spinbox.setDecimals(decimals)
    if singleStep is not None:
      self._spinbox.setSingleStep(singleStep)
    if minimum is not None:
      self._spinbox.setMinimum(minimum)
    if maximum is not None:
      self._spinbox.setMaximum(maximum)
    if value is not None:
      self._spinbox.value = value
    if suffix is not None:
      self._spinbox.suffix = suffix

  def GetUI(self):
    return self._spinbox

  def GetValue(self):
    return self._spinbox.value

class IntegerParameterWithSlider(object):
  """
  Creates a parameter for getting integer values conforming to the
  PipelineCreator's needs that has a UI of both a slider and a spinbox
  in a horizontal layout.
  """
  def __init__(self, value=None, minimum=None, maximum=None, singleStep=None, suffix=None):
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
    if suffix is not None:
      self._spinbox.suffix = suffix

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

class FloatParameterWithSlider(object):
  """
  Creates a parameter for getting float values conforming to the
  PipelineCreator's needs that has a UI of both a slider and a spinbox
  in a horizontal layout.
  """
  def __init__(self, value=None, minimum=None, maximum=None, singleStep=None, decimals=2, suffix=None):
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
    if suffix is not None:
      self._spinbox.suffix = suffix

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

class FloatRangeParameter(object):
  def __init__(self, minimumValue=None, maximumValue=None, minimum=None, maximum=None,
               singleStep=None, decimals=None, suffix=None):
    self._rangeWidget = ctk.ctkRangeWidget()
    #important to set minimum/maximum before minimumValue/maximumValue
    if minimum:
      self._rangeWidget.minimum = minimum
    if maximum:
      self._rangeWidget.maximum = maximum
    if minimumValue:
      self._rangeWidget.minimumValue = minimumValue
    if maximumValue:
      self._rangeWidget.maximumValue = maximumValue
    if singleStep:
      self._rangeWidget.singleStep = singleStep
    if decimals:
      self._rangeWidget.decimals = decimals
    if suffix:
      self._rangeWidget.suffix = suffix

  def GetUI(self):
    return self._rangeWidget
  def GetValue(self):
    return (self._rangeWidget.minimumValue, self._rangeWidget.maximumValue)

class SaveFileParameter(object):
  def __init__(self, caption="Save file", filter=None, selectedFilter=None):
    self._hlayout = qt.QHBoxLayout()
    self._lineEdit = qt.QLineEdit()
    self._browseButton = qt.QPushButton()
    self._browseButton.setText("Browse")
    self._browseButton.clicked.connect(self._onBrowse)

    self._directory = os.path.expanduser("~")

    if isinstance(filter, list) or isinstance(filter, tuple):
      filter = ';;'.join(filter)

    self._filter = filter or ''
    self._selectedFilter = selectedFilter or ''
    self._caption = caption

    self._hlayout.addWidget(self._lineEdit)
    self._hlayout.addWidget(self._browseButton)

  def _onBrowse(self):
    filename = qt.QFileDialog.getSaveFileName(self._lineEdit.parentWidget(),
      self._caption, self._directory,
      self._filter, self._selectedFilter)
    if filename:
      self._lineEdit.text = filename
      self._directory = os.path.dirname(filename)

  def GetUI(self):
    return self._hlayout

  def GetValue(self):
    return self._lineEdit.text

class OpenFileParameter(object):
  def __init__(self, caption="Open File", filter=None, selectedFilter=None):
    self._hlayout = qt.QHBoxLayout()
    self._lineEdit = qt.QLineEdit()
    self._browseButton = qt.QPushButton()
    self._browseButton.setText("Browse")
    self._browseButton.clicked.connect(self._onBrowse)

    self._directory = os.path.expanduser("~")

    if isinstance(filter, list) or isinstance(filter, tuple):
      filter = ';;'.join(filter)

    self._filter = filter or ''
    self._selectedFilter = selectedFilter or ''
    self._caption = caption

    self._hlayout.addWidget(self._lineEdit)
    self._hlayout.addWidget(self._browseButton)

  def _onBrowse(self):
    filename = qt.QFileDialog.getOpenFileName(self._lineEdit.parentWidget(),
      self._caption, self._directory,
      self._filter, self._selectedFilter)
    if filename:
      self._lineEdit.text = filename
      self._directory = os.path.dirname(filename)

  def GetUI(self):
    return self._hlayout

  def GetValue(self):
    return self._lineEdit.text
