# Contributing to Shadow AI

First off, thanks for taking the time to contribute! ❤️

Shadow AI is built by the community, for the community. Every contribution helps make it better for hackers, dads, and tired people who just want it to work.

## 🎯 Quick Links

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Style Guidelines](#style-guidelines)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)

---

## 📜 Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inspiring community for all. We expect all participants to:

- **Be respectful** - Value each other's ideas, styles and viewpoints
- **Be direct but professional** - Constructive criticism only
- **Be inclusive** - Welcome newcomers and encourage collaboration
- **Assume good faith** - Believe contributors have the project's best interests in mind

### Not Acceptable

- Harassment, discriminatory jokes, or personal attacks
- Trolling or insulting/derogatory comments
- Public or private harassment
- Publishing others' private information without permission

---

## 🤝 How Can I Contribute?

### Reporting Bugs

**Before submitting**: Search [existing issues](https://github.com/Wolf-G88/Shadow-AI/issues) to avoid duplicates.

**When reporting**:
1. Use a clear, descriptive title
2. Describe the exact steps to reproduce
3. Provide specific examples (commands run, error messages)
4. Include your environment:
   - OS: Ubuntu 22.04, etc.
   - Python version: `python3 --version`
   - Shadow AI version: Check settings or `dpkg -l | grep shadow-ai`
5. Attach logs if available

**Template**:
```markdown
## Bug Description
[Clear description of the bug]

## Steps to Reproduce
1. Launch Shadow AI
2. Type `!ls`
3. See error

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Environment
- OS: Ubuntu 22.04
- Python: 3.12
- Shadow AI: v2.0.2

## Additional Context
[Screenshots, logs, etc.]
```

### Suggesting Features

**Before suggesting**: Check the [roadmap](docs/ROADMAP_v2.0.3.md) and [existing issues](https://github.com/Wolf-G88/Shadow-AI/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement).

**When suggesting**:
1. Use a clear, descriptive title
2. Explain the problem this feature solves
3. Describe your proposed solution
4. Consider alternative solutions
5. Explain why this would be useful to most users

**Template**:
```markdown
## Feature Description
[Clear description]

## Problem it Solves
[Why is this needed?]

## Proposed Solution
[How should it work?]

## Alternatives Considered
[Other approaches?]

## Additional Context
[Mockups, examples, etc.]
```

### Contributing Code

We love pull requests! Here's how to contribute:

1. **Fork the repository**
2. **Create a branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** (see [Development Setup](#development-setup))
4. **Test your changes**: Run `python3 test_fixes.py`
5. **Commit**: Follow our [commit guidelines](#commit-messages)
6. **Push**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

### Contributing Documentation

Documentation is as important as code! You can help by:

- Fixing typos or unclear explanations
- Adding examples or use cases
- Translating documentation
- Improving the README or guides

Just follow the same PR process as code contributions.

---

## 🛠️ Development Setup

### Prerequisites

- Python 3.8+ (`python3 --version`)
- Git (`git --version`)
- Ollama (optional, for local models)

### Initial Setup

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/Shadow-AI.git
cd Shadow-AI

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install development dependencies
pip install pytest black flake8

# 5. Run Shadow AI
python3 main.py
```

### Project Structure

```
Shadow-AI/
├── main.py                  # Entry point
├── output/
│   └── gui.py              # Main GUI (streaming, safety gates)
├── core/
│   ├── engine.py           # Processing engine
│   ├── unified_llm.py      # API abstraction (15 providers)
│   ├── config.py           # Configuration manager
│   └── memory.py           # Context management
├── input/
│   ├── file.py             # File handling
│   └── text.py             # Text input
├── docs/                    # Documentation
├── tests/                   # Test files
└── debian-package/          # .deb packaging
```

### Running Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
python3 test_fixes.py

# Run specific module tests
python3 -m pytest tests/test_config.py

# Syntax check
python3 -m py_compile output/gui.py core/unified_llm.py
```

### Development Workflow

1. **Before coding**: Pull latest changes
   ```bash
   git checkout main
   git pull upstream main
   ```

2. **Create feature branch**: Name it descriptively
   ```bash
   git checkout -b feature/add-command-history
   # or
   git checkout -b fix/model-selection-bug
   ```

3. **Make changes**: Edit code, add features

4. **Test locally**: Ensure nothing breaks
   ```bash
   python3 test_fixes.py
   python3 main.py  # Manual testing
   ```

5. **Commit**: Follow commit message guidelines

6. **Push and PR**: Submit for review

---

## 📝 Style Guidelines

### Python Code Style

We follow **PEP 8** with some exceptions:

- **Line length**: 100 characters (not 79)
- **Docstrings**: Use triple quotes, describe params and return
- **Type hints**: Encouraged but not required

**Example**:
```python
def assess_command_risk(self, command: str) -> str:
    """
    Assess risk level of shell command.
    
    Args:
        command: Shell command to evaluate
        
    Returns:
        Risk level: 'critical', 'high', 'medium', or 'safe'
    """
    # Check critical patterns
    for pattern in self.critical_patterns:
        if pattern in command:
            return 'critical'
    # ... rest of logic
```

### Formatting Tools

```bash
# Auto-format with Black
black output/gui.py

# Check style with flake8
flake8 output/gui.py --max-line-length=100
```

### Comments

- **Do**: Explain *why*, not *what*
  ```python
  # Use v1beta for Gemini 1.5 models (v1 returns 404)
  api_version = "v1beta" if "1.5" in model else "v1"
  ```

- **Don't**: State the obvious
  ```python
  # Set x to 5
  x = 5  # Bad comment
  ```

### Naming Conventions

- **Functions**: `snake_case` (e.g., `assess_command_risk`)
- **Classes**: `PascalCase` (e.g., `UnifiedLLM`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_TOKENS`)
- **Private**: Prefix with `_` (e.g., `_process_queue`)

---

## 💬 Commit Messages

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Formatting, missing semicolons, etc. (no code change)
- **refactor**: Code restructuring (no feature change)
- **test**: Adding tests
- **chore**: Maintenance (dependencies, build, etc.)

### Examples

**Good commits**:
```
feat(gui): add command history with up/down arrow navigation

Implements a command history buffer that stores the last 50 commands.
Users can now press Up/Down arrows to recall previous commands.

Closes #42
```

```
fix(unified_llm): use v1beta endpoint for Gemini 1.5 models

Gemini 1.5 Pro and Flash require the v1beta API endpoint.
Added dynamic version selection based on model name.

Fixes #37
```

```
docs(readme): add troubleshooting section for model loading

Users were confused about why models weren't appearing. Added
step-by-step guide to pull models and restart the app.
```

**Bad commits**:
```
Updated stuff          # Too vague
Fix bug                # Which bug?
asdf                   # Not descriptive
```

### Co-Author Credit

If you pair-programmed or collaborated:
```
feat(safety): implement three-tier command safety system

Co-authored-by: Alice <alice@example.com>
Co-authored-by: Bob <bob@example.com>
```

---

## 🔄 Pull Request Process

### Before Submitting

1. **Update documentation** if you changed interfaces
2. **Add tests** for new features
3. **Run all tests**: `python3 test_fixes.py`
4. **Update ROADMAP** if implementing a planned feature
5. **Check code style**: `flake8 --max-line-length=100`

### PR Template

When opening a PR, include:

```markdown
## Description
[What does this PR do?]

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Related Issues
Closes #42
Fixes #37

## How Has This Been Tested?
[Describe your testing process]

## Checklist
- [ ] My code follows the style guidelines
- [ ] I have performed a self-review
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
```

### Review Process

1. **Automated checks** run first (syntax, tests)
2. **Maintainers review** within 1-3 days
3. **Address feedback** if requested
4. **Approve and merge** once checks pass

### After Merge

- Delete your feature branch (GitHub can do this automatically)
- Update your local repository:
  ```bash
  git checkout main
  git pull upstream main
  ```

---

## 🎯 Good First Issues

Looking for something to work on? Check issues labeled [`good first issue`](https://github.com/Wolf-G88/Shadow-AI/labels/good%20first%20issue).

**Easy contributions**:
- Fix typos in documentation
- Add examples to QUICK_REFERENCE.md
- Improve error messages
- Add unit tests

**Medium contributions**:
- Implement command history (see ROADMAP)
- Add RAM monitoring for GGUF
- Improve status bar animations

**Advanced contributions**:
- Implement quantum backend selection
- Add new API providers
- Create clickable file paths

---

## 🏆 Recognition

Contributors are recognized in:
- **README.md** - Special Thanks section
- **COMPLETION_SUMMARY.md** - Contributors list
- **Git history** - Your commits live forever
- **Releases** - Mentioned in release notes

---

## 📞 Questions?

- **General**: [GitHub Discussions](https://github.com/Wolf-G88/Shadow-AI/discussions)
- **Security**: Email wolfking@shadowai.local (for vulnerabilities only)
- **Documentation**: Check [docs/](docs/) directory

---

## 🙏 Thank You!

Every contribution, no matter how small, makes Shadow AI better for everyone. Whether you're fixing a typo, adding a feature, or helping others in discussions—you're part of the Wolf Clan.

**Built for hackers, dads, and tired people who just want it to work.**

---

**Last Updated**: January 2, 2026  
**Version**: 2.0.2
