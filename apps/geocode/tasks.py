from arcgis.geocoding import geocode, Geocoder, batch_geocode
from pprint import pprint


def geo():

    g = Geocoder(
        "https://cura-gis-web.asc.ohio-state.edu/arcgis/rest/services/geocoding/USA/GeocodeServer/"
    )

    batch_size = 10
    try:
        batch_size = min(g.properties.locatorProperties.SuggestedBatchSize, batch_size)
    except:
        pass


    import json
    data = json.load(open("../../allcases/scraped-2526-tzfix.json"))

    parties = [p for c in data for p in c["parties"]]
    #print(parties[:5])

    addresses = [{"Address": p["address"],
                  "City": p["city"],
                  "Region": p["state"],
                  "Postal": p["zip_code"],
                  "OBJECTID": idx} for idx,p in enumerate(parties[:1000])]
    #print(addresses)
    #return
    res = batch_geocode(
        addresses=addresses,
        geocoder=g,
        location_type="rooftop",
    )

    for a in res:

        print(a["address"])
        pprint(a)
        break
