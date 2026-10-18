"""
Dashboard · Reglas de asociación y recomendador de películas (MovieLens 1M)
Taller 2 · Aprendizaje no supervisado · Grupo 6

Lee los resultados exportados por el notebook (carpeta data/) y los muestra en 5 módulos:
resumen, explorador de reglas, visualizaciones, recomendador y evaluación.
"""

# =============================================================================
# IMPORTACIONES
# =============================================================================
from pathlib import Path                      # Manejo de rutas de archivos independiente del sistema operativo

import pandas as pd                           # Lectura de los CSV y manejo de tablas
import plotly.express as px                   # Gráficos interactivos (barras, dispersión y líneas)
import streamlit as st                        # Construcción de la interfaz web
import streamlit.components.v1 as components  # Respaldo para mostrar HTML en versiones antiguas de Streamlit
from pyvis.network import Network             # Construcción del mapa de flujo (grafo interactivo)


# =============================================================================
# CONFIGURACIÓN GENERAL DE LA PÁGINA
# =============================================================================
# Define el título de la pestaña del navegador, el ícono y el ancho de la página.
# layout="wide" hace que el contenido ocupe todo el ancho de la pantalla.
# Esta instrucción debe ser la primera llamada a Streamlit del archivo.
st.set_page_config(page_title="Recomendador de películas · Grupo 6", page_icon="🎬", layout="wide")

# Ruta de la carpeta data/, calculada a partir de la ubicación de este archivo.
# Así la app encuentra los CSV tanto en el computador como en Streamlit Cloud.
DATA = Path(__file__).parent / "data"

# Separador usado en el notebook para guardar los conjuntos de películas como texto.
# Ejemplo en el CSV: "Alien (1979) | Aliens (1986)".
SEPARADOR = " | "

# Colores asignados a cada sistema de recomendación. Se usan en los gráficos de la
# pestaña Evaluación y se eligieron para que se vean bien en modo claro y oscuro.
COLORES = {"Reglas (lift)": "#3b7dd8", "Reglas (confianza)": "#d64541",
           "Híbrido": "#f39c12", "Populares": "#95a5a6"}


# =============================================================================
# CARGA DE DATOS
# =============================================================================
# El decorador @st.cache_data guarda en memoria el resultado de la función.
# Streamlit vuelve a ejecutar todo el archivo cada vez que el usuario mueve un
# control; gracias a la caché, los CSV se leen una sola vez y la app responde rápido.
@st.cache_data
def cargar_datos():
    # Lectura de los cinco archivos exportados por la sección 9 del notebook
    reglas = pd.read_csv(DATA / "reglas.csv")                     # Reglas para el explorador y la dispersión
    reglas_rec = pd.read_csv(DATA / "reglas_recomendador.csv")    # Reglas película -> película del recomendador
    populares = pd.read_csv(DATA / "populares.csv")               # Las 200 películas ordenadas por popularidad
    hitrate = pd.read_csv(DATA / "hitrate.csv")                   # Resultados de la evaluación offline
    resumen = pd.read_csv(DATA / "resumen.csv")                   # Indicadores generales (transacciones, ítems, etc.)

    # En el CSV los antecedentes y consecuentes están guardados como texto ("A | B").
    # Aquí se convierten de nuevo en conjuntos (frozenset) para poder comparar,
    # por ejemplo, si el antecedente de una regla está contenido en la canasta del usuario.
    reglas["antecedente_set"] = reglas["antecedente"].apply(lambda s: frozenset(s.split(SEPARADOR)))
    reglas["consecuente_set"] = reglas["consecuente"].apply(lambda s: frozenset(s.split(SEPARADOR)))
    reglas_rec["antecedente_set"] = reglas_rec["antecedente"].apply(lambda s: frozenset(s.split(SEPARADOR)))

    # El resumen viene como tabla de dos columnas (indicador, valor).
    # Se transforma en diccionario para consultarlo así: resumen["transacciones"].
    resumen = dict(zip(resumen["indicador"], resumen["valor"]))
    return reglas, reglas_rec, populares, hitrate, resumen


