from setuptools import Extension
from setuptools import setup


setup(
    name='cmod',
    version='1',
    ext_modules=[Extension('cmod', ['cmod.c'])],
)
