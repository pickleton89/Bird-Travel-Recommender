Great, I’ll compile a comprehensive and technically detailed report on the public-facing eBird API. This will include a breakdown of all available endpoints, parameters you can use, what kind of data each endpoint returns, and how to interpret the responses. I’ll also provide clear explanations in regular and technical language, with Python code examples where helpful, to support your app development and learning goals.

I’ll let you know as soon as the report is ready.

# eBird API 2.0 – Comprehensive Endpoint Guide

**Overview:** The eBird API 2.0 provides programmatic access to bird observation data, hotspot information, taxonomy, and region lists from the eBird citizen science platform. This guide lists all public endpoints in the eBird 2.0 API and explains, in both general terms and technical detail, what each endpoint does, what parameters it accepts, what data it returns, and common use cases. Code examples in Python (`requests` library) are included to demonstrate how to call the API and handle the responses. The guide assumes you have an **eBird API key** (required for most endpoints) and some basic familiarity with JSON and Python.

**Authentication & Usage:** Most eBird API endpoints require an API key associated with your eBird account. Include this key in each request as an HTTP header (`X-eBirdApiToken`) or as a query parameter (`key`). The base URL for all endpoints is **`https://api.ebird.org/v2/`** (all responses are JSON by default unless noted). In Python, you can supply the API key like:

```python
headers = {"X-eBirdApiToken": "YOUR_API_KEY"}
response = requests.get(url, headers=headers)
```

Be mindful of usage: there is no strict public rate limit, but excessive requests can lead to your key being temporarily banned. It’s good practice to space out requests (e.g. a maximum of ~1 per second) and avoid downloading extremely large data sets in one go. The **Terms of Use** prohibit redistribution of raw data, so use the API for analysis or building applications, not bulk dumping of eBird data.

## Full List of eBird API Endpoints

eBird API 2.0 endpoints are organized by categories. Below is a list of all available endpoints, grouped by function:

- **Observation Data (recent and historical observations)** – under the path `data/obs` (and one under `data/nearest`):
    
    - **Recent observations in a region:** `GET /data/obs/{regionCode}/recent` – Latest sightings in a specified region (country, state, county, or hotspot).
        
    - **Recent notable observations in a region:** `GET /data/obs/{regionCode}/recent/notable` – Latest rare/unusual sightings in a region.
        
    - **Recent observations of a species in a region:** `GET /data/obs/{regionCode}/recent/{speciesCode}` – Latest sightings of a particular species in a region.
        
    - **Recent nearby observations:** `GET /data/obs/geo/recent?lat={lat}&lng={lng}` – Recent sightings within a radius around given GPS coordinates.
        
    - **Recent nearby observations of a species:** `GET /data/obs/geo/recent/{speciesCode}?lat={lat}&lng={lng}` – Recent sightings of a given species around coordinates.
        
    - **Nearest observations of a species:** `GET /data/nearest/geo/recent/{speciesCode}?lat={lat}&lng={lng}` – Nearest location(s) where the species was seen recently.
        
    - **Recent nearby notable observations:** `GET /data/obs/geo/recent/notable?lat={lat}&lng={lng}` – Recent rare sightings within a radius of coordinates.
        
    - **Recent checklists feed:** `GET /product/lists/{regionCode}` – Most recent eBird **checklists** submitted in a region (this endpoint is under “product” in the URL).
        
    - **Historic observations on a date:** `GET /data/obs/{regionCode}/historic/{year}/{month}/{day}` – All observations on a specific date in a region (e.g. for “big day” history).
        
- **Product Endpoints (top lists and summaries)** – under `product/`:
    
    - **Top 100 contributors on a date:** `GET /product/top100/{regionCode}/{year}/{month}/{day}` – Top 100 eBirders (users) in the region on that date, ranked by species count or checklist count.
        
    - **Checklists feed on a date:** `GET /product/lists/{regionCode}/{year}/{month}/{day}` – List of all checklists submitted in the region on a given date.
        
    - **Regional statistics on a date:** `GET /product/stats/{regionCode}/{year}/{month}/{day}` – Summary statistics for the region on that date (e.g. total checklists, total species, etc.).
        
    - **Species list for a region:** `GET /product/spplist/{regionCode}` – The list of all species ever reported in the region (historical species list).
        
    - **View checklist:** `GET /product/checklist/view/{subId}` – Detailed contents of a specific checklist (all observations and checklist metadata).
        
- **Hotspot Endpoints** – under `ref/hotspot`:
    
    - **Hotspots in a region:** `GET /ref/hotspot/{regionCode}` – All eBird hotspots within the given region (country, state, or county).
        
    - **Nearby hotspots:** `GET /ref/hotspot/geo?lat={lat}&lng={lng}` – Hotspot locations within a radius of specified coordinates.
        
    - **Hotspot info:** `GET /ref/hotspot/info/{locId}` – Detailed information for a specific hotspot (given its location ID).
        
- **Taxonomy Endpoints** – under `ref/taxonomy` and related paths:
    
    - **eBird Taxonomy:** `GET /ref/taxonomy/ebird` – The full eBird species taxonomy (or a filtered subset).
        
    - **Taxonomic forms:** `GET /ref/taxon/forms/{speciesCode}` – List of subspecies or forms for the given species (as recognized in eBird taxonomy).
        
    - **Taxa locale codes:** `GET /ref/taxa-locales/ebird` – Supported locale codes for common names (languages and regional dialects for species names).
        
    - **Taxonomy versions:** `GET /ref/taxonomy/versions` – List of all eBird taxonomy version identifiers (with indication of the latest).
        
    - **Taxonomic groups:** `GET /ref/sppgroup/{speciesGrouping}` – List of species in a given group or family (e.g. all “hawks”, “ducks”, etc.).
        
- **Region & Geography Endpoints** – under `ref/region` (and one under `ref/adjacent`):
    
    - **Region info:** `GET /ref/region/info/{regionCode}` – Metadata about a region (name, hierarchical level, parent region, etc.).
        
    - **Sub-region list:** `GET /ref/region/list/{regionType}/{regionCode}` – List of all subregions of a given type within a specified region (for example, all counties within a state).
        
    - **Adjacent regions:** `GET /ref/adjacent/{regionCode}` – Regions adjacent to the given region (e.g. neighboring counties). _Note:_ This currently works only for certain region types (U.S. counties, New Zealand and Mexico subnational2 regions).
        

Below, we go through each endpoint in detail. For each, we explain its purpose, required and optional parameters, the data structure of the response, typical use cases, and any special considerations or limitations. Example Python code is provided to illustrate how to call the endpoint and handle the result.

---

## Observational Data Endpoints (`data/obs`)

These endpoints return recent or historical bird observations (sightings) submitted to eBird. They are the core of the API for retrieving who-saw-what-where-and-when. All observation endpoints return JSON arrays of **observation records**, where each record is a JSON object with fields describing the sighting (species, location, time, count, etc.). Unless otherwise noted, results are limited to observations up to the past 30 days.

Each observation record in a response typically includes fields such as:

- `speciesCode` (six-letter species identifier in eBird’s taxonomy),
    
- `comName` (common name of the species),
    
- `sciName` (scientific name),
    
- `locId` (location ID, e.g. hotspot or personal location code),
    
- `locName` (name/description of the location),
    
- `obsDt` (date and time of the observation in local time),
    
- `howMany` (count of individuals observed, if provided),
    
- `lat`, `lng` (coordinates of the sighting),
    
- `obsValid` (boolean, if the record is valid),
    
- `obsReviewed` (boolean, if the record was reviewed by moderators),
    
- `locationPrivate` (boolean, true if location is a private/personal location),
    
- `subId` (submission ID of the checklist containing the observation).
    

For certain endpoints or when a “**detail=full**” parameter is used, additional fields may appear, such as observer’s name, checklist ID, or higher-level region codes. By default, most observation endpoints return “simple” detail (a subset of fields).

### Recent Observations in a Region (`GET /data/obs/{regionCode}/recent`)

**What it does:** Retrieves the most recent observations of birds in the specified region (country, state/province, county, or specific hotspot/location). The result will include at most one record per species – specifically the latest sighting of each species reported in that region, up to the last 30 days. This is useful for getting an overview of what species have been seen recently in an area.

**Required path parameter:**

- `regionCode` – The region’s code. This can be a 2-letter country code (e.g. `US`, `IN`), a country-subdivision code (subnational1, e.g. `US-NY` for New York state, `IN-KL` for Kerala), a subnational2 code (county level, e.g. `US-NY-109` for Tompkins County), or a specific location ID (`locId` for a hotspot or personal location, such as `L123456`). (See eBird documentation for region code formats.)
    

**Optional query parameters:**

- `back` (integer 1–30, default 14): How many days back from today to include in the search. For example, `back=7` restricts to the last week. The default is 14 days.
    
- `cat` (string, default “all”): Limit observations to certain taxonomic categories. For example, `cat=species` would exclude forms, hybrids, domestics, etc. (Valid categories include `species`, `issf` (subspecies), `hybrid`, `domestic`, etc.)
    
- `hotspot` (true/false, default false): If true, return only observations made at designated **hotspots** (excluding personal locations).
    
- `includeProvisional` (true/false, default false): If true, include unconfirmed reports that have not yet been reviewed (“provisional” observations). By default, only confirmed sightings are returned.
    
- `maxResults` (integer 1–10000, default is no limit): If set, limit the number of observation records returned. Without this, all recent species observations up to the date range will be returned.
    
- `r` (region or location code, up to 10 codes, optional): If provided, filters results to one or more specific locations within the region. For example, in a county search you could set `r` to specific hotspot IDs to get recent observations only from those hotspots.
    
- `sppLocale` (string, default `"en"`): Locale for species common names. This controls the language of the `comName` field (e.g. `"es"` for Spanish names).
    

**Returns:** A JSON array of observation objects (one per species). Each object contains at least the fields listed in the introduction above (speciesCode, comName, sciName, locId, locName, obsDt, howMany, lat, lng, etc.). By default, the **“simple”** detail level is returned, which excludes some less-used fields. In this simple format, for example, you will see `subId` (checklist ID) but not the observer’s name or country/subnational codes. The data is unsorted (or in no particular order by default). If you need it sorted (say by date or species), you can sort client-side or use other endpoints (see below).

**Use cases:** This endpoint is great for displaying a **“recent sightings” feed** for a region. For example, a birding app can show “recent birds in New York State” or “recent birds at ” using this data. It’s also useful for maintaining a regional species list that updates with new sightings (since it gives the latest observation of each species). Note that it will not give duplicate species entries – each species appears at most once. If you want _all_ observations (not just one per species), you would use the “historic observations on a date” endpoint or other data download methods.

**Example – Get recent sightings in a region (Python):**

```python
import requests

api_token = "YOUR_EBIRD_API_KEY"
region = "US-AZ"  # Arizona state code as an example
url = f"https://api.ebird.org/v2/data/obs/{region}/recent?back=7"
headers = {"X-eBirdApiToken": api_token}
response = requests.get(url, headers=headers)
if response.status_code == 200:
    observations = response.json()  # list of observation dicts
    print(f"Retrieved {len(observations)} recent observations in {region}")
    # Example: print the first observation's species and date
    if observations:
        first = observations[0]
        print(first["comName"], "seen on", first["obsDt"])
else:
    print("Error:", response.status_code, response.text)
```

In this snippet, we request the past week of sightings in Arizona. The response will be a list of observations. We then access the first entry’s common name and date. Each element of `observations` is a Python dict; for example, `first["comName"]` might be `"Northern Cardinal"` and `first["obsDt"]` `"2025-06-05 14:32"` (meaning a Northern Cardinal was seen on June 5, 2025 at 2:32 PM). You can iterate through this list to display each species and when/where it was last seen. For a more detailed output (including observer info or multiple sightings per species), consider other endpoints or adding parameters as described below.

### Recent Notable Observations in a Region (`GET /data/obs/{regionCode}/recent/notable`)

**What it does:** Retrieves recent **notable sightings** in the given region. “Notable” typically means rare birds or unusual observations, such as species that are flagged as rare for the area or out-of-season sightings. Essentially, this is the feed of rarities for the region in the past up to 30 days. Like the previous endpoint, it returns at most one observation per species (the most recent notable sighting of each notable species).

**Required path parameter:** `regionCode` (same format as above, e.g. country/region code or hotspot ID).

**Optional query parameters:**

- `back` (1–30, default 14): Days back to include (e.g. `back=30` for the last month).
    
- `detail` (`simple` or `full`, default `simple`): Level of detail for the response. By default it’s simple (basic fields). If `detail=full`, the observation objects will include additional fields such as the observer’s name, checklist ID, species’ region codes, etc..
    
