# liboqs-python Ubuntu Install Notes

Install system dependencies:

```bash
sudo apt update
sudo apt install -y build-essential cmake ninja-build libssl-dev python3-dev python3-venv git
```

Create and activate a local virtual environment:

```bash
python3 -m venv .venv
PATH=.venv/bin:$PATH python -m pip install -U pip
PATH=.venv/bin:$PATH python -m pip install -r backend/requirements.txt
```

If the project requirements file is not available, install the Python binding directly:

```bash
PATH=.venv/bin:$PATH python -m pip install liboqs-python
```

The Python import name is `import oqs`. Test the installation with:

```bash
PATH=.venv/bin:$PATH python -c "import oqs; print(oqs.get_enabled_sig_mechanisms())"
```
