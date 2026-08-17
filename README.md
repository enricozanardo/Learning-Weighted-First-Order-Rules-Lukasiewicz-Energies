# Numerical validation — paper7 companion code

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21980237.svg)](https://doi.org/10.5281/zenodo.21980237)

Companion code for the validation section of

> Zanardo, E. & Ragusa, M. A. (2026). *Learning Weighted First-Order Rules under
> Piecewise-Linear Łukasiewicz Energies: Structure Updates and Subgradient Weight
> Optimisation*.

## Quick start

```bash
git clone https://github.com/enricozanardo/Learning-Weighted-First-Order-Rules-Lukasiewicz-Energies.git
cd Learning-Weighted-First-Order-Rules-Lukasiewicz-Energies
python3 toy_induction_validation.py
```

Dependencies: Python 3.10+ standard library only. Wall-clock time: ≈ 0.12 s on a single CPU core.

## What is reproduced

| Quantity | Protocol | Reference (committed) |
|---|---|---|
| Pedagogical Q vs P scores | probe \(s=0.8\) | Table in manuscript |
| Monte Carlo discrimination | seeds 42–44; 200 trials × 5 constants | mean accept(true)=1.00; accept(distractor)≈0.02 |
| Closed-form vs PGD | 100 trials, seed 44, 2000 steps, \(\eta=0.05\) | \(\max\|s_{\mathrm{GD}}-s^\star\|<10^{-12}\) |
| Thresholds | \(\tau_s=0.55\), \(\tau_+=0.6\), \(\tau_\Delta=0.2\) | LIMEN `InductionConfig` defaults |

Canonical output: `reference_results.json`. Live runs write `results.json` and `plot_data.json` (gitignored).

## File layout

```
├── CITATION.cff
├── LICENSE
├── README.md
├── toy_induction_validation.py
└── reference_results.json
```

## Releases & archival

- **Version DOI (cite this):** https://doi.org/10.5281/zenodo.21980237
- **Concept DOI (latest):** https://doi.org/10.5281/zenodo.21980236
- **GitHub:** https://github.com/enricozanardo/Learning-Weighted-First-Order-Rules-Lukasiewicz-Energies

## Citation

```bibtex
@misc{zanardo2026inductionvalidation,
  author       = {Zanardo, Enrico and Ragusa, Maria Alessandra},
  title        = {Numerical validation for ``Learning Weighted First-Order Rules
                  under Piecewise-Linear {\L}ukasiewicz Energies''},
  year         = {2026},
  howpublished = {Software, Zenodo},
  doi          = {10.5281/zenodo.21980237},
  url          = {https://doi.org/10.5281/zenodo.21980237},
  note         = {Concept DOI 10.5281/zenodo.21980236 resolves to the latest deposit}
}
```

## License

MIT — see [LICENSE](LICENSE).
