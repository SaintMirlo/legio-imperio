# 5. Complementos de la especificación

Esta adenda complementa las secciones 1 a 4 del informe de Legio Imperium para el Hito 2. Precisa el alcance de la demostración, relaciona la arquitectura con el prototipo y establece criterios de revisión. Los requisitos del producto final conservan su numeración RU001 a RU010 y RT001 a RT004.

## 5.1. Información preliminar y control de versiones

El equipo Los Apóstrofes es responsable del análisis, diseño, prototipo y documentación. Los integrantes y sus contactos se encuentran en la portada. El profesor Daniel Moreno actúa como contraparte académica y Christopher Abarca como ayudante de la asignatura.

Cuadro 6 “Historial del informe y su adenda”

| Versión | Fecha | Contenido |
| --- | --- | --- |
| 2 | 30 de octubre de 2026 | Informe de análisis y diseño, arquitectura MVC y prototipo navegable. Corresponde a las páginas 1 a 20. |
| Adenda 2.1 | 30 de octubre de 2026 | Alcance del Hito 2, criterios verificables, vistas 4+1, riesgos y plan de pruebas. Corresponde a las páginas 21 a 28. |

### Distribución de responsabilidades

La coordinación del equipo consolida el informe y el tablero Kanban; el desarrollo mantiene el prototipo; la revisión verifica navegación, coherencia y evidencias. Estas responsabilidades deben distribuirse entre los integrantes en el tablero y explicarse individualmente durante la presentación.

### Contenido de la adenda

| Sección | Página |
| --- | --- |
| 5.1. Información preliminar y control de versiones | 21 |
| 5.2. Alcance y participantes del Hito 2 | 22 |
| 5.3. Criterios de aceptación y calidad | 23 |
| 5.4. Arquitectura según las vistas 4+1 | 24 |
| 5.5. Riesgos y decisiones del dominio | 25 |
| 6. Plan de pruebas del Hito 2 | 26 |
| 6.1. Definición de una prueba con excepciones | 27 |
| 6.2. Matriz de trazado de requisitos y pruebas | 28 |

<!-- pagina -->

## 5.2. Alcance y participantes del Hito 2

El objetivo de esta entrega es demostrar cómo el usuario configura y consulta una campaña y recorre una batalla. El enunciado define el Hito 2 como un prototipo navegable con pantallas, enlaces habilitados, datos fijos y mensajes simulados. La implementación de las reglas y la persistencia de una partida corresponden al Hito 3.

Cuadro 7 “Alcance de la entrega y del producto final”

| Proceso | Evidencia en el Hito 2 | Desarrollo del Hito 3 |
| --- | --- | --- |
| Campaña y legiones | Formularios y cadena de mando con cuatro legiones de ejemplo. | Crear entidades con los datos ingresados y conservar sus relaciones. |
| Contratación y recursos | Catálogo oficial, presupuestos y un rechazo de ejemplo por fondos insuficientes. | Calcular contratos, validar cantidades y actualizar tropas y fondos. |
| Combate y reagrupación | Recorrido fijo de dos turnos, etapas, bajas, sueldos y conversión de ejemplo. | Ejecutar las reglas, aplicar las decisiones y determinar el término. |
| Bitácora | Registro de ejemplo con filtros por turno, tipo y texto. | Registrar los eventos que produzca cada simulación. |
| Guardar y cargar | Descarga de JSON de ejemplo y validación de su estructura al cargar. | Restaurar HP, tropas, turnos, recursos e historial de una partida. |

### Actor operativo y participantes

En el prototipo, el Jugador o Encargado de la simulación realiza todos los recorridos del diagrama de casos de uso. El lector de bitácora y el evaluador pueden revisar esas pantallas; no existen sesiones ni permisos diferenciados. El administrador representa una responsabilidad de soporte. El Senado, los cónsules y los Legatus son entidades del dominio, no cuentas de acceso.

### Persistencia y exclusiones

La descarga de archivos demuestra el diálogo de guardado de RT004. No sustituye la base de datos externa de RT002. El Hito 2 no modifica el escenario con los formularios ni reconstruye una campaña importada. Se mantienen las limitaciones ya descritas: sin entorno tridimensional, mapas de desplazamiento ni formaciones adicionales.

