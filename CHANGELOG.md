# Changelog

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
