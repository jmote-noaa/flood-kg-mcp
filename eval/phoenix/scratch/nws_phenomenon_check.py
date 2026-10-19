"""Quick check: NWSHazardProduct instances grouped by phenomenon."""
import pyoxigraph

store = pyoxigraph.Store()
store.load(path="data/texas_flood2.ttl", format=pyoxigraph.RdfFormat.TURTLE)

SPARQL = """\
PREFIX kg:  <http://floodkg.org/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?ph (COUNT(?w) AS ?n)
WHERE {
  ?w a kg:NWSHazardProduct .
  OPTIONAL { ?w kg:phenomenon ?ph }
}
GROUP BY ?ph
"""

result = store.query(SPARQL)
for sol in result:
    ph = sol["ph"]
    n  = sol["n"]
    print(f"phenomenon={ph.value if ph else 'UNBOUND':<6}  count={n.value}")
