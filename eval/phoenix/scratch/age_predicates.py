"""List every kg:County predicate whose local name starts with age_"""
import pyoxigraph

store = pyoxigraph.Store()
store.load(path="data/texas_flood2.ttl", format=pyoxigraph.RdfFormat.TURTLE)

SPARQL = """\
PREFIX kg:  <http://floodkg.org/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT DISTINCT ?p
WHERE {
  ?county a kg:County ;
          ?p ?o .
  FILTER(STRSTARTS(STR(?p), "http://floodkg.org/age_"))
}
ORDER BY ?p
"""

result = store.query(SPARQL)
for sol in result:
    print(sol["p"].value)
