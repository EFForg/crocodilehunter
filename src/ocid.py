import requests
from access_points import get_scanner


def ocid_get_location(api_key):
    url = "https://us1.unwiredlabs.com/v2/process.php"
    wifi_scanner = get_scanner()
    aps = wifi_scanner.get_access_points()
    aps = [{'bssid': ap.bssid, 'signal': ap.quality*-1} for ap in aps]

    payload = {
        'token': api_key,
        'address': 0,
        'wifi': aps
    }
    response = requests.request("POST", url, json=payload)

    return response.json()

def ocid_search_cell(api_key, mcc, mnc, lac, cid):
    url = "http://opencellid.org/cell/get"
    payload = {
        "key": api_key,
        "mcc": mcc,
        "mnc": mnc,
        "lac": lac,
        "cellid": cid,
        "radio": "LTE",
        "format": "json"
    }
    response = requests.request("GET", url, params=payload)
    return response.json()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("ocid.py <api_key>")
        sys.exit(1)
    api_key = sys.argv[1]
    mcc = 310
    mnc = 410
    lac = 35634
    cid = 170003605
    print(ocid_get_location(api_key))
    print(ocid_search_cell(api_key,mcc,mnc,lac,cid))