- `hotspot` (true/false, default false): If true, include only observations from hotspots (exclude private locations).
    
- `maxResults` (1–10000, no default): Limit number of records returned.
    
- `r` (location code filter, up to 10): Filter to specific location(s) within the region, if desired (same usage as in previous endpoint).
    
- `sppLocale` (locale for names, default "en"): Language for species common names.
    

**Returns:** A JSON array of notable observation records. The structure is similar to the “recent observations” endpoint, but each record is by definition something eBird considers notable (rare). In **simple** detail, fields are like speciesCode, comName, locName, obsDt, etc. In **full** detail, you will get extra fields including specific region codes (`countryCode`, `subnational1Code`, etc.), the observer’s name (`firstName`, `lastName`), whether the observation had media (`hasRichMedia`), and identifiers like `obsId` and `checklistId` for the record. For example, a full-detail notable sighting might include: `"comName": "Little Blue Heron"`, `"obsDt": "2017-08-23 10:11"`, `"userDisplayName": "Kathleen Ashman"`, `"obsId": "OBS527233428"`, `"checklistId": "CL22364"`, etc., indicating who reported it and linking to the checklist.

**Use cases:** This endpoint is perfect for generating a **“rare bird alert”** or **notable sightings bulletin** for an area. Birding organizations often want to display what unusual species have been seen recently (for example, a local Audubon chapter might embed a feed of rare birds in their county). An app could use this to notify users of lifers or rarities nearby. Keep in mind it will not list common species, only those flagged as notable by eBird’s filters.

**Example – List recent rare birds in a region:**

```python
region = "US-NY"  # New York state
url = f"https://api.ebird.org/v2/data/obs/{region}/recent/notable?detail=full"
resp = requests.get(url, headers={"X-eBirdApiToken": api_token})
notable_obs = resp.json()
for obs in notable_obs:
    species = obs["comName"]
    loc = obs["locName"]
    date = obs["obsDt"]
    observer = obs.get("userDisplayName", "<unknown>")
    print(f"{species} seen at {loc} on {date} (reported by {observer})")
```

This will print out each notable species, where and when it was seen, and who observed it, for New York. For example, it might output a line like: **“Garganey seen at Jamaica Bay Wildlife Refuge on 2025-06-10 07:15 (reported by Jane Doe)”**. Such information could be used to alert birders to go look for the Garganey (a rare duck) at that hotspot. The `userDisplayName` comes in the full detail response; if `detail=simple` was used, observer name wouldn’t be included.

### Recent Observations of a Species in a Region (`GET /data/obs/{regionCode}/recent/{speciesCode}`)

**What it does:** Retrieves recent sightings (past up to 30 days) of a **specific species** within a given region. This filters the observations to one target species, and returns the most recent occurrences of that species. Unlike the general “recent observations” endpoint (which gives one per species), this one can return multiple entries (since it is one species, you may get several recent sightings of it, each at different locations or times). The results include only the latest observation **per location** for that species in the region. In other words, if the species was seen multiple times at the same location in the timeframe, you’ll get the most recent one from that location.

**Required path parameters:**

- `regionCode` – Region within which to search (same format as above).
    
- `speciesCode` – The eBird species code for the target species. This is typically a six-character string (sometimes with a digit if the name is duplicate). For example, Canada Goose’s code is `cangoo`, Northern Cardinal is `norcar`, etc. If you don’t know the code, you can find it from the taxonomy or by looking up a species on eBird (the species’s URL contains the code).
    

**Optional query parameters:**

- `back` (1–30, default 14): Days back to search.
    
- `hotspot` (true/false, default false): Only include hotspot locations if true.
    
- `includeProvisional` (true/false, default false): Include unconfirmed records if true.
    
- `maxResults` (1–10000, no default): Maximum number of observations to return. If the species is very common, you might want to limit this.
    
- `r` (location filter): Up to 10 location codes to filter within the region (optional). If provided, `regionCode` in the path should be empty (`.../obs//recent/speciesCode?r=Loc1,Loc2,...`) as per eBird docs.
    
- `sppLocale` (locale for common name, default "en"): Language for the species’ common name.
    

**Note:** If using the `r` filter (specific locations), eBird’s documentation says to set the `regionCode` part of the path to an empty string. For example: `/data/obs//recent/housep?r=L123456,L234567` would get House Sparrow at two specific locations.

**Returns:** A JSON array of observations for the given species. Each object has the standard fields (comName, sciName, locId, locName, obsDt, howMany, etc.) for that species’ sightings. By design, you will get at most one entry per distinct location where the species was observed (the latest at each location). For example, if your species is “Snowy Owl” and in the last 10 days it was seen at three different locations in the region (say an airport, a lake, and a field), you will get three records – one for each site’s most recent Snowy Owl sighting. This endpoint does _not_ include observer identity or other extended info (there is no `detail=full` option here; all returned fields are the default set).

**Use cases:** Use this endpoint when you want to track a **single species**. For instance, a user of your app may want to know “Where have _Barn Owls_ been seen recently in California?” You can call this and display a map of the latest Barn Owl sightings in California. It’s also useful for implementing a “target species” feature – e.g. find the nearest or latest occurrences of a bird the user hasn’t seen yet. Note that if you need _the single closest_ sighting to a point, consider the “nearest observations” endpoint below; if you need _all_ sightings (not just latest per location), you might need to use the eBird archive or other data services, since the API always condenses to one-per-location for recent endpoints.

**Example – Fetch recent sightings of a species:**

```python
species = "balori"  # Bald Eagle (Haliaeetus leucocephalus) speciesCode
region = "US-NY"
url = f"https://api.ebird.org/v2/data/obs/{region}/recent/{species}?back=30"
resp = requests.get(url, headers={"X-eBirdApiToken": api_token})
eagle_sightings = resp.json()
for obs in eagle_sightings:
    print(f"{obs['comName']} at {obs['locName']} on {obs['obsDt']}")
```

This might output lines like: “**Bald Eagle at Cayuga Lake on 2025-06-11 15:45**” and “**Bald Eagle at Montezuma NWR on 2025-06-10 08:20**”, etc., showing the latest eagle at each site in New York over the last month. From such results, you could, for example, mark these locations on a map for the user to chase the species.

### Recent Nearby Observations (`GET /data/obs/geo/recent?lat={lat}&lng={lng}`)

**What it does:** Retrieves recent bird observations within some radius of a given geographic point (latitude/longitude). This answers “what birds have been seen near me recently?” Results include at most one observation per species (the most recent sighting of each species in the area), within the last N days (default 14). The search radius defaults to 25 km and can be adjusted up to a maximum of 50 km.

**Required query parameters:**

- `lat` (latitude, required): Latitude of the center point, in decimal degrees (WGS84). Must be between -90 and 90. Use only two decimal places of precision (approx ~1 km).
    
- `lng` (longitude, required): Longitude of the center point, in decimal degrees, between -180 and 180.
    

**Optional query parameters:**

- `back` (1–30, default 14): Days back to include.
    
- `cat` (taxonomic category filter, default all): Same as in previous endpoints; e.g. `cat=species` to only include species (no subspecies, etc.).
    
- `dist` (0–50, default 25): Radius in kilometers for the search. The max allowed is 50 km. If you specify larger, it will be capped at 50.
    
- `hotspot` (true/false, default false): If true, only include sightings at hotspots.
    
- `includeProvisional` (true/false, default false): If true, include unconfirmed (provisional) records.
    
- `maxResults` (1–10000, no default): Limit on number of observations to return. Without this, it will return one entry per species found in the area/time window.
    
- `sort` (`"date"` or `"species"`, default `"date"`): How to sort the results. By default, results are sorted by date (most recent first). If `sort=species`, results are sorted taxonomically (according to eBird taxonomy order).
    
- `sppLocale` (locale for names, default "en"): Language for common names.
    

**Returns:** A JSON array of observation objects (one per species, most recent sighting). The fields are the same as described earlier (speciesCode, comName, locName, obsDt, etc.). For example, if 100 species have been reported around that coordinate in the last 2 weeks, you’ll get up to 100 records (one for each species). If `sort=date`, the first element in the array will be the most recently observed species in that area. If `sort=species`, the array will be in taxonomic order (e.g. ducks first, then chickens, etc., as eBird taxonomy defines). The sample response in the docs shows entries like a Domestic goose, Canada Goose, Wood Duck, etc., with their counts and locations.

**Use cases:** This endpoint powers any “**What's been seen near me?**” feature. For example, a mobile app can use the phone’s GPS to get coordinates and then show a list of species seen nearby recently. This is also useful for trip planning: input the coordinates of a park or reserve to see what you might expect there. Because it only returns one record per species, it’s not overwhelming – it gives a checklist-like summary of species near that location. If you need specific occurrences or multiple sightings per species, you might need to use a combination of this and other endpoints (like iterate through species of interest and use species-specific queries).

**Example – Get recent birds near a location:**

```python
lat, lng = 34.988, -111.490  # some coordinates (e.g. near Sedona, AZ)
url = f"https://api.ebird.org/v2/data/obs/geo/recent?lat={lat}&lng={lng}&dist=10"
resp = requests.get(url, headers={"X-eBirdApiToken": api_token})
nearby_obs = resp.json()
print(f"Species reported within 10km: {len(nearby_obs)}")
# Print the five most recent species and their sighting info
nearby_obs.sort(key=lambda o: o["obsDt"], reverse=True)  # sort by date descending
for obs in nearby_obs[:5]:
    print(f"{obs['comName']} – seen {obs['obsDt']} at {obs['locName']}")
```

This will fetch species seen within 10 km of the given lat/long. We then sort by date (though if we had used `sort=date` in the request, it would likely already be sorted by recency). The output might be, for example:

```
Species reported within 10km: 45  
House Finch – seen 2025-06-12 18:00 at Sedona Wastewater Treatment Plant  
Black-throated Sparrow – seen 2025-06-12 17:45 at Sedona Wastewater Treatment Plant  
Turkey Vulture – seen 2025-06-12 17:30 at Red Rock State Park  
... 
```

This shows the recent birds in the area and where they were spotted. You could use this data to show pins on a map for each recent species, or simply list them for a user to know what’s around.

### Recent Nearby Observations of a Species (`GET /data/obs/geo/recent/{speciesCode}?lat={lat}&lng={lng}`)

**What it does:** Similar to the above “nearby observations” endpoint, but filtered for **one species**. It returns all recent sightings of the specified species within the radius of a given point (up to the last 30 days). In contrast to the generic nearby endpoint which returned one entry per species, this will return potentially multiple records (if the species was seen at multiple different locations around the point). However, it will still return at most one record _per location_ (the latest at each location) for that species, within the time window.

**Path parameter:** `speciesCode` – The species of interest (same code format as before).

**Required query parameters:** `lat` and `lng` (the coordinates of the center point, same usage as in the previous endpoint).

**Optional query parameters:**

- `back` (1–30 days, default 14): Days back to search.
    
- `dist` (0–50 km, default 25): Radius around the point.
    
- `hotspot` (true/false, default false): If true, only include sightings at hotspots.
    
- `includeProvisional` (true/false, default false): Include unconfirmed sightings if true.
    
- `maxResults` (1–10000, no default): Max number of records to return.
    
- `sppLocale` (locale for common name, default "en").
    

**Returns:** A JSON array of observation objects for the given species, each representing the most recent sighting at a distinct location within the radius. For example, if the species is **Horned Lark** (`horlar`) and within 25 km there are 4 hotspots where it was seen in the last two weeks, you’ll get 4 records (one per hotspot). Each includes the usual fields (comName, locName, obsDt, etc.). The `comName` will be the same for all (the species in question), but lat/lng and locName will differ, showing different locations. This endpoint doesn’t have a sort parameter; typically you might want to sort by date or distance after fetching if needed. The **species code** is echoed in each record too (so you’ll see the same speciesCode repeated).

**Use cases:** When a user wants to find where a particular bird has been seen near a location. For instance, “Where around can I find a Snowy Owl recently?” A bird-finding application can use this to guide users to locations of target species. It’s also useful for confirming if a species is currently in an area: e.g. a researcher might query a rare species around a specific reserve to see if it’s been reported lately.

**Example – Find recent records of a species near coordinates:**

```python
species = "rufhum"  # Rufous Hummingbird species code
lat, lng = 47.6097, -122.3331  # Seattle, WA
url = f"https://api.ebird.org/v2/data/obs/geo/recent/{species}?lat={lat}&lng={lng}&dist=50"
response = requests.get(url, headers={"X-eBirdApiToken": api_token})
records = response.json()
for rec in records:
    print(f"{rec['comName']} seen on {rec['obsDt']} at {rec['locName']}")
```

