# outputs/: notes for readers and for Task 5

Written by `python -I src/run_all.py` (plan §10.3). Reruns are byte-identical. Every file
carries a `spec` column where it reports sensitivities.

## Denominator bases (plan §12.1, §12.3 note 1)

- `main`: 2018 and 2019 their own tables; 2021 and 2023 A1.4 net notified; 2022 A1.6
  male + female + transgender.
- `denominator_a1_2_registered`: the registered A1.2 N for 2021-2023, with its own draw
  sets. It is reported for every C1- and E1-dependent output:
  - cascade;
  - gaps;
  - priority (with this basis's own falling-coverage flag);
  - decomposition;
  - scenario;
  - trend;
  - the H2 companions (2022 vs 2018, 2022 vs 2019, 2023 vs 2018);
  - leave_one_out (the E1 act-now chain, 2023 and 2022).
- `denominator_2022_from_percent`: the 2022 N back-calculated from the printed
  percentage, for the 2022 C1- and E1-dependent outputs.
- **Main-basis only:** the k-grid (k = 1, 1.5, 2, the median and p90 benchmarks, the
  2019 + 2021 pool, the simple reference, shrinkage off), the NFHS x0.8 / x1.2 scaling,
  and the State-specific p_u perturbation (`perturbation.csv`) are computed on the main
  basis only.

## NFHS scaling (plan §8.11)

Under p_u x f, R = y / (k p_u) scales exactly by 1/f, at every fixed k.

Under k_b, the scaling cancels: k_b scales by 1/f, so k_b p_u is unchanged. E1, E2, C2,
H3, the decomposition and the scenario are therefore not rerun.

## Wording

The scenario is "an illustration, not a forecast". Its interval reflects binomial
uncertainty in coverage and yield only.

"Likely under-detection" is used only for the k = 1 fixed rule. Units below k_b are
described as "identification below the benchmark", a relative statement. About a
quarter of units lie above k_b by construction.
