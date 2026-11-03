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
    "NOVN.SW", "SHEL.L", "AZN.L", "ENI.MI",
]

STOCKS_ASIA = ["7203.T", "6758.T", "0700.HK", "9988.HK"]

ETFS = [
    "SPY", "QQQ", "IWM", "EWG", "EWJ", "EEM", "FXI", "INDA", "GLD", "SLV",
    "XLE", "XLF", "XLK", "SMH", "ITA", "URA", "TLT",
]

CRYPTO = ["BTC-USD", "ETH-USD", "SOL-USD"]

# Marktumfeld: Volatilität, Indizes, Zinsen, Rohstoffe, Währungen, Kredit, Branchen
MACRO = {
    "^VIX": "VIX (Angstindex)",
    "^GSPC": "S&P 500",
    "^GDAXI": "DAX",
    "^N225": "Nikkei 225",
    "^TNX": "US-Rendite 10J",
    "^IRX": "US-Rendite 3M",
    "BZ=F": "Brent-Öl",
    "CL=F": "Rohöl WTI",
    "NG=F": "Erdgas USA",
    "TTF=F": "Erdgas Europa (TTF)",
    "GC=F": "Gold",
    "HG=F": "Kupfer",
    "ZW=F": "Weizen",
    "DX-Y.NYB": "US-Dollar-Index",
    "EURUSD=X": "EUR/USD",
    "USDJPY=X": "USD/JPY",
    "CNY=X": "USD/CNY",
    "HYG": "US-Hochzinsanleihen",
    "JETS": "Airlines (ETF)",
    "XOP": "Öl-Förderer (ETF)",
    "KRE": "US-Regionalbanken",
    "XLU": "Versorger",
    "XLY": "Zyklischer Konsum",
    "XLP": "Basiskonsum",
}

UNIVERSE = STOCKS_US + STOCKS_EU + STOCKS_ASIA + ETFS + CRYPTO

# Zusätzliche Aktien nur für Suche und Steckbrief (nicht im Signal-Scan)
PROFILE_EXTRA = [
    # DAX 40 (Rest)
    "AIR.DE", "BAYN.DE", "BEI.DE", "BNR.DE", "CBK.DE", "CON.DE", "DTG.DE", "DB1.DE", "DHL.DE", "EOAN.DE",
    "FRE.DE", "FME.DE", "HNR1.DE", "HEI.DE", "HEN3.DE", "MRK.DE", "MTX.DE", "P911.DE", "PAH3.DE", "QIA.DE",
    "RWE.DE", "SRT3.DE", "SHL.DE", "SY1.DE", "VOW3.DE", "VNA.DE", "ZAL.DE",
    # Weitere Deutschland
    "LHA.DE", "TUI1.DE", "PUM.DE", "HAG.DE", "RENK.DE", "AIXA.DE", "EVT.DE", "DWNI.DE", "TKA.DE", "SAX.DE",
    # USA
    "ABBV", "PFE", "MRK", "PEP", "PG", "HD", "BAC", "WFC", "GS", "MS", "INTC", "CSCO", "IBM", "QCOM", "TXN",
    "NKE", "MCD", "SBUX", "PYPL", "INTU", "NOW", "T", "VZ", "AMGN", "TMO", "ABT", "HON", "DE", "MMM", "F",
    "GM", "CRWD", "PANW", "SNOW", "ABNB", "SPOT", "ARM", "SMCI", "MSTR", "RIVN", "NIO", "PDD", "JD",
    "BKNG", "NEE", "LIN", "ISRG", "VRTX", "REGN", "MRNA", "BMY", "GILD", "CVS", "AXP", "C", "SCHW", "BLK",
    "UPS", "FDX", "NOC", "GD", "LRCX", "AMAT", "KLAC", "ANET", "DELL", "HPQ", "OKLO", "SOFI", "RBLX", "HOOD",
    # Europa
    "SAN.PA", "BNP.PA", "SU.PA", "RMS.PA", "KER.PA", "CS.PA", "SAF.PA", "DG.PA", "STLAM.MI", "RACE.MI",
    "ISP.MI", "UCG.MI", "INGA.AS", "PRX.AS", "ADYEN.AS", "PHIA.AS", "HEIA.AS", "UBSG.SW", "ZURN.SW",
    "ABBN.SW", "CFR.SW", "HSBA.L", "BP.L", "ULVR.L", "GSK.L", "RIO.L", "BARC.L", "RR.L", "BAE.L",
    "SAN.MC", "ITX.MC", "IBE.MC", "NESTE.HE", "NOKIA.HE", "ERIC-B.ST", "VOLV-B.ST", "EQNR.OL", "DSV.CO", "MAERSK-B.CO",
    # Asien / Sonstige
    "9984.T", "6861.T", "8306.T", "7974.T", "005930.KS", "000660.KS", "1211.HK", "3690.HK", "BHP.AX", "INFY", "SONY",
]
