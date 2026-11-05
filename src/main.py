import argparse
import logging

from api_toggle import ApiToggle
from display import RadarDisplay
from radar import Radar, SimulatedRadar
import config


def main():
    parser = argparse.ArgumentParser(description="RADVEM radar")
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="run with synthetic targets instead of Raspberry Pi hardware",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    print("================================")
    print("CONFIGURAÇÃO CARREGADA")
    print("================================")
    print(f"DETECTION_DISTANCE_CM = {config.DETECTION_DISTANCE_CM}")
    print(f"ANGLE_MIN = {config.ANGLE_MIN}")
    print(f"ANGLE_MAX = {config.ANGLE_MAX}")
    print(f"ANGLE_STEP = {config.ANGLE_STEP}")
    print(f"API_ENABLED = {config.API_ENABLED}")
    print(f"MODO = {'simulação' if args.simulate else 'hardware'}")
    print("================================\n")

    radar = SimulatedRadar() if args.simulate else Radar()
    api_toggle = ApiToggle(
        config.API_URL,
        config.API_TIMEOUT_SECONDS,
        config.API_ENABLED,
    )

    try:
        def nova_deteccao(detection):
            print("\n--- DETECÇÃO ---")
            print(f"ID:        {detection['detection_id']}")
            print(f"Ângulo:    {detection['angle_deg']}°")
            print(f"Distância: {detection['distance_cm']} cm")
            print(f"X:         {detection['x']}")
            print(f"Y:         {detection['y']}")
            print(f"Horário:   {detection['timestamp']}")
            api_toggle.submit(detection)

        print("RADVEM iniciado. Use o botão da interface para controlar a varredura.")
        display = RadarDisplay(
            radar, on_detection=nova_deteccao, api_toggle=api_toggle
        )
        display.run()

    finally:
        try:
            radar.close()
        finally:
            api_toggle.close()


if __name__ == "__main__":
    main()