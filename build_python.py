#!/usr/bin/env python3
import shutil
import subprocess
import sys
import os
from pathlib import Path

package_name = 'python'
python_version = '3.7.7'
macos_deployment_target = '10.12'

def macos():
    return sys.platform == 'darwin'

def windows():
    return sys.platform == 'win32'

def linux():
    return sys.platform.startswith('linux')

def centos():
    return linux() and Path('/etc/centos-release').exists()

def debian():
    return linux() and Path('/etc/debian_version').exists()

def ubuntu():
    return debian() and subprocess.check_output('lsb_release -i -s', shell=True).decode('utf-8').strip() == 'Ubuntu'

def platform():
    if linux():
        if centos():
            version = subprocess.check_output('rpm -E %{rhel}', shell=True).decode('utf-8').strip()
            return f'centos{version}'
        else:
            version = subprocess.check_output('lsb_release -r -s', shell=True).decode('utf-8').strip()
            return f'ubuntu{version}'
    return sys.platform

def output_base_name():
    components = [
        package_name,
        python_version,
    ]
    if 'BUILD_BUILDID' in os.environ:
        components.append(os.environ['BUILD_BUILDID'])
    else:
        components.append('dont-use-me-dev-build')
    components.append(platform())
    return '-'.join(components)

def python_destdir():
    if windows():
        return Path('D:\\x_mirror\\buildman\\tools\\Python')
    else:
        return Path('/opt/ccdc/third-party/python')

def python_version_destdir():
    return python_destdir() / output_base_name()

def prepare_output_dir():
    if linux():
        subprocess.run(f'sudo mkdir -p {python_destdir()}', shell=True)
        subprocess.run(f'sudo chown $USER {python_destdir()}', shell=True)

def install_from_msi():
    import urllib.request
    import tempfile
    url=f'https://www.python.org/ftp/python/{python_version}/python-{python_version}-amd64.exe'
    localfilename=f'python-{python_version}-amd64.exe'
    with tempfile.TemporaryDirectory() as tmpdir:
        localfile = Path(tmpdir) / localfilename
        print(f'Fetching {url} to {localfile}')
        with urllib.request.urlopen(url) as response:
            with open(localfile, 'wb') as final_file:
                shutil.copyfileobj(response, final_file)
        subprocess.run(f'{localfile} /quiet InstallAllUsers=0 Include_launcher=0 Include_doc=0 Include_debug=1 Include_symbols=1 Shortcuts=0 Include_test=0 CompileAll=1 TargetDir="{python_version_destdir()}" SimpleInstallDescription="Just for me, no test suite."', shell=True, check=True)

def install_prerequisites():
    if macos():
        subprocess.run(['brew', 'install', 'openssl', 'readline', 'sqlite3', 'xz', 'zlib', 'tcl-tk'], check=True)
    if linux():
        if centos():
            subprocess.run('sudo yum update -y', shell=True, check=True)
            subprocess.run('sudo yum install -y findutils gcc zlib-devel bzip2 bzip2-devel readline-devel sqlite sqlite-devel openssl-devel tk-devel xz xz-devel libffi-devel', shell=True, check=True)
        if ubuntu():
            subprocess.run('sudo apt-get -y update', shell=True, check=True)
            subprocess.run('sudo apt-get -y dist-upgrade', shell=True, check=True)
            subprocess.run('sudo apt-get -y install make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev', shell=True, check=True)

def install_pyenv():
    if macos():
        subprocess.run(['brew', 'install', 'pyenv'], check=True)
    if linux():
        subprocess.run(['rm -rf /tmp/pyenvinst'], shell=True, check=True)
        subprocess.run(['git clone https://github.com/pyenv/pyenv.git /tmp/pyenvinst'], shell=True, check=True)

def install_pyenv_version(version):
    python_build_env = dict(os.environ)
    if macos():
        python_build_env['PATH']=f"/usr/local/opt/tcl-tk/bin:{python_build_env['PATH']}"
        python_build_env['LDFLAGS']=f"-L/usr/local/opt/tcl-tk/lib -mmacosx-version-min={macos_deployment_target}"
        python_build_env['CPPFLAGS']=f"-I/usr/local/opt/tcl-tk/include -mmacosx-version-min={macos_deployment_target}"
        python_build_env['PKG_CONFIG_PATH']="/usr/local/opt/tcl-tk/lib/pkgconfig"
        python_build_env['PYTHON_CONFIGURE_OPTS']="--with-tcltk-includes='-I/usr/local/opt/tcl-tk/include' --with-tcltk-libs='-L/usr/local/opt/tcl-tk/lib -ltcl8.6 -ltk8.6'"
    if linux():
        python_build_env['PATH']=f"/tmp/pyenvinst/plugins/python-build/bin:{python_build_env['PATH']}"
        
    subprocess.run(f'sudo python-build {version} {python_version_destdir()}', shell=True, check=True, env=python_build_env)
        
def output_archive_filename():
        return f'{output_base_name()}.tar.gz'

def create_archive():
    if 'BUILD_ARTIFACTSTAGINGDIRECTORY' in os.environ:
        archive_output_directory = Path(
            os.environ['BUILD_ARTIFACTSTAGINGDIRECTORY'])
    else:
        archive_output_directory = python_destdir() / 'packages'
    archive_output_directory.mkdir(parents=True, exist_ok=True)
    print(f'Creating {output_archive_filename()} in {archive_output_directory}')
    command = [
        'tar',
        '-zcf',
        f'{ archive_output_directory / output_archive_filename() }',  # the tar filename
        f'{ python_version_destdir().relative_to(python_destdir()) }',
    ]
    try:
        # keep the name + version directory in the archive, but not the package name directory
        subprocess.run(command, check=True, cwd=python_destdir())
    except subprocess.CalledProcessError as e:
        if not windows():
            raise e
        command.insert(1, '--force-local')
        # keep the name + version directory in the archive, but not the package name directory
        subprocess.run(command, check=True, cwd=python_destdir())

def main():
    prepare_output_dir()
    if sys.platform == 'win32':
        install_from_msi()
    else:
        install_prerequisites()
        install_pyenv()
        install_pyenv_version(python_version)
    create_archive()

if __name__ == "__main__":
    main()
