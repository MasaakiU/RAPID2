# -*- coding: utf-8 -*-

import warnings
import numpy as np
from scipy import interpolate
from ..cython import rpd_calc
from ..process import deisotoping as diso

class RPD():
    def __init__(
        self, 
        data_hash, 
        file_path, 
        spectrum_type, 
        mz_set, 
        inten_set, 
        RT_list, 
        RT_unit, 
        spectrum_settings_dict, 
        # general_info
        ionization_type, 
        analyzer_type, 
        # Info that is not set during the file conversion
        ref_row=None, 
        mz_set_info_for_chromatogram_extraction=None
        # **kwargs
    ):
        # info
        self.data_hash = data_hash
        self.file_path = file_path
        # data
        self.spectrum_type = spectrum_type
        assert self.spectrum_type in ("discrete", "continuous")
        self.mz_set = mz_set        # shape: [N_RT, max_count_of_each_scan]
        self.inten_set = inten_set  # shape: [N_RT, max_count_of_each_scan]
        self.N_scan = len(self.mz_set)
        # get RT info and etc.
        self.RT_list = RT_list
        self.RT_unit = RT_unit
        self.spectrum_settings_dict = spectrum_settings_dict
        # add general info
        self.ionization_type = ionization_type
        self.analyzer_type = analyzer_type
        # Info that is not set during the file conversion
        self.ref_row = ref_row
        self.mz_set_info_for_chromatogram_extraction = mz_set_info_for_chromatogram_extraction # (2, N_scan)

        #########################################
        # attributes that are totally unrelated #
        #########################################
        self.inten_info_set_list_subtracted_by_deisotoping = IntenInfoSetList(len(self.RT_list))
    def ref_mz_list(self):
        return self.mz_set[self.ref_row]
    # used when dumping rpd data (required for reversible data compression)
    def get_mz_set_nan_start_locs(self):
        row_info, col_info = np.where(np.isnan(self.mz_set))
        unique_row, r = np.unique(row_info, return_index=True)
        unique_col = col_info[r]
        return unique_row, unique_col
    # used to get information for faster calculation of chromatogram extraction
    def get_mz_set_info_for_chromatogram_extraction(self):
        for ref_row, mz_list in enumerate(self.mz_set):
            if not np.isnan(mz_list).any():
                break
        else:
            raise Exception("Critical Error!")
        mz_set_info_for_chromatogram_extraction = self.get_mz_set_info_for_chromatogram_extraction_core(self.mz_set, ref_row)
        return mz_set_info_for_chromatogram_extraction, ref_row
    @staticmethod
    def get_mz_set_info_for_chromatogram_extraction_core(mz_set, ref_row):
        mz_set_info_for_chromatogram_extraction = np.empty((2, mz_set.shape[1]), dtype=int)
        for i in range(mz_set.shape[1]):
            # btm
            j = 1
            while True:
                idx_btm = i - j
                if idx_btm < 0:
                    mz_set_info_for_chromatogram_extraction[0, i] = 0
                    break
                if (mz_set[:, idx_btm] < mz_set[ref_row, i]).all():
                    mz_set_info_for_chromatogram_extraction[0, i] = idx_btm + 1
                    break
                else:
                    j += 1
            # top
            j = 1
            while True:
                idx_top = i + j
                if idx_top > mz_set.shape[1] - 1:
                    mz_set_info_for_chromatogram_extraction[1, i] = mz_set.shape[1] - 1
                    break
                if (mz_set[ref_row, i] < mz_set[:, idx_top]).all():
                    mz_set_info_for_chromatogram_extraction[1, i] = idx_top - 1
                    break
                else:
                    j += 1
        return mz_set_info_for_chromatogram_extraction
    def extract_mz_RT_2d_image(self, mz_range, RT_range):
        RT_idx_btm = rpd_calc.index_greater_than(RT_range[0], array1d=self.RT_list)
        RT_idx_top = rpd_calc.index_greater_than(RT_range[1], array1d=self.RT_list)
        mz_btm_idx_on_ref_row = max(rpd_calc.index_greater_than(mz_range[0], self.ref_mz_list()) - 1, 0)
        mz_top_idx_on_ref_row = min(rpd_calc.index_greater_than(mz_range[1], self.ref_mz_list())    , self.mz_set.shape[1] - 1)

        extracted_inten_set = self.inten_set[RT_idx_btm:RT_idx_top, mz_btm_idx_on_ref_row:mz_top_idx_on_ref_row]
        return extracted_inten_set

    def to_mz_RT_image(self):
        f = interpolate.interp1d(self.ref_mz_list(), self.inten_set, axis=1)
        return f(np.linspace(self.ref_mz_list()[0], self.ref_mz_list()[-1], num=len(self.ref_mz_list())))

    # chromatgram extraction related functions
    def extract_chromatogram(self, mz_btm, mz_top):
        # inten_list = self.extract_chromatogram_core(mz_btm, mz_top, self.mz_set, self.inten_set)
        inten_list = self.extract_chromatogram_core_with_cython(mz_btm, mz_top)
        return (self.RT_list, inten_list), self.calc_chromatogram_b4_deisotoping(mz_btm, mz_top, inten_list)
    def extract_chromatogram_fast(self, mz_btm, mz_top): # inaccurate, but ignorable for Q-TOF data
        # self.ref_row において、基準となる idx を求める
        mz_btm_idx_on_ref_row = max(rpd_calc.index_greater_than(mz_btm, self.ref_mz_list()) - 1, 0)
        mz_top_idx_on_ref_row = min(rpd_calc.index_greater_than(mz_top, self.ref_mz_list())    , self.mz_set.shape[1] - 1)
        # 基準となる idx を元に、（予め計算しておいた mz_ref_info_for... に基づいて）探索範囲の idx を取得する
        mz_btm_idx = self.mz_set_info_for_chromatogram_extraction[0, mz_btm_idx_on_ref_row]
        mz_top_idx = self.mz_set_info_for_chromatogram_extraction[1, mz_top_idx_on_ref_row]
        # extracted_mz_set = self.mz_set[:, mz_btm_idx:mz_top_idx + 1]
        extracted_inten_set = self.inten_set[:, mz_btm_idx:mz_top_idx + 1]
        inten_list = np.nansum(extracted_inten_set, axis=1)
        return (self.RT_list, inten_list), self.calc_chromatogram_b4_deisotoping(mz_btm, mz_top, inten_list)
    # @staticmethod
    # def extract_chromatogram_core(mz_btm, mz_top, mz_set, inten_set):
    #     # For TIC, pass (mz_btm, mz_top) = (0, np.inf) as args.
    #     mz_filter = (mz_btm <= mz_set) & (mz_set <= mz_top)
    #     inten_list_pre = np.where(mz_filter, inten_set, np.nan)
    #     inten_list = np.nansum(inten_list_pre, axis=1)
    #     # Rows with all np.nan will be calculated as 0, so correct them.
    #     inten_list[np.isnan(inten_list_pre).all(axis=1)] = np.nan
    #     return inten_list
    def extract_chromatogram_core_with_cython(self, mz_btm, mz_top):
        # self.ref_row において、基準となる idx を求める
        mz_btm_idx_on_ref_row = max(rpd_calc.index_greater_than(mz_btm, self.ref_mz_list()) - 1, 0)
        mz_top_idx_on_ref_row = min(rpd_calc.index_greater_than(mz_top, self.ref_mz_list())    , self.mz_set.shape[1] - 1)
        # 基準となる idx を元に、（予め計算しておいた mz_ref_info_for... に基づいて）探索範囲の idx を取得する
        mz_btm_idx = self.mz_set_info_for_chromatogram_extraction[0, mz_btm_idx_on_ref_row]
        mz_top_idx = self.mz_set_info_for_chromatogram_extraction[1, mz_top_idx_on_ref_row]
        extracted_mz_set = self.mz_set[:, mz_btm_idx:mz_top_idx + 1]
        extracted_inten_set = self.inten_set[:, mz_btm_idx:mz_top_idx + 1]
        # 上記探索範囲の idx を元にデータをを切り出し -> 漸く chromatogram_extraction が行える
        inten_list = rpd_calc.extract_chromatogram_core_float64int32(mz_btm, mz_top, extracted_mz_set, extracted_inten_set)
        # inten_list = self.extract_chromatogram_core(mz_btm, mz_top, extracted_mz_set, extracted_inten_set)
        return inten_list
    def calc_chromatogram_b4_deisotoping(self, mz_btm, mz_top, inten_list_after_subtraction):
        return self.inten_info_set_list_subtracted_by_deisotoping.extract_chromatogram_b4_subtraction(mz_btm, mz_top, inten_list_after_subtraction)
    def extract_spectrum(self, RT_btm, RT_top):
        RT_idx_btm = rpd_calc.index_greater_than(threshold=RT_btm, array1d=self.RT_list)
        RT_idx_top = rpd_calc.index_greater_than(threshold=RT_top, array1d=self.RT_list)
        mz_list, inten_list = self.extract_spectrum_default(RT_idx_btm, RT_idx_top)
        return (mz_list, inten_list), self.extract_spectrum_b4_deisotoping(RT_idx_btm, RT_idx_top, mz_list, inten_list)
    def extract_spectrum_fast(self, RT_btm, RT_top):
        RT_idx_btm = max(rpd_calc.index_greater_than(threshold=RT_btm, array1d=self.RT_list) - 1, 0)
        RT_idx_top = min(rpd_calc.index_greater_than(threshold=RT_top, array1d=self.RT_list)    , len(self.RT_list) - 1)
        inten_set = self.inten_set[RT_idx_btm:RT_idx_top]
        mz_set = self.mz_set[RT_idx_btm:RT_idx_top]
        mz_list = mz_set.mean(axis=0)
        inten_list = inten_set.mean(axis=0)
        return (mz_list, inten_list), self.extract_spectrum_b4_deisotoping_fast(RT_idx_btm, RT_idx_top, mz_list, inten_list)
    def extract_spectrum_default(self, RT_idx_btm, RT_idx_top):
        # extract data
        inten_set = self.inten_set[RT_idx_btm:RT_idx_top]
        mz_set = self.mz_set[RT_idx_btm:RT_idx_top]
        # get target data, calc average
        return self.calc_mz_inten_list_average(mz_set.reshape(-1), inten_set.reshape(-1), RT_idx_top - RT_idx_btm)
    def extract_spectrum_b4_deisotoping(self, RT_idx_btm, RT_idx_top, mz_list, inten_list):
        subtracted_mz_list, subtracted_inten_list = self.inten_info_set_list_subtracted_by_deisotoping.extract_as_spectrum(RT_idx_btm, RT_idx_top)
        return subtracted_mz_list, subtracted_inten_list + np.interp(subtracted_mz_list, mz_list, inten_list)
    def extract_spectrum_b4_deisotoping_fast(self, RT_idx_btm, RT_idx_top, mz_list, inten_list):
        subtracted_mz_list, subtracted_inten_list = self.inten_info_set_list_subtracted_by_deisotoping.extract_spectrum_b4_subtraction_fast(RT_idx_btm, RT_idx_top, inten_list)
        return subtracted_mz_list, subtracted_inten_list + np.interp(subtracted_mz_list, mz_list, inten_list)
    @staticmethod
    def calc_mz_inten_list_average(mz_list, inten_list, N_RT):
        if N_RT == 0:
            return np.array([]), np.array([])
        # prepare for sorting
        mz_indices = np.argsort(mz_list, kind="mergesort")
        if len(mz_indices) % N_RT != 0:
            mz_indices = mz_indices[:-(len(mz_indices)%N_RT)]
            if len(mz_indices) == 0:
                return np.array([]), np.array([])
        # return average
        return mz_list[mz_indices].reshape((N_RT, -1), order="F").mean(axis=0), inten_list[mz_indices].reshape((N_RT, -1), order="F").mean(axis=0)
    # def extract_RT_idx_where(self, RT_btm, RT_top):
    #     return (RT_btm < self.RT_list) * (self.RT_list < RT_top)
    def extract_info(self):
        return Info(self)
    def calc_chromatogram_auc(
        self, 
        mz_btm, 
        mz_top, 
        RT_btm, 
        RT_top, 
        return_BG_subtraction, 
        return_height, 
        return_baseline_height, 
        return_real_RT_range
    ):
        RT_idx_btm = rpd_calc.index_greater_than(threshold=RT_btm, array1d=self.RT_list)
        RT_idx_top = rpd_calc.index_greater_than(threshold=RT_top, array1d=self.RT_list)
        if RT_idx_top - RT_idx_btm < 2:
            return None
        extracted_RT_list = self.RT_list[RT_idx_btm:RT_idx_top]
        extracted_mz_set = self.mz_set[RT_idx_btm:RT_idx_top, :]
        extracted_inten_set = self.inten_set[RT_idx_btm:RT_idx_top, :]
        # extracted_inten_list = self.extract_chromatogram_core(mz_btm, mz_top, extracted_mz_set, extracted_inten_set)
        extracted_inten_list = rpd_calc.extract_chromatogram_core_float64int32(mz_btm, mz_top, extracted_mz_set, extracted_inten_set)
        auc = self.calc_auc_core(extracted_RT_list, extracted_inten_list)
        r = [auc]
        if return_BG_subtraction:
            BG = extracted_inten_list.min() * (extracted_RT_list[-1] - extracted_RT_list[0])
            r += [auc - BG]
        if return_height:
            r += [extracted_inten_list.max()]
        if return_baseline_height:
            r += [extracted_inten_list.min()]
        if return_real_RT_range:
            r += [extracted_RT_list[[0, -1]]]
        return r
    def calc_spectrum_auc(self, RT_btm, RT_top):
        pass
    @staticmethod
    def calc_auc_core(x_list, y_list):
        return ((y_list[1:] + y_list[:-1]) * np.diff(x_list)).sum() / 2
    def set_deisotoping(self, deisotoping):
        # clear previous deisotoping
        if not self.inten_info_set_list_subtracted_by_deisotoping.is_empty():
            self.clear_deisotoping()
        # set deisotoping
        for i in range(deisotoping.count()):
            relative_atomic_mass_list, isotopic_composition_list, data_item = deisotoping.get_deisotoping_info(i)
            RT_idx_btm = rpd_calc.index_greater_than(threshold=data_item.RT - data_item.RT_range, array1d=self.RT_list)
            RT_idx_top = rpd_calc.index_greater_than(threshold=data_item.RT + data_item.RT_range, array1d=self.RT_list)
            mz_btm = relative_atomic_mass_list[0] - data_item.mz_range
            mz_top = relative_atomic_mass_list[-1] + data_item.mz_range
            # RT で回す
            for RT_idx in range(RT_idx_btm, RT_idx_top):
                mz_idx_btm = rpd_calc.index_greater_than(threshold=mz_btm, array1d=self.mz_set[RT_idx, :])
                mz_idx_top = rpd_calc.index_greater_than(threshold=mz_top, array1d=self.mz_set[RT_idx, :])
                target_mz_list = self.mz_set[RT_idx, mz_idx_btm:mz_idx_top]
                target_inten_list = self.inten_set[RT_idx, mz_idx_btm:mz_idx_top]
                # execute deisotoping
                subtracted_inten_list = diso.deisotope_core(target_mz_list, target_inten_list, relative_atomic_mass_list, isotopic_composition_list)
                # store subtracted values
                self.inten_info_set_list_subtracted_by_deisotoping.update_data(RT_idx, self.RT_list[RT_idx], mz_idx_btm, mz_idx_top, target_mz_list, subtracted_inten_list)
        # set mz_idx_blocks: deisotoping 前の図を表示する際、スペクトルが途切れるべき部分がつながってしまうことを防止する。
        self.inten_info_set_list_subtracted_by_deisotoping.update_mz_idx_blocks()
    def clear_deisotoping(self):
        raise Exception("Clearing of deisotoping is not implemented yet!")

        self.inten_set[~np.isnan(self.inten_info_set_list_subtracted_by_deisotoping)] = self.inten_info_set_list_subtracted_by_deisotoping[~np.isnan(self.inten_info_set_list_subtracted_by_deisotoping)].astype(self.inten_set.dtype)
        self.inten_info_set_list_subtracted_by_deisotoping = IntenInfoSetList(len(self.RT_list))

