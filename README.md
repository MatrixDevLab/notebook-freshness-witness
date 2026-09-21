# notebook-freshness-witness

`nbfresh` is a small, dependency-free CI witness for a narrow Jupyter problem:
an `.ipynb` file stores code, outputs, and an execution count, but does not by
itself prove that the visible output belongs to the current source. Notebook
diff tools and execution caches solve adjacent problems; this tool makes the
missing claim explicit.

## First version

Record a manifest from an executed notebook:

```sh
python nbfresh.py record executed.ipynb --manifest executed.nbfresh.json
```

Check a later notebook against that manifest:

```sh
python nbfresh.py check executed.ipynb --manifest executed.nbfresh.json
```

The JSON report distinguishes `fresh_under_manifest`, `source_changed`,
`output_changed`, `missing_output`, and `missing_manifest`. A fresh result is
only a bounded claim: it proves equality with the recorded source/output
hashes, not reproducibility under changed dependencies, files, network data,
or kernels.

## Problem evidence and overlap boundary

- Jupyter's notebook schema defines `execution_count` as a prompt number and
  stores outputs, but does not bind an output to a source hash:
  [nbformat schema](https://github.com/jupyter/nbformat/blob/main/nbformat/v4/nbformat.v4.5.schema.json).
- JupyterLab users still report noisy notebook diffs from outputs and execution
  counts: [issue #9444](https://github.com/jupyterlab/jupyterlab/issues/9444).
- `nbdime` provides notebook diff/merge, while `jupyter-cache` provides an
  execution cache and explicitly lists robust invalidation of external
  dependencies as unfinished work. `nbfresh` is intentionally a static,
  fail-closed witness, not an executor, cache, or notebook merger:
  [nbdime](https://github.com/jupyter/nbdime),
  [jupyter-cache](https://github.com/executablebooks/jupyter-cache).

## Roadmap

1. Keep the manifest schema stable and add fixtures for cell insertions,
   deletions, and notebooks without cell IDs.
2. Add an optional explicitly supplied environment/dependency digest; never
   imply that a source/output match proves external reproducibility.
3. Stop if users need execution, cache invalidation, or rich notebook diffs;
   those belong to the adjacent projects above.

## Validation

```sh
python -m unittest -v
python -m py_compile nbfresh.py
python nbfresh.py --help
```

## Stopping point

This product is useful only if it remains a small, reviewable admission check
for CI or notebook review. It must not become a second notebook executor,
general provenance database, or replacement for `nbdime`/`jupyter-cache`.
