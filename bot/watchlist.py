"""Beobachtete Werte (Yahoo-Finance-Symbole), weltweit gestreut.

Suffixe: .DE Xetra, .PA Paris, .AS Amsterdam, .MI Mailand, .SW Zürich,
.CO Kopenhagen, .L London, .T Tokio, .HK Hongkong, -USD Krypto.
"""

STOCKS_US = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "AMD",
    "NFLX", "CRM", "ORCL", "ADBE", "PLTR", "UBER", "SHOP", "COIN", "MU",
    "JPM", "V", "MA", "BRK-B", "LLY", "UNH", "JNJ", "XOM", "CVX", "COST",
    "WMT", "KO", "DIS", "BA", "CAT", "GE", "LMT", "RTX", "TSM", "BABA",
]

STOCKS_EU = [
    "SAP.DE", "SIE.DE", "ALV.DE", "DTE.DE", "MBG.DE", "BMW.DE", "BAS.DE",
    "IFX.DE", "RHM.DE", "ADS.DE", "MUV2.DE", "DBK.DE", "ENR.DE", "AIR.PA",
    "MC.PA", "OR.PA", "TTE.PA", "ASML.AS", "NOVO-B.CO", "NESN.SW",
    "ROG.SW", "SHEL.L", "AZN.L", "ENI.MI",
]

STOCKS_ASIA = ["7203.T", "6758.T", "0700.HK", "9988.HK"]

ETFS = [
    "SPY", "QQQ", "IWM", "EWG", "EWJ", "EEM", "FXI", "INDA", "GLD", "SLV",
    "XLE", "XLF", "XLK", "SMH", "ITA", "URA", "TLT",
]

CRYPTO = ["BTC-USD", "ETH-USD", "SOL-USD"]

# Marktumfeld: Volatilität, Indizes, Zinsen, Rohstoffe, Dollar
MACRO = {
    "^VIX": "VIX (Angstindex)",
    "^GSPC": "S&P 500",
    "^GDAXI": "DAX",
    "^N225": "Nikkei 225",
    "^TNX": "US-Rendite 10J",
    "CL=F": "Rohöl WTI",
    "GC=F": "Gold",
    "DX-Y.NYB": "US-Dollar-Index",
}

UNIVERSE = STOCKS_US + STOCKS_EU + STOCKS_ASIA + ETFS + CRYPTO