class IntenInfoSetList(list):
    def __init__(self, N_RT):
        super().__init__([None for i in range(N_RT)])
    def is_empty(self):
        for inten_list_info in self:
            if inten_list_info is not None:
                return False
        else:
            return True            
    def update_data(self, RT_idx, RT, mz_idx_btm, mz_idx_top, mz_list, inten_list):
        inten_list_info = self[RT_idx]
        if inten_list_info is None:
            self[RT_idx] = IntenListInfo(RT, RT_idx, mz_idx_btm, mz_idx_top, mz_list, inten_list)
        else:
            inten_list_info.update_data(mz_idx_btm, mz_idx_top, mz_list, inten_list)
        """
        DO NOT FORGET TO EXECUTE self.update_mz_idx_blocks() AFTER ALL OF THE self.update_data() PROCESS FINISHED!!!
        deisotoping 前の図を表示する際、スペクトルが途切れるべき部分がつながってしまうことを防止する。
        """
    def update_mz_idx_blocks(self):
        for inten_list_info in self:
            if inten_list_info is None:
                continue
            else:
                inten_list_info.update_mz_idx_blocks()
    def extract_as_spectrum(self, RT_idx_btm, RT_idx_top):
        # get target data
        mz_list = []
        inten_list = []
        N_RT = 0
        for inten_list_info in self[RT_idx_btm:RT_idx_top]:
            if inten_list_info is None:
                continue
            mz_list.extend(inten_list_info.mz_list)
            inten_list.extend(inten_list_info.inten_list)
            N_RT += 1
        mz_list, inten_list = RPD.calc_mz_inten_list_average(np.array(mz_list), np.array(inten_list), N_RT)
        return mz_list, inten_list * N_RT / (RT_idx_top - RT_idx_btm)
    def extract_spectrum_b4_subtraction_fast(self, RT_idx_btm, RT_idx_top, inten_list_after_subtraction):
        # get target data
        mz_list = np.full((RT_idx_top - RT_idx_btm, len(inten_list_after_subtraction)), np.nan, order="F")
        inten_list = np.full((RT_idx_top - RT_idx_btm, len(inten_list_after_subtraction)), np.nan, order="F")
        is_empty = True
        for i, inten_list_info in enumerate(self[RT_idx_btm:RT_idx_top]):
            if inten_list_info is not None:
                is_empty = False
                for block_start_idx, block_end_idx in inten_list_info.mz_idx_blocks:
                    mz_idx_start, mz_idx_end = inten_list_info.mz_idx_list[[block_start_idx, block_end_idx]]
                    mz_list[i, mz_idx_start:mz_idx_end + 1] = inten_list_info.mz_list[block_start_idx:block_end_idx + 1]
                    inten_list[i, mz_idx_start:mz_idx_end + 1] = inten_list_info.inten_list[block_start_idx:block_end_idx + 1]
        if not is_empty:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                mz_list_result, inten_list_result = np.nanmean(mz_list, axis=0), np.nansum(inten_list, axis=0) / (RT_idx_top - RT_idx_btm)
            return mz_list_result, inten_list_result
        else:
            return np.array([np.nan]), np.array([np.nan])
    # def extract_as_chromatogram(self, mz_btm, mz_top):
    #     RT_list = []
    #     inten_list = []
    #     for inten_list_info in self:
    #         if inten_list_info is None:
    #             RT_list.append(np.nan)
    #             inten_list.append(np.nan)
    #         else:
    #             RT_list.append(inten_list_info.RT)
    #             inten_list.append(inten_list_info.extract_chromatogram_value(mz_btm, mz_top))
    #     return np.array(RT_list), np.array(inten_list)
    def extract_chromatogram_b4_subtraction(self, mz_btm, mz_top, inten_list_after_subtraction):
        assert len(self) == len(inten_list_after_subtraction)
        RT_list = np.full(len(self), np.nan)
        inten_list = np.full(len(self), np.nan)
        for i, inten_list_info in enumerate(self):
            if inten_list_info is not None:
                RT_list[i] = inten_list_info.RT
                inten_list[i] = inten_list_info.extract_chromatogram_value(mz_btm, mz_top) + inten_list_after_subtraction[inten_list_info.RT_idx]
        return RT_list, inten_list

