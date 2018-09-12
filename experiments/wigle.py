#!/usr/bin/python3
"""
Interface to the wigle.net API
put the username and access key in the following environment variables: WIGLE_NAME, WIGLE_KEY
author: cooperq@eff.org
licence: GPL3
"""
import json
import os
import urllib
import requests

def _api_request(api_stub, qs_params, method="GET"):
    """
    make a request to the wigle.net API
    @param string api_stub The last part of the path to the API endpoint after /api/v2/
    @param dictionary qs_params A dictionary containing key,value pairs to append to the querystring
    @param string method what HTTP method to use, defaults to "GET"
    @return dictionary returns the decoded json response from wigle as a dict
    """
    # TODO raise a useful error if either env variable is missing
    query = urllib.parse.urlencode(qs_params)
    full_url = f"https://api.wigle.net/api/v2/{api_stub}?{query}"
    resp = requests.request(method, full_url,
                            auth=(os.environ["WIGLE_NAME"], os.environ["WIGLE_KEY"],))
    resp = json.loads(resp.text)
    return resp

def get_stats_user():
    """ Get statistics for the currently logged in user """
    return _api_request("stats/user", {})

def get_cell_detail(operator, lac, cid):
    """ Get detail for a specific CID/LAC combo """
    qs_params = {
        "operator": operator,
        "lac": lac,
        "cid": cid,
    }
    return _api_request("network/detail", qs_params)

def test():
    """ Run some basic tests """
    resp = get_stats_user()
    print(f"{resp['user']}'s rank this month: {resp['statistics']['monthRank']}")

    resp = get_cell_detail("310260", "14450", "25541899")
    print(f"\n=============\n{resp}\n============")
    resp = get_cell_detail("310260", "14450", "666")
    print(f"\n=============\n{resp}\n============")

def main():
    """ main entry point, only used to run tests """
    test()

if __name__ == "__main__":
    main()
