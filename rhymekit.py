#!/usr/bin/env python3
"""rhymekit.py — reference implementation of Artifacts A (algebra) + C (lane renderer).
Usage:
  python rhymekit.py                  # algebra self-demo
  python rhymekit.py r2.json out.svg  # render Artifact B (pseudoknot lane view)
"""
import json, itertools, colorsys, re, sys
from dataclasses import dataclass, field
from xml.sax.saxutils import escape
INF = 9.0

# ── feature tables ──────────────────────────────────────────────
VOW = {"IH":("HIGH","FRONT"),"IY":("HIGH","FRONT"),"EH":("MID","FRONT"),"AE":("LOW","FRONT"),
       "EY":("MID","FRONT"),"AA":("LOW","BACK"),"AO":("LOW","BACK"),"OW":("MID","BACK"),
       "UH":("HIGH","BACK"),"UW":("HIGH","BACK"),"ER":("MID","CENT"),"AH":("MID","CENT")}
HI = {"HIGH":0,"MID":1,"LOW":2}; BI = {"FRONT":0,"CENT":1,"BACK":2}
CC = {p:"stop" for p in "P B T D K G".split()} | {p:"fric" for p in "F V S Z TH DH SH ZH H".split()} \
   | {p:"nas" for p in "M N NG".split()} | {p:"aff" for p in "CH JH".split()} | {p:"approx" for p in "L R W Y".split()}
TIERS = ["PERF","FAM","ASSON","CONS","MOS","ORTHO","HOMO"]          # lattice in leq()
def leq(t1,t2):  # §A: PERF ≤ FAM ≤ {ASSON,CONS} ≤ ⊤
    return (t1,t2) in {("PERF","FAM"),("PERF","ASSON"),("PERF","CONS"),("FAM","ASSON"),("FAM","CONS")} or t1==t2

@dataclass
class Key:  nuc:str; coda:list; seq:list=field(default_factory=list); orth:str=""
@dataclass(eq=False)  # eq=False -> identity-based hash/eq; Site instances go in sets (curate()) by identity, not structural equality
class Site: id:str; key:Key; voice:str="v0"; layer:str="LOCAL"; tier:str="FAM"; t0:float=0.0; t1:float=0.0; latent:bool=False; group:str=None
@dataclass
class Group: id:str; tier:str; members:list; layer:str="LOCAL"; late:list=field(default_factory=list)
@dataclass
class Arc:  g:str; a:object; b:object; cross:bool=False; span:float=0.0

# ── P→S operators ───────────────────────────────────────────────
def vdist(a,b): return (VOW[a][0]!=VOW[b][0]) + (VOW[a][1]!=VOW[b][1])
def cdist(c1,c2):
    n = max(len(c1),len(c2))
    if not n: return 0.0
    d = 0.0
    for i in range(n):
        x, y = (c1[i] if i<len(c1) else None), (c2[i] if i<len(c2) else None)
        if x==y: continue
        d += 0.5 if (x and y and CC.get(x)==CC.get(y)) else 1.0
    return d/n
def edit(a,b):
    dp = list(range(len(b)+1))
    for i,ca in enumerate(a,1):
        prev = dp[:]; dp[0] = i
        for j,cb in enumerate(b,1):
            dp[j] = min(prev[j]+1, dp[j-1]+1, prev[j-1]+(ca!=cb))
    return dp[-1]
def D(t,k1,k2):                                   # proximity, §A (0=identical)
    if t=="PERF": return 0.0 if (k1.nuc==k2.nuc and k1.coda==k2.coda) else INF
    if t=="HOMO": return 0.0 if (k1.nuc==k2.nuc and k1.coda==k2.coda) else INF
    if t=="FAM" : return INF if k1.nuc!=k2.nuc else cdist(k1.coda,k2.coda)
    if t=="ASSON": return float(vdist(k1.nuc,k2.nuc))
    if t=="CONS": return cdist(k1.coda,k2.coda)
    if t=="MOS" : return 0.0 if (k1.seq and k1.seq==k2.seq) else (0.0 if k1.nuc==k2.nuc else 1.0)
    if t=="ORTHO": return edit(k1.orth,k2.orth)/max(len(k1.orth),len(k2.orth),1)
    return INF
