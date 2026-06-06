"""
OBJETIVO: Integrar IA para validar imagenes locales antes de activar el flujo MQTT con ESP32-CAM.
SE CARGA EN: Laptop o PC con Python.
RESPONSABLE PRINCIPAL: Alvarez Guevara Estefania Guadalupe.
APOYO DE LECTURA: Rangel revisa la logica de decision y Pablo revisa el uso fisico del sistema.
INTEGRANTES: Alvarez Guevara Estefania Guadalupe (23240077), Rangel Hernandez Aldo (23240272), Reyes Gutierrez Pablo Alberto (23240055)
PROYECTO: VestaGuard

Modelo: clasificacion visual de apoyo con precision aproximada esperada entre 0.80 y 0.92 en un dataset local.
Tipo de prediccion: amenaza, vigilancia o normal a partir de imagenes estaticas.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from servidor_ia import MotorDecisionIA, cv2


def _listar_imagenes(entrada: Path):
    extensiones = {".jpg", ".jpeg", ".png", ".bmp"}
    if entrada.is_file():
        return [entrada]
    return [archivo for archivo in sorted(entrada.rglob("*")) if archivo.suffix.lower() in extensiones]


def main():
    parser = argparse.ArgumentParser(description="Validacion estatica de la IA visual del proyecto")
    parser.add_argument("--entrada", required=True, help="Ruta de imagen o carpeta con imagenes de prueba")
    parser.add_argument("--salida", default="", help="Archivo opcional para guardar resultados JSON")
    args = parser.parse_args()

    motor = MotorDecisionIA()
    entrada = Path(args.entrada)
    imagenes = _listar_imagenes(entrada)

    if not imagenes:
        raise FileNotFoundError(f"No se encontraron imagenes en {entrada}")

    resultados = []
    for ruta in imagenes:
        if cv2 is None:
            raise RuntimeError("OpenCV no esta disponible para abrir la imagen")
        imagen = cv2.imread(str(ruta))
        decision = motor.clasificar_frame(imagen)
        resultado = {
            "archivo": str(ruta),
            "clasificacion": decision.clasificacion,
            "confianza": round(float(decision.confianza), 3),
            "accion": decision.accion,
            "fuente": decision.fuente,
        }
        resultados.append(resultado)
        print(json.dumps(resultado, ensure_ascii=False))

    if args.salida:
        salida = Path(args.salida)
        salida.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
