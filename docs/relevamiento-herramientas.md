# Relevamiento de herramientas de inteligencia territorial y planificación urbana

**Objetivo:** Validar el rumbo de **Cóndor View** — un mapa web que puntúa zonas de un territorio por potencial de desarrollo (IAT 0–100) y permite simular intervenciones (colocar una ruta/infraestructura hipotética y ver qué se desbloquea), orientado a la toma de decisión pública (intendentes, municipios, organismos provinciales).

**Fecha del relevamiento:** junio 2026.
**Método:** búsqueda web multi-fuente y verificación de afirmaciones contra fuentes oficiales (producto, documentación, reviews). Las fuentes están citadas al pie de cada sección y consolidadas al final.

---

## Resumen ejecutivo (TL;DR)

1. **El nicho exacto de Cóndor View está vacío en LatAm.** Ninguna de las plataformas de catastro/IDE de la región (IDECOR, IDE Mendoza, IGN, IDE Chile, INDE Brasil, ICDE Colombia) ofrece *scoring de potencial de desarrollo* ni *simulación what-if* empaquetada. Son visores y catálogos de datos; IDECOR es la única con analítica real (valuación masiva con IA), pero se detiene en mapas descriptivos.
2. **El producto dedicado de "scenario planning" de ESRI (ArcGIS GeoPlanner) está siendo discontinuado** (versión ArcGIS Online retirada en julio 2025; Enterprise se retira en diciembre 2026). ESRI dispersó esa capacidad en su plataforma, encareciéndola.
3. **Los simuladores serios (ArcGIS Urban, UrbanSim, UrbanFootprint, Replica) son caros, opacos en precio, y/o exigen calibración de años y datos masivos US-only** — sobredimensionados para un municipio chico.
4. **La capacidad más directa para "¿qué desbloquea una ruta nueva?" es open-source y combinable:** isócronas/accesibilidad con OSRM o R5/r5r (Conveyal) alimentando un score multicriterio (MCDA/AHP). Ese es exactamente el camino técnico de Cóndor View, y es defendible.
5. **Cóndor View se posiciona como el "tier 0" gratuito, explicable y sin backend** que ninguno de los grandes cubre: instantáneo, auditable, en español y con un simulador de intervención que los visores LatAm no tienen y los grandes esconden tras licencias caras.

---

## 1. Tabla comparativa de herramientas