TH = {"PERF":0.0,"FAM":0.5,"ASSON":1.0,"CONS":0.5,"MOS":0.0,"ORTHO":0.4,"HOMO":0.0}

def cluster(U,tier,th):                           # monotone; chain-coherence repair
    uf = {u.id:u.id for u in U}; comps = {u.id:[u] for u in U}
    def find(x):
        while uf[x]!=x: uf[x]=uf[uf[x]]; x=uf[x]
        return x
    edges = sorted(((D(tier,a.key,b.key),a.id,b.id)
                    for a,b in itertools.combinations(U,2)), key=lambda e:e[0])
    for d,a,b in edges:
        if d>th: break
        ra,rb = find(a),find(b)
        if ra==rb: continue
        merged = comps[ra]+comps[rb]
        diam = max((D(tier,x.key,y.key) for x,y in itertools.combinations(merged,2)), default=0)
        if diam <= 2*th:
            uf[ra]=rb; comps[rb]=merged; del comps[ra]
    return [Group(f"g{i}",tier,c) for i,c in enumerate(comps.values()) if len(c)>1]

def curate(cands, spine_ids):                     # the SECTION choice (§11)
    def sc(P):
        cov = len({s for g in P for s in g.members if s in spine_ids and len(g.members)>1})
        return (2*cov + 1*len(P) + sum(TIERS.index(g.tier) for g in P))
    return max(cands, key=sc)
def arcs_of(G):
    ms = sorted(G.members, key=lambda s:s.t0)
    return [Arc(G.id,a,b) for a,b in zip(ms,ms[1:])]
def crossp(pos,u,v):
    i,k,j,l = pos[u.a.id],pos[u.b.id],pos[v.a.id],pos[v.b.id]
    return i<j<k<l or j<i<l<k
def nest(arcs,pos):
    def depth(a):
        return 1+max((depth(b) for b in arcs
                      if pos[a.a.id]<pos[b.a.id]<pos[b.b.id]<pos[a.b.id]), default=0)
    return max((depth(a) for a in arcs), default=0)
def latency(g,t):
    f=[s for s in g.members if s.t0<=t]
    return (len(f)==1, t-f[0].t0 if f else 0.0)
def scheme_canon(sites,groups):                   # orbit rep under relabeling
    lab={}; out=[]
    gm={s.id:g.id for g in groups for s in g.members}
    for s in sorted(sites,key=lambda s:s.t0):
        if s.id in gm: out.append(lab.setdefault(gm[s.id],chr(97+len(lab))))
    return "CC." + "".join(out)
def meta(seq): return "CC." + "+".join(dict.fromkeys(re.sub(r"\d","n",s.split(".",1)[1]) for s in seq))
def embed(q):                                     # vowel lattice ↪ OKLCH-ish (§10.3)
    h,b = VOW.get(q,("MID","CENT"))
    hue = (190 - 70*BI[b] + 15*HI[h]) % 360
    r,g,bl = colorsys.hls_to_rgb(hue/360, 0.72-0.12*HI[h], 0.85)
    return "#%02X%02X%02X" % (int(r*255),int(g*255),int(bl*255))
def fingerprint(sites,arcs,pos,bars=1.8):
    X = sum(1 for u,v in itertools.combinations(arcs,2) if crossp(pos,u,v))
    return {"d":round(len(arcs)/max(len(sites),1),2),"X":X,"N":nest(arcs,pos),
            "L":round(max((abs(u.b.t0-u.a.t0) for u in arcs), default=0)/bars,1)}

