from datetime import datetime, timedelta
import json
import os

from bs4 import BeautifulSoup
from dateutil.parser import parse as dateparse
import requests

START_DATE = dateparse("2008-03-15").date()


def main():
    number_ones = open_hot_100_file("hot-100.json")
    number_ones["_last_updated"] = dateparse(
        number_ones["_last_updated"]
    ).date()
    year = number_ones["_last_updated"].year
    while year <= datetime.now().year:
        yearly_number_ones = get_yearly_number_ones(year)
        for no, number_one in yearly_number_ones.items():
            if (
                no in number_ones["songs"]
                or number_one["issue_date"] < number_ones["_last_updated"]
            ):
                continue

            print(
                f"({number_one['issue_date']}): {number_one['song']}, "
                + f"{number_one['artist']}"
            )
            get_single(number_one)
            if number_one.get("album"):
                get_album(number_one)
            else:
                number_one["album"] = ""

            if (
                number_one.get("album")
                and number_one["issue_date"] > number_one["album_release_date"]
            ):
                number_one["preferred"] = "album"
            else:
                number_one["preferred"] = "single"

            number_ones["songs"][no] = number_one
            number_ones["_last_updated"] = number_one["issue_date"]
            save_file("hot-100.json", number_ones)

        year += 1

    for no, number_one in number_ones["songs"].items():
        print(
            f"{no}|{number_one['issue_date']}|{number_one['song']}"
            + f"|{number_one['artist']}|{number_one['album']}"
            + f"|{number_one['preferred']}"
        )


def open_hot_100_file(filename):
    if not os.path.isfile(filename):
        data = {
            "_last_updated": START_DATE,
            "songs": {},
        }
        save_file(filename, data)

    with open(filename, encoding="utf-8") as infile:
        return json.load(infile)


def save_file(filename, data):
    with open(filename, "w", encoding="utf-8") as outfile:
        json.dump(data, outfile, indent=4, default=str)


def get_yearly_number_ones(year):
    number_ones = {}
    site = (
        "https://en.wikipedia.org/wiki/"
        + f"List_of_Billboard_Hot_100_number_ones_of_{year}"
    )
    page = requests.get(site)
    soup = BeautifulSoup(page.content, "html.parser")
    rows = soup.find_all("tr")
    seeking = True
    data = {
        "no_rowspan": 1,
        "song_rowspan": 1,
        "artist_rowspan": 1,
    }
    for row in rows:
        if len(row.find_all("th")) == 5:
            seeking = False
            continue

        if seeking:
            continue

        if row.find("sup"):
            row.find("sup").clear()

        row = row.find_all(["td", "th"])
        row.pop()
        if data["artist_rowspan"] == 1:
            artist = row.pop()
            data["artist"] = artist.get_text().strip()
            data["artist_rowspan"] = int(artist.get("rowspan", 1))
        else:
            data["artist_rowspan"] -= 1

        if data["song_rowspan"] == 1:
            song = row.pop()
            data["song"] = song.get_text().split('"')[1]
            data["song_link"] = song.a["href"] if song.a else None
            data["song_rowspan"] = int(song.get("rowspan", 1))
        else:
            data["song_rowspan"] -= 1

        data["issue_date"] = dateparse(
            f"{row.pop().get_text()}, {year}"
        ).date()

        if data["no_rowspan"] == 1:
            no = row.pop()
            data["no"] = no.get_text().strip()
            data["no_rowspan"] = int(no.get("rowspan", 1))
            if data["no"] != "re":
                number_ones[data["no"]] = {
                    "issue_date": data["issue_date"],
                    "song": data["song"],
                    "song_link": data["song_link"],
                    "artist": data["artist"],
                }
        else:
            data["no_rowspan"] -= 1

        if data["issue_date"] >= dateparse(f"{year}-12-25").date() or data[
            "issue_date"
        ] >= datetime.now().date() + timedelta(days=1):
            break

    return number_ones


def get_single(number_one):
    site = f"https://en.wikipedia.org{number_one['song_link']}"
    page = requests.get(site)
    soup = BeautifulSoup(page.content, "html.parser")
    rows = soup.find_all("tr")
    for row in rows:
        if row.th and row.th.get_text().startswith("from the "):
            number_one["album"] = row.a.get_text()
            number_one["album_link"] = row.a["href"]
        if row.th and row.th.get_text() == "Released":
            release_date = dateparse(next(row.td.stripped_strings)).date()
            number_one["release_date"] = release_date
            break


def get_album(number_one):
    site = f"https://en.wikipedia.org{number_one['album_link']}"
    page = requests.get(site)
    soup = BeautifulSoup(page.content, "html.parser")
    rows = soup.find_all("tr")
    for row in rows:
        if row.th and row.th.get_text() == "Released":
            album_release_date = dateparse(
                next(row.td.stripped_strings)
            ).date()
            number_one["album_release_date"] = album_release_date
            break


if __name__ == "__main__":
    main()