Assuming Rufous Hummingbirds have been reported within 50 km of Seattle in the timeframe, this might print for example: “**Rufous Hummingbird seen on 2025-06-05 09:00 at Discovery Park**” and “**Rufous Hummingbird seen on 2025-06-03 07:15 at Union Bay Natural Area**”, etc. Each line corresponds to the latest sighting at a different site. If the species hasn’t been reported nearby recently, you might get an empty list.

### Nearest Observations of a Species (`GET /data/nearest/geo/recent/{speciesCode}?lat={lat}&lng={lng}`)

**What it does:** Finds the nearest locations to a given point where the target species has been observed recently. This is a special endpoint for answering “Where is the closest to me right now?”. It will search within a 50 km radius (or less if specified) around the given coordinates for the species, and return observations ordered by distance (closest first).

**Path parameter:** `speciesCode` – The species of interest.

**Required query parameters:** `lat` and `lng` for the point of reference (same usage as previous endpoints).

**Optional query parameters:**

- `back` (1–30 days, default 14): How far back to search for the species.
    
- `hotspot` (true/false, default false): If true, restrict to sightings at hotspots.
    
- `includeProvisional` (true/false, default false): Include unconfirmed sightings if true.
    
- `dist` (0–50 km, default **no default** which effectively means 50): You can specify a maximum distance (in km) to look. If not specified, it will consider up to 50 km by default. If the species hasn’t been seen within that distance/time, you might get an empty response.
    
- `maxResults` (1–3000, default 3000): The maximum number of observations to return. The default is 3000 (which essentially means "no limit" for most practical uses, since it’s unlikely to find more than that in a 50 km radius).
    
- `sppLocale` (locale for names, default "en").
    

**Returns:** A JSON array of observation records for the species. Each record is the _same format as other observations_, but importantly, the list is sorted by distance from your provided lat/lng (closest first). The API doesn’t directly return the distance value, but since it’s sorted, the first item is the nearest sighting. You may infer distance by comparing coordinates if needed, or by using the Haversine formula externally. The fields are standard (speciesCode, comName, locName, obsDt, lat, lng, etc.). If no one has reported the species in the area/time, the response will be an empty array.

**Use cases:** This is extremely useful for birders chasing a species – for example, “Where is the nearest reported Snowy Owl?” A field guide app could have a feature “Nearest [target bird]” that uses this endpoint to direct the user to the closest recent location of that bird. Another use is in automated tools for listing the closest lifers (birds not on one’s life list); the tool could iterate over target species codes and use this endpoint to see if any have been spotted nearby recently.

**Example – Nearest sighting of a species:**

```python
species = "snobow"  # Snowy Owl
coords = (42.45, -76.50)  # Ithaca, NY area
url = f"https://api.ebird.org/v2/data/nearest/geo/recent/{species}?lat={coords[0]}&lng={coords[1]}&back=30"
resp = requests.get(url, headers={"X-eBirdApiToken": api_token})
sightings = resp.json()
if sightings:
    closest = sightings[0]
    print(f"Nearest {closest['comName']} was seen on {closest['obsDt']} at {closest['locName']}")
else:
    print("No recent sightings of that species nearby.")
```

This will give the closest Snowy Owl in the past 30 days around Ithaca, NY. For example, it might print: **“Nearest Snowy Owl was seen on 2025-02-14 17:00 at Montezuma NWR–Knox-Marsellus Marsh”**. If multiple records come back, you can check the next ones for second-closest, etc. Under the hood, the query looked out to 50 km by default (since we didn’t specify `dist`), but you could constrain it (e.g. `&dist=20`). This endpoint effectively does the work of filtering and sorting by distance for you.

**Note:** The `dist` parameter was introduced in the 2.0 API (older versions had a fixed radius). Now you can ensure you don’t get results beyond a certain range if you want. According to eBird, if you specify a dist > 50 it will be treated as 50 km. The default `maxResults` of 3000 is usually plenty – that would be if the species was extremely common everywhere in the radius. Also note that if the species is not found at all in the radius, the response is simply `[]` (empty list).

### Recent Nearby Notable Observations (`GET /data/obs/geo/recent/notable?lat={lat}&lng={lng}`)

**What it does:** Combines the “nearby” and “notable” concepts – it returns recent **notable (rare) bird observations** within a given radius of a point. Essentially, “are there any rare birds near me?”. It works like the general nearby endpoint but filters to only show species that eBird flags as unusual for the area/season.

**Required query parameters:** `lat` and `lng` (the central coordinates).

**Optional query parameters:**

- `back` (1–30, default 14): Days back for sightings.
    
- `detail` (`simple` or `full`, default `simple`): Level of detail for the output. If `full`, the observation records will include additional fields like observer name, etc. (similar to notable in region).
    
- `dist` (0–50 km, default 25): Search radius.
    
- `hotspot` (true/false, default false): Only hotspots if true.
    
- `lat`/`lng` (required, as above).
    
- `maxResults` (1–10000, no default): Limit number of records.
    
- `sppLocale` (locale for names).
    

The meaning of these is identical to the earlier “recent notable in region” and “nearby” parameters combined.

**Returns:** A JSON array of observation records for notable sightings within the radius. If `detail=simple`, each record has basic fields (speciesCode, comName, locName, obsDt, etc.). If `detail=full`, it will include the extended fields like country/state codes, observer name, etc.. For example, you might find an entry: `"comName": "Pink-footed Goose", "obsDt": "2025-01-10 14:00", "locName": "Some Lake (AZ)", "lat":..., "lng":..., "obsValid": false, "obsReviewed": false, "userDisplayName": "John Doe", ...`. The `obsValid:false` and `obsReviewed:false` often indicate a rare (unconfirmed) report that’s pending review – common in notable sightings data.

One important note: The **list is not explicitly sorted** by either date or distance. You may want to sort the results client-side. Often, you’ll want to sort by distance (to know which rare bird is closest). The API does not return the distance, but since you have lat/lng for each record, you could compute it, or you could make multiple smaller radius calls if needed.

**Use cases:** Perfect for implementing a **local rare bird alert map or list**. A birder could open your app, hit “Rare birds around me”, and see a list or pins of all species considered rare in their vicinity recently. It’s a specialized but popular feature. It can also feed into a notification system – e.g. if a new rare bird appears within X km of the user’s saved locations, alert them.

**Example – Rare birds around a location:**

```python
lat, lng = 40.7128, -74.0060  # New York City coordinates
url = f"https://api.ebird.org/v2/data/obs/geo/recent/notable?lat={lat}&lng={lng}&dist=10&detail=full"
resp = requests.get(url, headers={"X-eBirdApiToken": api_token})
notable_nearby = resp.json()
for obs in notable_nearby:
    species = obs["comName"]
    place = obs["locName"]
    date = obs["obsDt"]
    observer = obs.get("userDisplayName", "")
    print(f"* {species} at {place} on {date}" + (f" (reported by {observer})" if observer else ""))
```

This might output, for instance:

- _Barnacle Goose at Central Park Reservoir on 2025-03-15 09:20 (reported by Alice Smith)_
    
- _Painted Bunting at Staten Island–Clove Lakes Park on 2025-03-10 07:45 (reported by John Doe)_
    

Each line is a notable sighting within 10 km of NYC. From this data, you might hyperlink the location names to maps, or the species names to info pages. Since we requested `detail=full`, we were able to include the reporter’s name in parentheses (if available). If no notable birds are around, the list will be empty.

### Recent Checklists Feed (`GET /product/lists/{regionCode}`)

**What it does:** Provides the most recent eBird **checklists** submitted in the given region. A “checklist” in eBird is a complete submission by an observer at a place and time, potentially containing many species. This endpoint returns a feed of checklists (not individual observations) sorted by submission time, with the newest first. Essentially, it’s a real-time feed of birding activity in the region.

**Important:** Although this is conceptually observational data, note that the endpoint is under the `product` category (the path includes `/product/lists/`). It is separate from the `data/obs` endpoints because it returns checklists rather than individual observation records.

**Required path parameter:**

- `regionCode` – The region of interest (country, subnational1, subnational2, or a hotspot/location ID). It accepts the same codes as observation endpoints for regions.
    

**Optional query parameters:**

- `maxResults` (1–200, default 10): The number of recent checklists to fetch. You can get up to 200 most recent checklists in that region. If you omit this, it will return 10 by default.
    

This endpoint does not take `back` or date parameters – it always returns the latest checklists up to the maxResults count.

**Returns:** A JSON array of **checklist entries**. Each entry represents one checklist submission. The fields of a checklist entry include:

- `userDisplayName` (name or username of the observer who submitted the list),
    
- `subId` (the checklist ID, e.g. "S12345678"),
    
- `subId` may sometimes also appear as `checklistId`,
    
- `locId` and `locName` (where the checklist was made),
    
- `obsDt` (date/time of the checklist),
    
- `numSpecies` (number of species reported on that checklist),
    
- possibly `subnational1Code`, `subnational2Code`, etc. for the location’s region codes,
    
- `latitude`, `longitude` of the location,
    
- `hasRichMedia` (true if the checklist has photos/audio attached),
    
- etc.
    

Basically, it’s a summary of each checklist. For example, one element might look like:

```json
{
  "subId": "S162345678",
  "userDisplayName": "Jane Birder",
  "locId": "L123456",
  "locName": "Central Park",
  "obsDt": "2025-06-12 07:15",
  "numSpecies": 23,
  "lat": 40.78,
  "lng": -73.96,
  "subnational1Code": "US-NY",
  "subnational2Code": "US-NY-061",
  "countryCode": "US",
  "hasRichMedia": true
}
```

This indicates Jane Birder submitted a checklist at Central Park on June 12, 2025 at 7:15 AM with 23 species, and it had photos/audio. (This is an illustrative example – actual field names might slightly vary, e.g. some fields might be lowercase like `lat` and `lng`.)

**Use cases:** This endpoint is ideal for a **“recent checklists” or activity feed** feature. For instance, on a birding club’s website, one might show “Latest checklists in [Your County]” so people can see what others are reporting in near-real-time. It’s also useful if you want to count how many checklists have been submitted today or to list the most active hotspots (by seeing repeated locNames). If building an app, you could poll this periodically to get new checklists as they come in. Keep in mind the max of 200 – if the region is very active, you might consider using smaller regions (e.g., a single hotspot) or using the date-specific feed (next endpoint) to page through.

**Example – Fetch recent checklists in a region:**

```python
region = "US-AZ-YU"  # Yuma County, Arizona (subnational2 code)
url = f"https://api.ebird.org/v2/product/lists/{region}?maxResults=5"
resp = requests.get(url, headers={"X-eBirdApiToken": api_token})
checklists = resp.json()
for cl in checklists:
    print(f"{cl['obsDt']} – {cl['locName']} – {cl['numSpecies']} species by {cl['userDisplayName']}")
```

Output might be:

```
2025-06-12 18:05 – Cibola NWR–Unit 1 – 42 species by Alice B.  
2025-06-12 17:50 – Yuma West Wetlands – 17 species by Bob C.  
2025-06-12 17:30 – Yuma West Wetlands – 5 species by Bob C.  
2025-06-12 17:20 – Cocopah RV Resort – 8 species by Carol D.  
2025-06-12 16:45 – Yuma West Wetlands – 33 species by Dan E.
```

This shows the five most recent checklists in Yuma County, AZ, with timestamp, location, species count, and observer. We can see Bob C. submitted two back-to-back lists at Yuma West Wetlands, etc. You could use the `subId` to link to the full checklist (see “View Checklist” endpoint below). If you wanted more than 5, adjust `maxResults`. Note that this is real-time data; if you run it again later, you’ll see new checklists as birders submit them.

### Historic Observations on a Date (`GET /data/obs/{regionCode}/historic/{year}/{month}/{day}`)

**What it does:** Retrieves **all observations on a specific date** in a given region. In other words, it’s a full list of species (and counts, etc.) reported for that region on that date. This can be considered a “historical day list” for the region. It’s different from recent endpoints because it can return multiple observations per species if they were reported by different checklists, or the same species at different locations on that date. You can control whether you get just one per species or all records via the `rank` parameter.

**Required path parameters:**

- `regionCode` – Region of interest (country, state, county, or locId). **Note:** In practice, this endpoint is most commonly used for regional summaries (e.g., a county or state on a given day).
    
- `year`, `month`, `day` – The date you want data for. Year is four digits (>= 1800 up to current year), month 1–12, day 1–31 (as appropriate for the month).
    

**Optional query parameters:**

- `cat` (category filter, default all): Taxonomic category filter, like in other obs endpoints. You could set `cat=species` to exclude subspecies, etc.
    
