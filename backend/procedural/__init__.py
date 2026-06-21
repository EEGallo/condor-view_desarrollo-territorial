"""Generación 3D procedural (CAPA 2).

Toma un PolygonContext (Capa 1) y genera un escenario de ocupación
normativamente válido (damero LOD1): calles → manzanas → lotes → masas 3D.
Cómputo en EPSG:5343, salida en EPSG:4326. Reusa backend.extraction.
"""
