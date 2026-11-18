"""Pruebas de la aplicación Flask: el recorrido completo con formularios reales y el cliente de pruebas.

Cada prueba usa una base de datos SQLite nueva en una carpeta temporal. Todas las páginas HTML
que se piden se revisan para que no muestren identificadores de requisitos (CU001, RU008…).
"""
import io
import json
import os
import re
import tempfile
import unittest
from urllib.parse import urlsplit

from app import crear_app
from modelo.catalogos import UNIDADES

INSIGNIA_DE_REQUISITO = re.compile(r"\b[CR]U0\d\d")
FETCH = {"X-Requested-With": "fetch"}


class AplicacionTests(unittest.TestCase):
    def setUp(self):
        carpeta = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(carpeta.cleanup)
        self.carpeta = carpeta.name
        self.app = self.nueva_app("legio_imperium.db")
        self.cliente = self.app.test_client()

    def nueva_app(self, archivo):
        return crear_app({"TESTING": True, "DATABASE": os.path.join(self.carpeta, archivo), "SECRET_KEY": "pruebas"})

    # --- Ayudantes ------------------------------------------------------------------------

    def pedir(self, metodo, url, estado, cliente=None, **opciones):
        """Hace la petición, comprueba el código HTTP y revisa que el HTML no tenga insignias de requisitos."""
        respuesta = getattr(cliente or self.cliente, metodo)(url, **opciones)
        self.assertEqual(respuesta.status_code, estado, f"{metodo.upper()} {url}")
        if respuesta.mimetype == "text/html":
            insignia = INSIGNIA_DE_REQUISITO.search(respuesta.get_data(as_text=True))
            self.assertIsNone(insignia, f"{url} muestra el identificador de requisito {insignia and insignia.group()}")
        return respuesta

    def get(self, url, estado=200, **opciones):
        return self.pedir("get", url, estado, **opciones)

    def post(self, url, datos=None, estado=302, **opciones):
        return self.pedir("post", url, estado, data=datos, **opciones)

    @staticmethod
    def html(respuesta):
        return respuesta.get_data(as_text=True)

    @staticmethod
    def destino(respuesta):
        return urlsplit(respuesta.headers["Location"]).path

    def crear_campana(self):
        respuesta = self.post("/campana/nueva", {"nombre": "Guerra Civil de César", "consul_1": "Julio César",
                                                 "consul_2": "Pompeyo Magno"})
        self.assertEqual(self.destino(respuesta), "/campana")

    def datos_legion(self, nombre, consul, legatus, bono_atk, bono_def, presupuesto):
        return {"nombre": nombre, "consul": str(consul), "legatus": legatus, "bono_atk": str(bono_atk),
                "bono_def": str(bono_def), "presupuesto": str(presupuesto)}

    def crear_legion(self, *datos):
        respuesta = self.post("/legiones/nueva", self.datos_legion(*datos))
        coincidencia = re.fullmatch(r"/legiones/(\d+)/contratar", self.destino(respuesta))
        self.assertIsNotNone(coincidencia, self.destino(respuesta))
        return int(coincidencia.group(1))

    def contratar(self, id_legion, **tropas):
        respuesta = self.post(f"/legiones/{id_legion}/contratar", {tipo: str(tropas.get(tipo, 0)) for tipo in UNIDADES})
        self.assertEqual(self.destino(respuesta), f"/legiones/{id_legion}")

    def campana_con_dos_legiones(self):
        """La aplicación sortea la semilla; con estas tropas la batalla termina en 7 a 10 pasos
        (comprobado con 3.000 semillas al azar), muy por debajo del tope de 400 de la prueba."""
        self.crear_campana()
        a = self.crear_legion("Legio I", 1, "Marco Antonio", 10, 5, 20_000)
        self.contratar(a, legionario=200, caballeria=50, ballesta=30, ingeniero=10, esclavo=100)
        b = self.crear_legion("Legio II", 2, "Tito Labieno", 25, -10, 15_000)
        self.contratar(b, legionario=150, caballeria=80, ballesta=40)
        return a, b

    def iniciar_batalla(self, a, b, nombre="Batalla de Farsalia"):
        respuesta = self.post("/combate/preparar", {"atacante": str(a), "defensora": str(b), "nombre": nombre})
        self.assertEqual(self.destino(respuesta), "/combate/")

    def avanzar(self, paso, visto=0, **campos):
        """Un paso de la consola por fetch: devuelve (respuesta, html, data-paso del fragmento)."""
        respuesta = self.post("/combate/avanzar", {"paso": str(paso), "visto": str(visto), **campos}, estado=200,
                              headers=FETCH)
        html = self.html(respuesta)
        return respuesta, html, int(re.search(r'data-paso="(\d+)"', html).group(1))

    def campana_guardada(self, app=None):
        gestor = (app or self.app).extensions["persistencia"]
        return gestor.cargar_campana(gestor.ultima_campana_id())

    def cargar_archivo(self, contenido, nombre="campana.json", cliente=None):
        datos = {"archivo": (io.BytesIO(contenido), nombre), "volver": "/campana"}
        return self.post("/campana/cargar", datos, cliente=cliente, content_type="multipart/form-data")

    # --- Campaña y legiones ---------------------------------------------------------------

    def test_inicio_sin_campana(self):
        """Sin campaña, el inicio responde 200 y el panel redirige al inicio con un aviso."""
        self.assertIn("Nueva campaña", self.html(self.get("/")))
        respuesta = self.get("/campana", estado=302)
        self.assertEqual(self.destino(respuesta), "/")
        self.assertIn("Crea una campaña nueva o carga un archivo", self.html(self.get("/")))

    def test_crear_campana(self):
        """Crear la campaña lleva al panel; dos cónsules con el mismo nombre responden 400."""
        respuesta = self.post("/campana/nueva", {"nombre": "Guerra", "consul_1": "Julio", "consul_2": "julio"}, estado=400)
        self.assertIn("dos cónsules distintos", self.html(respuesta))
        self.get("/campana", estado=302)  # sigue sin campaña
        self.crear_campana()
        panel = self.html(self.get("/campana"))
        for texto in ("Guerra Civil de César", "Julio César", "Pompeyo Magno"):
            self.assertIn(texto, panel)

    def test_crear_legion(self):
        """Crear una legión con su Legatus lleva a contratar; un bono fuera de [−25, +25] responde 400."""
        self.crear_campana()
        self.get("/legiones/nueva")
        respuesta = self.post("/legiones/nueva", self.datos_legion("Legio I", 1, "Marco Antonio", 30, 0, 1000), estado=400)
        self.assertIn("entre −25% y +25%", self.html(respuesta))
        id_legion = self.crear_legion("Legio I", 1, "Marco Antonio", 10, 5, 1000)
        self.get(f"/legiones/{id_legion}/contratar")
        legion = self.campana_guardada().legion(id_legion)
        self.assertEqual((legion.legatus.bono_atk, legion.legatus.bono_def, legion.presupuesto), (10, 5, 1000))
        respuesta = self.post("/legiones/nueva", self.datos_legion("legio i", 2, "Otro", 0, 0, 1000), estado=400)
        self.assertIn("Ya existe una legión", self.html(respuesta))

    def test_simular_y_contratar(self):
        """La vista previa del contrato responde JSON; el contrato descuenta el costo y lleva a las fuerzas."""
        self.crear_campana()
        id_legion = self.crear_legion("Legio I", 1, "Marco Antonio", 10, 5, 1000)
        vista = self.get(f"/legiones/{id_legion}/simular?legionario=10&caballeria=2").get_json()
        self.assertTrue(vista["valido"])
        self.assertEqual((vista["costo"], vista["restante"]), (74, 926))  # el Legatus no cambia el precio
        self.assertEqual(vista["texto"]["costo"], "74")
        vista = self.get(f"/legiones/{id_legion}/simular?legionario=1000").get_json()
        self.assertFalse(vista["valido"])
        self.assertEqual(vista["costo"], 5000)
        self.assertIn("Presupuesto insuficiente", vista["mensaje"])
        vista = self.get(f"/legiones/{id_legion}/simular?legionario=diez").get_json()
        self.assertFalse(vista["valido"])
        self.assertNotIn("texto", vista)

        self.post(f"/legiones/{id_legion}/contratar", {"legionario": "1000"}, estado=400)
        self.contratar(id_legion, legionario=10, caballeria=2)
        self.assertIn("Legio I", self.html(self.get(f"/legiones/{id_legion}")))
        legion = self.campana_guardada().legion(id_legion)
        self.assertEqual((legion.presupuesto, legion.contar()["legionario"], legion.contar()["caballeria"]), (926, 10, 2))
        self.get("/legiones/999", estado=404)
        self.get("/legiones/999/contratar", estado=404)

    # --- Batalla --------------------------------------------------------------------------

    def test_batalla_completa(self):
        """Preparar, avanzar por fetch paso a paso hasta el final, ver el resultado y la bitácora filtrada."""
        a, b = self.campana_con_dos_legiones()
        self.get("/combate/preparar")
        self.iniciar_batalla(a, b)
        self.assertIn('data-paso="0"', self.html(self.get("/combate/")))

        # En el turno 1 no se puede elegir otra formación: error y la consola no avanza.
        respuesta, html, paso = self.avanzar(0, formacion_a="cuneus")
        self.assertEqual((respuesta.headers["X-Legio-Estado"], paso), ("error", 0))
        self.assertIn("En el primer turno ambas legiones forman en Triplex Acies.", html)

        respuesta, html, paso = self.avanzar(0)
        self.assertEqual((respuesta.headers["X-Legio-Estado"], paso), ("ok", 1))
        self.assertIn('data-fase="etapa_1"', html)
        self.assertNotIn("<html", html)  # es un fragmento, no la página completa

        # Un paso viejo (doble clic) no avanza: la consola solo se actualiza.
        respuesta, html, paso = self.avanzar(0)
        self.assertEqual(paso, 1)
        self.assertIn("La consola mostraba un paso anterior", html)

        visto = 0
        for _ in range(400):
            respuesta, html, nuevo = self.avanzar(paso, visto)
            self.assertEqual(respuesta.headers["X-Legio-Estado"], "ok")
            self.assertEqual(nuevo, paso + 1)
            paso = nuevo
            visto = int(re.search(r'name="visto" value="(\d+)"', html).group(1))
            if 'data-en-curso="0"' in html:
                break
        else:
            self.fail("La batalla no terminó en 400 pasos.")
        enfrentamiento = self.campana_guardada().enfrentamiento(1)
        self.assertEqual(enfrentamiento.estado, "finalizada")
        veredicto = (f"Vence {enfrentamiento.participantes[enfrentamiento.ganador].nombre}"
                     if enfrentamiento.ganador else "Empate")
        self.assertIn(veredicto, html)

        self.assertEqual(self.destino(self.get("/combate/", estado=302)), "/combate/1")
        resultado = self.html(self.get("/combate/1"))
        self.assertIn(veredicto, resultado)
        self.get("/combate/99", estado=404)

        self.assertIn("Batalla de Farsalia", self.html(self.get("/bitacora")))
        filtrada = self.html(self.get("/bitacora?enfrentamiento=1&tipo=combate&q=ATACA"))
        tipos = re.findall(r'<li class="registro-evento tipo-(\w+)', filtrada)
        esperados = self.campana_guardada().bitacora.obtener_historial(enfrentamiento=1, tipo="combate", texto="ataca")
        self.assertGreater(len(tipos), 0)
        self.assertEqual(len(tipos), len(esperados))
        self.assertEqual(set(tipos), {"combate"})

    def test_abandonar_batalla(self):
        """Abandonar lleva a la página de resultado; mientras combate, la legión no se puede configurar."""
        a, b = self.campana_con_dos_legiones()
        self.iniciar_batalla(a, b)
        self.avanzar(0)
        respuesta = self.post(f"/legiones/{a}/configurar", self.datos_legion("Legio I", 1, "Otro", 0, 0, 10), estado=400)
        self.assertIn("está en combate", self.html(respuesta))
        self.assertEqual(self.destino(self.post(f"/legiones/{a}/eliminar")), f"/legiones/{a}")
        self.assertEqual(self.destino(self.get(f"/legiones/{a}/contratar", estado=302)), "/combate/")
        self.assertIn(a, self.campana_guardada().legiones)

        respuesta = self.post("/combate/abandonar")
        self.assertEqual(self.destino(respuesta), "/combate/1")
        resultado = self.html(self.get("/combate/1"))
        self.assertIn("abandonado", resultado)
        enfrentamiento = self.campana_guardada().enfrentamiento(1)
        self.assertEqual((enfrentamiento.estado, enfrentamiento.ganador), ("abandonada", None))
        # Ya sin combate, la legión vuelve a poder configurarse.
        respuesta = self.post(f"/legiones/{a}/configurar", self.datos_legion("Legio I", 1, "Otro", 0, 0, 10))
        self.assertEqual(self.destino(respuesta), f"/legiones/{a}")

    # --- Archivos de campaña --------------------------------------------------------------

    def test_guardar_y_cargar_campana(self):
        """Guardar descarga un .json; cargarlo restaura la campaña (en la misma base o en una nueva)."""
        a, b = self.campana_con_dos_legiones()
        self.iniciar_batalla(a, b)
        self.avanzar(0)
        respuesta = self.get("/campana/guardar")
        self.assertEqual(respuesta.mimetype, "application/json")
        self.assertRegex(respuesta.headers["Content-Disposition"],
                         r'^attachment; filename="legio-imperium-guerra-civil-de-cesar-\d{4}-\d{2}-\d{2}-\d{4}\.json"$')
        contenido = respuesta.get_data()
        guardada = json.loads(contenido)["campana"]

        # Después de guardar, la campaña cambia: se abandona la batalla y se crea otra legión.
        self.post("/combate/abandonar")
        self.crear_legion("Legio III", 1, "Quinto Cicerón", 0, 0, 1000)

        respuesta = self.cargar_archivo(contenido, "respaldo.json")
        self.assertEqual(self.destino(respuesta), "/combate/")  # el archivo tenía una batalla en curso
        consola = self.html(self.get("/combate/"))
        self.assertIn("cargada", consola)
        self.assertIn("Reemplazó la versión que había en la base de datos.", consola)
        restaurada = self.campana_guardada().a_dict()
        self.assertEqual(restaurada["legiones"], guardada["legiones"])
        self.assertEqual(restaurada["enfrentamientos"], guardada["enfrentamientos"])
        self.assertEqual(restaurada["bitacora"][:-1], guardada["bitacora"])
        self.assertIn("respaldo.json", restaurada["bitacora"][-1]["texto"])

        # En una aplicación con otra base de datos, el archivo crea la campaña.
        otra_app = self.nueva_app("otra.db")
        otro_cliente = otra_app.test_client()
        self.cargar_archivo(contenido, cliente=otro_cliente)
        consola = self.html(self.get("/combate/", cliente=otro_cliente))
        self.assertIn("Quedó guardada en la base de datos.", consola)
        self.assertEqual(self.campana_guardada(otra_app).a_dict()["legiones"], guardada["legiones"])

    def test_cargar_archivo_invalido(self):
        """Un archivo inválido no cambia nada: redirige y muestra el motivo."""
        self.crear_campana()
        antes = self.campana_guardada().a_dict()
        casos = {
            b"esto no es json": "El archivo no contiene un JSON válido.",
            json.dumps({"formato": "otro"}).encode(): "Ese archivo no es una campaña de Legio Imperium.",
            json.dumps({"formato": "legio-imperium", "version": 1}).encode(): "Ese archivo es del prototipo del Hito 2",
        }
        for contenido, mensaje in casos.items():
            with self.subTest(mensaje=mensaje):
                respuesta = self.cargar_archivo(contenido, "malo.json")
                self.assertEqual(self.destino(respuesta), "/campana")
                self.assertIn(mensaje, self.html(self.get("/campana")))
        respuesta = self.post("/campana/cargar", {"volver": "/campana"}, content_type="multipart/form-data")
        self.assertEqual(self.destino(respuesta), "/campana")
        self.assertIn("Elige un archivo de campaña", self.html(self.get("/campana")))
        self.assertEqual(self.campana_guardada().a_dict(), antes)

    # --- Rutas y pantallas ----------------------------------------------------------------

    def test_ruta_inexistente(self):
        """Una ruta que no existe responde 404 con la página propia."""
        self.assertIn("no figura en los mapas", self.html(self.get("/no-existe", estado=404)))

    def test_ninguna_pagina_muestra_identificadores_de_requisitos(self):
        """Ninguna pantalla muestra insignias como CU001 o RU008 (pedido del usuario); pedir() revisa cada HTML."""
        self.get("/")
        self.get("/campana/nueva")
        a, b = self.campana_con_dos_legiones()
        for url in ("/", "/campana/nueva", "/campana", "/legiones/nueva", f"/legiones/{a}", f"/legiones/{a}/contratar",
                    f"/legiones/{a}/configurar", "/combate/preparar", f"/combate/comparar?atacante={a}&defensora={b}",
                    "/bitacora"):
            self.get(url)
        self.iniciar_batalla(a, b)
        self.get("/combate/")
        paso = 0
        for _ in range(4):  # etapa 1, etapa 2, sueldos y la etapa 1 del turno 2
            _, html, paso = self.avanzar(paso)
            if 'data-en-curso="0"' in html:
                break
        self.get(f"/legiones/{a}")
        self.post("/combate/abandonar")
        self.get("/combate/1")
        self.get("/bitacora?enfrentamiento=1")
        self.get("/no-existe", estado=404)


if __name__ == "__main__":
    unittest.main()
