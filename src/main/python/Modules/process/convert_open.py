# -*- coding: utf-8 -*-

import sys

import numpy as np
import pickle
from io import BytesIO
import xml.etree.cElementTree as ET
import hashlib
import base64
import struct
import pickle
import traceback

from PyQt6.QtCore import (
    Qt, 
    QThread, 
    QRunnable, 
    pyqtSignal, 
    pyqtSlot, 
    QObject, 
)
from ..MVP import database as db
from ..widgets import popups

def mzdata2rpd(file_path, option):
    root = ET.ElementTree(file=file_path).getroot()
    # read first spectrum   ("discrete" or "continuous")
    spectrum = root.find("spectrumList")[0]
    spectrum_type = spectrum.find("spectrumDesc/spectrumSettings/acqSpecification").get("spectrumType")
    # mz
    mz_binary = spectrum.find("mzArrayBinary/data")
    mz_precision = mz_binary.get("precision")
    mz_endian = mz_binary.get("endian")
    # inten
    inten_binary = spectrum.find("intenArrayBinary/data")
    inten_precision = inten_binary.get("precision")
    inten_endian = inten_binary.get("endian")
    # set params
    if mz_endian == "little":       mz_e = "<"
    elif mz_endian == "big":        mz_e = ">"
    else:                           raise Exception(f"unsupported mz endian:{mz_endian}")
    if mz_precision == "32":        mz_p, mz_dtype = "f", np.float32
    elif mz_precision == "64":      mz_p, mz_dtype = "d", np.float64
    else:                           raise Exception(f"unsupported inten precision:{mz_precision}")
    if inten_endian == "little":    inten_e = "<"
    elif inten_endian == "big":     inten_e = ">"
    else:                           raise Exception(f"unsupported mz endian:{inten_endian}")
    if inten_precision == "32":     inten_p, inten_dtype = "f", np.int32
    elif inten_precision == "64":   inten_p, inten_dtype = "d", np.int64
    else:                           raise Exception(f"unsupported inten precision:{inten_precision}")

    # read all data
    N_scan = int(root.find("spectrumList").get("count"))
    mz_set_pre = [None for i in range(N_scan)]
    inten_set_pre = [None for i in range(N_scan)]
    spectrum_settings_list = [None for i in range(N_scan)]
    for i, spectrum in enumerate(root.find("spectrumList")):
        # spectrum description (RT etc.)
        spectrum_settings_list[i] = spectrum.find("spectrumDesc/spectrumSettings/spectrumInstrument")
        # mz
        mz_binary = spectrum.find("mzArrayBinary/data")
        mz_set_pre[i] = struct.unpack(f"{mz_e}{mz_binary.get('length')}{mz_p}", base64.b64decode(mz_binary.text))
        # inten
        inten_binary = spectrum.find("intenArrayBinary/data")
        inten_set_pre[i] = struct.unpack(f"{inten_e}{inten_binary.get('length')}{inten_p}", base64.b64decode(inten_binary.text))
    mz_set, inten_set = convert_2_ndarray2d(mz_set_pre, inten_set_pre, mz_dtype, inten_dtype)
    RT_list, RT_unit, spectrum_settings_dict = parse_spectrum_settings(spectrum_settings_list)
    # RPD
    rpd = db.RPD(
        data_hash = None,  # will be generated when saving file
        file_path = file_path, 
        spectrum_type = spectrum_type, 
        mz_set = mz_set, 
        inten_set = inten_set, 
        RT_list = RT_list, 
        RT_unit = RT_unit, 
        spectrum_settings_dict = spectrum_settings_dict, 
        # general_info
        ionization_type = root.find("description/instrument/source/cvParam").get("value"),      # Esi
        analyzer_type = root.find("description/instrument/analyzerList/analyzer/cvParam").get("value")   # TimeOfFlight
    )

    # RAPID 処理
    if option != "skip RAPID":
        raise Exception("not yet!")

    return rpd
