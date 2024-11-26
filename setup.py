# setup.py for command_executor package 

from setuptools import setup
setup(
    name='command_executor',
    version='1.0',
    packages=['command_executor'],
    author="Stefan Nožinić",
    author_email="stefan@lugons.org",
    description="Command executor package enables you to convert any class to a command line tool.",
    license="MIT",
    keywords="command line tool",
    url="https://github.com/fantastic001/CommandExecutor",
    install_requires=[
        'argparse'
    ]
)
