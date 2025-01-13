import json
import urllib.request

API_URL = "https://en.wikipedia.org/api/rest_v1/page/random/summary"


def fetch():
    print("Fetch Data")
    with urllib.request.urlopen(API_URL) as responce:
        return json.load(responce)