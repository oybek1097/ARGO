# Releasing `argo-brain` to PyPI

This runbook covers cutting a release of the `argo-brain` Python package to
[PyPI](https://pypi.org/project/argo-brain/). It targets the **v3.0.0 GA**
release of ARGO Agent v3.0.

> Status: ARGO is alpha approaching its GA. Treat the first GA upload with
> care — there is no second chance to overwrite a version on PyPI.

## Prerequisites

- Python 3.12 with the `build` and `twine` tools:
  ```bash
  python -m pip install --upgrade build twine
  ```
- Repository checked out clean (`git status` shows no changes) on `main`.
- All tests green:
  ```bash
  cd argo-brain
  python3 -m unittest discover -s tests
  python3 -m argo_brain selftest
  ```
- Maintainer access to the `argo-brain` PyPI and TestPyPI projects (only
  needed for the manual upload path; the trusted-publishing path uses CI).

## Recommended path: trusted publishing (OIDC)

The preferred way to release is **PyPI trusted publishing** — no long-lived
API tokens are stored anywhere. The GitHub Actions workflow
`.github/workflows/release-pypi.yml` builds the artifacts and publishes them
via OIDC when a `v*` tag is pushed.

One-time setup on PyPI and TestPyPI:

1. On <https://pypi.org/manage/account/publishing/> add a *pending publisher*
   for the `argo-brain` project:
   - Owner: `oybek1097`
   - Repository: `ARGO`
   - Workflow filename: `release-pypi.yml`
   - Environment: `pypi`
2. Repeat on <https://test.pypi.org/manage/account/publishing/> with
   environment `testpypi`.
3. In the GitHub repo, create the `pypi` and `testpypi`
   [environments](https://docs.github.com/en/actions/deployment/targeting-different-environments)
   (Settings → Environments). Optionally add required reviewers to `pypi`.

After setup, releasing is just the **tag** step below — CI does the rest.

## Release steps

### 1. Reconcile and bump the version

The in-repo `argo-brain/pyproject.toml` carries the development version.
The GA metadata lives in `release/pypi/pyproject.release.toml`.

- Reconcile `argo-brain/pyproject.toml` against
  `release/pypi/pyproject.release.toml` (classifiers, URLs, keywords,
  `build-system`, extras).
- Set the version in **both** of these to the release version (e.g. `3.0.0`):
  - `argo-brain/pyproject.toml` → `[project] version`
  - `argo-brain/argo_brain/__init__.py` → `__version__`
- Copy `release/pypi/MANIFEST.in` into `argo-brain/MANIFEST.in`.
- Update `CHANGELOG.md` with the release notes and date.
- Commit:
  ```bash
  git commit -am "release: argo-brain 3.0.0"
  ```

### 2. Build the distributions

```bash
./scripts/build-pypi.sh
```

This produces an sdist (`.tar.gz`) and a wheel (`.whl`) under
`argo-brain/dist/` and runs `twine check` on them. To build manually:

```bash
cd argo-brain
rm -rf dist build *.egg-info
python -m build
```

### 3. Validate the artifacts

```bash
cd argo-brain
twine check dist/*
```

`twine check` must report `PASSED` for every file. Also smoke-test the wheel
in a throwaway virtual environment:

```bash
python -m venv /tmp/argo-rc && . /tmp/argo-rc/bin/activate
pip install argo-brain/dist/argo_brain-3.0.0-py3-none-any.whl
argo-brain version
python -m argo_brain selftest
deactivate && rm -rf /tmp/argo-rc
```

### 4. TestPyPI dry-run

Always publish to TestPyPI first and install from there.

```bash
twine upload --repository testpypi argo-brain/dist/*
```

Then verify a clean install (the `--extra-index-url` lets pip resolve any
real dependencies pulled in by extras):

```bash
python -m venv /tmp/argo-test && . /tmp/argo-test/bin/activate
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ argo-brain==3.0.0
argo-brain version
deactivate && rm -rf /tmp/argo-test
```

### 5. Upload to real PyPI

Preferred — let CI do it via trusted publishing (go to step 6).

Manual fallback (requires an API token):

```bash
twine upload argo-brain/dist/*
```

### 6. Tag and push

```bash
git tag -a v3.0.0 -m "ARGO Agent v3.0.0 GA"
git push origin main
git push origin v3.0.0
```

Pushing the `v3.0.0` tag triggers `.github/workflows/release-pypi.yml`,
which builds, runs the TestPyPI dry-run job, and — if that succeeds —
publishes to PyPI via OIDC.

### 7. GitHub release

```bash
gh release create v3.0.0 \
    --title "ARGO Agent v3.0.0 GA" \
    --notes-file release-notes.md \
    argo-brain/dist/*
```

Or create it from the GitHub UI, copying the relevant `CHANGELOG.md` section.

## Post-release checklist

- [ ] `pip install argo-brain` from a clean environment installs `3.0.0`.
- [ ] The PyPI project page renders the README correctly.
- [ ] The GitHub release is published and lists the artifacts.
- [ ] Bump the in-repo `version` to the next development cycle
      (e.g. `3.1.0.dev0`).

## If something goes wrong

- A PyPI version **cannot be overwritten or re-uploaded**. If a release is
  broken, yank it on PyPI and publish a fixed patch version (`3.0.1`).
- TestPyPI uploads can be deleted; use TestPyPI freely for rehearsal.
- If the CI publish job fails on OIDC, re-check the pending-publisher
  configuration (owner, repo, workflow filename, environment name).
