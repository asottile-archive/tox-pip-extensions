from setuptools import Extension
from setuptools import setup


setup(
    name='cmod',
    version='2',
    ext_modules=[Extension('cmod', ['cmod.c'])],
)
