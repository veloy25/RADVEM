from radar import Radar
import config


def nova_deteccao(detection):
    print("\n--- DETECÇÃO ---")
    print(f"ID:       {detection['detection_id']}")
    print(f"Ângulo:   {detection['angle_deg']}°")
    print(f"Distância:{detection['distance_cm']} cm")
    print(f"X:        {detection['x']}")
    print(f"Y:        {detection['y']}")
    print(f"Horário:  {detection['timestamp']}")


def main():
    print("================================")
    print("CONFIGURAÇÃO CARREGADA")
    print("================================")
    print(f"DETECTION_DISTANCE_CM = {config.DETECTION_DISTANCE_CM}")
    print(f"ANGLE_MIN = {config.ANGLE_MIN}")
    print(f"ANGLE_MAX = {config.ANGLE_MAX}")
    print(f"ANGLE_STEP = {config.ANGLE_STEP}")
    print("================================\n")

    radar = Radar()

    radar.on_detection = nova_deteccao

    try:
        print("RADVEM iniciado.")
        print("Pressione Ctrl+C para parar.\n")

        radar.start()

        while True:
            radar.update()

    except KeyboardInterrupt:
        print("\nEncerrando RADVEM...")

    finally:
        radar.close()
        print("Radar encerrado.")


if __name__ == "__main__":
    main()