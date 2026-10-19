"""
Pre-flight checks before writing gold_queries.py:
  1. How is paProgramDeclared stored? (string "true" / xsd:boolean / something else)
  2. How do hurricanes appear in FEMADisasterDeclaration?
     - distinct incidentType values
     - declarationTitle values that contain "hurricane"
"""
import pyoxigraph

store = pyoxigraph.Store()
store.load(path="data/texas_flood2.ttl", format=pyoxigraph.RdfFormat.TURTLE)

PREFIXES = """\
PREFIX kg:  <http://floodkg.org/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""

def run(sparql):
    result = store.query(PREFIXES + sparql)
    rows = []
    for sol in result:
        row = {v.value: sol[v] for v in result.variables}
        rows.append(row)
    return rows

# ── 1. paProgramDeclared raw term inspection ──────────────────────────────────
print("=== paProgramDeclared raw terms (first 5) ===")
rows = run("""
SELECT ?val
WHERE {
  ?cd a kg:CountyDesignation ;
      kg:paProgramDeclared ?val .
}
LIMIT 5
""")
for r in rows:
    term = r["val"]
    # show value, datatype, and Python type
    print(f"  value={term.value!r}  datatype={getattr(term, 'datatype', None)}  pytype={type(term).__name__}")

# ── 2. Distinct incidentType values on FEMADisasterDeclaration ───────────────
print("\n=== Distinct incidentType values ===")
rows = run("""
SELECT DISTINCT ?incidentType (COUNT(?decl) AS ?n)
WHERE {
  ?decl a kg:FEMADisasterDeclaration ;
        kg:incidentType ?incidentType .
}
GROUP BY ?incidentType
ORDER BY DESC(?n)
""")
for r in rows:
    print(f"  {r['incidentType'].value!r}  ({r['n'].value})")

# ── 3. declarationTitle values containing "hurricane" (case-insensitive) ─────
print("\n=== declarationTitle values containing 'hurricane' ===")
rows = run("""
SELECT ?disasterNumber ?declarationTitle ?incidentType
WHERE {
  ?decl a kg:FEMADisasterDeclaration ;
        kg:disasterNumber  ?disasterNumber ;
        kg:declarationTitle ?declarationTitle ;
        kg:incidentType     ?incidentType .
  FILTER(CONTAINS(LCASE(STR(?declarationTitle)), "hurricane"))
}
ORDER BY ?disasterNumber
""")
for r in rows:
    print(f"  #{r['disasterNumber'].value}  type={r['incidentType'].value!r}  title={r['declarationTitle'].value!r}")