# =============================================================================
# FUNCIONES AUXILIARES DE FORMATO
# =============================================================================
# Estas funciones solo cambian cómo se muestran los números en pantalla,
# usando la convención chilena (coma decimal y punto de miles).

def porcentaje(x, decimales=1):
    # Convierte una proporción en porcentaje con coma decimal. Ejemplo: 0.1813 -> "18,1 %"
    return f"{x * 100:.{decimales}f} %".replace(".", ",")


def entero(x):
    # Agrega punto como separador de miles. Ejemplo: 6004 -> "6.004"
    return f"{int(x):,}".replace(",", ".")


def corto(titulo, largo=28):
    # Acorta títulos largos para que quepan en las etiquetas del mapa de flujo.
    # El título completo se sigue viendo al pasar el mouse sobre el nodo.
    return titulo if len(titulo) <= largo else titulo[:largo - 1] + "…"


# -----------------------------------------------------------------------------
# Ejecución de la carga y variables de uso general
# -----------------------------------------------------------------------------
reglas, reglas_rec, populares, hitrate, resumen = cargar_datos()

# Lista de las 200 películas ordenadas de la más a la menos popular.
# Se usa como opciones del selector del recomendador y como respaldo de populares.
peliculas = populares["pelicula"].tolist()

# Diccionario película -> soporte. Determina el tamaño de cada círculo en el mapa de flujo.
soporte_pelicula = dict(zip(populares["pelicula"], populares["soporte"]))

# Lift mínimo del híbrido conmutado (2,0), leído desde resumen.csv para que
# coincida siempre con el valor usado en el notebook.
LIFT_MINIMO = float(resumen["lift_minimo_hibrido"])


# =============================================================================
# FUNCIÓN RECOMENDAR
# =============================================================================
# Es la misma lógica de la función recomendar() de la sección 6 del notebook,
# adaptada para leer las reglas desde el CSV.
#   canasta  : películas que el usuario eligió como favoritas
#   reglas   : tabla de reglas película -> película
#   populares: lista de películas ordenadas por popularidad (respaldo)
#   top      : cantidad de recomendaciones a entregar (N)
#   orden    : criterio para ordenar las reglas ("lift" o "confianza")
def recomendar(canasta, reglas, populares, top=5, orden="lift"):
    canasta = set(canasta)

    # Paso 1. Reglas activas: el antecedente está completamente dentro de la canasta
    # y la película recomendada (producto) todavía no está en la canasta.
    activa = reglas["antecedente_set"].apply(lambda x: x <= canasta)
    nueva = ~reglas["producto"].isin(canasta)
    candidatas = reglas[activa & nueva]

    # Paso 2. Se ordenan por el criterio elegido (con la confianza como desempate)
    # y se deja una sola regla por película, la de mejor puntaje.
    candidatas = candidatas.sort_values([orden, "confianza"], ascending=False)
    candidatas = candidatas.drop_duplicates("producto").head(top)

    # Paso 3. Se arma la lista de sugerencias con su motivo ("Porque te gustó X"),
    # su confianza, su lift y su origen (regla).
    sugerencias = [{"película": r["producto"],
                    "motivo": f"Porque te gustó {r['antecedente'].replace(SEPARADOR, ' y ')}",
                    "confianza": r["confianza"], "lift": r["lift"], "origen": "regla"}
                   for _, r in candidatas.iterrows()]

    # Paso 4. Respaldo de populares: si las reglas no alcanzan para completar N
    # recomendaciones (o no se activó ninguna: arranque en frío), se completa con
    # las películas más populares que el usuario aún no tiene.
    ya_sugeridas = {s["película"] for s in sugerencias}
    for pelicula in populares:
        if len(sugerencias) >= top:
            break
        if pelicula not in canasta and pelicula not in ya_sugeridas:
            sugerencias.append({"película": pelicula, "motivo": "Más popular",
                                "confianza": None, "lift": None, "origen": "más popular"})
    return pd.DataFrame(sugerencias)


