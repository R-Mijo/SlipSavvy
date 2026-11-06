# Contributing

Use Python 3.11 or newer. This project has no third-party runtime or test dependencies.

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
```

Include a reproducible failing example for a bug fix. Use synthetic data. Keep actual identifiers, credentials, restoration maps and private source documents out of issues, commits and test fixtures. Explain modeling or trust-boundary assumptions in changes that affect them.
