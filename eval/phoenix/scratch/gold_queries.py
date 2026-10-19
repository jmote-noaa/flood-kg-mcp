"""
Gold SPARQL queries for the Texas Flood KG evaluation dataset.
Run with: uv run python eval/phoenix/scratch/gold_queries.py

Pre-flight checks confirmed:
  - paProgramDeclared stored as xsd:integer 1/0; every designation has all four flags
  - iaProgramDeclared is 0 for all designations in this graph
  - incidentType="Hurricane" (capital H) for hurricane declarations; one instance (#4798)
  - NWSHazardProduct: only phenomenon=FF exists (1350 instances)
  - elderly_share: sum all six 65+ bands per updated schema_prototype2.yml
"""
import pyoxigraph

store = pyoxigraph.Store()
store.load(path="data/texas_flood2.ttl", format=pyoxigraph.RdfFormat.TURTLE)

PREFIXES = """\
PREFIX kg:    <http://floodkg.org/>
PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd:   <http://www.w3.org/2001/XMLSchema#>
"""


def run_select(sparql):
    result = store.query(PREFIXES + sparql)
    rows = []
    for sol in result:
        row = {v.value: (sol[v].value if sol[v] is not None else None)
               for v in result.variables}
        rows.append(row)
    return rows


def show(label, sparql, rows, note=None):
    print(f"\n{'='*72}")
    print(f"  {label}")
    print(f"{'='*72}")
    print("SPARQL:")
    for line in sparql.strip().splitlines():
        print(f"  {line}")
    print(f"\nResult ({len(rows)} row{'s' if len(rows) != 1 else ''}):")
    for r in rows:
        print("  " + " | ".join(f"{k}={v}" for k, v in r.items()))
    if note:
        print(f"\nNote: {note}")


# ─────────────────────────────────────────────────────────────────────────────
# Q1. How many flood events are in the graph?
# ─────────────────────────────────────────────────────────────────────────────
q1 = """
SELECT (COUNT(DISTINCT ?event) AS ?floodEventCount)
WHERE {
  ?event a kg:FloodEvent .
}
"""
show("Q1. How many flood events are in the graph?", q1, run_select(q1))


# ─────────────────────────────────────────────────────────────────────────────
# Q2. Which declarations included Public Assistance?
# paProgramDeclared is on CountyDesignation as xsd:integer 1 (confirmed).
# Surfacing distinct FEMADisasterDeclarations with at least one PA county.
# ─────────────────────────────────────────────────────────────────────────────
q2 = """
SELECT DISTINCT ?disasterNumber ?declarationTitle ?declarationDate
WHERE {
  ?cd a kg:CountyDesignation ;
      kg:paProgramDeclared 1 ;
      kg:forDeclaration ?decl .
  ?decl kg:disasterNumber   ?disasterNumber ;
        kg:declarationTitle ?declarationTitle ;
        kg:declarationDate  ?declarationDate .
}
ORDER BY ?disasterNumber
"""
show("Q2. Which declarations included Public Assistance?", q2, run_select(q2))


# ─────────────────────────────────────────────────────────────────────────────
# Q3. Which counties have the highest broadband access rates?
# broadband_access_rate = broadband_subscription / internet_access
# (formula from kg://schema analytical_concepts)
# ─────────────────────────────────────────────────────────────────────────────
q3 = """
SELECT ?countyName
       (xsd:decimal(?bb) / xsd:decimal(?ia) AS ?broadbandAccessRate)
WHERE {
  ?county a kg:County ;
          kg:countyName             ?countyName ;
          kg:broadband_subscription ?bb ;
          kg:internet_access        ?ia .
  FILTER(xsd:decimal(?ia) > 0)
}
ORDER BY DESC(xsd:decimal(?bb) / xsd:decimal(?ia))
LIMIT 10
"""
show("Q3. Which counties have the highest broadband access rates?", q3, run_select(q3))


