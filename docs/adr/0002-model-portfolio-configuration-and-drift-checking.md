# 0002: Interactive Model Portfolio Configuration and Portfolio Drift Checking

- **Status:** accepted
- **Labels:** `ready-for-agent`, `v0.12`

## Problem Statement

An investor managing their wealth across the three independent portfolio buckets (**Safety Net Portfolio**, **Long Term Portfolio**, and **Aggressive Portfolio**) currently has limited control over how each **Model Portfolio** is configured and monitored from the command line:

1. **Rigid Preset-Only Configuration:** During **Vault Initialization**, the user can only select one of four fixed presets and a global **Single-Stock Concentration** cap. There is no interactive way—either during initial setup or at any later time—to customize individual **Target Allocation** weights, configure secondary **Allocation Layers** (sectors or individual holdings), or set custom **Tolerance Corridor** percentages at the portfolio or individual **Target Allocation** level.
2. **Overly Strict 100% Layer Sum Constraint:** The configuration schema currently rejects any **Allocation Layer** whose **Target Allocation** weights sum to less than `100.0%`. Investors who only want to enforce targets on specific pillars (for example, `30%` Equities and `30%` Bonds, leaving the remaining `40%` unconstrained) cannot express this without inventing dummy targets.
3. **Missing CLI Portfolio Drift Checker & Overloaded Terminology:** While an in-note dashboard view calculates rebalancing status inside Obsidian, there is no standalone Python script or unified runner command that evaluates **Portfolio Drift** against each **Model Portfolio**. Furthermore, the existing asset-level alert rule named "Allocation Drift" only checks **Single-Stock Concentration** (whether a single equity exceeds `15%` of total wealth) and tags individual asset notes, rather than evaluating portfolio-level **Tolerance Corridor** breaches.
4. **Noisy Warnings on Empty Portfolios and Micro-Deltas:** The existing dashboard view raises rebalancing warnings even when a portfolio bucket has zero **Base Value** (such as in a fresh **Clean Vault**) or when the required trade delta in **Base Currency** is smaller than the configured minimum trade threshold.

## Solution

We will introduce a unified interactive **Model Portfolio** configurator and a dedicated portfolio-level **Portfolio Drift** evaluation engine, aligned with the Obsidian dashboard views:

1. **Unified Interactive Model Portfolio Configurator:** Available both during **Vault Initialization** (Step 4) and on demand at any time via a standalone CLI command and unified runner flag. The wizard allows selecting a starter preset or retaining current settings, and optionally entering a guided customization flow for any portfolio bucket (**Safety Net Portfolio**, **Long Term Portfolio**, **Aggressive Portfolio**) to configure rebalancing strategy, default **Tolerance Corridor**, minimum trade threshold, **Allocation Layers** (asset classes, sectors, individual holdings), target weights, and per-target **Tolerance Corridor** overrides, with a diff preview before non-destructive YAML persistence.
2. **Flexible Allocation Layer Validation (`<= 100%`):** Relax **Allocation Layer** validation so that configured **Target Allocation** weights must be greater than `0%` and sum to at most `100.0%` (`0 < sum <= 100.0%`). Any remaining percentage up to `100%` is treated as unconstrained portfolio capacity.
3. **Standalone Portfolio Drift Checker Script & Runner Step:** A dedicated script and unified pipeline step (`--rebalance`) that evaluates each configured **Model Portfolio** against live holdings in **Base Currency** without modifying or tagging individual asset notes.
   - Evaluates **only** the **Target Allocations** explicitly configured in each active **Allocation Layer**, while using the **full portfolio bucket Base Value (`100%`)** as the denominator (unmodeled holdings contribute to total portfolio value but are not flagged).
   - Ignores empty portfolio buckets (`total_value == 0`) and ignores corridor breaches whose absolute **Base Currency** rebalance delta is strictly below the effective minimum trade threshold (`abs(delta) < min_trade_amount`).
   - Emits a structured `WARN` alert per breached portfolio bucket detailing which **Target Allocation** breached its **Tolerance Corridor**, its actual weight vs. target weight and corridor bounds `[min%–max%]`, both the drift from target (`+X.X%`) and the breach beyond the corridor limit (`+Y.Y%`), and the required **Base Currency** adjustment.
   - Exits with code `0` by default (so warnings do not abort full pipeline runs) and supports a `--strict` flag that exits with code `1` when any portfolio requires rebalancing.
