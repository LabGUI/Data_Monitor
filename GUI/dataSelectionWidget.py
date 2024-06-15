from PyQt5 import QtCore, QtWidgets, QtGui
import localvars





class DataSelectionWidget(QtWidgets.QWidget):
    datafileSelected = QtCore.pyqtSignal(dict)  # Outgoing
    datafileChanged = QtCore.pyqtSignal(dict)   # Possible incoming
    def __init__(self):
        super().__init__()

        self.main_layout = QtWidgets.QHBoxLayout()

        self.monitorSimilarCheckbox = QtWidgets.QCheckBox()
        self.monitorSimilarLabel = QtWidgets.QLabel('Monitor similar files?')
        self.filePath = QtWidgets.QLineEdit()
        self.filePath.setPlaceholderText("Select a file")
        self.selectButton = QtWidgets.QPushButton("Browse")
        self.applyButton = QtWidgets.QPushButton("Apply")

        self.filePath.editingFinished.connect(self.filePathEditedCallback)
        self.selectButton.pressed.connect(self.selectCallback)
        self.applyButton.pressed.connect(self.applyCallback)

        self.applyButton.setEnabled(False)


        self.main_layout.addWidget(self.monitorSimilarLabel)
        self.main_layout.addWidget(self.monitorSimilarCheckbox)
        self.main_layout.addWidget(self.filePath)
        self.main_layout.addWidget(self.selectButton)
        self.main_layout.addWidget(self.applyButton)

        self.setLayout(self.main_layout)


    def set_current_datafile(self, current_value = None):
        self.filePath.setText(current_value)
        self.applyButton.setEnabled(True)


    def selectCallback(self):
        options = QtWidgets.QFileDialog.Options()
        file_name,_ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select Data File",
            "",
            "All Files (*);;Data Files (*.dat);;Text Files (*.txt)",
            options=options
        )
        # TODO: If monitoring multiple, need to make more of these input fields
        self.set_current_datafile(file_name)

    def applyCallback(self):
        self.datafileSelected.emit({
            'path':self.filePath.text(),
            'checkSimilar':self.monitorSimilarCheckbox.isChecked(),
        })
        if localvars.DEBUG_MODE:
            print("Selected data file: ",{
                'path':self.filePath.text(),
                'checkSimilar':self.monitorSimilarCheckbox.isChecked(),
            })
        self.applyButton.setEnabled(False)

    def filePathEditedCallback(self):
        self.applyButton.setEnabled(True)


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    ds = DataSelectionWidget()
    ds.show()
    sys.exit(app.exec())