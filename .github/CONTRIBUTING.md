# Contributing to OpenWarrant

Thank you for your interest in contributing to OpenWarrant! This project benefits from domain expertise across healthcare, finance, and insurance.

## How to Contribute

### Reporting Issues

- Use GitHub Issues for bug reports and feature requests
- Include steps to reproduce for bugs
- For security vulnerabilities, please email privately rather than opening a public issue

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Add or update tests as appropriate
5. Ensure all tests pass:
   - Python: `cd packages/core-python && pytest`
   - TypeScript: `cd packages/core-typescript && npx vitest run`
6. Submit a pull request

### Code Style

- **Python**: Follow PEP 8. Use type hints. Target Python 3.10+.
- **TypeScript**: Use strict mode. Prefer interfaces over type aliases for public APIs.

### Warrant Templates

We welcome warrant template contributions for new regulated domains. Templates should:

- Follow the schema defined in `docs/warrant-schema.yaml`
- Include realistic conditions relevant to the domain
- Reference applicable regulations in the `notes` field
- Be placed in `examples/warrants/`

### Areas Where We Need Help

- **Domain experts** in healthcare, finance, insurance to review and author warrant templates
- **Security researchers** to audit the cryptographic model
- **Framework developers** to build adapters for agent frameworks
- **Documentation** improvements and tutorials

## Development Setup

```bash
# Python
cd packages/core-python
pip install -e ".[dev]"
pytest

# TypeScript
cd packages/core-typescript
npm install
npx vitest run
```

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.
