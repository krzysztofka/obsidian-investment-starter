# Investment Second Brain

Domain terminology for the portfolio management system, multi-portfolio asset allocation, and multi-currency valuation workflows.

## Valuation & Currencies

**Base Currency**:
The primary reference fiat currency configured for the vault, used for total portfolio valuation, target allocations, and performance charts.
_Avoid_: Home currency, default currency, local currency

**Quote Currency**:
The native trading or denomination currency of an individual asset holding or cash balance.
_Avoid_: Asset currency, traded currency, transaction currency

**Base Value**:
The financial market value of an asset holding expressed in the vault's Base Currency.
_Avoid_: Converted value, PLN value, total PLN

**FX Cross Rate**:
The exchange rate between a Quote Currency and the Base Currency.
_Avoid_: FX multiplier, conversion factor

## Portfolio Architecture

**Safety Net Portfolio**:
Liquid emergency reserves, currency cushions, and guaranteed inflation-indexed retail bonds.
_Avoid_: Emergency fund, cash bucket

**Long Term Portfolio**:
Foundation for multi-decade compound wealth building, broad index ETFs, physical gold, and real estate.
_Avoid_: Core portfolio, retirement bucket

**Aggressive Portfolio**:
Alpha generation, high-conviction individual equities, and thematic/cyclical opportunities.
_Avoid_: Speculative bucket, trading portfolio

## Vault Architecture & Lifecycle

**Upstream Template Starter**:
The public, open-source template repository providing the automation engine (`99_System/`), note templates, Dataview views, documentation, and sample datasets without private personal financial data.
_Avoid_: Master vault, parent repo

**Downstream Personal Vault**:
The investor's private Obsidian financial vault holding actual personal asset notes, investment theses, raw broker statements, credentials, and custom target allocations.
_Avoid_: User vault, child repo, private instance

**Vault Initialization**:
The guided onboarding and scaffolding workflow (`init.py` or `run.py --init`) configuring platform extensions, base currency, investor risk profile, and environment variables for a new vault.
_Avoid_: Setup script, install run

**Clean Vault**:
A personal investment vault initialized with an empty asset ledger and pristine historical timeline, ready for live personal broker imports.
_Avoid_: Empty vault, bare repo

**Demo Vault**:
A vault initialized or populated with synthetic demonstration assets, mock raw files, and sample performance history for exploration and testing.
_Avoid_: Sample vault, test workspace

