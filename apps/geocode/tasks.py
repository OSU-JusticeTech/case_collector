import logging
from dataclasses import dataclass

from arcgis.geocoding import geocode, Geocoder, batch_geocode
from pprint import pprint

from django.conf import settings
from django.contrib.gis.geos import Point
from django.db.models import Model

from apps.cases.models import Party
from apps.geocode.models import Location
from apps.violations.models import CodeViolation


@dataclass(frozen=True)
class GeocodeAdapter:
    # {geocoder API field name: model field name}, OR None for single-string mode
    field_map: dict | None
    address_field: str = "address"  # used only when field_map is None

    def address_payload(self, obj):
        """What gets sent to the geocoder for this object."""
        if self.field_map is None:
            return getattr(obj, self.address_field)
        return {api: getattr(obj, model) for api, model in self.field_map.items()}

    def match_kwargs(self, obj):
        """How to find all rows sharing this same address."""
        if self.field_map is None:
            return {self.address_field: getattr(obj, self.address_field)}
        return {model: getattr(obj, model) for model in self.field_map.values()}

    def hashable(self, payload):
        """A hashable dedupe/skip key for this address."""
        if self.field_map is None:
            return payload  # already a string, already hashable
        return tuple(payload.values())


ADAPTERS = {
    Party: GeocodeAdapter(field_map={
        "Address": "address",
        "City": "city",
        "Region": "state",
        "Postal": "zip_code",
    }),
    CodeViolation: GeocodeAdapter(field_map=None, address_field="address"),
}


def get_addresses(cls, adapter, skip_list, batch_size):
    addresses = []
    uniq = set()
    for p in cls.objects.filter(location__isnull=True):
        payload = adapter.address_payload(p)
        already_geocoded = cls.objects.filter(
            location__isnull=False, **adapter.match_kwargs(p)
        ).first()
        if already_geocoded is not None:
            p.location = already_geocoded.location
            p.save()
            continue

        hashable = adapter.hashable(payload)
        if hashable in uniq or hashable in skip_list:
            continue
        uniq.add(hashable)
        addresses.append((payload, p))
        if len(addresses) >= batch_size:
            break
    return addresses

def geo(cls, skip=None):

    g = Geocoder(settings.GEOCODER_URL)

    batch_size = 1000
    try:
        batch_size = min(g.properties.locatorProperties.SuggestedBatchSize, batch_size)
    except:
        pass

    skip_list = set() if skip is None else skip

    adapter = ADAPTERS[cls]
    addresses = get_addresses(cls, adapter, skip_list, batch_size)

    print("len", len(addresses))
    res = batch_geocode(
        addresses=[a[0] for a in addresses],
        geocoder=g,
        location_type="rooftop",
    )

    print("resultlen", len(res))
    unfindable = set()
    for a in res:
        # print(a["attributes"]['ResultID'])
        p_obj = addresses[a["attributes"]["ResultID"]][1]
        p_addr = addresses[a["attributes"]["ResultID"]][0]
        # print(p_obj)

        try:
            attrs = {k: v for k, v in a["attributes"].items() if k != "ResultID"}
            loc, _ = Location.objects.get_or_create(
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

            for m in cls.objects.filter(location__isnull=True, **ADAPTERS[cls].match_kwargs(p_obj)):
                m.location = loc
                m.save()

        except Exception as e:
            unfindable.add(ADAPTERS[cls].hashable(p_addr))
            logging.error(
                "could not geolocate %d: %s to %s because of %s",
                p_obj.pk,
                p_obj,
                a,
                e.__repr__(),
            )

        # print(a["address"])
        # pprint(a)
        # break
    return {"geocoded_count": len(res), "unfindable": unfindable}