def mostrar_red(red, alto):
    # Muestra un grafo de pyvis dentro de la app.
    # pyvis genera una página HTML completa, que se incrusta en un iframe.
    html = red.generate_html()
    if hasattr(st, "iframe"):          # Versiones recientes de Streamlit
        st.iframe(html, height=alto + 20)
    else:                              # Versiones anteriores (método antiguo)
        components.html(html, height=alto + 20)


# =============================================================================
# ENCABEZADO DE LA APLICACIÓN
# =============================================================================
st.title("🎬 ¿Qué ver después?")
st.write(
    "Reglas de asociación sobre **MovieLens 1M**: a quienes les gustó una película, ¿qué otras les gustaron? "
    "Cada usuario es una transacción y cada película con nota ≥ 4 es un ítem."
)

# Creación de las cinco pestañas. Cada variable (tab_resumen, tab_reglas, etc.)
# representa una pestaña, y todo lo que se escriba dentro de su bloque "with"
# aparece solo en esa pestaña.
tab_resumen, tab_reglas, tab_graficos, tab_recomendador, tab_evaluacion = st.tabs(
    ["Resumen", "Explorador de reglas", "Visualizaciones", "Recomendador", "Evaluación"]
)


# =============================================================================
# PESTAÑA 1: RESUMEN DE DATOS
# =============================================================================
with tab_resumen:
    # --- Indicadores principales: cuatro tarjetas en una fila ---
    # El texto de "help" aparece al pasar el mouse sobre el signo de pregunta.
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Transacciones (usuarios)", entero(resumen["transacciones"]),
              help=f"De {entero(resumen['usuarios_totales'])} usuarios, los que tienen al menos 2 de las películas analizadas.")
    c2.metric("Ítems (películas)", entero(resumen["items"]),
              help=f"Las más populares de {entero(resumen['peliculas_totales'])} películas con alguna nota ≥ 4.")
    c3.metric("Densidad de la matriz", porcentaje(resumen["densidad"]),
              help="Porcentaje de celdas usuario × película con un 1.")
    c4.metric("Reglas finales", entero(resumen["reglas_finales"]),
              help=f"Soporte ≥ {resumen['soporte_min']} y confianza ≥ {resumen['confianza_min']}; todas significativas (Fisher + Holm).")

    # --- Gráfico de barras horizontales con las 20 películas más populares ---
    st.subheader("Las 20 películas que más gustan")
    # Se ordena de menor a mayor para que, al dibujar barras horizontales,
    # la película más popular quede arriba.
    top20 = populares.head(20).sort_values("soporte")
    fig = px.bar(top20, x="soporte", y="pelicula", orientation="h",
                 hover_data={"usuarios": True, "generos": True, "pelicula": False},   # Datos visibles al pasar el mouse
                 labels={"soporte": "Proporción de usuarios a los que les gustó", "pelicula": ""},
                 color_discrete_sequence=[COLORES["Reglas (lift)"]], height=560)
    fig.update_layout(xaxis_tickformat=".0%")   # Eje X expresado en porcentaje
    st.plotly_chart(fig)
    st.caption("Pocas películas concentran los gustos (cola larga): *American Beauty* le gusta a casi la mitad de los usuarios.")


