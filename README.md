# Legio Imperium (Hito 3)

Gestión táctica y simulación de batallas del ejército romano. Aplicación web local en Flask con
arquitectura MVC: las legiones, los contratos, el combate por turnos, los sueldos y la bitácora
siguen las reglas del enunciado y se guardan en una base de datos SQLite.

## Cómo ejecutarlo

Requiere Python 3.10 o superior.

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python app.py
```

Abre http://127.0.0.1:8000 en el navegador. Para detenerlo, presiona `Ctrl+C` en la terminal.

La primera ejecución crea `instance/legio_imperium.db` (la base de datos) e
`instance/clave_secreta.txt` (la clave de las sesiones). La carpeta `instance/` no se sube al
repositorio. Para usar otra base de datos, define la variable de entorno `LEGIO_DB` con su ruta.

Al abrir la aplicación se continúa la última campaña modificada.

## Recorrido sugerido para la presentación

1. **Inicio** → *Nueva campaña*: nombre de la campaña y los dos cónsules del Senado.
2. **Panel** → *+ Crear legión*: nombre, cónsul, Legatus con sus bonos de ATK y DEF (el %Costo se
   calcula solo) y presupuesto. Crea al menos dos.
3. **Contratar tropas**: escribe cantidades y mira cómo cambian en vivo el costo, el saldo, los
   sueldos por turno y el ATK y la DEF de la legión. Un contrato que excede el presupuesto se
   rechaza.
4. *Preparar enfrentamiento*: elige atacante y defensora; la pantalla muestra si la sinergia de
   Triplex Acies está activa y el daño previsto del turno 1.
5. **Consola**: *Resolver etapa 1 →* avanza un paso; *▶ Automático* avanza solo a la velocidad
   elegida. Las barras de salud se animan con cada golpe y la bitácora se actualiza en el panel
   con scroll.
6. Desde el turno 2: cambia la formación (Cuneus o Orbis), convierte esclavos o contrata
   refuerzos en la preparación del turno.
7. **Resultado**: veredicto, bajas, gastos y sueldos de cada legión, y el detalle turno a turno.
8. **Bitácora**: filtros por enfrentamiento, turno, tipo de suceso y texto.
9. *Guardar campaña* y *Cargar campaña* en la cabecera.

Una batalla entre legiones con muchos legionarios puede durar varios turnos sin daño: la
sinergia de Triplex Acies (+35% DEF) hace que la DEF total supere al ATK total. Para que haya
bajas, la legión atacante necesita más ATK: Cuneus, más caballería o ballestas, o un Legatus
ofensivo. La consola lo advierte cuando la defensa resiste.

## Arquitectura: MVC con Flask

| Capa | Carpeta | Contenido |
|---|---|---|
| Modelo | `modelo/` | Reglas del juego sin dependencias de Flask: clases del diagrama de clases, motor de combate, bitácora, archivos de campaña y base de datos |
| Vista | `vista/` | Plantillas Jinja, estilos (`static/css/legio.css`) y la interacción del navegador (`static/js/legio.js`) |
| Controlador | `controlador/` | Rutas de Flask: leen los formularios, piden al modelo que aplique las reglas y eligen la vista |

`app.py` arma la aplicación y une las tres capas.

### Modelo

| Archivo | Clases |
|---|---|
| `campana.py` | `Campana`: cónsules, legiones, enfrentamientos y bitácora; valida cada acción del jugador |
| `legion.py` | `Legion`: tropas, presupuesto, contratos, atributos, sueldos y conversión de esclavos |
| `legatus.py` | `Legatus`: bonos de ATK y DEF entre −25% y +25%; %Costo = %ATK + %DEF |
| `unidades.py` | `UnidadMilitar` y sus subclases `Legionario`, `Caballeria`, `Ballesta`, `Ingeniero` y `EsclavoAuxiliar`, con sus habilidades |
| `estrategias.py` | `EstrategiaTactica` y sus subclases `TriplexAcies`, `Cuneus` y `Orbis` |
| `combate.py` | `Enfrentamiento`, `TurnoCombate`, `EtapaCombate` y `MotorCombate`, que resuelve cada etapa |
| `bitacora.py` | `Bitacora` y `EventoBatalla` |
| `persistencia.py` | `GestorPersistencia`: guarda y carga campañas en SQLite |
| `archivo.py` | Exporta e importa la campaña completa en un archivo JSON |
| `catalogos.py` | Tablas 2 y 3 del enunciado (unidades y estrategias) y los límites del juego |

### Consola de batalla

Cada botón de la consola envía el paso al servidor con `fetch`. El servidor aplica las reglas,
guarda la campaña y responde con el fragmento HTML actualizado (tablas, barras, bitácora), que
reemplaza al anterior sin recargar la página. El modo automático repite el paso con una pausa
y se detiene al terminar el combate, ante un error o si el jugador edita una decisión. Sin
JavaScript, los mismos formularios funcionan recargando la página.

Cada paso lleva un número: si dos pestañas intentan avanzar la misma batalla, la segunda recibe
un aviso y no avanza dos veces.

## Reglas implementadas

### Legiones y economía

- Cada legión tiene un Legatus nombrado por uno de los dos cónsules. Sus bonos de ATK y DEF van
  de −25% a +25% y su %Costo es la suma de ambos.
- Los contratos cuestan el precio del catálogo por unidad; el Legatus no lo modifica. Una
  legión admite hasta 10.000 integrantes; una campaña, hasta 30 legiones.
- Sueldos por turno = costo base de las tropas × (100 + %Costo) × (100 − descuento) / 10.000,
  redondeado. Los esclavos descuentan 15% por cada 50 (como máximo 90%).
- Los sueldos se pagan al cerrar cada turno. Una legión que no puede pagarlos no paga nada y
  pierde; si ninguna puede, el enfrentamiento termina en empate.

### Combate

- Turno 1: ambas legiones forman en Triplex Acies. Desde el turno 2, cada una elige su formación
  en la preparación; Cuneus requiere caballería y Orbis, legionarios.
- Cada turno tiene dos etapas: en la 1 ataca la legión atacante y en la 2 la defensora. Los
  atributos se recalculan al inicio de cada etapa.
- Los porcentajes se suman: %ATK = Legatus + formación; %DEF = Legatus + formación + sinergia de
  Triplex (+35% con al menos 50% de legionarios) + ingenieros (+1% por cada 10).
- ATK_TOTAL y DEF_TOTAL suman los atributos de todas las unidades vivas con sus bonos.
  **Daño = ATK_TOTAL − DEF_TOTAL**; si no es positivo, la defensa resiste. Una legión en Cuneus
  recibe +50% de daño.
- El daño se reparte entre legionarios, caballería y ballestas según cuántos son (con 700, 200
  y 100, un daño de 600 se reparte 420, 120 y 60). Los ingenieros y los esclavos aportan ATK y
  DEF a los totales, pero no atacan.
- La sinergia de Triplex da +15% a la parte de las ballestas; los ingenieros, +2% por cada 10;
  Cuneus da +50% a la parte de la caballería.
- Cada golpe elige al azar un objetivo válido y vale ATK − DEF de ambas unidades, como mínimo 1.
  Después se aplican las habilidades: la caballería hace +20% a los legionarios, la ballesta +50%
  a la caballería y el legionario ignora 20% del daño en formación cerrada (Triplex y Orbis).
- Objetivos: legionarios y caballería solo golpean a ballestas, ingenieros y esclavos cuando el
  enemigo ya no tiene legionarios ni caballería; en Cuneus la caballería también golpea esclavos;
  las ballestas golpean a cualquiera. En Orbis, la caballería no ataca y las ballestas e
  ingenieros no reciben daño.
- Una unidad con HP 0 muere y deja de contar de inmediato. Pierde la legión que se queda sin
  integrantes que no sean esclavos.
- En la preparación de cada turno se pueden contratar refuerzos y, desde el turno 2, convertir
  esclavos en legionarios (5 denarios) o caballería (12). Se convierten primero los esclavos más
  heridos y las nuevas unidades llegan con el HP completo.
- Un enfrentamiento se puede abandonar: termina sin vencedor y las legiones conservan sus tropas
  y presupuestos.

### Decisiones donde el enunciado no es explícito

| Tema | Decisión |
|---|---|
| Ejemplo de la página 5 (ATK 43 contra DEF 37) | Se aplica la fórmula del enunciado: 43 − 37 = 6 de daño (el texto dice 8) |
| Daño que sobra al matar a una unidad | Se pierde; no pasa a otra unidad |
| Caballería en Orbis | No ataca, así que no suma ATK |
| Descuento por esclavos | Máximo 90%, para que los sueldos nunca lleguen a cero |
| Duración máxima | 100 turnos: si nadie cae ni se queda sin dinero, empate |
| Heridas | Las unidades conservan su HP entre enfrentamientos |
| Azar | Cada enfrentamiento tiene una semilla; una partida guardada y recuperada sigue igual |

## Persistencia

- **Base de datos (RT002).** SQLite, incluida en Python. Las tablas siguen la jerarquía del
  enunciado: campaña → cónsules → legiones → Legatus y unidades, y campaña → enfrentamientos →
  participantes, turnos y etapas, más la bitácora. Cada acción guarda la campaña completa en una
  transacción; si una regla rechaza la acción, la base queda como estaba.
- **Archivos (RT004).** *Guardar campaña* abre el diálogo «Guardar como» en Chrome y Edge (en
  otros navegadores, la descarga) y escribe un JSON con toda la campaña: legiones, tropas con su
  HP, enfrentamientos con cada turno y la bitácora. *Cargar campaña* abre el selector de
  archivos, valida cada dato con las mismas reglas del juego y restaura la campaña, incluso con
  una batalla en curso. Los archivos del prototipo del Hito 2 se rechazan con un aviso, porque
  solo traían datos de ejemplo.

## Pruebas

```bash
python -m unittest discover -s tests -v
```

| Archivo | Qué prueba |
|---|---|
| `tests/test_modelo.py` | Reglas: Legatus, contratos, sueldos, formaciones y sinergias, fórmulas de daño y reparto, objetivos, conversiones, fin del combate |
| `tests/test_persistencia.py` | Guardar y cargar en SQLite y en archivos JSON; rechazo de archivos inválidos o alterados |
| `tests/test_aplicacion.py` | Recorrido completo en la aplicación web, de la campaña nueva al resultado, la bitácora y los archivos |

## Trazabilidad

La interfaz no muestra los códigos de requisitos; esta tabla los relaciona con las pantallas.

| Requisito | Dónde se cumple |
|---|---|
| RU001 Crear y configurar legiones | Panel de campaña, *Crear legión* y *Configurar* |
| RU002 Contratar tropas del catálogo | *Contratar tropas* y refuerzos en la consola |
| RU003 Calcular y consultar estadísticas | Panel, fuerzas de cada legión y tablas de la consola |
| RU004 Preparar un enfrentamiento | *Preparar enfrentamiento* |
| RU005 Elegir la formación del turno | Selector de formación en la consola |
| RU006 Desarrollar el combate por turnos | Consola paso a paso o automática y resultado |
| RU007 Reorganizar el ejército | Conversión de esclavos y refuerzos en la consola |
| RU008 Consultar la bitácora de batalla | Panel de bitácora en la consola y pantalla *Bitácora* |
| RU009 Guardar el progreso de campaña | Base de datos en cada acción y *Guardar campaña* |
| RU010 Recuperar una campaña | *Cargar campaña* y la reapertura de la última campaña |
| RT001 Interfaz web | Flask en http://127.0.0.1:8000 |
| RT002 Persistencia externa | `modelo/persistencia.py` (SQLite) |
| RT003 Arquitectura MVC | Carpetas `modelo/`, `vista/` y `controlador/` |
| RT004 Guardar y cargar mediante archivos | `modelo/archivo.py` y los botones de la cabecera |

Las fuentes (Pinyon Script y Plus Jakarta Sans) se cargan desde Google Fonts. Sin internet, el
navegador usa sus fuentes de sistema.
