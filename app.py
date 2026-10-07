import os, io, csv, base64, secrets, functools, html
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

SANCTUARY = [
"13702 Sage Thrasher Ln","13400 Sage Thrasher Ln","10310 Wildlife Rd","10220 Wildlife Rd",
"10412 Wildlife Rd","10320 Wildlife Rd","9208 Flying Eagle Ln","9214 Flying Eagle Ln",
"9105 Island Point Rd","9044 Island Point Rd","10535 Island Point Rd","10530 Sweetleaf Pl",
"10300 Sweetleaf Pl","10424 Sweetleaf Pl","10500 Sweetleaf Pl","12627 Ninebark Trl",
"12835 Ninebark Trl","13105 Ninebark Trl","10723 Green Heron Ct","10915 Hermit Thrush Ln"
]

def db():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

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
        for a in SANCTUARY:
            cur.execute(
                "INSERT INTO properties(address,city,state,zip,token) VALUES(%s,%s,%s,%s,%s)",
                (a,"Charlotte","NC","28278",secrets.token_urlsafe(10))
            )
    c.commit(); c.close()

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
      <h2 style="margin:0">The Sanctuary pilot</h2><a class="btn green" href="/add">+ Add property</a>
    </div></div>
    <div class="card" style="overflow:auto;padding:0"><table><thead><tr><th>#</th><th>Address</th><th>Photo</th><th>Mockup</th><th>Status</th><th>Scans</th><th>Quote</th></tr></thead><tbody>
    {% for p in rows %}<tr><td>{{p.id}}</td><td><a href="/property/{{p.id}}"><b>{{p.address}}</b></a><br><span class="muted">{{p.city}}, {{p.state}} {{p.zip}}</span></td><td>{{"✓" if p.has_original else "—"}}</td><td>{{"✓" if p.has_mockup else "—"}}</td><td><span class="badge">{{p.status}}</span></td><td>{{p.scans}}</td><td>{{("$%.0f"|format(p.quote_amount)) if p.quote_amount else "—"}}</td></tr>{% endfor %}
    </tbody></table></div>
    """
    return page("RS Permanent Lighting",body,s=stats,rows=rows)

@app.route("/add",methods=["GET","POST"])
@auth_required
def add_property():
    if request.method=="POST":
        c=db(); cur=c.cursor()
        cur.execute("INSERT INTO properties(address,city,state,zip,owner_name,token) VALUES(%s,%s,%s,%s,%s,%s) RETURNING id",
          (request.form["address"].strip(),request.form.get("city","Charlotte"),request.form.get("state","NC"),request.form.get("zip","28278"),request.form.get("owner_name",""),secrets.token_urlsafe(10)))
        pid=cur.fetchone()["id"]; c.commit(); c.close()
        return redirect(url_for("property_detail",pid=pid))
    return page("Add property","""
    <div class="card"><h2>Add property</h2><form method=post>
    <label>Street address</label><input name=address required>
    <div class=two><div><label>City</label><input name=city value=Charlotte></div><div><label>State</label><input name=state value=NC></div></div>
    <div class=two><div><label>ZIP</label><input name=zip value=28278></div><div><label>Owner name (optional)</label><input name=owner_name></div></div>
    <button class=green>Add property</button></form></div>""")

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
                    cur.execute("UPDATE properties SET original_image=%s,original_mime=%s,status='READY_FOR_MOCKUP' WHERE id=%s",(psycopg2.Binary(data),f.mimetype,pid))
                else:
                    cur.execute("UPDATE properties SET mockup_image=%s,mockup_mime=%s,status='REVIEW' WHERE id=%s",(psycopg2.Binary(data),f.mimetype,pid))
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
        <form method=post enctype=multipart/form-data><input type=hidden name=action value=upload_original><input type=file name=image accept="image/*" required><button>Upload real photo</button></form>
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
        c=db(); cur=c.cursor(); cur.execute("UPDATE properties SET mockup_image=%s,mockup_mime='image/png',status='REVIEW' WHERE id=%s",(psycopg2.Binary(img),pid)); c.commit(); c.close()
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
    return render_template_string("""
<!doctype html><html><head><meta name=viewport content="width=device-width,initial-scale=1"><title>{{biz}}</title>
<style>body{margin:0;font-family:Arial;background:#f2f6f8;color:#14384c}.hero{background:#075b8d;color:white;padding:28px 20px}.wrap{max-width:850px;margin:auto;padding:18px}.card{background:white;border-radius:16px;padding:18px;margin:15px 0}img{width:100%;border-radius:12px}input,textarea{width:100%;box-sizing:border-box;padding:12px;margin:6px 0 12px;border:1px solid #ced9df;border-radius:8px;font-size:16px}button{background:#96be32;border:0;border-radius:9px;padding:13px 18px;font-size:17px;font-weight:bold;color:#17384a}</style></head>
<body><div class=hero><div class=wrap><b>{{biz}}</b><h1>See your home in a whole new light.</h1><p>Permanent architectural lighting designed for {{p.address}}.</p></div></div>
<div class=wrap><div class=card>{% if p.mockup_image or p.original_image %}<img src="/media/{{p.id}}/{{kind}}">{% endif %}<h2>Get pricing for this home</h2>
<form method=post action="/lead/{{p.token}}"><input name=name placeholder="Name" required><input name=phone placeholder="Phone" required><input type=email name=email placeholder="Email"><textarea name=notes placeholder="Anything we should know?"></textarea><button>Request my estimate</button></form><p>{{phone}}</p></div></div></body></html>
""",biz=BUSINESS_NAME,p=p,kind=img_kind,phone=BUSINESS_PHONE)

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
