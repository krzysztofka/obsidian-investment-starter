# Import Positions from Degiro, Exante, and mBM (IKE & IKZE)

## Requirements (for a new machine)
- Python 3.x
- `pip install .`
  *(Defined in `pyproject.toml`; includes `yfinance`, `beautifulsoup4`, `requests`, `python-dotenv`, `finnhub-python`, `pyyaml`, etc.)*

## Exante REST API Configuration (.env)
To import live positions directly from Exante without downloading CSV files, create or update `.env` in the vault root:
```env
EXANTE_API_KEY=your_application_id_or_api_key
EXANTE_API_SECRET=your_shared_key_or_api_secret
EXANTE_ACCOUNT_ID=your_account_id (optional, auto-detected if omitted)
EXANTE_API_URL=https://api-live.exante.eu (optional, default: https://api-live.exante.eu)
```

## mBM (Biuro Maklerskie mBanku) CSV Exports (IKE & IKZE)
Place your mBM portfolio CSV export files in `00_Raw/mBM/`:
- **IKZE export files:** named `ikze-YYYY-MM-DD.csv` (e.g. `00_Raw/mBM/ikze-2026-09-16.csv`)
- **IKE export files:** named `ike-YYYY-MM-DD.csv` (e.g. `00_Raw/mBM/ike-2026-09-16.csv`)
The system automatically assigns positions to the `Long term` portfolio with platform `mBM` and tags (`#ikze` / `#ike`).

## Unified CLI Runner Usage (Recommended)
`run.py` at the vault root provides a single unified entry point for all operations:
```bash
# Full pipeline (import -> update rates -> sync ETFs -> check alerts -> update history):
python run.py --all

# Import broker assets from Degiro (CSV), Exante (CSV/API) & mBM (IKE/IKZE CSV):
python run.py --import

# Import live positions directly via Exante REST API:
python run.py --import --api

# Import specific platform or file:
python run.py --import --platform degiro
python run.py --import --platform exante
python run.py --import --platform mbm
python run.py --import --platform ikze
python run.py --import --platform ike
python run.py --import --platform pkobp
python run.py --import --file 00_Raw/mBM/sample_ikze.csv
```

## Direct Script Usage (`import_assets.py` & `platforms/*.py`)
```bash
# Import all platforms (Degiro, Exante, mBM, and PKO BP):
python 99_System/Scripts/import_assets.py

# Import all platforms using Exante REST API for Exante:
python 99_System/Scripts/import_assets.py --api

# Import specific platform:
python 99_System/Scripts/import_assets.py --platform degiro
python 99_System/Scripts/import_assets.py --platform exante
python 99_System/Scripts/import_assets.py --platform mbm
python 99_System/Scripts/import_assets.py --platform pkobp
python 99_System/Scripts/platforms/mbm.py --account ikze
python 99_System/Scripts/platforms/mbm.py --account ike
python 99_System/Scripts/platforms/pkobp.py
python 99_System/Scripts/platforms/exante.py --api

# Import specific file (platform is automatically recognized from the file path):
python 99_System/Scripts/import_assets.py --file 00_Raw/Degiro/sample_degiro.csv
python 99_System/Scripts/import_assets.py --file 00_Raw/mBM/sample_ikze.csv
python 99_System/Scripts/import_assets.py --file 00_Raw/Exante/sample_exante.csv
python 99_System/Scripts/import_assets.py --file 00_Raw/pkobp/sample_pkobp.xls
```

## Currency Update Procedure
To update the `value_pln` property of all assets in `10_Finance/Assets/*.md` using live exchange rates from Yahoo Finance (`yfinance`):
1. Open the terminal in the workspace root or `99_System/Scripts` directory.
2. Run the command:
   ```bash
   python 99_System/Scripts/update_currencies.py
   ```

**Note:** The import script (`import_assets.py`) as well as `update_currencies.py` update the YAML frontmatter properties (including `value_pln` via exchange rates from Yahoo Finance) in `10_Finance/Assets/*.md`. Existing investment thesis notes and content below the frontmatter block are preserved.
Assets imported from broker platforms (Degiro, Exante) are assigned `source: platform`. Manually created assets (such as physical gold, treasury bonds, or external cash) use `source: manual` and will not be overwritten or removed by broker imports. During broker import, existing platform assets are verified against the imported file; any platform assets that are no longer present in the broker export (e.g., closed/sold positions) are automatically removed.

After assets are updated, the history script (`99_System/Scripts/history/update_portfolio.py`) automatically syncs and sorts all position entries in `10_Finance/History/portfolio.csv`. It can also be run manually at any time:
```bash
python 99_System/Scripts/history/update_portfolio.py
```