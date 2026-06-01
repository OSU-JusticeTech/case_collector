from arcgis.geocoding import geocode, Geocoder, batch_geocode
from pprint import pprint

from django.conf import settings
from django.contrib.gis.geos import Point
from django.db.models import Model

from apps.cases.models import Party
from apps.geocode.models import Location


def geo():

    g = Geocoder(settings.GEOCODER_URL)

    batch_size = 1000
    try:
        batch_size = min(g.properties.locatorProperties.SuggestedBatchSize, batch_size)
    except:
        pass

    addresses = []
    uniq = set()
    for p in Party.objects.filter(location__isnull=True):
        already_geocoded = Party.objects.filter(
            address=p.address,
            city=p.city,
            state=p.state,
            zip_code=p.zip_code,
            location__isnull=False,
        ).first()
        if already_geocoded is not None:
            p.location = already_geocoded.location
            p.save()
            continue
        addr = {
            "Address": p.address,
            "City": p.city,
            "Region": p.state,
            "Postal": p.zip_code,
        }
        hashable = tuple(addr.values())
        if hashable not in uniq:
            uniq.add(hashable)
            addresses.append((addr, p))
            if len(addresses) >= batch_size:
                break

    print("len", len(addresses))
    res = batch_geocode(
        addresses=[a[0] for a in addresses],
        geocoder=g,
        location_type="rooftop",
    )

    print("resultlen", len(res))
    for a in res:
        # print(a["attributes"]['ResultID'])
        p_obj = addresses[a["attributes"]["ResultID"]][1]
        # print(p_obj)

        attrs = a["attributes"]
        loc = Location.objects.create(
            full_address=a["address"],
            street_number=attrs.get("AddNum", ""),
            street_name=attrs.get("StName", ""),
            street_type=attrs.get("StType", ""),
            street_direction=attrs.get("StDir", ""),
            unit_type=attrs.get("UnitType", ""),
            unit_number=attrs.get("UnitName", ""),
            city=attrs.get("City", ""),
            county=attrs.get("Subregion", ""),
            state=attrs.get("Region", ""),
            state_code=attrs.get("RegionAbbr", ""),
            postal_code=attrs.get("Postal", ""),
            postal_code_ext=attrs.get("PostalExt", ""),
            country=attrs.get("Country", ""),
            rooftop=Point(
                a["location"]["x"],  # longitude
                a["location"]["y"],  # latitude
                srid=4326,  # WGS84
            ),
            geocode_score=a.get("score"),
            geocode_type=attrs.get("Addr_type", ""),
            geocode_rank=attrs.get("Rank", -1),
            raw_geocode=attrs,
        )

        matching_parties = Party.objects.filter(
            address=p_obj.address,
            city=p_obj.city,
            state=p_obj.state,
            zip_code=p_obj.zip_code,
        )

        for m in matching_parties:
            m.location = loc
            m.save()

        # print(a["address"])
        # pprint(a)
        # break
    return len(res)
