# test

First, install [`tox`](https://tox.readthedocs.io/en/latest/):

```
pip3 install tox
```

To run the tests:

```
tox
```

This runs `mypy` over the `moneybot/` and `tests/` directories, then invokes [`pytest`](https://docs.pytest.org/en/latest/contents.html) on the `tests/` directory.

To recreate the testing environment (necessary when dependency versions change), add `-r` or `--recreate`. To run `pytest` with more detailed output, add `-e verbose`.
