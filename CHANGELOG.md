# Changelog

## [v1.1]

- Added correct handling of `typing.Annotated`

## Making a release

- Bump version in `setup.py`
- Update `CHANGELOG.md`
- `python -m build`
- `twine upload dist/*`
