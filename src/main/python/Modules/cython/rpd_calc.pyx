# ビルド
# python rpd_calc_setup.py build_ext --inplace

cimport cython
from cython.parallel cimport prange
# from libc.math cimport sqrt
import numpy as np
cimport numpy as np
# from scipy.stats import norm
# from scipy.optimize import newton
# from scipy.ndimage import filters
DTYPEint32 = np.int32
DTYPEint64 = np.int64
DTYPEfloat64 = np.float64
ctypedef np.int32_t DTYPEint32_t
ctypedef np.int64_t DTYPEint64_t
ctypedef np.float64_t DTYPEfloat64_t


################
# JUNC ここから#
################

@cython.boundscheck(False) # turn off bounds-checking for entire function
@cython.wraparound(False)  # turn off negative index wrapping for entire function
@cython.nonecheck(False)
def cumsum_2d_axis0_float64(
        np.ndarray[DTYPEfloat64_t, ndim=2] array2d, 
    ):
    cdef np.ndarray[DTYPEfloat64_t, ndim=1] cumsum_array1d = np.zeros(array2d.shape[1], dtype=np.float64)
    cdef np.ndarray[DTYPEfloat64_t, ndim=2] result_array2d = np.empty_like(array2d, dtype=np.float64)
    for i in range(array2d.shape[0]):
        cumsum_array1d += array2d[i]
        result_array2d[i, :] = cumsum_array1d
    return result_array2d
@cython.boundscheck(False) # turn off bounds-checking for entire function
@cython.wraparound(False)  # turn off negative index wrapping for entire function
@cython.nonecheck(False)
def cumsum_2d_axis1_float64(
        np.ndarray[DTYPEfloat64_t, ndim=2] array2d, 
    ):
    cdef np.ndarray[DTYPEfloat64_t, ndim=1] cumsum_array1d = np.zeros(array2d.shape[0], dtype=np.float64)
    cdef np.ndarray[DTYPEfloat64_t, ndim=2] result_array2d = np.empty_like(array2d, dtype=np.float64)
    for i in range(array2d.shape[1]):
        cumsum_array1d += array2d[:, i]
        result_array2d[:, i] = cumsum_array1d
    return result_array2d
@cython.boundscheck(False) # turn off bounds-checking for entire function
@cython.wraparound(False)  # turn off negative index wrapping for entire function
@cython.nonecheck(False)
def cumsum_2d_axis0_int32(
        np.ndarray[DTYPEint32_t, ndim=2] array2d, 
    ):
    cdef np.ndarray[DTYPEint32_t, ndim=1] cumsum_array1d = np.zeros(array2d.shape[1], dtype=np.int32)
    cdef np.ndarray[DTYPEint32_t, ndim=2] result_array2d = np.empty_like(array2d, dtype=np.int32)
    for i in range(array2d.shape[0]):
        cumsum_array1d += array2d[i]
        result_array2d[i, :] = cumsum_array1d
    return result_array2d
@cython.boundscheck(False) # turn off bounds-checking for entire function
@cython.wraparound(False)  # turn off negative index wrapping for entire function
@cython.nonecheck(False)
def cumsum_2d_axis1_int32(
        np.ndarray[DTYPEint32_t, ndim=2] array2d, 
    ):
    cdef np.ndarray[DTYPEint32_t, ndim=1] cumsum_array1d = np.zeros(array2d.shape[0], dtype=np.int32)
    cdef np.ndarray[DTYPEint32_t, ndim=2] result_array2d = np.empty_like(array2d, dtype=np.int32)
    for i in range(array2d.shape[1]):
        cumsum_array1d += array2d[:, i]
        result_array2d[:, i] = cumsum_array1d
    return result_array2d

################
# JUNC ここまで#
################



@cython.boundscheck(False) # turn off bounds-checking for entire function
@cython.wraparound(False)  # turn off negative index wrapping for entire function
@cython.nonecheck(False)
def index_greater_than(
        DTYPEfloat64_t threshold, 
        np.ndarray[DTYPEfloat64_t, ndim=1] array1d, 
    ):
    assert type(threshold) == float
    assert array1d.dtype == DTYPEfloat64
    cdef int i
    for i in range(len(array1d)):
        if threshold < array1d[i]:
            return i
    else:
        return i + 1

