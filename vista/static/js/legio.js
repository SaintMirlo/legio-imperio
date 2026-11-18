/* Comportamiento de la interfaz de Legio Imperium (Hito 3).
   Las reglas del juego viven en el modelo (Python). Aquí solo hay interacción: avisos,
   diálogos de archivo, vistas previas en vivo y la consola de batalla (paso a paso y
   automática), que pide al servidor cada paso y reemplaza el fragmento con la respuesta. */
(() => {
  "use strict";

  const CABECERAS = { "X-Requested-With": "fetch" };
  const avisos = document.getElementById("avisos");

  // --- Avisos -----------------------------------------------------------------------------

  function cerrarDespues(aviso, milisegundos = 7000) {
    setTimeout(() => aviso.classList.add("saliendo"), milisegundos);
  }

  function avisar(texto, categoria = "info") {
    const aviso = document.createElement("div");
    aviso.className = `aviso aviso-${categoria}`;
    aviso.setAttribute("role", "status");
    const mensaje = document.createElement("span");
    mensaje.textContent = texto;
    const cerrar = document.createElement("button");
    cerrar.type = "button";
    cerrar.className = "aviso-cerrar";
    cerrar.setAttribute("aria-label", "Cerrar aviso");
    cerrar.textContent = "×";
    aviso.append(mensaje, cerrar);
    avisos.append(aviso);
    cerrarDespues(aviso);
  }

  avisos.querySelectorAll(".aviso").forEach((aviso) => cerrarDespues(aviso));
  avisos.addEventListener("click", (evento) => {
    const boton = evento.target.closest(".aviso-cerrar");
    if (boton) boton.closest(".aviso").remove();
  });
  avisos.addEventListener("animationend", (evento) => {
    if (evento.animationName === "aviso-sale") evento.target.remove();
  });

  // --- Guardar campaña (CU013): diálogo «Guardar como» del sistema ------------------------

  function marcaDeTiempo(fecha = new Date()) {
    const dos = (n) => String(n).padStart(2, "0");
    return `${fecha.getFullYear()}-${dos(fecha.getMonth() + 1)}-${dos(fecha.getDate())}-${dos(fecha.getHours())}${dos(fecha.getMinutes())}`;
  }

  document.querySelectorAll("[data-guardar]").forEach((boton) => {
    boton.addEventListener("click", async () => {
      const sugerido = `${boton.dataset.prefijo || "legio-imperium"}-${marcaDeTiempo()}.json`;
      let destino = null;
      try {
        // El diálogo se abre antes de descargar: así conserva el permiso del clic.
        if ("showSaveFilePicker" in window) {
          destino = await window.showSaveFilePicker({
            suggestedName: sugerido,
            types: [{ description: "Campaña de Legio Imperium", accept: { "application/json": [".json"] } }],
          });
        }
        boton.disabled = true;
        const respuesta = await fetch(boton.dataset.guardar, { headers: CABECERAS });
        if (!respuesta.ok) throw new Error(`El servidor respondió ${respuesta.status}`);
        const contenido = await respuesta.blob();
        if (destino) {
          const escritura = await destino.createWritable();
          await escritura.write(contenido);
          await escritura.close();
          avisar(`Campaña guardada en «${destino.name}».`, "exito");
        } else {
          const nombre = /filename="([^"]+)"/.exec(respuesta.headers.get("Content-Disposition") || "")?.[1] || sugerido;
          const enlace = document.createElement("a");
          enlace.href = URL.createObjectURL(contenido);
          enlace.download = nombre;
          document.body.append(enlace);
          enlace.click();
          enlace.remove();
          setTimeout(() => URL.revokeObjectURL(enlace.href), 2000);
          avisar(`Campaña guardada como «${nombre}».`, "exito");
        }
      } catch (error) {
        if (error.name === "AbortError") avisar("Guardado cancelado.", "info");
        else avisar("No se pudo guardar la campaña.", "error");
      } finally {
        boton.disabled = false;
      }
    });
  });

  // --- Cargar campaña (CU014): selector de archivos del sistema ---------------------------

  const cargar = document.querySelector("[data-cargar]");
  cargar?.addEventListener("change", () => {
    if (cargar.files.length) cargar.form.submit();
  });
  document.querySelectorAll("[data-abrir-cargar]").forEach((boton) => {
    boton.addEventListener("click", () => cargar?.click());
  });

  // --- Confirmaciones de acciones que no se pueden deshacer -------------------------------

  document.addEventListener("submit", (evento) => {
    const formulario = evento.target;
    if (formulario.matches?.("[data-confirmar]") && !window.confirm(formulario.dataset.confirmar)) {
      evento.preventDefault();
      evento.stopImmediatePropagation();
    }
  }, true);

  // --- Legatus: valor de cada deslizador y %Costo = %ATK + %DEF ---------------------------

  const conSigno = (n) => (n > 0 ? `+${n}%` : n < 0 ? `−${-n}%` : "0%");
  const bonos = [...document.querySelectorAll("[data-bono]")];
  function refrescarBonos() {
    let suma = 0;
    for (const deslizador of bonos) {
      const valor = Number(deslizador.value);
      suma += valor;
      const salida = document.querySelector(`output[for="${deslizador.id}"]`);
      if (salida) salida.textContent = conSigno(valor);
    }
    const costo = document.getElementById("bono-costo");
    if (costo) costo.textContent = conSigno(suma);
  }
  bonos.forEach((deslizador) => deslizador.addEventListener("input", refrescarBonos));

  // --- Contratar tropas: vista previa del costo y de la legión resultante -----------------

  const contrato = document.querySelector("[data-contrato]");
  if (contrato) {
    const campos = [...contrato.querySelectorAll('input[type="number"]')];
    const vista = (clave) => contrato.querySelector(`[data-vista="${clave}"]`);
    const confirmar = contrato.querySelector("[data-confirmar-contrato]");
    let pedido = 0;
    let espera = null;

    async function actualizar() {
      const parametros = new URLSearchParams();
      campos.forEach((campo) => parametros.set(campo.name, campo.value.trim()));
      const numero = ++pedido;
      try {
        const respuesta = await fetch(`${contrato.dataset.contrato}?${parametros}`, { headers: CABECERAS });
        const datos = await respuesta.json();
        if (numero !== pedido) return; // llegó una respuesta más nueva
        if (datos.texto) {
          for (const clave of ["costo", "restante", "integrantes", "mantenimiento", "atk", "def"]) {
            vista(clave).textContent = datos.texto[clave];
          }
          for (const [tipo, valor] of Object.entries(datos.texto.subtotales)) {
            contrato.querySelector(`[data-subtotal="${tipo}"]`).textContent = valor;
          }
        }
        const mensaje = vista("mensaje");
        const mostrar = Boolean(datos.mensaje) && datos.nuevas !== 0;
        mensaje.hidden = !mostrar;
        mensaje.textContent = mostrar ? datos.mensaje : "";
        confirmar.disabled = !datos.valido;
      } catch {
        // Sin vista previa el formulario sigue funcionando: el servidor valida al enviar.
      }
    }

    contrato.addEventListener("input", () => {
      clearTimeout(espera);
      espera = setTimeout(actualizar, 200);
    });
    actualizar();
  }

  // --- Preparar enfrentamiento: comparación de las legiones elegidas ----------------------

  const preparar = document.querySelector("[data-preparar]");
  if (preparar) {
    const destino = document.getElementById("comparacion");
    preparar.addEventListener("change", async (evento) => {
      if (!evento.target.matches("select")) return;
      const parametros = new URLSearchParams({
        atacante: preparar.elements.atacante.value,
        defensora: preparar.elements.defensora.value,
      });
      try {
        const respuesta = await fetch(`${preparar.dataset.preparar}?${parametros}`, { headers: CABECERAS });
        if (respuesta.ok) destino.innerHTML = await respuesta.text();
      } catch {
        // Si falla, la validación se hace igual al iniciar el enfrentamiento.
      }
    });
  }

  // --- Bitácora: filtros que se aplican al cambiarlos --------------------------------------

  const filtros = document.querySelector("[data-filtros-bitacora]");
  if (filtros) {
    filtros.addEventListener("change", (evento) => {
      if (!evento.target.matches("select")) return;
      if (evento.target.name === "enfrentamiento") filtros.elements.turno.value = "";
      filtros.requestSubmit();
    });
    filtros.addEventListener("submit", () => {
      // Los filtros vacíos no se envían: la dirección queda limpia.
      [...filtros.elements].forEach((campo) => {
        if (campo.name && !campo.value) campo.disabled = true;
      });
    });
    // Al volver con «Atrás», el navegador puede restaurar la página con esos campos deshabilitados.
    window.addEventListener("pageshow", () => {
      [...filtros.elements].forEach((campo) => {
        campo.disabled = false;
      });
    });
  }

  // --- Paneles con scroll: muestran el último suceso --------------------------------------

  function desplazarRegistros(raiz = document) {
    raiz.querySelectorAll("[data-autoscroll]").forEach((lista) => {
      lista.scrollTop = lista.scrollHeight;
    });
  }
  desplazarRegistros();

  // --- Consola de batalla ------------------------------------------------------------------

  const consola = document.querySelector("[data-consola]");
  if (consola) iniciarConsola(consola);

  function iniciarConsola(consola) {
    let automatico = false;
    let velocidad = 800;
    let ocupada = false;
    let temporizador = null;

    const batalla = () => consola.querySelector(".batalla");
    const formularioPaso = () => consola.querySelector("#form-avanzar");
    const enCurso = () => batalla()?.dataset.enCurso === "1";

    function sincronizar() {
      const boton = consola.querySelector("[data-auto]");
      if (boton) {
        boton.classList.toggle("activo", automatico);
        boton.textContent = automatico ? "❚❚ Pausar" : "▶ Automático";
      }
      const selector = consola.querySelector("[data-velocidad]");
      if (selector) selector.value = String(velocidad);
      const paso = batalla()?.dataset.paso;
      document.querySelectorAll("[data-contador-pasos]").forEach((elemento) => {
        elemento.textContent = `Paso ${paso}`;
      });
      document.querySelectorAll("[data-solo-en-curso]").forEach((elemento) => {
        elemento.hidden = !enCurso();
      });
    }

    function detener(motivo) {
      if (!automatico) return;
      automatico = false;
      clearTimeout(temporizador);
      sincronizar();
      if (motivo) avisar(motivo, "info");
    }

    function programar() {
      clearTimeout(temporizador);
      if (!automatico) return;
      if (!enCurso()) {
        detener();
        return;
      }
      temporizador = setTimeout(() => {
        const formulario = formularioPaso();
        if (automatico && formulario && enCurso()) enviar(formulario);
      }, velocidad);
    }

    // Decisiones escritas pero no enviadas: se conservan si la respuesta no avanzó el paso.
    function leerDecisiones() {
      const valores = {};
      consola.querySelectorAll("[data-decision]").forEach((campo) => {
        if (campo.name) valores[campo.name] = campo.value;
      });
      const abiertos = [...consola.querySelectorAll("details[open]")].map((d) => d.closest(".lado")?.className);
      return { valores, abiertos };
    }

    function restaurarDecisiones({ valores, abiertos }, todas) {
      consola.querySelectorAll("[data-decision]").forEach((campo) => {
        const conservar = todas || /^(formacion|convertir)_/.test(campo.name);
        if (conservar && campo.name in valores && !campo.disabled) campo.value = valores[campo.name];
      });
      if (todas) {
        consola.querySelectorAll("details").forEach((detalle) => {
          if (abiertos.includes(detalle.closest(".lado")?.className)) detalle.open = true;
        });
      }
    }

    async function enviar(formulario) {
      if (ocupada) return;
      ocupada = true;
      consola.classList.add("ocupada");
      const pasoAntes = batalla()?.dataset.paso;
      const decisiones = leerDecisiones();
      try {
        const respuesta = await fetch(formulario.action, {
          method: "POST",
          body: new FormData(formulario),
          headers: CABECERAS,
        });
        const estado = respuesta.headers.get("X-Legio-Estado");
        if (!estado) {
          // Sin fragmento de consola (p. ej., no hay campaña abierta): se recarga la página.
          window.location.reload();
          return;
        }
        consola.innerHTML = await respuesta.text();
        if (batalla()?.dataset.paso === pasoAntes) restaurarDecisiones(decisiones, estado === "error");
        desplazarRegistros(consola);
        if (estado === "error") detener("Modo automático detenido: revisa el mensaje de la consola.");
      } catch {
        detener();
        avisar("No se pudo comunicar con el servidor. Revisa que la aplicación siga en ejecución.", "error");
      } finally {
        ocupada = false;
        consola.classList.remove("ocupada");
        sincronizar();
        programar();
      }
    }

    consola.addEventListener("submit", (evento) => {
      const formulario = evento.target;
      if (formulario.id !== "form-avanzar" && !formulario.matches("[data-refuerzos]")) return;
      evento.preventDefault();
      if (formulario.matches("[data-refuerzos]")) detener();
      enviar(formulario);
    });

    consola.addEventListener("click", (evento) => {
      if (!evento.target.closest("[data-auto]")) return;
      if (automatico) {
        detener();
        return;
      }
      automatico = true;
      sincronizar();
      const formulario = formularioPaso();
      if (formulario) enviar(formulario);
    });

    consola.addEventListener("change", (evento) => {
      if (!evento.target.matches("[data-velocidad]")) return;
      velocidad = Number(evento.target.value) || 800;
      programar();
    });

    // Editar una decisión pausa el modo automático para que no se envíe a medias.
    consola.addEventListener("focusin", (evento) => {
      if (automatico && evento.target.matches("[data-decision]")) {
        detener("Modo automático en pausa mientras editas las decisiones del turno.");
      }
    });

    sincronizar();
  }
})();
