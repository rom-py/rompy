# Developer Guide

Welcome to the rompy developer documentation. This section provides detailed technical information about contributing to the Rompy project and understanding the internal architecture.

## Getting Started with Development

To get started developing for Rompy:

1. **Fork and clone the repository**
2. **Set up your development environment** - See the [Installation Guide](../installation.md) for setup instructions
3. **Run the tests** - Make sure you can run the test suite before making changes
4. **Read the contribution guidelines** - See the [Contribution Guidelines](../contributing.md) for important information

## Key Architecture Concepts

For detailed information about Rompy's architecture, see:

- [**Architecture Overview**](../architecture_overview.md) - High-level system architecture
- [**Plugin Architecture**](../plugin_architecture.md) - Extension mechanisms and plugin system
- [Backend Reference](backend_reference.md) - Technical details for backend development

## Development Process

### Testing

Rompy uses pytest for testing. Before submitting changes:

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=rompy
```

### Code Style

- Follow PEP 8 guidelines
- Use type hints for all public functions
- Write docstrings using Google style

### Commit Messages

- Use present tense ("Add feature" not "Added feature")
- Limit first line to 72 characters
- Reference issues when applicable

## Common Development Tasks

### Adding New Configuration Types

When adding new configuration types, extend the appropriate base classes and consider using Pydantic discriminated unions for type safety.

### Adding New Backends

To add new execution backends, implement the appropriate interface and register via entry points.

### Extending Model Support

To add support for new ocean models, follow the plugin architecture patterns described in the [Plugin Architecture](../plugin_architecture.md) documentation.

## Need Help?

- Check the [FAQ](../faq.md) for common developer questions
- Join the discussion on GitHub issues
- For complex architectural questions, review the [Architecture Overview](../architecture_overview.md)