# =============================================================================
# PESTAÑA 2: EXPLORADOR DE REGLAS
# =============================================================================
with tab_reglas:
    st.write("Ajusta los umbrales y busca una película para ver qué reglas la involucran.")

    # --- Controles deslizantes de umbrales ---
    # Formato: st.slider(etiqueta, mínimo, máximo, valor inicial, paso).
    # Los valores iniciales son los umbrales finales del notebook (soporte 0,15 y confianza 0,6).
    c1, c2, c3 = st.columns(3)
    sop_min = c1.slider("Soporte mínimo", float(reglas["soporte"].min()), float(reglas["soporte"].max()),
                        float(resumen["soporte_min"]), step=0.01)
    conf_min = c2.slider("Confianza mínima", float(reglas["confianza"].min()), 1.0,
                         float(resumen["confianza_min"]), step=0.05)
    lift_min = c3.slider("Lift mínimo", 1.0, float(reglas["lift"].max()), 1.0, step=0.1)

    # --- Filtro por película y lado de la regla ---
    c4, c5 = st.columns([2, 1])
    pelicula_filtro = c4.selectbox("Película", ["(todas)"] + sorted(peliculas))
    lado = c5.radio("Aparece en", ["Cualquier lado", "Antecedente", "Consecuente"], horizontal=True)

    # --- Aplicación de los filtros de umbrales ---
    filtradas = reglas[(reglas["soporte"] >= sop_min) &
                       (reglas["confianza"] >= conf_min) &
                       (reglas["lift"] >= lift_min)]

    # --- Aplicación del filtro por película (solo si se eligió una) ---
    if pelicula_filtro != "(todas)":
        en_ante = filtradas["antecedente_set"].apply(lambda s: pelicula_filtro in s)   # La película está en el antecedente
        en_cons = filtradas["consecuente_set"].apply(lambda s: pelicula_filtro in s)   # La película está en el consecuente
        filtro = {"Cualquier lado": en_ante | en_cons, "Antecedente": en_ante, "Consecuente": en_cons}[lado]
        filtradas = filtradas[filtro]

    # --- Tabla ordenable ---
    # st.dataframe permite ordenar haciendo clic en el encabezado de cada columna.
    # column_config define el nombre visible y el formato numérico de cada columna.
    tabla = filtradas[["regla", "soporte", "confianza", "lift", "leverage", "conviccion"]]
    st.write(f"**{entero(len(tabla))} reglas** cumplen los filtros (de {entero(len(reglas))}). "
             "Haz clic en el nombre de una columna para ordenar.")
    st.dataframe(tabla, hide_index=True, height=420,
                 column_config={
                     "regla": st.column_config.TextColumn("Regla", width="large"),
                     "soporte": st.column_config.NumberColumn("Soporte", format="%.3f"),
                     "confianza": st.column_config.NumberColumn("Confianza", format="%.3f"),
                     "lift": st.column_config.NumberColumn("Lift", format="%.2f"),
                     "leverage": st.column_config.NumberColumn("Leverage", format="%.3f"),
                     "conviccion": st.column_config.NumberColumn("Convicción", format="%.2f"),
                 })

    # --- Botón de descarga ---
    # Descarga exactamente las reglas que se ven en la tabla, con los filtros aplicados.
    st.download_button("Descargar estas reglas (CSV)", tabla.to_csv(index=False).encode("utf-8"),
                       file_name="reglas_filtradas.csv", mime="text/csv")


