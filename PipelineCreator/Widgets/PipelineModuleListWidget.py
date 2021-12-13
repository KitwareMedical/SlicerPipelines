import qt
import ctk

from .SelectModulePopUp import SelectModulePopUp

class _PipelineModuleWidget(qt.QWidget):
  def __init__(self, parent=None, module=None):
    qt.QWidget.__init__(self, parent)

    self.parameters = module.GetParameters()
    self.module = module

    self._mainLayout = qt.QVBoxLayout(self)

    self._cbutton = ctk.ctkCollapsibleButton()
    self._mainLayout.addWidget(self._cbutton)
    self._cbutton.setText(self.module.GetName())
    self._cbutton.collapsed = False

    # hlayout of up/delete/down buttons and parameters
    hlayout = qt.QHBoxLayout()
    self._cbutton.setLayout(hlayout)

    # add up/delete/down buttons
    buttonVLayout = qt.QVBoxLayout()
    hlayout.addLayout(buttonVLayout)
    self._upButton = qt.QPushButton("↑")
    self._deleteButton = qt.QPushButton("X")
    self._downButton = qt.QPushButton("↓")
    buttonVLayout.addWidget(self._upButton)
    buttonVLayout.addWidget(self._deleteButton)
    buttonVLayout.addWidget(self._downButton)

    # add input/output labels and parameters
    moduleFormLayout = qt.QFormLayout()
    hlayout.addLayout(moduleFormLayout)
    self._inputTypeWidget = qt.QLineEdit(str(self.module.GetInputType()))
    self._inputTypeWidget.setReadOnly(True)
    moduleFormLayout.addRow("Input Type", self._inputTypeWidget)

    for tup in self.parameters:
      try:
        if len(tup) == 2: #name, ui
          name, param = tup
          moduleFormLayout.addRow(name, param.GetUI())
        elif len(tup) == 3: #name, label, ui
          _, label, param = tup
          moduleFormLayout.addRow(label, param.GetUI())
      except Exception as e:
        raise Exception ("Exception trying to create parameter: '%s' for module '%s'\n    %s"
          % (tup[0], self.module.GetName(), str(e)))

    self._outputTypeWidget = qt.QLineEdit(str(self.module.GetOutputType()))
    self._outputTypeWidget.setReadOnly(True)
    moduleFormLayout.addRow("Output Type", self._outputTypeWidget)

  def setInputTypePalette(self, palette):
    self._inputTypeWidget.setPalette(palette)

  def setOutputTypePalette(self, palette):
    self._outputTypeWidget.setPalette(palette)

  @property
  def upClicked(self):
    return self._upButton.clicked

  @property
  def downClicked(self):
    return self._downButton.clicked

  @property
  def deleteClicked(self):
    return self._deleteButton.clicked