| Herramienta | Qué hace | Usuario objetivo | ¿Simula escenarios/intervenciones? | Open-source / pago | Fortalezas | Debilidades |
|---|---|---|---|---|---|---|
| **ArcGIS Urban** (ESRI) | Planificación urbana 3D: convierte zonificación en volúmenes 3D, diseña y compara escenarios de desarrollo, gemelos digitales | Urbanistas, agencias de gobierno, consultoras | **Sí** (núcleo): dibuja edificios, ajusta FAR/altura/retiros, compara what-if lado a lado, mide capacidad. *No* predice uso del suelo/tráfico/economía en el tiempo | Pago. Desde jun-2025 sólo en el tier "Professional Plus"; requiere suscripción ArcGIS Online/Enterprise | 3D de zonificación líder; comparación de escenarios; integración con la plataforma ESRI | Curva de aprendizaje fuerte; subió de precio para equipos chicos; recomendado < ~50.000 parcelas; precio opaco |
| **ArcGIS GeoPlanner** (ESRI) | Geodiseño: análisis de aptitud por *weighted overlay* + comparación de alternativas con KPIs | Planificadores, gobierno | **Sí** (históricamente) | Pago. **En retiro**: ArcGIS Online retirado jul-2025; Enterprise se retira dic-2026 | Era el producto de aptitud + escenarios de ESRI | Prácticamente indisponible para nuevos usuarios; deja un hueco en la línea ESRI |
| **ArcGIS Hub** (ESRI) | Portal de datos abiertos + participación ciudadana (low-code) | Gobierno, ONGs, educación | No | Freemium dentro de ArcGIS (Basic incluido; Premium extra) | Bueno para portales de datos abiertos y engagement | No es herramienta de planificación ni simulación |
| **UrbanSim** (cloud, UrbanSim Inc.) | Microsimulación de uso del suelo + transporte + economía para evaluar planes regionales | Inmobiliarias, urbanistas, MPOs | **Sí** (predictivo fuerte): población, empleo, uso del suelo, viajes bajo distintos escenarios | SaaS propietario, precio no público | Más riguroso econométricamente; feedback uso-suelo/transporte; usado en metros 100k–9.6M hab | Calibración multianual; alta exigencia de datos; sobredimensionado para un municipio |
| **UrbanSim** (lib. open-source, UDST) | Librería Python para modelar uso del suelo/demografía | Agencias, consultoras, investigadores | Sí (modelado estadístico) | **Open-source** (BSD-3 / MIT) | Gratis, rigor académico, núcleo abierto | Estancada (v3.2, 2020); requiere Python + estadística + datos calibrados |
| **UrbanFootprint** | Plataforma SaaS de "decision intelligence": integra miles de datasets para evaluar uso del suelo, vivienda, transporte, clima, equidad a escala parcela | Planificadores, agencias, consultoras, utilities, banca | **Sí**: compara escenarios actuales/futuros, ajusta supuestos de políticas (eficiencia, flota, emisiones) | SaaS propietario, precio no público | Viene pre-cargado con datos nacionales (160M parcelas) → poca preparación local; bajo umbral GIS | **Datos solo de EE.UU.** (inusable fuera de US); precio opaco; débil en valor fiscal por acre |
| **Replica** | Analítica de movilidad: datos sintéticos de viajes validados + modelo de demanda de viajes nacional | Agencias públicas (MPOs, DOTs, ciudades) | **Sí** ("Replica Scenario"): el cliente provee proyecciones (cierres, cambios de red/uso del suelo) y re-corre el modelo | SaaS propietario, precio no público | Sin recolección local de datos; demografía de viajes rica out-of-the-box | **Datos solo de EE.UU.**; enfocado en transporte (no desarrollo ni fiscal); precio enterprise opaco |
| **Urban3** | Consultoría de economía del valor del suelo: visualiza "valor por acre", cost-of-service, impacto fiscal de escenarios | Municipios, gobiernos locales, desarrollo económico | **Sí**, pero como **análisis de consultoría entregado**, no auto-servicio | **Consultoría a medida** (no producto), precio por proyecto | Responde "¿este desarrollo se paga solo?"; visuales 3D para concejos no técnicos; usa datos que la ciudad ya tiene | No es software propio; depende de la calidad contable de la ciudad; no se re-corre sin re-contratar |
| **CommunityViz / Scenario 360** (City Explained / Texas A&M) | DSS de what-if, build-out y aptitud como extensión de ArcGIS Desktop | Planificadores de gobierno regional/local; transporte | **Sí** (fuerte): motor dinámico, 100+ indicadores, "Suitability Wizard" con re-ponderación | Propietario (pago); requiere ArcGIS Desktop pago | Maduro (desde 2001), 90+ funciones, flujo GIS+planificación | Atado a ArcGIS Desktop viejo (10.5–10.8); alta exigencia GIS; no es web |
| **Online What if?** (Klosterman) | PSS web: aptitud + demanda + asignación de uso del suelo para construir/comparar escenarios | Funcionarios, grupos de interés, ciudadanos (participativo) | **Sí**: smart-growth vs sprawl vs preservación | **Open-source** (la versión online) | Diseñado para participación pública; lógica transparente; 20+ años de trayectoria | Asignación por zona/grilla gruesa; sin accesibilidad de red; mantenimiento limitado |
| **Envision Tomorrow** | Paquete de "pintar escenarios" para planificación regional, sobre ArcGIS + planillas Excel | Comunidades, planificadores, factibilidad | **Sí**: pinta escenarios y compara en tiempo real; fuerte en pro-forma financiera | **Gratis y open-source** (pero requiere ArcGIS pago) | Gratis; lógica de planillas transparente; fuerte en factibilidad/fiscal | Nivel "sketch"; depende de ArcGIS propietario; cálculo en planillas (frágil) |
| **Conveyal Analysis + R5 / r5r** | Motor de ruteo multimodal + accesibilidad por oportunidades acumuladas; lo más directo para "qué desbloquea una ruta/línea" | Planificadores de transporte, agencias, investigadores | **Sí, lo mejor en su clase**: aplica "parches" a la red y recalcula accesibilidad/isócronas antes vs después | **R5 open-source (MIT)**; `r5r` (R) open-source; Conveyal hosted es SaaS pago | Cuantifica el cambio de accesibilidad por infraestructura; scriptable en pipeline | Auto-hosteo "a tu riesgo" (sin soporte, API no estable); pesado en Java/memoria; necesita GTFS+OSM |
| **OSRM / osrm-isochrone** | Motor de ruteo open-source sobre OSM; genera isócronas (polígonos de tiempo de viaje) | Desarrolladores de apps de accesibilidad | **Sí** para rutas nuevas: editás el grafo OSM y re-corrés isócronas | **Open-source** | Gratis, auto-hosteable, **red editable** (ideal para "ruta hipotética"), sub-segundo | Sin transporte público nativo; operás la infraestructura vos |
| **Mapbox Isochrone API** | API hosteada de polígonos de tiempo de viaje | Desarrolladores web | Limitado: usa la red viva de Mapbox, difícil agregar rutas hipotéticas | Pago (free tier + por request) | Trivial de integrar, sin infra | No modela rutas hipotéticas fácil; máx 4 contornos/60 min/100 km; pago a escala |
| **MCDA / AHP / Weighted Overlay** | *Método* (no producto) para puntuar potencial combinando criterios ponderados | Analistas GIS, planificadores | Sí, vía capa de proximidad/tiempo que se regenera tras una intervención | **Método libre** (QGIS, GDAL, Python `rasterio`/`numpy`, GRASS `r.mcda`) | Transparente, auditable, falsable; pesos explícitos y testeables | Estático (sin dinámica de mercado); sensible a la elección de pesos |
| **IDECOR** (Córdoba, AR) | IDE provincial; geoportal MapasCordoba; valuación masiva con IA y mapas de valor de la tierra | Ministerios, 42+ municipios, academia, sector privado, público | **No** (sin scoring compuesto ni simulación). Tiene mapa de "tierra vacante por manzana" (descriptivo) | **Datos abiertos** (consultables, descargables, geoservicios/API) | Valuación abierta líder; fuerte adopción municipal; analítica real (AVM/ML) | Es plataforma de datos+valuación; sin modelado prospectivo ni scoring |
| **IDERA** (nacional AR) | Comunidad/marco nacional de interoperabilidad de datos espaciales (estándares OGC) | Gobierno, academia, privados | No | Open-data | Columna vertebral de estandarización nacional | No es herramienta de decisión de usuario final |
| **IGN / Argenmap** (nacional AR) | Geoportal y visor nacional; WMS/WFS, base cartográfica, MDE | Gobierno, GIS, público | No | Open (Argenmap open-source) | Datos base autoritativos | Visor de referencia; sin analítica |
| **IDE Mendoza + Catastro ATM** | IDE provincial + catastro (físico/legal/económico), NSIT | Gobierno provincial/municipal | No | Infraestructura de gobierno | Modernización activa ("catastro multipropósito", reorg. feb-2025) | Sin scoring ni simulación pública; menos maduro analíticamente que Córdoba |
| **IDE Chile / INDE Brasil / ICDE Colombia / IDEuy** | IDEs nacionales: catálogos y visores; ICDE corre un Observatorio Inmobiliario | Instituciones públicas, academia, ciudadanos | No (salvo observatorios de valor, descriptivos) | Open-data | Catálogos coordinados; precedente de "valor" (observatorios) | Visores/descarga; sin modelado de decisión |
| **UN-Habitat — UPDL / Our City Plans / PAT / CityRAP** | Asistencia técnica + toolkits metodológicos participativos | Gobiernos local/regional/nacional | No (asesoría y metodología, no software de simulación) | Servicio / toolkits gratuitos | Implementación a medida, credibilidad ONU, integra lo legal/financiero | Consultoría/PDFs, no auto-servicio; depende de fondos y capacidad local |
| **UN-Habitat — UMF / City Prosperity Index** | Marco de monitoreo: 100+ indicadores en 6 dimensiones; benchmarking de ciudades | Autoridades urbanas, stakeholders nacionales | No (diagnóstico/benchmark, no simulación) | Datos abiertos (Urban Indicators DB) | Benchmark comparable internacionalmente, alineado a ODS | Retrospectivo; datos pesados; cifras de cobertura inconsistentes entre páginas |
| **World Bank — City Planning Labs** (Indonesia; Urban Performance) | Infraestructura de datos + 3 herramientas; "Urban Performance" crea escenarios de crecimiento con inversiones/políticas/regulación | Gobiernos locales y nacionales | **Sí** (Urban Performance): el caso más claro de simulación de escenarios entre las opciones internacionales | Licencia no clara; desarrollado con consultora (CAPSUS) bajo fondos del Banco Mundial | Simulación prospectiva ligada a inversiones/políticas; adopción municipal probada | Open-source/licencia no clara; atado al programa de Indonesia; portabilidad no documentada |

