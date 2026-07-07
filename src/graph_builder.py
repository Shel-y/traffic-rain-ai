"""
Módulo: graph_builder

Responsabilidad:
    Descargar (o cargar de cache) el grafo de calles de las alcaldías
    seleccionadas de CDMX usando osmnx. Almacena localmente para no
    re-descargar en ejecuciones posteriores.

Zona: Coyoacán + Tlalpan (sur de CDMX)
Tipo de red: drive (calles transitables en auto)

Origen: Nuevo módulo (Fase 3.1)
"""

from pathlib import Path
from typing import List, Optional

import networkx as nx
import osmnx as ox


# ─── Configuración por defecto ───────────────────────────────────────────────

DEFAULT_PLACES = [
    "Coyoacán, Ciudad de México, México",
    "Tlalpan, Ciudad de México, México",
]

DEFAULT_NETWORK_TYPE = "drive"
DEFAULT_CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "graph"
DEFAULT_CACHE_FILENAME = "cdmx_coyoacan_tlalpan.graphml"


# ─── Funciones públicas ──────────────────────────────────────────────────────


def build_graph(
    places: Optional[List[str]] = None,
    network_type: str = DEFAULT_NETWORK_TYPE,
    cache_dir: Optional[Path] = None,
    cache_filename: str = DEFAULT_CACHE_FILENAME,
    force_download: bool = False,
) -> nx.MultiDiGraph:
    """
    Construye o carga de cache el grafo de calles.

    Parámetros
    ----------
    places : list[str] o None
        Nombres de las zonas a descargar de OSM.
        Si None, usa Coyoacán + Tlalpan.
    network_type : str
        Tipo de red ('drive', 'walk', 'bike', 'all').
    cache_dir : Path o None
        Directorio para almacenar el GraphML cacheado.
    cache_filename : str
        Nombre del archivo de cache.
    force_download : bool
        Si True, ignora el cache y re-descarga.

    Retorna
    -------
    nx.MultiDiGraph
        Grafo dirigido con atributos:
        - Nodos: osmid, x (lon), y (lat)
        - Aristas: length (metros), name, highway, etc.
    """
    if places is None:
        places = DEFAULT_PLACES
    if cache_dir is None:
        cache_dir = DEFAULT_CACHE_DIR

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / cache_filename

    # Intentar cargar de cache
    if cache_path.exists() and not force_download:
        print(f"  ✓ Cargando grafo desde cache: {cache_path}")
        G = ox.load_graphml(cache_path)
        _print_graph_stats(G)
        return G

    # Descargar de OpenStreetMap
    print(f"  ↓ Descargando grafo de calles desde OSM...")
    print(f"    Zonas: {places}")
    print(f"    Tipo de red: {network_type}")

    G = ox.graph_from_place(places, network_type=network_type)

    # Agregar velocidades y tiempos de recorrido estimados
    G = ox.routing.add_edge_speeds(G)
    G = ox.routing.add_edge_travel_times(G)

    # Guardar en cache
    ox.save_graphml(G, cache_path)
    print(f"  ✓ Grafo guardado en cache: {cache_path}")

    _print_graph_stats(G)
    return G


def get_nearest_node(G: nx.MultiDiGraph, lat: float, lon: float) -> int:
    """
    Encuentra el nodo del grafo más cercano a un punto (lat, lon).

    Retorna
    -------
    int
        ID del nodo más cercano (osmid).
    """
    return ox.nearest_nodes(G, X=lon, Y=lat)


def get_node_coordinates(G: nx.MultiDiGraph, node_id: int) -> tuple:
    """
    Obtiene las coordenadas (lat, lon) de un nodo.

    Retorna
    -------
    (lat, lon)
    """
    node_data = G.nodes[node_id]
    return (node_data["y"], node_data["x"])


# ─── Funciones auxiliares ────────────────────────────────────────────────────


def _print_graph_stats(G: nx.MultiDiGraph) -> None:
    """Imprime estadísticas básicas del grafo."""
    print(f"  📊 Estadísticas del grafo:")
    print(f"     Nodos: {G.number_of_nodes():,}")
    print(f"     Aristas: {G.number_of_edges():,}")

    # Calcular extensión geográfica
    nodes_data = G.nodes(data=True)
    lats = [d["y"] for _, d in nodes_data]
    lons = [d["x"] for _, d in nodes_data]
    print(f"     Lat: [{min(lats):.3f}, {max(lats):.3f}]")
    print(f"     Lon: [{min(lons):.3f}, {max(lons):.3f}]")