- `detail` (`simple` or `full`, default `simple`): Level of detail for the response. `full` will include extra fields (e.g., observer info).
    
- `hotspot` (true/false, default false): If true, only include observations from hotspots.
    
- `includeProvisional` (true/false, default false): If true, include unconfirmed sightings.
    
- `maxResults` (1–10000, default all): Limit number of observations returned. If you only want the first N records.
    
- `rank` (`"mrec"` or `"create"`, default `"mrec"`): This determines which observation to return _if multiple observations of the same species exist_ on that date.
    
    - If `rank=mrec` (most recent), you’ll get the **latest** observation of each species on that date (so essentially one record per species, being the last one of the day).
        
    - If `rank=create`, you’ll get the **first** observation of each species that was added on that date (earliest sighting per species).
        
    - If you want **all observations** (potentially multiple per species), you can supply an `r` parameter instead (see next).
        
- `r` (up to 50 location codes, optional): Fetch observations from specific locations on that date. If you supply this, you should set `regionCode` in the path to empty (similar to earlier pattern). Essentially this lets you get multiple specific locations’ data in one call (up to 50). If you _don’t_ supply `r`, the data returned covers the whole region in the path.
    
- `sppLocale` (locale for common names, default "en").
    

**Notes:** By default (`rank=mrec`), this endpoint returns one observation per species (the latest on that date). If you want **every single sighting record** on that date, one trick is to use a dummy subregion: for example, if you want all observations in a county on Jan 1, you could list all hotspots and personal locations in that county as the `r` parameter (but that requires you have those loc IDs, which is not trivial). Generally, the intent is either summary per species or to query specific known locations.

The response for this endpoint **may be cached for 30 minutes on the server** – meaning if you query the same date/region repeatedly, you might get a cached result (to reduce server load).

**Returns:** A JSON array of observation records from that date and region. The structure of each record is the same as earlier observation records, with possibly additional fields if `detail=full`. If `rank=mrec` or `create`, you’ll get at most one entry per species. If multiple records per species are allowed (by using `r` to specify locations), then you could have repeats of species (from different checklists or sites). Each record includes a `subId` (checklist ID) which is crucial if you need to reference the specific checklist the observation came from. In full detail, you also get observer name fields, etc., which might be useful for something like a Big Day report.

**Use cases:** The primary use is for generating **“daily summary” reports**. For example, on eBird’s website, there is a “Historic Bar Chart” or “Notable observations on this day in history” – this endpoint is what powers the display of what was seen on a particular date. A practical use case: if you are organizing a **Big Day event**, you could use this to get a list of all species seen in your region on that day for scoreboard purposes. Or if a user wants to see what a birding trip yielded in terms of species for a given date in a county, this provides that. It’s also useful for pulling out the **first and last sightings** of each species on that day if you use the `rank` parameter creatively (e.g., to see what species started the day and ended the day).

**Example – Get all species reported on a given date:**

```python
region = "US-IL-031"  # Cook County, Illinois
date = (2025, 5, 14)   # May 14, 2025
url = f"https://api.ebird.org/v2/data/obs/{region}/historic/{date[0]}/{date[1]}/{date[2]}?rank=mrec"
resp = requests.get(url, headers={"X-eBirdApiToken": api_token})
day_obs = resp.json()
print(f"Species seen in {region} on {date}: {len(day_obs)}")
# Print first 5 species
for obs in day_obs[:5]:
    print(obs["comName"], "-", obs["howMany"] if obs.get("howMany") else "X", "seen at", obs["locName"])
```

If, say, 180 species were reported in Cook County on May 14, 2025, it will output “Species seen in US-IL-031 on (2025, 5, 14): 180”. Then a few species lines like:

- Canada Goose – 34 seen at Lincoln Park
    
- Mallard – X seen at Lincoln Park
    
- Mourning Dove – 5 seen at Jackson Park
    
- ...
    

Here “X” means the observer reported the species but didn’t provide a precise count (X is eBird’s shorthand for present). Each record corresponds to the last report of that species on that date in that county (because we used rank=mrec). If we wanted the first report per species, we could use `rank=create`. If we wanted absolutely every record (say every checklist’s entry), we would need to gather them differently (not directly possible with one call unless listing locations in `r`). The above is a summary useful for checking total species. We could also filter the result to only `obsReviewed=false` to see which were unconfirmed.

---

Now that we’ve covered all the observation data endpoints, let’s move on to the **“product”** endpoints which provide leaderboards and summaries, then reference endpoints for hotspots, taxonomy, and regions.

## “Product” Endpoints (Top 100, Checklists, Stats, etc.)

The “product” endpoints are so called because they correspond to various summary pages on the eBird website (Top 100 rankings, recent checklists, etc.). These are high-level data products that eBird provides, which can be very useful in apps. The product endpoints typically require an API key as well. They often involve date-specific queries or return composite information.

### Top 100 (Top eBirders) on a Date (`GET /product/top100/{regionCode}/{year}/{month}/{day}`)

**What it does:** Returns the **Top 100 eBird contributors** (users) for the given region and date. In other words, it’s a leaderboard of who saw the most birds on that date in that region. eBird’s website often shows this for big days or any given day historically. By default, the ranking is by number of species seen, but you can also rank by number of checklists via a parameter.

**Required path parameters:**

- `regionCode` – Region of interest (country, subnational1, or subnational2 – typically you’d use a larger region like a country or state, but smaller regions work if enough data).
    
- `year`, `month`, `day` – The date of interest.
    

**Optional query parameters:**

- `rankedBy` (string, values likely `"species"` or `"checklists"`, default is `"species"`): Determines whether to rank users by species count or checklist count. If you choose species, the person with most species on that date is #1. If by checklists, the person with the most checklists gets top spot. (If two users have equal numbers, there may be ties or some internal ordering).
    
- `maxResults` (1–100, default 100): How many results to return. The default (and max allowed) is 100, since it’s the “Top 100”. You could set a smaller number if you only want the top 10, for example.
    

**Returns:** A JSON array of up to `maxResults` entries, each representing one eBird user’s total for that day. Each entry (let’s call it a **Top100ListEntry**) includes fields such as:

- `userId` or some user identifier (often eBird uses an encoded user ID),
    
- `userDisplayName` (the birder’s name or username),
    
- `numSpecies` (number of species they reported in that region on that date),
    
- `numChecklists` (number of checklists they submitted that day for that region),
    
- Possibly `rank` (1 through maxResults),
    
- Possibly `profileUrl` or similar (if eBird provided a link, though likely not directly here).
    

For example, an entry might look like:

```json
{ "userDisplayName": "John Doe", "numSpecies": 135, "numChecklists": 5 }
```

if John Doe saw 135 species on that date with 5 checklists, and that was the top result.

If `rankedBy=checklists`, then presumably the list is sorted by `numChecklists` and you’d likely look at that field instead.

**Use cases:** This is used for things like **birding competitions or events**. For example, during a global big day, you might use this endpoint to show the top birders in each state or country for that day. It could also be fun in an app to show a user how they ranked on a given day in their area. Researchers might use it to identify who were the major contributors of data on a certain day. Essentially it is a gamified statistic.

**Example – Top 10 birders in a region on a date (by species):**

```python
region = "US-TX"  # Texas
date = (2025, 4, 25)
url = f"https://api.ebird.org/v2/product/top100/{region}/{date[0]}/{date[1]}/{date[2]}?rankedBy=species&maxResults=10"
resp = requests.get(url, headers={"X-eBirdApiToken": api_token})
leaderboard = resp.json()
for rank, entry in enumerate(leaderboard, start=1):
    print(f"{rank}. {entry['userDisplayName']} - {entry['numSpecies']} species")
```

This would list the top 10 eBirders in Texas on April 25, 2025 by species count. For example, output might be:

```
1. Alice Smith – 189 species  
2. Bob Jones – 175 species  
3. Carlos Diaz – 162 species  
...  
4. Jane Doe – 140 species
```

Each of those lines corresponds to an entry from the JSON. If we had used `rankedBy=checklists`, we would instead interpret `entry['numChecklists']` for ranking (and perhaps include that in the printout). Note that the API presumably already sorted the entries correctly. We used `enumerate(start=1)` because the data might not explicitly include the rank number (though it’s inherently ordered).

### Checklist Feed on a Date (`GET /product/lists/{regionCode}/{year}/{month}/{day}`)

**What it does:** Retrieves **all checklists submitted on a specific date** in the given region. This is basically a dated version of the “recent checklists feed” but for a specific historical or current date. It returns the list of checklists (with their metadata) for that day, region-wide. It is similar to the "Historic observations on a date" endpoint, but at the checklist level rather than species observation level.

**Required path parameters:**

- `regionCode` – Region of interest (country, state, county, etc. as usual).
    
- `year`, `month`, `day` – The date of interest.
    

**Optional query parameters:**

- `sortKey` (likely values `"obsDt"` or `"subId"` or `"taxonomic"` perhaps; default might be by time): This parameter is indicated by Hackage as `sortKey`. The documentation suggests it can sort the checklists by certain keys. The likely options are sorting by checklist start time or maybe by some other attribute. On the eBird website, checklists of a day can be sorted by location or submission time. However, the exact allowed values are not explicitly given in our sources. We can assume the default sort is chronological by submission time (most likely).
    
- `maxResults` (1–any, but practically maybe all checklists, default maybe none i.e. return all): The Hackage snippet shows a `maxResults` for this endpoint, similar to others. Possibly you can limit how many checklists to return if the day had many.
    

Unlike the undated feed, here you specify a date so essentially you're paginating by date rather than by a count.

**Returns:** A JSON array of **checklist entries** (similar structure to the recent checklists feed described earlier), but covering that entire date. Each entry includes checklist ID, observer name, location, date/time, number of species, etc. Because it’s for a specific date, all `obsDt` fields will share that date (differing in time of day). If more than one checklist was submitted by the same observer at the same location and time, those would be separate entries (they might have different subId). Typically, this list can be long (on a big day in a bird-rich area, hundreds of checklists could be submitted). If `maxResults` is not set or is large, you’ll get all of them. Use caution if you request a very active region on a busy date, as the JSON could be quite large (though still probably manageable, since it’s just checklist headers).

**Use cases:** This can be used for a **“daily feed” archive**. For example, if building a tool to analyze effort or participation on a certain day, you can fetch all checklists and then compute stats like total participants, total effort hours (though effort hours are not directly given, you could approximate by number of checklists). Another use is a timeline: maybe you want to display all checklists from a certain event date. It’s also a way to programmatically gather all checklist IDs for a region-date combination, which you could then feed into the “View Checklist” endpoint to get complete details of each (though that could be a lot of calls if there are many checklists).

**Example – List checklists in a region on a date:**

```python
region = "CA-BC-GV"  # Greater Vancouver, British Columbia (just an example region code)
date = (2024, 12, 25)  # Christmas 2024
url = f"https://api.ebird.org/v2/product/lists/{region}/{date[0]}/{date[1]}/{date[2]}?maxResults=5"
resp = requests.get(url, headers={"X-eBirdApiToken": api_token})
checklists = resp.json()
for cl in checklists:
    print(f"{cl['obsDt']} - {cl['locName']} - {cl['numSpecies']} species - by {cl['userDisplayName']}")
```

Output might look like:

```
2024-12-25 16:45 - Stanley Park - 12 species - by Bob Bird  
2024-12-25 15:30 - Reifel Bird Sanctuary - 34 species - by Alice Birder  
2024-12-25 14:10 - Queen Elizabeth Park - 8 species - by Carol C.  
2024-12-25 13:00 - Stanley Park - 20 species - by Derek D.  
2024-12-25 12:05 - Burnaby Lake - 18 species - by Evan E.  
```

These are 5 checklists from Christmas Day 2024 in Greater Vancouver. They’re ordered by time (likely latest first in this example). One can see two from Stanley Park at different times. If we had requested all, we’d see all checklists from that day. This could feed into a visualization of birding activity throughout the day, or simply an archive to browse historical data.

### Regional Statistics on a Date (`GET /product/stats/{regionCode}/{year}/{month}/{day}`)

**What it does:** Provides summary **statistics for all checklists on a given date in a region**. This typically includes totals like the number of species reported, number of checklists submitted, and perhaps number of observers, for that region and date. Essentially, it aggregates the day’s activity into a single report. It’s analogous to a “day summary” – e.g. “On 2025-05-05, in Region X, Y species were reported across Z checklists by N observers.”

**Required path parameters:**

- `regionCode` – The region of interest.
    
- `year`, `month`, `day` – The date.
    

**Query parameters:** None documented explicitly for filtering (the Hackage interface shows no query params besides the path). So it’s a straight lookup of that date and region.

