from setuptools import setup, find_packages
import platform
import sys

def get_requirements():
    with open('requirements.txt') as f:
        requirements = f.read().splitlines()
    return requirements

def check_nmap_installation():
    import subprocess
    try:
        subprocess.run(['nmap', '-V'], capture_output=True, check=True)
        print('✓ Nmap is installed')
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        system = platform.system().lower()
        if system == 'windows':
            print('⚠ Nmap is not installed. Please download and install it from:')
            print('https://nmap.org/download.html#windows')
        else:  # Linux/Unix systems
            print('⚠ Nmap is not installed. Install it using your package manager:')
            print('Ubuntu/Debian: sudo apt-get install nmap')
            print('Fedora: sudo dnf install nmap')
            print('Arch Linux: sudo pacman -S nmap')
        return False

def main():
    # Check Python version
    if sys.version_info < (3, 7):
        sys.exit('Python 3.7 or higher is required')

    # Check Nmap installation
    if not check_nmap_installation():
        sys.exit('Please install Nmap before proceeding')

    # Setup the package
    setup(
        name='network_monitor_bot',
        version='1.0.0',
        packages=find_packages(),
        install_requires=get_requirements(),
        python_requires='>=3.7',
        author='Your Name',
        description='A network monitoring bot with Discord notifications',
    )

if __name__ == '__main__':
    main()