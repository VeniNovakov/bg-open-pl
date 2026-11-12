# Analysis notebook

`analysis.ipynb` explores the results: who competes, how strong the field is, where lifts are
missed, how attempts are chosen, and whether lifters who compete again improve. It also checks
how clean the source data is.

## Run it

From the project root, with the virtual environment active:

```bash
pip install -e ".[analysis]"        # pandas, matplotlib, JupyterLab
BGOPL_DATA_DIR=../test_data jupyter lab
```

Open `notebooks/analysis.ipynb` and choose **Run → Run All Cells**.

In VS Code, open the notebook, pick the `.venv` interpreter as the kernel, and set the folder in a
first cell if you need to: `import os; os.environ["BGOPL_DATA_DIR"] = "../test_data"`.

## Which data

The notebook reads every `.xlsx` in the folder named by `BGOPL_DATA_DIR`.
The default is `../test_data`, relative to the `notebooks/` folder.

| Folder | Content |
|---|---|
| `test_data/` | 12 synthetic meets
| `data/` | the real protocols (git-ignored, never committed) |

Start Jupyter from the project root and use paths relative to it (`test_data`). If you start it
inside `notebooks/`, use `../test_data`.

The sample data is random, so the numbers it produces say nothing about real athletes.

## What is in it

1. **Who competes**: meets, sex, divisions, weight classes
2. **Strength**: bodyweight against total, IPF GL points by sex and division
3. **Missed lifts**: success rate by lift and attempt number
4. **Attempt selection**: jumps between attempts, and each lift's share of the total
5. **Progress**: do lifters who compete again improve?
6. **Data quality**: what the validator found in the source files

## Nothing is hardcoded

Divisions, sexes, weight classes and chart ranges are read from the data. The sentences that state
findings are computed by code cells, so they update when meets are added. Only the caveats (for
example "returning lifters are not a random sample") are fixed text. To analyse equipped lifting
instead, set `EQUIPMENT = "equipped"` at the top of the notebook.

## How the data is loaded

```python
from bgopl.analysis import load_frames
lifters, attempts, findings = load_frames("data/")
```

| Table | One row per |
|---|---|
| `lifters` | lifter and meet (division, class, bodyweight, bests, total, points, status) |
| `attempts` | attempt taken (lift, attempt number, weight, good or failed) |
| `findings` | validator finding (meet, code, severity) |

## Privacy

Names are not loaded. Lifters are followed across meets by `lifter_id`, a short hash of sex and
name. That is pseudonymous, not anonymous, so it is still personal data. Keep tables and any
exports derived from real data out of the repository, and clear the outputs before you commit a
notebook that was run on real data (**Edit → Clear Outputs of All Cells**). Charts and counts on
the synthetic samples are safe to share.

## Limits

- Identity is sex plus name, so two people with the same name in a meet are merged. The notebook
  drops names that occur twice in one meet from the progress analysis.
- The progress section only sees people who came back. Lifters who stopped are missing.
- Meets differ in time of year and peaking, so changes between meets are not clean comparisons.
- The notebook reports what the files say. It does not correct source errors.