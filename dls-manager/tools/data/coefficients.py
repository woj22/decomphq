#!/usr/bin/env python3
"""UEFA coefficients for the career (menu/data.json "coeff").

Country coefficients (5 seasons 2021/22-2025/26) and club points for our clubs, from
kassiesa.net's UEFA rankings (method 5, 2026), copied here as data. A club's coefficient is
its 5-season points or 20% of its country's coefficient, whichever is higher (computed in
the menus). Clubs without European points in those seasons have none.

Usage: python3 -I coefficients.py menu/data.json
"""
import json
import sys

SEASONS = ["2021/22", "2022/23", "2023/24", "2024/25", "2025/26"]
COUNTRIES = """England 21.000 23.000 17.375 29.464 28.680
Italy 15.714 22.357 21.000 21.875 19.000
Spain 18.428 16.571 16.062 23.892 22.093
Germany 16.214 17.125 19.357 18.421 21.785
France 18.416 12.583 16.250 17.928 18.321
Portugal 12.916 12.500 11.000 16.250 20.500
Netherlands 19.200 13.500 10.000 15.250 9.979
Belgium 6.600 14.200 14.400 15.650 11.400
Türkiye 6.700 11.800 12.000 10.300 11.075
Czechia 6.700 6.750 13.500 10.550 11.025
Greece 8.000 2.125 11.400 12.687 14.200
Poland 4.625 7.750 6.875 11.750 15.750
Denmark 7.800 5.900 8.500 7.656 12.250
Norway 7.625 5.750 8.000 11.812 8.050
Cyprus 4.125 5.100 3.750 10.562 12.156
Switzerland 7.750 8.500 5.200 7.050 6.200
Austria 10.400 4.900 4.800 9.650 4.100
Scotland 7.900 3.500 6.400 9.250 5.000
Sweden 5.125 6.250 1.875 11.375 5.000
Croatia 6.000 3.375 5.875 5.875 7.031
Israel 6.750 6.250 8.750 2.875 2.875
Hungary 2.750 5.875 4.500 6.625 7.437
Ukraine 4.200 5.700 4.100 3.600 8.312
Serbia 9.500 5.375 1.400 3.725 5.750
Romania 2.250 6.250 3.250 7.750 5.750
Slovenia 3.000 2.125 3.875 9.093 6.375
Azerbaijan 4.375 4.000 5.875 2.875 5.812
Russia 5.300 4.333 4.333 4.333 4.333
Slovakia 4.125 6.000 5.000 4.625 2.625
Bulgaria 3.375 4.500 4.375 3.625 5.187
Ireland 2.875 3.375 1.500 5.343 4.250
Iceland 1.500 3.000 3.833 4.562 3.625
Armenia 1.875 2.375 2.250 4.375 4.187
Moldova 5.250 3.750 2.000 2.125 1.500
Finland 3.750 2.625 1.750 2.250 3.625
Kosovo 2.333 2.875 3.000 2.000 3.781
Kazakhstan 2.875 1.125 3.125 3.000 3.625
Bosnia-Herzegovina 1.625 2.000 2.250 4.531 3.312
Latvia 2.625 2.750 1.625 3.875 2.000
Faroe Islands 1.500 2.250 2.750 1.500 1.750
Malta 1.875 2.625 1.500 1.000 2.000
Liechtenstein 0.000 6.500 0.500 0.500 1.000
Estonia 3.666 1.166 0.125 1.625 1.625
Albania 1.625 0.875 2.125 1.250 2.250
North Macedonia 0.625 1.625 1.500 0.666 3.343
Lithuania 1.750 2.375 1.125 1.375 1.125
Northern Ireland 1.625 1.250 1.125 1.500 1.750
Gibraltar 1.250 0.875 0.166 1.500 3.333
Andorra 1.500 0.666 1.666 1.000 2.000
Belarus 0.250 0.625 1.750 1.875 2.125
Luxembourg 1.250 1.125 2.250 1.250 0.750
Montenegro 0.750 1.000 1.333 2.500 1.000
Georgia 1.250 1.125 1.250 1.250 1.125
Wales 1.500 1.166 0.625 2.000 0.333
San Marino 0.166 0.833 0.333 0.666 0.833"""
CLUBS = {
    "arsenal": [0, 17, 22, 36, 44], "aston-villa": [0, 0, 17, 30.25, 35.75], "brighton": [0, 0, 16, 0, 0], "chelsea": [25, 21, 0, 30, 23.25],
    "crystal-palace": [0, 0, 0, 0, 21.88], "liverpool": [33, 19, 20, 29.5, 28.5], "manchester-city": [27, 33, 28, 14.75, 22.75],
    "manchester-united": [18, 19, 7, 32.5, 0], "newcastle-united": [0, 0, 8, 0, 21.75], "nottingham-forest": [0, 0, 0, 0, 23],
    "tottenham-hotspur": [5, 18, 0, 32.25, 26.75],
    "athletic-club": [0, 0, 0, 26.75, 12], "atletico-madrid": [19, 8, 24, 26.5, 27.25], "barcelona": [15, 9, 23, 36.25, 30],
    "celta-vigo": [0, 0, 0, 0, 16.25], "osasuna": [0, 0, 2.5, 0, 0], "rayo-vallecano": [0, 0, 0, 0, 22], "real-betis": [11, 16, 6, 19.25, 22.25],
    "real-madrid": [30, 29, 34, 24.5, 27], "real-sociedad": [9, 16, 18, 14, 0], "sevilla": [12, 21, 6, 0, 0], "villarreal": [24, 12, 16, 0, 7],
    "olimpija-ljubljana": [2, 1.5, 4, 8.375, 2.5], "maribor": [1.5, 2.5, 2, 2.5, 1.5], "celje": [0, 0, 2.5, 9.5, 11],
    "mura": [2.5, 1.5, 0, 0, 0], "koper": [0, 1.5, 0, 0, 1.5], "bravo": [0, 0, 0, 1.5, 0],
}


def main():
    path = sys.argv[1]
    data = json.load(open(path, encoding="utf-8"))
    countries = {}
    for line in COUNTRIES.splitlines():
        parts = line.rsplit(" ", 5)
        countries[parts[0]] = [float(x) for x in parts[1:]]
    data["coeff"] = {"seasons": SEASONS, "countries": countries, "clubs": CLUBS,
                     "leagueCountry": {"premier_league": "England", "la_liga": "Spain", "prvaliga": "Slovenia", "slovenia_2snl": "Slovenia"},
                     "source": "kassiesa.net UEFA rankings (method 5), 2025/26"}
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(len(countries), "countries,", len(CLUBS), "clubs with points")


if __name__ == "__main__":
    main()
