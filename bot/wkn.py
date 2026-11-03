"""WKN (Wertpapierkennnummer) zu den Yahoo-Symbolen der Watchlist.

Nur Einträge, die sicher bekannt sind. Fehlt ein Symbol, zeigen Dashboard und Telegram einen
Suchlink statt einer geratenen Nummer. US-ETFs (SPY, XLK, ...) sind für Privatanleger in der EU
meist nicht kaufbar (PRIIPs) und haben daher bewusst keine WKN.
"""

from urllib.parse import quote

WKN = {
    # USA
    "AAPL": "865985", "MSFT": "870747", "NVDA": "918422", "AMZN": "906866", "GOOGL": "A14Y6F",
    "META": "A1JWVX", "TSLA": "A1CX3T", "AVGO": "A2JG9Z", "AMD": "863186", "NFLX": "552484",
    "CRM": "A0B87V", "ORCL": "871460", "ADBE": "871981", "PLTR": "A2QA4J", "UBER": "A2PHHG",
    "SHOP": "A14TJP", "COIN": "A2QP7J", "MU": "869020", "JPM": "850628", "V": "A0NC7B",
    "MA": "A0F602", "BRK-B": "A0YJQ2", "LLY": "858560", "UNH": "869561", "JNJ": "853260",
    "XOM": "852549", "CVX": "852552", "COST": "888351", "WMT": "860853", "KO": "850663",
    "DIS": "855686", "BA": "850471", "CAT": "850598", "GE": "851144", "LMT": "894648",
    "TSM": "909800", "BABA": "A117ME",
    # Europa
    "SAP.DE": "716460", "SIE.DE": "723610", "ALV.DE": "840400", "DTE.DE": "555750",
    "MBG.DE": "710000", "BMW.DE": "519000", "BAS.DE": "BASF11", "IFX.DE": "623100",
    "RHM.DE": "703000", "ADS.DE": "A1EWWW", "MUV2.DE": "843002", "DBK.DE": "514000",
    "ENR.DE": "ENER6Y", "AIR.PA": "938914", "MC.PA": "853292", "OR.PA": "853888",
    "TTE.PA": "850727", "ASML.AS": "A1J4U4", "NOVO-B.CO": "A3EU6F", "NESN.SW": "A0Q4DC",
    "NOVN.SW": "904278", "SHEL.L": "A3C99G", "AZN.L": "886455", "ENI.MI": "897791",
    # Asien
    "7203.T": "853510", "6758.T": "853687", "0700.HK": "A1138D",
}


def wkn(ticker: str) -> str:
    return WKN.get(ticker, "")


def search_url(query: str) -> str:
    return "https://www.finanzen.net/suchergebnis.asp?_search=" + quote(query)


NAMES = {
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "Nvidia", "AMZN": "Amazon", "GOOGL": "Alphabet (Google)",
    "META": "Meta Platforms", "TSLA": "Tesla", "AVGO": "Broadcom", "AMD": "AMD", "NFLX": "Netflix",
    "CRM": "Salesforce", "ORCL": "Oracle", "ADBE": "Adobe", "PLTR": "Palantir", "UBER": "Uber",
    "SHOP": "Shopify", "COIN": "Coinbase", "MU": "Micron", "JPM": "JPMorgan Chase", "V": "Visa",
    "MA": "Mastercard", "BRK-B": "Berkshire Hathaway B", "LLY": "Eli Lilly", "UNH": "UnitedHealth",
    "JNJ": "Johnson & Johnson", "XOM": "ExxonMobil", "CVX": "Chevron", "COST": "Costco", "WMT": "Walmart",
    "KO": "Coca-Cola", "DIS": "Walt Disney", "BA": "Boeing", "CAT": "Caterpillar", "GE": "GE Aerospace",
    "LMT": "Lockheed Martin", "RTX": "RTX (Raytheon)", "TSM": "TSMC (ADR)", "BABA": "Alibaba (ADR)",
    "SAP.DE": "SAP", "SIE.DE": "Siemens", "ALV.DE": "Allianz", "DTE.DE": "Deutsche Telekom",
    "MBG.DE": "Mercedes-Benz", "BMW.DE": "BMW", "BAS.DE": "BASF", "IFX.DE": "Infineon",
    "RHM.DE": "Rheinmetall", "ADS.DE": "Adidas", "MUV2.DE": "Munich Re", "DBK.DE": "Deutsche Bank",
    "ENR.DE": "Siemens Energy", "AIR.PA": "Airbus", "MC.PA": "LVMH", "OR.PA": "L'Oréal",
    "TTE.PA": "TotalEnergies", "ASML.AS": "ASML", "NOVO-B.CO": "Novo Nordisk", "NESN.SW": "Nestlé",
    "NOVN.SW": "Novartis", "SHEL.L": "Shell", "AZN.L": "AstraZeneca", "ENI.MI": "Eni",
    "7203.T": "Toyota", "6758.T": "Sony", "0700.HK": "Tencent", "9988.HK": "Alibaba (HK)",
}


def name(ticker: str) -> str:
    return NAMES.get(ticker, ticker)