# =============================================================================
# PESTAÑA 3: VISUALIZACIONES INTERACTIVAS
# =============================================================================
with tab_graficos:
    # --- Dispersión soporte vs. confianza, coloreada por lift (Plotly) ---
    # Usa la variable "filtradas" de la pestaña anterior, por lo que responde
    # a los mismos controles del explorador de reglas.
    st.subheader("Dispersión de reglas")
    st.caption("Usa los mismos filtros del explorador. Pasa el mouse sobre un punto para ver la regla.")
    if filtradas.empty:
        st.info("Ninguna regla cumple los filtros del explorador. Baja los umbrales para ver puntos.")
    else:
        fig = px.scatter(filtradas, x="soporte", y="confianza", color="lift", hover_name="regla",
                         hover_data={"soporte": ":.3f", "confianza": ":.3f", "lift": ":.2f"},
                         color_continuous_scale="Reds", height=480)
        fig.update_traces(marker=dict(size=8, line=dict(width=0.3, color="white")))
        st.plotly_chart(fig)

    # --- Mapa de flujo película -> película (pyvis) ---
    st.subheader("Mapa de flujo película → película")
    st.caption("Cada flecha es una regla «a quien le gustó A, también le gustó B». "
               "Grosor = confianza, color = lift, tamaño del círculo = popularidad. Puedes arrastrar y hacer zoom.")
    # Control para mostrar solo las asociaciones más fuertes; con valores bajos
    # aparecen demasiadas flechas y el mapa se vuelve ilegible.
    lift_mapa = st.slider("Mostrar solo flechas con lift mayor o igual a", 2.0, 4.0, 3.0, step=0.1)

    seleccion = reglas_rec[reglas_rec["lift"] >= lift_mapa]
    if seleccion.empty:
        st.info("No hay reglas con ese lift. Baja el valor del control.")
    else:
        red = Network(height="620px", width="100%", directed=True, cdn_resources="remote")
        lift_lo, lift_hi = seleccion["lift"].min(), seleccion["lift"].max()
        escala = px.colors.sequential.Reds     # Escala de rojos: más oscuro = mayor lift

        # Nodos: un círculo por película; su tamaño depende de la popularidad (soporte)
        nodos = set(seleccion["antecedente"]) | set(seleccion["producto"])
        for pelicula in nodos:
            red.add_node(pelicula, label=corto(pelicula), title=pelicula, shape="dot", color="#0b1f45",
                         size=10 + 60 * soporte_pelicula.get(pelicula, 0.1),
                         font={"size": 18, "color": "#0b1f45", "strokeWidth": 5, "strokeColor": "white"})

        # Flechas: una por regla; el grosor depende de la confianza y el color del lift
        for _, r in seleccion.iterrows():
            proporcion = (r["lift"] - lift_lo) / (lift_hi - lift_lo) if lift_hi > lift_lo else 1
            color = escala[min(len(escala) - 1, 3 + int(proporcion * (len(escala) - 4)))]
            red.add_edge(r["antecedente"], r["producto"], width=1 + 8 * r["confianza"], color=color,
                         title=f"{r['antecedente']} ⇒ {r['producto']}\nconfianza: {r['confianza']:.3f}\nlift: {r['lift']:.2f}")

        # Configuración de la física del grafo (separación entre nodos) y despliegue
        red.barnes_hut(gravity=-9000, spring_length=160)
        st.write(f"{entero(len(seleccion))} reglas entre {len(nodos)} películas.")
        mostrar_red(red, 620)


# =============================================================================
# PESTAÑA 4: RECOMENDADOR
# =============================================================================
with tab_recomendador:
    st.write("Elige películas que te gustaron y el sistema te sugiere qué ver después, explicando por qué.")

    # --- Canasta del usuario (selección múltiple) ---
    canasta = st.multiselect("Películas que te gustaron", peliculas,
                             default=["Toy Story (1995)", "Aladdin (1992)"],
                             placeholder="Busca por título, por ejemplo Matrix")

    # --- Cantidad de recomendaciones y sistema a utilizar ---
    c1, c2 = st.columns([1, 2])
    n_recomendaciones = c1.slider("¿Cuántas recomendaciones?", 1, 10, 5)
    sistema = c2.radio("Sistema", ["Híbrido (recomendado)", "Reglas por lift", "Reglas por confianza"],
                       horizontal=True,
                       help=f"El híbrido usa solo reglas con lift ≥ {LIFT_MINIMO:g} ordenadas por confianza; "
                            "si ninguna se activa, recomienda las más populares.")

    # --- Cálculo de las recomendaciones según el sistema elegido ---
    if sistema.startswith("Híbrido"):
        # Híbrido conmutado: solo reglas con lift >= 2, ordenadas por confianza
        resultado = recomendar(canasta, reglas_rec[reglas_rec["lift"] >= LIFT_MINIMO], peliculas,
                               n_recomendaciones, orden="confianza")
    elif sistema == "Reglas por lift":
        resultado = recomendar(canasta, reglas_rec, peliculas, n_recomendaciones, orden="lift")
    else:
        resultado = recomendar(canasta, reglas_rec, peliculas, n_recomendaciones, orden="confianza")

    # --- Avisos sobre el uso del respaldo de populares ---
    respaldo = (resultado["origen"] == "más popular").sum()   # Cuántas recomendaciones no vienen de reglas
    if not canasta:
        # Canasta vacía: arranque en frío
        st.info("Arranque en frío: sin películas elegidas no se activa ninguna regla, así que se muestran las más populares.")
    elif respaldo == len(resultado):
        # Hay películas elegidas, pero ninguna activó reglas
        st.warning("Ninguna regla se activó con estas películas: se muestran las más populares (respaldo).")
    elif respaldo > 0:
        # Algunas recomendaciones vienen de reglas y otras del respaldo
        st.info(f"{respaldo} de {len(resultado)} recomendaciones vienen del respaldo de populares, "
                "porque no había suficientes reglas activas.")

    # --- Tabla de recomendaciones con su regla de origen, confianza y lift ---
    st.dataframe(resultado[["película", "motivo", "confianza", "lift", "origen"]], hide_index=True,
                 column_config={
                     "película": st.column_config.TextColumn("Te recomendamos", width="medium"),
                     "motivo": st.column_config.TextColumn("Por qué (regla de origen)", width="large"),
                     "confianza": st.column_config.NumberColumn("Confianza", format="%.3f"),
                     "lift": st.column_config.NumberColumn("Lift", format="%.2f"),
                     "origen": st.column_config.TextColumn("Origen"),
                 })