4. **Synchronized Obsidian Dashboards:** Update the in-note rebalance dashboard view and the central alerts dashboard to apply the exact same filtering rules (ignoring empty portfolios and deltas below the minimum trade threshold, evaluating only configured targets against total portfolio value) and display the detailed per-portfolio warning breakdown.

## User Stories

1. As an investor bootstrapping a new vault, I want to configure my **Model Portfolio** during **Vault Initialization**, so that my target allocations and **Tolerance Corridors** are ready from day one.
2. As an investor with an existing **Downstream Personal Vault**, I want to launch the **Model Portfolio** configurator at any time via a standalone CLI flag or script, so that I can adjust my targets and **Tolerance Corridors** without re-running the entire initialization wizard.
3. As an investor in a hurry, I want to pick one of the four built-in multi-asset presets (`Balanced`, `Conservative`, `Aggressive Growth`, `Classic`) or keep my existing configuration with a single `Enter` keystroke, so that onboarding remains fast when I do not need custom weights.
4. As a hands-on investor, I want to enter an interactive customization mode for any individual portfolio bucket (**Safety Net Portfolio**, **Long Term Portfolio**, **Aggressive Portfolio**), so that I can tailor each bucket's targets independently.
5. As an investor, I want to configure the default **Tolerance Corridor** percentage (e.g., `±5.0%`) at the portfolio bucket level, so that all targets in that bucket inherit a sensible default deviation band.
6. As an investor, I want to override the **Tolerance Corridor** percentage for a specific **Target Allocation** (e.g., setting `±3.0%` on Bonds while keeping `±5.0%` on Equities), so that critical or volatile allocations can have tighter or wider bands.
7. As an investor, I want to configure the minimum trade threshold in **Base Currency** at the portfolio bucket level (and optionally override it per **Target Allocation**), so that small market fluctuations do not trigger fee-inefficient micro-rebalancing warnings.
8. As an investor, I want to choose the rebalancing strategy (`inflow_first` vs. `full_rebalance`) per portfolio bucket in the configurator, so that my tax-optimization preference is recorded for both dashboards and the AI rebalancing advisor.
9. As an investor, I want to configure **Target Allocations** across any of the three **Allocation Layers** (`asset_classes`, `sectors`, `assets`) and choose which layer is the `primary_layer`, so that I can model broad asset classes in one bucket and sector or ticker weights in another.
10. As an investor, I want the configurator to allow **Target Allocation** weights in an **Allocation Layer** to sum to less than `100.0%` (e.g., `30%` Equities and `30%` Bonds = `60%` total) while blocking sums above `100.0%`, so that I can enforce corridors only on specific holdings while leaving the rest of the portfolio unconstrained.
11. As an investor editing weights in the CLI wizard, I want to see the remaining unallocated percentage after each entry and have the option to auto-fill the remaining balance to `100%`, so that I do not have to do mental arithmetic.
12. As an investor, I want to see a clear visual summary and diff preview of my **Model Portfolio** changes before they are written to disk, so that I can verify or cancel accidental edits.
13. As an investor, I want saving my **Model Portfolio** changes to preserve all existing comments, formatting, and unrelated configuration sections in my vault configuration file, so that my custom broker rules and settings are never lost.
14. As an investor, I want to run a dedicated **Portfolio Drift** check from the CLI (both standalone and via the unified runner), so that I can see in the terminal which portfolio buckets require rebalancing.
15. As an investor running the full automation pipeline (`--all`), I want the **Portfolio Drift** check to execute automatically and display warnings in the pipeline summary without failing the pipeline run (exit code `0`), so that subsequent pipeline steps like historical snapshots still complete.
16. As an automation user, I want an optional `--strict` flag on the **Portfolio Drift** checker that returns a non-zero exit code (`1`) when any portfolio bucket has a `WARN` alert, so that I can use it in automated checks or scripts.
17. As an investor when a **Target Allocation** breaches its **Tolerance Corridor**, I want the `WARN` alert to state the portfolio name, the breached target name, the direction (`Overweight` / `Underweight`), the actual weight percentage, the target weight and corridor range `[min%–max%]`, the percentage-point drift from the target, the percentage-point breach beyond the corridor boundary, and the **Base Currency** rebalance delta.
18. As an investor holding an unmodeled asset (e.g., `27%` Gold in a portfolio whose **Model Portfolio** only specifies `30%` Equities and `30%` Bonds with `±5%` tolerance), I want the **Portfolio Drift** checker to include Gold in the `100%` total portfolio value denominator when computing Equities (`33%`) and Bonds (`40%`) weights, but only evaluate and report warnings for the configured targets (flagging only Bonds at `40%` vs. `[25%–35%]`), so that I am only alerted on the rules I explicitly defined.
19. As an investor with an empty portfolio bucket (`0` **Base Value**, such as in a fresh **Clean Vault**), I want the **Portfolio Drift** checker and Obsidian dashboards to skip drift warnings for that bucket, so that I do not get false `Underweight` alerts before importing any assets.
20. As an investor whose **Target Allocation** has drifted outside its percentage **Tolerance Corridor** by an amount whose **Base Currency** rebalance delta is smaller than the minimum trade threshold, I want both the Python checker and the Obsidian dashboards to ignore that breach and not raise a `WARN` alert, so that I am only alerted when an actionable trade size is reached.
21. As an investor viewing my vault in Obsidian, I want the central alerts dashboard and the per-portfolio rebalance status banner to display the exact same portfolio-level `WARN` details (what breached, in which portfolio, and by how much) as the CLI script, so that terminal and UI reporting are 100% consistent.
22. As an investor upgrading my **Downstream Personal Vault** from v0.11.0 to v0.12.0 via the patch engine, I want the sequential migration patch to upgrade the scripts and views while preserving my personal assets, history, and existing custom configuration.

