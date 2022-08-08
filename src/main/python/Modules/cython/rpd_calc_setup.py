# ビルド
# python rpd_setup.py build_ext --inplace

from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext

import numpy as np
setup(
    cmdclass = {'build_ext': build_ext},
    ext_modules = [Extension("rpd_calc", ["rpd_calc.pyx"])],
    include_dirs=[np.get_include()] # gcc (C言語のコンパイラ) に numpy にまつわるヘッダファイルの所在を教えてあげなければいけない
)


