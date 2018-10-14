from setuptools import setup


setup(
    name='tox-pip-extensions',
    description=(
        'Augment tox with different installation methods via progressive '
        'enhancement.'
    ),
    url='https://github.com/tox-dev/tox-pip-extensions',
    version='1.4.1',

    author='Anthony Sottile',
    author_email='asottile@umich.edu',

    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],

    py_modules=['tox_pip_extensions'],
    install_requires=['six', 'tox>=3.3'],
    entry_points={'tox': ['pip_extensions = tox_pip_extensions']}
)