---

## 2. Qué features de decisión pública / simulación / visualización tienen las mejores

Cruzando las herramientas más fuertes, los patrones que aportan valor real a la decisión pública son:

### a) Simulación "what-if" comparable lado a lado
- **ArcGIS Urban** y **CommunityViz** permiten construir varios escenarios y compararlos en paralelo (capacidad, volumen edificable, indicadores). La decisión no es "¿cuánto vale esta zona hoy?" sino "¿cómo cambia si hago X?".
- **Conveyal/R5** es el patrón más directo para infraestructura: aplica "parches" a la red de transporte y **recalcula la accesibilidad antes/después** (isócronas + oportunidades alcanzables: empleos, población, servicios). Es exactamente el motor conceptual de "¿qué desbloquea una ruta nueva?".
- **World Bank Urban Performance** modela escenarios de crecimiento que incorporan **proyectos de inversión, políticas públicas y regulación del suelo** — no sólo geometría.

### b) Scoring de aptitud/potencial transparente y re-ponderable
- **GeoPlanner** (en retiro) y **CommunityViz Suitability Wizard** usan *weighted overlay*: el usuario pondera criterios y ve el resultado actualizarse. La transparencia del peso es la clave de la confianza.
- El método **MCDA/AHP** es el estándar académico falsable para "potencial de desarrollo": cada criterio (pendiente, proximidad a rutas, riesgo hídrico, zonificación) puntúa en una escala común y se combina con pesos explícitos y testeables por análisis de sensibilidad.

