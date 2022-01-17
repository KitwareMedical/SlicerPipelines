import qt

class SelectModulePopUp(qt.QDialog):
  def __init__(self, availableModules, defaultInput=None, parent = None):
    qt.QDialog.__init__(self, parent)

    self._chosenModule = None
    self._availableModules = availableModules

    self.masterLayout = qt.QVBoxLayout()
    self.setLayout(self.masterLayout)
    self.resize(600,300)

    #title
    self.fontTitle = qt.QFont()
    self.fontTitle.setBold(True)
    self.fontTitle.setPointSize(14)
    self.lblTitle = qt.QLabel("Select Module")
    self.lblTitle.setFont(self.fontTitle)

    self.formLayout = qt.QFormLayout()

    #input type
    self.cboxInputType = qt.QComboBox()
    items = sorted(list(set([x.GetInputType() for x in self._availableModules])))
    self.cboxInputType.addItems(items)
    self.cboxInputType.currentTextChanged.connect(self._updateListWidget)
    self.formLayout.addRow("Input Type:", self.cboxInputType)

    #output type
    self.leOutputType = qt.QLineEdit()
    self.leOutputType.setReadOnly(True)
    self.formLayout.addRow("Output Type:", self.leOutputType)

    #list of modules for input type
    self.listWidget = qt.QListWidget()
    self.listWidget.itemClicked.connect(self._updateOutputType)

    #ok and cancel
    self.okButton = qt.QPushButton("OK")
    self.okButton.setEnabled(False)
    self.okButton.clicked.connect(lambda _: self.accept())
    self.cancelButton = qt.QPushButton("Cancel")
    self.cancelButton.clicked.connect(lambda _: self.reject())
    self.okCancelLayout = qt.QHBoxLayout()
    self.okCancelLayout.addWidget(self.okButton)
    self.okCancelLayout.addWidget(self.cancelButton)

    #double click is same as ok
    self.listWidget.itemDoubleClicked.connect(self._updateAndAccept)

    #put everything in the master layout
    self.masterLayout.addWidget(self.lblTitle)
    self.masterLayout.addLayout(self.formLayout)
    self.masterLayout.addWidget(self.listWidget)
    self.masterLayout.addLayout(self.okCancelLayout)

    verticalSpacer = qt.QSpacerItem(20, 40, qt.QSizePolicy.Minimum, qt.QSizePolicy.Expanding)
    self.masterLayout.addItem(verticalSpacer)

    #ui is ready. initialize state
    if defaultInput is not None:
      try:
        self.cboxInputType.setCurrentIndex(items.index(defaultInput))
      except ValueError:
        pass
    self._updateListWidget()

  def _updateListWidget(self):
    self.listWidget.clear()
    self.leOutputType.setText("")
    self.okButton.setEnabled(False)

    for module in [m for m in self._availableModules if m.GetInputType() == self.cboxInputType.currentText]:
      self.listWidget.addItem(module.GetName())

  def _updateOutputType(self):
    listItem = self.listWidget.currentItem()
    if listItem:
      modules = [m for m in self._availableModules if m.GetInputType() == self.cboxInputType.currentText]
      module = [x for x in modules if x.GetName() == listItem.text()][0]
      self.leOutputType.setText(module.GetOutputType())
      self._chosenModule = module
      self.okButton.setEnabled(True)
    else:
      self.leOutputType.setText("")

  def _updateAndAccept(self):
    self._updateOutputType()
    self.accept()


  @property
  def chosenModule(self):
    return self._chosenModule
