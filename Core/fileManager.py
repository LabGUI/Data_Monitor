"""
Class that deals with log data
"""
from Core.fileMonitor import *

from PyQt5 import QtCore

class DataChannel:
    def __init__(self, fname, data_path=DATA_PATH):
        self.fname = fname
        self.fd = None

        self.labels = []
        self.data = []

        self.comments = None
        self.last_data = {}
        self.last_time = None
        self.start_time = None
        self.channels = []
        self.instruments = []
        self.parameters = []
        self.preamble = None

        self.data_path = data_path

    def reset(self):
        self.labels = []
        self.data = []

        self.last_data = {}
        self.last_time = None
        self.start_time = None
        self.channels = []
        self.instruments = []
        self.parameters = []
        self.preamble = None
        self.comments = None


    def update_path_information(self, fname):
        self.fname = fname

    def open(self, fname = None):
        self.close()
        if fname:
            self.update_path_information(fname)
        self.reset()
        self.fd = open(os.path.join(self.data_path, self.fname), 'r')

    def hardReset(self):
        self.close()
        self.open(self.fname)
        return self.update()

    def update(self):
        flines = [l.strip(' \t\r\n') for l in self.fd.readlines()]# if l[-1] == '\n']
        if len(flines) == 0:
            return None, None

        processed, comments = process_data_file_lines(flines)
        if self.comments is None:
            if len(comments) == 0:
                logging.error(f"Invalid datafile {self.fname}, please reset. Will continue anyways using indices")
            self.comments = comments

        data, self.start_time, self.channels, self.instruments, self.parameters, self.preamble = process_data_file_rows(processed, self.comments)

        self.labels = [(ch, instr, param) for ch, instr, param in zip(self.channels, self.instruments, self.parameters)]
        self.data += (list(data.items()))
        if len(self.data) > MAXIMUM_DATAPOINT_HISTORY:
            self.data = self.data[-MAXIMUM_DATAPOINT_HISTORY:]

        last_time, last_data = get_last_entry(data)
        if last_time is None or last_data is None:
            return self.last_time, self.last_data

        self.last_time = last_time
        self.last_data = last_data
        return self.last_time, self.last_data

    def close(self):
        if self.fd:
            self.fd.close()
            self.fd = None

    def export(self):
        return {
            'data':self.data, # Can simply convert it to a dict
            'start_time':self.start_time,
            'channels':self.channels,
            'instruments':self.instruments,
            'parameters':self.parameters,
            'preamble':self.preamble,
            'labels':self.labels
        }

    def __del__(self):
        self.close()




class DummyFileManager(QThread):
    processedChanges = QtCore.pyqtSignal(dict)
    allData = QtCore.pyqtSignal(dict)
    dataFileSelected = QtCore.pyqtSignal(dict)
    dataFileChanged = QtCore.pyqtSignal(dict)
    def __init__(self, data_path=DATA_PATH):
        super().__init__()
        self.dataChannels = {}
        self.overseer = Overseer()
        self.overseer.changeSignal.connect(self.changeDetected)
        #self.dataFileSelected.connect(self.overseer.dataFileSelected)
        self.dataFileSelected.connect(self.dataFileSelectedCallback)
        self.latest_log_files = {} #load_all_possible_log_files(log_path)

        self.last_emitted_changes = {}
        self.most_recent_changes = {}

        self.changes_read = {}

        self.path = None

        if data_path:
            self.setDataFile(data_path)

    def dataFileSelectedCallback(self, change_dict):
        if 'path' in change_dict and self.path != change_dict['path']:
            self.overseer.dataFileSelected.emit(change_dict)
            self.setDataFile(change_dict['path'])

    def setDataFile(self, path):
        # Unset most recent
        logging.debug(f"Setting path to {path} in FileManager")
        self.path = path
        previous_fnames = list(self.dataChannels.keys())
        for prfname in previous_fnames:
            prdch = self.dataChannels.pop(prfname)
            del prdch
        # Find similar ones
        mainfname = path.split(os.sep)[-1]
        data_path = os.path.dirname(path)
        fnames = find_all_similar_data_files(mainfname, data_path=data_path)
        # Add new ones
        for fname in fnames:
            self.dataChannels[fname] = DataChannel(fname, data_path=data_path)
            self.dataChannels[fname].open()
            self.dataChannels[fname].update()

        # Add all new files and changes to queue
        # TODO: Figure out way to emit all recent changes, might be better to do in main thread after




    def emitData(self):
        self.allData.emit(self.dumpData())

    def dumpData(self):
        return {fname:ch.export() for fname, ch in self.dataChannels.items()}

    def run(self):
        self.overseer.start()
        while True:
            logging.debug("Looping")
            if len(self.changes_read.keys()) > 0:
                logging.debug("Pending changes emitting")
                self.last_emitted_changes = self.changes_read
                self.changes_read = {}
                self.processedChanges.emit(self.last_emitted_changes)
                self.most_recent_changes.update(self.last_emitted_changes)
            time.sleep(CHANGE_PROCESS_CHECK)

    def stop(self):
        self.overseer.stop()
        self.overseer.join()

    def __del__(self):
        pass

    def changeDetected(self, change, fname, path):
        if self.path is None: # THeres nothing to do just skip
            logging.debug("Change detected before start")
            return

        # This works for created too!
        if fname not in self.dataChannels:
            similar_fnames = find_all_similar_data_files(self.path, None)
            if fname in similar_fnames:
                print(f"Monitoring new datafile that is similar: {fname} at {path} ")
                self.dataChannels[fname] = DataChannel(fname, data_path=path)
            else:
                return
        if change == 'modified': # At this point, fname should be in dataChannels
            if not self.dataChannels[fname].fd:
                self.dataChannels[fname].open()
            time, data = self.dataChannels[fname].update()
            if fname not in self.changes_read:
                self.changes_read[fname] = {}
            self.changes_read[fname].update({time:data})


    def currentStatus(self):
        return {fname: (ch.last_time, ch.last_data) for fname, ch in self.dataChannels.items()}

    def mostRecentChanges(self):
        return self.most_recent_changes