class IntenListInfo():
    def __init__(self, RT, RT_idx, mz_idx_btm, mz_idx_top, mz_list, inten_list):
        self.RT = RT
        self.RT_idx = RT_idx
        self.mz_idx_list = np.arange(mz_idx_btm, mz_idx_top)
        self.mz_idx_blocks = None
        self.mz_list = mz_list
        self.inten_list = inten_list
        self.update_mz_idx_blocks()
    def update_mz_idx_blocks(self):
        is_mz_idx_discrete = np.diff(self.mz_idx_list)
        idx_discrete_location = np.where(is_mz_idx_discrete > 1)[0]
        self.mz_idx_blocks = list(zip([0] + list(idx_discrete_location + 1), list(idx_discrete_location) + [len(self.mz_idx_list) - 1]))
    def extract_chromatogram_value(self, mz_btm, mz_top):
        loc = np.logical_and(mz_btm <= self.mz_list, self.mz_list <= mz_top)
        if loc.any():
            return self.inten_list[loc].sum()
        else:
            return np.nan
    def update_data(self, mz_idx_btm, mz_idx_top, mz_list, subtracted_inten_list):
        # only mz_idx that does not exist in self.mz_idx_ist will be inserted.
        mz_idx_list_new = np.arange(mz_idx_btm, mz_idx_top)
        idx_list_for_extraction_newly_appeared = []
        idx_list_for_extraction_already_exist = []
        for i, mz_idx in enumerate(mz_idx_list_new):
            if mz_idx not in self.mz_idx_list:
                idx_list_for_extraction_newly_appeared.append(i)
            else:
                idx_list_for_extraction_already_exist.append(i)
        # get insertion_idx
        mz_idx_list_newly_appeared = mz_idx_list_new[idx_list_for_extraction_newly_appeared]
        insertion_idx_newly_appeared = np.searchsorted(self.mz_idx_list, mz_idx_list_newly_appeared)
        self.mz_idx_list = np.insert(self.mz_idx_list, insertion_idx_newly_appeared, mz_idx_list_newly_appeared)
        self.mz_list = np.insert(self.mz_list, insertion_idx_newly_appeared, mz_list[idx_list_for_extraction_newly_appeared])
        self.inten_list = np.insert(self.inten_list, insertion_idx_newly_appeared, 0)
        # add to already exist
        insertion_idx = np.searchsorted(self.mz_idx_list, mz_idx_list_new)
        self.inten_list[insertion_idx] += subtracted_inten_list
        """
        DO NOT FORGET TO EXECUTE self.update_mz_idx_blocks() AFTER ALL OF THE self.update_data() PROCESS FINISHED!!!
        deisotoping 前の図を表示する際、スペクトルが途切れるべき部分がつながってしまうことを防止する。
        """