# =============================================================================
# PESTAÑA 5: EVALUACIÓN
# =============================================================================
with tab_evaluacion:
    st.write(
        f"Evaluación *offline* con {entero(resumen['casos_prueba'])} usuarios de prueba (partición 80/20 con semilla fija): "
        "a cada uno se le oculta una película y se mide si el sistema la recupera entre sus N recomendaciones."
    )

    # Orden fijo de los sistemas en leyendas y tablas: Reglas (lift), Reglas (confianza), Híbrido, Populares
    orden_sistemas = list(COLORES)

    # --- Gráficos lado a lado: precisión (izquierda) y novedad (derecha) ---
    c1, c2 = st.columns(2)
    with c1:
        # HitRate@N: proporción de casos en que la película oculta aparece entre las N recomendaciones
        fig = px.line(hitrate, x="N", y="hitrate", color="sistema", markers=True,
                      category_orders={"sistema": orden_sistemas}, color_discrete_map=COLORES,
                      labels={"hitrate": "HitRate@N", "N": "N (largo de la lista)", "sistema": ""},
                      title="Precisión: ¿acierta la película oculta?", height=420)
        fig.update_layout(xaxis=dict(tickvals=[1, 3, 5, 10]), yaxis_tickformat=".0%")
        st.plotly_chart(fig)
    with c2:
        # Cobertura: porcentaje de las 200 películas que cada sistema llega a recomendar
        fig = px.line(hitrate, x="N", y="cobertura", color="sistema", markers=True,
                      category_orders={"sistema": orden_sistemas}, color_discrete_map=COLORES,
                      labels={"cobertura": "% del catálogo recomendado", "N": "N (largo de la lista)", "sistema": ""},
                      title="Novedad: ¿cuánto del catálogo recomienda?", height=420)
        fig.update_layout(xaxis=dict(tickvals=[1, 3, 5, 10]), yaxis_tickformat=".0%")
        st.plotly_chart(fig)

    # --- Tabla de HitRate@N ---
    # pivot reorganiza los datos: una fila por N y una columna por sistema
    st.subheader("HitRate@N")
    tabla_hr = hitrate.pivot(index="N", columns="sistema", values="hitrate")[orden_sistemas]
    st.dataframe(tabla_hr.style.format("{:.1%}"))

    # --- Tablas de cobertura y de casos con regla activa ---
    c3, c4 = st.columns(2)
    with c3:
        st.subheader("Cobertura del catálogo")
        tabla_cob = hitrate.pivot(index="N", columns="sistema", values="cobertura")[orden_sistemas]
        st.dataframe(tabla_cob.style.format("{:.1%}"))
    with c4:
        # El porcentaje de regla activa es igual para todos los N, por eso se toma una fila por sistema
        st.subheader("Casos con al menos una regla activa")
        activa = hitrate.drop_duplicates("sistema").set_index("sistema")["regla_activa"].reindex(orden_sistemas)
        st.dataframe(activa.rename("% de casos").to_frame().style.format("{:.1%}"))

    # --- Conclusión breve bajo las tablas ---
    st.caption(
        "Las reglas ordenadas por confianza son las más precisas; las ordenadas por lift recomiendan más variedad. "
        "El híbrido logra el mejor equilibrio entre ambas, y todas las versiones con reglas superan o igualan "
        "a la línea base de populares en precisión o en variedad."
    )
