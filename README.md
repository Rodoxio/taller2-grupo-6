# 🎬 ¿Qué ver después? Reglas de asociación y recomendador de películas

**Taller 2 · Aprendizaje no supervisado · Grupo 6**
Docente: Danilo Gómez Correa

Integrantes: Lucas Hermosilla Díaz · Rodolfo Hidalgo Memmel · Ariel Linero Torres

**App publicada:** [PEGAR AQUÍ EL LINK DE STREAMLIT](https://share.streamlit.io)

---

## El problema

Una plataforma de streaming quiere sugerir qué ver a continuación. Usando reglas de asociación sobre las películas que les gustaron a miles de usuarios, construimos un recomendador del tipo **"porque te gustó X, te recomendamos Y"**, lo evaluamos contra la alternativa más simple (recomendar siempre lo más popular) y publicamos los resultados en un dashboard interactivo.

## Ficha de la base de datos

| | |
|---|---|
| **Nombre** | MovieLens 1M (GroupLens Research, Universidad de Minnesota) |
| **Enlace** | https://grouplens.org/datasets/movielens/1m/ |
| **Datos originales** | 1.000.209 evaluaciones (1 a 5 estrellas) de 6.040 usuarios sobre 3.883 películas |
| **Transacción** | Un **usuario**: el conjunto de películas que le gustaron |
| **Ítem** | Una **película** evaluada con nota ≥ 4 |
| **Después de la limpieza** | 6.038 transacciones y 3.533 ítems; para minar reglas se usan las **200 películas más populares** y los **6.004 usuarios** que tienen al menos 2 de ellas |
| **Licencia** | Uso libre para investigación y docencia, citando la fuente. No permite redistribuir los datos, por eso este repositorio **no incluye los archivos originales**: el notebook los descarga directamente desde GroupLens |
| **Cita** | Harper, F. M. y Konstan, J. A. (2015). The MovieLens Datasets: History and Context. *ACM Transactions on Interactive Intelligent Systems*, 5(4), 19 |

## Principales resultados

- **341 reglas** con soporte ≥ 0,15 y confianza ≥ 0,6, todas estadísticamente significativas (test exacto de Fisher con corrección de Holm) y ninguna redundante. Las más fuertes unen sagas (*El Padrino II ⇒ El Padrino*, confianza 0,87) y estilos de una época (*Raiders + Star Wars V ⇒ Indiana Jones y la Última Cruzada*, lift 2,82).
- Sin conocer los géneros, las reglas revelan **comunidades de gusto**: animación familiar, cine criminal de los 90, acción de los 80, clásicos y ciencia ficción de culto.
- En la evaluación *offline* (80/20, *leave-one-out*), el recomendador por reglas **supera a recomendar lo más popular**: ordenando por confianza acierta la película oculta en primer lugar en el 6,0 % de los casos, contra 3,4 % de los populares. Ordenando por lift recomienda el 62,5 % del catálogo, contra 43,5 %. El **híbrido conmutado** logra el mejor equilibrio entre precisión y variedad.

## Estructura del repositorio

```
├── README.md                 ← este archivo
├── requirements.txt          ← dependencias del dashboard
├── app.py                    ← dashboard en Streamlit
├── data/                     ← resultados exportados desde el notebook (sección 9)
│   ├── reglas.csv               reglas para el explorador
│   ├── reglas_recomendador.csv  reglas película → película del recomendador
│   ├── populares.csv            las 200 películas con su soporte y géneros
│   ├── hitrate.csv              HitRate@N, cobertura y % de regla activa
│   └── resumen.csv              indicadores generales
└── Taller2_Grupo_6.ipynb     ← notebook con todo el análisis
```

El notebook está organizado en 9 secciones: 1) problema y base de datos, 2) limpieza y transacciones, 3) exploración, 4) itemsets y reglas, 5) Fisher, redundantes y consulta dirigida, 6) recomendador, 7) evaluación offline, 8) hallazgos y recomendaciones, y 9) exportación de CSV para el dashboard.

## El dashboard

| Pestaña | Qué muestra |
|---|---|
| **Resumen** | Transacciones, ítems, densidad, reglas finales y las 20 películas más populares |
| **Explorador de reglas** | Controles de soporte, confianza y lift; filtro por película en el antecedente o el consecuente; tabla ordenable y descarga en CSV |
| **Visualizaciones** | Dispersión soporte–confianza coloreada por lift y mapa de flujo película → película |
| **Recomendador** | El usuario elige películas y recibe N recomendaciones con su regla de origen, confianza y lift, indicando cuándo se usó el respaldo de populares |
| **Evaluación** | HitRate@N y cobertura del catálogo de los cuatro sistemas frente a la línea base |

## Ejecutarlo

### Dashboard en tu computador

Requiere Python 3.10 o superior.

```bash
git clone <URL-DE-ESTE-REPOSITORIO>
cd <CARPETA-DEL-REPOSITORIO>
pip install -r requirements.txt
streamlit run app.py
```

La app se abre en el navegador en `http://localhost:8501`. Lee los resultados desde la carpeta `data/`, por lo que no necesita volver a minar las reglas.

### Notebook

Abrir `Taller2_Grupo_6.ipynb` en Google Colab y ejecutar todas las celdas (**Entorno de ejecución → Ejecutar todo**). El notebook instala sus librerías, descarga MovieLens 1M desde GroupLens y, en la sección 9, vuelve a generar los archivos de `data/`. Todos los procesos aleatorios usan una semilla fija (`SEMILLA = 2026`), así que los resultados son reproducibles.

## Uso de inteligencia artificial

Se utilizó Claude (Anthropic) como apoyo para estructurar el código, adaptar las funciones de la guía de clase a esta base y redactar parte de los textos. Todo el código fue ejecutado, revisado y validado por el grupo.
