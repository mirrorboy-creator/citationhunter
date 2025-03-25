from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

def buscar_crossref(query):
    url = f"https://api.crossref.org/works?query={query}&rows=1"
    r = requests.get(url)
    if r.status_code != 200:
        return None
    items = r.json().get("message", {}).get("items", [])
    if not items:
        return None

    item = items[0]
    autor = item.get("author", [{}])[0].get("family", "Autor desconocido")
    anio = item.get("issued", {}).get("date-parts", [[None]])[0][0]
    titulo = item.get("title", ["Sin título"])[0]
    revista = item.get("container-title", ["Revista no especificada"])[0]
    doi = item.get("DOI", "")
    url_final = f"https://doi.org/{doi}" if doi else "URL no disponible"

    return f"{autor} ({anio}). *{titulo}*. *{revista}*. {url_final}"

def buscar_semanticscholar(query):
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit=1&fields=title,authors,year,url"
    r = requests.get(url)
    if r.status_code != 200:
        return None
    data = r.json().get("data", [])
    if not data:
        return None

    paper = data[0]
    autor = paper.get("authors", [{}])[
