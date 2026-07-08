"""
fares.py — Real TFL fares via the Unified API, with a station name -> ID lookup.

Uses the TFL fares endpoint:
    https://api.tfl.gov.uk/Stoppoint/{fromId}/FareTo/{toId}

A small curated list of major stations maps user-friendly names to the
station IDs the API requires. Extend STATIONS with more as needed.
"""

import os
import requests
from dataclasses import dataclass

TFL_APP_KEY = os.getenv("TFL_APP_KEY", "")
BASE_URL = "https://api.tfl.gov.uk"

# Curated map of major station names -> TFL StopPoint IDs (Underground).
# Extend this list with more stations as you like. IDs are TFL Naptan codes.
STATIONS = {
    "Acton Town": "940GZZLUACT",
    "Aldgate": "940GZZLUALD",
    "Aldgate East": "940GZZLUADE",
    "Alperton": "940GZZLUALP",
    "Amersham": "940GZZLUAMS",
    "Angel": "940GZZLUAGL",
    "Archway": "940GZZLUACY",
    "Arnos Grove": "940GZZLUASG",
    "Arsenal": "940GZZLUASL",
    "Baker Street": "940GZZLUBST",
    "Balham": "940GZZLUBLM",
    "Bank": "940GZZLUBNK",
    "Barbican": "940GZZLUBBN",
    "Barking": "940GZZLUBKG",
    "Barkingside": "940GZZLUBKE",
    "Barons Court": "940GZZLUBSC",
    "Battersea Power Station": "940GZZBPSUST",
    "Bayswater": "940GZZLUBWT",
    "Becontree": "940GZZLUBEC",
    "Belsize Park": "940GZZLUBZP",
    "Bermondsey": "940GZZLUBMY",
    "Bethnal Green": "940GZZLUBLG",
    "Blackfriars": "940GZZLUBKF",
    "Blackhorse Road": "940GZZLUBLR",
    "Bond Street": "940GZZLUBND",
    "Borough": "940GZZLUBOR",
    "Boston Manor": "940GZZLUBOS",
    "Bounds Green": "940GZZLUBDS",
    "Bow Road": "940GZZLUBWR",
    "Brent Cross": "940GZZLUBTX",
    "Brixton": "940GZZLUBXN",
    "Bromley-by-Bow": "940GZZLUBBB",
    "Buckhurst Hill": "940GZZLUBKH",
    "Burnt Oak": "940GZZLUBTK",
    "Caledonian Road": "940GZZLUCAR",
    "Camden Town": "940GZZLUCTN",
    "Canada Water": "940GZZLUCWR",
    "Canary Wharf": "940GZZLUCYF",
    "Canning Town": "940GZZLUCGT",
    "Cannon Street": "940GZZLUCST",
    "Canons Park": "940GZZLUCPK",
    "Chalfont & Latimer": "940GZZLUCAL",
    "Chalk Farm": "940GZZLUCFM",
    "Chancery Lane": "940GZZLUCHL",
    "Charing Cross": "940GZZLUCHX",
    "Chesham": "940GZZLUCSM",
    "Chigwell": "940GZZLUCWL",
    "Chiswick Park": "940GZZLUCWP",
    "Chorleywood": "940GZZLUCYD",
    "Clapham Common": "940GZZLUCPC",
    "Clapham North": "940GZZLUCPN",
    "Clapham South": "940GZZLUCPS",
    "Cockfosters": "940GZZLUCKS",
    "Colindale": "940GZZLUCND",
    "Colliers Wood": "940GZZLUCSD",
    "Covent Garden": "940GZZLUCGN",
    "Croxley": "940GZZLUCXY",
    "Dagenham East": "940GZZLUDGE",
    "Dagenham Heathway": "940GZZLUDGY",
    "Debden": "940GZZLUDBN",
    "Dollis Hill": "940GZZLUDOH",
    "Ealing Broadway": "940GZZLUEBY",
    "Ealing Common": "940GZZLUECM",
    "Earl's Court": "940GZZLUECT",
    "East Acton": "940GZZLUEAN",
    "East Finchley": "940GZZLUEFY",
    "East Ham": "940GZZLUEHM",
    "East Putney": "940GZZLUEPY",
    "Eastcote": "940GZZLUEAE",
    "Edgware": "940GZZLUEGW",
    "Edgware Road (Bakerloo)": "940GZZLUERB",
    "Edgware Road (Circle Line)": "940GZZLUERC",
    "Elephant & Castle": "940GZZLUEAC",
    "Elm Park": "940GZZLUEPK",
    "Embankment": "940GZZLUEMB",
    "Epping": "940GZZLUEPG",
    "Euston": "940GZZLUEUS",
    "Euston Square": "940GZZLUESQ",
    "Fairlop": "940GZZLUFLP",
    "Farringdon": "940GZZLUFCN",
    "Finchley Central": "940GZZLUFYC",
    "Finchley Road": "940GZZLUFYR",
    "Finsbury Park": "940GZZLUFPK",
    "Fulham Broadway": "940GZZLUFBY",
    "Gants Hill": "940GZZLUGTH",
    "Gloucester Road": "940GZZLUGTR",
    "Golders Green": "940GZZLUGGN",
    "Goldhawk Road": "940GZZLUGHK",
    "Goodge Street": "940GZZLUGDG",
    "Grange Hill": "940GZZLUGGH",
    "Great Portland Street": "940GZZLUGPS",
    "Green Park": "940GZZLUGPK",
    "Greenford": "940GZZLUGFD",
    "Gunnersbury": "940GZZLUGBY",
    "Hainault": "940GZZLUHLT",
    "Hammersmith (Dist&Picc Line)": "940GZZLUHSD",
    "Hammersmith (H&C Line)": "940GZZLUHSC",
    "Hampstead": "940GZZLUHTD",
    "Hanger Lane": "940GZZLUHGR",
    "Harlesden": "940GZZLUHSN",
    "Harrow & Wealdstone": "940GZZLUHAW",
    "Harrow-on-the-Hill": "940GZZLUHOH",
    "Hatton Cross": "940GZZLUHNX",
    "Heathrow Terminal 4": "940GZZLUHR4",
    "Heathrow Terminal 5": "940GZZLUHR5",
    "Heathrow Terminals 2 & 3": "940GZZLUHRC",
    "Hendon Central": "940GZZLUHCL",
    "High Barnet": "940GZZLUHBT",
    "High Street Kensington": "940GZZLUHSK",
    "Highbury & Islington": "940GZZLUHAI",
    "Highgate": "940GZZLUHGT",
    "Hillingdon": "940GZZLUHGD",
    "Holborn": "940GZZLUHBN",
    "Holland Park": "940GZZLUHPK",
    "Holloway Road": "940GZZLUHWY",
    "Hornchurch": "940GZZLUHCH",
    "Hounslow Central": "940GZZLUHWC",
    "Hounslow East": "940GZZLUHWE",
    "Hounslow West": "940GZZLUHWT",
    "Hyde Park Corner": "940GZZLUHPC",
    "Ickenham": "940GZZLUICK",
    "Kennington": "940GZZLUKNG",
    "Kensal Green": "940GZZLUKSL",
    "Kensington (Olympia)": "940GZZLUKOY",
    "Kentish Town": "940GZZLUKSH",
    "Kenton": "940GZZLUKEN",
    "Kew Gardens": "940GZZLUKWG",
    "Kilburn": "940GZZLUKBN",
    "Kilburn Park": "940GZZLUKPK",
    "King's Cross St. Pancras": "940GZZLUKSX",
    "Kingsbury": "940GZZLUKBY",
    "Knightsbridge": "940GZZLUKNB",
    "Ladbroke Grove": "940GZZLULAD",
    "Lambeth North": "940GZZLULBN",
    "Lancaster Gate": "940GZZLULGT",
    "Latimer Road": "940GZZLULRD",
    "Leicester Square": "940GZZLULSQ",
    "Leyton": "940GZZLULYN",
    "Leytonstone": "940GZZLULYS",
    "Liverpool Street": "940GZZLULVT",
    "London Bridge": "940GZZLULNB",
    "Loughton": "940GZZLULGN",
    "Maida Vale": "940GZZLUMVL",
    "Manor House": "940GZZLUMRH",
    "Mansion House": "940GZZLUMSH",
    "Marble Arch": "940GZZLUMBA",
    "Marylebone": "940GZZLUMYB",
    "Mile End": "940GZZLUMED",
    "Mill Hill East": "940GZZLUMHL",
    "Monument": "940GZZLUMMT",
    "Moor Park": "940GZZLUMPK",
    "Moorgate": "940GZZLUMGT",
    "Morden": "940GZZLUMDN",
    "Mornington Crescent": "940GZZLUMTC",
    "Neasden": "940GZZLUNDN",
    "Newbury Park": "940GZZLUNBP",
    "Nine Elms": "940GZZNEUGST",
    "North Acton": "940GZZLUNAN",
    "North Ealing": "940GZZLUNEN",
    "North Greenwich": "940GZZLUNGW",
    "North Harrow": "940GZZLUNHA",
    "North Wembley": "940GZZLUNWY",
    "Northfields": "940GZZLUNFD",
    "Northolt": "940GZZLUNHT",
    "Northwick Park": "940GZZLUNKP",
    "Northwood": "940GZZLUNOW",
    "Northwood Hills": "940GZZLUNWH",
    "Notting Hill Gate": "940GZZLUNHG",
    "Oakwood": "940GZZLUOAK",
    "Old Street": "940GZZLUODS",
    "Osterley": "940GZZLUOSY",
    "Oval": "940GZZLUOVL",
    "Oxford Circus": "940GZZLUOXC",
    "Paddington": "940GZZLUPAC",
    "Paddington (H&C Line)-Underground": "940GZZLUPAH",
    "Park Royal": "940GZZLUPKR",
    "Parsons Green": "940GZZLUPSG",
    "Perivale": "940GZZLUPVL",
    "Piccadilly Circus": "940GZZLUPCC",
    "Pimlico": "940GZZLUPCO",
    "Pinner": "940GZZLUPNR",
    "Plaistow": "940GZZLUPLW",
    "Preston Road": "940GZZLUPRD",
    "Putney Bridge": "940GZZLUPYB",
    "Queen's Park": "940GZZLUQPS",
    "Queensbury": "940GZZLUQBY",
    "Queensway": "940GZZLUQWY",
    "Ravenscourt Park": "940GZZLURVP",
    "Rayners Lane": "940GZZLURYL",
    "Redbridge": "940GZZLURBG",
    "Regent's Park": "940GZZLURGP",
    "Richmond": "940GZZLURMD",
    "Rickmansworth": "940GZZLURKW",
    "Roding Valley": "940GZZLURVY",
    "Royal Oak": "940GZZLURYO",
    "Ruislip": "940GZZLURSP",
    "Ruislip Gardens": "940GZZLURSG",
    "Ruislip Manor": "940GZZLURSM",
    "Russell Square": "940GZZLURSQ",
    "Seven Sisters": "940GZZLUSVS",
    "Shepherd's Bush (Central)": "940GZZLUSBC",
    "Shepherd's Bush Market": "940GZZLUSBM",
    "Sloane Square": "940GZZLUSSQ",
    "Snaresbrook": "940GZZLUSNB",
    "South Ealing": "940GZZLUSEA",
    "South Harrow": "940GZZLUSHH",
    "South Kensington": "940GZZLUSKS",
    "South Kenton": "940GZZLUSKT",
    "South Ruislip": "940GZZLUSRP",
    "South Wimbledon": "940GZZLUSWN",
    "South Woodford": "940GZZLUSWF",
    "Southfields": "940GZZLUSFS",
    "Southgate": "940GZZLUSGT",
    "Southwark": "940GZZLUSWK",
    "St. James's Park": "940GZZLUSJP",
    "St. John's Wood": "940GZZLUSJW",
    "St. Paul's": "940GZZLUSPU",
    "Stamford Brook": "940GZZLUSFB",
    "Stanmore": "940GZZLUSTM",
    "Stepney Green": "940GZZLUSGN",
    "Stockwell": "940GZZLUSKW",
    "Stonebridge Park": "940GZZLUSGP",
    "Stratford": "940GZZLUSTD",
    "Sudbury Hill": "940GZZLUSUH",
    "Sudbury Town": "940GZZLUSUT",
    "Swiss Cottage": "940GZZLUSWC",
    "Temple": "940GZZLUTMP",
    "Theydon Bois": "940GZZLUTHB",
    "Tooting Bec": "940GZZLUTBC",
    "Tooting Broadway": "940GZZLUTBY",
    "Tottenham Court Road": "940GZZLUTCR",
    "Tottenham Hale": "940GZZLUTMH",
    "Totteridge & Whetstone": "940GZZLUTAW",
    "Tower Hill": "940GZZLUTWH",
    "Tufnell Park": "940GZZLUTFP",
    "Turnham Green": "940GZZLUTNG",
    "Turnpike Lane": "940GZZLUTPN",
    "Upminster": "940GZZLUUPM",
    "Upminster Bridge": "940GZZLUUPB",
    "Upney": "940GZZLUUPY",
    "Upton Park": "940GZZLUUPK",
    "Uxbridge": "940GZZLUUXB",
    "Vauxhall": "940GZZLUVXL",
    "Victoria": "940GZZLUVIC",
    "Walthamstow Central": "940GZZLUWWL",
    "Wanstead": "940GZZLUWSD",
    "Warren Street": "940GZZLUWRR",
    "Warwick Avenue": "940GZZLUWKA",
    "Waterloo": "940GZZLUWLO",
    "Watford": "940GZZLUWAF",
    "Wembley Central": "940GZZLUWYC",
    "Wembley Park": "940GZZLUWYP",
    "West Acton": "940GZZLUWTA",
    "West Brompton": "940GZZLUWBN",
    "West Finchley": "940GZZLUWFN",
    "West Ham": "940GZZLUWHM",
    "West Hampstead": "940GZZLUWHP",
    "West Harrow": "940GZZLUWHW",
    "West Kensington": "940GZZLUWKN",
    "West Ruislip": "940GZZLUWRP",
    "Westbourne Park": "940GZZLUWSP",
    "Westminster": "940GZZLUWSM",
    "White City": "940GZZLUWCY",
    "Whitechapel": "940GZZLUWPL",
    "Willesden Green": "940GZZLUWIG",
    "Willesden Junction": "940GZZLUWJN",
    "Wimbledon": "940GZZLUWIM",
    "Wimbledon Park": "940GZZLUWIP",
    "Wood Green": "940GZZLUWOG",
    "Wood Lane": "940GZZLUWLA",
    "Woodford": "940GZZLUWOF",
    "Woodside Park": "940GZZLUWOP",
}

