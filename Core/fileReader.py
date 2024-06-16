# Similar to log file reader program, but with more specific use cases
from localvars import *
import os
from datetime import datetime
import logger
logging = logger.Logger(__file__)

class DataFile:
    def __init__(self, name, data, start_time, channels, instruments, parameters, preamble, data_path):
        self.name = name
        self.data = data
        self.start_time = start_time
        self.channels = channels
        self.instruments = instruments
        self.parameters = parameters
        self.preamble = preamble

        self.times = list(sorted(self.data.keys()))

        self.labels = [(ch,instr,param) for ch,instr,param in zip(channels, instruments, parameters)]

        self.data_path = data_path

    @classmethod
    def FromFile(cls, path):
        if not os.path.exists(path) or not os.path.isfile(path):
            return None
        name = path.split(os.sep)[-1]
        data, start_time, channels, instruments, parameters, preamble = read_data_file(path)
        return cls(name,data, start_time, channels, instruments, parameters, preamble, data_path=os.path.dirname(path))

    def getLastLine(self):
        if len(self.times) > 0:
            return {self.times[-1]:self.data[self.times[-1]]}, self.labels


def read_data_file(path):
    """
    They look like this:
    # Description: SdH local measurements of CBM301
    #Measurement: 4pt conductance
    #At 1mT B field offset
    #
    #PreAmp used with typical settings
    #Voltage divider 100kOhm and 100Ohm from LI1 to D, measuring with amplifier B to K, then M split between 1k resistor grounded and LI2 (gpib7)
    #
    #Iterator = Step for each field sweep iteration and hold time
    #C'dt(s)', 'X_CBM301(V)', 'Y_CBM301(V)', 'iX_CBM301(V)', 'iY_CBM301(V)', 'Field(T)', 'Step(#)'
    #I'TIME[].dt', 'SR830[GPIB0::11::INSTR].X', 'SR830[GPIB0::11::INSTR].Y', 'SR830[GPIB0::7::INSTR].X', 'SR830[GPIB0::7::INSTR].Y', 'IPS120[GPIB0::25::INSTR].Field', 'ITERATOR[DUMMY].Step'
    #P'dt', 'X', 'Y', 'X', 'Y', 'Field', 'Step'
    #T'1718477385.8619533'
    data  data  data  data  data  data
    data  data  data  data  data  data
    """

    with open(path, 'r') as f:
        flines = [l.strip(' \t\r\n') for l in f.readlines() if l[-1] == '\n']

    datalines, comments = process_data_file_lines(flines)
    data, start_time, channels, instruments, parameters, preamble = process_data_file_rows(datalines, comments) # Always want this form
    return data, start_time, channels, instruments, parameters, preamble




def process_data_file_lines(lines):
    """
    process raw lines from the file into an array with a time stamp and converted values (int/float/etc)

    :param lines: array of lines read directly from file
    :param channel: log file channel
    :param date: date
    :return: array of lines in proper formats
    """
    processed = []
    comments = []
    datalines = []
    for line in lines:
        if line[0] == '#':
            comments.append(line[1:])
        else:
            datalines.append(line)

    for line in datalines:
        try:
            values = line.strip('\n').split(DATAFILE_DELIMITER)
            values = [float(x) for x in values]
            processed.append(values)
        except ValueError as e:
            logging.error("Read error occured: "+str(e))

    return processed, comments

def process_data_file_rows(processed, comments):
    """

    :param channel: log file channel
    :param processed: processed lines of the file
    :return: {} processed rows
    """
    data = {}
    channels = []
    instruments = []
    parameters = []
    preamble = ""
    start_time = None

    for comment in reversed(comments):
        if comment[0:2] == "T'" and comment[-1] == "'" and start_time is None:
            start_time = float(comment[1:].strip("'"))
        elif comment[0:2] == "C'" and comment[-1] == "'" and len(channels) == 0:
            channels = [ch.strip("' ") for ch in comment[1:].split(',')]
        elif comment[0:2] == "P'" and comment[-1] == "'" and len(parameters) == 0:
            parameters = [ch.strip("' ") for ch in comment[1:].split(',')]
        elif comment[0:2] == "I'" and comment[-1] == "'" and len(instruments) == 0:
            instruments = [ch.strip("' ") for ch in comment[1:].split(',')]
        else:
            preamble = comment.strip(' \n') + f"\n{preamble}"


    if start_time is None or len(channels) == 0 or len(instruments) == 0 or len(parameters) == 0:
        logging.error("Invalid datafile found, returning nothing")
        return None, None, None, None, None, None
    try:
        time_idx = [i.split('.')[0] for i in instruments].index('TIME[]') # This is the time instrument
    except ValueError:
        time_idx = None
        logging.warning("Found datafile without time idx, using iterator instead")

    for i,datarow in enumerate(processed):
        t = i
        if time_idx:
            t = datarow[time_idx]
            if t < start_time: # This is the case when using dt, so we need to add to get current time
                t = t + start_time

        row_obj = {
            (ch,instr,param):val
            for ch,instr,param,val in zip(channels, instruments, parameters, datarow)
        }
        data[t] = row_obj

    return data, start_time, channels, instruments, parameters, preamble


def get_last_entry(data):
    """
    Determines last entry from data/labels format
    """
    times = sorted(data.keys())
    if len(times) > 0:
        return times[-1], data[times[-1]]

if __name__ == "__main__":
    from tabulate import tabulate
    data, labels = read_data_file('Channels', '24-06-03')
    lf = DataFile.FromFile('Channels', '24-06-03')
    #data, label = lf.getLastLine()
    array = [[k] + list(v.values()) for k,v in data.items()]

    print(tabulate(array, headers=['time']+labels))

    print([v['void'] for k,v in data.items()])