#####################
# equivalent method #
#####################
# @staticmethod
# def extract_chromatogram_core(mz_btm, mz_top, mz_set, inten_set):
#     # For TIC, pass (mz_btm, mz_top) = (0, np.inf) as args.
#     mz_filter = (mz_btm <= mz_set) & (mz_set <= mz_top)
#     inten_list_pre = np.where(mz_filter, inten_set, np.nan)
#     inten_list = np.nansum(inten_list_pre, axis=1)
#     # Rows with all np.nan will be calculated as 0, so correct them.
#     inten_list[np.isnan(inten_list_pre).all(axis=1)] = np.nan
#     return inten_list
# mz_set[i, :] の右側に任意の個数 np.nan が含まれていても、動作するはず。
@cython.boundscheck(False) # turn off bounds-checking for entire function
@cython.wraparound(False)  # turn off negative index wrapping for entire function
@cython.nonecheck(False)
def extract_chromatogram_core_float64int32( # float64 for mz_set, int32 for inten_set
        DTYPEfloat64_t mz_btm, 
        DTYPEfloat64_t mz_top, 
        np.ndarray[DTYPEfloat64_t, ndim=2] mz_set,  # (len(RT_list), spectrum_number)
        np.ndarray[DTYPEint32_t, ndim=2] inten_set, # (len(RT_list), spectrum_number)
    ):
    assert type(mz_btm) == float
    assert type(mz_top) == float
    assert mz_set.dtype == DTYPEfloat64
    assert inten_set.dtype == DTYPEint32
    cdef np.ndarray[DTYPEfloat64_t, ndim=1] result_inten_list = np.zeros(mz_set.shape[0], dtype=np.float64)
    cdef int i
    cdef int j
    cdef int left_idx = 0
    cdef int right_idx = mz_set.shape[1] - 1
    cdef int i_max = mz_set.shape[0] - 1
    for i in range(mz_set.shape[0]):
        left_idx = custom_searchsorted_btm(mz_set[i, :], mz_btm, left_idx)
        right_idx = custom_searchsorted_top(mz_set[i, :], mz_top, right_idx)
        if not left_idx < right_idx:
            if right_idx > i_max:
                right_idx = i_max
            if left_idx > i_max:
                left_idx = i_max
            result_inten_list[i] = np.nan
            continue
        for j in range(left_idx, right_idx):
            result_inten_list[i] += inten_set[i, j]
        if right_idx > i_max:
            right_idx = i_max
        if left_idx > i_max:
            left_idx = i_max
    return result_inten_list

    # mz_filter = (mz_btm <= mz_set) & (mz_set <= mz_top)
    # inten_list_pre = np.where(mz_filter, inten_set, np.nan)
    # inten_list = np.nansum(inten_list_pre, axis=1)
    # # Rows with all np.nan will be calculated as 0, so correct them.
    # inten_list[np.isnan(inten_list_pre).all(axis=1)] = np.nan
    # return inten_list

@cython.boundscheck(False) # turn off bounds-checking for entire function
@cython.wraparound(False)  # turn off negative index wrapping for entire function
@cython.nonecheck(False)
cdef custom_searchsorted_btm(
        np.ndarray[DTYPEfloat64_t, ndim=1] array1d, 
        float threshold, 
        int ssi
    ):  # ssi: search_start_idx
    # array1d[ssi - 1] < threshold <= array1d[ssi] となるような ssi を返す
    # threshold < array1d[0] の場合であっても 0 を返す。
    # しかし、
    # array1d[-1] < threshold の場合は len(array1d) を返す。
    if threshold <= array1d[ssi]:
        while True:
            # threshold <= array1d[0]
            if ssi == 0:
                return ssi
            # array1d[ssi - 1] < threshold <= array1d[ssi]
            elif array1d[ssi - 1] < threshold:
                return ssi
            else:
                ssi -= 1
    else:   # array1d[ssi] < threshold
        while True:
            # array1d[-1] < threshold
            if len(array1d) - 1 <= ssi:
                return len(array1d)
            # array1d[ssi] < threshold <= array1d[ssi + 1]
            elif threshold <= array1d[ssi + 1]:
                return ssi + 1
            else:
                ssi += 1

@cython.boundscheck(False) # turn off bounds-checking for entire function
@cython.wraparound(False)  # turn off negative index wrapping for entire function
@cython.nonecheck(False)
cdef custom_searchsorted_top(
        np.ndarray[DTYPEfloat64_t, ndim=1] array1d, 
        float threshold, 
        int ssi
    ):  # ssi: search_start_idx
    # array1d[ssi - 1] <= threshold < array1d[ssi] となるような ssi を返す
    # threshold < array1d[0] の場合であっても 0 を返す。
    # しかし、
    # array1d[-1] < threshold の場合は len(array1d) を返す。
    if not threshold >= array1d[ssi]: # np.nan 対策：threshold < array1d[ssi]:
        while True:
            # threshold < array1d[0]
            if ssi == 0:
                return ssi
            # array1d[ssi - 1] <= threshold < array1d[ssi]
            elif array1d[ssi - 1] <= threshold:
                return ssi
            else:
                ssi -= 1
    else:   # array1d[ssi] <= threshold
        while True:
            # array1d[-1] <= threshold
            if len(array1d) - 1 <= ssi:
                return len(array1d)
            # array1d[ssi] <= threshold < array1d[ssi + 1]
            elif threshold < array1d[ssi + 1]:
                return ssi + 1
            else:
                ssi += 1


