import textwrap
import pytest

from random_wikipedia_article_bebebeeeyan.fetch import fetch

def main():
    # raise Exception("Boom!")
    data = fetch()
    print(data["title"], end="\n\n")
    print(textwrap.fill(data["extract"]))


import json
import urllib.request

API_URL = "https://en.wikipedia.org/api/rest_v1/page/random/summary"


@pytest.fixture
def random_wikipedia_article():
    with urllib.request.urlopen(API_URL) as responce:
        return json.load(responce)