**Returns:** A JSON object (not an array) representing the regional stats for that day. Let’s call the structure **RegionalStatistics**. From the nature of the data, likely fields include:

- `numSpecies` (total distinct species reported in that region on that date),
    
- `numChecklists` (total number of checklists submitted),
    
- `numObservers` (distinct eBird users who submitted checklists),
    
- Possibly `numLocations` (distinct locations birded),
    
- Possibly `allObs` or similar (total number of observations, though that is similar to checklists count times average species per list, not as commonly reported),
    
- Possibly `speciesList` (maybe a list of species codes or count of species – but since numSpecies is given, not sure if they include the list; likely not here),
    
- Possibly a breakdown like `highCount` if they include a highlight (though probably not – just raw totals).
    

The eBird website’s “regional statistics” page (for a Date) typically shows how many species and how many checklists were logged for that area and date. For example: _“On 1 Jan 2023 in New York State, 120 species were reported across 250 checklists by 180 observers.”_

The API likely returns an object with keys like `"numSpeciesAllTime"` or similar as well, but given this is date-specific, it likely focuses on that date.

Since our direct sources don’t list the keys, we infer from context:  
The Hackage code indicates this returns a type `RegionalStatistics`, which suggests a single object.

**Use cases:** This is useful for summary displays or analytics. For example, during a birding event (like a Christmas Bird Count day or a Global Big Day), you can use this to quickly fetch how the day went in terms of numbers. An app might use it to show a quick “Yesterday in this region: X species, Y checklists”. It can also be used to compare regions or track participation over time by querying multiple dates. For a researcher, this provides a quick measure of birding activity intensity on any given day and place.

**Example – Get stats for a region on a date:**

```python
region = "GB-ENG"  # England (just an example region code)
date = (2023, 5, 13)  # May 13, 2023
url = f"https://api.ebird.org/v2/product/stats/{region}/{date[0]}/{date[1]}/{date[2]}"
resp = requests.get(url, headers={"X-eBirdApiToken": api_token})
stats = resp.json()
print(f"{stats['numSpecies']} species reported on {date} in {region}, "
      f"from {stats['numChecklists']} checklists by {stats['numObservers']} observers.")
```

If, say, on 13 May 2023 in England there were 210 species, 500 checklists, and 300 observers, the output would be: **“210 species reported on (2023, 5, 13) in GB-ENG, from 500 checklists by 300 observers.”** This matches what the eBird site might show as summary for that region and date.

Keep in mind region could be as large as a country or as small as a county. If the region is very small (like a single hotspot), `numObservers` might effectively equal number of checklists (since usually one checklist per observer per location/time), but in a big region many checklists can come from the same person or vice versa.

### Species List for a Region (`GET /product/spplist/{regionCode}`)

**What it does:** Returns the **complete list of species ever reported** in the given region. Essentially, it’s the avifaunal list for that region, according to eBird data. This is an all-time species list, not time-bound (except that it’s based on eBird observations, so if a species was never reported, it won’t be included). It’s analogous to going to eBird’s “Explore Species” for a region and retrieving the checklist of all species seen there.

**Required path parameter:**

- `regionCode` – The region of interest (country, subnational1, subnational2, or a hotspot/location).
    

**Optional parameters:** None (no query params in this endpoint).

**Returns:** The documentation suggests it returns an array of species codes, i.e., essentially a list of species identified by their codes. The Hackage definition shows it as `Get [JSON] [SpeciesCode]`, meaning the JSON is likely an array of species code strings. However, it’s possible the API might return more info like common names as well. But likely it’s just codes to keep it light (since you can map codes to names via taxonomy if needed).

If it is just species codes, an example return for a region might be:

```json
["mallar3", "gadwal", "norshov", "eurwig", ... ]
```

a list of codes for Mallard, Gadwall, Northern Shoveler, Eurasian Wigeon, etc., if those are present.

We should note: in older API, region species list used locIDs. In v2, they allow any regionCode (the changelog mentioned this change). So you can use it for a hotspot (`Lxxxx`) or a whole country (`US`). For a large region, the list could be quite long (e.g., US might return 1000+ species codes).

**Use cases:** This is extremely useful for populating checklists or guides in an app. For instance, if a user is about to go birding in a certain county, you can use this to show them all species ever seen in that county (a regional checklist) to know what to expect. Conservationists might use it to see species diversity of an area. It’s basically the backbone for any feature that needs a **bird list for a region** – which could be used to filter search results, to generate regional bird bingo cards, etc.

Since the response might be just codes, you might want to then translate codes to common names. To do that, you could either call the taxonomy endpoint to get names for all codes, or use the `locale` parameter in taxonomy to get common names in a desired language. Alternatively, you might maintain a local mapping of speciesCode to names (perhaps by downloading the taxonomy once and using it offline).

**Example – Get species list for a region:**

```python
region = "KE"  # Kenya country code
url = f"https://api.ebird.org/v2/product/spplist/{region}"
resp = requests.get(url, headers={"X-eBirdApiToken": api_token})
species_codes = resp.json()
print(f"{len(species_codes)} species have been reported in {region}.")
# Print first 10 species names using taxonomy for demonstration
tax_url = "https://api.ebird.org/v2/ref/taxonomy/ebird?species=" + ",".join(species_codes[:10])
tax_resp = requests.get(tax_url, headers={"X-eBirdApiToken": api_token})
tax_info = tax_resp.json()
for species in tax_info:
    print(species["comName"])
```

First, we get the list of species codes for Kenya. Suppose it prints “**1080 species have been reported in KE.**”. Then we take the first 10 codes and query the taxonomy endpoint with them (using the `species` query parameter to filter taxonomy). The taxonomy response will include common names and scientific names for those species. We print the common names. This might output some of the birds of Kenya, e.g.:

```
Ostrich, Common  
Grebe, Little  
Swift, African Palm-  
... 
```

This demonstrates how to map the species codes to actual names. In a real application, you might cache the taxonomy or at least the relevant portion to avoid making an extra call for each species. Alternatively, if you want only common names in a certain language, eBird suggests using the taxonomy call with `locale` or the alternate locale list endpoint.

**Important:** As of an update in 2020, `spplist` accepts any region code (previously it required a locId), which makes it much more flexible. So feel free to use it on states, countries, etc.

### View Checklist (`GET /product/checklist/view/{subId}`)

**What it does:** Retrieves the **detailed content of a single checklist** by its submission ID. This returns all observations (species) on that checklist along with checklist-level information. Essentially, it’s like viewing an eBird checklist in JSON form.

**Required path parameter:**

- `subId` – The checklist ID. These IDs start with “S” followed by numbers (e.g. S12345678). You would typically get this ID from other endpoints (like the recent checklists feed or historic observations data, which includes `subId` for each observation or checklist).
    

**Optional parameters:** None.

**Returns:** A JSON object containing the checklist details. Let’s break down what to expect:

- **Checklist metadata:** This includes things like the checklist’s `subId`, the location (`locId`, `locName`), the date/time (`obsDt`), the observer (`userDisplayName` and possibly user ID), and effort info if available (e.g. protocol type, duration, distance, number of observers, etc.). It may also include flags like whether the checklist is complete.
    
- **Observations list:** Within the checklist object, there will be a list (array) of species observations that were part of that checklist. Each observation entry likely has:
    
    - `speciesCode`, `comName`, `sciName` for the species,
        
    - `howMany` (the count recorded, or null if X),
        
    - `obsDt` (the date/time which might be the same for all since the whole checklist has one time),
        
    - `obsValid`, `obsReviewed` (usually true and either true/false depending on review status),
        
    - Possibly a `speciesComments` if the observer added a note for that species,
        
    - `hasRichMedia` if photos/sounds attached for that species,
        
    - etc.
        
- **Checklist comments:** If the observer wrote any general comments for the checklist, those might appear as well.
    

It essentially merges what you’d see on the eBird checklist page: list of species with counts and any remarks, plus top-of-page info like location, date, observers, and effort.

Because the format might be nested (the doc description just says “details and observations for a checklist”), the JSON might have a structure like:

```json
{
  "subId": "S12345678",
  "userDisplayName": "John Doe",
  "obsDt": "2025-06-12 07:15",
  "locId": "L123456",
  "locName": "Central Park",
  "subnational1Code": "US-NY",
  "numObservers": 1,
  "durationHrs": 2.5,
  "allObsReported": true,
  "obs": [
      {"speciesCode": "norcar", "comName": "Northern Cardinal", "howMany": 2, "obsDt": "2025-06-12 07:15", "obsValid": true, "hasRichMedia": false, "speciesComments": "pair at feeder"},
      {"speciesCode": "dowood", "comName": "Downy Woodpecker", "howMany": 1, "obsDt": "2025-06-12 07:15", "obsValid": true, "hasRichMedia": true},
      ...
  ],
  "comments": "Sunny morning, lots of activity."
}
```

_(Note: this structure is an educated guess for illustration. The actual field names could differ slightly.)_

With that data, you have a full accounting of the checklist. For example, you can see John Doe saw 2 Northern Cardinals and 1 Downy Woodpecker, etc., and he left a comment, plus one of the observations had rich media (photo/audio).

**Use cases:** This endpoint is useful if you want to drill down to exact details after using other endpoints. For instance, if your app shows a list of recent checklists (from earlier feed), you can allow the user to tap one and then call this to show all species on that checklist. It’s also handy for data analysis if you want to extract species co-occurrence or effort info from specific checklists. Keep in mind that you should have the `subId` beforehand (from feeds or from an eBird URL or data export).

**Example – Fetch and display a checklist:**

```python
subID = "S98765432"
url = f"https://api.ebird.org/v2/product/checklist/view/{subID}"
resp = requests.get(url, headers={"X-eBirdApiToken": api_token})
checklist = resp.json()
print(f"Checklist {checklist['subId']} by {checklist['userDisplayName']} at {checklist['locName']} on {checklist['obsDt']}")
print(f"Species observed ({len(checklist['obs'])}):")
for obs in checklist['obs']:
    count = obs['howMany'] if obs.get('howMany') is not None else 'X'
    print(f" - {obs['comName']} ({count})")
```

Output:

```
Checklist S98765432 by Jane Doe at Central Park on 2025-05-10 07:20
Species observed (5):
 - Mallard (4)
 - Mourning Dove (X)
 - Downy Woodpecker (1)
 - Blue Jay (2)
 - Northern Cardinal (1)
```

This indicates Jane’s checklist at Central Park on May 10, 2025 had 5 species. Mourning Dove had an ‘X’ (present, count not given). The others have counts. We could also check if `checklist.get('comments')` exists to print general comments, or look at `obsReviewed` flags to see if anything was flagged, etc. Also, `hasRichMedia` could tell us if any species had photos; we might use that to show an icon in the UI.

For a real application, you might combine this with the **media API** (not covered here since the question is about eBird’s main API) if you wanted to retrieve the actual photos or sounds. But that’s beyond our scope and often requires a separate approach (eBird media is usually accessed via the checklist’s webpage or external links).

---

## Hotspot Endpoints (Hotspot Reference Data)

The following endpoints under `ref/hotspot` give information about eBird hotspots – which are public birding locations shared by the community. These are typically used to populate maps or dropdowns of hotspots in a region, find nearby hotspots, and get details about specific hotspots.

**Important note on format:** The hotspot endpoints have a quirk: they can return CSV by default if not specified, which is unusual since most others default to JSON. To ensure JSON format, always include the query param `fmt=json` on these requests (or ensure the Accept header asks for JSON). We will include `fmt=json` in our examples to be safe.

### Hotspots in a Region (`GET /ref/hotspot/{regionCode}`)

**What it does:** Returns the list of all eBird **hotspots within a specified region**. The region can be a country, subnational1 (state/province), or subnational2 (county). You can also specify a smaller region like a city if eBird had a code, but typically these codes are at country/state/county level. It will **not** include personal locations, only hotspots (shared locations marked with a hotspot ID).

**Required path parameter:**

- `regionCode` – Region in standard eBird code format (e.g. `US-NY-109` for a county, `AU-QLD` for Queensland, etc.).
    

**Optional query parameters:**

- `back` (integer, default perhaps 0 or none): The documentation snippet shows a `back` parameter for this endpoint. Likely this `back` means “include hotspots that have had observations in the last X days only.” If provided, it might filter out inactive hotspots (ones with no recent observations within that many days).
    
- `fmt` (`"json"` or `"csv"`, default CSV): As mentioned, by default the API might return CSV. By adding `fmt=json`, you ensure the output is JSON format.
    

**Returns:** A JSON array of **Hotspot** objects (or if CSV, it would be rows). Each hotspot object includes:

