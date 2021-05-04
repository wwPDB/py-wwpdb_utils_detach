# OneDep Detached Process Support Utilities

master: [![Build Status](https://dev.azure.com/wwPDB/wwPDB%20Python%20Projects/_apis/build/status/wwPDB.py-wwpdb_utils_detach?branchName=master)](https://dev.azure.com/wwPDB/wwPDB%20Python%20Projects/_build/latest?definitionId=9&branchName=master)

develop: [![Build Status](https://dev.azure.com/wwPDB/wwPDB%20Python%20Projects/_apis/build/status/wwPDB.py-wwpdb_utils_detach?branchName=develop)](https://dev.azure.com/wwPDB/wwPDB%20Python%20Projects/_build/latest?definitionId=9&branchName=develop)

## Introduction

This repository povides utilities used by detached services

### Installation

Download the library source software from the project repository:

```bash

git clone --recurse-submodules https://github.com/wwpdb/py-wwpdb_utils_detach.git

```

Optionally, run test suite using the Tox test runner

```bash
python setup.py test

or simply run

tox

Installation is via the program [pip](https://pypi.python.org/pypi/pip).

```bash
pip install wwpdb.utils.detach

or from the local repository:

pip install .