## Implementation Decisions

1. **Domain Model & Schema Validation (`ModelPortfolioLayers`, `ModelPortfolioConfig`, `ModelPortfolioTargetItem`):**
   - Retain `ModelPortfolioTargetItem` support for `target`, `weight_pct` (`0.0` to `100.0`), optional `tolerance_band_pct`, and optional `min_trade_amount`.
   - Modify `ModelPortfolioLayers` validation: for each non-empty **Allocation Layer** (`asset_classes`, `sectors`, `assets`), enforce that `0.0 < sum(weight_pct) <= 100.0 + 0.1` (allowing partial layer definitions `< 100.0%` while rejecting `> 100.0%` or duplicate target names within the same layer).
   - Represent drift evaluation results using immutable/structured data objects (`TargetDriftResult`, `LayerDriftReport`, `PortfolioDriftReport`):

   ```python
   class TargetDriftStatus(str, Enum):
       BALANCED = "BALANCED"
       OVERWEIGHT = "OVERWEIGHT"
       UNDERWEIGHT = "UNDERWEIGHT"
       BELOW_MIN_TRADE = "BELOW_MIN_TRADE"


   @dataclass
   class TargetDriftResult:
       target: str
       actual_value_base: float
       actual_weight_pct: float
       target_weight_pct: float
       tolerance_band_pct: float
       lower_bound_pct: float
       upper_bound_pct: float
       drift_pct: float  # actual_weight_pct - target_weight_pct
       corridor_breach_pct: float  # >0 when outside [lower_bound_pct, upper_bound_pct], else 0.0
       delta_base: float  # ((target_weight_pct - actual_weight_pct) / 100) * total_portfolio_value
       min_trade_amount: float
       is_actionable_breach: bool  # True iff outside corridor AND abs(delta_base) >= min_trade_amount
       status: TargetDriftStatus
   ```

