from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logger

logging = logger.Logger(__file__)
import time

from PyQt5.QtCore import QThread, pyqtSignal, QObject


from Core.fileUtilities import *
from Core.fileReader import *


class DataFileWatchdog(FileSystemEventHandler, QObject):
    changeSignal = pyqtSignal(str, str, str)
    def __init__(self):
        super().__init__()


    def on_created(self, event):
        print("Working", event)
        fname = event.src_path.split(os.sep)[-1]
        path = os.path.dirname(event.src_path)
        self.changeSignal.emit('created', fname, path)

    def on_modified(self, event):
        print("Working", event)
        fname = event.src_path.split(os.sep)[-1]
        path = os.path.dirname(event.src_path)
        channel = fname[:-len(SUFFIX_FORMAT)].strip(' _')
        date = fname[-len(SUFFIX_FORMAT):][:-4]  # to get rid of the .log extension
        self.changeSignal.emit('modified', fname, path)



class Overseer(QThread):
    changeSignal = pyqtSignal(str, str, str)
    dataFileSelected = pyqtSignal(dict)
    def __init__(self, path = None, checkSimilar = False):
        super().__init__()
        if path is None or os.path.isdir(path):
            self.path = path
            self.dataFile = None
        else:
            self.path = os.path.dirname(path)
            self.dataFile = path[len(self.path):].strip(os.sep)
            path = self.path
        self.checkSimilar = checkSimilar

        self.dataFileWatchdog = DataFileWatchdog()
        self.dataFileWatchdog.changeSignal.connect(self.changeSignal)
        self.dataFileSelected.connect(self.changeDataFile)

        self.observer = Observer()
        self.schedule = None

        self.dataFileSelected.connect(self.changeDataFile)
        if path:
            self.schedule = self.observer.schedule(self.dataFileWatchdog, self.path,
                                                   recursive=False)
            logging.debug(f"Schedule: {str(self.schedule)}")

    def run(self):
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()

    def changeDataFile(self, change_dict):
        logging.debug("Changing Data File")
        if 'path' not in change_dict or 'checkSimilar' not in change_dict:
            logging.error(f"Invalid argument for Overseer.changeDataFile(): {str(change_dict)}")
            return
        df_path = change_dict['path']
        if os.path.isdir(df_path):
            path = df_path
            dataFile = None
        else:
            path = os.path.dirname(df_path)
            dataFile = df_path[len(path):].strip(os.sep)

        self.path = path
        self.dataFile = dataFile
        self.checkSimilar = change_dict['checkSimilar']
        self.observer.unschedule_all()
        self.schedule = self.observer.schedule(self.dataFileWatchdog, path, recursive=False)

        logging.debug(f"Changed path to {self.path}")


if __name__ == "__main__":
    from PyQt5.QtWidgets import QMainWindow, QTextEdit, QVBoxLayout, QWidget, QApplication
    test_path = r"C:\Users\zberks\OneDrive - McGill University\G2 Lab\Fridges\BlueFors Fridge\Data\24F1"
    new_path = r"C:\Users\zberks\OneDrive - McGill University\G2 Lab\Fridges\BlueFors Fridge\Data\24G1"
    import sys
    class MainThread(QThread):
        mainSignal = pyqtSignal(str, str, str)
        dataFileChanged = pyqtSignal(dict)
        def __init__(self):
            super().__init__()
            self.overseer = Overseer(test_path)
            self.overseer.changeSignal.connect(self.callback)
            self.dataFileChanged.connect(self.overseer.dataFileSelected)


        def run(self):
            self.overseer.run()
            while True:
                time.sleep(10)

        def stop(self):
            self.overseer.stop()
            self.overseer.wait()

        def callback(self, *args):
            print(args)
            self.mainSignal.emit(*args)


    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Watchdog and PyQt5 Integration")
            self.resize(800, 600)

            self.text_edit = QTextEdit()
            layout = QVBoxLayout()
            layout.addWidget(self.text_edit)

            container = QWidget()
            container.setLayout(layout)
            self.setCentralWidget(container)

            self.file_watcher_thread = MainThread()
            self.file_watcher_thread.mainSignal.connect(self.on_file_changed)
            self.file_watcher_thread.start()


            self.file_watcher_thread.dataFileChanged.emit({'path':new_path, 'checkSimilar':False})

        def on_file_changed(self, change, channel, date):
            logging.debug(f"{change}, {channel}, {date}")
            self.text_edit.append(f"File {change}: {date} {channel}")

        def closeEvent(self, event):
            self.file_watcher_thread.stop()
            event.accept()


    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())