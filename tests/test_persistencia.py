"""Pruebas de persistencia: base de datos SQLite (GestorPersistencia) y archivos JSON de campaña."""
import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime

from modelo.archivo import exportar_campana, importar_campana, nombre_archivo
from modelo.campana import Campana
from modelo.errores import ArchivoCampanaInvalido, ReglaInvalida
from modelo.legion import Legion
from modelo.persistencia import CampanaNoEncontrada, GestorPersistencia

INSTANTES = {"creada", "actualizada", "creado", "actualizado", "instante"}


def sin_instantes(valor):
    """a_dict() sin fechas y horas, que dependen del reloj y no del juego."""
    if isinstance(valor, dict):
        return {clave: sin_instantes(v) for clave, v in valor.items() if clave not in INSTANTES}
    if isinstance(valor, list):
        return [sin_instantes(v) for v in valor]
    return valor


def agregar_legion(campana, nombre, tropas, restante, bono_atk=0, bono_def=0, consul=1):
    """Crea la legión y contrata sus tropas; le quedan `restante` denarios tras el contrato."""
    legion = campana.crear_legion(nombre, consul, f"Legatus de {nombre}", bono_atk, bono_def,
                                  Legion.costo_contrato(tropas) + restante)
    campana.contratar_tropas(legion.id, tropas)
    return legion


def campana_simple(nombre="Guerra de las Galias"):
    """Campaña con dos legiones con tropas y sin enfrentamientos."""
    campana = Campana.iniciar(nombre, "Julio César", "Pompeyo Magno")
    agregar_legion(campana, "Legio X", {"legionario": 50, "ballesta": 5}, 1000, bono_atk=5)
    agregar_legion(campana, "Legio XII", {"legionario": 40, "caballeria": 10}, 1000, consul=2)
    return campana


def campana_completa():
    """Campaña con tres legiones (una cuarta fue disuelta), un enfrentamiento terminado y otro en curso
    con unidades heridas, refuerzos, conversión de esclavos y cambio de formación."""
    campana = Campana.iniciar("Guerra Civil de César", "Julio César", "Pompeyo Magno")
    i = agregar_legion(campana, "Legio I", {"legionario": 200, "caballeria": 50, "ballesta": 30, "ingeniero": 10,
                                            "esclavo": 100}, 17_600, bono_atk=10, bono_def=5)
    ii = agregar_legion(campana, "Legio II", {"legionario": 150, "caballeria": 80, "ballesta": 40}, 12_490,
                        bono_atk=25, bono_def=-10, consul=2)
    campana.iniciar_enfrentamiento("Batalla de Farsalia", i.id, ii.id, semilla=1)
    while campana.enfrentamiento_activo():
        campana.avanzar_combate()
    campana.eliminar_legion(ii.id)  # la vencida se disuelve; su enfrentamiento queda en el historial

    iii = agregar_legion(campana, "Legio III", {"legionario": 150, "caballeria": 40, "ballesta": 30, "esclavo": 60},
                         20_000, bono_atk=20)
    iv = agregar_legion(campana, "Legio IV", {"legionario": 120, "caballeria": 60, "ballesta": 40, "ingeniero": 20},
                        20_000, bono_atk=25, bono_def=-5, consul=2)
    campana.iniciar_enfrentamiento("Batalla de Munda", iii.id, iv.id, semilla=2)
    for _ in range(3):
        campana.avanzar_combate()
    campana.contratar_refuerzos("b", {"ballesta": 5})
    campana.avanzar_combate({"a": {"formacion": "orbis", "convertir": {"legionario": 10}}})
    return campana


def hay_heridos(campana):
    return any(unidad.esta_herida() for legion in campana.legiones.values()
               for lista in legion.unidades.values() for unidad in lista)


class EscenarioTests(unittest.TestCase):
    def test_la_campana_completa_cubre_lo_que_se_quiere_guardar(self):
        """Comprueba el escenario de las demás pruebas: heridos, un combate terminado y otro en curso."""
        campana = campana_completa()
        terminado, activo = campana.enfrentamientos
        self.assertEqual(terminado.estado, "finalizada")
        self.assertTrue(activo.en_curso)
        self.assertEqual(activo.turno_actual.formaciones["a"], "orbis")
        self.assertEqual(activo.participantes["a"].convertidos["legionario"], 10)
        self.assertEqual(activo.participantes["b"].contratados["ballesta"], 5)
        self.assertEqual(len(campana.legiones), 3)
        self.assertTrue(hay_heridos(campana))