def convert_2_ndarray2d(mz_set_pre, inten_set_pre, mz_dtype, inten_dtype):
    # prepare
    columns = max(map(lambda x: len(x), mz_set_pre))
    N_scan = len(mz_set_pre)
    mz_set = np.full((N_scan, columns), np.nan, dtype=mz_dtype)
    inten_set = np.zeros((N_scan, columns), dtype=inten_dtype)
    # fill values
    for r, (mz_data, inten_data) in enumerate(zip(mz_set_pre, inten_set_pre)):
        e = len(mz_data)
        mz_set[r, :e] = mz_data
        inten_set[r, :e] = inten_data
    return mz_set, inten_set
def parse_spectrum_settings(spectrum_settings_list):
    # read first scan
    spectrum_settings_dict = {cvParam.get("name"):cvParam.get("value") for cvParam in spectrum_settings_list[0]}
    RT_list = np.empty(len(spectrum_settings_list), dtype=float)
    RT_unit = "TimeInMinutes"
    del spectrum_settings_dict[RT_unit]
    # read all data
    for i, cvParam_list in enumerate(spectrum_settings_list):
        for cvParam in cvParam_list:
            if cvParam.get("name") == RT_unit:
                RT_list[i] = cvParam.get("value")
            else:
                assert cvParam.get("value") == spectrum_settings_dict[cvParam.get("name")]
    return RT_list, RT_unit, spectrum_settings_dict

def get_rpd_path(file_path, return_rpd):
    if (file_path.suffix == ".xml") and (file_path.with_suffix("").suffix == ".mzdata"):
        if return_rpd:
            rpd = mzdata2rpd(file_path, option="skip RAPID")
        rpd_path = file_path.with_suffix("").with_suffix(".rpd")
    else:
        raise Exception(f"unsupported file type\n{file_path}")
    # return
    if return_rpd:
        return rpd_path, rpd
    else:
        return rpd_path

def convert_file(file_path):
    rpd_path, rpd = get_rpd_path(file_path, return_rpd=True)
    # compress_test(rpd, file_path)
    # joblib.dump(rpd, rpd_path, compress=("lzma", 1))
    ######################
    # history of dumping #
    ######################
    # dump_2_2(rpd, rpd_path)
    dump_2_3(rpd, rpd_path)

