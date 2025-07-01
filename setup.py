# setup.py for command_executor package 

from setuptools import setup
setup(
    name='orgasm-package',
    version='1.5',
    packages=['orgasm'],
    author="Stefan Nožinić",
    author_email="stefan@lugons.org",
    description="Optimized Runtime for Generating Apps, Servers and Modules. ORGASM enables you to convert any class to a command line tool.",
    license="MIT",
    keywords="command line tool",
    url="https://github.com/fantastic001/ORGASM",
    install_requires=[
        'argparse',
        "argcomplete"
    ]
)
