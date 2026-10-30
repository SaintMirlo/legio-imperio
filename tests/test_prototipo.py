"""Pruebas del prototipo navegable; no acreditan el motor de combate del Hito 3."""
import io
import json
import unittest
from html.parser import HTMLParser
from urllib.parse import urlsplit

from app import crear_app
from modelo.prototipo import ArchivoCampanaInvalido, RepositorioPrototipo, validar_archivo_campana


class Enlaces(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rutas = set()

    def handle_starttag(self, tag, attrs):
        valores = dict(attrs)
        if tag in ("a", "link") and valores.get("href", "").startswith("/"):
            self.rutas.add(valores["href"])
        if tag in ("script", "img") and valores.get("src", "").startswith("/"):
            self.rutas.add(valores["src"])


class ModeloPrototipoTests(unittest.TestCase):
    def setUp(self):
        self.prototipo = RepositorioPrototipo()

    def test_UT001_consultas_no_alteran_el_escenario(self):
        legion = self.prototipo.legion("xiii")
        legion["tropas"]["legionario"] = 0
        paso = self.prototipo.paso(0)
        paso["estado"]["xiii"]["presupuesto"] = 0
        self.assertEqual(self.prototipo.legion("xiii")["tropas"]["legionario"], 500)
        self.assertEqual(self.prototipo.paso(0)["estado"]["xiii"]["presupuesto"], 12050)
        for invalido in (-1, self.prototipo.cantidad_pasos, True):
            with self.subTest(paso=invalido), self.assertRaises(IndexError):
                self.prototipo.paso(invalido)

    def test_UT002_exportacion_coherente_con_la_configuracion_inicial(self):
        contenido = self.prototipo.archivo_de_ejemplo()
        self.assertEqual(validar_archivo_campana(contenido), self.prototipo.campana()["nombre"])
        self.assertEqual(contenido["modo"], "prototipo-hito-2")
        self.assertIsNone(contenido["batalla"])
        self.assertTrue(all(e["turno"] == 0 for e in contenido["bitacora"]))
        self.assertEqual(contenido["legiones"][0]["tropas"], self.prototipo.legion("xiii")["tropas"])

    def test_UT003_rechaza_estructuras_json_incompatibles(self):
        invalidos = [None, [], {}, {"formato": "otro", "version": 1}]
        for campo, valor in (("version", True), ("version", 2), ("legiones", []), ("bitacora", {}), ("consules", []), ("batalla", {})):
            contenido = self.prototipo.archivo_de_ejemplo()
            contenido[campo] = valor
            invalidos.append(contenido)
        for valor in (-1, True, "500"):
            contenido = self.prototipo.archivo_de_ejemplo()
            contenido["legiones"][0]["tropas"]["legionario"] = valor
            invalidos.append(contenido)
        contenido = self.prototipo.archivo_de_ejemplo()
        contenido["consules"][0]["legiones"] = ["inexistente"]
        invalidos.append(contenido)
        contenido = self.prototipo.archivo_de_ejemplo()
        contenido["legiones"][0]["consul"] = "Otro cónsul"
        invalidos.append(contenido)
        for contenido in invalidos:
            with self.subTest(contenido=contenido), self.assertRaises(ArchivoCampanaInvalido):
                validar_archivo_campana(contenido)


class NavegacionTests(unittest.TestCase):
    def setUp(self):
        self.app = crear_app({"TESTING": True, "SECRET_KEY": "solo-pruebas"})
        self.cliente = self.app.test_client()

    def subir(self, contenido, nombre="campana.json", **opciones):
        respuesta = self.cliente.post(
            "/campana/cargar", data={"archivo": (io.BytesIO(contenido), nombre)}, **opciones,
        )
        self.addCleanup(respuesta.close)
        self.addCleanup(respuesta.request.close)
        self.addCleanup(respuesta.request.environ["wsgi.input"].close)
        return respuesta

    def test_IT001_pantallas_y_enlaces_internos_sin_errores(self):
        rutas = ["/", "/campana", "/campana/nueva", "/legiones/nueva", "/combate/preparar",
                 "/combate/reagrupacion", "/combate/resultado", "/bitacora"]
        rutas += [f"/legiones/{id_legion}{final}" for id_legion in ("xiii", "x", "i", "ix")
                  for final in ("", "/contratar")]
        rutas += [f"/combate/paso/{i}" for i in range(6)]
        rutas += ["/combate/contratar/xiii", "/combate/contratar/i"]
        enlaces = Enlaces()
        for ruta in rutas:
            with self.subTest(ruta=ruta):
                respuesta = self.cliente.get(ruta)
                self.assertEqual(respuesta.status_code, 200)
                enlaces.feed(respuesta.get_data(as_text=True))
        for ruta in enlaces.rutas:
            with self.subTest(enlace=ruta):
                with self.cliente.get(ruta) as respuesta:
                    self.assertEqual(respuesta.status_code, 200)
        for ruta in ("/no-existe", "/legiones/otra", "/combate/paso/6", "/combate/contratar/x"):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.cliente.get(ruta).status_code, 404)

    def test_IT002_exportar_validar_sin_restaurar_datos(self):
        exportada = self.cliente.get("/campana/exportar")
        self.assertEqual(exportada.mimetype, "application/json")
        self.assertIn("attachment", exportada.headers["Content-Disposition"])
        contenido = exportada.get_json()
        contenido["campana"] = "Campaña distinta"
        respuesta = self.subir(json.dumps(contenido).encode(), follow_redirects=True)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("todavía no se restaura una partida", respuesta.get_data(as_text=True))
        self.assertEqual(self.cliente.get("/campana/exportar").get_json()["campana"], exportada.get_json()["campana"])

    def test_IT003_carga_invalida_no_se_anuncia_como_exitosa(self):
        for contenido, nombre in ((b'no es json', "renombrado.json"), (b'[]', "lista.json"),
                                   (b'{}', "vacio.json"), (b'\xff\xfe', "binario.json"), (b'{}', "otro.txt")):
            with self.subTest(nombre=nombre):
                respuesta = self.subir(contenido, nombre, follow_redirects=True)
                self.assertEqual(respuesta.status_code, 200)
                self.assertIn("aviso-error", respuesta.get_data(as_text=True))
                self.assertNotIn("validado.", respuesta.get_data(as_text=True))
        respuesta = self.subir(b'{}', "otro.txt", headers={"Referer": "https://example.com"})
        self.assertFalse(urlsplit(respuesta.location).netloc)
        self.assertEqual(self.cliente.post("/campana/cargar").status_code, 302)
        self.assertEqual(self.subir(b'x' * (1024 * 1024 + 1)).status_code, 413)

    def test_IT004_preparacion_rechaza_participantes_invalidos(self):
        for a, b in (("xiii", "xiii"), ("xiii", "ix"), ("otra", "i"), (None, None)):
            with self.subTest(a=a, b=b):
                datos = {"legion_a": a, "legion_b": b} if a else {}
                respuesta = self.cliente.post("/combate/preparar", data=datos, follow_redirects=True)
                self.assertIn("aviso-error", respuesta.get_data(as_text=True))
                self.assertEqual(respuesta.request.path, "/combate/preparar")
        self.assertEqual(self.cliente.post("/combate/cerrar-turno", data={"turno": "99"}).status_code, 400)

    def test_AT001_recorrido_completo_del_hito_2(self):
        pasos = [
            ("/campana/nueva", {"nombre": "Demostración"}, "/campana"),
            ("/legiones/nueva", {"nombre": "Legión prueba", "legatus": "Legatus prueba"}, "/legiones/x/contratar"),
            ("/legiones/x/contratar", {}, "/legiones/x"),
            ("/combate/preparar", {"legion_a": "xiii", "legion_b": "i", "atacante": "a"}, "/combate/paso/0"),
        ]
        for ruta, datos, destino in pasos:
            with self.subTest(ruta=ruta):
                respuesta = self.cliente.post(ruta, data=datos, follow_redirects=True)
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta.request.path, destino)
        rechazada = self.cliente.post("/legiones/ix/contratar", data={}, follow_redirects=True)
        self.assertEqual(rechazada.request.path, "/legiones/ix/contratar")
        self.assertIn("Presupuesto insuficiente", rechazada.get_data(as_text=True))
        for paso in (1, 2):
            self.assertEqual(self.cliente.get(f"/combate/paso/{paso}").status_code, 200)
        respuesta = self.cliente.post("/combate/cerrar-turno", data={"turno": "1"}, follow_redirects=True)
        self.assertEqual(respuesta.request.path, "/combate/reagrupacion")
        respuesta = self.cliente.post("/combate/reagrupacion", data={}, follow_redirects=True)
        self.assertEqual(respuesta.request.path, "/combate/paso/3")
        respuesta = self.cliente.get("/combate/paso/3?auto=1")
        self.assertNotIn("data-auto-segundos", respuesta.get_data(as_text=True))
        respuesta = self.cliente.post("/combate/formaciones", data={}, follow_redirects=True)
        self.assertEqual(respuesta.request.path, "/combate/paso/4")
        self.assertEqual(self.cliente.get("/combate/paso/5").status_code, 200)
        respuesta = self.cliente.post("/combate/cerrar-turno", data={"turno": "2"}, follow_redirects=True)
        self.assertEqual(respuesta.request.path, "/combate/resultado")
        self.assertIn("Victoria", respuesta.get_data(as_text=True))
        self.assertEqual(self.cliente.get("/bitacora").status_code, 200)


if __name__ == "__main__":
    unittest.main()