def compress_test(rpd, file_path):
    import bz2
    import gzip
    import lzma
    import pickle
    import joblib
    import time

    # JOBLIB WAS MUCH FASTER

    t0 = time.time()
    joblib.dump(rpd, file_path.with_suffix(".jlgz3"), compress=("gzip", 3))
    t1 = time.time()# 52.2 MB
    print(t1 - t0)  # 1.7094099521636963

    t0 = time.time()
    joblib.dump(rpd, file_path.with_suffix(".jlgz2"), compress=("gzip", 2))
    t1 = time.time()# 52.9 MB
    print(t1 - t0)  # 1.491044282913208

    t0 = time.time()
    joblib.dump(rpd, file_path.with_suffix(".jlgz1"), compress=("gzip", 1))
    t1 = time.time()# 53.4 MB
    print(t1 - t0)  # 1.394075870513916

    t0 = time.time()
    joblib.dump(rpd, file_path.with_suffix(".jlxz3"), compress=("xz", 3))
    t1 = time.time()# 42.1 MB
    print(t1 - t0)  # 16.56401801109314

    t0 = time.time()
    joblib.dump(rpd, file_path.with_suffix(".jlxz2"), compress=("xz", 2))
    t1 = time.time()# 42.0 MB
    print(t1 - t0)  # 10.12470293045044

    t0 = time.time()
    joblib.dump(rpd, file_path.with_suffix(".jlxz1"), compress=("xz", 1))
    t1 = time.time()# 41.9 MB
    print(t1 - t0)  # 6.983075857162476

    t0 = time.time()
    joblib.dump(rpd, file_path.with_suffix(".jllzma3"), compress=("lzma", 3))
    t1 = time.time()# 42.1 MB
    print(t1 - t0)  # 15.50425386428833

    t0 = time.time()
    joblib.dump(rpd, file_path.with_suffix(".jllzma2"), compress=("lzma", 2))
    t1 = time.time()# 42 MB
    print(t1 - t0)  # 11.046019792556763

    t0 = time.time()
    joblib.dump(rpd, file_path.with_suffix(".jllzma1"), compress=("lzma", 1))
    t1 = time.time()# 41.9 MB
    print(t1 - t0)  # 7.345890045166016

    t0 = time.time()
    joblib.dump(rpd, file_path.with_suffix(".jlbz2_3"), compress=("bz2", 3))
    t1 = time.time()# 48.1 MB
    print(t1 - t0)  # 8.718559980392456

    t0 = time.time()
    joblib.dump(rpd, file_path.with_suffix(".jlbz2_2"), compress=("bz2", 2))
    t1 = time.time()# 48.3 MB
    print(t1 - t0)  # 8.404618978500366

    t0 = time.time()
    joblib.dump(rpd, file_path.with_suffix(".jlbz2_1"), compress=("bz2", 1))
    t1 = time.time()# 48.9 MB
    print(t1 - t0)  # 8.404618978500366

    t0 = time.time()
    joblib.dump(rpd, file_path.with_suffix(".jlzlib3"), compress=("zlib", 3))
    t1 = time.time()# 52.2 MB
    print(t1 - t0)  # 1.7587709426879883

    t0 = time.time()
    joblib.dump(rpd, file_path.with_suffix(".jlzlib2"), compress=("zlib", 2))
    t1 = time.time()# 52.9 MB?
    print(t1 - t0)  # 1.5617659091949463

    t0 = time.time()
    joblib.dump(rpd, file_path.with_suffix(".jlzlib1"), compress=("zlib", 1))
    t1 = time.time()# 0 MB?
    print(t1 - t0)  # 1.7587709426879883


    # SLOW
    t0 = time.time()
    with open(file_path.with_suffix(".pickle"), 'wb') as f:
        pickle.dump(rpd, f)
    t1 = time.time()# 76.6 MB
    print(t1 - t0)  # 0.029000043869018555

    with gzip.open(file_path.with_suffix(".gz"), "wb") as f:
        pickle.dump(rpd, f)
    t2 = time.time()# 50.5 MB
    print(t2 - t1)  # 42.234386920928955

    with bz2.BZ2File(file_path.with_suffix(".pbz2"), 'wb') as f:
        pickle.dump(rpd, f)
    t3 = time.time()# 47.5 MB
    print(t3 - t2)  # 10.061593055725098

    with lzma.open(file_path.with_suffix(".xz"), "wb") as f:
        pickle.dump(rpd, f)
    t4 = time.time()# 40.0 MB
    print(t4 - t3)  # 29.979784965515137

class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)
class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
    @pyqtSlot()
    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done
# use this class when the order of Worker, QThreadpook is important.
class WorkerResultsProcessor():
    def __init__(self):
        self.worker_produced_results = []
    def append_worker_produced_results(self, order, results):
        self.worker_produced_results.append([order, results])
    def thread_pool_finished(self, func):
        order = np.argsort([order for order, args in self.worker_produced_results])
        for i in order:
            func(*self.worker_produced_results[i][1])

def open_file(file_path):
    if file_path.suffix == ".rpd":
        # rpd, message = load_2_2(file_path)
        rpd, message = load_2_3(file_path)
    elif (file_path.suffix == ".xml") and (file_path.with_suffix("").suffix == ".mzdata"):
        raise Exception(f"Conversion to '.rpd' file is required to open '\n{file_path}'")
        rpd = mzdata2rpd(file_path, option="skip RAPID")
    else:
        raise Exception(f"unsupported file type\n{file_path}")
    return rpd, message

class InfoNoSave():
    magic_number = b"\x13RAPID" # fixed
    byteorder = "little"        # fixed
    header_info_len = 2         # fixed
    @classmethod
    def magic_number_size(cls):
        return len(cls.magic_number)
    @staticmethod
    def major_ver_size():
        return 1                # fixed
    @staticmethod
    def minor_ver_size():
        return 1                # fixed
    @staticmethod
    def generate_hash(header_mz_set_inten_set_no_compression_data_bytes):
        return hashlib.sha256(header_mz_set_inten_set_no_compression_data_bytes).hexdigest()
    @staticmethod
    def hash_size():
        return 64               # fixed: sha256
