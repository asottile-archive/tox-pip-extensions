[![Build Status](https://travis-ci.org/asottile/tox-pip-extensions.svg?branch=master)](https://travis-ci.org/asottile/tox-pip-extensions)
[![Coverage Status](https://coveralls.io/repos/github/asottile/tox-pip-extensions/badge.svg?branch=master)](https://coveralls.io/github/asottile/tox-pip-extensions?branch=master)

tox-pip-extensions
==================

Augment tox with different installation methods via progressive enhancement.

## Installation

`pip install tox-pip-extensions`

## Supported extensions

### [venv-update (pip-faster)](https://github.com/Yelp/venv-update)

venv-update has the desirable behavior that it synchronizes the installed
packages to the dependencies you ask for and uninstalls extraneous things
quickly (without removing the virtualenv) -- you'll never need
`tox --recreate` again!

To enable this enhancement, simply add:

```ini
[tox]
tox_pip_extensions_ext_venv_update = true
```

### [pip-custom-platform](https://github.com/asottile/pip-custom-platform)

pip-custom-platform is useful if you'd like to target other operating systems
and maintain an internal pypi server containing precompiled wheels.

To enable this enhancement, simply add:

```ini
[tox]
tox_pip_extensions_ext_pip_custom_platform = true
```

### pip-custom-platform + venv-update (pip-faster)

These extensions can be used together, simply add both:

```ini
[tox]
tox_pip_extensions_ext_venv_update = true
tox_pip_extensions_ext_pip_custom_platform = true
```

## Bootstrap requirements

By default, `tox-pip-extensions` will intelligently choose what versions to
install based on the plugins selected.

If you'd like to pin specific versions, `tox-pip-extensions` will defer to a
file named `requirements-bootstrap.txt` in the same directory as `tox.ini`.