2. **Portfolio Drift Evaluation Engine:**
   - Implemented as a standalone module that can be invoked directly from the CLI and imported by the unified runner.
   - **Portfolio Value Denominator:** For each configured **Model Portfolio**, collect all asset holdings belonging to that portfolio bucket and compute `total_portfolio_value` as the sum of their **Base Value** (`value_base`, falling back to `value_pln` for legacy notes). Every asset in the bucket contributes to `total_portfolio_value` regardless of whether its category appears in the **Model Portfolio** targets.
   - **Empty Portfolio Rule:** If `total_portfolio_value <= 0`, mark the portfolio report status as `EMPTY` with zero warnings and do not evaluate target breaches.
   - **Layer Aggregation Rules:**
     - `asset_classes`: If an asset note defines multi-asset `asset_allocation` percentages, apportion its **Base Value** proportionally across `Equities`, `Bonds`, `Real Estate`, `Commodities`/`Gold`, and `Cash`; otherwise classify by `asset_type`, `dominant_sector`, and ticker/name conventions matching the existing dashboard logic. Normalize synonyms (`Bonds` / `Obligations`, `Gold` / `Commodities`).
     - `sectors`: Aggregate **Base Value** by `dominant_sector` (falling back to `industry` or `"Diversified"`).
     - `assets`: Aggregate **Base Value** by `ticker` (or asset `name` / note basename).
   - **Target-Only Evaluation & Actionable Threshold Rule:** Iterate strictly over the `ModelPortfolioTargetItem` entries configured in each non-empty **Allocation Layer** (starting with `primary_layer`, plus any additional populated layers). Unmodeled categories present in the portfolio are not iterated or flagged.
   - For each configured target:
     - `lower_bound_pct = max(0.0, target_weight_pct - effective_tolerance_band_pct)`
     - `upper_bound_pct = min(100.0, target_weight_pct + effective_tolerance_band_pct)`
     - `drift_pct = actual_weight_pct - target_weight_pct`
     - If `actual_weight_pct > upper_bound_pct`, `corridor_breach_pct = actual_weight_pct - upper_bound_pct` (direction: `OVERWEIGHT`).
     - If `actual_weight_pct < lower_bound_pct`, `corridor_breach_pct = actual_weight_pct - lower_bound_pct` (negative value, direction: `UNDERWEIGHT`).
     - `delta_base = ((target_weight_pct - actual_weight_pct) / 100.0) * total_portfolio_value`
     - A `WARN` (`is_actionable_breach = True`) is triggered **if and only if** `actual_weight_pct` is outside `[lower_bound_pct, upper_bound_pct]` **AND** `abs(delta_base) >= effective_min_trade_amount`. If outside the corridor but `abs(delta_base) < effective_min_trade_amount`, the target is not counted as an active warning.
   - **CLI Reporting & Exit Codes:**
     - Prints a structured report per portfolio bucket showing `OK`, `EMPTY`, or `⚠️ WARN — Rebalancing required`, listing each breached target with actual %, target % ± band % `[lower%–upper%]`, drift from target, breach beyond corridor, and formatted **Base Currency** delta.
     - Supports `--portfolio <name>` to check a single bucket, `--json` for machine-readable output, and `--strict` to return exit code `1` when at least one portfolio has an actionable warning (default exit code is `0`).

3. **Interactive Model Portfolio Configuration Wizard:**
   - Exposed via three unified entry points:
     1. During **Vault Initialization** (`Step 4: model_portfolios`),
     2. Standalone step reconfiguration (`--step model_portfolios`),
     3. Direct runner flag (`--setup-model-portfolios`) and standalone script execution.
   - **Two-Stage Interactive Flow:**
     - **Stage 1 (Quick Selection):** Displays the current **Model Portfolio** summary (if already configured) alongside the 4 built-in presets (`Balanced`, `Conservative`, `Aggressive Growth`, `Classic`), plus the **Single-Stock Concentration** cap (`max_single_stock_pct`). Prompts the user whether to accept the selected/current configuration as-is (`[Enter]`) or customize individual portfolios (`[C]`).
     - **Stage 2 (Guided Customization Loop):** Allows selecting a portfolio bucket (`Safety net`, `Long term`, `Aggressive`) to edit:
       - Portfolio-level `rebalance_strategy` (`inflow_first` or `full_rebalance`), default `tolerance_band_pct`, `min_trade_amount`, and `primary_layer` (`asset_classes`, `sectors`, `assets`).
       - Layer target editor for any of `asset_classes`, `sectors`, or `assets`: interactive loop to add/edit/remove `Target Allocation` items with target name, `weight_pct` (displaying remaining percentage to `100%` after each item and allowing partial sums `<= 100%`), optional per-target `tolerance_band_pct` override (`Enter` to inherit portfolio default), and optional per-target `min_trade_amount` override.
     - **Preview & Safe Persistence:** Displays a before/after diff of the `model_portfolios:` YAML block, validates via Pydantic, and writes the updated block in-place into the configuration file while preserving all comments and other sections.

4. **Unified Runner & Obsidian Dashboard Alignment:**
   - Register `--setup-model-portfolios` (interactive configuration action) and `--rebalance` / `--check-model` (pipeline step) in the unified runner, and include the `rebalance` check step in `--all` right after `alerts`.
   - Update the Obsidian in-note rebalance view and the central alerts dashboard note:
     - Do not trigger `[!WARNING]` when `totalPortfolioValue <= 0`.
     - Only increment `driftCount` and mark a row as an active warning (`🟠 Overweight` / `🔵 Underweight`) when the weight is outside `[lowerBound, upperBound]` **and** `Math.abs(deltaBase) >= minTrade`.
     - Include the explicit list of breached targets and their drift / corridor breach percentages directly in the `[!WARNING]` callout banner and in a dedicated **Model Portfolio Rebalance Warnings** section on the central alerts dashboard.

