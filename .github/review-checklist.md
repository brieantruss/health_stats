# PR Review Checklist (health_stats)

Use this when reviewing changes in this repo.

## 1) Scope and intent
- [ ] PR title/description clearly states purpose.
- [ ] Diff matches stated scope.
- [ ] No unrelated file churn.

## 2) Security and access
- [ ] No secrets committed (.env, keys, tokens).
- [ ] Public endpoints were not unintentionally opened.
- [ ] IAM/auth changes are intentional and documented.

## 3) Streamlit/API changes
- [ ] UI flow still works for add/view/manage records.
- [ ] API error handling remains user-friendly.
- [ ] Any removed UI capability is explicitly called out.

## 4) ETL changes
- [ ] Extract scripts still resolve expected source folders.
- [ ] Parser regex/header mapping changes are backward compatible.
- [ ] Path/host changes are portable and environment-safe.

## 5) Dataform/BigQuery changes
- [ ] Dataform compile succeeds.
- [ ] Dataset location/config is correct (US vs regional).
- [ ] View/table names and semantics remain stable.

## 6) Operational safety
- [ ] Logging remains useful and not noisy.
- [ ] Failure modes are handled (timeouts/network/empty files).
- [ ] Rollback path is clear.

## 7) Documentation
- [ ] README/docs updated if workflow changed.
- [ ] Screenshots/instructions still match actual UI.
