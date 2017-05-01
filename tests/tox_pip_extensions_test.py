import os
import re
import subprocess
import sys
import time

import ephemeral_port_reserve
import mock
import pytest
import six


class CalledProcessError(ValueError):
    def __str__(self):  # pragma: no cover (only for error cases)
        return 'cmd: {}\nreturncode: {}\nout:\n{}\n'.format(*self.args)


def _check_output(*cmd):
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    out, _ = proc.communicate()
    out = out.decode('UTF-8')
    if proc.returncode:
        raise CalledProcessError(cmd, proc.returncode, out)
    else:
        return out


@pytest.fixture(autouse=True, scope='session')
def enable_coverage():
    if 'TOP' in os.environ:  # pragma: no branch
        coveragerc = os.path.join(os.environ['TOP'], '.coveragerc')
        os.environ['COVERAGE_PROCESS_START'] = coveragerc


@pytest.fixture
def in_tmpdir(tmpdir):
    src = tmpdir.join('src').ensure_dir()
    with src.as_cwd():
        yield src


@pytest.fixture(scope='session')
def platform_name():
    return _check_output(
        sys.executable, '-m', 'pip_custom_platform.main',
        'show-platform-name',
    ).strip()


def _wheel(mod, dest, pkgs):
    subprocess.check_call(
        (sys.executable, '-m', mod, 'wheel', '--wheel-dir', dest) + pkgs
    )


def _testing(pth):
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 'testing', pth,
    )


@pytest.fixture(scope='session')
def indexserver(tmpdir_factory):
    pypi = tmpdir_factory.mktemp('indexserver').ensure_dir()
    _wheel('pip', pypi.strpath, ('pip-custom-platform', 'venv-update'))
    _wheel('pip', pypi.strpath, ('venv-update==2.1.0', 'mccabe==0.6.0'))
    for pip in ('pip', 'pip_custom_platform.main'):
        for pkg in (_testing('cmod_v1'), _testing('cmod_v2')):
            _wheel(pip, pypi.strpath, (pkg,))

    port = ephemeral_port_reserve.reserve('0.0.0.0')
    index_url = 'http://localhost:{}/simple'.format(port)
    proc = subprocess.Popen((
        sys.executable, '-m', 'pypiserver', '-p', str(port), pypi.strpath,
    ))
    try:
        timeout = 10
        timeout_time = time.time() + timeout
        while time.time() < timeout_time:
            try:
                response = six.moves.urllib.request.urlopen(index_url)
                assert response.getcode() == 200
                break
            except Exception:
                print('not up yet')
                time.sleep(.1)
        else:
            raise AssertionError('No pypi after {} seconds'.format(timeout))
        yield index_url
    finally:
        proc.terminate()


@pytest.fixture
def cache_dir(tmpdir):
    cache = tmpdir.join('cache').ensure_dir()
    with mock.patch.dict(os.environ, {'XDG_CACHE_HOME': cache.strpath}):
        yield cache


TOXINI = (
    '[tox]\n'
    'envlist = py\n'
    '{extensions}\n'
    'indexserver =\n'
    '    default = {indexserver}\n'
    '[testenv]\n'
    'deps = -rrequirements.txt\n'
    'passenv = TOP COVERAGE_ENABLE_SUBPROCESS\n'
    'commands =\n'
    '    pip freeze --all\n'
)


def _setup_py(in_tmpdir):
    in_tmpdir.join('setup.py').write(
        'import setuptools; setuptools.setup(name="test-pkg-please-ignore")',
    )


def _tox():
    return _check_output(sys.executable, '-m', 'tox', '-vvv')


def _assert_installed(out, pkg):
    _, freeze = out.split('bin/pip freeze --all')
    assert '\n{}\n'.format(pkg) in freeze


def _assert_not_installed(out, pkg):
    _, freeze = out.split('bin/pip freeze --all')
    assert '\n{}\n'.format(pkg) not in freeze


def _assert_platform(out, platform_name):
    assert 'linux_x86_64' not in out
    assert platform_name in out


def _get_prune_line(out):
    return re.search('.*--prune.*', out).group().strip()


def test_status_quo(in_tmpdir, indexserver, cache_dir, platform_name):
    _setup_py(in_tmpdir)
    in_tmpdir.join('tox.ini').write(TOXINI.format(
        indexserver=indexserver, extensions='',
    ))
    requirements = in_tmpdir.join('requirements.txt')

    requirements.write('cmod==1\nmccabe==0.6.0')
    out = _tox()
    assert platform_name not in out
    _assert_installed(out, 'cmod==1')
    _assert_installed(out, 'mccabe==0.6.0')

    requirements.write('cmod==2')
    out = _tox()
    assert platform_name not in out
    _assert_installed(out, 'cmod==1')
    _assert_installed(out, 'mccabe==0.6.0')


def test_venv_update_acceptance(in_tmpdir, indexserver, cache_dir):
    _setup_py(in_tmpdir)
    in_tmpdir.join('tox.ini').write(TOXINI.format(
        indexserver=indexserver,
        extensions='tox_pip_extensions_ext_venv_update = true',
    ))
    requirements = in_tmpdir.join('requirements.txt')

    requirements.write('cmod==1\nmccabe==0.6.0')
    out = _tox()
    _assert_installed(out, 'cmod==1')
    _assert_installed(out, 'mccabe==0.6.0')

    requirements.write('cmod==2')
    out = _tox()
    _assert_installed(out, 'cmod==2')
    _assert_not_installed(out, 'mccabe==0.6.0')


