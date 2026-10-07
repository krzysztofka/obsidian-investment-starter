import re

# Known ISIN to Stooq ticker mappings
KNOWN_ISIN_STOOQ_MAP: dict[str, str] = {
    # GPW Polish Equities
    "PLKGHM000017": "kgh",
    "PLPKN0000018": "pkn",
    "PLPZU0000011": "pzu",
    "PLTORPL00016": "tor",
    "PLOPTTC00011": "cdr",
    "PLDINPL00011": "dnp",
    "PLALE0000019": "ale",
    "PLPEKAO00016": "peo",
    "PLPKO0000016": "pko",
    "PLSOFTB00016": "acp",
    "PLJSW0000015": "jsw",
    "PLCCC0000012": "ccc",
    "PLKRK0000010": "kru",
    "PLCYFRW00016": "cps",
    "PL11BIT00012": "11b",
    "PLTENSC00019": "tsg",
    "PLXTB0000010": "xtb",
    "PLBIG0000016": "mil",
    "PLGRNPT00010": "gpp",
    "PLMBK0000016": "mbk",
    "PLALIOR00045": "alr",
    "PLLPP0000011": "lpp",
    "PLBZ00000044": "spl",
    "PLZTKMD00010": "kty",
    "PLMDGLL00015": "mdg",
    "PLTAURN00011": "tpe",
    "PLEGPRO00025": "ena",
    "PLPGE0000010": "pge",
    "PLBUDMX00013": "bdx",
    "PLTEXT000010": "txt",
    "PLNEUCA00013": "neu",
    "PLAB00000019": "abpl",
    "PLASBPC00014": "asb",
    "PLVSTLA00011": "vrc",
    "PLVRG0000012": "vrg",
    "PLINTER00011": "car",
    "PLSNK0000010": "snk",
    "PLDOMDV00015": "dom",
    "PLDEVEL00014": "dvl",
    "PLATLST00018": "ats",
    "PLCLNPH00013": "cln",
    "PLBOS0000019": "bos",
    "PLKGN0000017": "kgn",
    "PLAGORA00067": "ago",
    "PLAMBRL00014": "amc",
    "PLACTIN00018": "act",
    "PLARTRM00012": "atp",
    "PLAPATR00018": "apt",
    "PLAUTOP00010": "atc",
    "PLVOX0000014": "vox",
    "PLWIRT000014": "wpl",
    "PLZUE0000015": "zue",
    # UCITS ETFs
    "IE00BMVB5R75": "v80a.de",  # Vanguard LifeStrategy 80% Equity UCITS ETF
    "IE00BMVB5P51": "v60a.de",  # Vanguard LifeStrategy 60% Equity UCITS ETF
    "IE00BMVB5N38": "v40a.de",  # Vanguard LifeStrategy 40% Equity UCITS ETF
    "IE00BMVB5M21": "v20a.de",  # Vanguard LifeStrategy 20% Equity UCITS ETF
    "IE00BK5BQT80": "vwra.uk",  # Vanguard FTSE All-World UCITS ETF (USD Acc)
    "IE00B3RBWM25": "vwrl.uk",  # Vanguard FTSE All-World UCITS ETF (USD Dist)
    "IE00B8GKDB10": "vhyl.uk",  # Vanguard FTSE All-World High Dividend Yield UCITS ETF
    "IE00B43HR379": "iuhc.uk",  # iShares S&P 500 Health Care Sector UCITS ETF
    "IE00BYXPSP02": "ibta.uk",  # iShares $ Treasury Bond 7-10yr UCITS ETF
    "IE000YYE6WK5": "dfen.de",  # VanEck Defense UCITS ETF
    "NL0011683594": "tdiv.nl",  # VanEck Morningstar Developed Markets Dividend Leaders UCITS ETF
    "IE00B4L5Y983": "swda.uk",  # iShares Core MSCI World UCITS ETF
    "IE00B5BMR087": "cspx.uk",  # iShares Core S&P 500 UCITS ETF
    "IE00BKM4GZ66": "emim.uk",  # iShares Core MSCI EM IMI UCITS ETF
    "LU1681045370": "lcwd.uk",  # Amundi Core MSCI World UCITS ETF
}

# Known Ticker / Identifier to Stooq ticker mappings
KNOWN_TICKER_STOOQ_MAP: dict[str, str] = {
    # Commodities & Precious Metals
    "GOLD": "xauusd",
    "XAUUSD": "xauusd",
    "XAU": "xauusd",
    "SILVER": "xagusd",
    "XAGUSD": "xagusd",
    "XAG": "xagusd",
    # Bonds & Benchmarks
    "10PLY": "10ply.b",
    "10USY": "10usy.b",
    "10DEY": "10dey.b",
    "WIG20": "wig20",
    "MWIG40": "mwig40",
    "SWIG80": "swig80",
    "WIG": "wig",
    "SPX": "spx",
    "NDX": "ndx",
    # Currencies
    "EURPLN": "eurpln",
    "USDPLN": "usdpln",
    "EURUSD": "eurusd",
    "GBPPLN": "gbppln",
    "CHFPLN": "chfpln",
    # Specific Custom Portfolio Assets
    "V80A_IKZE": "v80a.de",
}


