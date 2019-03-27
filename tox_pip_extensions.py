from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import collections
import contextlib

import six
from tox import hookimpl


TOX_KEY = 'tox_pip_extensions_ext_'

PIP_CUSTOM_PLATFORM = 'pip_custom_platform'
VENV_UPDATE = 'venv_update'

INSTALL_DEPS = {
    PIP_CUSTOM_PLATFORM: str('pip-custom-platform>=0.3.1'),
    VENV_UPDATE: str('venv-update>=2.1.3'),
}

_INSTALL = ('install', '{opts}', '{packages}')
_PCP = ('pip-custom-platform',) + _INSTALL
_VU = ('pip-faster',) + _INSTALL
_PCP_VU = ('pymonkey', 'pip-custom-platform', '--') + _VU

VANILLA_PIP_INSTALL_CMD = ('python', '-m', 'pip',) + _INSTALL

INSTALL_CMD = {
    (PIP_CUSTOM_PLATFORM, VENV_UPDATE): _PCP_VU,
    (PIP_CUSTOM_PLATFORM,): _PCP,
    (VENV_UPDATE,): _VU,
}

Config = collections.namedtuple('Config', ('extensions', 'bootstrap_deps'))


def _assert_true_value(k, v):
    if v.lower() in {'true', '1'}:
        return True
    else:
        raise ValueError('Expected "true" but got {} = {!r}'.format(k, v))


@hookimpl
def tox_configure(config):
    cfg = six.moves.configparser.ConfigParser()
    cfg.read(str(config.toxinipath))
    configured = tuple(sorted(
        k[len(TOX_KEY):]
        for k, v in cfg.items('tox')
        if k.startswith(TOX_KEY) and _assert_true_value(k, v)
    ))
    if configured:
        bootstrap = config.toxinidir.join('requirements-bootstrap.txt')
        if bootstrap.exists():
            bootstrap_deps = (str('-r{}').format(bootstrap),)
        else:
            bootstrap_deps = [INSTALL_DEPS[ext] for ext in configured]
            # venv-update has more restrictive dependencies, list it first
            bootstrap_deps = tuple(reversed(bootstrap_deps))

        install_cmd = INSTALL_CMD[configured] + bootstrap_deps
        for k, cfg in config.envconfigs.items():
            if tuple(cfg.install_command) != VANILLA_PIP_INSTALL_CMD:
                print('!' * 79)
                print(
                    'tox-pip-extension(s) ({}) used but testenv ({}) sets '
                    'install_command!'.format(', '.join(configured), k),
                )
                print('!' * 79)
                exit(1)
            cfg.install_command[:] = install_cmd
    else:
        bootstrap_deps = None

    config.pip_extensions = Config(configured, bootstrap_deps)


def _install(venv, action, step, deps):
    if deps:
        action.setactivity(step, ','.join(map(str, deps)))
        venv._install(deps, action=action)


@contextlib.contextmanager
def _install_cmd(envconfig, install_command):
    orig = envconfig.install_command[:]
    envconfig.install_command[:] = install_command
    try:
        yield
    finally:
        envconfig.install_command[:] = orig


def _install_bootstrap(venv, action, bootstrap_deps):
    with _install_cmd(venv.envconfig, VANILLA_PIP_INSTALL_CMD):
        _install(venv, action, 'bootstrap', bootstrap_deps)


@hookimpl(tryfirst=True)
def tox_testenv_install_deps(venv, action):
    config = venv.envconfig.config
    extensions, bootstrap_deps = config.pip_extensions

    # If there's nothing special for us to do, defer to other plugins
    if not extensions:
        return None

    _install_bootstrap(venv, action, bootstrap_deps)
    _install(venv, action, 'installdeps', venv.get_resolved_dependencies())

    # Indicate to the plugin framework that we have handled installation
    return True


@hookimpl
def tox_runtest_pre(venv):
    config = venv.envconfig.config
    extensions, bootstrap_deps = config.pip_extensions

    # If there's nothing special for us to do, defer to other plugins
    if not extensions:
        return None

    action = venv.new_action('tox-pip-extensions')

    _install_bootstrap(venv, action, bootstrap_deps)

    install_command = list(venv.envconfig.install_command)
    if 'venv_update' in extensions:
        install_command.append('--prune')

    def _extras(opt):
        if venv.envconfig.extras:
            return opt + '[{}]'.format(','.join(venv.envconfig.extras))
        else:
            return opt

    if venv.envconfig.usedevelop:
        install_command.append(_extras('-e{}'.format(config.toxinidir)))
    elif not config.skipsdist and not venv.envconfig.skip_install:
        install_command.append(_extras(venv.package))

    with _install_cmd(venv.envconfig, install_command):
        _install(venv, action, 'installdeps', venv.get_resolved_dependencies())

    # Show what we installed
    output = venv._pcall(
        venv.envconfig.list_dependencies_command,
        cwd=config.toxinidir,
        action=action,
    ).split('\n\n')[-1]
    action.setactivity('installed', ','.join(output.splitlines()))