class Header():
    def __init__(self):
        self.major_ver = 2
        self.minor_ver = 3
        # introduced in v2.2
        self.mz_set_bytes_info_len = 10
        self.inten_set_bytes_info_len = 10
        self.no_compression_data_bytes_info_len = 5
        # introduced in v2.3
        self.mz_set_info_for_chromatogram_extraction_bytes_info_len = 5
class NoCompressionData():
    def __init__(
        self, 
        spectrum_type, 
        RT_list, 
        RT_unit, 
        spectrum_settings_dict, 
        ionization_type, 
        analyzer_type, 
        mz_set_nan_start_locs, 
    ):
        self.spectrum_type = spectrum_type
        self.RT_list = RT_list
        self.RT_unit = RT_unit
        self.spectrum_settings_dict = spectrum_settings_dict
        self.ionization_type = ionization_type
        self.analyzer_type = analyzer_type
        self.mz_set_nan_start_locs = mz_set_nan_start_locs  # [nan_start_rows, nan_start_cols]
    # pickle時に呼ばれる
    def __getstate__(self):
        state = self.__dict__.copy()
        # state['dd'] = dict(self.dd) # pickle 化できないものを変更可能
        return state
    # unpickle時に呼ばれる
    def __setstate__(self, state):
        self.__dict__.update(state)

def deep_diff(array2d, axis_list):
    initial_arrays = []
    for axis in axis_list:
        initial_arrays.append(array2d.take(indices=0, axis=axis))
        array2d = np.diff(array2d, axis=axis)
    return initial_arrays, array2d

from ..cython import rpd_calc

def revert_deep_diff(array2d, initial_arrays, axis_list):
    if len(initial_arrays) != len(axis_list):
        raise Exception(f"invalid")

    # import time
    # t0 = time.time()
    for initial_array, axis in zip(initial_arrays[::-1], axis_list[::-1]):
        # if (array2d.dtype == np.float64) and (axis == 0):
        #     array2d = rpd_calc.cumsum_2d_axis0_float64(np.vstack((np.expand_dims(initial_array, axis), array2d)))
        #     continue
        # elif (array2d.dtype == np.float64) and (axis == 1):
        #     array2d = rpd_calc.cumsum_2d_axis1_float64(np.hstack((np.expand_dims(initial_array, axis), array2d)))
        #     continue
        # elif (array2d.dtype == np.int32) and (axis == 0):
        #     array2d = rpd_calc.cumsum_2d_axis0_int32(np.vstack((np.expand_dims(initial_array, axis), array2d)))
        #     continue
        # elif (array2d.dtype == np.int32) and (axis == 1):
        #     array2d = rpd_calc.cumsum_2d_axis1_int32(np.hstack((np.expand_dims(initial_array, axis), array2d)))
        #     continue

        if axis == 0:
            array2d = np.cumsum(np.vstack((np.expand_dims(initial_array, axis), array2d)), axis=0, dtype=array2d.dtype)
        elif axis == 1:
            array2d = np.cumsum(np.hstack((np.expand_dims(initial_array, axis), array2d)), axis=1, dtype=array2d.dtype)
    # print(time.time() - t0)
    return array2d