- `locId` – the hotspot’s location ID (starts with "L", e.g. L123456),
    
- `locName` – the name of the hotspot,
    
- `latitude` (`lat`) and `longitude` (`lng`),
    
- `latestObsDt` – the date of the most recent observation at that hotspot (this field appears in some contexts),
    
- `numSpeciesAllTime` – number of species ever reported from that hotspot,
    
- Possibly `subnational2Code`, `subnational1Code`, `countryCode` for its location context.
    

For example, one entry might be:

```json
{
  "locId": "L123456",
  "locName": "Central Park",
  "lat": 40.782,
  "lng": -73.965,
  "latestObsDt": "2025-06-10",
  "numSpeciesAllTime": 201
}
```

Meaning Central Park hotspot has 201 species reported all-time and the latest observation was on June 10, 2025.

If you don’t include `fmt=json`, the default CSV would list these in comma-separated form. But using JSON is easier for a developer.

**Use cases:** Use this to populate a list or map of hotspots for users to choose from. For instance, if your app lets the user pick a birding location, you can call this for their county or state to get all known hotspots. You can also use `numSpeciesAllTime` to sort or highlight popular hotspots (a high number suggests a well-birded spot). The `latestObsDt` can indicate if a hotspot is active recently. If `back` parameter is used (say `back=30`), you’d only get hotspots that had at least one checklist in the last month – useful if you want to ignore spots that haven’t been birded in a long time.

**Example – List hotspots in a county:**

```python
region = "US-AZ-007"  # Gila County, Arizona (just an example county code)
url = f"https://api.ebird.org/v2/ref/hotspot/{region}?fmt=json"
resp = requests.get(url, headers={"X-eBirdApiToken": api_token})
hotspots = resp.json()
print(f"{len(hotspots)} hotspots in {region}:")
for ht in hotspots[:5]:
    print(f" - {ht['locName']} (ID: {ht['locId']}, {ht['numSpeciesAllTime']} species all-time)")
```

Output might be:

```
12 hotspots in US-AZ-007:
 - Tonto Creek Fish Hatchery (ID: L123445, 150 species all-time)
 - Jake's Corner (ID: L543210, 89 species all-time)
 - Greenview Park (ID: L678901, 45 species all-time)
 - Flowing Springs (ID: L112233, 92 species all-time)
 - Payson Wastewater Treatment Plant (ID: L998877, 110 species all-time)
```

And so on (listing only first 5 for brevity). This tells us there are 12 hotspots in that county, with their IDs and species counts. One could use the coordinates from each to plot them on a map. If we were only interested in currently active ones, we could add e.g. `?back=30` to only include those with observations in the past 30 days – those might have `latestObsDt` within that range.

### Nearby Hotspots (`GET /ref/hotspot/geo?lat={lat}&lng={lng}`)

**What it does:** Returns hotspots **within a radius of a given lat/long**. This allows you to find the nearest hotspots to a user’s location or any point of interest.

**Required query parameters:**

- `lat`, `lng` – Coordinates of the center point (same format and rules as in observation endpoints: -90 to 90 for lat, -180 to 180 for lng, use two decimal places ideally).
    

**Optional query parameters:**

- `back` (days, default maybe none): Similar to region hotspots, this likely filters to hotspots active in last X days if provided.
    
- `dist` (km, default 25): The search radius in kilometers. If not given, it might default to 25 km. Max could be 50 km (often eBird uses 50 as an upper bound for nearby searches).
    
- `fmt` (`json`/`csv`, default CSV): Set `fmt=json` to get JSON output.
    

**Returns:** A JSON array of hotspot objects, in a similar format to the previous endpoint (locId, locName, lat, lng, latestObsDt, numSpeciesAllTime). In addition, since these are specifically location-based, the output **might be sorted by distance** from the given point (not explicitly stated, but it’s likely—they typically return closest first). However, because the default response is CSV if not specified, the ordering might indeed be by distance in that CSV. In JSON, we should assume the order is by increasing distance unless we verify otherwise.

For example, the first entry in the list would be the closest hotspot. Each entry is like:

```json
{
  "locId": "L271112",
  "locName": "City Park Pond",
  "lat": 34.123,
  "lng": -118.456,
  "latestObsDt": "2025-06-11",
  "numSpeciesAllTime": 80
}
```

You won’t get the distance in kilometers in the response, so if you need to display how far it is, you’d have to calculate based on lat/lng.

**Use cases:** When a user wants to find good birding spots nearby, use this. For instance, an app could have a “Find Nearby Hotspots” button that shows the closest hotspots within, say, 20 km. You could also combine it with the observation endpoints: e.g., first get nearby hotspots, then for each, fetch recent observations at that hotspot (by using its locId in the observations endpoints – which is possible via the `regionCode` being a locId). This way you can show not just where the hotspots are, but what’s been seen there lately.

**Example – Nearest hotspots to a location:**

```python
lat, lng = 47.60, -122.33  # Seattle, WA
url = f"https://api.ebird.org/v2/ref/hotspot/geo?lat={lat}&lng={lng}&dist=10&fmt=json"
resp = requests.get(url, headers={"X-eBirdApiToken": api_token})
hotspots = resp.json()
print("Closest hotspots:")
for ht in hotspots[:5]:
    # You might compute distance here if needed
    print(f" {ht['locName']} (ID {ht['locId']}, {ht['numSpeciesAllTime']} species)")
```

Possible output:

```
Closest hotspots:
 Discovery Park (ID L123456, 230 species)
 Union Bay Natural Area (ID L234567, 210 species)
 Magnuson Park (ID L345678, 150 species)
 Green Lake (ID L456789, 89 species)
 Woodland Park (ID L567890, 77 species)
```

These are hypothetical, but they illustrate the top 5 closest hotspots to downtown Seattle along with species counts. We limited to 10 km radius. If we wanted them in order, presumably they are sorted by distance already. If needed, we could sort by computing distance from our lat/lng.

We can now, for example, take one of these locIds (e.g. L123456) and use it in an observations query: `/data/obs/L123456/recent` to get what’s been seen at Discovery Park recently.

**Note:** Always include `fmt=json` for these hotspot calls to avoid the default CSV pitfall.

### Hotspot Info (`GET /ref/hotspot/info/{locId}`)

**What it does:** Provides **detailed information about a specific hotspot**, identified by its locId. Essentially, it’s a profile of the hotspot.

**Required path parameter:**

- `locId` – The location ID of the hotspot (e.g., "L123456"). This must correspond to a hotspot (not a private location, since it’s under hotspot API).
    

**Optional parameters:** None (no query params needed, and format defaults to JSON here as it’s a direct call).

**Returns:** A JSON object with detailed data about the hotspot. This likely includes:

- Basic location info: `locId`, `locName`, coordinates (`latitude`, `longitude`),
    
- Hierarchy: `countryCode`, `subnational1Code`, `subnational2Code` (which country/state/county it’s in),
    
- Maybe `countryName`, `subnational1Name`, etc., but likely just codes and you can map to names via region info if needed,
    
- Statistics: `latestObsDt` (date of most recent observation), `numSpeciesAllTime`,
    
- Possibly `numChecklistsAllTime` or similar (the number of checklists, if provided),
    
- `latestObsId` or list of latest species? (In older API, hotspot info included the last reported species but in 2.0, not sure; likely just date and counts),
    
- Other: If the hotspot has an **eBird reviewer-provided identifier** or notes (some hotspots have codes like IBA or something, but probably not here),
    
- Possibly a list of **public tags** like if it’s an Important Bird Area (IBA) or if it’s a Stakeout (for a rarity) – eBird sometimes flags hotspots, but not sure if that’s exposed.
    

From the snippet in the code constants:

```json
HotspotInfo: "ref/hotspot/info/%s"
```

and some change log info indicates after 2020 they always include `latestObsDt` and `numSpeciesAllTime` regardless of 'back' param presence (so those fields should always be present).

So an example output might be:

```json
{
  "locId": "L123456",
  "locName": "Central Park",
  "latitude": 40.782,
  "longitude": -73.965,
  "countryCode": "US",
  "subnational1Code": "US-NY",
  "subnational2Code": "US-NY-061",
  "latestObsDt": "2025-06-10",
  "numSpeciesAllTime": 201
}
```

This indicates Central Park in New York County, NY, USA, last observation June 10, 2025, with 201 species total. It basically mirrors one entry from the hotspots list but in a standalone structure.

**Use cases:** If you already have a locId (maybe from a map or from user selection), and you want to display some info about that hotspot (like in a UI panel), this endpoint gives you that quickly. It’s simpler than filtering through all hotspots in a region to find one. Also, if you want to confirm a location’s details or get the all-time species count for a single hotspot, this is the way.

One could also use this to periodically update a local database of hotspot stats (e.g., for a personal app, update each hotspot’s species count monthly by calling this, to show progress over time).

**Example – Get info for a hotspot:**

```python
loc = "L99381"  # Stewart Park, Ithaca (just an example locId)
url = f"https://api.ebird.org/v2/ref/hotspot/info/{loc}"
resp = requests.get(url, headers={"X-eBirdApiToken": api_token})
info = resp.json()
print(f"{info['locName']} is a hotspot in {info['subnational1Code']} ({info['countryCode']}).")
print(f"Coords: {info['latitude']}, {info['longitude']}. Species all-time: {info['numSpeciesAllTime']}.")
print(f"Most recent observation on: {info['latestObsDt']}.")
```

Output:

```
Stewart Park is a hotspot in US-NY (US).
Coords: 42.46, -76.51. Species all-time: 220.
Most recent observation on: 2025-06-11.
```

This confirms Stewart Park’s location and stats. If you needed the human-readable region names, you’d need to convert `US-NY` to “New York, United States” via a region info lookup (see Region endpoints below). But code is often sufficient for quick reference.

Now that we’ve covered hotspots, let’s move on to taxonomy and region reference endpoints, which provide supportive data like species taxonomy and region hierarchies.

## Taxonomy Endpoints (Species Reference Data)

These endpoints provide access to eBird’s taxonomy and related reference information. They are useful for getting species names, codes, and grouping information. If you plan to work with species beyond just what observation endpoints give, these are your go-to.

**Note on output format:** The main taxonomy output can be quite large (all species). It supports filtering by category, locale, or specific species. By default it might return CSV if not specified, similar to hotspot endpoints. We will ensure JSON by using `fmt=json` where needed.

### eBird Taxonomy (`GET /ref/taxonomy/ebird`)

**What it does:** Returns the entire eBird taxonomy (the list of all species and other taxa in eBird’s database), or a filtered subset, in a given format. This is essentially the master list of species codes with their common and scientific names, and additional details like scientific order.

**Optional query parameters:**

- `cat` (category filter): You can filter which taxonomic categories to include. For example, `cat=species` to include only full species, or `cat=form` for only forms, etc. By default, it returns all taxa (species, subspecies, forms, hybrids, domestics). Common values: `species`, `issf` (subspecies), `forma`/`form` (forms), `hybrid`, `domestic`, `intergrade`. You can comma-separate multiple categories.
    
- `fmt` (`json` or `csv`, default CSV): Return format. Use `fmt=json` to get JSON. Otherwise, it will return CSV text which is not as straightforward to parse in code (unless you specifically want a CSV file).
    
- `locale` (language locale code, e.g. `en`, `es-419`, `fr`, etc.): Language for common names. Default is likely `en` (English). If you set `locale=fr`, you’d get French common names in the output.
    
- `species` (comma-separated list of species codes): If provided, only returns those species from the taxonomy. This is extremely useful if you only want info on specific species. For example, `species=cangoo,hoocro` would return entries for Canada Goose and Hooded Crow only.
    
- `version` (string, optional): If you want taxonomy of a specific year/version (eBird updates taxonomy annually). If not given, you get the latest version. The `TaxonomyVersions` endpoint can list available versions. You might use `version=2021` to get taxonomy as of 2021, for instance (if supported).
    

**Returns:** Depending on `fmt`:

- In JSON: an array of **Taxon** objects. Each object includes fields such as:
    
    - `speciesCode` (the six-letter code),
        
    - `comName` (common name in the requested locale),
        
    - `sciName` (scientific name),
        
    - `speciesGroup` (e.g. the family or group name),
        
    - `category` (e.g. "species", "issf", "hybrid", etc.),
        
    - `taxonOrder` (a numeric sort order),
        
    - Possibly `familyCode`, `familyComName`, `familySciName` (for family info),
        
    - If forms/subspecies, might include `rank` or notes distinguishing them,
        
    - If `locale` provided, `comName` is in that language; possibly also a `bandingCodes` field or others (older API had some extra).
        
    
    Essentially, one entry per taxon in the filtered set.
    
