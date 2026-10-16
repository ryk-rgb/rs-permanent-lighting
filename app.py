import os, io, csv, base64, secrets, functools, html, sqlite3, math
from datetime import datetime
from flask import Flask, request, redirect, url_for, Response, render_template_string, flash
import qrcode
import requests
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(24))

DATABASE_URL = os.environ.get("DATABASE_URL", "")
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_IMAGE_MODEL = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1")
GHL_WEBHOOK_URL = os.environ.get("GHL_WEBHOOK_URL", "")
BUSINESS_NAME = os.environ.get("BUSINESS_NAME", "RS Permanent Lighting")
BUSINESS_PHONE = os.environ.get("BUSINESS_PHONE", "704-621-6399")
BUSINESS_WEBSITE = os.environ.get("BUSINESS_WEBSITE", "")
ATTOM_API_KEY = os.environ.get("ATTOM_API_KEY", "")
ATTOM_SLIPSTREAM_URL = os.environ.get("ATTOM_SLIPSTREAM_URL", "").strip()
ATTOM_SLIPSTREAM_TOKEN = os.environ.get("ATTOM_SLIPSTREAM_TOKEN", "")
ATTOM_SLIPSTREAM_MARKET = os.environ.get("ATTOM_SLIPSTREAM_MARKET", "*")
ATTOM_SLIPSTREAM_AUTH_HEADER = os.environ.get("ATTOM_SLIPSTREAM_AUTH_HEADER", "Authorization")
ATTOM_SLIPSTREAM_AUTH_PREFIX = os.environ.get("ATTOM_SLIPSTREAM_AUTH_PREFIX", "Bearer ")
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
MAPILLARY_ACCESS_TOKEN = os.environ.get("MAPILLARY_ACCESS_TOKEN", "")
MAPILLARY_RADIUS_METERS = int(os.environ.get("MAPILLARY_RADIUS_METERS", "90"))

TARGET_PROPERTIES = [{"address":"433 Hollis Road","city":"Charlotte","state":"NC","zip":"28209"},{"address":"529 Kenlough Drive","city":"Charlotte","state":"NC","zip":"28209"},{"address":"1901 Runnymede Lane","city":"Charlotte","state":"NC","zip":"28211"},{"address":"844 Armstrong Road","city":"Belmont","state":"NC","zip":"28012"},{"address":"631 May Green Drive","city":"Clover","state":"SC","zip":"29710"},{"address":"12414 Tantallon Court","city":"Pineville","state":"NC","zip":"28134"},{"address":"2065 Marquesas Avenue","city":"Tega Cay","state":"SC","zip":"29708"},{"address":"5480 Glen Forest Drive","city":"Charlotte","state":"NC","zip":"28226"},{"address":"4843 Lindstrom Drive","city":"Charlotte","state":"NC","zip":"28226"},{"address":"512 Olmsted Park Place","city":"Charlotte","state":"NC","zip":"28203"},{"address":"7615 Quail Hill Road","city":"Charlotte","state":"NC","zip":"28210"},{"address":"16516 Riverpointe Drive","city":"Charlotte","state":"NC","zip":"28278"},{"address":"4206 Foxmoor Drive #L43B2M19-181","city":"Charlotte","state":"NC","zip":"28226"},{"address":"5109 Wedgewood Drive","city":"Charlotte","state":"NC","zip":"28210"},{"address":"4124 Bridgewood Lane","city":"Charlotte","state":"NC","zip":"28226"},{"address":"423 Crisfield Court","city":"York","state":"SC","zip":"29745"},{"address":"105 Coburn Court","city":"Fort Mill","state":"SC","zip":"29715"},{"address":"1816 Cedar Park Drive","city":"Pineville","state":"NC","zip":"28134"},{"address":"976 Park Slope Drive","city":"Charlotte","state":"NC","zip":"28209"},{"address":"5807 Sharon Road #F","city":"Charlotte","state":"NC","zip":"28210"},{"address":"529 Putting Drive","city":"Fort Mill","state":"SC","zip":"29715"},{"address":"1333 Secret Path Drive","city":"Fort Mill","state":"SC","zip":"29708"},{"address":"7007 Shaw Court","city":"Indian Land","state":"SC","zip":"29707"},{"address":"727 Clayfield Court","city":"Charlotte","state":"NC","zip":"28209"},{"address":"12726 Axel Road","city":"Pineville","state":"NC","zip":"28134"},{"address":"12708 Axel Road","city":"Pineville","state":"NC","zip":"28134"},{"address":"12720 Axel Road","city":"Pineville","state":"NC","zip":"28134"},{"address":"1710 Evergreen Drive","city":"Charlotte","state":"NC","zip":"28208"},{"address":"15506 Parkside Crossing Drive","city":"Charlotte","state":"NC","zip":"28278"},{"address":"12716 Axel Road","city":"Pineville","state":"NC","zip":"28134"},{"address":"12730 Axel Road","city":"Pineville","state":"NC","zip":"28134"},{"address":"12712 Axel Road","city":"Pineville","state":"NC","zip":"28134"},{"address":"3820 Planters Watch Drive","city":"Charlotte","state":"NC","zip":"28278"},{"address":"7515 Starvalley Drive","city":"Charlotte","state":"NC","zip":"28210"},{"address":"9482 Ketchum Drive","city":"Gastonia","state":"NC","zip":"28056"},{"address":"4053 Navajo Court","city":"Rock Hill","state":"SC","zip":"29732"},{"address":"12734 Axel Road","city":"Pineville","state":"NC","zip":"28134"},{"address":"13918 Wild Heather Court","city":"Charlotte","state":"NC","zip":"28273"},{"address":"3013 Callaway Court","city":"Cramerton","state":"NC","zip":"28032"},{"address":"6000 Gray Gate Lane #I","city":"Charlotte","state":"NC","zip":"28210"},{"address":"433 Battery Circle","city":"Clover","state":"SC","zip":"29710"},{"address":"11101 Sevilla Court","city":"Charlotte","state":"NC","zip":"28226"},{"address":"4620 Piedmont Row Road","city":"Charlotte","state":"NC","zip":"28210"},{"address":"10905 Rail Tye Place","city":"Pineville","state":"NC","zip":"28134"},{"address":"5718 Natick Drive","city":"Charlotte","state":"NC","zip":"28214"},{"address":"1761 J Julian Lane","city":"Charlotte","state":"NC","zip":"28208"},{"address":"1765 J Julian Lane","city":"Charlotte","state":"NC","zip":"28208"},{"address":"1773 J Julian Lane","city":"Charlotte","state":"NC","zip":"28208"},{"address":"420 English Ivy Court","city":"Fort Mill","state":"SC","zip":"29715"},{"address":"115 Adcock Street","city":"Belmont","state":"NC","zip":"28012"},{"address":"9719 Nine Eagles Lane","city":"Charlotte","state":"NC","zip":"28278"},{"address":"9715 Nine Eagles Lane","city":"Charlotte","state":"NC","zip":"28278"},{"address":"3200 Beaty Road","city":"Gastonia","state":"NC","zip":"28056"},{"address":"1811 Queens Road W","city":"Charlotte","state":"NC","zip":"28207"},{"address":"19800 Youngblood Road W","city":"Charlotte","state":"NC","zip":"28278"},{"address":"13702 Sage Thrasher Lane","city":"Charlotte","state":"NC","zip":"28278"},{"address":"6000 Midsomer Road","city":"Charlotte","state":"NC","zip":"28214"},{"address":"9305 White Ibis Court","city":"Belmont","state":"NC","zip":"28012"},{"address":"5620 Merry Mount Drive","city":"Charlotte","state":"NC","zip":"28226"},{"address":"2129 Queens Road W #403","city":"Charlotte","state":"NC","zip":"28207"},{"address":"6239 Sharon Hills Road","city":"Charlotte","state":"NC","zip":"28210"},{"address":"5204 Masons Ferry Road","city":"Clover","state":"SC","zip":"29710"},{"address":"932 Heather Lane","city":"Charlotte","state":"NC","zip":"28209"},{"address":"11828 Stephenson Court","city":"Charlotte","state":"NC","zip":"28277"},{"address":"15700 Youngblood Road","city":"Charlotte","state":"NC","zip":"28278"},{"address":"401 McDonald Avenue","city":"Charlotte","state":"NC","zip":"28203"},{"address":"10220 Sweetleaf Place","city":"Charlotte","state":"NC","zip":"28278"},{"address":"5549 Fairview Road","city":"Charlotte","state":"NC","zip":"28209"},{"address":"16525 Forest Home Road","city":"Charlotte","state":"NC","zip":"28278"},{"address":"6510 Sharon Hills Road","city":"Charlotte","state":"NC","zip":"28210"},{"address":"907 Osprey Bluff Court #1","city":"Belmont","state":"SC","zip":"29710"},{"address":"1218 Townes Road","city":"Charlotte","state":"NC","zip":"28209"},{"address":"6323 Saint Stephen Lane","city":"Charlotte","state":"NC","zip":"28210"},{"address":"1525 Lynway Drive","city":"Charlotte","state":"NC","zip":"28203"},{"address":"632 Ideal Way","city":"Charlotte","state":"NC","zip":"28203"},{"address":"2625/2655 Pleasant Road","city":"Fort Mill","state":"SC","zip":"29715"},{"address":"2129 Queens Road W #201","city":"Charlotte","state":"NC","zip":"28207"},{"address":"249 Blue Heron Drive","city":"Rock Hill","state":"SC","zip":"29732"},{"address":"5650 Riverfront Road","city":"Clover","state":"SC","zip":"29710"},{"address":"5555 Fairview Road","city":"Charlotte","state":"NC","zip":"28209"},{"address":"3240 Sunset Drive","city":"Charlotte","state":"NC","zip":"28209"},{"address":"2161 Windy Oaks Road","city":"Fort Mill","state":"SC","zip":"29708"},{"address":"10601 Wildlife Road","city":"Charlotte","state":"NC","zip":"28278"},{"address":"3407 Willow Oak Road","city":"Charlotte","state":"NC","zip":"28209"},{"address":"2640 Sadler Road","city":"Charlotte","state":"NC","zip":"28278"},{"address":"16312 Cozy Cove Road","city":"Charlotte","state":"NC","zip":"28278"},{"address":"331 Ivy Arbor Circle","city":"Rock Hill","state":"SC","zip":"29732"},{"address":"13117 Hamilton Place Drive","city":"Charlotte","state":"NC","zip":"28273"},{"address":"2250 Colony Road #A","city":"Charlotte","state":"NC","zip":"28209"},{"address":"10930 Green Heron Court","city":"Charlotte","state":"NC","zip":"28278"},{"address":"506 Joslin Pointe Lane","city":"Rock Hill","state":"SC","zip":"29732"},{"address":"15650 Youngblood Road","city":"Charlotte","state":"NC","zip":"28278"},{"address":"10310 Wildlife Road","city":"Charlotte","state":"NC","zip":"28278"},{"address":"10717 Wildlife Road","city":"Charlotte","state":"NC","zip":"28278"},{"address":"13703 Grand Palisades Parkway","city":"Charlotte","state":"NC","zip":"28278"},{"address":"5907 Kiowa Road","city":"Clover","state":"SC","zip":"29710"},{"address":"1920 Marlin Drive","city":"Lake Wylie","state":"SC","zip":"29710"},{"address":"2354 Valelake Road","city":"York","state":"SC","zip":"29745"},{"address":"3416 Windsor Drive","city":"Charlotte","state":"NC","zip":"28209"},{"address":"4448 Halstead Drive","city":"Charlotte","state":"NC","zip":"28209"}]

