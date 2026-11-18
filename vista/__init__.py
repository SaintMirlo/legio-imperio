"""Vista (V de MVC): plantillas HTML, estilos, JavaScript de la interfaz y formatos."""
from modelo.catalogos import (CATALOGO, ESTRATEGIA, ESTRATEGIAS, ETAPAS, INTEGRANTES_MAXIMOS, LEGIONES_MAXIMAS,
                              PRESUPUESTO_MAXIMO, TIPOS_EVENTO, TURNOS_MAXIMOS, UNIDAD, UNIDADES)
from modelo.combate import ESTADOS, FASES
from modelo.unidades import EsclavoAuxiliar, Ingeniero
from vista.formato import registrar_filtros


def registrar_vista(app):
    registrar_filtros(app)
    # Las macros importadas sin contexto también necesitan los catálogos.
    app.jinja_env.globals.update(
        catalogo=CATALOGO, unidades=UNIDAD, tipos_unidad=UNIDADES, estrategias=ESTRATEGIAS,
        estrategia_por_clave=ESTRATEGIA, tipos_evento=TIPOS_EVENTO, etapas=ETAPAS,
        fases=FASES, estados_combate=ESTADOS,
        limites={"presupuesto": PRESUPUESTO_MAXIMO, "integrantes": INTEGRANTES_MAXIMOS,
                 "legiones": LEGIONES_MAXIMAS, "turnos": TURNOS_MAXIMOS,
                 "descuento_esclavos": EsclavoAuxiliar.DESCUENTO_MAXIMO},
        reglas={"esclavos_bloque": EsclavoAuxiliar.POR_BLOQUE, "esclavos_descuento": EsclavoAuxiliar.DESCUENTO_POR_BLOQUE,
                "ingenieros_bloque": Ingeniero.POR_BLOQUE},
    )