class FileManager(QThread):
    processedChanges = QtCore.pyqtSignal(dict)
    allData = QtCore.pyqtSignal(dict)
    def __init__(self, log_path=DATA_PATH):
        super().__init__()
        self.logChannels = {}
        self.overseer = Overseer()
        self.overseer.changeSignal.connect(self.changeDetected)
        self.latest_log_files = load_all_possible_data_files(log_path)
        for channel, date in self.latest_log_files.items():
            if channel in CHANNEL_BLACKLIST:
                continue
            self.logChannels[channel] = DataChannel(channel, log_path)
            self.logChannels[channel].open(date)
            self.logChannels[channel].update()
            self.logChannels[channel].close()

        self.last_emitted_changes = {}
        self.most_recent_changes = {}

        self.changes_read = {}

    def emitData(self):
        self.allData.emit(self.dumpData())

    def dumpData(self):
        return {ch:lc.data for ch,lc in self.logChannels.items()}
    def run(self):
        self.overseer.start()
        while True:
            logging.debug("Looping")
            if len(self.changes_read.keys()) > 0:
                logging.debug("Pending changes emitting")
                self.last_emitted_changes = self.changes_read
                self.changes_read = {}
                self.processedChanges.emit(self.last_emitted_changes)
                self.most_recent_changes.update(self.last_emitted_changes)
            time.sleep(CHANGE_PROCESS_CHECK)

    def stop(self):
        self.overseer.stop()
        self.overseer.join()

    def __del__(self):
        for channel, logChannel in self.logChannels.items():
            logChannel.close()

    def changeDetected(self, change, channel, date):
        logging.debug("Change detected")
        if channel not in self.logChannels:
            logging.error(f"Channel {channel} not found in log channels")
            return
        if self.logChannels[channel].date != date:
            self.logChannels[channel].update_path_information(date)
        if not self.logChannels[channel].fd:
            self.logChannels[channel].open()
        time, data = self.logChannels[channel].update()
        if channel not in self.changes_read:
            self.changes_read[channel] = {}
        self.changes_read[channel].update({time:data})

    def currentStatus(self):
        return {ch: (lc.last_time, lc.last_data) for ch, lc in self.logChannels.items()}

    def mostRecentChanges(self):
        return self.most_recent_changes


if __name__ == "__main__":
    from PyQt5.QtWidgets import QMainWindow, QTextEdit, QVBoxLayout, QWidget, QApplication
    import sys


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

            self.file_watcher_thread = FileManager()
            self.file_watcher_thread.processedChanges.connect(self.on_processed_changed)
            self.file_watcher_thread.start()

            self.data = (self.file_watcher_thread.dumpData())

        def on_processed_changed(self, change_dict):
            #print(change_dict)
            self.text_edit.append(str(change_dict))

        def closeEvent(self, event):
            self.file_watcher_thread.stop()
            self.file_watcher_thread.join()
            event.accept()


    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())