# ── C: lane renderer (pseudoknot view) ──────────────────────────
LANES = ["SAMPLE","LOCAL","INTERNAL","ADLIB","ORTHO","SPINE"]
# NOTE: original mapping put gORT at "IH", same family as gSP -> hue
# collision, tripping the injectivity QA assert in render(). Fixed: gORT
# marks a homophone/ortho-divergence annotation (a spelling relation, not
# a vowel family) so it gets the palette's dedicated neutral gray instead
# of being forced onto the vowel-family hue scale.
GROUP_FAMILY = {"gOW":"OW","gSP":"IH","gEY":"EY","gMOS":"mosaic","gAE":"AE","gIY":"IY","gAA":"AA","gORT":"gray"}
def render(doc,out):
    S = {s["id"]:s for s in doc["sites"]}
    order = sorted(S.values(), key=lambda s:s["t0"]); pos = {s["id"]:i for i,s in enumerate(order)}
    G = {g["id"]:g for g in doc["groups"]}
    res = {e["g"]:e["t"] for e in doc.get("resolve_events",[])}
    late = {g["id"]:{lm["s"] for lm in g.get("latency",{}).get("late_members",[])} for g in doc["groups"]}
    pal = doc.get("palette",{})
    hue = lambda gid: pal.get(GROUP_FAMILY.get(gid,"IH"), embed(GROUP_FAMILY.get(gid,"IH")))
    arcs = [a for g in doc["groups"] for a in
            [ (lambda ms: [{"g":g["id"],"a":ms[i],"b":ms[i+1]} for i in range(len(ms)-1)] )
              (sorted(g["members"], key=lambda i:S[i]["t0"])) ][0] ] if False else \
           [ar for g in doc["groups"]
              for ms in [sorted(g["members"], key=lambda i:S[i]["t0"])]
              for ar in [{"g":g["id"],"a":ms[i],"b":ms[i+1]} for i in range(len(ms)-1)]]
    fp = fingerprint([Site(i,Key("IH",[])) for i in S],
                     [Arc(a["g"],Site(a["a"],Key("IH",[]),t0=S[a["a"]]["t0"]),
                            Site(a["b"],Key("IH",[]),t0=S[a["b"]]["t0"])) for a in arcs], pos)
    T = max(s["t1"] for s in S.values()); M=50; SC=70
    W = int(M*2+SC*T); LH=80; H = 90+LH*len(LANES)+70
    y = {ln:100+i*LH for i,ln in enumerate(LANES)}
    voff = {"v0":0,"v1":16,"v2":-16}
    lane_of = lambda g: G[g]["layer"].split("+")[0] if G[g]["layer"].split("+")[0] in LANES else "LOCAL"
    # Arc stacking (readability, crossings preserved). Rewritten: the
    # original hmap-keyed-by-(group,site_a) approach couldn't recover an
    # arc's second endpoint from the stored key alone (a real bug — see
    # docs/ARC_DIAGRAM_ARCHITECTURE.md), so overlap comparison here tracks
    # each placed arc's full (lane, xa, xb, height) instead.
    placed = []
    hmap = {}
    for a in sorted(arcs, key=lambda a: abs(S[a["b"]]["t0"] - S[a["a"]]["t0"]), reverse=True):
        xa, xb = S[a["a"]]["t0"], S[a["b"]]["t0"]; lane = lane_of(a["g"]); h = 1
        for (pl, pxa, pxb, ph) in placed:
            if pl == lane and pxa < xb and xa < pxb:
                h = max(h, ph + 1)
        placed.append((lane, xa, xb, h))
        hmap[(a["g"], a["a"])] = h
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="serif">',
         f'<rect width="{W}" height="{H}" fill="#C9C9C9"/>']
    for ln,yy in y.items():
        svg.append(f'<text x="8" y="{yy+4}" font-size="11" fill="#333">{ln}</text>')
    for p in doc["phrases"]:
        x0 = M+SC*next(s for s in doc["lines"] if s["id"]==p["lines"][0])["t0"]
        svg.append(f'<line x1="{x0}" y1="70" x2="{x0}" y2="{H-60}" stroke="#888" stroke-dasharray="2,4"/>')
        svg.append(f'<text x="{x0+4}" y="64" font-size="12" fill="#222">{p["id"]} · {escape(p["scheme"])}</text>')
    for a in arcs:                                       # arcs
        sa,sb = S[a["a"]],S[a["b"]]; lane=lane_of(a["g"])
        ya,yb = y[lane]+voff.get(sa.get("voice","v0"),0), y[lane]+voff.get(sb.get("voice","v0"),0)
        xa,xb = M+SC*sa["t0"], M+SC*sb["t0"]; h=hmap[(a["g"],a["a"])]*16
        g = G[a["g"]]
        dashed = (a["a"] in late[a["g"]] or a["b"] in late[a["g"]]) or \
                 ((sa.get("latent") or sb.get("latent")) and res.get(a["g"],INF) >= sb["t0"])
        dash = ' stroke-dasharray="5,4"' if dashed else ''
        svg.append(f'<path d="M {xa} {ya} C {xa} {ya-h}, {xb} {yb-h}, {xb} {yb}" fill="none" '
                   f'stroke="{hue(a["g"])}" stroke-width="2.5"{dash}><title>{escape(a["g"])} '
                   f'{escape(sa.get("chunk",""))}→{escape(sb.get("chunk",""))}</title></path>')
    sp = [s for s in order if any(s["id"] in g["members"] for g in doc["groups"] if g["id"]=="gSP")]
    if sp:                                               # spine baseline path
        pts = " ".join(f"{M+SC*s['t0']},{y['SPINE']}" for s in sp)
        svg.append(f'<polyline points="{pts}" fill="none" stroke="{hue("gSP")}" stroke-width="3.5" opacity="0.9"/>')
    for s in order:                                      # site dots + tooltips
        gid = next((g["id"] for g in doc["groups"] if s["id"] in g["members"]),None)
        if not gid: continue
        yy = y[lane_of(gid)]+voff.get(s.get("voice","v0"),0); xx = M+SC*s["t0"]
        svg.append(f'<circle cx="{xx}" cy="{yy}" r="4" fill="{hue(gid)}" stroke="#111"><title>'
                   f'{escape(s["id"])} {escape(s.get("chunk",""))} · {gid} · {s.get("layer","")}</title></circle>')
    lx = M
    for f,q in [("OW","OW"),("EY","EY"),("IH","IH"),("AE","AE"),("IY","IY"),("AA","AA")]:  # legend
        svg.append(f'<rect x="{lx}" y="{H-40}" width="14" height="14" fill="{pal.get(q,embed(q))}"/>')
        svg.append(f'<text x="{lx+18}" y="{H-29}" font-size="11">{f}</text>'); lx+=70
    svg.append(f'<text x="{M}" y="{H-8}" font-size="12">recomputed Φ = {fp} · Σ = '
               f'{escape(meta([p["scheme"] for p in doc["phrases"]]))} · X={fp["X"]} crossings</text>')
    svg.append('</svg>')
    open(out,"w").write("\n".join(svg))
    # QA invariants (§C6)
    assert len({hue(g) for g in G})==len(G), "hue collision"
    print("wrote",out,"| Φ:",fp,"| arcs:",len(arcs))

