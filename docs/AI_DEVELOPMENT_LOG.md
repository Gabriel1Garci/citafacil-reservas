# AI Development Log

**Proyecto 1 · Tópicos Especiales II · Prof. Regis Rivera**
**Estudiante:** Gabriel García
**App base:** [citafacil](https://github.com/gianca675/citafacil) (FastAPI, SQLite, HTML/CSS/JS)
**Herramienta de IA:** Claude Code (Claude Sonnet 5.5)

> Hice el proyecto solo. La IA hizo los tres roles por separado (Developer, Reviewer y QA) y lo dejó escrito en cada Pull Request (#7 al #18).

## 1. Resultado

| Historia | Issue | PR | Estado |
|---|---|---|---|
| US1 - Reserva rápida con datos guardados (del profesor) | #2 | #12 | Mergeada |
| US2 - Calendario con días disponibles y ocupados (del profesor) | #3 | #9 | Mergeada |
| US3 - Gráficos de previsión de demanda (del profesor) | #4 | #13 | Mergeada |
| US4 - Cancelar la reserva con un código (adicional) | #5 | #11 | Mergeada |
| US5 - Exportar reservas a CSV (adicional) | #6 | #14 | Mergeada |
| Bug: los tests fallaban en Windows | #1 | #7 | Mergeada |
| Bug: seed.py fallaba en Windows | #8 | #16 | Mergeada |
| Seguridad: falla XSS | #10 | #15 | Mergeada |

Los tests pasaron de 6 a **69**.

## 2. Análisis antes de programar

Antes de pedirle código a la IA leí todo el proyecto. Esto encontré:

- No hay usuarios ni pagos. Para la US1 hubo que crear un pago simulado y un perfil de cliente.
- Los tests usaban la ruta `/tmp` y no corrían en Windows.
- `create_all` no agrega columnas a tablas que ya existen.
- El frontend usaba `innerHTML` con datos del usuario (riesgo de XSS).
- El archivo `scores.py` es de un juego que no tiene que ver con reservas. No lo toqué.

## 3. Log de uso de IA

| Actividad | Herramienta IA | Qué se solicitó | Resultado | Decisión humana |
|---|---|---|---|---|
| Análisis del repo | Claude Code | Leer el código antes de cambiarlo | Vio que no hay pagos ni usuarios, que los tests usan /tmp y que hay riesgo de XSS | Aceptada |
| Entorno | Claude Code | Instalar las dependencias | Las versiones fijas no sirven para Python 3.14 | Modificada: se instalaron versiones nuevas en un venv |
| Testing (base) | Claude Code | Correr pytest antes de cambiar nada | Los 6 tests fallaban en Windows | Corregida (PR #7) |
| Testing US2 | Claude Code | 5 tests del calendario | Un test suponía mal los domingos pasados | Incorrecta: se corrigió el test |
| Frontend US2 | Claude Code | Calendario del mes | Título "Octubre De 2026" y otra fuente en los números | Corregida antes del merge |
| Código US4 | Claude Code | Cancelar con código | Usó create_all y la base vieja no tenía la columna | Modificada: se agregó ensure_schema() |
| Testing US4 | Claude Code | Test de código que no existe | Pasaba antes de programar (era un 404 por ruta inexistente) | Corregida: se reforzó el test |
| Diseño US1 | Claude Code | Cómo guardar los datos del cliente | Propuso identificarlo por teléfono | Rechazada: se usa un token en el navegador |
| Código US1 | Claude Code | Pago y reserva rápida | Los errores 422 devolvían el número de tarjeta y el CVV | Incorrecta: corregida con un handler y un test |
| Testing US1 | Claude Code | 20 tests de pagos | Pasaron a la primera y dos no probaban nada | Corregida: se reescribieron y se probaron con mutación |
| Frontend US1 | Claude Code | Flujo de pago en el navegador | Después de un pago rechazado se perdía la hora elegida | Corregida |
| Commit US1 | Claude Code | Mensaje del commit | Decía 30 tests nuevos y eran 20 | Corregida antes de subir |
| Código US3 | Claude Code | Previsión de demanda | Daba 21.2 de 20 horarios (más que la capacidad) | Modificada: se limita a la capacidad |
| Testing US3 | Claude Code | Test del límite de capacidad | Los datos de prueba estaban mal calculados | Incorrecta: se rehízo el test |
| Modelo US3 | Claude Code | Elegir cómo calcular la previsión | Promedio por día de la semana por la tendencia | Aceptada |
| Código US5 | Claude Code | Exportar a CSV | El archivo se bajaba como reservas.csv por un tema de CORS | Corregida |
| UI US5 | Claude Code | Botón de exportar | El filtro no se aplicaba al cambiar el selector | Modificada |
| Seguridad (#10) | Claude Code | Arreglar el XSS | La primera prueba no probaba nada (la reserva dio 409) | Incorrecta: se rehízo la prueba |

## 4. Respuestas incorrectas de la IA

1. **Datos de tarjeta en los errores 422.** La API devolvía el número y el CVV. Lo encontró el Reviewer.
2. **Tests que no probaban nada.** Uno pasaba antes de programar, otros siempre daban verdadero y otro tenía mal los números.
3. **Suposición falsa en un test.** Los domingos pasados salen como `past`, no como `closed`.
4. **Dato falso en un commit.** Decía 30 tests nuevos y eran 20.
5. **Esquema de la base.** `create_all` no agrega columnas nuevas.

## 5. Cambios rechazados o modificados

Rechazados o rehechos:

- Perfil identificado por teléfono. Otra persona podría ver los datos. Ahora se usa un token.
- `create_all` para agregar columnas. Ahora se usa `ensure_schema()`.
- Tests débiles. Se rehicieron.
- Primera previsión (pasaba la capacidad) y filtros que no se aplicaban al cambiar. Se modificaron.

Decisiones que tomé desde el inicio (no fueron errores de la IA):

- No tocar `scores.py`.
- No usar machine learning para la previsión.
- No cambiar el teléfono en el CSV, porque ya viene validado.

## 6. Decisiones humanas

- **Las tomó Gabriel García:** elegir citafacil, crear el repositorio público y dejar los tres roles a la IA.
- **Las tomó la IA con su permiso:** las historias US4 y US5, el pago simulado, el token del cliente, el cálculo de la previsión y los límites de seguridad.

Estas últimas hay que revisarlas para poder explicarlas en la presentación.

## 7. Limitaciones

- El pago es simulado. En un sistema real se usaría un proveedor de pagos.
- Se cobra antes de guardar la cita.
- No hay límite de intentos en cancelar ni en el perfil.
- El historial de la demo es inventado (`seed_history.py`).
- La previsión no cuenta feriados.
- En el celular el texto de los gráficos se ve pequeño.
- Las citas viejas no tienen código de cancelación.

## 8. Flujo de Git

Cada cambio salió de una rama (`feature/*`, `fix/*`, `docs/*`). Cada Pull Request tiene la descripción del Developer, un comentario del Reviewer y uno del QA con los resultados.
