"""Check whether undeclared program flags are stored as 0 or simply absent."""
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

flags = ["iaProgramDeclared", "ihProgramDeclared", "paProgramDeclared", "hmProgramDeclared"]

for flag in flags:
    rows = run(f"""
SELECT ?val (COUNT(?cd) AS ?n)
WHERE {{
  ?cd a kg:CountyDesignation ;
      kg:{ flag } ?val .
}}
GROUP BY ?val
ORDER BY ?val
""")
    print(f"\n=== {flag} ===")
    if rows:
        for r in rows:
            term = r["val"]
            print(f"  value={term.value!r}  datatype={getattr(term,'datatype',None)}  count={r['n'].value}")
    else:
        print("  (no triples — predicate never present)")

    # Also count how many CountyDesignations lack the predicate entirely
    absent = run(f"""
SELECT (COUNT(?cd) AS ?absent)
WHERE {{
  ?cd a kg:CountyDesignation .
  FILTER NOT EXISTS {{ ?cd kg:{flag} ?v }}
}}
""")
    print(f"  absent (no triple at all): {absent[0]['absent'].value}")