class PipelineModuleListWidget(qt.QWidget):
  modified = qt.Signal()

  def __init__(self, parent=None):
    qt.QWidget.__init__(self, parent)

    self._good = True
    self._availableModules = []
    self._moduleWidgets = []
    self._errorPalette = qt.QPalette()
    self._errorPalette.setColor(qt.QPalette.Base, qt.QColor(255, 128, 128))

    self._layout = qt.QVBoxLayout(self)

    insertButton = qt.QPushButton()
    insertButton.setText("Insert Module")
    insertButton.clicked.connect(lambda: self._onInsert())
    self._layout.addWidget(insertButton)

  def setAvailableModules(self, availableModules):
    self._availableModules = availableModules

  def moduleAt(self, index):
    return self._moduleWidgets[index].module

  def setErrorPalette(self, palette):
    self._errorPalette = palette
  def getErrorPalette(self):
    return self._errorPalette

  def getParameters(self, index):
    return self._moduleWidgets[index].parameters

  def getAllParameters(self):
    return [(m.module.GetName(), m.parameters) for m in self._moduleWidgets]

  def count(self):
    return len(self._moduleWidgets)

  def _checkGood(self):
    defaultPalette = qt.QLineEdit().palette
    badPalette = self._errorPalette

    self._good = True
    if self._moduleWidgets:
      self._moduleWidgets[0].setInputTypePalette(defaultPalette)
      self._moduleWidgets[-1].setOutputTypePalette(defaultPalette)
      for curWidget, nextWidget in zip(self._moduleWidgets[:-1], self._moduleWidgets[1:]):
        match = curWidget.module.GetOutputType() == nextWidget.module.GetInputType()
        palette = defaultPalette if match else badPalette
        curWidget.setOutputTypePalette(palette)
        nextWidget.setInputTypePalette(palette)
        self._good = self._good and match

  def good(self):
    return self._good

  def emitModified(self):
    self._checkGood()
    self.modified.emit()

  def _onInsert(self):
    popUp = SelectModulePopUp(self._availableModules, self.getOutputType(), self)
    popUp.accepted.connect(lambda: self._onPopUpAccepted(popUp))
    popUp.open()

  def _onModuleMoveUp(self, pipelineModuleWidget):
    self._onModuleMove(pipelineModuleWidget, -1)

  def _onModuleMoveDown(self, pipelineModuleWidget):
    self._onModuleMove(pipelineModuleWidget, 1)

  def _onModuleMove(self, pipelineModuleWidget, movement):
    index = self._moduleWidgets.index(pipelineModuleWidget)
    if 0 <= index + movement < len(self._moduleWidgets):
      pipelineModuleWidget.hide()
      self._moduleWidgets.pop(index)
      self._moduleWidgets.insert(index + movement, pipelineModuleWidget)
      self._layout.removeWidget(pipelineModuleWidget)
      self._layout.insertWidget(index + movement, pipelineModuleWidget)
      pipelineModuleWidget.show()
      self.emitModified()

  def _onDeleteModule(self, pipelineModuleWidget):
    q = qt.QMessageBox()
    q.setWindowTitle("Deleting module")
    q.setText("Are you sure you want to delete module '%s'?" % pipelineModuleWidget.module.GetName())
    q.addButton(qt.QMessageBox.Yes)
    q.addButton(qt.QMessageBox.No)

    if q.exec() == qt.QMessageBox.Yes:
      pipelineModuleWidget.hide()
      self._layout.removeWidget(pipelineModuleWidget)
      self._moduleWidgets.remove(pipelineModuleWidget)
      # for some reason the buttonHolder is not getting deleted from memory
      # delete the parameters as a temp solution for some clean up of memory
      # In truth, the reason this is here is so the bridge parameters from the CLIModuleWrapping
      # get properly deleted, but this class shouldn't really know about that
      pipelineModuleWidget.parameters = None

      self.emitModified()

  def _onPopUpAccepted(self, popUp):
    module = popUp.chosenModule
    try:
      popUp.close()
      popUp.destroy()

      pipelineModuleWidget = _PipelineModuleWidget(module=module)
      pipelineModuleWidget.upClicked.connect(lambda: self._onModuleMoveUp(pipelineModuleWidget))
      pipelineModuleWidget.downClicked.connect(lambda: self._onModuleMoveDown(pipelineModuleWidget))
      pipelineModuleWidget.deleteClicked.connect(lambda: self._onDeleteModule(pipelineModuleWidget))

      self._layout.insertWidget(self._layout.count() - 1, pipelineModuleWidget)
      self._moduleWidgets.append(pipelineModuleWidget)
      self.emitModified()

    except Exception as e:
      print ("Exception trying add module: '%s'\n    %s"
        % (module.GetName(), str(e)))
      raise

  def clear(self):
    for moduleWidget in self._moduleWidgets:
      moduleWidget.hide()
      self._layout.removeWidget(moduleWidget)
    self._moduleWidgets.clear()
    self.emitModified()

  def getInputType(self):
    return self._moduleWidgets[0].module.GetInputType() if self._moduleWidgets else None

  def getOutputType(self):
    return self._moduleWidgets[-1].module.GetOutputType() if self._moduleWidgets else None