5. **Sequential Migration Patch (`0.11.0` -> `0.12.0`):**
   - Register sequential migration patch bumping `.vault_version` to `0.12.0` and synchronizing updated scripts, views, and dashboards to **Downstream Personal Vaults** without altering personal configurations or asset notes.

## Testing Decisions

### What Makes a Good Test
- Tests must verify observable external behavior at module boundaries (inputs -> returned reports, exit codes, stdout summaries, and persisted YAML configuration files), never internal private helper implementation details.
- Tests should use temporary directories (`tmp_path`) with synthetic configuration files and asset markdown notes rather than mutating the workspace vault.

### Testing Seams
We will test this feature across **two high-level seams**:

1. **Seam 1 — Model Portfolio Configuration & Wizard Entry Point:**
   - **Boundary:** Calling the configuration entry point / wizard with simulated CLI inputs (`monkeypatch` / `unittest.mock.patch("builtins.input")`) and a temporary `config.yaml` file, then loading the resulting configuration via `load_vault_config()`.
   - **Behaviors covered:**
     - Accepting a preset vs. customizing a portfolio bucket's `tolerance_band_pct`, `min_trade_amount`, `rebalance_strategy`, and `primary_layer`.
     - Setting per-target `tolerance_band_pct` and `min_trade_amount` overrides across `asset_classes`, `sectors`, and `assets` layers.
     - Validating **Allocation Layer** weights summing to `< 100.0%` (e.g., `30%` Equities + `30%` Bonds = `60%` valid) vs. rejecting sums `> 100.0%`.
     - Preserving unrelated `config.yaml` sections and comments after saving.

2. **Seam 2 — Portfolio Drift Evaluation Engine Entry Point:**
   - **Boundary:** Calling the **Portfolio Drift** evaluation runner against a temporary vault directory containing a `config.yaml` and synthetic asset notes in `10_Finance/Assets/*.md`.
   - **Behaviors covered:**
     - Detecting `OVERWEIGHT` and `UNDERWEIGHT` breaches with both portfolio-default and per-target `tolerance_band_pct` overrides, verifying exact `drift_pct`, `corridor_breach_pct`, and `delta_base` calculations and formatted `WARN` messages.
     - Partial model / unmodeled asset scenario (`30%` Equities target, `30%` Bonds target, `±5%` tolerance, with actual holdings of `33%` Equities, `40%` Bonds, and `27%` unmodeled Gold): verifying that Gold is included in the `100%` portfolio denominator, Equities (`33%`) is `BALANCED`, Gold (`27%`) is ignored, and **only** Bonds (`40%`, `+10%` drift from target, `+5%` above `35%` upper corridor) raises a `WARN`.
     - Ignoring empty portfolios (`total_value == 0` -> `EMPTY` status, `0` warnings).
     - Ignoring corridor breaches where `abs(delta_base) < min_trade_amount` (`0` warnings).
     - Verifying exit code `0` by default when warnings exist, and exit code `1` when `--strict` is enabled.

### Prior Art in Codebase
- Configuration & Pydantic schema tests in `99_System/Tests/test_model_portfolio_config.py`.
- Interactive CLI wizard tests using `unittest.mock.patch("builtins.input")` and `tempfile.TemporaryDirectory` in `99_System/Tests/test_init_vault.py`.
- Alert engine and rule evaluation tests in `99_System/Tests/alerts/test_engine.py` and `99_System/Tests/alerts/test_rules.py`.
- Sequential patch migration tests in `99_System/Tests/test_patch.py`.

## Out of Scope

- Automated trade execution or order placement with brokers (rebalancing remains strictly advisory and decision-note driven).
- Modifying frontmatter tags (`#alert/...`) inside individual asset notes in `10_Finance/Assets/` for **Portfolio Drift** (portfolio drift is strictly a portfolio-level warning, distinct from asset-level **Single-Stock Concentration**).
- Real estate parametric valuation models (`area_sqm`, hedonic scoring), which belong to Milestone v0.13.

## Further Notes

- This specification directly fulfills Milestone **v0.12** in the project roadmap (`todo.md`) and resolves the domain terminology distinction between **Portfolio Drift** (portfolio-level **Model Portfolio** corridor breach) and **Single-Stock Concentration** (individual equity weight cap) documented in `GLOSSARY.md`.