def dump_2_2(rpd, rpd_path):
    """ 
    # KEYS TO SAVE
    # info
    self.data_hash

    # data
    self.spectrum_type
    self.mz_set
    self.inten_set

    # RT info and etc.
    self.RT_list
    self.RT_unit
    self.spectrum_settings_dict

    # general info
    self.ionization_type = ionization_type
    self.analyzer_type = analyzer_type

    # KEYS NO SAVE
        self.file_path
        self.N_scan
    """
    ##########
    # header #
    ##########
    header = Header()
    with BytesIO() as f:
        pickle.dump(header, f)
        f.seek(0)
        header_bytes = f.read()

    #######################
    # no_compression_data #
    #######################
    no_compression_data = NoCompressionData(
        spectrum_type = rpd.spectrum_type, 
        RT_list = rpd.RT_list, 
        RT_unit = rpd.RT_unit, 
        spectrum_settings_dict = rpd.spectrum_settings_dict, 
        ionization_type = rpd.ionization_type, 
        analyzer_type = rpd.analyzer_type, 
        mz_set_nan_start_locs = rpd.get_mz_set_nan_start_locs()
    )
    with BytesIO() as f:
        pickle.dump(no_compression_data, f)
        f.seek(0)
        no_compression_data_bytes = f.read()

    #############
    # inten_set #
    #############
    (initial_inten_array0, ), inten_diff = deep_diff(rpd.inten_set, axis_list=[0]) # 88.5 MB
    with BytesIO() as f:
        np.savez_compressed(
            f, 
            initial_inten_array0=initial_inten_array0, 
            inten_set_diff=inten_diff)
        f.seek(0)
        inten_set_bytes = f.read()

    ##########
    # mz_set #
    ##########
    mz_set = np.nan_to_num(rpd.mz_set, nan=0)  # Without this line, deep_diff function will lost information.
    (initial_mz_array0, initial_mz_array1, initial_mz_array2), mz_set_diff = deep_diff(mz_set, axis_list=[1, 1, 0])
    with BytesIO() as f:
        np.savez_compressed(
            f, 
            initial_mz_array0=initial_mz_array0, 
            initial_mz_array1=initial_mz_array1, 
            initial_mz_array2=initial_mz_array2, 
            mz_set_diff=mz_set_diff
        )       # 35.6 MB
        f.seek(0)
        mz_set_bytes = f.read()

    #################
    # COMBINE BYTES #
    #################
    header_mz_set_inten_set_no_compression_data_bytes = (
        len(header_bytes).to_bytes(InfoNoSave.header_info_len, byteorder=InfoNoSave.byteorder, signed=False) + 
        header_bytes + 
        len(mz_set_bytes).to_bytes(header.mz_set_bytes_info_len, byteorder=InfoNoSave.byteorder, signed=False) + 
        mz_set_bytes + 
        len(inten_set_bytes).to_bytes(header.inten_set_bytes_info_len, byteorder=InfoNoSave.byteorder, signed=False) + 
        inten_set_bytes + 
        len(no_compression_data_bytes).to_bytes(header.no_compression_data_bytes_info_len, byteorder=InfoNoSave.byteorder, signed=False) + 
        no_compression_data_bytes
    )
    ########
    # SAVE #
    ########
    with open(rpd_path, "wb") as f:
        magic_number = InfoNoSave.magic_number
        major_ver = (header.major_ver).to_bytes(1, byteorder=InfoNoSave.byteorder, signed=False)
        minor_ver = (header.minor_ver).to_bytes(1, byteorder=InfoNoSave.byteorder, signed=False)
        data_hash = InfoNoSave.generate_hash(header_mz_set_inten_set_no_compression_data_bytes).encode()
        f.write(
            magic_number + 
            major_ver + 
            minor_ver + 
            data_hash + 
            header_mz_set_inten_set_no_compression_data_bytes
        )