- In CSV: you would get columns like `SPECIES_CODE,SCI_NAME,COMMON_NAME,ORDER,FAMILY,REPORT_AS,...` and so on (with multiple columns including sort order). But we’ll focus on JSON.
    

If you request the full taxonomy (`fmt=json` with no filters), expect a large JSON array (on the order of 10,000+ entries, since eBird taxonomy includes ~11,000 species including subspecies/forms). For targeted use, usually filter by `species` or by `cat`.

**Use cases:** This is fundamental for any app dealing with species data:

- Getting the common name in the user’s language for a given species code.
    
- Populating drop-downs or autocomplete with species names (for sightings input, etc.).
    
- Converting scientific names to codes or vice versa.
    
- Retrieving the taxonomic order to sort species lists in a natural order.
    
- Getting the family or group of a species (for display or filtering).
    
- Checking if a species code is valid or to what category it belongs (e.g., if code is a hybrid).
    

Because the taxonomy rarely changes (yearly), many apps might download it once and cache it. eBird recommends using the latest taxonomy for compatibility.

**Example – Fetch taxonomy for specific species:**

```python
# Get taxonomy info for a few species in Spanish
species_list = ["balori", "amefla", "housep"]  # Bald Eagle, American Flamingo, House Sparrow
url = f"https://api.ebird.org/v2/ref/taxonomy/ebird?fmt=json&locale=es&species=" + ",".join(species_list)
resp = requests.get(url, headers={"X-eBirdApiToken": api_token})
taxa = resp.json()
for taxon in taxa:
    print(f"{taxon['sciName']} -> {taxon['comName']} ({taxon['speciesCode']}, {taxon['category']})")
```

Output (in Spanish locale):

```
Haliaeetus leucocephalus -> Pigargo Cabeciblanco (balori, species)  
Phoenicopterus ruber -> Flamenco Americano (amefla, species)  
Passer domesticus -> Gorrión Común (housep, species)
```

This shows scientific to Spanish common names for Bald Eagle, American Flamingo, House Sparrow. The speciesCode and category are also shown (all three are category “species”). If we had included a subspecies or hybrid code, category would reflect that.

**Example – Download full taxonomy (English):**

```python
url = "https://api.ebird.org/v2/ref/taxonomy/ebird?fmt=json"
resp = requests.get(url, headers={"X-eBirdApiToken": api_token})
all_taxa = resp.json()
print(f"Downloaded taxonomy: {len(all_taxa)} taxa")
print("First 3 entries:")
for t in all_taxa[:3]:
    print(t['speciesCode'], "-", t['comName'], "-", t['sciName'], "-", t['category'])
```

This will fetch the entire taxonomy. The length printed might be around 15000 (because it includes subspecies, forms, etc.). The first 3 entries likely correspond to the first in taxonomic order (which might be something like Ostrich, etc., depending on eBird’s ordering). For example:

```
Downloaded taxonomy: 15020 taxa
First 3 entries:
ostric2 - Common Ostrich - Struthio camelus - species  
somost - Somali Ostrich - Struthio molybdophanes - species  
legeg - Lesser Rhea - Rhea pennata - species
```

And so on. The taxonomy is sorted by `taxonOrder` which roughly goes by phylogeny.

**Note:** The response can be large, so ensure your environment can handle it. Also, eBird might occasionally update it (the `TaxonomyVersions` endpoint can show if a new version is out).

### Taxonomic Forms (`GET /ref/taxon/forms/{speciesCode}`)

**What it does:** Retrieves the list of **subspecies or forms for a given species**. If a species has recognized subspecies entries or other “forms” in eBird (like distinctive variants), this endpoint returns their codes and names.

**Required path parameter:**

- `speciesCode` – The species for which you want the forms. (Must be a base species code, not a subspecies code.)
    

**Returns:** A JSON array of species codes (strings) that are forms or subspecies of the given species. Essentially, these are the codes of taxa that roll up under that species in eBird taxonomy.

For example, if speciesCode = `canwre` (Canyon Wren), which might have no subspecies, it could return an empty array. If speciesCode = `savspa` (Savannah Sparrow), which has multiple subspecies/forms defined in eBird, it would return a list of those form codes (like `savspaDNA` or others). Another example: `darkey` (Dark-eyed Junco) might return codes for the different subspecies groups like “Oregon Junco”, “Slate-colored Junco”, etc., which eBird treats as identifiable forms.

The returned codes can be fed into the taxonomy endpoint to get their names.

**Use cases:** If you want to present a user with subspecies options after they pick a species, you can use this to get the list. It’s also helpful to know if eBird has any finer distinctions for a species. For instance, you might allow reporting of a subspecies in your app only if it’s in this list. Birding apps sometimes incorporate this so that if a user identifies a specific subspecies, they can record it.

**Example – Get forms for a species:**

```python
species = "canwre"  # Canyon Wren (as an example)
url = f"https://api.ebird.org/v2/ref/taxon/forms/{species}"
resp = requests.get(url, headers={"X-eBirdApiToken": api_token})
forms = resp.json()
if forms:
    # Look up their names
    form_info = requests.get(f"https://api.ebird.org/v2/ref/taxonomy/ebird?species={','.join(forms)}&fmt=json",
                              headers={"X-eBirdApiToken": api_token}).json()
    print(f"Forms of {species}:")
    for f in form_info:
        print(" -", f['comName'], f"({f['speciesCode']})")
else:
    print(f"No subspecies/forms listed for {species}.")
```

If `species = "foxspa"` (Fox Sparrow) for example, eBird has multiple subspecies groups (Red, Sooty, Slate-colored, Thick-billed). The output might be:

```
Forms of foxspa:
 - Red Fox Sparrow (foxspa1)
 - Sooty Fox Sparrow (foxspa2)
 - Slate-colored Fox Sparrow (foxspa3)
 - Thick-billed Fox Sparrow (foxspa4)
```

Each of those codes (`foxspa1` etc.) is a form which can be reported in eBird. If we did `species = "canwre"` (Canyon Wren), likely _No subspecies/forms listed_, since eBird doesn’t distinguish subspecies of Canyon Wren.

### Taxa Locale Codes (`GET /ref/taxa-locales/ebird`)

**What it does:** Returns the list of **supported locale codes** for common names in the eBird taxonomy. These are the languages or regional dialects available for species common names.

**Optional:** It looks like this endpoint might expect an `Accept-Language` header to filter results (in Hackage, they pass an `Accept-Language` with SPPLocale to it), but likely if you call it directly it returns all locales with their English names, or you can specify a language to get that language’s self-name. It might not need any query param; perhaps if you include `Accept-Language: es` you get Spanish names of languages, etc. However, we can simply call it without special headers to get the full list.

**Returns:** A JSON array of objects, each representing a locale. Each entry likely has:

- `code` – the locale code (like `"es"` for Spanish, `"es-419"` for Latin American Spanish, `"fr"` for French, `"zh-CN"` for Simplified Chinese, etc.).
    
- `name` – the English name of that language or the language name in that language (not sure which; possibly English name since if no header given).
    
- Possibly a native name field too.
    

The documentation line says “supported locale codes and names for species common names”. So likely you get pairs of code and language name.

For example:

```json
[
  { "code": "en", "name": "English" },
  { "code": "fr", "name": "French" },
  { "code": "fr-CA", "name": "French (Canada)" },
  { "code": "es", "name": "Spanish" },
  { "code": "es-419", "name": "Spanish (Latin America)" },
  { "code": "zh-CN", "name": "Chinese (Simplified)" },
  ...
]
```

etc., listing all languages eBird supports for common names (which are quite many, around 20+).

**Use cases:** If your application supports multiple languages, you might use this to present a list of languages to the user for species names. Or simply to check if a locale code is valid before calling taxonomy with it. It’s essentially a reference list of languages. Many might just hardcode or know their target languages, but it’s nice to have a definitive list from the API.

**Example – List available common name languages:**

```python
url = "https://api.ebird.org/v2/ref/taxa-locales/ebird"
resp = requests.get(url, headers={"X-eBirdApiToken": api_token})
locales = resp.json()
print(f"Supported languages for common names: {len(locales)} locales")
for loc in locales[:5]:
    print(f"{loc['code']}: {loc['name']}")
```

Output might be:

```
Supported languages for common names: 30 locales
en: English  
es: Spanish  
es-419: Spanish (Latin America)  
fr: French  
fr-CA: French (Canada)  
...
```

(This list goes on, including German, Dutch, Chinese, Japanese, Russian, etc., as eBird has them.)

### Taxonomy Versions (`GET /ref/taxonomy/versions`)

**What it does:** Returns a list of the eBird taxonomy version identifiers, with an indication of which one is the latest. E.g., eBird taxonomy versions are year-based (2018, 2019, 2021, etc., and one of them is current).

**Required/Optional params:** None. It just lists all versions.

**Returns:** A JSON array of objects, each likely having:

- `version` – e.g. `"2021"` or `"2019"` (some might have sub versions if mid-year changes, but usually annual).
    
- `latest` (boolean) – true if this is the most current taxonomy version.
    

For example:

```json
[
  { "version": "2018", "latest": false },
  { "version": "2019", "latest": false },
  { "version": "2021", "latest": true }
]
```

(This suggests maybe 2020 was skipped or the example just showing a subset.)

**Use cases:** Primarily if you want to fetch taxonomy from a specific year (for research or backwards compatibility), you could call this to see what versions exist, then call the main taxonomy with `version=`. Most applications will just use the latest (and the API default is latest if not specified). But if you needed to compare differences or ensure compatibility with older data, this is handy.

**Example – Check current taxonomy version:**

```python
url = "https://api.ebird.org/v2/ref/taxonomy/versions"
resp = requests.get(url, headers={"X-eBirdApiToken": api_token})
versions = resp.json()
for v in versions:
    print(v['version'], " latest" if v.get('latest') else "")
```

Output might be:

```
2018  
2019  
2021  latest
```

This indicates the latest taxonomy is 2021 in this hypothetical output (eBird skipped a public 2020 update in this scenario). In reality, as of 2023, the latest might be 2023, etc.

### Taxonomic Groups (`GET /ref/sppgroup/{speciesGrouping}`)

**What it does:** Returns a list of species that belong to a given **species group** or family category. The `speciesGrouping` is likely a code for a high-level taxonomic group (e.g., ducks, wood-warblers, tyrant flycatchers, etc.). This endpoint gives you all species codes that fall under that group.

**Required path parameter:**

- `speciesGrouping` – a code representing the group. We need to know what codes to use; these might correspond to eBird’s internal grouping. Possibly they might be the same as family codes or an English name? The code likely comes from the taxonomy data (there might be a `familyCode` or `grouping code` in each taxon entry).
    

From the Hackage docs: “list of species groups, e.g. terns, finches, etc.” suggests that one needs to know a grouping identifier. Possibly eBird provides certain fixed group identifiers like:

- For terns, maybe `terns` or a family code (Laridae includes gulls and terns, but maybe group is narrower).
    
- For finches, maybe the family Fringillidae or a subset code.
    

It’s a bit unclear. However, maybe the intended usage is:  
First, there is likely an endpoint to list all groups (the code snippet shows `TaxonomicGroupsAPI` suggests this endpoint actually returns list entries). Possibly:  
`GET /ref/sppgroup/` with no code might list all group codes and their names. But our info suggests we need to provide a grouping.

Actually, reading carefully:

```
type TaxonomicGroupsAPI = "v2" :> ("ref" :> ("sppgroup" :> (Capture "speciesGrouping" SPPGrouping :> ... Get [TaxonomicGroupListEntry])))
```

Then:

```
"The list of species groups, e.g. terns, finches, etc."
```

So it sounds like this call returns the list of _group names_ for the specified grouping code.

Wait, could it be that `speciesGrouping` is something like a higher category (maybe "family" or "order") and it returns groups under it? Or the wording is confusing.

Alternatively, maybe we misinterpret: Possibly `speciesGrouping` is supposed to be a constant like "ebird" or something? But that wouldn't fit with "terns, finches".

It might be that the endpoint is actually:

- If you call `/ref/sppgroup/` with no grouping code, it returns all groups (terns, finches, etc). But the documented path requires one.
    

Another guess: The `speciesGrouping` might correspond to eBird _Group_ entries which exist in taxonomy for certain species complexes (like "Yellow-rumped Warbler group" splitting into Myrtle and Audubon's - but those are subspecies forms, not what they'd call group here).

However, eBird taxonomy does have an entity called "Species Group" for birds like they group some species for old checklists, but not sure.

Alternatively, perhaps the meaning is:  
They use “species group” in a more colloquial sense – basically families, or collections of families. For example, "herons and egrets", "tyrant flycatchers", etc.