### c) Visualización del valor económico / fiscal de la decisión
- **Urban3** traduce el análisis a la pregunta que un intendente entiende: **"¿esta zona/desarrollo genera más de lo que cuesta en servicios?"** y lo muestra en 3D para concejos no técnicos. Es el puente entre el mapa y el presupuesto municipal.
- **IDECOR** demuestra que el **valor de la tierra abierto** (AVM/ML, $/m² por manzana) es un insumo creíble y políticamente potente en contexto argentino.

### d) Benchmarking e indicadores comparables
- **City Prosperity Index** ofrece un marco de 100+ indicadores en 6 dimensiones para ubicar dónde está débil una ciudad y "identificar áreas potenciales de intervención" — diagnóstico, no simulación, pero útil para el relato de política.

### e) Apertura de datos + geoservicios interoperables
- **IDECOR**, **IGN/Argenmap** e **IDERA** muestran que en LatAm el estándar es abrir datos vía geoservicios OGC. Construir *sobre* esos servicios (en vez de competir con ellos) da legitimidad y reduce el costo de datos.

### f) Participación y explicabilidad para audiencia no técnica
- **Online What if?** se diseñó explícitamente para "funcionarios, grupos de interés y ciudadanos". La accesibilidad para el no-experto es un feature de producto, no un extra.

---

## 3. Recomendaciones concretas para Cóndor View

Ideas a adoptar para diferenciarse y dar valor a un intendente:

