# 24 — Guía UX para principiantes

Estado: implementado  
Fecha: 2026-07-28

## Vista simple

Es la vista predeterminada. Prioriza cinco preguntas:

1. ¿Funciona el sistema?
2. ¿Cuándo se actualizaron los datos?
3. ¿Cuántos mercados se observan?
4. ¿Qué probabilidades cambiaron más?
5. ¿Hay avisos que requieren atención?

Presenta estado, fuentes, antigüedad, cobertura histórica, cambios y
minialertas con explicaciones breves. Evita identificadores, errores técnicos y
contadores internos.

## Vista avanzada

Añade series históricas, volumen, liquidez, timeline, sincronizaciones,
timestamps, procedencia y resolución. El cambio de modo no modifica datos; sólo
su nivel de detalle.

## Reglas

- Una probabilidad es informativa, no una promesa ni una cotización.
- No se muestran ROI, cartera, operaciones o rentabilidad ficticia.
- Simulación aparece deshabilitada hasta que exista su módulo real.
- Verde significa confirmación positiva o salud; rojo error crítico; amarillo
  advertencia; azul información; gris desconocido. Todo color se acompaña con
  texto, icono y `aria-label`.
- Navegación, tablas y tooltips son operables con teclado.
- Loading, vacío y error tienen estados explícitos y legibles por tecnologías
  de asistencia.