def dump_2_3(rpd, rpd_path):
    """ 
    # KEYS TO SAVE
    # info
    self.data_hash

    # data
    self.spectrum_type
    self.mz_set
    self.inten_set

    # RT info and etc.
    self.RT_list
    self.RT_unit
    self.spectrum_settings_dict

    # general info
    self.ionization_type = ionization_type
    self.analyzer_type = analyzer_type

    # KEYS NO SAVE
        self.file_path
        self.N_scan
    """
    ##########
    # header #
    ##########
    header = Header()
    with BytesIO() as f:
        pickle.dump(header, f)
        f.seek(0)
        header_bytes = f.read()

    #######################
    # no_compression_data #
    #######################
    no_compression_data = NoCompressionData(
        spectrum_type = rpd.spectrum_type, 
        RT_list = rpd.RT_list, 
        RT_unit = rpd.RT_unit, 
        spectrum_settings_dict = rpd.spectrum_settings_dict, 
        ionization_type = rpd.ionization_type, 
        analyzer_type = rpd.analyzer_type, 
        mz_set_nan_start_locs = rpd.get_mz_set_nan_start_locs()
    )
    with BytesIO() as f:
        pickle.dump(no_compression_data, f)
        f.seek(0)
        no_compression_data_bytes = f.read()

    #############
    # inten_set #
    #############
    (initial_inten_array0, ), inten_diff = deep_diff(rpd.inten_set, axis_list=[0]) # 88.5 MB
    with BytesIO() as f:
        np.savez_compressed(
            f, 
            initial_inten_array0=initial_inten_array0, 
            inten_set_diff=inten_diff)
        f.seek(0)
        inten_set_bytes = f.read()

    ##########
    # mz_set #
    ##########
    mz_set = np.nan_to_num(rpd.mz_set, nan=0)  # Without this line, deep_diff function will lost information.
    (initial_mz_array0, initial_mz_array1, initial_mz_array2), mz_set_diff = deep_diff(mz_set, axis_list=[1, 1, 0])
    with BytesIO() as f:
        np.savez_compressed(
            f, 
            initial_mz_array0=initial_mz_array0, 
            initial_mz_array1=initial_mz_array1, 
            initial_mz_array2=initial_mz_array2, 
            mz_set_diff=mz_set_diff
        )       # 35.6 MB
        f.seek(0)
        mz_set_bytes = f.read()

    ###########################################
    # mz_set_info_for_chromatogram_extraction #
    ###########################################
    mz_set_info_for_chromatogram_extraction, ref_row = rpd.get_mz_set_info_for_chromatogram_extraction()
    with BytesIO() as f:
        np.savez_compressed(
            f, 
            ref_row=ref_row, 
            mz_set_info_for_chromatogram_extraction=mz_set_info_for_chromatogram_extraction, 
        )
        f.seek(0)
        mz_set_info_for_chromatogram_extraction_bytes = f.read()

    #################
    # COMBINE BYTES #
    #################
    header_mz_set_inten_set_no_compression_data_bytes = (
        len(header_bytes).to_bytes(InfoNoSave.header_info_len, byteorder=InfoNoSave.byteorder, signed=False) + 
        header_bytes + 
        len(mz_set_bytes).to_bytes(header.mz_set_bytes_info_len, byteorder=InfoNoSave.byteorder, signed=False) + 
        mz_set_bytes + 
        len(inten_set_bytes).to_bytes(header.inten_set_bytes_info_len, byteorder=InfoNoSave.byteorder, signed=False) + 
        inten_set_bytes + 
        len(mz_set_info_for_chromatogram_extraction_bytes).to_bytes(header.mz_set_info_for_chromatogram_extraction_bytes_info_len, byteorder=InfoNoSave.byteorder, signed=False) + 
        mz_set_info_for_chromatogram_extraction_bytes + 
        len(no_compression_data_bytes).to_bytes(header.no_compression_data_bytes_info_len, byteorder=InfoNoSave.byteorder, signed=False) + 
        no_compression_data_bytes
    )
    ########
    # SAVE #
    ########
    with open(rpd_path, "wb") as f:
        magic_number = InfoNoSave.magic_number
        major_ver = (header.major_ver).to_bytes(1, byteorder=InfoNoSave.byteorder, signed=False)
        minor_ver = (header.minor_ver).to_bytes(1, byteorder=InfoNoSave.byteorder, signed=False)
        data_hash = InfoNoSave.generate_hash(header_mz_set_inten_set_no_compression_data_bytes).encode()
        f.write(
            magic_number + 
            major_ver + 
            minor_ver + 
            data_hash + 
            header_mz_set_inten_set_no_compression_data_bytes
        )

