# Revisión del Proyecto Ingeso para el Hito 2

Fecha: 30 de octubre de 2026.

Se revisaron la plantilla DERS referencial del 10 de septiembre de 2025, el enunciado oficial del segundo semestre de 2026, las 20 páginas de Proyecto Ingeso versión 2 y los archivos del prototipo. El enunciado de 2026 determina el alcance de la entrega; las referencias de la plantilla a 2025-2 no cambian ese alcance.

## Qué integrar de la plantilla

| Sección | Decisión | Motivo |
| --- | --- | --- |
| Información preliminar e historial | Incorporada en la adenda | Permite identificar la ampliación y sus responsables sin cambiar la portada existente. |
| Alcance específico de la entrega | Incorporado | Distingue las pantallas y mensajes del Hito 2 de las reglas y la persistencia del Hito 3. |
| Criterios de aceptación y calidad | Incorporados | Permiten verificar la navegación, la carga de archivos y la claridad de la demostración. |
| Arquitectura 4+1 | Incorporada | Complementa MVC y los cuatro diagramas existentes con las perspectivas lógica, desarrollo, procesos, física y escenarios. |
| Riesgos y decisiones pendientes | Incorporados | Evita resolver silenciosamente contradicciones del enunciado antes de construir el motor. |
| Plan de pruebas y trazabilidad RU/CU/prueba | Incorporados en alcance reducido | Incluye pruebas unitarias, de integración y de aceptación del prototipo, más revisión manual del navegador. El enunciado ofrece el plan como opcional para el Hito 3. |
| Puntos de función y análisis de repago | Pospuestos | El enunciado del Hito 2 no los solicita expresamente. No hay estimaciones de costos y esfuerzo acordadas para sostenerlos. |
| Gantt completo y factibilidad de 5 a 8 páginas | Pospuestos | Basta una secuencia de revisión del prototipo y el tablero Kanban hasta que exista planificación detallada. |
| Nuevos roles de acceso e integraciones externas | No se incorporan al código | No existe una necesidad del enunciado que justifique autenticación, permisos o servicios ajenos al dominio. |

## Conservación del informe

El informe ampliado conserva las 20 páginas originales, en el mismo orden, sin cambiar texto, diagramas, capturas, portada, índice ni diagramación. La adenda agrega las páginas 21 a 28 y un índice propio. La numeración de cuadros continúa desde el Cuadro 6 para evitar intervenir las etiquetas existentes.

Las nuevas páginas reproducen el tamaño de 596 × 842 puntos, Times New Roman de 12 puntos, títulos de 14 puntos, interlineado del cuerpo de aproximadamente 15,87 puntos, márgenes del texto y numeración de 11 puntos del informe. El generador anexa páginas al PDF; no vuelve a componer las páginas existentes.

## Observaciones que se explican sin editar el texto previo

- La tabla de usuarios enumera varios perfiles, mientras el diagrama usa un único Jugador. La adenda aclara el actor operativo del Hito 2 y las responsabilidades de revisión y soporte.
- La arquitectura describe el producto final. La adenda distingue esas clases del repositorio de datos fijos que realmente existe en esta entrega.
- La base de datos externa RT002 es un requisito del producto final. Un archivo JSON no acredita su cumplimiento; tampoco implica que el prototipo restaure una partida.
- El ejemplo de ATK 43 y DEF 37 dice 8 de daño. La resta es 6. Además, deben acordarse la selección de objetivos, los redondeos, el orden de los bonos y el límite del descuento por esclavos.
- La portada sigue indicando versión 2. El historial identifica la ampliación como adenda 2.1; no se modifica la portada por instrucción del usuario.
- Los anexos individuales de trabajo deben usar aportes semanales reales. No se inventaron registros, RUT, roles personales ni compromisos de calendario.

## Cambios de código

Se conservan las rutas, pantallas y cifras del recorrido. Los catálogos oficiales se separan de las fotografías del escenario; RepositorioPrototipo centraliza consultas y devuelve copias; los controladores gestionan HTTP y las vistas preparan su contexto común. La fábrica de aplicación admite configuración para pruebas.

La exportación ya no mezcla tropas iniciales con una batalla del turno 2. Descarga una configuración inicial identificada como ejemplo. La carga comprueba JSON, versión, estructura y relaciones básicas, limita el tamaño a 1 MB e informa que no restaura una partida. Los mensajes de creación y elección de formaciones identifican la simulación. El automático se detiene ante la selección de formaciones.

La suite automatizada contiene UT001 a UT003, IT001 a IT004 y AT001. El motor, la economía dinámica y la persistencia externa continúan fuera de la implementación del Hito 2.

La revisión en navegador comprobó filtros, descarga del ejemplo, selector de archivos y detención del modo automático. La bitácora conserva un ancho legible con desplazamiento horizontal en pantallas estrechas, y Cargar campaña utiliza un botón accesible por teclado.

## Fuentes revisadas

- Plantilla-Contenido-DERS-2025-09-10-REFERENCIAL.docx: información preliminar, arquitectura, riesgos y plan de pruebas.
- ENUNCIADO-OFICIAL-PROYECTO-INGENIERIA-DE-SOFTWARE.pdf: reglas, hitos y entregables de 2026.
- Proyecto Ingeso.pdf: informe versión 2 del equipo Los Apóstrofes, 30 de octubre de 2026.

Los originales permanecen en Descargas. El PDF ampliado y el texto de la adenda se encuentran en esta carpeta.
