"""Q3 (lowest broadband) and Q6 (count) verification with tie check."""
import pyoxigraph

store = pyoxigraph.Store()
store.load(path="data/texas_flood2.ttl", format=pyoxigraph.RdfFormat.TURTLE)

PREFIXES = """\
PREFIX kg:    <http://floodkg.org/>
PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX xsd:   <http://www.w3.org/2001/XMLSchema#>
"""

def run(sparql):
    result = store.query(PREFIXES + sparql)
    rows = []
    for sol in result:
        row = {v.value: (sol[v].value if sol[v] is not None else None)
               for v in result.variables}
        rows.append(row)
    return rows

# ── Q3: lowest broadband access rate, top 10 ascending ───────────────────────
print("=== Q3. Lowest broadband access rates (LIMIT 10) ===")
q3_low = """
SELECT ?countyName
       (xsd:decimal(?bb) / xsd:decimal(?ia) AS ?broadbandAccessRate)
WHERE {
  ?county a kg:County ;
          kg:countyName             ?countyName ;
          kg:broadband_subscription ?bb ;
          kg:internet_access        ?ia .
  FILTER(xsd:decimal(?ia) > 0)
}
ORDER BY ASC(xsd:decimal(?bb) / xsd:decimal(?ia))
LIMIT 10
"""
for r in run(q3_low):
    print(f"  {r['countyName']}  rate={r['broadbandAccessRate']}")

# Tie check: what is the rate at rank 10, and how many counties share it?
print("\n=== Q3 tie check: rate at rank 10 ===")
q3_rank10 = """
SELECT ?countyName
       (xsd:decimal(?bb) / xsd:decimal(?ia) AS ?broadbandAccessRate)
WHERE {
  ?county a kg:County ;
          kg:countyName             ?countyName ;
          kg:broadband_subscription ?bb ;
          kg:internet_access        ?ia .
  FILTER(xsd:decimal(?ia) > 0)
}
ORDER BY ASC(xsd:decimal(?bb) / xsd:decimal(?ia))
LIMIT 15
"""
rows_15 = run(q3_rank10)
rate_10 = rows_15[9]['broadbandAccessRate']
print(f"  Rate at rank 10: {rate_10}")
ties = [r for r in rows_15 if r['broadbandAccessRate'] == rate_10]
print(f"  Counties sharing that rate (within top 15): {len(ties)}")
for t in ties:
    print(f"    {t['countyName']}  {t['broadbandAccessRate']}")

# ── Q6: count of counties with both NWS warnings AND FEMA declarations ────────
print("\n=== Q6. Count of counties with NWS warnings AND FEMA declarations ===")
q6_count = """
SELECT (COUNT(DISTINCT ?county) AS ?countyCount)
WHERE {
  ?w  a kg:NWSHazardProduct ;
      kg:coversCounty ?county .
  ?cd a kg:CountyDesignation ;
      kg:forCounty ?county .
}
"""
for r in run(q6_count):
    print(f"  countyCount={r['countyCount']}")