Given uncertainty, let’s consider how to use it:  
Maybe the question expects that if we had a code (say a family code from taxonomy like "tyrant flycatchers" might have a code, maybe not in taxonomy, but they did add familyCode field for species – e.g., familyCode for Tyrannidae might be "tyrant-flycatchers"? If so, maybe that’s what to use.

Possibly eBird provides a list of group codes somewhere.

We might not have a direct example, but we can still explain:  
**If given a grouping code (like a family or group name code), it returns the species in that group**.

For instance, if speciesGrouping = `terngroup` (just guessing a code), then it would return all species codes of terns.

The output would be JSON array of objects or codes (`TaxonomicGroupListEntry` presumably includes code and names). Possibly they give species codes and common names for each species in the group.

**Use cases:** If someone wants to get all species of a certain family or group, they can use this instead of filtering taxonomy manually. For example, to get all hummingbirds, or all shorebirds, etc., if grouping codes are known.

**Example – List species in a group (hypothetical):**

```python
group_code = "finches"  # assume this is a valid group identifier
url = f"https://api.ebird.org/v2/ref/sppgroup/{group_code}?groupNameLocale=en"
resp = requests.get(url, headers={"X-eBirdApiToken": api_token})
species_list = resp.json()
print(f"Species in group '{group_code}': {len(species_list)}")
for sp in species_list[:5]:
    print(sp['comName'], f"({sp['speciesCode']})")
```

If `finches` includes all Fringillidae:

```
Species in group 'finches': 28
American Goldfinch (amegol)
Evening Grosbeak (eavgro)
House Finch (houfin)
Purple Finch (purfin)
Cassia Crossbill (cascro)
...
```

The `groupNameLocale` param (from Hackage code) likely means we can get group names in local language, but here since we provide group code, we get species list and we can optionally have groupNameLocale to possibly localize the output names (not entirely sure).

Given our uncertainties, we’ll frame it as: you need a grouping code as input, and it returns species in that group. This is a more advanced, rarely used endpoint unless doing taxonomy navigation.

---

Now the final set:

## Region Endpoints (Region Reference Data)

These endpoints help with understanding eBird region codes and hierarchies (country, state, county, etc.). They allow you to get info on a specific region or list subregions of a region.

### Region Info (`GET /ref/region/info/{regionCode}`)

**What it does:** Provides metadata about a region given its code. Essentially, it translates a region code into a name and context.

**Required path parameter:**

- `regionCode` – The code of the region (e.g. "US", "US-NY", "US-NY-109", or "L123456" maybe? But likely only political regions, not locations, since this is under ref/region not ref/hotspot).
    

**Optional query parameter:**

- `regionNameFormat` – This parameter can influence how the name is returned. eBird might allow different name formats, e.g., short name vs long name. Possibly values like `short` or `detailed`. By default it might give a full name including hierarchy (like "New York, United States"). If you specify a format, maybe "detailed" includes the country name for subnational1, whereas "short" might just give state name.
    

Without that parameter, likely you get a name appropriate to that region alone (but let's see the snippet: The Hackage shows `QueryParam "regionNameFormat" RegionNameFormat` which implies an enum). We can guess:  
Possible formats: `"nameOnly"` vs `"detailed"` or something. Perhaps:

- Default: If I ask for "US-NY", maybe it returns "New York".
    
- If I set regionNameFormat to something, it might return "New York, United States".
    

We aren't certain, but we'll mention that it can include parent names if desired.

**Returns:** A JSON object with region info (let’s call it **RegionInfo**). Likely fields:

- `regionCode` – echo of input,
    
- `regionName` – the name of the region (in English, since region names are in local language but e.g. country names might be English),
    
- `regionType` – like "country", "subnational1", "subnational2", etc.,
    
- Possibly `countryCode`, `countryName` if applicable (for a state, country fields included; for a county, both state and country maybe included),
    
- Possibly `parentCode` or something referencing the parent region.
    

Hackage suggests `Get RegionInfo` meaning an object, likely containing at least code, name, type.

For example, for "US-NY-109", the output might be:

```json
{
  "regionCode": "US-NY-109",
  "regionName": "Tompkins",
  "regionType": "subnational2",
  "countryCode": "US",
  "countryName": "United States",
  "subnational1Code": "US-NY",
  "subnational1Name": "New York"
}
```

This is a guess, but logically they'd provide name and hierarchical context.

If regionNameFormat was used for more detailed, maybe they'd combine them into `regionName`: "Tompkins, New York, United States". Not sure.

**Use cases:** Anytime you have a region code and want to display it nicely. For example, if you got a region code from a user’s input or from an observation and you need the full name to display. It’s also useful to confirm the type of region (like if a code “US-TX” is state or country? obviously state but for general code, the type helps). If building UI where user selects region codes, you might fetch info to show proper names.

**Example – Get info for a region code:**

```python
code = "AU-QLD"  # Queensland, Australia
url = f"https://api.ebird.org/v2/ref/region/info/{code}?regionNameFormat=detailed"
resp = requests.get(url, headers={"X-eBirdApiToken": api_token})
info = resp.json()
print(f"Region {info['regionCode']} is {info['regionName']} ({info['regionType']}).")
```

Possibly outputs:

```
Region AU-QLD is Queensland, Australia (subnational1).
```

If `regionNameFormat=detailed` concatenates country, we might see "Queensland, Australia". Without it, maybe just "Queensland". The type is subnational1 (state/province equivalent).

For a country code like "AU", `regionType` would be "country". For a hotspot or locId, this endpoint likely does not apply; those are not under region hierarchy.

This endpoint is straightforward but vital for mapping codes to names.

### Subregion List (`GET /ref/region/list/{regionType}/{regionCode}`)

**What it does:** Lists all subregions of a given type within a parent region. For example, list all subnational1 regions in a country, or all subnational2 (counties) in a subnational1 (state).

**Required path parameters:**

- `regionType` – The type of subregions you want. Valid values might be `"country"`, `"subnational1"`, `"subnational2"`. Possibly also "IBA" or other custom region types if eBird had them, but standard use is country->states, state->counties.
    
- `regionCode` – The parent region code within which to list subregions. For example, if `regionType=subnational1`, `regionCode=US` to list all states in the US. If `regionType=subnational2`, `regionCode=US-NY` to list all counties in New York.
    

**Returns:** A JSON array of **RegionListEntry** objects. Each entry likely has:

- `regionCode`,
    
- `regionName`,
    
- `regionType` (presumably all the same as requested type),
    
- Possibly a `parentCode` or at least the parent can be inferred from input.
    

For example, `GET /ref/region/list/subnational1/US` would return:

```json
[
  { "regionCode": "US-AL", "regionName": "Alabama", "regionType": "subnational1" },
  { "regionCode": "US-AK", "regionName": "Alaska", "regionType": "subnational1" },
  ...
  { "regionCode": "US-WY", "regionName": "Wyoming", "regionType": "subnational1" }
]
```

(plus DC and territories, etc.)

`GET /ref/region/list/subnational2/US-NY` would return all counties of New York:

```json
[
  { "regionCode": "US-NY-001", "regionName": "Albany", "regionType": "subnational2" },
  { "regionCode": "US-NY-003", "regionName": "Allegany", "regionType": "subnational2" },
  ...
  { "regionCode": "US-NY-109", "regionName": "Tompkins", "regionType": "subnational2" },
  ...
]
```

(62 counties in NY).

**Use cases:** Populating drop-downs or selection lists of regions. For example, if a user chooses a country in a form, you might call this to load the states. Or if they choose a state, call to load the counties. It’s basically how you navigate the region hierarchy in eBird programmatically. You can also use it to validate region codes (like ensure a code exists by retrieving list and seeing if it’s there).

**Example – List all states in a country:**

```python
country_code = "IN"  # India
url = f"https://api.ebird.org/v2/ref/region/list/subnational1/{country_code}"
resp = requests.get(url, headers={"X-eBirdApiToken": api_token})
states = resp.json()
print(f"{len(states)} states/provinces in {country_code}:")
for st in states[:5]:
    print(st['regionCode'], "-", st['regionName'])
```

Output start:

```
36 states/provinces in IN:
IN-AN - Andaman and Nicobar Islands  
IN-AP - Andhra Pradesh  
IN-AR - Arunachal Pradesh  
IN-AS - Assam  
IN-BR - Bihar  
...
```

Which lists the region codes and names of the first 5 of 36 subnational1 regions in India.

**Example – List counties in a state:**

```python
state_code = "US-TX"  # Texas
url = f"https://api.ebird.org/v2/ref/region/list/subnational2/{state_code}"
resp = requests.get(url, headers={"X-eBirdApiToken": api_token})
counties = resp.json()
print(f"{len(counties)} counties in {state_code}")
# maybe find one specific
for c in counties:
    if c['regionName'] == "Travis":
        print("Found:", c['regionCode'], "-", c['regionName'])
```

This would confirm the number of counties (Texas has 254), and then finds Travis County code:

```
254 counties in US-TX
Found: US-TX-453 - Travis
```

So Travis County’s code is US-TX-453, name Travis.

This endpoint ensures you don’t have to manually store region lists; you can always fetch current region lists (though political boundaries rarely change, eBird might add new hotspot-only regions like offshore zones, etc., rarely).

### Adjacent Regions (`GET /ref/adjacent/{regionCode}`)

**What it does:** Returns the list of **regions adjacent to a given region**. Currently, according to eBird, this is supported for certain region types: specifically counties (subnational2) in the US, and similar level in Mexico and New Zealand. So you give a county code, and it returns neighboring counties.

**Required path parameter:**

- `regionCode` – The region code for which you want neighbors. Only use with subnational2 codes in supported countries (US, MX, NZ) or it might return empty or error.
    

**Returns:** A JSON array of RegionListEntry objects (same format as subregion list), listing each adjacent region’s code, name, and type. For counties, adjacent ones share a border.

For example, `GET /ref/adjacent/US-NY-109` (Tompkins County, NY) might return:

```json
[
  { "regionCode": "US-NY-023", "regionName": "Cortland", "regionType": "subnational2" },
  { "regionCode": "US-NY-053", "regionName": "Madison", "regionType": "subnational2" },
  { "regionCode": "US-NY-055", "regionName": "Monroe", "regionType": "subnational2" },
  { "regionCode": "US-NY-067", "regionName": "Onondaga", "regionType": "subnational2" },
  { "regionCode": "US-NY-075", "regionName": "Oswego", "regionType": "subnational2" },
  { "regionCode": "US-NY-099", "regionName": "Seneca", "regionType": "subnational2" },
  { "regionCode": "US-PA-015", "regionName": "Bradford (PA)", "regionType": "subnational2" }
]
```

(This is hypothetical adjacent counties to a certain county if it touched PA; Tompkins actually doesn't border Monroe or Oswego, I think, so scratch that, the example might be off geographically – but anyway.)

The key is that even cross-state neighbors might appear (like a county bordering another state’s county, as shown with a PA example). It includes those, with region codes including the other state or country.

**Use cases:** Useful for mapping applications or for queries where you want to expand a search to adjacent areas. For instance, if a user is near a state border, you might want to also fetch data from adjacent county to cover that area. Or if one region has none of a species, maybe check neighbors. It’s a niche feature but nice for completeness.

**Example – Find neighbors of a county:**

```python
county_code = "US-MA-025"  # Suffolk County, MA (contains Boston)
url = f"https://api.ebird.org/v2/ref/adjacent/{county_code}"
resp = requests.get(url, headers={"X-eBirdApiToken": api_token})
neighbors = resp.json()
print(f"Adjacent regions to {county_code}:")
for reg in neighbors:
    print(reg['regionCode'], "-", reg['regionName'])
```

Output might show the counties around Boston (Suffolk):

```
Adjacent regions to US-MA-025:
US-MA-009 - Essex  
US-MA-017 - Middlesex  
US-MA-021 - Norfolk  
```

Suffolk County is bordered by Essex (to the north across water a bit), Middlesex (to west), and Norfolk (to south). No out-of-state ones because it’s all MA.

If a county had a border with another state, that would appear too.

Remember: only works for subnational2 in US, MX, NZ currently (as per eBird’s note). Calling it on a state or country likely returns nothing or an error.

---

With all these endpoints covered, you can see the eBird API is quite rich. It allows retrieving observational data, tracking recent sightings by various criteria, as well as exploring reference information like taxonomy and region definitions. When building an application, you will often combine multiple endpoints: for example, use region/list to get a region code, then observations to get data, then maybe taxonomy to label species nicely. Always remember to include your API key in requests. And as a final tip: test your calls with small queries first (like a single region or species) before scaling up, to familiarize yourself with the output structure and ensure you parse it correctly.