<!-- pagina -->

## 5.3. Criterios de aceptación y calidad

Los siguientes criterios permiten revisar el prototipo sin confundir su comportamiento visual con la implementación de las reglas del producto final. Son complementarios a los requisitos de la sección 3 y no agregan nuevos procesos de negocio.

Cuadro 8 “Criterios de aceptación del Hito 2”

| ID | Criterio verificable | Evidencia |
| --- | --- | --- |
| CA01 | Las pantallas y sus enlaces internos abren correctamente; una ruta inexistente muestra una página de error. | IT001 y revisión del navegador. |
| CA02 | El recorrido permite pasar por preparación, dos etapas, reagrupación, segundo turno y resultado. | AT001. |
| CA03 | La consola muestra cambios entre fotografías del escenario y el modo automático se detiene ante la selección de formaciones. | AT001 y MAN003. |
| CA04 | La bitácora filtra por turno, tipo y texto, e informa cuando no hay coincidencias. | MAN002. |
| CA05 | Guardar genera un JSON identificable; cargar rechaza contenido inválido e informa que no restaura una partida. | UT002, UT003, IT002 e IT003. |

### Condiciones de calidad

Usabilidad: conservar nombres, navegación y mensajes consistentes. Los avisos deben distinguir las acciones simuladas. Las barras de salud acompañan los valores numéricos y las pantallas identifican sus RU y CU.

Mantenibilidad: mantener separados catálogos, fotografías del escenario, consultas del modelo, rutas y plantillas. Los controladores no deben implementar cálculos de daño o mantenimiento. La interfaz podrá reutilizarse cuando se implemente el modelo del Hito 3.

Robustez: comprobar el contenido del archivo, además de su extensión; rechazar cargas mayores a 1 MB y versiones incompatibles. La carga no debe provocar errores internos ni cambiar el escenario de ejemplo.

Ambiente de operación: Python 3.10 o superior, Flask y un navegador. La aplicación se ejecuta localmente en el puerto 8000. Las fuentes externas tienen alternativas de sistema, por lo que la navegación debe continuar cuando no estén disponibles.

<!-- pagina -->

## 5.4. Arquitectura según las vistas 4+1

La arquitectura MVC descrita en la sección 4.5 puede analizarse mediante las vistas 4+1. MVC organiza responsabilidades; las vistas permiten explicar la estructura, la ejecución y el despliegue desde perspectivas complementarias.

Cuadro 9 “Vistas de arquitectura y su relación con el proyecto”

| Vista | Representación y responsabilidad |
| --- | --- |
| Escenarios (+1) | El diagrama de casos de uso de la Figura 1 y el recorrido crear campaña, contratar, combatir y consultar la bitácora explican las acciones del Jugador. |
| Lógica | La Figura 2 representa Campaña, Legión, Legatus, UnidadMilitar, Enfrentamiento, TurnoCombate, EtapaCombate y EstrategiaTáctica. Son el diseño del modelo funcional del Hito 3. |
| Desarrollo | La Figura 3 organiza los componentes. En el prototipo, modelo contiene catálogos y consultas; controlador agrupa las rutas; vista contiene plantillas, formatos, estilos y JavaScript. app.py integra las capas. |
| Procesos | El navegador envía una petición HTTP; Flask selecciona la ruta; el controlador consulta el escenario; Jinja genera HTML. El modo automático solicita el siguiente paso del recorrido, sin ejecutar un motor de batalla. |
| Física | La Figura 4 describe el despliegue previsto. En el Hito 2, Flask se ejecuta en el computador local y el navegador presenta la interfaz. El archivo JSON se descarga al equipo del usuario. |

### Separación del prototipo y el modelo funcional

RepositorioPrototipo entrega copias de los datos de ejemplo para que las consultas no alteren las fotografías de la demostración. Los catálogos conservan los valores de las tablas 2 y 3 del enunciado. Esta clase facilita el acceso al escenario; no reemplaza las clases de dominio de la Figura 2.

La validación de JSON pertenece al modelo y la elección de la respuesta HTTP al controlador. La base de datos externa y la reconstrucción del estado completo quedan pendientes para el Hito 3. Antes de implementarlas, el equipo debe precisar su servicio y su integración con GestorPersistencia.

<!-- pagina -->

