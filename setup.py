import os
import subprocess
import sys

from setuptools import setup, find_packages, Command

tests_require = ["pytest", "pytest-cov", "codecov", "asynctest", "coverage", "flake8", "black", "aiohttp", "dataclasses_json"]

here = os.path.abspath(os.path.dirname(__file__))


class BaseCommand(Command):
    """Base Command"""

    user_options = []

    @staticmethod
    def status(s):
        """Prints things in bold."""
        print("\033[1m{0}\033[0m".format(s))

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def _run(self, s, command):
        try:
            self.status(s + "\n" + " ".join(command))
            subprocess.check_call(command)
        except subprocess.CalledProcessError as error:
            sys.exit(error.returncode)


class ValidateCommand(BaseCommand):
    """Support setup.py validate."""

    description = "Run Python static code analyzer (flake8), formatter (black) and unit tests (pytest)."

    def run(self):
        self._run(
            "Installing test dependencies…",
            [sys.executable, "-m", "pip", "install"] + tests_require,
        )
        self._run("Running black…", [sys.executable, "-m", "black", f"{here}/flyte"])
        self._run("Running flake8…", [sys.executable, "-m", "flake8", f"{here}/flyte"])
        self._run(
            "Running pytest…",
            [
                sys.executable,
                "-m",
                "pytest",
                f"--cov=flyte",
                "tests/",
            ],
        )


setup(name='flyte-client',
      version='0.1',
      url='https://github.expedia.biz/iasensiomejia/python-flyte-client',
      license='MIT',
      description='Flyte client',
      packages=find_packages(exclude=['tests']),
      long_description=open('README.md').read(),
      install_requires=[
          "aiohttp>3.5.2",
          "dataclasses-json==0.3.2"
      ],
      extras_require={
          'testing': 'pytest',
          'coverage': 'coverage',
      },
      setup_requires=["pytest-runner"],
      test_suite="tests",
      tests_require=tests_require,
      cmdclass={"validate": ValidateCommand},
      zip_safe=False)