@dataclass
class FareResult:
    from_station: str
    to_station: str
    fare: str          # human-readable fare description
    found: bool


def station_names():
    """Return a sorted list of available station names for the UI dropdowns."""
    return sorted(STATIONS.keys())


def get_real_fare(from_name: str, to_name: str) -> FareResult:
    """Fetch the real fare between two stations from the TFL API."""
    from_id = STATIONS.get(from_name)
    to_id = STATIONS.get(to_name)

    if not from_id or not to_id:
        return FareResult(from_name, to_name, "Station not found.", False)
    if from_id == to_id:
        return FareResult(from_name, to_name, "Start and end stations are the same.", False)

    url = f"{BASE_URL}/Stoppoint/{from_id}/FareTo/{to_id}"
    params = {}
    if TFL_APP_KEY:
        params["app_key"] = TFL_APP_KEY

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return FareResult(from_name, to_name, f"Could not fetch fare: {e}", False)

    # Parse the nested structure:
    # data[] -> section -> rows[] -> ticketsAvailable[] -> {cost, ticketType, ticketTime}
    fare_lines = []
    try:
        for section in data:
            for row in section.get("rows", []):
                for ticket in row.get("ticketsAvailable", []):
                    cost = ticket.get("cost")
                    ttype = ticket.get("ticketType", {}).get("type", "")
                    ttime = ticket.get("ticketTime", {}).get("type", "")
                    if cost is not None:
                        # Build a readable label, e.g. "Pay as you go (Off Peak): £3.00"
                        label = ttype
                        if ttime and ttime != "Anytime":
                            label += f" ({ttime})"
                        fare_lines.append(f"{label}: £{float(cost):.2f}")
    except Exception:
        pass

    # de-duplicate while preserving order
    seen = set()
    unique_lines = []
    for line in fare_lines:
        if line not in seen:
            seen.add(line)
            unique_lines.append(line)

    if unique_lines:
        return FareResult(from_name, to_name, "\n\n".join(unique_lines), True)
    else:
        return FareResult(
            from_name, to_name,
            "No fare data available for this route.", False
        )