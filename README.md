# no_implicit_optional

A codemod to make your implicit optional type hints PEP 484 compliant.

## Running

This tool will make changes to your code. Make sure you're using version control, like `git`.

```bash
pipx run no_implicit_optional <path>
```

Alternatively, and perhaps more familiarly:
```bash
pip install no_implicit_optional
no_implicit_optional <path>
```

To make this tool use PEP 604 `X | None` syntax instead of `Optional[X]`, use the
`--use-union-or` flag. Note that this syntax is only fully supported on Python 3.10 and newer.

## What's going on?

By default, mypy 0.982 and earlier allowed eliding `Optional` for arguments with default values of
`None`. From experience, this was found to be a source of confusion and bugs.

In 2018, PEP 484 was updated to require the explicit use of `Optional` (or a `Union` with `None`)
and mypy enforces this when run using `mypy --strict` or `mypy --no-implicit-optional`.
Similarly, other type checkers like pyright do not recognise implicit `Optional` at all.

Here's what this looks like in practice:

```python
def bad(x: int = None):
    ...

def good(x: Optional[int] = None):
    ...

def good(x: Union[int, None] = None):
    ...

# PEP 604 syntax, requires Python 3.10+ or `from __future__ import annotations`
def good(x: int | None = None):
    ...
```

Anyway, mypy is changing its default to match PEP 484 and disallow implicit `Optional`. In order
to make the transition easier, this tool will try to automatically fix your code, building off
of [libcst](https://libcst.readthedocs.io/en/latest/) to do so.

Also refer to:
- https://peps.python.org/pep-0484/#union-types
- https://github.com/python/mypy/issues/9091
- https://github.com/python/mypy/pull/13401


## I don't want to change my code

Use `mypy --implicit-optional` or set `implicit_optional = True` in your mypy config.
