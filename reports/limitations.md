# Limitations

- The dataset is a de-identified single HCP extract and may not generalise to other hospitals, years, or coding practices.
- The target is billed episode charge, not true economic or clinical cost.
- No external cost, outcome, or audited finance validation was available.
- Several features used by the strongest model, including LOS, same-day status, procedure count, comorbidity count, final MDC/DRG-derived grouping, and mode of separation, are known only after episode completion or final coding.
- Therefore the current model is best framed as completed episode charge benchmarking, expected charge estimation, and unusual charge review, not admission-time early warning.
- Random train/test splitting may overestimate future generalisation; a time-based split is reported separately as a more realistic sensitivity check.
- Associations in EDA and SHAP are not causal evidence.
- Charge distribution is highly right-skewed; log-transforming the target reduces the influence of extreme values but high-charge episodes remain clinically and commercially important.
- MAPE is reported only as a supporting metric because low-charge episodes can make percentage error unstable.
- Coding practices may influence diagnosis, procedure, comorbidity, and DRG-derived features.
- Row-level worst-prediction outputs are local review artifacts and should not be published in a public repository.