# ─────────────────────────────────────────────────────────────────────────────
# Q4. Which declarations were associated with hurricanes?
# incidentType="Hurricane" (capital H, confirmed by pre_checks.py).
# ─────────────────────────────────────────────────────────────────────────────
q4 = """
SELECT ?disasterNumber ?declarationTitle ?declarationDate
       ?incidentBeginDate ?incidentEndDate
WHERE {
  ?decl a kg:FEMADisasterDeclaration ;
        kg:incidentType      "Hurricane" ;
        kg:disasterNumber    ?disasterNumber ;
        kg:declarationTitle  ?declarationTitle ;
        kg:declarationDate   ?declarationDate ;
        kg:incidentBeginDate ?incidentBeginDate ;
        kg:incidentEndDate   ?incidentEndDate .
}
ORDER BY ?disasterNumber
"""
show("Q4. Which declarations were associated with hurricanes?", q4, run_select(q4))


# ─────────────────────────────────────────────────────────────────────────────
# Q5. Which FEMA-designated counties have the highest poverty rates?
# poverty_rate = poverty_below / poverty_universe (kg://schema)
# Restricted to counties that appear in at least one CountyDesignation.
# ─────────────────────────────────────────────────────────────────────────────
q5 = """
SELECT DISTINCT ?countyName
       (xsd:decimal(?pb) / xsd:decimal(?pu) AS ?povertyRate)
WHERE {
  ?cd a kg:CountyDesignation ;
      kg:forCounty ?county .
  ?county kg:countyName      ?countyName ;
          kg:poverty_below   ?pb ;
          kg:poverty_universe ?pu .
  FILTER(xsd:decimal(?pu) > 0)
}
ORDER BY DESC(xsd:decimal(?pb) / xsd:decimal(?pu))
LIMIT 10
"""
show("Q5. Which FEMA-designated counties have the highest poverty rates?", q5, run_select(q5))


# ─────────────────────────────────────────────────────────────────────────────
# Q6. Which counties received NWS flood warnings AND also had FEMA disaster
#     declarations? Cross-dataset join through shared County entity.
# ─────────────────────────────────────────────────────────────────────────────
q6 = """
SELECT DISTINCT ?countyName
WHERE {
  ?w  a kg:NWSHazardProduct ;
      kg:coversCounty ?county .
  ?cd a kg:CountyDesignation ;
      kg:forCounty ?county .
  ?county kg:countyName ?countyName .
}
ORDER BY ?countyName
"""
show(
    "Q6. Which counties received NWS flood warnings AND FEMA disaster declarations?",
    q6, run_select(q6),
)


# ─────────────────────────────────────────────────────────────────────────────
# Q7. Which counties are most vulnerable to flooding?
# Per kg://schema vulnerability construct + guidelines: generate a SEPARATE
# ranked query for each primary indicator. Never combine into a composite index.
# Primary indicators: poverty_rate, elderly_share, mobile_home_share,
#                     vehicle_access_deficit.
# ─────────────────────────────────────────────────────────────────────────────

# Q7a — poverty_rate top-5
q7a = """
SELECT ?countyName
       (xsd:decimal(?pb) / xsd:decimal(?pu) AS ?povertyRate)
WHERE {
  ?county a kg:County ;
          kg:countyName      ?countyName ;
          kg:poverty_below   ?pb ;
          kg:poverty_universe ?pu .
  FILTER(xsd:decimal(?pu) > 0)
}
ORDER BY DESC(xsd:decimal(?pb) / xsd:decimal(?pu))
LIMIT 5
"""
show("Q7a. Vulnerability — poverty_rate (top 5)", q7a, run_select(q7a))