class BaseDeDatosTests(unittest.TestCase):
    def setUp(self):
        carpeta = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(carpeta.cleanup)
        self.ruta = os.path.join(carpeta.name, "legio_imperium.db")
        self.gestor = GestorPersistencia(self.ruta)

    def test_ida_y_vuelta_de_una_campana_completa(self):
        """RT002: guardar y cargar devuelve exactamente la misma campaña (a_dict() idéntico)."""
        campana = campana_completa()
        self.gestor.guardar_campana(campana)
        cargada = self.gestor.cargar_campana(campana.id)
        self.assertEqual(cargada.a_dict(), campana.a_dict())
        self.assertTrue(hay_heridos(cargada))
        # Volver a guardar reemplaza la versión anterior sin duplicar filas.
        self.gestor.guardar_campana(cargada)
        self.assertEqual(self.gestor.cargar_campana(campana.id).a_dict(), campana.a_dict())
        self.assertEqual(len(self.gestor.listar_campanas()), 1)

    def test_la_campana_recuperada_sigue_jugando_igual(self):
        """Una campaña cargada de la base y la misma cargada de un archivo continúan el combate igual."""
        campana = campana_completa()
        self.gestor.guardar_campana(campana)
        desde_base = self.gestor.cargar_campana(campana.id)
        desde_archivo = importar_campana(exportar_campana(campana))
        pasos = campana.enfrentamiento_activo().pasos
        for copia in (desde_base, desde_archivo):
            copia.avanzar_combate(paso=pasos)
            copia.avanzar_combate(paso=pasos + 1)
        self.assertEqual(desde_base.enfrentamientos[-1].pasos, pasos + 2)
        self.assertEqual(sin_instantes(desde_base.a_dict()), sin_instantes(desde_archivo.a_dict()))

    def test_consultas(self):
        """existe, nombre_campana, ultima_campana_id y listar_campanas (de la más reciente a la más antigua)."""
        self.assertEqual(self.gestor.listar_campanas(), [])
        self.assertIsNone(self.gestor.ultima_campana_id())
        galias = campana_simple()
        civil = campana_completa()
        galias.actualizada = "2026-01-01T10:00:00"
        civil.actualizada = "2026-01-02T10:00:00"
        self.gestor.guardar_campana(galias)
        self.gestor.guardar_campana(civil)

        self.assertTrue(self.gestor.existe(galias.id))
        self.assertFalse(self.gestor.existe("f" * 32))
        self.assertEqual(self.gestor.nombre_campana(galias.id), "Guerra de las Galias")
        self.assertIsNone(self.gestor.nombre_campana("f" * 32))
        self.assertIsNone(self.gestor.cargar_campana("f" * 32))
        self.assertEqual(self.gestor.ultima_campana_id(), civil.id)
        lista = self.gestor.listar_campanas()
        self.assertEqual([c["id"] for c in lista], [civil.id, galias.id])
        self.assertEqual([c["nombre"] for c in lista], ["Guerra Civil de César", "Guerra de las Galias"])
        self.assertEqual([c["legiones"] for c in lista], [3, 2])
        self.assertEqual([bool(c["en_combate"]) for c in lista], [True, False])

        galias.actualizada = "2026-01-03T10:00:00"
        self.gestor.guardar_campana(galias)
        self.assertEqual(self.gestor.ultima_campana_id(), galias.id)

    def test_eliminar_campana(self):
        """eliminar_campana borra la campaña y todas sus filas (en cascada) sin tocar las demás."""
        galias = campana_simple()
        civil = campana_completa()
        self.gestor.guardar_campana(galias)
        self.gestor.guardar_campana(civil)
        self.gestor.eliminar_campana(civil.id)
        self.assertFalse(self.gestor.existe(civil.id))
        self.assertIsNone(self.gestor.cargar_campana(civil.id))
        self.assertEqual(self.gestor.cargar_campana(galias.id).a_dict(), galias.a_dict())
        tablas = ("consul", "legion", "legatus", "unidad", "enfrentamiento", "participante", "turno", "etapa", "evento")
        with closing(sqlite3.connect(self.ruta)) as conexion:
            for tabla in tablas:
                filas = conexion.execute(f"SELECT COUNT(*) FROM {tabla} WHERE campana_id = ?", (civil.id,)).fetchone()[0]
                self.assertEqual(filas, 0, tabla)

    def test_editar_guarda_si_el_bloque_termina_bien(self):
        """editar(id) entrega la campaña y la guarda al salir del bloque sin errores."""
        campana = campana_simple()
        self.gestor.guardar_campana(campana)
        with self.gestor.editar(campana.id) as editada:
            editada.crear_legion("Legio Nueva", 1, "Quinto Cicerón", 0, 0, 500)
        nombres = [legion.nombre for legion in self.gestor.cargar_campana(campana.id).legiones.values()]
        self.assertIn("Legio Nueva", nombres)

    def test_editar_no_guarda_si_el_bloque_falla(self):
        """editar(id) no guarda nada si el bloque lanza un error: la base queda como estaba."""
        campana = campana_simple()
        self.gestor.guardar_campana(campana)
        antes = self.gestor.cargar_campana(campana.id).a_dict()
        with self.assertRaises(ReglaInvalida):
            with self.gestor.editar(campana.id) as editada:
                legion = editada.crear_legion("Legio Fantasma", 1, "Quinto Cicerón", 0, 0, 500)
                editada.contratar_tropas(legion.id, {"legionario": 1000})  # cuesta 5.000: no alcanza
        self.assertEqual(self.gestor.cargar_campana(campana.id).a_dict(), antes)

    def test_editar_una_campana_que_no_existe(self):
        """editar(id) con un id desconocido lanza CampanaNoEncontrada."""
        with self.assertRaises(CampanaNoEncontrada):
            with self.gestor.editar("f" * 32):
                pass


