# -*- coding: utf-8 -*-

import numpy as np
from . import atomic_ratio as ar
from ..cython import rpd_calc

class Deisotoping():
    mass_number_threshold = 5
    composition_threshold = 10**(-9)
    def __init__(self, data_items):
        self.data_items = data_items
        self.sort_by_mw()
    def sort_by_mw(self):
        relative_atomic_mass0_list = self.relative_atomic_mass0_list()
        argsort = np.argsort(relative_atomic_mass0_list)
        self.data_items = [self.data_items[a] for a in argsort]
    def relative_atomic_mass0_list(self):
        relative_atomic_mass0_list = []
        for data_item in self.data_items:
            relative_atomic_mass_list, isotopic_composition_list, mass_number_list = ar.e.mass_distribution(ar.Formula(data_item.formula), composition_threshold=10**(-9), group_by_mass_number=True)
            relative_atomic_mass0_list.append(relative_atomic_mass_list[0])
        return relative_atomic_mass0_list            

    def count(self):
        return len(self.data_items)

    def get_deisotoping_info(self, i):
        data_item = self.data_items[i]
        formula = ar.Formula(data_item.formula)
        relative_atomic_mass_list, isotopic_composition_list, mass_number_list = ar.e.mass_distribution(formula, composition_threshold=10**(-9), group_by_mass_number=True)
        charge = abs(ar.e.calc_charge(formula))
        assert charge > 0
        relative_atomic_mass_list = relative_atomic_mass_list[:self.mass_number_threshold] / charge
        isotopic_composition_list = isotopic_composition_list[:self.mass_number_threshold] / isotopic_composition_list[0]
        return relative_atomic_mass_list, isotopic_composition_list, data_item

def deisotope_core(target_mz_list, target_inten_list, relative_atomic_mass_list, isotopic_composition_list):
    original_target_inten_list = np.copy(target_inten_list)
    # Values of "target_intens_list", which should be a view of some other list, will be updated.
    if isotopic_composition_list[0] != 1:
        isotopic_composition_list /= isotopic_composition_list[0]
    # get index
    mz_between_idx_list = [
        rpd_calc.index_greater_than(threshold=mz_between, array1d=target_mz_list) for mz_between in (relative_atomic_mass_list[1:] + relative_atomic_mass_list[:-1]) / 2
    ] + [-1]
    # get reference (M+0) spectrum
    ref_mz_list = target_mz_list[:mz_between_idx_list[0]]
    ref_inten_list = target_inten_list[:mz_between_idx_list[0]]
    ref_inten_list = ref_inten_list - ref_inten_list.min()
    # mz (M+0, M+1,...) で回す
    for i, (relative_atomic_mass_diff, isotopic_composition) in enumerate(zip(
        relative_atomic_mass_list[1:] - relative_atomic_mass_list[0], 
        isotopic_composition_list[1:]
    )):
        # adjust mz and inten
        ref_mz_list_mod = ref_mz_list + relative_atomic_mass_diff
        ref_inten_list_mod = ref_inten_list * isotopic_composition
        # get target M+n spectrum
        mz_btm_idx = mz_between_idx_list[i]
        mz_top_idx = mz_between_idx_list[i + 1]
        mz_list_to_be_corrected = target_mz_list[mz_btm_idx:mz_top_idx]
        # interpolation
        inten_list_to_subtract = np.interp(mz_list_to_be_corrected, ref_mz_list_mod, ref_inten_list_mod, left=0, right=0).astype(target_inten_list.dtype)
        target_inten_list[mz_btm_idx:mz_top_idx] -= inten_list_to_subtract
    # Values below zero are not allowed.
    target_inten_list[target_inten_list < 0] = 0
    return original_target_inten_list - target_inten_list









