# cb-D1 ledger

## RED (unchanged su.py, base 62c91293)
```
tests/test_su_finite.py:135: AssertionError
=========================== short test summary info ============================
FAILED tests/test_su_finite.py::test_number_rejects_non_finite[nan] - Asserti...
FAILED tests/test_su_finite.py::test_number_rejects_non_finite[inf] - Asserti...
FAILED tests/test_su_finite.py::test_number_rejects_non_finite[-inf] - Assert...
FAILED tests/test_su_finite.py::test_non_finite_money_rate_gives_none_not_nan[NaN]
FAILED tests/test_su_finite.py::test_non_finite_money_rate_gives_none_not_nan[Infinity]
FAILED tests/test_su_finite.py::test_non_finite_money_rate_gives_none_not_nan[-Infinity]
FAILED tests/test_su_finite.py::test_non_finite_site_price_gives_none[NaN] - ...
FAILED tests/test_su_finite.py::test_non_finite_site_price_gives_none[Infinity]
FAILED tests/test_su_finite.py::test_non_finite_site_price_gives_none[-Infinity]
FAILED tests/test_su_finite.py::test_non_finite_factor_is_unknown[NaN] - asse...
FAILED tests/test_su_finite.py::test_non_finite_factor_is_unknown[Infinity]
FAILED tests/test_su_finite.py::test_non_finite_factor_is_unknown[-Infinity]
FAILED tests/test_su_finite.py::test_non_finite_task_value_is_unknown[cpus-nan]
FAILED tests/test_su_finite.py::test_non_finite_task_value_is_unknown[cpus-inf]
FAILED tests/test_su_finite.py::test_non_finite_task_value_is_unknown[realtime-nan]
FAILED tests/test_su_finite.py::test_non_finite_task_value_is_unknown[realtime-inf]
FAILED tests/test_su_finite.py::test_non_finite_usd_rate_is_none[Infinity] - ...
FAILED tests/test_su_finite.py::test_non_finite_price_or_su_gives_no_dollars[NaN]
FAILED tests/test_su_finite.py::test_non_finite_price_or_su_gives_no_dollars[Infinity]
FAILED tests/test_su_finite.py::test_non_finite_price_or_su_gives_no_dollars[-Infinity]
FAILED tests/test_su_finite.py::test_the_finite_check_is_the_one_in_cloud_cost
21 failed, 15 passed in 3.06s
```