class ArchivoTests(unittest.TestCase):
    def assertArchivoInvalido(self, contenido, inicio):
        with self.assertRaises(ArchivoCampanaInvalido) as contexto:
            importar_campana(contenido)
        self.assertTrue(str(contexto.exception).startswith(inicio), str(contexto.exception))

    def test_ida_y_vuelta_en_json(self):
        """RU009/RU010: exportar e importar devuelve la misma campaña (texto, bytes o UTF-8 con BOM)."""
        campana = campana_completa()
        texto = exportar_campana(campana)
        datos = json.loads(texto)
        self.assertEqual((datos["formato"], datos["version"]), ("legio-imperium", 2))
        for contenido in (texto, texto.encode("utf-8"), ("﻿" + texto).encode("utf-8")):
            self.assertEqual(importar_campana(contenido).a_dict(), campana.a_dict())

    def test_nombre_del_archivo(self):
        """El archivo se llama legio-imperium-<nombre sin tildes>-AAAA-MM-DD-HHMM.json."""
        campana = campana_simple("Guerra Civil de César")
        self.assertEqual(nombre_archivo(campana, datetime(2026, 11, 17, 18, 30)),
                         "legio-imperium-guerra-civil-de-cesar-2026-11-17-1830.json")
        self.assertRegex(nombre_archivo(campana), r"^legio-imperium-guerra-civil-de-cesar-\d{4}-\d{2}-\d{2}-\d{4}\.json$")
        campana.nombre = "¡Ñandú & Águila!"
        self.assertEqual(nombre_archivo(campana, datetime(2026, 1, 2, 3, 4)), "legio-imperium-nandu-aguila-2026-01-02-0304.json")

    def test_archivo_que_no_es_json(self):
        """Un archivo que no es JSON se rechaza con un mensaje claro."""
        for contenido in (b"esto no es json", b"\xff\xfe\x00basura", "{'formato': 'legio-imperium'}", ""):
            with self.subTest(contenido=contenido):
                self.assertArchivoInvalido(contenido, "El archivo no contiene un JSON válido.")

    def test_json_que_no_es_una_campana(self):
        """Un JSON sin "formato": "legio-imperium" no es una campaña."""
        for datos in ([], "texto", {"version": 2, "campana": {}}, {"formato": "otro-juego", "version": 2}):
            with self.subTest(datos=datos):
                self.assertArchivoInvalido(json.dumps(datos), "Ese archivo no es una campaña de Legio Imperium.")

    def test_archivo_del_prototipo(self):
        """Un archivo de la versión 1 (prototipo del Hito 2) se rechaza con su propio mensaje."""
        contenido = json.dumps({"formato": "legio-imperium", "version": 1, "legiones": []})
        self.assertArchivoInvalido(contenido, "Ese archivo es del prototipo del Hito 2")

    def test_version_desconocida(self):
        """Una versión distinta de 1 y 2 no es compatible."""
        for version in (3, 0, "2", None):
            datos = json.loads(exportar_campana(campana_simple()))
            datos["version"] = version
            with self.subTest(version=version):
                self.assertArchivoInvalido(json.dumps(datos), "La versión del archivo no es compatible")

    def test_datos_alterados(self):
        """Un archivo modificado a mano que rompe una regla se rechaza: «El archivo está dañado o fue modificado»."""
        def presupuesto_negativo(c):
            c["legiones"][0]["presupuesto"] = -1

        def hp_sobre_el_maximo(c):
            c["legiones"][0]["unidades"]["legionario"] = [[21, 1]]

        def bono_imposible(c):
            c["legiones"][0]["legatus"]["atk"] = 99

        def hueco_en_la_bitacora(c):
            del c["bitacora"][1]

        def nombres_repetidos(c):
            c["legiones"][1]["nombre"] = c["legiones"][0]["nombre"]

        def nombres_repetidos_con_mayusculas(c):
            c["legiones"][1]["nombre"] = c["legiones"][0]["nombre"].upper()

        def combate_con_legion_inexistente(c):
            activo = next(e for e in c["enfrentamientos"] if e["estado"] == "en_curso")
            id_legion = activo["participantes"]["a"]["legion_id"]
            c["legiones"] = [legion for legion in c["legiones"] if legion["id"] != id_legion]

        base = exportar_campana(campana_completa())
        for alterar in (presupuesto_negativo, hp_sobre_el_maximo, bono_imposible, hueco_en_la_bitacora,
                        nombres_repetidos, nombres_repetidos_con_mayusculas, combate_con_legion_inexistente):
            datos = json.loads(base)
            alterar(datos["campana"])
            with self.subTest(alteracion=alterar.__name__):
                self.assertArchivoInvalido(json.dumps(datos), "El archivo está dañado o fue modificado")


if __name__ == "__main__":
    unittest.main()
