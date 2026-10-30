# Legio Imperium: prototipo navegable (Hito 2)

Pantallas del sistema con datos de ejemplo fijos, links habilitados y mensajes simulados.
Todavía no calcula nada: la lógica real llega en el Hito 3, sobre esta misma estructura.

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

Después abre http://127.0.0.1:8000 en el navegador. Para detenerlo, presiona `Ctrl+C` en la terminal.

## Arquitectura: MVC con Flask

| Capa | Carpeta | En el Hito 2 | En el Hito 3 |
|---|---|---|---|
| Modelo | `modelo/` | Datos fijos de una campaña de ejemplo (`datos_prototipo.py`) | Clases del diagrama de clases (Campaña, Legión, Legatus, MotorCombate…) y la base de datos |
| Vista | `vista/` | Plantillas HTML (Jinja), estilos y el JS de la interfaz | Las mismas pantallas, con datos reales |
| Controlador | `controlador/` | Rutas de Flask: navegación y mensajes simulados | Piden al modelo que aplique las reglas y eligen la vista |

`app.py` arma la aplicación y une las tres capas.

## Pantallas

Cada pantalla muestra arriba a la derecha los casos de uso y requisitos que cubre; al pasar el mouse por un código se ve su nombre.

| Pantalla | Ruta | Casos de uso | Requisitos |
|---|---|---|---|
| Inicio | `/` | CU014 | RU010 |
| Nueva campaña | `/campana/nueva` | CU001 | RU001 |
| Panel de campaña: cadena de mando y legiones | `/campana` | CU001, CU004 | RU001, RU003 |
| Crear legión, con Legatus y presupuesto | `/legiones/nueva` | CU001, CU002 | RU001 |
| Contratar tropas | `/legiones/<id>/contratar` | CU003 | RU002 |
| Fuerzas y recursos de una legión | `/legiones/<id>` | CU004 | RU003 |
| Preparar enfrentamiento | `/combate/preparar` | CU005 | RU004 |
| Consola de simulación (paso a paso o automático) | `/combate/paso/<n>` | CU006, CU007, CU008, CU010, CU013 | RU005, RU006, RU009 |
| Contratar tropas al elegir la formación del turno 2 | `/combate/contratar/<id>` | CU003, CU006 | RU002 |
| Reagrupación: sueldos y conversión de esclavos | `/combate/reagrupacion` | CU009, CU011 | RU006, RU007 |
| Resultado de la batalla | `/combate/resultado` | CU007, CU009 | RU006 |
| Bitácora con filtros | `/bitacora` | CU010, CU012 | RU008 |
| Guardar / Cargar campaña | Botones de la cabecera | CU013, CU014 | RU009, RU010 |

Los ids de legión son `xiii`, `x`, `i` e `ix`. En plena batalla solo contratan `xiii` e `i`, las que combaten.

## Relaciones del diagrama de casos de uso

El prototipo sigue el diagrama de casos de uso nuevo. El Jugador inicia directamente CU001 a CU006 y CU011 a CU014; a CU007, CU008, CU009 y CU010 se llega desde otros casos de uso.

