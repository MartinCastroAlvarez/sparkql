import os
import json
import random
import urllib.parse
from SPARQLWrapper import SPARQLWrapper, JSON


PREFIXES: dict[str, str] = {
    "dbo": "<http://dbpedia.org/ontology/>",
    "dbp": "<http://dbpedia.org/property/>",
    "res": "<http://dbpedia.org/resource/Valencia>",
    "geo": "<http://www.w3.org/2003/01/geo/wgs84_pos#>",
    "foaf": "<http://xmlns.com/foaf/0.1/>",
    "dbr": "<http://dbpedia.org/resource/>",
    "rdfs": "<http://www.w3.org/2000/01/rdf-schema#>",
}


def dedent(s: str) -> str:
    return "\n".join([
        line.strip()
        for line in s.split("\n")
    ])


def send(query: str) -> list[dict]:
    sparql: SPARQLWrapper = SPARQLWrapper("http://dbpedia.org/sparql")
    sparql.setReturnFormat(JSON)
    for prefix in reversed(PREFIXES):
        query = f"PREFIX {prefix}: {PREFIXES[prefix]}\n{query}"
    query = dedent(query)
    sparql.setQuery(query)
    print(f"Query:\n{query}")
    response = sparql.query().convert()
    # print(f"Response:\n{json.dumps(response, indent=2, sort_keys=True)}")
    return [
        result
        for result in response.get("results", {}).get("bindings", [])
    ]


def test():

    output = "valencia.txt"
    if os.path.isfile(output):
        os.remove(output)

    query = """
        SELECT
            ?abstract
            ?website
            ?country
            ?zip
            ?areaTotal
            ?areaUrban
            ?population
            ?lat
            ?long
        WHERE {
            dbr:Valencia
                dbo:abstract            ?abstract       ;
                dbp:website             ?website        ;
                dbo:country             ?country        ;
                dbo:postalCode          ?zip            ;
                dbp:areaTotalKm         ?areaTotal      ;
                dbp:areaUrbanKm         ?areaUrban      ;
                dbo:populationTotal     ?population     ;
                geo:lat                 ?lat            ;
                geo:long                ?long           .
            FILTER (lang(?abstract) = 'es')
        }
    """
    details = send(query)
    assert details
    assert len(details) == 1
    details = details[0]

    query = """
        SELECT
            ?ref
        WHERE {
            dbr:Valencia foaf:depiction ?ref
        }
    """
    references = send(query)
    assert references

    query = """
        SELECT ?event WHERE {
            ?event dbo:location dbr:Valencia .
        }
    """
    locations = send(query)
    assert locations

    names = []
    location_samples = 3
    for location in random.sample(locations, location_samples):
        uri = location['event']['value']
        name = urllib.parse.quote(uri.split('resource/')[1], safe='')
        names.append(f"dbr:{name}")

    query = f"""
        SELECT
            (SAMPLE(?label) AS ?label)
            ?entity
            (SAMPLE(?abstract) AS ?abstract)
            (SAMPLE(?website) AS ?website)
            (SAMPLE(?date) AS ?date)
            (SAMPLE(?lat) AS ?lat)
            (SAMPLE(?long) AS ?log)
        WHERE {{
            VALUES ?entity {{ {' '.join(names)} }}
            OPTIONAL {{?entity dbo:abstract ?abstract . FILTER (lang(?abstract) = 'es')}}
            OPTIONAL {{?entity rdfs:label ?label}}
            OPTIONAL {{?entity foaf:homepage ?website}}
            OPTIONAL {{?entity dbo:startDate ?date}}
            OPTIONAL {{?entity dbo:lat ?lat}}
            OPTIONAL {{?entity dbo:long ?long}}
        }}
        GROUP BY ?entity
    """
    location_details = send(query)
    assert location_details
    assert len(location_details) == location_samples, len(location_details)

    with open(output, "w") as f:
        f.write("DETAILS:\n")
        for key, value in details.items():
            f.write(f"{key}: {value['value']}"[:300] + "\n")
        f.write("\n\n")
        f.write("IMAGES:\n")
        for reference in random.sample(references, 9):
            f.write(f" - {reference['ref']['value']}\n")
        f.write("\n\n")
        f.write("LOCATIONS:\n")
        for location in location_details:
            f.write("\n")
            for key, value in location.items():
                f.write(f"{key}: {value['value']}"[:300] + "\n")

if __name__ == "__main__":
    test()
