# 24 — Experiencia ejecutiva

Estado: implementado
Fecha: 2026-07-31

## Objetivo

La interfaz predeterminada está diseñada para una persona que necesita saber
si el laboratorio funciona y qué está haciendo, sin conocer sus componentes
técnicos. La trazabilidad completa se conserva en PostgreSQL y en la API, pero
no compite con la información necesaria para tomar una decisión.

La pantalla principal responde cuatro preguntas:

1. ¿Está funcionando el sistema?
2. ¿Qué resultado simulado acumula?
3. ¿Encontró oportunidades?
4. ¿Qué hizo recientemente?

## Jerarquía de información

- **Resumen:** estado, resultado paper, capital, mercados y evolución.
- **Oportunidades:** comparación simple entre mercado y estimación, confianza
  y conclusión comercial.
- **Actividad:** operaciones simuladas automáticas y manuales, diferenciadas
  con texto y color.
- **Mercados:** búsqueda, probabilidad actual y evolución de cada mercado.

IDs, hashes, correlation IDs, configuración de agentes, detalles del collector,
snapshots y diagnósticos permanecen disponibles para auditoría mediante API y
logs, pero no se muestran en la experiencia ejecutiva.

## Principios

- Todo importe está rotulado como simulado; no existe dinero real.
- La automatización es la opción predeterminada. La acción manual es opcional y
  nunca reemplaza ni detiene la campaña automática.
- El lenguaje describe consecuencias antes que mecanismos internos.
- El color siempre se acompaña con texto e iconos.
- Los detalles se cargan sólo al abrirlos para reducir carga y ruido visual.
- Los estados de carga, vacío y error explican qué ocurre y qué puede hacer la
  persona.
- Navegación, filtros, modales y acciones son accesibles por teclado.
- Animaciones breves aportan respuesta visual; `prefers-reduced-motion` las
  desactiva para quien lo solicite.

## Estilo visual

La paleta usa fondo marfil, texto azul tinta y acentos violeta, verde, naranja
y azul. Las tarjetas, botones y enlaces tienen estados visibles de hover,
focus y click. En dispositivos con puntero fino aparece un halo discreto que
sigue el cursor; se desactiva en pantallas táctiles.
