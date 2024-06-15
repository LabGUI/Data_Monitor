from PyQt5 import QtWidgets
from Core.fileManager import *

from PyQt5 import QtCore, QtWidgets, QtGui

from localvars import *
from Core.mailer import Mailer
from Core.fileManager import FileManager
from Core.monitorManager import MonitorManager

from GUI.collapsibleBox import CollapsibleBox
from GUI.monitorWidget import MonitorWidget
from GUI.monitorsWidget import MonitorsWidget
from GUI.activeMonitorsWidget import ActiveMonitorsWidget
from GUI.dataSelectionWidget import DataSelectionWidget

from GUI.consoleWidget import Printerceptor, ConsoleWidget
import sys
import json
sys.stdout = stdout = Printerceptor()
if sys.platform == 'win32':
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('labgui.monitor.app.1')
import logger

logging = logger.Logger(__file__)

import traceback


class MainApplication(QtWidgets.QMainWindow):
    monitorSignal = QtCore.pyqtSignal(dict)
    monitorChange = QtCore.pyqtSignal(dict)
    widgetResize = QtCore.pyqtSignal()
    def __init__(self, log_path=LOG_PATH):
        super().__init__()
        # Initialize the console widget and connect stdout to console to capture init prints
        self.consoleWidget = ConsoleWidget()
        stdout.printToConsole.connect(self.consoleWidget.printToConsole)

        self.fileManager = DummyFileManager(log_path)
        self.monitorsWidget = MonitorsWidget()
        self.monitorManager = MonitorManager(self)
        self.activeMonitorWidget = ActiveMonitorsWidget()
        self.dataSelectionWidget = DataSelectionWidget()


        self.mailer = Mailer(RECIPIENTS)
        self.values = self.fileManager.dumpData()


        if SEND_TEST_EMAIL_ON_LAUNCH:
            self.mailer.send_test(self.fileManager.currentStatus())

        self.monitorsWidget.init_ui(self.values)

        # connect file manager so we can process changes in monitorsWidget and check for alerts
        self.fileManager.processedChanges.connect(self.monitorsWidget.processChangesCallback)
        self.fileManager.processedChanges.connect(self.checkMonitors)
        # TODO: if adding plotting widget, make sure it sends changes there too

        # Connect monitorsWidget to activeMonitorsWidget
        self.monitorsWidget.monitorSignal.connect(self.monitorSignal)
        self.monitorSignal.connect(self.activeMonitorWidget.monitorSignal)
        self.monitorChange.connect(self.monitorsWidget.monitorChange)
        # Connect activeMonitorsWidget to monitorsWidget
        self.activeMonitorWidget.monitorChange.connect(self.monitorsWidget.monitorChange)

        # Connect monitorsWidget to here so we can actually set up monitors
        self.monitorSignal.connect(self.monitorSignalCallback)


        # Add icon
        self.setWindowIcon(QtGui.QIcon('Resources/LabGUI.png'))
        self.setWindowTitle("LabGUI Data Monitor")
        if DEBUG_MODE:
            self.setWindowTitle("LabGUI Data Monitor (DEBUG)")

        # TODO: Add resizing event captures!
        self.monitorsWidget.widgetResize.connect(self.widgetResize)
        self.activeMonitorWidget.widgetResize.connect(self.widgetResize)
        self.consoleWidget.widgetResize.connect(self.widgetResize)

        self.widgetResize.connect(self.resizeWidgets)



    def load_history(self, fname='history.monitor'):
        if os.path.exists(fname):
            with open(fname, 'r') as f:
                try:
                    monitorHistory = json.load(f)
                    self.activeMonitorWidget.importMonitors(monitorHistory)
                except Exception as e:
                    logging.warning(f"Cannot load monitor history: {str(e)}")

    def export_history(self, fname='history.monitor'):
        with open(fname, 'w') as f:
            monitorHistory = self.activeMonitorWidget.exportMonitors()
            if len(monitorHistory.keys()) > 0:
                json.dump(monitorHistory, f)

    def init_ui(self):
        ########### Create docks
        # dataSelectionWidget
        self.dock_dataSelectionWidget = QtWidgets.QDockWidget('Data File Selection')
        self.dock_dataSelectionWidget.setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        #self.dock_dataSelectionWidget.setWidget(self.dataSelectionWidget)
        self.dock_dataSelectionWidget.setContentsMargins(0, 0, 0, 0)

        # monitorsWidget
        self.dock_monitorsWidget = QtWidgets.QDockWidget('Monitors')
        self.dock_monitorsWidget.setFeatures(QtWidgets.QDockWidget.DockWidgetFloatable |
                 QtWidgets.QDockWidget.DockWidgetMovable)
        self.dock_monitorsWidget.setWidget(self.monitorsWidget)
        self.dock_monitorsWidget.setContentsMargins(0,0,0,0)


        # consoleWidget
        self.dock_consoleWidget = QtWidgets.QDockWidget('Console')
        self.dock_consoleWidget.setFeatures(QtWidgets.QDockWidget.DockWidgetFloatable |
                 QtWidgets.QDockWidget.DockWidgetMovable)
        self.dock_consoleWidget.setWidget(self.consoleWidget)
        self.dock_consoleWidget.setContentsMargins(0,0,0,0)

        # activeMonitorsWidget
        self.dock_activeMonitorWidget = QtWidgets.QDockWidget('Active Monitors')
        self.dock_activeMonitorWidget.setFeatures(QtWidgets.QDockWidget.DockWidgetFloatable |
                 QtWidgets.QDockWidget.DockWidgetMovable)
        self.dock_activeMonitorWidget.setWidget(self.activeMonitorWidget)
        self.dock_activeMonitorWidget.setContentsMargins(0,0,0,0)

        #self.addDockWidget(QtCore.Qt.DockWidgetArea.TopDockWidgetArea, self.dock_dataSelectionWidget)
        self.toolbar_dataSelectionWidget = QtWidgets.QToolBar()
        self.toolbar_dataSelectionWidget.addWidget(self.dataSelectionWidget)
        self.addToolBar(self.toolbar_dataSelectionWidget)
        # Add docks to main window
        if SPLIT_MONITOR_WIDGETS:
            # Monitor top left, Active monitor top right, Console bottom
            self.addDockWidget(QtCore.Qt.DockWidgetArea.TopDockWidgetArea, self.dock_monitorsWidget)
            self.addDockWidget(QtCore.Qt.DockWidgetArea.TopDockWidgetArea, self.dock_activeMonitorWidget)

            self.splitDockWidget(self.dock_monitorsWidget, self.dock_activeMonitorWidget, QtCore.Qt.Orientation.Horizontal)
            self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self.dock_consoleWidget)
        else:
            # Monitor bottom left, Active monitor right, Console bottom left
            self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_monitorsWidget)
            self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.dock_activeMonitorWidget)
            self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_consoleWidget)
            self.splitDockWidget(self.dock_monitorsWidget, self.dock_activeMonitorWidget, QtCore.Qt.Orientation.Horizontal)

            self.splitDockWidget(self.dock_monitorsWidget, self.dock_consoleWidget, QtCore.Qt.Orientation.Vertical)

        # deal with sizing:
        if FIX_CONSOLE_HEIGHT:
            size = self.consoleWidget.sizeHint() # fix it? idr why I had this
            self.consoleWidget.consoleTextEdit.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            self.consoleWidget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            self.dock_consoleWidget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        if FIX_ACTIVE_WIDTH:
            self.activeMonitorWidget.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)



    def init_threads(self):
        self.fileManager.start()

    def checkMonitors(self, obj):
        vals = self.monitorManager.checkMonitors(obj)
        triggered = (self.monitorManager.WhatMonitorsTriggered(vals))
        triggered_data = self.monitorManager.triggeredMonitorInfo(obj, triggered)
        if len(vals.items()) and len(triggered):
            logging.info(f"Alerts triggered: {', '.join([':'.join(x) if type(x) != str else x for x in triggered])}")
        # if len(vals.items()):
        #    print(vals)
        if len(triggered) > 0:
            print(f"Alerts triggered: {', '.join([':'.join(x) if type(x) != str else x for x in triggered])}")
            # print(triggered_data)
            self.mailer.send_alert(triggered_data, self.fileManager.currentStatus())

        # print(self.fileManager.mostRecentChanges())
        # print(self.fileManager.currentStatus())

    def monitorSignalCallback(self, obj):
        """
        This occurs when one of the monitor checkboxes are toggled
        :param obj: monitor object
        :return: None
        """

        if obj['active']:
            self.monitorManager.addMonitor(channel=obj['channel'], subchannel=obj['subchannel'], type=obj['type'], values=obj['values'], variables=obj['variables'])
            logging.info(f"Monitor {obj['monitor']} activated, (channel={obj['channel']}, subchannel={obj['subchannel']}, type={obj['type']}, values={obj['values']}, variables={obj['variables']})")
            print(f"Monitor {obj['monitor']} activated")
        else:
            self.monitorManager.removeMonitor(channel=obj['channel'], subchannel=obj['subchannel'])
            logging.info(f"Monitor {obj['monitor']} deactivated, (channel={obj['channel']}, subchannel={obj['subchannel']}, type={obj['type']}, values={obj['values']}, variables={obj['variables']})")
            print(f"Monitor {obj['monitor']} deactivated")


    def resizeWidgets(self):
        #print("resizeWidgets")
        #self.monitorsWidget.adjustSize()
        #self.activeMonitorWidget.adjustSize()
        self.adjustSize()

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        super().resizeEvent(a0)
        #self.monitorsWidget.adjustSize()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = MainApplication()
    w.init_ui()
    w.init_threads()
    w.load_history()
    w.show()
    exitcode = app.exec()
    w.export_history()
    sys.exit(exitcode)