# ── self-demo + CLI ─────────────────────────────────────────────
if __name__=="__main__":
    K = lambda n,c,o="": Key(n,c,[],o)
    demo = [Site("tolerated",K("EY",["T","IH","D"])), Site("overrated",K("EY",["T","IH","D"])),
            Site("upgraded", K("EY",["D","IH","D"])), Site("painted", K("EY",["N","T","IH","D"])),
            Site("ate",      K("EY",["T"])),          Site("potato",  K("EY",["T","OW"])),
            Site("chips",    K("IH",["P","S"])),       Site("when",    K("IH",["N"])),
            Site("villainous",K("IH",["L","AH","N","IY","S"],"villainous")),
            Site("ill_in_us", K("IH",["L","AH","N","IY","S"],"ill in us"))]
    for t in ["PERF","FAM","ASSON","ORTHO"]:
        gs = cluster(demo,t,TH[t])
        print(f"{t:6s} ->", [[s.id for s in g.members] for g in gs])
    print("curate ->", [[s.id for s in g.members] for g in curate([cluster(demo,t,TH[t]) for t in TIERS[:4]], set())])
    print("scheme  ->", scheme_canon(demo, cluster(demo,"ASSON",1.0)))
    print("embed   ->", {q:embed(q) for q in ["IH","EY","AE","OW","AA"]})
    if len(sys.argv)==3: render(json.load(open(sys.argv[1])), sys.argv[2])