def test_pip_custom_platform_acceptance(
        in_tmpdir, indexserver, cache_dir, platform_name,
):
    _setup_py(in_tmpdir)
    in_tmpdir.join('tox.ini').write(TOXINI.format(
        indexserver=indexserver,
        extensions='tox_pip_extensions_ext_pip_custom_platform = true',
    ))
    requirements = in_tmpdir.join('requirements.txt')

    requirements.write('cmod==1\nmccabe==0.6.0')
    out = _tox()
    _assert_platform(out, platform_name)
    _assert_installed(out, 'cmod==1')
    _assert_installed(out, 'mccabe==0.6.0')

    # pip-custom-platform does not support pruning
    requirements.write('cmod==2')
    out = _tox()
    _assert_platform(out, platform_name)
    _assert_installed(out, 'cmod==2')
    _assert_installed(out, 'mccabe==0.6.0')


def test_pip_custom_platform_venv_update_acceptance(
        in_tmpdir, indexserver, cache_dir, platform_name,
):
    _setup_py(in_tmpdir)
    in_tmpdir.join('tox.ini').write(TOXINI.format(
        indexserver=indexserver,
        extensions=(
            'tox_pip_extensions_ext_pip_custom_platform = true\n'
            'tox_pip_extensions_ext_venv_update = true'
        ),
    ))
    requirements = in_tmpdir.join('requirements.txt')

    requirements.write('cmod==1\nmccabe==0.6.0')
    out = _tox()
    _assert_platform(out, platform_name)
    _assert_installed(out, 'cmod==1')
    _assert_installed(out, 'mccabe==0.6.0')

    requirements.write('cmod==2')
    out = _tox()
    _assert_platform(out, platform_name)
    _assert_installed(out, 'cmod==2')
    _assert_not_installed(out, 'mccabe==0.6.0')


def test_honors_requirements_bootstrap(in_tmpdir, indexserver, cache_dir):
    _setup_py(in_tmpdir)
    in_tmpdir.join('tox.ini').write(TOXINI.format(
        indexserver=indexserver,
        extensions='tox_pip_extensions_ext_venv_update = true',
    ))
    in_tmpdir.join('requirements-bootstrap.txt').write('venv-update==2.1.0')
    requirements = in_tmpdir.join('requirements.txt')

    requirements.write('cmod==1')
    out = _tox()
    assert 'requirements-bootstrap.txt' in out
    _assert_installed(out, 'cmod==1')
    _assert_installed(out, 'venv-update==2.1.0')


def test_skip_sdist(in_tmpdir, indexserver, cache_dir):
    _setup_py(in_tmpdir)
    in_tmpdir.join('tox.ini').write(
        '[tox]\n'
        'envlist = py\n'
        'tox_pip_extensions_ext_venv_update = true\n'
        'skipsdist = true\n'
        'indexserver = \n'
        '    default = {indexserver}\n'
        '[testenv]\n'
        'deps = -rrequirements.txt\n'
        'commands = pip freeze --all\n'.format(indexserver=indexserver),
    )
    requirements = in_tmpdir.join('requirements.txt')

    requirements.write('cmod==1')
    out = _tox()
    assert _get_prune_line(out).endswith('--prune')


def test_use_develop(in_tmpdir, indexserver, cache_dir):
    _setup_py(in_tmpdir)
    in_tmpdir.join('tox.ini').write(
        '[tox]\n'
        'envlist = py\n'
        'tox_pip_extensions_ext_venv_update = true\n'
        'indexserver = \n'
        '    default = {indexserver}\n'
        '[testenv]\n'
        'usedevelop = true\n'
        'deps = -rrequirements.txt\n'
        'commands = pip freeze --all\n'.format(indexserver=indexserver),
    )
    requirements = in_tmpdir.join('requirements.txt')

    requirements.write('cmod==1')
    out = _tox()
    assert ' -e' in _get_prune_line(out)


def test_does_not_crash_with_no_deps(in_tmpdir, indexserver, cache_dir):
    _setup_py(in_tmpdir)
    in_tmpdir.join('tox.ini').write(
        '[tox]\n'
        'envlist = py\n'
        'tox_pip_extensions_ext_venv_update = true\n'
        'indexserver = \n'
        '    default = {indexserver}\n'
        '[testenv]\n'
        'commands = pip freeze --all\n'.format(indexserver=indexserver),
    )
    _tox()


def test_errors_when_install_cmd_specified(in_tmpdir):
    _setup_py(in_tmpdir)
    in_tmpdir.join('tox.ini').write(
        '[tox]\n'
        'envlist = py27\n'
        'tox_pip_extensions_ext_venv_update = true\n'
        '[testenv]\n'
        'passenv = TOP COVERAGE_ENABLE_SUBPROCESS\n'
        'install_command = pip install --use-wheel {opts} {packages}\n'
    )

    with pytest.raises(CalledProcessError) as excinfo:
        _tox()
    expected = (
        'tox-pip-extension(s) (venv_update) used but testenv (py27) sets '
        'install_command!'
    )
    assert expected in excinfo.value.args[2]


def test_errors_for_garbage_config_value(in_tmpdir):
    _setup_py(in_tmpdir)
    in_tmpdir.join('tox.ini').write(
        '[tox]\n'
        'tox_pip_extensions_ext_venv_update = garbage\n'
    )
    with pytest.raises(CalledProcessError) as excinfo:
        _tox()
    expected = (
        'Expected "true" but got tox_pip_extensions_ext_venv_update = '
        "'garbage'"
    )
    assert expected in excinfo.value.args[2]
