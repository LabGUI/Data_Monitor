import os
from localvars import *
from datetime import datetime



def find_all_similar_data_files(data_file, data_path = DATA_PATH):
    """
    Given some data file (eg datafile.dat), will return all files in data_path that are named similarly, eg:
    in folder: [datafile.dat, datafile_001.dat datafile_123.dat, anotherdatafile.dat, datafile_test.dat]
    will return:
        datafile.dat
        datafile_001.dat
        datafile_123.dat
        datafile_test.dat

    """
    if os.sep in data_file:
        data_path = os.path.dirname(data_file)
        data_file = data_file.split(os.sep)[-1]
    if data_path is None:
        data_path = '.'

    if not os.path.isfile(os.path.join(data_path, data_file)):
        return []

    data_files = load_all_possible_data_files(data_path)
    # To find similar datafiles, the "similar" datafile will differ just by trailing numbers
    ext = data_file.split('.')[-1]
    if ext == data_file:
        ext = ''

    df_similar = data_file[:-(len(ext)+1)].rstrip("0123456789") if ext != '' else data_file.rstrip("0123456789")
    return [f for f in data_files if f[:len(df_similar)] == df_similar]

def load_all_possible_data_files(data_path = DATA_PATH):
    return [f for f in os.listdir(data_path) if os.path.isfile(os.path.join(data_path, f))]


if __name__ == "__main__":
    data_path = r"C:\Users\zberks\OneDrive - McGill University\G2 Lab\Fridges\BlueFors Fridge\Data\24G1"
    print(find_all_similar_data_files(
        '150624_CBM301_Conductance_SdH_001.dat',
        data_path
    ))