1. **Convertir el simulador de intervención en el corazón del producto (no las pesas).**
   El diferenciador real frente a TODA la oferta LatAm (que son visores) es el what-if. Adoptar el patrón Conveyal/R5: el usuario dibuja una ruta hipotética y el mapa **recalcula la accesibilidad y el IAT antes/después**, mostrando "qué zonas se desbloquean". Técnicamente esto es **OSRM (red OSM editable) o r5r/R5** generando isócronas → la capa `dist_vial_m` / `S_acc` se regenera → el IAT se recalcula. Es 100% open-source, falsable y alineado con el principio "sin backend" si se pre-computan escenarios o se corre el ruteo en un worker liviano.

2. **Mantener y exhibir la explicabilidad como ventaja competitiva, no como limitación.**
   ArcGIS Urban es "caja de visualización", UrbanSim es caja negra econométrica. Cóndor View ya tiene el desglose IAT por sub-índice y `flags`. Reforzar el "por qué" de cada puntaje (qué criterio penalizó, con qué peso) — es justo lo que GeoPlanner/CommunityViz hacían bien y que esa región no ofrece.

3. **Agregar una capa de "valor para el municipio" estilo Urban3, aunque sea simple.**
   Un intendente decide por presupuesto y votos, no por geometría. Aunque sea un proxy (p.ej. valor potencial de la tierra × superficie desbloqueada, o recaudación potencial estimada), traducir el IAT a un número económico/fiscal multiplica el valor percibido. IDECOR demuestra que el valor de la tierra abierto es viable en Argentina.

4. **Construir sobre geoservicios abiertos LatAm en vez de re-crear datos.**
   Integrar **IDECOR** (valor de tierra, tierra vacante) y, para el piloto, **IDE Mendoza / Catastro ATM** e **IGN** (MDE, rutas, base) como fuentes. Esto reduce el riesgo R1/R2 del spec y da legitimidad institucional.

5. **Re-ponderación en cliente como mini-"scenario planning".**
   El `WeightControls` ya implementado es, de hecho, una versión ligera del *Suitability Wizard* de CommunityViz/GeoPlanner — un producto pago en retiro. Posicionarlo así: "ajustá las prioridades del municipio (¿priorizamos cercanía a rutas o suelo seguro?) y mirá cómo cambia el mapa al instante".

6. **Indicadores agregados comparables (mini-CPI).**
   El `StatsBar` puede evolucionar a un panel de "salud territorial" del área visible (% suelo apto, IAT promedio, superficie desbloqueable por un escenario) — el lenguaje de benchmarking que usa el City Prosperity Index, pero accionable y local.

7. **Exportar para el expediente.**
   Un intendente necesita un PDF/imagen para una reunión o una ordenanza. El `ExportButton` debe producir un entregable presentable (mapa + desglose + supuestos), porque la decisión pública vive en documentos.

8. **No competir donde se pierde: evitar microsimulación econométrica y 3D.**
   UrbanSim/ArcGIS Urban ganan en profundidad y 3D, pero a costo de años y dólares. El spec ya pone esto "fuera de alcance" — correcto. La ventaja de Cóndor View es velocidad, gratuidad y claridad, no profundidad de motor.

---

## 4. Posicionamiento de Cóndor View

Cóndor View (MVP gratis, sin backend, explicable, con simulador de intervención) se ubica en un **cuadrante que nadie ocupa bien**:

| Eje | Visores/IDE LatAm (IDECOR, IDE Mendoza, IGN) | Simuladores pesados (ArcGIS Urban, UrbanSim, UrbanFootprint, Replica) | **Cóndor View** |
|---|---|---|---|
| Costo | Gratis (datos abiertos) | Caro y opaco (suscripción/consultoría) | **Gratis** |
| Simulación what-if | **No** | Sí (pero pesada/lenta de montar) | **Sí, liviana e instantánea** |
| Explicabilidad | Media (datos crudos) | Baja-media (cajas negras/3D) | **Alta (cada puntaje auditable)** |
| Tiempo a valor | Inmediato pero sólo visualiza | Meses/años de calibración | **Inmediato y accionable** |
| Datos requeridos | Ya cargados | Masivos (y US-only en varios casos) | **Modestos (OSM + MDE + catastro)** |
| Foco geográfico | LatAm/AR | Mayormente EE.UU. | **Argentina/LatAm, en español** |
| Backend/infra | Portal pesado | SaaS/Desktop | **Cero (archivos estáticos)** |