## 5.5. Riesgos y decisiones del dominio

La evaluación siguiente es cualitativa y sirve para priorizar el trabajo. La probabilidad expresa una estimación del equipo para la planificación; no corresponde a una medición estadística.

Cuadro 10 “Riesgos del proyecto y medidas de mitigación”

| Riesgo | Probabilidad e impacto | Mitigación |
| --- | --- | --- |
| RSK01. Confundir el prototipo con el sistema terminado. | Alta / Alto | Informar qué datos y acciones son simulados y separar la evidencia de cada hito. |
| RSK02. Divergencia entre informe, diagramas y código. | Media / Alto | Mantener la trazabilidad RU/CU/pantalla/prueba y revisar los cambios antes de integrarlos. |
| RSK03. Archivo corrupto o incompatible. | Media / Alto | Validar JSON, versión, estructura y tamaño; mostrar un mensaje y conservar el escenario. |
| RSK04. Reglas ambiguas que produzcan cálculos distintos. | Alta / Alto | Registrar las dudas y acordar criterios con la contraparte antes de implementar el combate. |
| RSK05. Fallas de navegación o del entorno durante la exposición. | Media / Medio | Ejecutar las pruebas, ensayar en el equipo de presentación y comprobar las fuentes de sistema. |

### Decisiones que deben resolverse antes del Hito 3

Daño y selección de objetivos: el enunciado describe un daño global y después ataques individuales. También combina referencias a selección equiprobable y a proporciones de unidades. Debe precisarse cómo se relacionan ambos cálculos. El ejemplo de ATK 43 y DEF 37 menciona 8 de daño, aunque la resta es 6.

Bonos y economía: acordar el orden de aplicación de porcentajes, los redondeos, el tratamiento de daños no positivos y el límite del descuento de mantenimiento por esclavos. Los valores fijos del prototipo no constituyen una definición de estas reglas.

Condición de término y persistencia: precisar los casos en que sobreviven ingenieros o solo auxiliares, y qué datos permiten reconstruir unidades heridas. El archivo del prototipo no acredita esa reconstrucción ni la implementación de RT002.

<!-- pagina -->

# 6. Plan de pruebas del Hito 2

El plan verifica la estabilidad del prototipo y prepara la validación posterior del producto. El enunciado contempla el plan de pruebas como un entregable opcional del Hito 3; incorporarlo desde esta entrega permite organizar sus evidencias sin anticipar resultados del motor de combate.

### Tipos de prueba y alcance

Pruebas unitarias: aislamiento de los datos de consulta, coherencia del ejemplo exportado y rechazo de estructuras JSON incompatibles. No comprueban fórmulas de ataque, defensa, bajas ni mantenimiento.

Pruebas de integración: renderizado de pantallas y enlaces, descarga y validación de archivos, rechazo de cargas inválidas y participantes de batalla inexistentes o sin tropas. Se ejecutan con el cliente de pruebas de Flask.

Prueba de aceptación: recorrido de campaña, contratación simulada, dos turnos de batalla, reagrupación, resultado y bitácora. La aceptación se limita al flujo del Hito 2.

Pruebas manuales: MAN001 revisa legibilidad y navegación con teclado en escritorio y pantalla estrecha; MAN002 revisa filtros y ausencia de resultados en la bitácora; MAN003 revisa automático, pausa y diálogos de archivos. Deben conservarse capturas o un registro de observaciones.

### Organización de la verificación

Cuadro 11 “Secuencia propuesta para una sesión de revisión”

| Inicio relativo | Duración | Responsable y evidencia |
| --- | --- | --- |
| T+00 min | 15 min | Desarrollo: preparar el entorno y ejecutar las ocho pruebas automatizadas; guardar su salida. |
| T+15 min | 30 min | Revisión: realizar MAN001 a MAN003; registrar incidencias y capturas. |
| T+45 min | 15 min | Equipo: ensayar la demostración y revisar la trazabilidad del informe. |

T representa la fecha y hora de la sesión que el equipo registre en Kanban antes de la presentación. Esta secuencia es una propuesta de trabajo, no un compromiso de calendario. La salida requiere pruebas aprobadas y ausencia de errores que bloqueen el recorrido.

<!-- pagina -->

