# Changelog

## [v1.3]

- Add `--use-union-or` to use PEP 604 `X | None` syntax
- Treat `T` as a possible alias for the `typing` module

## [v1.2]

- Restore compatibility with Python 3.8 and older

## [v1.1]

- Added correct handling of `typing.Annotated`

## Making a release

- Bump version in `setup.py`
- Update `CHANGELOG.md`
- `rm -rf build dist`
- `python -m build`
- `twine upload dist/*`