| Relación | Dónde se ve en el prototipo |
|---|---|
| CU002 Asignar Legatus y presupuesto «include» CU001 Crear legiones | *Crear legión* pide el Legatus y el presupuesto en el mismo formulario |
| CU003 Contratar tropas del catálogo «include» CU001 Crear legiones | *Crear legión y contratar tropas* lleva directo al catálogo |
| CU004 Revisar fuerzas y recursos «include» CU003 Contratar tropas | *Contratar tropas* en las fuerzas de cada legión |
| CU005 Preparar un enfrentamiento «extend» CU004 Revisar fuerzas | *Preparar enfrentamiento* en las fuerzas de una legión con tropas |
| CU001 Crear legiones «include» CU005 Preparar un enfrentamiento | *Preparar enfrentamiento* en el panel de campaña |
| CU007 Desarrollar el combate «include» CU005 Preparar un enfrentamiento | La consola de simulación parte de *Preparar enfrentamiento* |
| CU006 Elegir la formación «include» CU007 Desarrollar el combate | *Confirmar formaciones* resuelve la etapa 1 del turno 2 |
| CU003 Contratar tropas «extend» CU006 Elegir la formación | *+ Contratar tropas* en cada legión durante la preparación del turno 2 |
| CU008 Calcular efectos de ataque y bajas «extend» CU007 | Daño, reparto y bajas en el centro de la consola |
| CU009 Cobrar mantenimiento de legiones «extend» CU007 | Sueldos al cerrar cada turno: reagrupación y resultado |
| CU010 Anotar sucesos en la bitácora «extend» CU007 | Consola de eventos bajo el campo de batalla |
| CU011 Reorganizar el ejército «extend» CU007 | Conversión de esclavos en la reagrupación |
| CU013 Guardar el progreso de campaña «extend» CU007 | *Guardar progreso* en los controles de la consola |
| CU012 Examinar el registro de batalla «extend» CU010 | *Abrir bitácora completa* desde la consola de eventos |

## Recorrido sugerido para la presentación

1. **Inicio** → *Nueva campaña* → *Crear campaña*.
2. **Panel** → *+ Crear legión* → *Crear legión y contratar tropas* → *Firmar contrato*: muestra las fuerzas de la legión.
3. **Panel** → Legio IX Hispana → *Contratar tropas* → *Firmar contrato*: el contrato excede el presupuesto y aparece el error.
4. *Preparar enfrentamiento* → *Iniciar batalla*.
5. En la consola, *Paso a paso* o *Automático* hasta cerrar el turno 1.
6. **Reagrupación**: sueldos pagados y conversión de esclavos → formaciones del turno 2.
7. **Turno 2 · Preparación**: *+ Contratar tropas* en la Legio XIII Gemina abre el catálogo con los 6.097 denarios que le quedan y los sueldos del turno → *Volver a la batalla* → *Guardar progreso*.
8. Turno 2 → **Resultado**: la Legio I Pompeiana no puede pagar los sueldos y pierde.
9. **Bitácora**: filtrar por turno, tipo de evento o texto.
10. *Guardar campaña* y *Cargar campaña* desde la cabecera.

## Verificación del prototipo

```bash
python -m unittest discover -s tests -v
```

Incluye tres pruebas unitarias, cuatro de integración y una de aceptación del recorrido. No valida las reglas de combate ni la persistencia del Hito 3.

Los catálogos oficiales están en `modelo/catalogos.py`; las fotografías de la demostración, en `modelo/datos_prototipo.py`. `RepositorioPrototipo` centraliza las consultas y devuelve copias para conservar el escenario. Los controladores no dependen de las constantes internas del ejemplo.

## Qué es «de mentira»

- Las cifras de la batalla salen de `modelo/datos_prototipo.py`. Se prepararon a mano como ejemplo; no acreditan la implementación de las reglas del enunciado.
- Los formularios no guardan nada: muestran un mensaje y pasan a la pantalla siguiente.
- La batalla siempre recorre las mismas etapas, sin importar las formaciones que se elijan ni las tropas que se contraten en el turno 2.
- *Guardar campaña* escribe un JSON de la configuración inicial de ejemplo, identificado como `prototipo-hito-2`; no guarda el paso actual de combate. En los navegadores que lo permiten abre «Guardar como»; en los demás lo descarga.
- *Cargar campaña* abre el selector y valida extensión, JSON, versión, estructura y relaciones básicas. Acepta archivos de hasta 1 MB. Muestra el ejemplo y un aviso; no restaura una partida.
- Las fuentes (Cinzel y Source Sans 3) se cargan desde Google Fonts. Sin internet, el navegador usa sus fuentes de sistema.