## 6.1. Definición de una prueba con excepciones

Caso de uso: CU014 Recuperar una campaña. Requisito relacionado: RU010. En el Hito 2 se valida el archivo y se muestra la campaña de ejemplo; no se reconstruye una partida con los valores importados.

### Precondiciones y recursos

Aplicación iniciada, acceso a Cargar campaña y disponibilidad del JSON generado por Guardar campaña. El entorno automatizado utiliza Python, las dependencias del proyecto y unittest. La comprobación de diálogos requiere un navegador y acceso al sistema de archivos.

### Flujo esperado

El usuario elige el archivo exportado. El sistema comprueba formato, versión, nombre de campaña, legiones, tropas, cónsules e historial. Si es compatible, informa que el archivo fue validado y abre el panel de ejemplo. La configuración de la demostración no cambia.

Cuadro 12 “Escenarios alternativos de carga”

| Entrada o situación | Respuesta esperada |
| --- | --- |
| No se adjunta archivo o la extensión no es .json. | Mostrar un aviso de error y volver al inicio. |
| Archivo renombrado como .json con texto o datos binarios. | Rechazar el contenido sin anunciar una carga exitosa. |
| JSON sin los campos requeridos o con una versión incompatible. | Informar que la estructura no es compatible. |
| Tropas con cantidades negativas, texto o valores booleanos. | Rechazar la estructura del archivo. |
| Relaciones de cónsules y legiones inconsistentes. | Rechazar las referencias inválidas o duplicadas. |
| Carga superior a 1 MB. | Mostrar la página de archivo demasiado grande, con respuesta HTTP 413. |

### Postcondiciones y responsabilidades

En todos los escenarios se conserva el ejemplo del Hito 2. Un error permite volver al inicio y repetir la operación. Desarrollo mantiene UT003, IT002 e IT003; revisión comprueba los diálogos mediante MAN003; el equipo conserva la evidencia y registra los defectos en Kanban.

La prueba se considera aprobada cuando cada entrada produce la respuesta esperada, no aparece un error interno y los archivos inválidos no se anuncian como restaurados. La restauración exacta de HP, turno y tropas requerirá nuevas pruebas en el Hito 3.

<!-- pagina -->

## 6.2. Matriz de trazado de requisitos y pruebas

La matriz complementa la sección 3.3. La cobertura corresponde a navegación, presentación y validación del ejemplo; no acredita la implementación funcional completa de cada RU.

Cuadro 13 “Trazabilidad de requisitos, casos de uso y pruebas”

| RU | Casos de uso | Pruebas | Evidencia del Hito 2 |
| --- | --- | --- | --- |
| RU001 | CU001, CU002 | IT001, AT001 | Formularios y panel de campaña. |
| RU002 | CU001, CU003 | IT001, AT001 | Contratación y rechazo simulados. |
| RU003 | CU004 | UT001, IT001 | Consulta de fuerzas sin alterar el escenario. |
| RU004 | CU005 | IT004, AT001 | Participantes válidos y acceso al recorrido. |
| RU005 | CU006 | AT001, MAN003 | Formación y detención del automático. |
| RU006 | CU007 a CU010 | AT001 | Etapas, cierre y resultado predefinidos. |
| RU007 | CU011 | AT001 | Reagrupación y segundo turno. |
| RU008 | CU010, CU012 | IT001, MAN002 | Bitácora y filtros de eventos. |
| RU009 | CU013 | UT002, IT002, MAN003 | Descarga del ejemplo JSON. |
| RU010 | CU014 | UT003, IT002, IT003 | Validación del archivo y manejo de errores. |

### Evidencia automatizada y evolución

La suite contiene tres pruebas unitarias, cuatro de integración y una de aceptación. Se ejecuta con python -m unittest discover -s tests -v. Los identificadores de sus métodos permiten relacionar los resultados con esta matriz.

Para el Hito 3 deberán agregarse pruebas de límites del Legatus, contratación y presupuesto, sinergias, objetivos permitidos, bajas y unidades heridas, mantenimiento, conversión y término del combate. La integración deberá comprobar la base de datos externa y la recuperación exacta de una campaña guardada.

Los anexos individuales se completarán con los registros semanales reales exigidos por el enunciado. La planificación detallada se mantiene en Kanban.
