# RADVEM

Radar didático com varredura eletromecânica, desenvolvido para Raspberry Pi 4
Model B. Um servo SG90 gira um sensor ultrassônico HC-SR04; o programa mede
distâncias, identifica objetos dentro do limite configurado e apresenta as
leituras em uma interface gráfica Tkinter. Uma API HTTP pode ser habilitada
opcionalmente para receber as detecções.

## Funcionalidades

- Varredura de ida e volta entre os ângulos configurados, com deteção de
  objetos até a distância limite.
- Interface Tkinter com ângulo de varredura, botão para iniciar/parar,
  indicadores de estado e pontos de detecção que desaparecem após alguns
  segundos.
- Modo de simulação com três alvos sintéticos, sem acesso ao servo ou sensor.
- Envio opcional de detecções para uma API HTTP em uma thread separada.
- Testes automatizados que não precisam de um Raspberry Pi nem de componentes
  físicos.

## Hardware

O programa usa numeração BCM para os pinos GPIO:

| Componente | Conexão |
| --- | --- |
| Sinal do servo SG90 | GPIO 18 |
| TRIG do HC-SR04 | GPIO 23 |
| ECHO do HC-SR04 | GPIO 24, usando divisor de tensão ou conversor de nível |
| Terra (GND) | Terra comum entre Raspberry Pi, sensor e fonte do servo |

**Segurança elétrica:** o ECHO do HC-SR04 opera a 5 V. Nunca o conecte
diretamente a um GPIO do Raspberry Pi, que opera a 3,3 V. Alimente o servo
com uma fonte externa adequada de 5 V; não use o pino de 3,3 V do Raspberry
Pi para alimentar o servo. Mantenha os terras em comum e confira a pinagem
antes de energizar o circuito.

O aplicativo atual usa uma interface gráfica em monitor conectado ao
Raspberry Pi. Um display OLED e um botão físico mencionados em versões ou
documentos anteriores não fazem parte do software atual.

## Requisitos

- Python 3.
- Tkinter, necessário para a interface gráfica.
- Para execução com hardware: `gpiozero` e `lgpio`, além de acesso aos GPIOs
  no Raspberry Pi.
- Para executar os testes: a biblioteca `hypothesis`.

No Raspberry Pi OS, instale os pacotes do sistema (os nomes podem variar
conforme a versão da distribuição):

```sh
sudo apt update
sudo apt install python3 python3-tk python3-gpiozero python3-lgpio python3-hypothesis
```

Em outros ambientes de desenvolvimento, instale `hypothesis` no ambiente
Python escolhido:

```sh
python -m pip install hypothesis
```

No Windows, o modo de simulação e os testes podem ser usados para
desenvolvimento; a operação com servo e sensor requer Raspberry Pi e os
respectivos drivers GPIO.

## Instalação e execução

Clone o repositório e entre na pasta do projeto. No Raspberry Pi, use uma
sessão gráfica:

```sh
git clone https://github.com/veloy25/RADVEM.git
cd RADVEM
python3 src/main.py
```

Essa execução usa o servo e o sensor físicos. A janela mostra o radar; use
**Iniciar varredura** para começar e **Parar varredura** para pausar. Fechar a
janela encerra os recursos de hardware e a integração com a API.

Para executar a interface sem Raspberry Pi ou componentes físicos:

```sh
python3 src/main.py --simulate
```

O modo de simulação percorre os mesmos fluxos de interface e varredura, com
alvos sintéticos a 30°, 75° e 120°. Ele não simula sinais elétricos, movimento
físico do servo nem leituras reais do sensor.

## Configuração

Os parâmetros ficam em [`src/config.py`](src/config.py):

