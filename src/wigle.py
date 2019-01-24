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

class Wigle():

    def __init__(self):
        self.api_name = os.environ["WIGLE_NAME"]
        self.api_key = os.environ["WIGLE_KEY"]

    def _api_request(self, api_stub, qs_params, method="GET"):
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
        print(full_url)
        resp = requests.request(method, full_url,
                                auth=(self.api_name, self.api_key,))
        resp = json.loads(resp.text)
        return resp

    def get_cell_detail(self, operator, lac, cid):
        """ Get detail for a specific CID/LAC combo """
        # TODO: this never seems to actually return any search results?
        qs_params = {
            "operator": operator,
            "lac": lac, # TODO: why is it lac here, but cell_net below?
            "cid": cid,
        }
        return self._api_request("network/detail", qs_params)

    def cell_search(self, lat, lon, gps_offset, cell_id, tac = None):
        """ gps_offset is so that we can specify the search radius around the GPS coords."""
        # TODO: this doesn't return results as often as it should, meaning we end up marking things are more suspicious than they actually are.
        params = {
            "latrange1": lat + gps_offset,
            "latrange2": lat - gps_offset,
            "longrange1": lon + gps_offset,
            "longrange2": lon - gps_offset,
            "cell_id": cell_id,
        }
        if tac is not None:
            params["cell_net"] = tac
        return self._api_request("cell/search", params)

#    def cell_search(self, latrange1, latrange2, longrange1, longrange2):
#        qs_params = {
#            "latrange1": latrange1,
#            "latrange2": latrange2,
#            "longrange1": longrange1,
#            "longrange2": longrange2,
#        }
#        return _api_request("cell/search", qs_params)

    def run_test(self):
        """ Run some basic tests """
        print(f"{resp['user']}'s rank this month: {resp['statistics']['monthRank']}")
        """
        resp = get_cell_detail("310260", "14450", "25541899")
        print(f"\n=============\n{resp}\n============")
        resp = get_cell_detail("310260", "14450", "666")
        print(f"\n=============\n{resp}\n============")
        """

        resp = self.cell_search("37.781", "37.782", "-122.421", "-122.422")
        print(f"\n=============\n{resp}\n============")


if __name__ == "__main__":
    w = Wigle()
    w.run_test()

