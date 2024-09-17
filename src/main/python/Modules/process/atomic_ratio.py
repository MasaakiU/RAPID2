# -*- coding: utf-8 -*-

import numpy as np
import re
from itertools import combinations_with_replacement, product
from math import factorial
from pathlib import Path

# 同位体区別した原子（12C, 13C, etc）
class Atom():
    def __init__(
        self, 
        atomic_number = None, 
        atomic_symbol = None, 
        mass_number = None, 
        relative_atomic_mass = None, 
        isotopic_composition = None, 
        standard_atomic_weight = [None, None], # 分子量（平均）計算時？
        notes = None
    ):
        self.atomic_number = atomic_number
        self.atomic_symbol = atomic_symbol
        self.mass_number = mass_number
        self.relative_atomic_mass = relative_atomic_mass
        self.isotopic_composition = isotopic_composition
        self.standard_atomic_weight = standard_atomic_weight
        self.notes = notes

# 同位体をまとめた原子
class Atoms():
    def __init__(self) -> None:
        self.atomic_number = None
        self.atomic_symbol = None
        self.atom_list = []
    def add_atom(self, atom):
        self.atom_list.append(atom)
    def relative_atomic_mass_list(self):
        return np.array([atom.relative_atomic_mass for atom in self.atom_list])
    def isotopic_composition_list(self):
        return np.array([atom.isotopic_composition for atom in self.atom_list])
    def mass_number_list(self):
        return np.array([atom.mass_number for atom in self.atom_list])
    def get_most_abundant_atom(self):
        return self.atom_list[np.nanargmax(self.isotopic_composition_list())]
    def relative_atomic_mass_isotopic_composition_mass_number_list(self, ignore_nan=True):
        relative_atomic_mass_list = self.relative_atomic_mass_list()
        isotopic_composition_list = self.isotopic_composition_list()
        mass_number_list = self.mass_number_list()
        if ignore_nan:
            where = ~np.isnan(isotopic_composition_list)
            relative_atomic_mass_list = relative_atomic_mass_list[where]
            isotopic_composition_list = isotopic_composition_list[where]
            mass_number_list = mass_number_list[where]
        return relative_atomic_mass_list, isotopic_composition_list, mass_number_list
    def atom_distribution(self, n, composition_threshold):
        relative_atomic_mass_list, isotopic_composition_list, mass_number_list = self.relative_atomic_mass_isotopic_composition_mass_number_list()
        relative_atomic_mass_list_new = []
        isotopic_composition_list_new = []
        mass_number_list_new = []
        for relative_atomic_mass_cmb, isotopic_composition_cmb, mass_number_cmb in zip(
            combinations_with_replacement(relative_atomic_mass_list, n), 
            combinations_with_replacement(isotopic_composition_list, n), 
            combinations_with_replacement(mass_number_list, n)
        ):
            # get unique values
            unique_v, index, counts = np.unique(relative_atomic_mass_cmb, return_index=True, return_counts=True)
            isotopic_compositions = np.array(isotopic_composition_cmb)[index]
            # calc combinations etc.
            composition = np.prod([factorial(i) // factorial(j) // factorial(i - j) for i, j in zip(np.cumsum(counts)[::-1], counts[::-1])])
            for isotopic_composition, i in zip(isotopic_compositions, counts):
                composition *= isotopic_composition ** i
            # 格納
            if composition_threshold < composition:
                relative_atomic_mass_list_new.append(sum(relative_atomic_mass_cmb))
                isotopic_composition_list_new.append(composition)
                mass_number_list_new.append(sum(mass_number_cmb))
        return relative_atomic_mass_list_new, isotopic_composition_list_new, mass_number_list_new

# 全原子
class Elements():
    def __init__(self):
        self.atoms_list = []
    def load_atoms(self, file_path):
        a = Atom()
        with open(file_path, "r") as f:
            for l in f.readlines():
                if l.strip() == "":
                    # register old atom
                    self.add_atom(a)
                    # new atoms
                    a = Atom()
                else:
                    # break down line
                    arg_val_pre = l.strip().split("=")
                    if len(arg_val_pre) == 1:
                        arg_pre = arg_val_pre[0].strip()
                        val_pre = ""
                    elif len(arg_val_pre) == 2:
                        arg_pre = arg_val_pre[0].strip()
                        val_pre = arg_val_pre[1].strip()
                    else:
                        raise Exception(f"invalid arg_val_pre: {arg_val_pre}")
                    # transform arg and val
                    arg = "_".join(map(lambda x: x.lower(), arg_pre.split(" ")))
                    if arg == "atomic_symbol":
                        val = val_pre
                        atomic_symbol = val
                    elif arg == "atomic_number":
                        val = int(val_pre)
                        atomic_number = val
                    elif arg in "mass_number":
                        val = int(val_pre)
                    elif arg in ("relative_atomic_mass", "isotopic_composition"):
                        if val_pre == "":   val = np.nan
                        else:               val = float(val_pre.split("(")[0])
                    elif arg == "standard_atomic_weight":
                        if val_pre.startswith("["): val = eval(val_pre)
                        elif val_pre == "":         val = np.nan
                        else:                       val = float(val_pre.split("(")[0])
                    elif arg == "notes":
                        pass
                    else:
                        raise Exception(f"unknown arg: {arg}")
                    setattr(a, arg, val)
    def add_atom(self, atom):
        new_atomic_number = atom.atomic_number
        # print(new_atomic_number)
        for atoms in self.atoms_list:
            if new_atomic_number == atoms.atomic_number:
                atoms.add_atom(atom)
                return
        else:
            if hasattr(self, atom.atomic_symbol):
                raise Exception(f"duplicated atomic_symbol: {atom.atomic_symbol}")
            atoms = Atoms()
            atoms.atomic_number = atom.atomic_number
            atoms.atomic_symbol = atom.atomic_symbol
            atoms.add_atom(atom)
            setattr(self, atom.atomic_symbol, atoms)
            self.atoms_list.append(atoms)
    def add_atoms(self, atoms):
        for atom in atoms:
            self.add_atom(atom)
    def remove_atoms(self, atomic_number):
        for atoms in self.atoms_list:
            if atoms.atomic_number == atomic_number:
                break
        else:
            raise Exception(f"no atoms with atomic number f{atomic_number}")
        atomic_symbol = atoms.atomic_symbol
        delattr(self, atomic_symbol)
        self.atoms_list.remove(atoms)
    def atomic_symbol_list(self):
        return [atoms.atomic_symbol for atoms in self.atoms_list]
    def mass_distribution(self, formula, composition_threshold, group_by_mass_number):
        # 各原子の種類毎にまとめてみたときの分布（パルミチン酸なら、C16個、H32個、O2個、それぞれの分布）
        distribution_patterns_of_each_atoms = []
        for atomic_symbol, n in formula:
            if not hasattr(self, atomic_symbol):
                return np.array([]), np.array([]), np.array([])
            distribution_patterns_of_each_atoms.append(getattr(self, atomic_symbol).atom_distribution(n, composition_threshold))
        distribution_patterns = combine_distribution_patterns(
            distribution_patterns_of_each_atoms, 
            composition_threshold=composition_threshold, 
            group_by_mass_number=group_by_mass_number
        )
        return distribution_patterns
    def calc_exact_mass(self, formula):
        if isinstance(formula, str):
            formula = Formula(formula)
        exact_mass = 0
        for atomic_symbol, n in formula:
            if not hasattr(self, atomic_symbol):
                exact_mass = 0
                break
            exact_mass += n * getattr(self, atomic_symbol).get_most_abundant_atom().relative_atomic_mass
        return exact_mass
    def calc_charge(self, formula):
        if isinstance(formula, str):
            formula = Formula(formula)
        try:    positive_charge = getattr(formula, "+")
        except: positive_charge = 0
        try:    negative_charge = getattr(formula, "-")
        except: negative_charge = 0
        return positive_charge - negative_charge

def combine_distribution_patterns(distribution_patterns_of_each_atoms, composition_threshold, group_by_mass_number):
    relative_atomic_mass_list_new = []
    isotopic_composition_list_new = []
    mass_number_list_new = []
    if distribution_patterns_of_each_atoms == []:
        return np.array([]), np.array([]), np.array([])
    relative_atomic_mass_set, isotopic_composition_set, mass_number_set = zip(*distribution_patterns_of_each_atoms)
    for atomic_mass_list, composition_list, mass_number_list in zip(product(*relative_atomic_mass_set), product(*isotopic_composition_set), product(*mass_number_set)):
        composition = np.prod(composition_list)
        if composition_threshold < composition:
            relative_atomic_mass_list_new.append(sum(atomic_mass_list))
            isotopic_composition_list_new.append(composition)
            mass_number_list_new.append(sum(mass_number_list))
    relative_atomic_mass_list_new = np.array(relative_atomic_mass_list_new)
    isotopic_composition_list_new = np.array(isotopic_composition_list_new)
    mass_number_list_new = np.array(mass_number_list_new)
    # group by mass_number
    if group_by_mass_number:
        unique_mass_numbers = np.unique(mass_number_list_new)
        unique_mass_number_relative_atomic_mass_list = []
        unique_mass_number_isotopic_composition_list = []
        for unique_mass_number in unique_mass_numbers:
            where = mass_number_list_new == unique_mass_number
            # 抽出
            tmp_relative_atomic_mass_list = relative_atomic_mass_list_new[where]
            tmp_isotopic_composition_list = isotopic_composition_list_new[where]
            # 平均
            isotopic_composition = tmp_isotopic_composition_list.sum()
            relative_atomic_mass = (tmp_relative_atomic_mass_list * tmp_isotopic_composition_list).sum() / isotopic_composition
            # 追加
            unique_mass_number_isotopic_composition_list.append(isotopic_composition)
            unique_mass_number_relative_atomic_mass_list.append(relative_atomic_mass)
        idx_list = np.argsort(unique_mass_numbers)
        return \
            np.array(unique_mass_number_relative_atomic_mass_list)[idx_list], \
            np.array(unique_mass_number_isotopic_composition_list)[idx_list], \
            unique_mass_numbers[idx_list]
    else:
        idx_list = np.argsort(relative_atomic_mass_list_new)
        return relative_atomic_mass_list_new[idx_list], isotopic_composition_list_new[idx_list], mass_number_list_new[idx_list]

class Formula():
    def __init__(self, formula_pre):
        pattern = r"([A-Z][a-z]*|-|\+)([0-9]*)"
        pattern4split = r"(?:[A-Z][a-z]*|-|\+)[0-9]*"
        # とりま、都合の悪い文字が入ってたら全部エラーを返す
        extra_letters = re.split(pattern4split, formula_pre)
        error = [extra_letter for extra_letter in extra_letters if extra_letter != ""]
        if len(error) != 0:
            raise Exception(f"Error!\nLetter {error} is not allowed!")
        # 実行
        self.atomic_symbol_list = []
        m = re.findall(pattern, formula_pre)
        for atomic_symbol, n in m:
            if n == "":
                n = 1
            self.add_number(atomic_symbol, int(n))
    def add_number(self, atomic_symbol, n):
        if not hasattr(self, atomic_symbol):
            setattr(self, atomic_symbol, n)
            self.atomic_symbol_list.append(atomic_symbol)
        else:
            setattr(self, atomic_symbol, getattr(self, atomic_symbol) + n)
    def sub_number(self, atomic_symbol, n):
        # チャージは面倒なので、逆にして足す
        if atomic_symbol == "+":
            self.add_number("-", n)
        elif atomic_symbol == "-":
            self.add_number("+", n)
        else:
            # 実行本体
            if not hasattr(self, atomic_symbol):
                raise Exception("error")
            else:
                new_n = getattr(self, atomic_symbol) - n
                if new_n < 0:
                    raise Exception("error")
                elif new_n == 0:
                    self.delete_atom(atomic_symbol)
                else:
                    setattr(self, atomic_symbol, new_n)
    def delete_atom(self, atomic_symbol):
        delattr(self, atomic_symbol)
        self.atomic_symbol_list.remove(atomic_symbol)
    def organize_charge(self):
        if ("+" in self.atomic_symbol_list) and ("-" in self.atomic_symbol_list):
            plus_charge = getattr(self, "+")
            minus_charge = getattr(self, "-")
            if plus_charge == minus_charge:
                self.delete_atom("+")
                self.delete_atom("-")
            elif plus_charge > minus_charge:
                setattr(self, "+", plus_charge - minus_charge)
                self.delete_atom("-")
            else:
                setattr(self, "-", minus_charge - plus_charge)
                self.delete_atom("+")
    def __iadd__(self, formula):
        for atomic_symbol in formula.atomic_symbol_list:
            self.add_number(atomic_symbol, getattr(formula, atomic_symbol))
        self.organize_charge()
        return self
    def __isub__(self, formula):
        for atomic_symbol in formula.atomic_symbol_list:
            self.sub_number(atomic_symbol, getattr(formula, atomic_symbol))
        self.organize_charge()
        return self
    def __mul__(self, n: int):
        formula = Formula("")
        for atomic_symbol in self.atomic_symbol_list:
            atom_number = getattr(self, atomic_symbol)
            formula.add_number(atomic_symbol, atom_number * n)
        return formula
    def __str__(self):
        return "".join([f"{atomic_symbol}{getattr(self, atomic_symbol)}" if getattr(self, atomic_symbol) > 1 else atomic_symbol for atomic_symbol in self.atomic_symbol_list])
    def __iter__(self):
        self._i = 0
        return self
    def __next__(self):
        if self._i > len(self.atomic_symbol_list) - 1: raise StopIteration
        atomic_symbol = self.atomic_symbol_list[self._i]
        number = getattr(self, atomic_symbol)
        self._i += 1
        return atomic_symbol, number
    @staticmethod
    def sum(*list_of_formula):
        formula_base = Formula("")
        for formula in list_of_formula:
            formula_base += formula
        return formula_base

# https://www.nist.gov/pml/atomic-weights-and-isotopic-compositions-relative-atomic-masses
def load_elements(atomic_ratio_source):
    global e
    e = Elements()
    e.load_atoms(str(atomic_ratio_source))
    set_electron()
    set_custom_deuterium_atoms(d_purity=1.00)

def custom_electron_adduct():
    custom_electron_adduct = [
        Atom(
            atomic_number = -1, 
            atomic_symbol = "-", 
            mass_number = 0, 
            relative_atomic_mass = 0.00, 
            isotopic_composition = 1.00, 
            standard_atomic_weight = [None, None], 
            notes = None
        )
    ]
    return custom_electron_adduct
def custom_electron_removal():
    custom_electron_removal = [
        Atom(
            atomic_number = -2, 
            atomic_symbol = "+", 
            mass_number = 0, 
            relative_atomic_mass = 0.00, 
            isotopic_composition = 1.00, 
            standard_atomic_weight = [None, None], 
            notes = None
        )
    ]
    return custom_electron_removal
def custom_deuterium_atoms(d_purity):
    custom_deuterium_atoms = [
        Atom(
            atomic_number = -3, 
            atomic_symbol = "D", 
            mass_number = 2, 
            relative_atomic_mass = 2.01410177812, 
            isotopic_composition = d_purity, 
            standard_atomic_weight = [None, None], 
            notes = None
        ), 
        Atom(
            atomic_number = -3, 
            atomic_symbol = "D", 
            mass_number = 1, 
            relative_atomic_mass = 1.00782503223, 
            isotopic_composition = 1 - d_purity, 
            standard_atomic_weight = [None, None], 
            notes = None
        )
    ]
    return custom_deuterium_atoms
def set_custom_deuterium_atoms(d_purity):
    e.add_atoms(custom_deuterium_atoms(d_purity=d_purity))
def set_electron():
    e.add_atoms(custom_electron_adduct())
    e.add_atoms(custom_electron_removal())
def remove_custom_deuterium_atoms():
    e.remove_atoms(atomic_number=-1)


""" examples
    # print(e.H)
    # print(e.H.atomic_symbol)
    # print(e.H.atomic_number)
    # print(e.H.relative_atomic_mass_list())
    # print(e.H.isotopic_composition_list())

    # print(e.He.atomic_symbol)
    # print(e.He.relative_atomic_mass_list())
    # print(e.He.isotopic_composition_list())
"""

if __name__ == "__main__":
    import matplotlib.pyplot as plt

    atomic_ratio_source = Path(__file__).parents[3] / "resources" / "Atomic Weights and Isotopic Compositions 20220704.txt"
    load_elements(str(atomic_ratio_source))
    # Add artificial Deuterium
    e.add_atoms(custom_deuterium_atoms(d_purity=0.99))

    # # d0  Palmitic Acid (C16H32O2)
    # distribution_patterns = e.mass_distribution(formula=Formula("C16H32O2"), composition_threshold=10**(-9), group_by_mass_number=True)

    # d31 Palmitic Acid (C16HO2D31)
    # txt_formula = "C16HO2D31"
    # distribution_patterns = e.mass_distribution(formula=Formula(txt_formula), composition_threshold=10**(-9), group_by_mass_number=True)

    # print(distribution_patterns[0])
    # print(distribution_patterns[1])

    # txt_formula = "C40H80NO8P"
    txt_formula = "C5H14NO+" # "C5H12NO2"
    distribution_patterns = e.mass_distribution(formula=Formula(txt_formula), composition_threshold=10**(-9), group_by_mass_number=True)
    print(distribution_patterns[0])
    print(distribution_patterns[1])


    # draw
    fig = plt.figure()
    for i, j, k in zip(*distribution_patterns):
        plt.plot([i, i], [0, j], c="k")
    # view
    ax = fig.gca()
    ax.set_ylim(0, 1)
    ax.set_xlim(100.3743, 107.3732)
    ax.set_xlabel("m/z")
    ax.set_ylabel("relative abundance")
    title = f"{txt_formula} (D purity={d_composition * 100}%)"
    ax.set_title(title)
    # tick
    x_lim = ax.get_xlim()
    ax.set_xticks(np.arange(np.ceil(x_lim[0]), np.floor(x_lim[1] + 1)))
    # save
    plt.savefig(f"{title}.pdf")
    plt.show()






