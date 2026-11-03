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
    # DAX und weitere Deutschland
    "AIR.DE": "938914", "BAYN.DE": "BAY001", "BEI.DE": "520000", "BNR.DE": "A1DAHH", "CBK.DE": "CBK100",
    "CON.DE": "543900", "DTG.DE": "DTR0CK", "DB1.DE": "581005", "DHL.DE": "555200", "EOAN.DE": "ENAG99",
    "FRE.DE": "578560", "FME.DE": "578580", "HNR1.DE": "840221", "HEI.DE": "604700", "HEN3.DE": "604843",
    "MRK.DE": "659990", "MTX.DE": "A0D9PT", "P911.DE": "PAG911", "PAH3.DE": "PAH003", "RWE.DE": "703712",
    "SRT3.DE": "716563", "SHL.DE": "SHL100", "SY1.DE": "SYM999", "VOW3.DE": "766403", "VNA.DE": "A1ML7J",
    "ZAL.DE": "ZAL111", "LHA.DE": "823212", "TUI1.DE": "TUAG50", "PUM.DE": "696960", "HAG.DE": "HAG000",
    "R3NK.DE": "RENK73", "AIXA.DE": "A0WMPJ", "EVT.DE": "566480", "TKA.DE": "750000",
    # USA
    "ABBV": "A1J84E", "PFE": "852009", "MRK": "A0YD8Q", "PEP": "851995", "PG": "852062", "HD": "866953",
    "BAC": "858388", "WFC": "857949", "GS": "920332", "MS": "885836", "INTC": "855681", "CSCO": "878841",
    "IBM": "851399", "QCOM": "883121", "TXN": "852654", "NKE": "866993", "MCD": "856958", "SBUX": "884437",
    "PYPL": "A14R7U", "INTU": "886053", "NOW": "A1JX4P", "T": "A0HL9Z", "VZ": "868402", "AMGN": "867900",
    "TMO": "857209", "ABT": "850103", "HON": "870153", "DE": "850866", "MMM": "851745", "F": "502391",
    "GM": "A1C9CM", "CRWD": "A2PK2R", "ARM": "A3EUCD", "BKNG": "A2JEXP", "NEE": "A1CZ4H", "LIN": "A3DL3T",
    "ISRG": "888024", "VRTX": "882807", "REGN": "881535", "MRNA": "A2N9D9", "BMY": "850501", "GILD": "885823",
    "AXP": "850226", "C": "A1H92V", "NOC": "851915", "LRCX": "869686", "AMAT": "865177",
    "KLAC": "865884", "SMCI": "A0MKJF", "MSTR": "722713",
    "NEM": "853823", "AEM": "860325", "GFI": "868144",
    # Europa
    "SAN.PA": "920657", "BNP.PA": "887771", "SU.PA": "860180", "RMS.PA": "886670", "SAF.PA": "924781",
    "DG.PA": "867475", "RACE.MI": "A2ACKK", "ADYEN.AS": "A2JNF4", "UBSG.SW": "A12DFH", "HSBA.L": "923893",
    "BP.L": "850517", "ULVR.L": "A0JNE2", "GSK.L": "A3DMTV", "RIO.L": "852147", "RR.L": "A1H81L", "BA.L": "866131",
    "ITX.MC": "A11873", "IBE.MC": "A0M46B", "NOKIA.HE": "870737", "EQNR.OL": "675213",
    # Asien
    "9984.T": "891624", "7974.T": "864009", "1211.HK": "A0M4W9",
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
    "DHL.DE": "DHL Group", "EOAN.DE": "E.ON", "TUI1.DE": "TUI", "SAX.DE": "Ströer",
    "NEM": "Newmont", "AEM": "Agnico Eagle Mines", "B": "Barrick Mining", "WPM": "Wheaton Precious Metals",
    "FNV": "Franco-Nevada", "KGC": "Kinross Gold", "GFI": "Gold Fields", "AU": "AngloGold Ashanti",
    "NST.AX": "Northern Star Resources", "EVN.AX": "Evolution Mining", "2899.HK": "Zijin Mining", "GDX": "VanEck Gold Miners ETF",
}


def name(ticker: str) -> str:
    return NAMES.get(ticker, ticker)