def resolve_stooq_ticker(
    isin: str | None = None,
    yahoo_ticker: str | None = None,
    ticker: str | None = None,
    name: str | None = None,
    asset_type: str | None = None,
    country: str | None = None,
    currency: str | None = None,
) -> str | None:
    """Resolve the standardized Stooq ticker symbol for any financial asset.

    Supports:
      - Equities: US (.us), GPW (lowercase code), European (.de, .uk, .nl, .fr, .it)
      - ETFs: US (.us), UCITS (.de, .uk, .nl)
      - Bonds: Polish retail treasury bonds & 10Y benchmarks (10ply.b, 10usy.b)
      - Commodities: Physical / Spot Gold (xauusd), Silver (xagusd)
      - Currencies: FX pairs (eurpln, usdpln, eurusd)
    """
    clean_isin = str(isin).strip().upper() if isin else ""
    clean_yt = str(yahoo_ticker).strip().upper() if yahoo_ticker else ""
    clean_t = str(ticker).strip().upper() if ticker else ""
    clean_name = str(name).strip().lower() if name else ""
    clean_type = str(asset_type).strip().lower() if asset_type else ""

    # 1. Non-market assets (Cash, Real Estate, IKE wrappers)
    if clean_type in ("cash", "real estate", "ike", "deposit") or clean_t.startswith(
        ("DEGIRO_CASH", "EXANTE_CASH", "MBANK_CASH", "MBANK_DEPOSIT", "NN_IKE", "JASINSKIEGO")
    ):
        if clean_type != "commodities" and "gold" not in clean_name and "gold" not in clean_t.lower():
            return None

    # 2. Precious Metals / Commodities (Gold, Silver)
    if (
        clean_t in ("GOLD", "XAUUSD", "XAU")
        or "physical gold" in clean_name
        or "spot gold" in clean_name
        or (clean_type == "commodities" and "gold" in clean_name)
    ):
        return "xauusd"
    if clean_t in ("SILVER", "XAGUSD", "XAG") or "silver" in clean_name:
        return "xagusd"

    # 3. Known Ticker / Identifier Overrides
    if clean_t in KNOWN_TICKER_STOOQ_MAP:
        return KNOWN_TICKER_STOOQ_MAP[clean_t]

    # 4. Polish Treasury Retail Bonds (EDO, ROD, COI, TOS, etc.) -> Polish 10Y Benchmark Yield
    if clean_type == "bond" or re.match(r"^(EDO|ROD|COI|TOS|OTS|DOS|ROR|DOR|WS|DS|OK|PS|WZ)\d+", clean_t):
        return "10ply.b"

    # 5. Known ISIN Overrides
    if clean_isin in KNOWN_ISIN_STOOQ_MAP:
        return KNOWN_ISIN_STOOQ_MAP[clean_isin]

    # 6. Polish GPW Equities (from ISIN starting with PL)
    if clean_isin.startswith("PL"):
        # Check if yahoo_ticker is like KGH.WA -> kgh
        if clean_yt.endswith(".WA"):
            return clean_yt[:-3].lower()
        # Fallback to extracting characters from ISIN e.g. PLKGHM000017 -> kgh (if matched)
        clean_prefix = clean_isin[2:6].rstrip("0123456789").lower()
        if clean_prefix:
            return clean_prefix

    # 7. Translation from Yahoo Finance Ticker
    if clean_yt:
        # Polish GPW (.WA)
        if clean_yt.endswith(".WA"):
            return clean_yt[:-3].lower()
        # German XETRA (.DE)
        if clean_yt.endswith(".DE"):
            return clean_yt.lower()
        # London LSE (.L / .LN) -> .uk
        if clean_yt.endswith(".L"):
            return f"{clean_yt[:-2].lower()}.uk"
        if clean_yt.endswith(".LN"):
            return f"{clean_yt[:-3].lower()}.uk"
        # Amsterdam Euronext (.AS / .NL)
        if clean_yt.endswith(".AS"):
            return f"{clean_yt[:-3].lower()}.nl"
        if clean_yt.endswith(".NL"):
            return clean_yt.lower()
        # Paris Euronext (.PA) -> .fr
        if clean_yt.endswith(".PA"):
            return f"{clean_yt[:-3].lower()}.fr"
        # Milan Borsa Italiana (.MI) -> .it
        if clean_yt.endswith(".MI"):
            return f"{clean_yt[:-3].lower()}.it"
        # SG / Swiss / others fallback to base or .de if ETF
        if clean_yt.endswith(".SG") or clean_yt.endswith(".SW") or clean_yt.endswith(".F"):
            base_sym = clean_yt.split(".")[0].lower()
            if base_sym.startswith("ie") or base_sym.startswith("nl") or base_sym.startswith("lu"):
                # ISIN ticker fallback
                pass
            else:
                return f"{base_sym}.de"
        # Standard US Equity / ETF (no dot suffix or standard US symbol)
        if "." not in clean_yt:
            return f"{clean_yt.lower()}.us"

    # 8. Translation from Broker Ticker (e.g. DVYE.ARCA, EWS.ARCA, IBTA.LSE, GAZ.XETRA, VTV.ARCA)
    if "." in clean_t:
        sym, exch = clean_t.split(".", 1)
        sym_l = sym.lower()
        exch_u = exch.upper()
        if exch_u in ("ARCA", "NYSE", "NASDAQ", "US", "BATS"):
            return f"{sym_l}.us"
        if exch_u in ("LSE", "LON"):
            return f"{sym_l}.uk"
        if exch_u in ("XETRA", "FRA", "GER", "DE"):
            return f"{sym_l}.de"
        if exch_u in ("AMS", "AS", "NL"):
            return f"{sym_l}.nl"
        if exch_u in ("PAR", "PA", "FR"):
            return f"{sym_l}.fr"

    # 9. General US fallback for Equities / ETFs with clean alphabetic tickers
    if clean_t and re.match(r"^[A-Z]{1,5}$", clean_t):
        if country == "United States" or currency == "USD" or clean_type in ("equity", "etf"):
            return f"{clean_t.lower()}.us"

    return None