**Lectura estratégica:**

- **Frente a los visores LatAm (IDECOR et al.):** Cóndor View no compite, los *complementa*. Ellos tienen los datos; Cóndor View agrega la capa que les falta a todos — **scoring de potencial + simulación de intervención**. Construir sobre sus geoservicios es la jugada.
- **Frente a los simuladores pesados (ESRI/UrbanSim):** Cóndor View es el **"tier 0"**: lo que un intendente puede abrir hoy, gratis, entender en 5 minutos y usar en una reunión — sin licencia, sin consultora, sin calibración de años. No reemplaza a ArcGIS Urban para un estudio de 3D; lo precede como herramienta de tamizado y conversación.
- **El hueco de GeoPlanner es una oportunidad:** ESRI retiró su producto de aptitud+escenarios (jul-2025/dic-2026) y dispersó la capacidad encareciéndola. Cóndor View ofrece justo esa función (weighted overlay re-ponderable + comparación de escenarios) de forma gratuita y web.
- **El riesgo a gestionar es la credibilidad de los pesos** (riesgo R3 del spec): los grandes lo resuelven con metodología publicada (AHP, validación). Cóndor View debe validar pesos con un urbanista y exponer el análisis de sensibilidad — convertir la transparencia en su foso defensivo.

**Conclusión:** El rumbo de Cóndor View está validado. El nicho "scoring de potencial + simulador de intervención, gratis, explicable y en español para gobiernos LatAm" no está ocupado: los locales no simulan y los que simulan son caros, opacos y US-céntricos. El factor decisivo será (1) que el simulador "qué desbloquea una ruta" funcione de forma creíble (OSRM/R5 + MCDA) y (2) traducir el resultado al lenguaje del intendente (valor económico/fiscal + entregable presentable).

---

## Fuentes

**ESRI / ArcGIS**
- https://www.esri.com/en-us/arcgis/products/arcgis-urban/overview
- https://www.esri.com/en-us/arcgis/products/arcgis-urban/features/3d-scenario-modeling
- https://www.esri.com/en-us/arcgis/products/arcgis-urban/buy
- https://flypix.ai/arcgis-urban-tool-review/
- https://community.esri.com/t5/arcgis-urban-blog/arcgis-urban-faqs/ba-p/884835
- https://doc.arcgis.com/en/geoplanner/latest/documentation/analyze-data.htm
- https://www.esri.com/en-us/arcgis/products/arcgis-geoplanner/overview
- https://www.esri.com/arcgis-blog/products/arcgis-geoplanner/announcements/announcement-deprecation-of-arcgis-geoplanner
- https://community.esri.com/t5/arcgis-geoplanner-blog/support-for-your-arcgis-geoplanner-transition/ba-p/1602046
- https://www.esri.com/en-us/arcgis/products/arcgis-hub/pricing
- https://www.esri.com/en-us/arcgis/products/arcgis-hub/purchase-options
- https://www.esri.com/en-us/arcgis/products/arcgis-online/buy
- https://equatorstudios.com/what-will-arcgis-cost-personal-vs-team-pricing/

**UrbanSim / UrbanFootprint / Replica / Urban3**
- https://www.urbansim.com/
- https://en.wikipedia.org/wiki/UrbanSim
- https://github.com/UDST/urbansim
- https://cloud.urbansim.com/docs/general/documentation/introduction-modeler.html
- https://urbanfootprint.com/
- https://urbanfootprint.com/features/scenario-planning/
- https://sgc.ca.gov/tools/urban-footprint/what-is/
- https://www.g2.com/products/urbanfootprint/reviews
- https://replicahq.com/
- https://www.replicahq.com/platform
- https://www.replicahq.com/post/the-first-nationwide-activity-based-travel-demand-model
- https://replicahq.com/scenario
- https://www.urbanthree.com/
- https://www.urbanthree.com/services/revenue-modeling/
- https://www.urbanthree.com/services/cost-of-service-analysis/
- https://regrid.com/tutorials/unequal-property-tax-assessments-a-chat-with-urban3