def load_2_2(rpd_path):
    with open(rpd_path, "rb") as f:
        magic_number = f.read(InfoNoSave.magic_number_size())
        if magic_number != InfoNoSave.magic_number:
            raise Exception(f"file broken: {rpd_path}")
        major_ver = int.from_bytes(f.read(InfoNoSave.major_ver_size()), byteorder=InfoNoSave.byteorder)
        minor_ver = int.from_bytes(f.read(InfoNoSave.minor_ver_size()), byteorder=InfoNoSave.byteorder)
        print(f"file version: {major_ver}.{minor_ver}")
        data_hash = f.read(InfoNoSave.hash_size())

        ###############
        # open header #
        ###############
        header_size = int.from_bytes(f.read(InfoNoSave.header_info_len), byteorder=InfoNoSave.byteorder)
        header_bytes = f.read(header_size)
        with BytesIO() as f_h:
            f_h.write(header_bytes)
            f_h.seek(0)
            header = pickle.load(f_h)

        ###############
        # open mz_set #
        ###############
        mz_set_bytes_size = int.from_bytes(f.read(header.mz_set_bytes_info_len), byteorder=InfoNoSave.byteorder)
        mz_set_bytes = f.read(mz_set_bytes_size)
        with BytesIO() as f_mz:
            f_mz.write(mz_set_bytes)
            f_mz.seek(0)
            compressed_mz_set = np.load(f_mz)
            initial_mz_array_list = [
                compressed_mz_set["initial_mz_array0"], 
                compressed_mz_set["initial_mz_array1"], 
                compressed_mz_set["initial_mz_array2"]
            ]
            mz_set_diff = compressed_mz_set["mz_set_diff"]
            mz_set_loaded = revert_deep_diff(mz_set_diff, initial_mz_array_list, axis_list=[1, 1, 0])

        ##################
        # open inten_set #
        ##################
        inten_set_bytes_size = int.from_bytes(f.read(header.inten_set_bytes_info_len), byteorder=InfoNoSave.byteorder)
        inten_set_bytes = f.read(inten_set_bytes_size)
        with BytesIO() as f_inten:
            f_inten.write(inten_set_bytes)
            f_inten.seek(0)
            compressed_inten_set = np.load(f_inten)
            initial_inten_array_list = [
                compressed_inten_set["initial_inten_array0"], 
            ]
            inten_set_diff = compressed_inten_set["inten_set_diff"]
            inten_set_loaded = revert_deep_diff(inten_set_diff, initial_inten_array_list, axis_list=[0])

        ############################
        # open no_compression_data #
        ############################
        no_compression_data_bytes_size = int.from_bytes(f.read(header.no_compression_data_bytes_info_len), byteorder=InfoNoSave.byteorder)
        no_compression_data_bytes = f.read(no_compression_data_bytes_size)
        with BytesIO() as f_ncd:
            f_ncd.write(no_compression_data_bytes)
            f_ncd.seek(0)
            no_compression_data = pickle.load(f_ncd)

    # LOAD
    rpd = db.RPD(
        data_hash = data_hash, 
        file_path = rpd_path, 
        spectrum_type = no_compression_data.spectrum_type, 
        mz_set = mz_set_loaded, 
        inten_set = inten_set_loaded, 
        RT_list = no_compression_data.RT_list, 
        RT_unit = no_compression_data.RT_unit, 
        spectrum_settings_dict = no_compression_data.spectrum_settings_dict, 
        # general_info
        ionization_type = no_compression_data.ionization_type, 
        analyzer_type = no_compression_data.analyzer_type, 
    )
    return rpd