| Parâmetro | Valor padrão | Descrição |
| --- | ---: | --- |
| `SERVO_GPIO` | 18 | Pino BCM do sinal do servo |
| `TRIG_GPIO` / `ECHO_GPIO` | 23 / 24 | Pinos BCM do sensor HC-SR04 |
| `ANGLE_MIN` / `ANGLE_MAX` | 0° / 150° | Limites da varredura |
| `ANGLE_STEP` | 5° | Incremento angular |
| `SWEEP_TIME` | 1,0 s | Temporização base do trecho; cada posição também aguarda a leitura do sensor |
| `DETECTION_DISTANCE_CM` | 50 cm | Distância máxima para registrar uma detecção |
| `SENSOR_MAX_DISTANCE_CM` | 100 cm | Alcance configurado para o sensor; deve ser maior que o limite de detecção |
| `FADEOUT_TIME` | 3,0 s | Tempo de exibição dos pontos de detecção |
| `SCREEN_WIDTH` / `SCREEN_HEIGHT` | 800 / 480 | Tamanho da janela |
| `API_ENABLED` | `False` | Estado inicial do envio à API |
| `API_URL` | URL configurada no arquivo | Endpoint HTTP de detecções |
| `API_TIMEOUT_SECONDS` | 5 s | Timeout de cada requisição |
| `RADAR_ID` | `RADVEM-001` | Identificador do radar na detecção local |

Altere esses valores em `src/config.py` e confira a montagem elétrica antes de
usar uma configuração de GPIO diferente. O valor do servo é calculado
linearmente com base em `ANGLE_MIN` e `ANGLE_MAX`; confirme os limites
mecânicos do servo antes de ampliar o intervalo.

## Detecções e API

Cada detecção criada localmente contém `radar_id`, `detection_id`,
`timestamp`, `angle_deg`, `distance_cm`, `x` e `y`. `x` e `y` são
coordenadas em pixels na interface. O eixo horizontal cresce para a direita e
o eixo vertical da tela cresce para baixo.

O envio está desativado por padrão. Quando ativado, use a caixa **API** na
interface. O cliente envia uma requisição HTTP `POST` com conteúdo JSON; o
corpo contém somente:

```json
{
  "angle_degrees": 30,
  "distance_cm": 8.0,
  "x_cm": 6.9,
  "y_cm": 4.0
}
```

As coordenadas em centímetros são calculadas a partir do ângulo e da
distância: `x_cm` usa o cosseno e `y_cm` usa o seno, com Y positivo para
cima. O identificador do radar, o ID da detecção, o horário e as coordenadas
em pixels não são enviados.

Antes de habilitar o envio, confirme com o serviço remoto a URL, o contrato do
JSON, a autenticação e as respostas esperadas. O cliente não implementa
autenticação, repetição automática nem fila persistente; falhas de envio são
registradas no log da aplicação.

## Testes

Execute os testes automatizados na raiz do repositório:

```sh
python3 -m unittest discover -s tests -v
```

Os testes cobrem a conversão de ângulo do servo, os limites da varredura, o
modo de simulação, o desenho da interface e o comportamento da integração
com a API. Os testes de hardware usam objetos simulados; passar neles não
substitui validar o circuito real no Raspberry Pi. Não é necessário iniciar a
interface nem conectar o hardware para executar a suíte.

## Estrutura do projeto

```text
src/
  api.py          Cliente HTTP e envio de detecções em segundo plano
  api_toggle.py   Ativação e encerramento da integração com a API
  config.py       Pinos e parâmetros do radar, interface e API
  display.py      Interface gráfica e processamento de eventos
  main.py         Inicialização e coordenação da aplicação
  radar.py        Varredura, leituras, detecções e simulador
tests/
  test_api.py
  test_api_toggle.py
  test_display.py
  test_radar_hardware.py
  test_radar_simulation.py
  test_servo_formula.py
```

## Equipe

- Fábio Sadao Sato - 22.00984-0
- Gabriel Barrochelo — 22.10193-4
- Ruth Romeu Ramos — 22.01003-3
- Vinicius Eloy Araujo — 22.01026-2

## Apresentação

[Vídeo do projeto](https://mauabr-my.sharepoint.com/:v:/g/personal/22_01026-2_maua_br/IQCVvv75TYhwQJXoWr_qHLo0AcjH3mTAMmMyXW0rdlmhDQ0?nav=eyJyZWZlcnJhbEluZm8iOnsicmVmZXJyYWxBcHAiOiJPbmVEcml2ZUZvckJ1c2luZXNzIiwicmVmZXJyYWxBcHBQbGF0Zm9ybSI6IldlYiIsInJlZmVycmFsTW9kZSI6InZpZXciLCJyZWZlcnJhbFZpZXciOiJNeUZpbGVzTGlua0NvcHkifX0&e=1gfOAm)

## Documentação complementar

O documento de arquitetura do workspace está em
`../RADVEM_ARQUITETURA_SOFTWARE.md`. Ele fica fora deste repositório e pode
não estar disponível em um clone independente.