**Scenario planning / PSS / accesibilidad (open-source)**
- https://en.wikipedia.org/wiki/CommunityViz
- https://communityviz.com/product-information/scenario-360/
- https://link.springer.com/article/10.1007/s12061-015-9133-7
- https://www.planetizen.com/node/31483
- http://envisiontomorrow.org/envision-tomorrow-overview
- http://envisiontomorrow.org/faq
- https://github.com/conveyal/r5
- https://ipeagit.github.io/r5r/reference/isochrone.html
- https://docs.mapbox.com/api/navigation/isochrone/
- https://github.com/mapbox/osrm-isochrone
- https://www.nature.com/articles/s41599-023-01609-x
- https://www.sciencedirect.com/science/article/abs/pii/S1364815210001842

**LatAm — IDE / catastro / planeamiento**
- https://www.idecor.gob.ar/
- https://www.idecor.gob.ar/nuevos-mapas-de-valores-de-la-tierra-en-la-provincia-de-cordoba/
- https://www.idecor.gob.ar/que-es-y-para-que-sirve-el-observatorio-de-mercado-inmobiliario/
- https://www.idecor.gob.ar/donde-hay-tierra-vacante-mira-el-nuevo-mapa/
- https://www.idera.gob.ar/index.php?id=5
- https://www.ign.gob.ar/geoservicios
- https://mapa.ign.gob.ar/
- https://atm.mendoza.gov.ar/direcciones/direccion-general-de-catastro/
- https://www.elsol.com.ar/mendoza/el-gobierno-anuncio-cambios-en-la-gestion-de-datos-espaciales-cuales-seran-las-funciones-del-idemendoza/
- https://www.ide.cl/
- https://inde.gov.br/
- https://www.icde.gov.co/datos-y-recursos/observatorio-inmobiliario
- https://plataformaurbana.cepal.org/es/instrumentos/planificacion/planes-del-ordenamiento-territorial
- https://www.argentina.gob.ar/habitat/desarrollo-territorial/programa-planificacion-y-ordenamiento-territorial

**UN-Habitat / Banco Mundial**
- https://unhabitat.org/urban-planning-and-design-labs-tools-for-integrated-and-participatory-urban-planning
- https://unhabitat.org/network/global-network-of-urban-planning-and-design-labs
- https://unhabitat.org/our-city-plans-an-incremental-and-participatory-toolbox-for-urban-planning
- https://unhabitat.org/plan-assessment-tool-for-rapidly-growing-cities
- https://unhabitat.org/tool/the-city-resilience-action-planning-tool
- https://unhabitat.org/the-global-urban-monitoring-framework
- https://data.unhabitat.org/pages/city-prosperity-index
- https://data.unhabitat.org/
- https://www.worldbank.org/en/data/statistical-capacity-building/data-innovation-fund/urban-planning-tools
- https://www.worldbank.org/en/news/feature/2016/09/22/how-gathering-data-in-one-place-can-improve-indonesia-cities

---

### Notas de confianza sobre las fuentes
- Cifras de precio de ESRI: sólo Creator ($845/año) es público; "Professional Plus" y "Hub Premium" son "contactar ventas" (no verificables públicamente). El estimado ~US$25.000/año para 5 usuarios es de un tercero (Equator Studios), no oficial.
- Páginas de **Urban3** y **Replica** devolvieron 403 al fetch directo; sus afirmaciones se corroboraron vía snippets de búsqueda del mismo dominio oficial.
- El artículo primario de **Online What if?** (SpringerLink) está tras paywall; corroborado vía Planetizen y resúmenes de búsqueda.
- Las cifras de cobertura del **City Prosperity Index** son inconsistentes entre páginas de UN-Habitat (300+ / 400+ / "539 ciudades en 54 países" a 2020) — usar con cautela.
- Ninguna afirmación central del informe (ausencia de scoring/simulación en IDEs LatAm; retiro de GeoPlanner; naturaleza open-source de R5/OSRM/MCDA) dependió de una fuente débil; todas tienen respaldo en documentación oficial.