def load_2_3(rpd_path):
    with open(rpd_path, "rb") as f:
        magic_number = f.read(InfoNoSave.magic_number_size())
        if magic_number != InfoNoSave.magic_number:
            raise Exception(f"file broken: {rpd_path}")
        major_ver = int.from_bytes(f.read(InfoNoSave.major_ver_size()), byteorder=InfoNoSave.byteorder)
        minor_ver = int.from_bytes(f.read(InfoNoSave.minor_ver_size()), byteorder=InfoNoSave.byteorder)
        data_hash = f.read(InfoNoSave.hash_size())

        ################################
        # version specific process PRE #
        ################################
        version_int = major_ver + minor_ver/10
        if version_int == 2.2:
            message = f"The file version 2.2 may have lost some information in the high m/z range, although it should be negligible in most cases.\nPlease re-generate '*.rpd' file from the original data, such as '*.mzdata'.\n{rpd_path}"
            rpd = load_2_2(rpd_path)
            mz_set_info_for_chromatogram_extraction, ref_row = rpd.get_mz_set_info_for_chromatogram_extraction()
            rpd.ref_row = ref_row
            rpd.mz_set_info_for_chromatogram_extraction = mz_set_info_for_chromatogram_extraction
            return rpd, message
        elif version_int == 2.3:
            message = None
            print(f"file version: {major_ver}.{minor_ver}")

        ###############
        # open header #
        ###############
        header_size = int.from_bytes(f.read(InfoNoSave.header_info_len), byteorder=InfoNoSave.byteorder)
        header_bytes = f.read(header_size)
        with BytesIO() as f_h:
            f_h.write(header_bytes)
            f_h.seek(0)
            header = pickle.load(f_h)

        ###############
        # open mz_set #
        ###############
        mz_set_bytes_size = int.from_bytes(f.read(header.mz_set_bytes_info_len), byteorder=InfoNoSave.byteorder)
        mz_set_bytes = f.read(mz_set_bytes_size)
        with BytesIO() as f_mz:
            f_mz.write(mz_set_bytes)
            f_mz.seek(0)
            compressed_mz_set = np.load(f_mz)
            initial_mz_array_list = [
                compressed_mz_set["initial_mz_array0"], 
                compressed_mz_set["initial_mz_array1"], 
                compressed_mz_set["initial_mz_array2"]
            ]
            mz_set_diff = compressed_mz_set["mz_set_diff"]
            mz_set_loaded = revert_deep_diff(mz_set_diff, initial_mz_array_list, axis_list=[1, 1, 0])

        ##################
        # open inten_set #
        ##################
        inten_set_bytes_size = int.from_bytes(f.read(header.inten_set_bytes_info_len), byteorder=InfoNoSave.byteorder)
        inten_set_bytes = f.read(inten_set_bytes_size)
        with BytesIO() as f_inten:
            f_inten.write(inten_set_bytes)
            f_inten.seek(0)
            compressed_inten_set = np.load(f_inten)
            initial_inten_array_list = [
                compressed_inten_set["initial_inten_array0"], 
            ]
            inten_set_diff = compressed_inten_set["inten_set_diff"]
            inten_set_loaded = revert_deep_diff(inten_set_diff, initial_inten_array_list, axis_list=[0])

        ######################################################
        # open mz_set_info_for_chromatogram_extraction_bytes #
        ######################################################
        mz_set_info_for_chromatogram_extraction_bytes_size = int.from_bytes(f.read(header.mz_set_info_for_chromatogram_extraction_bytes_info_len), byteorder=InfoNoSave.byteorder)
        mz_set_info_for_chromatogram_extraction_bytes = f.read(mz_set_info_for_chromatogram_extraction_bytes_size)
        with BytesIO() as f_mz_set_info:
            f_mz_set_info.write(mz_set_info_for_chromatogram_extraction_bytes)
            f_mz_set_info.seek(0)
            compressed_mz_set_info_for_chromatogram_extraction = np.load(f_mz_set_info)
            ref_row = compressed_mz_set_info_for_chromatogram_extraction["ref_row"]
            mz_set_info_for_chromatogram_extraction = compressed_mz_set_info_for_chromatogram_extraction["mz_set_info_for_chromatogram_extraction"]

        ############################
        # open no_compression_data #
        ############################
        no_compression_data_bytes_size = int.from_bytes(f.read(header.no_compression_data_bytes_info_len), byteorder=InfoNoSave.byteorder)
        no_compression_data_bytes = f.read(no_compression_data_bytes_size)
        with BytesIO() as f_ncd:
            f_ncd.write(no_compression_data_bytes)
            f_ncd.seek(0)
            no_compression_data = pickle.load(f_ncd)

        #################################
        # version specific process POST #
        #################################
        if major_ver + minor_ver/10 >= 2.3:
            for nan_start_row, nan_start_col in zip(*no_compression_data.mz_set_nan_start_locs):
                mz_set_loaded[nan_start_row, nan_start_col:] = np.nan

    # LOAD
    rpd = db.RPD(
        data_hash = data_hash, 
        file_path = rpd_path, 
        spectrum_type = no_compression_data.spectrum_type, 
        mz_set = mz_set_loaded, 
        inten_set = inten_set_loaded, 
        RT_list = no_compression_data.RT_list, 
        RT_unit = no_compression_data.RT_unit, 
        spectrum_settings_dict = no_compression_data.spectrum_settings_dict, 
        # general_info
        ionization_type = no_compression_data.ionization_type, 
        analyzer_type = no_compression_data.analyzer_type, 
        # Info that is not set during the file conversion
        ref_row=ref_row, 
        mz_set_info_for_chromatogram_extraction=mz_set_info_for_chromatogram_extraction
    )
    return rpd, message
    