class Info():
    def __init__(self, rpd) -> None:
        self.data_hash = rpd.data_hash          # sha256
        self.file_path = rpd.file_path
        self.spectrum_type = rpd.spectrum_type  # ("discrete" or "continuous")
        self.spectrum_settings_dict = rpd.spectrum_settings_dict
        # general info
        self.ionization_type = rpd.ionization_type
        self.analyzer_type = rpd.analyzer_type
    def get_scan_settings_text(self, full=False):
        polarity = self.spectrum_settings_dict["Polarity"]
        scan_mode = self.spectrum_settings_dict["ScanMode"]
        if not full:
            # ionization type
            ionization_type = self.ionization_type.upper()
            # polarity
            if polarity == "Positive":
                polarity = "+"
            elif polarity == "Negative":
                polarity = "-"
            else:
                pass
            # analyzer type
            if self.analyzer_type == "TimeOfFlight":
                analyzer_type = "TOF"
            else:
                analyzer_type = self.analyzer_type
            # scan mode
            scan_mode = scan_mode.upper()
        else:
            ionization_type = self.ionization_type
            analyzer_type = self.analyzer_type
        return f"{ionization_type}{polarity} {analyzer_type} {scan_mode}"
    def __getattr__(self, k):
        if k in ("polarity", "scanmode"):
            return self.spectrum_settings_dict[k.capitalize()]
        elif k == "scan_settings":
            return self.get_scan_settings_text(full=False)
        else:
            raise Exception(f"unknown attribute: {k}")

class DataBase():
    def __init__(self, main_window):
        self.main_window = main_window
        # the following lists must be synchronyzed
        self.data_list = []
        self.data_type_list = []
        self.data_hash_list = []
    def model(self):
        return self.main_window.model
    def N_data(self):
        return len(self.data_hash_list)
    def add_rpd(self, rpd):
        self.data_list.append(rpd)
        self.data_type_list.append("rpd")
        self.data_hash_list.append(rpd.data_hash)
    # please return appropriate rpd data based on **option
    def get_all_rpd_data(self, **option):
        data_list = []
        for data_type, data in zip(self.data_type_list, self.data_list):
            if data_type == "rpd":
                data_list.append(data)
            else:
                # extract appropriate rpd data using opt in the future
                raise Exception(f"unexpected data type\n{data_type}")
        return self.data_hash_list, data_list
    # please return appropriate rpd data based on **option
    def get_rpd_data(self, index, **option):
        data_type = self.data_type_list[index]
        data = self.data_list[index]
        if data_type == "rpd":
            return self.data_hash_list[index], data
        else:
            # extract appropriate rpd data using opt in the future
            raise Exception(f"unexpected data type\n{data_type}")