# Q7b — elderly_share top-5
# Sum all six 65+ bands per updated schema_prototype2.yml.
q7b = """
SELECT ?countyName
       ((xsd:decimal(?e65m)  + xsd:decimal(?e65f)
       + xsd:decimal(?e67m)  + xsd:decimal(?e67f)
       + xsd:decimal(?e70m)  + xsd:decimal(?e70f)
       + xsd:decimal(?e75m)  + xsd:decimal(?e75f)
       + xsd:decimal(?e80m)  + xsd:decimal(?e80f)
       + xsd:decimal(?e85m)  + xsd:decimal(?e85f))
       / xsd:decimal(?pop) AS ?elderlyShare)
WHERE {
  ?county a kg:County ;
          kg:countyName        ?countyName ;
          kg:age_65_66_male    ?e65m ;
          kg:age_65_66_female  ?e65f ;
          kg:age_67_69_male    ?e67m ;
          kg:age_67_69_female  ?e67f ;
          kg:age_70_74_male    ?e70m ;
          kg:age_70_74_female  ?e70f ;
          kg:age_75_79_male    ?e75m ;
          kg:age_75_79_female  ?e75f ;
          kg:age_80_84_male    ?e80m ;
          kg:age_80_84_female  ?e80f ;
          kg:age_85plus_male   ?e85m ;
          kg:age_85plus_female ?e85f ;
          kg:pop_total         ?pop .
  FILTER(xsd:decimal(?pop) > 0)
}
ORDER BY DESC((xsd:decimal(?e65m)  + xsd:decimal(?e65f)
             + xsd:decimal(?e67m)  + xsd:decimal(?e67f)
             + xsd:decimal(?e70m)  + xsd:decimal(?e70f)
             + xsd:decimal(?e75m)  + xsd:decimal(?e75f)
             + xsd:decimal(?e80m)  + xsd:decimal(?e80f)
             + xsd:decimal(?e85m)  + xsd:decimal(?e85f))
            / xsd:decimal(?pop))
LIMIT 5
"""
show("Q7b. Vulnerability — elderly_share, all 65+ bands (top 5)", q7b, run_select(q7b))

# Q7c — mobile_home_share top-5
q7c = """
SELECT ?countyName
       (xsd:decimal(?mh) / xsd:decimal(?hu) AS ?mobileHomeShare)
WHERE {
  ?county a kg:County ;
          kg:countyName          ?countyName ;
          kg:housing_mobile_home  ?mh ;
          kg:housing_units_total  ?hu .
  FILTER(xsd:decimal(?hu) > 0)
}
ORDER BY DESC(xsd:decimal(?mh) / xsd:decimal(?hu))
LIMIT 5
"""
show("Q7c. Vulnerability — mobile_home_share (top 5)", q7c, run_select(q7c))

# Q7d — vehicle_access_deficit top-5
q7d = """
SELECT ?countyName
       (xsd:decimal(?v0) / (xsd:decimal(?v0) + xsd:decimal(?v1) + xsd:decimal(?v2p))
        AS ?vehicleAccessDeficit)
WHERE {
  ?county a kg:County ;
          kg:countyName    ?countyName ;
          kg:vehicle_0     ?v0 ;
          kg:vehicle_1     ?v1 ;
          kg:vehicle_2plus ?v2p .
  FILTER((xsd:decimal(?v0) + xsd:decimal(?v1) + xsd:decimal(?v2p)) > 0)
}
ORDER BY DESC(xsd:decimal(?v0) / (xsd:decimal(?v0) + xsd:decimal(?v1) + xsd:decimal(?v2p)))
LIMIT 5
"""
show("Q7d. Vulnerability — vehicle_access_deficit (top 5)", q7d, run_select(q7d))


# ─────────────────────────────────────────────────────────────────────────────
# Q8. What is the average duration of NWS flash flood warnings?
# warningDurationHours stored as xsd:decimal; all 1350 NWSHazardProducts
# are phenomenon=FF (confirmed by introspection).
# ─────────────────────────────────────────────────────────────────────────────
q8 = """
SELECT (AVG(xsd:decimal(?dur)) AS ?avgDurationHours)
WHERE {
  ?w a kg:NWSHazardProduct ;
     kg:phenomenon           "FF" ;
     kg:warningDurationHours  ?dur .
}
"""
show("Q8. What is the average duration of NWS flash flood warnings?", q8, run_select(q8))


print("\n" + "="*72)
print("  Q9  (refusal)      — composite flood resilience score — no query")
print("  Q10 (out-of-scope) — NFIP claims in Harris County    — no query")
print("="*72)
