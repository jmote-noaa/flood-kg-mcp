"""Introspect the KG: list all classes, and all predicates per class."""
import json
import pyoxigraph

store = pyoxigraph.Store()
store.load(path="data/texas_flood2.ttl", format=pyoxigraph.RdfFormat.TURTLE)

PREFIXES = """\
PREFIX kg:    <http://floodkg.org/>
PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd:   <http://www.w3.org/2001/XMLSchema#>
"""

def q(sparql):
    result = store.query(PREFIXES + sparql)
    rows = []
    for sol in result:
        row = {v.value: (sol[v].value if sol[v] is not None else None)
               for v in result.variables}
        rows.append(row)
    return rows

# --- Classes ---
print("=== CLASSES ===")
classes = q("""
SELECT ?class (COUNT(DISTINCT ?s) AS ?cnt)
WHERE { ?s rdf:type ?class }
GROUP BY ?class ORDER BY DESC(?cnt)
""")
for c in classes:
    print(f"  {c['class']}  ({c['cnt']})")

# --- Predicates per class ---
for cls_row in classes:
    cls_uri = cls_row['class']
    print(f"\n=== PREDICATES for <{cls_uri}> ===")
    preds = q(f"""
SELECT DISTINCT ?p
WHERE {{
  ?s rdf:type <{cls_uri}> ;
     ?p ?o .
}}
ORDER BY ?p
""")
    for p in preds:
        print(f"  {p['p']}")

# --- Sample NWSHazardProduct to check phenomenon values ---
print("\n=== SAMPLE NWSHazardProduct (phenomenon + significance) ===")
samples = q("""
SELECT DISTINCT ?phenomenon ?significance
WHERE {
  ?w a kg:NWSHazardProduct ;
     kg:phenomenon ?phenomenon ;
     kg:significance ?significance .
}
LIMIT 10
""")
for s in samples:
    print(f"  phenomenon={s['phenomenon']}  significance={s['significance']}")

# --- Sample FEMADisasterDeclaration properties ---
print("\n=== SAMPLE FEMADisasterDeclaration props (first 3 instances) ===")
sample_fema = q("""
SELECT ?decl ?p ?o
WHERE {
  ?decl a kg:FEMADisasterDeclaration ;
        ?p ?o .
}
LIMIT 40
""")
for row in sample_fema:
    print(f"  {row['p']}  =  {row['o'][:80] if row['o'] else None}")

# --- Check CountyDesignation predicates ---
print("\n=== SAMPLE CountyDesignation props ===")
sample_cd = q("""
SELECT DISTINCT ?p
WHERE {
  ?cd a kg:CountyDesignation ;
      ?p ?o .
}
""")
for row in sample_cd:
    print(f"  {row['p']}")

# --- Check programDeclared / iaProgramDeclared etc ---
print("\n=== PA program check on FEMADisasterDeclaration ===")
pa_check = q("""
SELECT ?p (COUNT(?s) AS ?cnt)
WHERE {
  ?s a kg:FEMADisasterDeclaration ;
     ?p ?o .
  FILTER(CONTAINS(LCASE(STR(?p)), "program"))
}
GROUP BY ?p
""")
for row in pa_check:
    print(f"  {row['p']}  ({row['cnt']})")

# --- Check broadband / internet predicate names ---
print("\n=== broadband / internet predicates on County ===")
bb_check = q("""
SELECT DISTINCT ?p
WHERE {
  ?county a kg:County ;
          ?p ?o .
  FILTER(CONTAINS(LCASE(STR(?p)), "broad") || CONTAINS(LCASE(STR(?p)), "internet"))
}
""")
for row in bb_check:
    print(f"  {row['p']}")

# --- Check poverty predicates ---
print("\n=== poverty predicates on County ===")
pov = q("""
SELECT DISTINCT ?p
WHERE {
  ?county a kg:County ;
          ?p ?o .
  FILTER(CONTAINS(LCASE(STR(?p)), "poverty"))
}
""")
for row in pov:
    print(f"  {row['p']}")

# --- Sample warningDurationHours ---
print("\n=== warningDurationHours sample (FF phenomenon) ===")
dur = q("""
SELECT ?dur
WHERE {
  ?w a kg:NWSHazardProduct ;
     kg:phenomenon "FF" ;
     kg:warningDurationHours ?dur .
}
LIMIT 5
""")
for row in dur:
    print(f"  {row['dur']}")

print("\nDone.")