class SQLiteCursor:
    def __init__(self, cur): self.cur=cur
    def execute(self, sql, params=()):
        sql=sql.replace("%s","?").replace("NOW()","CURRENT_TIMESTAMP")
        sql=sql.replace("SERIAL PRIMARY KEY","INTEGER PRIMARY KEY AUTOINCREMENT").replace("BYTEA","BLOB").replace("BOOLEAN","INTEGER")
        if not params and ";" in sql.strip().rstrip(";"):
            self.cur.executescript(sql)
        else:
            self.cur.execute(sql, params)
        return self
    def fetchone(self):
        r=self.cur.fetchone(); return dict(r) if r is not None else None
    def fetchall(self):
        return [dict(r) for r in self.cur.fetchall()]

class SQLiteConn:
    def __init__(self, path):
        self.raw=sqlite3.connect(path)
        self.raw.row_factory=sqlite3.Row
    def cursor(self): return SQLiteCursor(self.raw.cursor())
    def commit(self): return self.raw.commit()
    def rollback(self): return self.raw.rollback()
    def close(self): return self.raw.close()

def db():
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return SQLiteConn(os.environ.get("SQLITE_PATH","/tmp/rs_lighting.db"))

def init_db():
    c = db()
    cur = c.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS properties(
      id SERIAL PRIMARY KEY,
      address TEXT NOT NULL,
      city TEXT NOT NULL DEFAULT 'Charlotte',
      state TEXT NOT NULL DEFAULT 'NC',
      zip TEXT NOT NULL DEFAULT '28278',
      owner_name TEXT NOT NULL DEFAULT '',
      original_image BYTEA,
      original_mime TEXT,
      mockup_image BYTEA,
      mockup_mime TEXT,
      image_source TEXT NOT NULL DEFAULT '',
      image_license_ok BOOLEAN NOT NULL DEFAULT FALSE,
      status TEXT NOT NULL DEFAULT 'PHOTO_NEEDED',
      token TEXT UNIQUE NOT NULL,
      scans INTEGER NOT NULL DEFAULT 0,
      mailed BOOLEAN NOT NULL DEFAULT FALSE,
      est_linear_ft NUMERIC NOT NULL DEFAULT 0,
      quote_amount NUMERIC NOT NULL DEFAULT 0,
      created_at TIMESTAMP NOT NULL DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS leads(
      id SERIAL PRIMARY KEY,
      property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
      name TEXT NOT NULL DEFAULT '',
      phone TEXT NOT NULL DEFAULT '',
      email TEXT NOT NULL DEFAULT '',
      notes TEXT NOT NULL DEFAULT '',
      created_at TIMESTAMP NOT NULL DEFAULT NOW()
    );
    """)
    cur.execute("SELECT COUNT(*) AS n FROM properties")
    if cur.fetchone()["n"] == 0:
        for p in TARGET_PROPERTIES:
            cur.execute(
                "INSERT INTO properties(address,city,state,zip,token) VALUES(%s,%s,%s,%s,%s)",
                (p["address"],p["city"],p["state"],p["zip"],secrets.token_urlsafe(10))
            )
    c.commit(); c.close()



def streetview_metadata_for_property(p):
    if not GOOGLE_MAPS_API_KEY:
        return None, "GOOGLE_MAPS_API_KEY is not configured on Render yet."
    location=f"{p['address']}, {p['city']}, {p['state']} {p['zip']}"
    r=requests.get(
        "https://maps.googleapis.com/maps/api/streetview/metadata",
        params={"location":location,"source":"outdoor","key":GOOGLE_MAPS_API_KEY},
        timeout=20
    )
    if not r.ok:
        return None, f"Google Street View metadata request failed ({r.status_code})."
    data=r.json()
    if data.get("status")!="OK":
        return None, f"Google Street View returned {data.get('status','UNKNOWN')} for this address."
    return data, None

def _geocode_property(p):
    full_address=f"{p['address']}, {p['city']}, {p['state']} {p['zip']}"

    # 1) ATTOM when coordinates are available.
    if ATTOM_API_KEY:
        try:
            r=requests.get(
                "https://api.gateway.attomdata.com/propertyapi/v1.0.0/property/id",
                params={"address":full_address},
                headers={"apikey":ATTOM_API_KEY,"Accept":"application/json"},
                timeout=30
            )
            if r.ok:
                prop=(r.json().get("property") or [None])[0] or {}
                loc=prop.get("location") or {}
                lat=loc.get("latitude"); lon=loc.get("longitude")
                if lat not in (None,"") and lon not in (None,""):
                    return {
                        "lat":float(lat),"lon":float(lon),
                        "attom_id":str((prop.get("identifier") or {}).get("attomId") or ""),
                        "source":"ATTOM"
                    }, None
        except Exception:
            pass

    # 2) U.S. Census Geocoder fallback. No extra API key required.
    try:
        cr=requests.get(
            "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress",
            params={
                "address":full_address,
                "benchmark":"Public_AR_Current",
                "vintage":"Current_Current",
                "format":"json"
            },
            timeout=30,
            headers={"User-Agent":"RS-Permanent-Lighting/1.0"}
        )
        if cr.ok:
            matches=((cr.json().get("result") or {}).get("addressMatches") or [])
            if matches:
                coords=matches[0].get("coordinates") or {}
                x=coords.get("x"); y=coords.get("y")
                if x not in (None,"") and y not in (None,""):
                    return {
                        "lat":float(y),"lon":float(x),
                        "attom_id":"",
                        "source":"US Census Geocoder",
                        "matched_address":matches[0].get("matchedAddress","")
                    }, None
    except Exception:
        pass

    return None, "Could not geocode this address with ATTOM or the U.S. Census geocoder."

def _haversine_m(lat1,lon1,lat2,lon2):
    r=6371008.8
    p1=math.radians(lat1); p2=math.radians(lat2)
    dp=math.radians(lat2-lat1); dl=math.radians(lon2-lon1)
    a=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*r*math.asin(math.sqrt(a))

def _bearing_deg(lat1,lon1,lat2,lon2):
    p1=math.radians(lat1); p2=math.radians(lat2); dl=math.radians(lon2-lon1)
    y=math.sin(dl)*math.cos(p2)
    x=math.cos(p1)*math.sin(p2)-math.sin(p1)*math.cos(p2)*math.cos(dl)
    return (math.degrees(math.atan2(y,x))+360)%360

def _angle_delta(a,b):
    return abs((a-b+180)%360-180)

def fetch_mapillary_photo_for_property(pid):
    p=get_property(pid)
    if not p:
        return False, "Property not found."
    if not MAPILLARY_ACCESS_TOKEN:
        return False, "MAPILLARY_ACCESS_TOKEN is not configured on Render."

    geo,err=_geocode_property(p)
    if err:
        return False, err
    lat,lon=geo["lat"],geo["lon"]
    radius=max(30,min(MAPILLARY_RADIUS_METERS,200))
    dlat=radius/111111.0
    dlon=radius/(111111.0*max(0.2,math.cos(math.radians(lat))))
    bbox=f"{lon-dlon},{lat-dlat},{lon+dlon},{lat+dlat}"
    fields="id,thumb_2048_url,thumb_1024_url,computed_geometry,captured_at,compass_angle,camera_type,creator"
    r=requests.get(
        "https://graph.mapillary.com/images",
        params={"access_token":MAPILLARY_ACCESS_TOKEN,"fields":fields,"bbox":bbox,"limit":80},
        timeout=35
    )
    if not r.ok:
        detail=""
        try: detail=(r.json().get("error") or {}).get("message","")
        except Exception: pass
        return False, f"Mapillary search failed ({r.status_code}){': '+detail if detail else ''}."

    candidates=[]
    for item in r.json().get("data",[]):
        geom=item.get("computed_geometry") or {}
        coords=geom.get("coordinates") or []
        if len(coords)<2: continue
        try:
            ilon,ilat=float(coords[0]),float(coords[1])
            dist=_haversine_m(lat,lon,ilat,ilon)
            if dist>radius*1.35: continue
            heading=float(item.get("compass_angle")) if item.get("compass_angle") is not None else None
            toward=_bearing_deg(ilat,ilon,lat,lon)
            angle=_angle_delta(heading,toward) if heading is not None else 90
            # Strongly prefer cameras aimed toward the parcel, then distance.
            score=dist + angle*1.25
            if angle>100: score+=180
            item["_distance"]=dist; item["_angle"]=angle; item["_score"]=score
            candidates.append(item)
        except Exception:
            continue

    if not candidates:
        return False, f"No Mapillary street-level images found within about {radius} meters."
    candidates.sort(key=lambda x:x["_score"])
    best=candidates[0]
    image_url=best.get("thumb_2048_url") or best.get("thumb_1024_url")
    if not image_url:
        # Thumbnail URLs can also be fetched from the image entity endpoint.
        ir=requests.get(
            f"https://graph.mapillary.com/{best['id']}",
            params={"access_token":MAPILLARY_ACCESS_TOKEN,"fields":"thumb_2048_url,thumb_1024_url,creator,captured_at"},
            timeout=25
        )
        if ir.ok:
            meta=ir.json(); image_url=meta.get("thumb_2048_url") or meta.get("thumb_1024_url")
            if meta.get("creator"): best["creator"]=meta["creator"]
    if not image_url:
        return False, "Mapillary found nearby imagery but did not return a usable thumbnail."

    img=requests.get(image_url,timeout=45)
    if not img.ok:
        return False, f"Mapillary image download failed ({img.status_code})."
    mime=img.headers.get("Content-Type","image/jpeg").split(";")[0]
    creator=best.get("creator") or {}
    if isinstance(creator,dict):
        username=creator.get("username") or creator.get("name") or ""
    else:
        username=str(creator or "")
    attribution=f"Mapillary image {best['id']}"
    if username: attribution+=f" by {username}"
    attribution+=" — CC BY-SA; attribution/share-alike requirements apply. Verify exact house before marketing use."
    c=db(); cur=c.cursor()
    cur.execute(
        "UPDATE properties SET original_image=%s,original_mime=%s,image_source=%s,image_license_ok=%s,status='READY_FOR_MOCKUP' WHERE id=%s",
        (img.content,mime,attribution,False,pid)
    )
    c.commit(); c.close()
    return True, f"Mapillary photo loaded from {best['_distance']:.0f} m away and camera angle checked. Verify this is the exact front exterior before generating the mockup."

def _kartaview_collect_photos(obj):
    out=[]
    def walk(x):
        if isinstance(x,dict):
            keys=set(x.keys())
            if ("lat" in keys and ("lng" in keys or "lon" in keys)) and any(k in keys for k in ("name","lth_name","th_name","photo","image")):
                out.append(x)
            for v in x.values(): walk(v)
        elif isinstance(x,list):
            for v in x: walk(v)
    walk(obj)
    return out

def _kartaview_url(v):
    if not v: return ""
    v=str(v)
    if v.startswith("http://") or v.startswith("https://"): return v
    return "https://api.openstreetcam.org/" + v.lstrip("/")

def fetch_kartaview_photo_for_property(pid):
    p=get_property(pid)
    if not p:
        return False, "Property not found."
    geo,err=_geocode_property(p)
    if err:
        return False, err
    lat,lon=geo["lat"],geo["lon"]
    radius=120
    try:
        r=requests.post(
            "https://api.openstreetcam.org/1.0/list/nearby-photos/",
            data={"lat":lat,"lng":lon,"radius":radius,"page":1,"ipp":100},
            timeout=35,
            headers={"User-Agent":"RS-Permanent-Lighting/1.0"}
        )
    except Exception as e:
        return False, f"KartaView request failed: {e}"
    if not r.ok:
        return False, f"KartaView search failed ({r.status_code})."
    try:
        payload=r.json()
    except Exception:
        return False, "KartaView returned an unreadable response."
    status=payload.get("status") if isinstance(payload,dict) else None
    if isinstance(status,dict):
        code=status.get("apiCode")
        if code not in (None,600,"600"):
            return False, f"KartaView API returned {code}: {status.get('apiMessage','request failed')}"

    photos=_kartaview_collect_photos(payload)
    candidates=[]
    for item in photos:
        try:
            ilat=float(item.get("lat"))
            ilon=float(item.get("lng",item.get("lon")))
            dist=_haversine_m(lat,lon,ilat,ilon)
            if dist>radius*1.4: continue
            heading=item.get("heading")
            heading=float(heading) if heading not in (None,"") else None
            toward=_bearing_deg(ilat,ilon,lat,lon)
            angle=_angle_delta(heading,toward) if heading is not None else 90
            score=dist + angle*1.1
            if angle>110: score+=150
            image_url=_kartaview_url(item.get("lth_name") or item.get("name") or item.get("th_name") or item.get("photo") or item.get("image"))
            if not image_url: continue
            candidates.append((score,dist,angle,item,image_url))
        except Exception:
            continue
    if not candidates:
        return False, f"No KartaView street-level images found within about {radius} meters."

    candidates.sort(key=lambda x:x[0])
    score,dist,angle,best,image_url=candidates[0]
    try:
        img=requests.get(image_url,timeout=45,headers={"User-Agent":"RS-Permanent-Lighting/1.0"},allow_redirects=True)
    except Exception as e:
        return False, f"KartaView image download failed: {e}"
    if not img.ok:
        return False, f"KartaView found imagery but image download failed ({img.status_code})."
    ctype=img.headers.get("Content-Type","image/jpeg")
    if "image" not in ctype.lower():
        return False, "KartaView returned a nearby record but not a usable image."
    mime=ctype.split(";")[0]
    photo_id=best.get("id","")
    user=best.get("user","")
    date=best.get("date_added","")
    attribution="KartaView/OpenStreetCam"
    if photo_id: attribution+=f" photo {photo_id}"
    if user: attribution+=f" by {user}"
    if date: attribution+=f" ({date})"
    attribution+=f"; {dist:.0f} m from property. Verify exact house and permitted marketing use before mailing."
    conn=db(); cur=conn.cursor()
    cur.execute(
        "UPDATE properties SET original_image=%s,original_mime=%s,image_source=%s,image_license_ok=%s,status='READY_FOR_MOCKUP' WHERE id=%s",
        (img.content,mime,attribution,False,pid)
    )
    conn.commit(); conn.close()
    return True, f"KartaView photo loaded from {dist:.0f} m away. Verify it is the exact front exterior before generating the mockup."

def _extract_photo_urls(obj):
    urls=[]
    def walk(x):
        if isinstance(x, dict):
            for k,v in x.items():
                key=str(k).lower()
                if isinstance(v,str) and v.startswith("http") and (
                    "image" in key or "photo" in key or
                    "listing-images.homejunction.com" in v or
                    v.lower().split("?")[0].endswith((".jpg",".jpeg",".png",".webp"))
                ):
                    urls.append(v)
                else:
                    walk(v)
        elif isinstance(x,list):
            for v in x: walk(v)
        elif isinstance(x,str) and x.startswith("http") and (
            "listing-images.homejunction.com" in x or
            x.lower().split("?")[0].endswith((".jpg",".jpeg",".png",".webp"))
        ):
            urls.append(x)
    walk(obj)
    dedup=[]
    for u in urls:
        if u not in dedup: dedup.append(u)
    return dedup

def fetch_attom_photo_for_property(pid):
    p=get_property(pid)
    if not p:
        return False, "Property not found."
    if not ATTOM_API_KEY:
        return False, "ATTOM_API_KEY is not configured on Render yet."

    full_address=f"{p['address']}, {p['city']}, {p['state']} {p['zip']}"
    # First validate/match the address with ATTOM property API.
    r=requests.get(
        "https://api.gateway.attomdata.com/propertyapi/v1.0.0/property/id",
        params={"address":full_address},
        headers={"apikey":ATTOM_API_KEY,"Accept":"application/json"},
        timeout=30
    )
    if not r.ok:
        return False, f"ATTOM address match failed ({r.status_code})."
    data=r.json()
    attom_id=""
    try:
        attom_id=str(data["property"][0]["identifier"]["attomId"])
    except Exception:
        pass

    # MLS/listing photos are separate ATTOM Slipstream data and require MLS licensing.
    if not ATTOM_SLIPSTREAM_URL or not ATTOM_SLIPSTREAM_TOKEN:
        note="ATTOM matched the address"
        if attom_id: note+=f" (ATTOM ID {attom_id})"
        note+=". Photo access still needs ATTOM Slipstream MLS credentials."
        c=db(); cur=c.cursor(); cur.execute("UPDATE properties SET image_source=%s WHERE id=%s",(note,pid)); c.commit(); c.close()
        return False, note

    headers={"Accept":"application/json", ATTOM_SLIPSTREAM_AUTH_HEADER:f"{ATTOM_SLIPSTREAM_AUTH_PREFIX}{ATTOM_SLIPSTREAM_TOKEN}"}
    params={"market":ATTOM_SLIPSTREAM_MARKET,"address":full_address}
    lr=requests.get(ATTOM_SLIPSTREAM_URL,params=params,headers=headers,timeout=45)
    if not lr.ok:
        return False, f"ATTOM Slipstream lookup failed ({lr.status_code}). Check your MLS/photo entitlement and credentials."

    urls=_extract_photo_urls(lr.json())
    if not urls:
        return False, "ATTOM matched the property but did not return a licensed listing photo for this address."

    # Prefer the first image returned by the listing feed; user must still visually verify the front exterior.
    ir=requests.get(urls[0],timeout=45)
    if not ir.ok:
        return False, "ATTOM returned a photo URL, but the image download failed."
    mime=ir.headers.get("Content-Type","image/jpeg").split(";")[0]
    c=db(); cur=c.cursor()
    cur.execute(
        "UPDATE properties SET original_image=%s,original_mime=%s,image_source=%s,image_license_ok=%s,status='READY_FOR_MOCKUP' WHERE id=%s",
        (ir.content,mime,"ATTOM Slipstream MLS photo",True,pid)
    )
    c.commit(); c.close()
    return True, "Licensed property photo fetched. Verify it is the correct front exterior before generating the AI mockup."

def auth_required(fn):
    @functools.wraps(fn)
    def wrapper(*a, **kw):
        if not ADMIN_PASSWORD:
            return fn(*a, **kw)
        auth = request.authorization
        if not auth or auth.username != ADMIN_USER or auth.password != ADMIN_PASSWORD:
            return Response("Authentication required", 401, {"WWW-Authenticate": 'Basic realm="RS Lighting Admin"'})
        return fn(*a, **kw)
    return wrapper

def get_property(pid):
    c=db(); cur=c.cursor(); cur.execute("SELECT * FROM properties WHERE id=%s",(pid,)); p=cur.fetchone(); c.close(); return p

BASE = """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }}</title>
<style>
:root{--blue:#075b8d;--dark:#073d5b;--green:#96be32;--bg:#f4f7f9;--line:#d9e3e8;--text:#17384a}
*{box-sizing:border-box}body{margin:0;font-family:Arial,Helvetica,sans-serif;background:var(--bg);color:var(--text)}
header{background:linear-gradient(135deg,var(--dark),var(--blue));color:white;padding:18px 22px;display:flex;justify-content:space-between;align-items:center;gap:12px}
header b{font-size:20px}header a{color:white;text-decoration:none}.wrap{max-width:1200px;margin:auto;padding:20px}.card{background:white;border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:16px}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}.stat strong{display:block;font-size:28px;color:var(--dark);margin-top:5px}
table{width:100%;border-collapse:collapse;background:white}th,td{padding:10px;border-bottom:1px solid var(--line);text-align:left;font-size:14px}th{background:#eaf1f4}
a.btn,button{display:inline-block;border:0;border-radius:8px;padding:10px 14px;background:var(--blue);color:white;text-decoration:none;font-weight:bold;cursor:pointer}.green{background:var(--green)!important;color:#17384a!important}.gray{background:#6f808a!important}
input,select,textarea{width:100%;padding:10px;border:1px solid #cfdbe1;border-radius:8px;font-size:15px;margin:5px 0 10px}label{font-size:13px;font-weight:bold}.thumb{width:100%;max-height:420px;object-fit:contain;background:#eef2f4;border-radius:10px}.badge{display:inline-block;padding:4px 8px;border-radius:99px;background:#edf2f4;font-size:12px}.muted{color:#6f808a;font-size:13px}
.flash{padding:10px;border-radius:8px;background:#e9f4d7;margin-bottom:12px}
@media(max-width:800px){.grid,.two{grid-template-columns:1fr 1fr}}@media(max-width:520px){.grid,.two{grid-template-columns:1fr}.wrap{padding:12px}}
</style></head><body>
<header><div><b>RS PERMANENT LIGHTING</b><div style="font-size:12px;opacity:.85">Personalized postcard campaign system</div></div><a href="/">Dashboard</a></header>
<div class="wrap">{% with msgs=get_flashed_messages() %}{% for m in msgs %}<div class="flash">{{m}}</div>{% endfor %}{% endwith %}{{ body|safe }}</div>
</body></html>
"""

def page(title, body, **ctx):
    inner = render_template_string(body, **ctx)
    return render_template_string(BASE, title=title, body=inner)

@app.get("/health")
def health():
    return {"ok": True, "service": "rs-permanent-lighting"}

@app.get("/")
@auth_required
def dashboard():
    c=db(); cur=c.cursor()
    cur.execute("SELECT id,address,city,state,zip,status,scans,mailed,quote_amount,(original_image IS NOT NULL) AS has_original,(mockup_image IS NOT NULL) AS has_mockup FROM properties ORDER BY id")
    rows=cur.fetchall()
    cur.execute("SELECT COUNT(*) n FROM leads"); leads=cur.fetchone()["n"]
    c.close()
    stats={
      "total":len(rows),"photos":sum(1 for r in rows if r["has_original"]),
      "mockups":sum(1 for r in rows if r["has_mockup"]),
      "approved":sum(1 for r in rows if r["status"]=="APPROVED"),
      "scans":sum(r["scans"] for r in rows),"leads":leads
    }
    body="""
    <div class="grid">
      <div class="card stat">Properties<strong>{{s.total}}</strong></div>
      <div class="card stat">Photos<strong>{{s.photos}}</strong></div>
      <div class="card stat">Mockups<strong>{{s.mockups}}</strong></div>
      <div class="card stat">Approved<strong>{{s.approved}}</strong></div>
      <div class="card stat">QR scans<strong>{{s.scans}}</strong></div>
      <div class="card stat">Leads<strong>{{s.leads}}</strong></div>
    </div>
    <div class="card"><div style="display:flex;justify-content:space-between;gap:10px;align-items:center;flex-wrap:wrap">
      <h2 style="margin:0">Canopy MLS target list</h2><div style="display:flex;gap:8px;flex-wrap:wrap"><a class="btn" href="/photo-queue">Needs photo queue</a><a class="btn green" href="/add">+ Add property</a></div>
    </div></div>
    <div class="card" style="overflow:auto;padding:0"><table><thead><tr><th>#</th><th>Address</th><th>Photo</th><th>Mockup</th><th>Status</th><th>Scans</th><th>Quote</th></tr></thead><tbody>
    {% for p in rows %}<tr><td>{{p.id}}</td><td><a href="/property/{{p.id}}"><b>{{p.address}}</b></a><br><span class="muted">{{p.city}}, {{p.state}} {{p.zip}}</span></td><td>{{"✓" if p.has_original else "—"}}</td><td>{{"✓" if p.has_mockup else "—"}}</td><td><span class="badge">{{p.status}}</span></td><td>{{p.scans}}</td><td>{{("$%.0f"|format(p.quote_amount)) if p.quote_amount else "—"}}</td></tr>{% endfor %}
    </tbody></table></div>
    """
    return page("RS Permanent Lighting",body,s=stats,rows=rows)

@app.get("/photo-queue")
@auth_required
def photo_queue():
    c=db(); cur=c.cursor()
    cur.execute("""SELECT id,address,city,state,zip,status,image_source
                   FROM properties
                   WHERE original_image IS NULL
                   ORDER BY id""")
    rows=cur.fetchall(); c.close()
    body="""
    <div class="card">
      <div style="display:flex;justify-content:space-between;gap:10px;align-items:center;flex-wrap:wrap">
        <div><h2 style="margin:0">Needs photo queue</h2><div class=muted>{{rows|length}} properties still need a usable real exterior photo.</div></div>
        <a class="btn gray" href="/">Back to dashboard</a>
      </div>
    </div>
    <div class="card" style="overflow:auto;padding:0">
      <table>
        <thead><tr><th>#</th><th>Property</th><th>Last result</th><th>Actions</th></tr></thead>
        <tbody>
        {% for p in rows %}
          <tr>
            <td>{{p.id}}</td>
            <td><a href="/property/{{p.id}}"><b>{{p.address}}</b></a><br><span class=muted>{{p.city}}, {{p.state}} {{p.zip}}</span></td>
            <td><span class=muted>{{p.image_source or "No source tried yet"}}</span></td>
            <td>
              <div style="display:flex;gap:6px;flex-wrap:wrap">
                <form method=post action="/property/{{p.id}}/mapillary"><button>Mapillary</button></form>
                <form method=post action="/property/{{p.id}}/kartaview"><button>KartaView</button></form>
                <a class="btn gray" href="/property/{{p.id}}/streetview" target="_blank">Street View verify</a>
                <a class="btn green" href="/property/{{p.id}}">Manual upload</a>
              </div>
            </td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
    """
    return page("Needs photo queue",body,rows=rows)

@app.route("/add",methods=["GET","POST"])
@auth_required
def add_property():
    if request.method=="POST":
        c=db(); cur=c.cursor()
        if DATABASE_URL:
            cur.execute("INSERT INTO properties(address,city,state,zip,owner_name,token) VALUES(%s,%s,%s,%s,%s,%s) RETURNING id",
              (request.form["address"].strip(),request.form.get("city","Charlotte"),request.form.get("state","NC"),request.form.get("zip","28278"),request.form.get("owner_name",""),secrets.token_urlsafe(10)))
            pid=cur.fetchone()["id"]
        else:
            cur.execute("INSERT INTO properties(address,city,state,zip,owner_name,token) VALUES(%s,%s,%s,%s,%s,%s)",
              (request.form["address"].strip(),request.form.get("city","Charlotte"),request.form.get("state","NC"),request.form.get("zip","28278"),request.form.get("owner_name",""),secrets.token_urlsafe(10)))
            pid=cur.cur.lastrowid
        c.commit(); c.close()
        ok,msg=fetch_attom_photo_for_property(pid)
        flash(msg)
        return redirect(url_for("property_detail",pid=pid))
    return page("Add property","""
    <div class="card"><h2>Add property</h2><form method=post>
    <label>Street address</label><input name=address required>
    <div class=two><div><label>City</label><input name=city value=Charlotte></div><div><label>State</label><input name=state value=NC></div></div>
    <div class=two><div><label>ZIP</label><input name=zip value=28278></div><div><label>Owner name (optional)</label><input name=owner_name></div></div>
    <button class=green>Add property</button></form></div>""")


@app.get("/property/<int:pid>/streetview")
@auth_required
def streetview_preview(pid):
    p=get_property(pid)
    if not p:
        return "Not found",404
    meta,err=streetview_metadata_for_property(p)
    if err:
        return page("Street View unavailable","<div class=card><h2>Street View</h2><p>{{msg}}</p><a class='btn' href='/property/{{pid}}'>Back</a></div>",msg=err,pid=pid)
    return page("Street View","""
    <div class=card>
      <h2 style="margin-top:0">Google Street View</h2>
      <img class=thumb src="/property/{{pid}}/streetview-image" alt="Google Street View for {{address}}">
      <p class=muted>Live Google Street View preview for verification only. It is not stored in the RS Permanent Lighting database.</p>
      <a class=btn href="/property/{{pid}}">Back to property</a>
    </div>
    """,pid=pid,address=p["address"])

@app.get("/property/<int:pid>/streetview-image")
@auth_required
def streetview_image(pid):
    p=get_property(pid)
    if not p:
        return "Not found",404
    meta,err=streetview_metadata_for_property(p)
    if err:
        return Response(err,404,mimetype="text/plain")
    location=f"{p['address']}, {p['city']}, {p['state']} {p['zip']}"
    # Stream directly from Google; do not persist or cache the imagery.
    r=requests.get(
        "https://maps.googleapis.com/maps/api/streetview",
        params={
            "size":"640x480",
            "location":location,
            "source":"outdoor",
            "fov":"90",
            "pitch":"0",
            "return_error_code":"true",
            "key":GOOGLE_MAPS_API_KEY
        },
        timeout=30
    )
    if not r.ok:
        return Response(f"Google Street View returned {r.status_code}.",r.status_code,mimetype="text/plain")
    return Response(
        r.content,
        mimetype=r.headers.get("Content-Type","image/jpeg"),
        headers={"Cache-Control":"no-store, max-age=0","Pragma":"no-cache"}
    )

@app.get("/media/<int:pid>/<kind>")
def media(pid,kind):
    if kind not in ("original","mockup"): return "Not found",404
    c=db(); cur=c.cursor()
    col="original_image" if kind=="original" else "mockup_image"
    mime="original_mime" if kind=="original" else "mockup_mime"
    cur.execute(f"SELECT {col} AS data,{mime} AS mime FROM properties WHERE id=%s",(pid,))
    r=cur.fetchone(); c.close()
    if not r or r["data"] is None: return "Not found",404
    return Response(bytes(r["data"]),mimetype=r["mime"] or "image/jpeg")

@app.route("/property/<int:pid>",methods=["GET","POST"])
@auth_required
def property_detail(pid):
    p=get_property(pid)
    if not p:return "Not found",404
    if request.method=="POST":
        action=request.form.get("action")
        c=db(); cur=c.cursor()
        try:
            if action in ("upload_original","upload_mockup"):
                f=request.files.get("image")
                if not f or not f.filename: raise ValueError("Choose an image first.")
                data=f.read()
                if len(data)>15*1024*1024: raise ValueError("Image must be under 15 MB.")
                if action=="upload_original":
                    cur.execute("UPDATE properties SET original_image=%s,original_mime=%s,status='READY_FOR_MOCKUP' WHERE id=%s",(data,f.mimetype,pid))
                else:
                    cur.execute("UPDATE properties SET mockup_image=%s,mockup_mime=%s,status='REVIEW' WHERE id=%s",(data,f.mimetype,pid))
            elif action=="save":
                cur.execute("""UPDATE properties SET status=%s,image_source=%s,image_license_ok=%s,est_linear_ft=%s,quote_amount=%s,mailed=%s WHERE id=%s""",
                    (request.form.get("status","PHOTO_NEEDED"),request.form.get("image_source",""),bool(request.form.get("image_license_ok")),
                     request.form.get("est_linear_ft") or 0,request.form.get("quote_amount") or 0,bool(request.form.get("mailed")),pid))
            c.commit()
            flash("Saved.")
        except Exception as e:
            c.rollback(); flash(str(e))
        finally:c.close()
        return redirect(url_for("property_detail",pid=pid))
    p=get_property(pid)
    base = PUBLIC_BASE_URL or request.url_root.rstrip("/")
    public_url=f"{base}/p/{p['token']}"
    body="""
    <div class="card"><h2 style="margin-bottom:4px">{{p.address}}</h2><div class=muted>{{p.city}}, {{p.state}} {{p.zip}} · {{p.status}}</div></div>
    <div class=two>
      <div class=card><h3>1. Real house photo</h3>
        {% if p.original_image %}<img class=thumb src="/media/{{p.id}}/original">{% else %}<p class=muted>No photo uploaded.</p>{% endif %}
        <div style="margin:12px 0;padding:12px;border:1px solid #d9e3e8;border-radius:10px;background:#f8fafb">
          <div style="display:flex;justify-content:space-between;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:8px">
            <b>Live Google Street View verification</b>
            <a class="btn gray" href="/property/{{p.id}}/streetview" target="_blank">Open larger</a>
          </div>
          <img class=thumb src="/property/{{p.id}}/streetview-image" alt="Google Street View preview for {{p.address}}" onerror="this.style.display='none';this.nextElementSibling.style.display='block'">
          <div class=muted style="display:none;padding:10px 0">Street View is unavailable or the Google API key is not authorized for this address.</div>
          <p class=muted style="margin-bottom:0">Live preview only for checking the exact house. The image is not stored in our database.</p>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin:10px 0">
          <form method=post action="/property/{{p.id}}/fetch-photo"><button class=green>Fetch licensed property photo</button></form>
          <form method=post action="/property/{{p.id}}/mapillary"><button>Try Mapillary photo</button></form>
          <form method=post action="/property/{{p.id}}/kartaview"><button>Try KartaView photo</button></form>
        </div>
        <p class=muted>The app automatically tries ATTOM after you add an address. This button retries the licensed-photo lookup.</p>
        <form method=post enctype=multipart/form-data><input type=hidden name=action value=upload_original><input type=file name=image accept="image/*" required><button>Upload real photo manually</button></form>
      </div>
      <div class=card><h3>2. Lighting mockup</h3>
        {% if p.mockup_image %}<img class=thumb src="/media/{{p.id}}/mockup">{% else %}<p class=muted>No mockup yet.</p>{% endif %}
        <form method=post enctype=multipart/form-data><input type=hidden name=action value=upload_mockup><input type=file name=image accept="image/*" required><button>Upload mockup</button></form>
        <form method=post action="/property/{{p.id}}/generate" style="margin-top:10px"><button class=green {% if not p.original_image %}disabled{% endif %}>Generate AI mockup</button></form>
      </div>
    </div>
    <div class=two>
      <div class=card><h3>3. Review + estimate</h3><form method=post><input type=hidden name=action value=save>
        <label>Status</label><select name=status>{% for st in ["PHOTO_NEEDED","READY_FOR_MOCKUP","REVIEW","APPROVED","REJECTED"] %}<option {% if p.status==st %}selected{% endif %}>{{st}}</option>{% endfor %}</select>
        <label>Image source / permission note</label><input name=image_source value="{{p.image_source}}">
        <label><input type=checkbox name=image_license_ok style="width:auto" {% if p.image_license_ok %}checked{% endif %}> I have permission/licensing for this marketing image</label><br><br>
        <label>Estimated linear feet</label><input type=number step=.1 min=0 name=est_linear_ft value="{{p.est_linear_ft}}">
        <label>Quote amount ($)</label><input type=number step=1 min=0 name=quote_amount value="{{p.quote_amount}}">
        <label><input type=checkbox name=mailed style="width:auto" {% if p.mailed %}checked{% endif %}> Mark postcard mailed</label><br><br>
        <button class=green>Save</button></form></div>
      <div class=card><h3>4. QR + postcard</h3>
        <img src="/qr/{{p.token}}.png" style="width:180px;height:180px"><p class=muted style="word-break:break-all">{{public_url}}</p>
        <a class=btn href="/postcard/{{p.id}}" target=_blank>Open 6×9 postcard</a>
      </div>
    </div>
    """
    return page(p["address"],body,p=p,public_url=public_url)


@app.post("/property/<int:pid>/fetch-photo")
@auth_required
def fetch_property_photo(pid):
    try:
        ok,msg=fetch_attom_photo_for_property(pid)
        flash(msg)
    except Exception as e:
        flash(f"Photo lookup error: {e}")
    return redirect(url_for("property_detail",pid=pid))

@app.post("/property/<int:pid>/mapillary")
@auth_required
def fetch_mapillary_photo(pid):
    try:
        ok,msg=fetch_mapillary_photo_for_property(pid)
        flash(msg)
    except Exception as e:
        flash(f"Mapillary lookup error: {e}")
    return redirect(url_for("property_detail",pid=pid))

@app.post("/property/<int:pid>/kartaview")
@auth_required
def fetch_kartaview_photo(pid):
    try:
        ok,msg=fetch_kartaview_photo_for_property(pid)
        flash(msg)
    except Exception as e:
        flash(f"KartaView lookup error: {e}")
    return redirect(url_for("property_detail",pid=pid))

@app.post("/property/<int:pid>/generate")
@auth_required
def generate_mockup(pid):
    p=get_property(pid)
    if not p or p["original_image"] is None:
        flash("Upload the real house photo first."); return redirect(url_for("property_detail",pid=pid))
    if not OPENAI_API_KEY:
        flash("OPENAI_API_KEY is not configured on Render."); return redirect(url_for("property_detail",pid=pid))
    prompt=("Edit this exact property photo. Preserve the house architecture, roof geometry, windows, driveway, landscaping and camera viewpoint. "
            "Turn the scene into realistic dusk and add professionally installed permanent warm-white LED lighting neatly following the visible roof eaves and gable lines. "
            "Do not redesign the house, add rooms, change roof shapes, or replace landscaping. The result must clearly remain the exact same property.")
    files={"image":("house.jpg",bytes(p["original_image"]),p["original_mime"] or "image/jpeg")}
    data={"model":OPENAI_IMAGE_MODEL,"prompt":prompt,"size":"1536x1024"}
    try:
        r=requests.post("https://api.openai.com/v1/images/edits",headers={"Authorization":f"Bearer {OPENAI_API_KEY}"},files=files,data=data,timeout=180)
        if not r.ok: raise RuntimeError(f"OpenAI returned {r.status_code}: {r.text[:500]}")
        item=r.json()["data"][0]
        if item.get("b64_json"):
            img=base64.b64decode(item["b64_json"])
        elif item.get("url"):
            img=requests.get(item["url"],timeout=90).content
        else:
            raise RuntimeError("No image returned.")
        c=db(); cur=c.cursor(); cur.execute("UPDATE properties SET mockup_image=%s,mockup_mime='image/png',status='REVIEW' WHERE id=%s",(img,pid)); c.commit(); c.close()
        flash("AI mockup generated. Check the architecture carefully before approving.")
    except Exception as e:
        flash(str(e))
    return redirect(url_for("property_detail",pid=pid))

@app.get("/qr/<token>.png")
def qr_png(token):
    c=db(); cur=c.cursor(); cur.execute("SELECT id FROM properties WHERE token=%s",(token,)); p=cur.fetchone(); c.close()
    if not p:return "Not found",404
    base=PUBLIC_BASE_URL or request.url_root.rstrip("/")
    img=qrcode.make(f"{base}/p/{token}")
    out=io.BytesIO(); img.save(out,format="PNG")
    return Response(out.getvalue(),mimetype="image/png")

@app.get("/p/<token>")
def public_property(token):
    c=db(); cur=c.cursor(); cur.execute("SELECT * FROM properties WHERE token=%s",(token,)); p=cur.fetchone()
    if not p: c.close(); return "Not found",404
    cur.execute("UPDATE properties SET scans=scans+1 WHERE id=%s",(p["id"],)); c.commit(); c.close()
    img_kind="mockup" if p["mockup_image"] is not None else "original"
    phone_digits="".join(ch for ch in BUSINESS_PHONE if ch.isdigit())
    estimate=float(p["quote_amount"] or 0)
    linear_ft=float(p["est_linear_ft"] or 0)
    return render_template_string("""
<!doctype html>
<html>
<head>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>{{biz}} | {{p.address}}</title>
<style>
:root{--blue:#075b8d;--dark:#073d5b;--green:#96be32;--bg:#f3f7f9;--text:#17384a;--line:#d9e3e8}
*{box-sizing:border-box}body{margin:0;font-family:Arial,Helvetica,sans-serif;background:var(--bg);color:var(--text)}
.hero{background:linear-gradient(135deg,var(--dark),var(--blue));color:white;padding:18px 18px 34px}
.wrap{max-width:900px;margin:auto}.brand{font-size:15px;font-weight:800;letter-spacing:.08em}.eyebrow{font-size:13px;opacity:.85;margin-top:26px}
h1{font-size:clamp(34px,7vw,62px);line-height:.98;margin:8px 0 12px}.green{color:#b7dc50}.hero p{font-size:18px;line-height:1.5;max-width:700px;margin:0}
.main{max-width:900px;margin:-20px auto 0;padding:0 16px 32px}.card{background:white;border:1px solid var(--line);border-radius:18px;padding:18px;margin:14px 0;box-shadow:0 8px 28px rgba(20,56,76,.08)}
.house{width:100%;max-height:560px;object-fit:cover;border-radius:14px;background:#e7eef2}.kicker{font-size:13px;text-transform:uppercase;letter-spacing:.08em;font-weight:bold;color:var(--blue)}
.price{font-size:38px;font-weight:800;color:var(--dark);margin:5px 0}.price small{font-size:15px;font-weight:normal;color:#647985}.subtle{color:#647985;font-size:13px;line-height:1.45}
.ctas{display:grid;grid-template-columns:2fr 1fr 1fr;gap:10px;margin-top:14px}.btn,button{display:flex;align-items:center;justify-content:center;text-decoration:none;border:0;border-radius:11px;padding:14px 14px;font-size:16px;font-weight:800;cursor:pointer}
.primary{background:var(--green);color:#17384a}.secondary{background:var(--blue);color:white}.dark{background:var(--dark);color:white}
.features{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.feature{padding:13px;border-radius:12px;background:#f4f8fa;font-size:14px;line-height:1.35}.feature b{display:block;margin-bottom:4px}
.offer{border:2px solid var(--green);background:#f7fbe9}.offer h2{margin:0 0 8px}
form{margin-top:10px}input,textarea{width:100%;box-sizing:border-box;padding:13px;margin:6px 0 10px;border:1px solid #cbd7dd;border-radius:9px;font-size:16px}textarea{min-height:88px}
.formgrid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.sticky{display:none}
@media(max-width:680px){.ctas{grid-template-columns:1fr 1fr}.ctas .primary{grid-column:1/-1}.features{grid-template-columns:1fr}.formgrid{grid-template-columns:1fr}.main{padding-bottom:88px}.sticky{display:grid;grid-template-columns:1fr 1fr;position:fixed;left:0;right:0;bottom:0;z-index:20;background:white;border-top:1px solid #d6e0e5;padding:9px;gap:8px}.sticky .btn{padding:13px 10px}.hero{padding-bottom:38px}}
</style>
</head>
<body>
<div class=hero><div class=wrap>
  <div class=brand>{{biz}}</div>
  <div class=eyebrow>PERSONALIZED DESIGN FOR {{p.address}}</div>
  <h1>THIS IS <span class=green>YOUR HOME.</span></h1>
  <p>See what permanent architectural lighting could look like on your property — installed once and ready for every season.</p>
</div></div>

<main class=main>
  <div class=card>
    {% if p.mockup_image or p.original_image %}
      <img class=house src="/media/{{p.id}}/{{kind}}" alt="Lighting visualization for {{p.address}}">
    {% else %}
      <div style="padding:55px 20px;text-align:center;background:#edf2f4;border-radius:14px">Your custom home visualization is being prepared.</div>
    {% endif %}
    <div style="padding-top:16px">
      <div class=kicker>Designed for {{p.address}}</div>
      {% if estimate > 0 %}
        <div class=price>{{"$%.0f"|format(estimate)}} <small>preliminary project estimate</small></div>
        <div class=subtle>Final price is confirmed after an on-site measurement and design review.{% if linear_ft > 0 %} Current estimate is based on approximately {{ "%.0f"|format(linear_ft) }} linear ft.{% endif %}</div>
      {% else %}
        <div class=price>Custom pricing <small>for this home</small></div>
        <div class=subtle>Request a free on-site measurement and we’ll confirm the exact lighting layout and price.</div>
      {% endif %}

      <div class=ctas>
        <a class="btn primary" href="#estimate">Book My Free Estimate</a>
        <a class="btn secondary" href="tel:+1{{phone_digits}}">Call</a>
        <a class="btn dark" href="sms:+1{{phone_digits}}?body=Hi%20RS%20Permanent%20Lighting%2C%20I%20received%20a%20postcard%20for%20{{p.address|urlencode}}">Text</a>
      </div>
    </div>
  </div>

  <div class=card>
    <div class=kicker>Why permanent lighting?</div>
    <h2 style="margin:7px 0 14px">One installation. Endless occasions.</h2>
    <div class=features>
      <div class=feature><b>Low-profile installation</b>Designed to blend into the home during the day.</div>
      <div class=feature><b>App-controlled colors</b>Warm white, holidays, game days and custom scenes.</div>
      <div class=feature><b>No more ladders</b>Leave seasonal hanging and removal behind.</div>
    </div>
  </div>

  <div class="card offer">
    <h2>See the exact price for your home</h2>
    <p style="margin:0">Your consultation includes an on-site measurement, lighting layout and exact installation price. Ask about available payment or financing options during your estimate.</p>
  </div>

  <div class=card id=estimate>
    <div class=kicker>Free estimate</div>
    <h2 style="margin:7px 0">Want this look on your home?</h2>
    <p class=subtle style="font-size:15px">Send us your details and we’ll contact you to confirm the design and exact price for {{p.address}}.</p>
    <form method=post action="/lead/{{p.token}}">
      <div class=formgrid>
        <div><input name=name placeholder="Your name" required></div>
        <div><input name=phone placeholder="Phone number" required></div>
      </div>
      <input type=email name=email placeholder="Email address">
      <textarea name=notes placeholder="Questions, preferred contact time, or anything we should know?"></textarea>
      <button class="btn primary" style="width:100%">Book My Free Estimate</button>
    </form>
    <p class=subtle style="text-align:center;margin-bottom:0">Or call/text {{phone}}.</p>
  </div>
</main>

<div class=sticky>
  <a class="btn secondary" href="tel:+1{{phone_digits}}">Call Now</a>
  <a class="btn primary" href="#estimate">Free Estimate</a>
</div>
</body></html>
""",biz=BUSINESS_NAME,p=p,kind=img_kind,phone=BUSINESS_PHONE,phone_digits=phone_digits,estimate=estimate,linear_ft=linear_ft)

@app.post("/lead/<token>")
def lead(token):
    c=db(); cur=c.cursor(); cur.execute("SELECT * FROM properties WHERE token=%s",(token,)); p=cur.fetchone()
    if not p: c.close(); return "Not found",404
    payload={"name":request.form.get("name",""),"phone":request.form.get("phone",""),"email":request.form.get("email",""),"notes":request.form.get("notes","")}
    cur.execute("INSERT INTO leads(property_id,name,phone,email,notes) VALUES(%s,%s,%s,%s,%s)",(p["id"],payload["name"],payload["phone"],payload["email"],payload["notes"])); c.commit(); c.close()
    if GHL_WEBHOOK_URL:
        try:
            requests.post(GHL_WEBHOOK_URL,json={"source":"RS Permanent Lighting postcard","property":p["address"],**payload},timeout=12)
        except Exception: pass
    return render_template_string("<!doctype html><meta name=viewport content='width=device-width,initial-scale=1'><body style='font-family:Arial;text-align:center;padding:50px'><h1>Thanks — your request is in.</h1><p>We will contact you shortly.</p></body>")

@app.get("/postcard/<int:pid>")
@auth_required
def postcard(pid):
    p=get_property(pid)
    if not p:return "Not found",404
    img_kind="mockup" if p["mockup_image"] is not None else "original"
    return render_template_string("""
<!doctype html><html><head><meta charset=utf-8><title>Postcard</title><style>
@page{size:9in 6in;margin:0}*{box-sizing:border-box}body{margin:0;font-family:Arial}.page{width:9in;height:6in;position:relative;overflow:hidden;page-break-after:always}.front{background:#073d5b;color:white}.photo{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}.shade{position:absolute;inset:0;background:linear-gradient(90deg,rgba(0,40,63,.88),rgba(0,0,0,.05) 62%,rgba(0,0,0,.35))}.brand{position:absolute;left:.35in;top:.32in;font-size:.22in;font-weight:bold}.headline{position:absolute;left:.35in;top:1.25in;font-size:.57in;font-weight:bold;line-height:.98;text-shadow:0 2px 4px #000}.headline span{color:#a3cc39}.sub{position:absolute;left:.38in;top:3.05in;font-size:.23in;line-height:1.45}.qrbox{position:absolute;right:.35in;bottom:.35in;background:white;color:#073d5b;border:4px solid #96be32;border-radius:14px;padding:.12in;width:2.55in;display:flex;gap:.12in;align-items:center}.qrbox img{width:1in;height:1in}.back{background:white;color:#073d5b;padding:.42in}.cols{display:grid;grid-template-columns:1.1fr .9fr;gap:.35in}.back h2{font-size:.42in;margin:.05in 0}.green{color:#88ae2c}ul{font-size:.2in;line-height:1.6}.mail{border:2px solid #dbe4e8;border-radius:12px;padding:.25in;margin-top:.25in;font-size:.2in}@media print{button{display:none}}</style></head>
<body>
<section class="page front">{% if p.mockup_image or p.original_image %}<img class=photo src="/media/{{p.id}}/{{kind}}">{% endif %}<div class=shade></div><div class=brand>RS PERMANENT LIGHTING</div><div class=headline>YES — THAT'S<br><span>YOUR</span> HOUSE.</div><div class=sub>Permanent lighting.<br>Installed once.<br>Ready for every season.</div><div class=qrbox><img src="/qr/{{p.token}}.png"><div><b>LOVE THE LOOK?</b><br>Scan for pricing<br><small>{{p.address}}</small></div></div></section>
<section class="page back"><div class=cols><div><h2>ONE INSTALLATION.<br><span class=green>ENDLESS OCCASIONS.</span></h2><ul><li>Custom design for your home</li><li>Low-profile permanent LED lighting</li><li>Control colors from your phone</li><li>Christmas, game day, Halloween & warm white</li><li>No more ladders or tangled lights</li></ul><p><b>We already designed this for your home.</b></p></div><div><h3>RS PERMANENT LIGHTING</h3><p>{{phone}}<br>{{website}}</p><div class=mail>LOCAL HOMEOWNER<br><br>{{p.address}}<br>{{p.city}}, {{p.state}} {{p.zip}}</div></div></div></section>
<script>setTimeout(()=>window.print(),600)</script></body></html>
""",p=p,kind=img_kind,phone=BUSINESS_PHONE,website=BUSINESS_WEBSITE)

with app.app_context():
    try:
        init_db()
    except Exception as e:
        print("Database initialization deferred:", e)

if __name__=="__main__":
    init_db()
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT","10000")))
